import bpy

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from . import c_utils as CTU
from . import pme
from .addon import uprefs
# from .bl_utils import ctx_dict
from .debug_utils import logi


def redraw_screen(area=None):
    # area = area or bpy.context.area or bpy.context.screen.areas[0]
    # if not area:
    #     return

    # with bpy.context.temp_override(area=area):
    #     bpy.ops.screen.screen_full_area()

    view = uprefs().view
    s = view.ui_scale
    view.ui_scale = 0.5
    view.ui_scale = s


def toggle_header(area):
    area.spaces.active.show_region_header = \
        not area.spaces.active.show_region_header


def move_header(area=None, top=None, visible=None, auto=None):
    if top is None and visible is None and auto is None:
        return True

    if auto is not None and top is None:
        return True

    area = area or bpy.context.area
    if not area:
        return True

    rh, rw = None, None
    for r in area.regions:
        if r.type == 'HEADER':
            rh = r
        elif r.type == 'WINDOW':
            rw = r

    is_visible = rh.height > 1
    if is_visible:
        is_top = rw.y == area.y
    else:
        is_top = rh.y > area.y

    kwargs = get_override_args(area=area, region=rh)
    if auto:
        if top:
            if is_top:
                with bpy.context.temp_override(**kwargs):
                    toggle_header(area)
            else:
                with bpy.context.temp_override(**kwargs):
                    bpy.ops.screen.region_flip()
                    not is_visible and toggle_header(area)
        else:
            if is_top:
                with bpy.context.temp_override(**kwargs):
                    bpy.ops.screen.region_flip()
                    not is_visible and toggle_header(area)
            else:
                with bpy.context.temp_override(**kwargs):
                    toggle_header(area)
    else:
        if top is not None and top != is_top:
            with bpy.context.temp_override(**kwargs):
                bpy.ops.screen.region_flip()

        if visible is not None and visible != is_visible:
            with bpy.context.temp_override(**kwargs):
                toggle_header(area)
    return True


# def parse_extra_keywords(kwargs_str: str) -> dict:
#     """
#     Parse a comma-separated string like:
#       "window=Window, screen=Screen.001, workspace=MyWorkspace"
#     into a dict:
#       { "window": "Window", "screen": "Screen.001", "workspace": "MyWorkspace" }
#     """
#     if not kwargs_str.strip():
#         return {}
#     kwargs = {}
#     for kv in kwargs_str.split(","):
#         kv = kv.strip()
#         if "=" not in kv:
#             continue
#         k, v = kv.split("=", 1)
#         kwargs[k.strip()] = v.strip()
#     return kwargs


def find_area(
    area_or_type: Union[str, bpy.types.Area, None],
    screen_or_name: Union[str, bpy.types.Screen, None] = None
) -> Optional[bpy.types.Area]:
    """Find and return an Area object, or None if not found."""
    try:
        if area_or_type is None:
            # return bpy.context.area  # fallback
            return None

        if isinstance(area_or_type, bpy.types.Area):
            return area_or_type

        # Find screen
        screen = None
        if isinstance(screen_or_name, bpy.types.Screen):
            screen = screen_or_name
        elif isinstance(screen_or_name, str):
            screen = bpy.data.screens.get(screen_or_name)
        else:
            screen = bpy.context.screen

        if screen:
            for a in screen.areas:
                if a.type == area_or_type:
                    return a

    except ReferenceError:
        # print_exc("find_area: invalid reference")
        pass

    return None


def find_region(
    region_or_type: Union[str, bpy.types.Region, None],
    area_or_type: Union[str, bpy.types.Area, None] = None,
    screen_or_name: Union[str, bpy.types.Screen, None] = None
) -> Optional[bpy.types.Region]:
    """Find and return a Region object within the specified Area, or None if not found."""
    try:
        if region_or_type is None:
            # return bpy.context.region  # fallback
            return None

        # Resolve area first
        area = find_area(area_or_type, screen_or_name)
        if not area:
            return None

        if isinstance(region_or_type, bpy.types.Region):
            return region_or_type

        for r in area.regions:
            if r.type == region_or_type:
                return r

    except ReferenceError:
        # print_exc("find_region: invalid reference")
        pass

    return None


def resolve_window(
    value: Optional[Union[str, bpy.types.Window]],
    context: bpy.types.Context,
) -> Optional[bpy.types.Window]:
    """Resolve string or Window object into a Window object, fallback to context.window if none."""
    if isinstance(value, bpy.types.Window):
        logi(f"resolve_window: {value}")
        return value
    # if isinstance(value, str):
    #     if w := context.window_manager.windows.get(value, None):
    #         return w
    #     return None
    logi(f"window fallback: {context.window}")
    # return context.window  # fallback
    return None


def resolve_screen(
    value: Optional[Union[str, bpy.types.Screen]],
    context: bpy.types.Context
) -> Optional[bpy.types.Screen]:
    """Resolve string or Screen object into a Screen object, fallback to context.screen if none."""
    if isinstance(value, bpy.types.Screen):
        logi(f"resolve_screen: {value}")
        return value
    # if isinstance(value, str):
    #     return bpy.data.screens.get(value)
    logi(f"screen fallback: {context.screen}")
    # return context.screen  # fallback
    return None


@dataclass
class ContextOverride:
    """
    Container for context override parameters.
    Allows specifying string or object references for Window/Screen/Area/Region,
    plus any additional overrides in 'extra'.
    """
    window: Optional[Union[str, bpy.types.Window]] = None
    screen: Optional[Union[str, bpy.types.Screen]] = None
    area: Optional[Union[str, bpy.types.Area]] = None
    region: Optional[Union[str, bpy.types.Region]] = None
    blend_data: Optional[bpy.types.BlendData] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate(
        self,
        context: bpy.types.Context,
        *,
        extra_priority: bool = False,
        delete_none: bool = True
    ) -> Dict[str, Any]:
        """
        Validate and resolve all fields into actual Blender objects.
        If 'extra_priority' is True, 'extra' keys override base fields.
        Otherwise, base fields override 'extra'.

        :param context: Must be an instance of bpy.types.Context, else TypeError
        :param extra_priority: If True, the base fields will override keys in 'extra'
                            (so 'extra' is applied first, then base).
        :param delete_none: If True, remove None entries from final dict.
        :param strict: If True, raise ValueError or TypeError if invalid references found
                       (e.g. invalid window). If False, just fallback or ignore.
        :return: A dict suitable for `with context.temp_override(**...)`.
        """
        # Resolve all fields
        w = resolve_window(self.window, context)
        sc = resolve_screen(self.screen, context)
        a = find_area(self.area, sc)
        r = find_region(self.region, self.area, sc)
        bd = self.blend_data  # or context.blend_data

        base_dict = {
            "window": w,
            "screen": sc,
            "area": a,
            "region": r,
            "blend_data": bd,
        }

        # TODO: Extra does not check for windows, areas, etc.
        if extra_priority:
            primary_dict = self.extra
            secondary_dict = base_dict
        else:
            primary_dict = base_dict
            secondary_dict = self.extra

        context_params = {**secondary_dict, **primary_dict}

        if delete_none:
            context_params = {k: v for k, v in context_params.items() if v is not None}

        return context_params

    def __str__(self):
        return (
            f"ContextOverride(\n"
            f"window={self.window},\n"
            f"screen={self.screen},\n"
            f"area={self.area},\n"
            f"region={self.region},\n"
            f"blend_data={self.blend_data},\n"
            f"extra={self.extra})\n"
        )


def create_context_override(
    area: Union[str, bpy.types.Area, None] = None,
    region: Union[str, bpy.types.Region, None] = None,  # "WINDOW",
    # screen: Union[str, bpy.types.Screen, None] = None,  # comment out for Test
    # window: Union[str, bpy.types.Window, None] = None,  # comment out for Test
    # override_kwargs_str: str = "",
    **kwargs,
) -> ContextOverride:
    # extra_kwargs = parse_extra_keywords(override_kwargs_str)
    extra_kwargs = {}
    extra_kwargs.update(kwargs)

    return ContextOverride(
        # window=window,
        # screen=screen,
        area=area,
        region=region,
        extra=extra_kwargs,
    )


def get_override_args(
    area: Union[str, bpy.types.Area] = None,
    region: Union[str, bpy.types.Region] = "WINDOW",
    screen: Union[str, bpy.types.Screen] = None,
    window: Union[str, bpy.types.Window] = None,
    # override_kwargs_str: str = "",
    extra_priority: bool = False,
    delete_none: bool = True,
    **kwargs,
) -> dict:
    cov = create_context_override(
        area=area,
        region=region,
        screen=screen,
        window=window,
        # override_kwargs_str=override_kwargs_str,
        **kwargs,
    )
    return cov.validate(bpy.context, extra_priority=extra_priority, delete_none=delete_none)


def focus_area(area, center=False, cmd=None):
    area = find_area(area)
    if not area:
        return

    event = pme.context.event
    move_flag = False
    if not event:
        center = True

    if center:
        x = area.x + area.width // 2
        y = area.y + area.height // 2
        move_flag = True
    else:
        x, y = event.mouse_x, event.mouse_y
        x = max(x, area.x)
        x = min(x, area.x + area.width - 1)
        y = max(y, area.y)
        y = min(y, area.y + area.height - 1)
        if x != event.mouse_x or y != event.mouse_y:
            move_flag = True

    if move_flag:
        bpy.context.window.cursor_warp(x, y)

    if cmd:
        with bpy.context.temp_override(area=area):
            bpy.ops.pme.timeout(cmd=cmd)


# TODO: Remove this function
def override_context(
        area, screen=None, window=None, region='WINDOW', **kwargs):
    # This is no longer necessary
    # but is documented in the old user docs so keeping it for now

    import traceback
    import warnings
    caller = traceback.extract_stack(None, 2)[0]
    warnings.warn(
        f"Deprecated: 'override_context' is deprecated, use 'get_override_args' instead. "
        f"Called from {caller.name} at {caller.line}",
        DeprecationWarning,
        stacklevel=2
    )
    return get_override_args(area, region, screen, window, **kwargs)


def toggle_sidebar(area=None, tools=True, value=None):
    area = find_area(area)

    s = area.spaces.active
    if tools and hasattr(s, "show_region_toolbar"):
        if value is None:
            value = not s.show_region_toolbar

        s.show_region_toolbar = value

    elif not tools and hasattr(s, "show_region_ui"):
        if value is None:
            value = not s.show_region_ui

        s.show_region_ui = value

    return True


def register():
    pme.context.add_global("focus_area", focus_area)
    pme.context.add_global("move_header", move_header)
    pme.context.add_global("toggle_sidebar", toggle_sidebar)
    pme.context.add_global("override_context", override_context)
    pme.context.add_global("redraw_screen", redraw_screen)
