import bpy

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from . import c_utils as CTU
from . import pme
from .addon import uprefs
# from .bl_utils import ctx_dict
from .debug_utils import logi


def redraw_screen():
    view = uprefs().view
    s = view.ui_scale
    view.ui_scale = 0.5
    view.ui_scale = s


def toggle_header(area=None):
    if area is None:
        return

    area.spaces.active.show_region_header ^= True


def move_header(area=None, top=None, visible=None, auto=None):
    if all(v is None for v in (top, visible, auto)):
        return True

    if auto is not None and top is None:
        return True

    C = bpy.context
    area = area or C.area
    if not area:
        return True

    rh, rw = None, None
    for r in area.regions:
        if r.type == 'HEADER':
            rh = r
        elif r.type == 'WINDOW':
            rw = r

    is_visible = rh.height > 1
    is_top = rh.y > area.y

    # TODO: Check why it was reversed above
    # is_top = (rw.y == area.y) if is_visible else (rh.y > area.y)

    kwargs = get_override_args(area=area, region=rh)
    if auto:
        if top:
            if is_top:
                with C.temp_override(**kwargs):
                    toggle_header(area)
            else:
                with C.temp_override(**kwargs):
                    bpy.ops.screen.region_flip()

                not is_visible and toggle_header(area)
        else:
            if is_top:
                with C.temp_override(**kwargs):
                    bpy.ops.screen.region_flip()

                not is_visible and toggle_header(area)
            else:
                toggle_header(area)
    else:
        if top is not None and top != is_top:
            with C.temp_override(**kwargs):
                bpy.ops.screen.region_flip()

        if visible is not None and visible != is_visible:
            toggle_header(area)

    return True


def find_area(
    area_or_type: Union[str, bpy.types.Area, None],
    screen_or_name: Union[str, bpy.types.Screen, None] = None
    # reverse: bool = False  # ref PME_OT_area_move.invoke()
) -> Optional[bpy.types.Area]:
    """Find and return an Area object, or None if not found."""
    if area_or_type is None:
        return None

    if isinstance(area_or_type, bpy.types.Area):
        return area_or_type

    screen = find_screen(screen_or_name, bpy.context)
    if screen is None:
        screen = bpy.context.screen

    for a in screen.areas:
        if a.type == area_or_type:
            return a

    return None


def find_region(
    region_or_type: Union[str, bpy.types.Region, None],
    area_or_type: Union[str, bpy.types.Area, None] = None,
    screen_or_name: Union[str, bpy.types.Screen, None] = None
) -> Optional[bpy.types.Region]:
    """Find and return a Region object within the specified Area, or None if not found."""
    if region_or_type is None:
        return None

    if isinstance(region_or_type, bpy.types.Region):
        return region_or_type

    area = find_area(area_or_type, screen_or_name)
    if area is None:
        area = bpy.context.area

    for r in area.regions:
        if r.type == region_or_type:
            return r

    return None


def find_window(
    window_identifier: Optional[Union[str, int, bpy.types.Window, None]],
    context: bpy.types.Context,
) -> Optional[bpy.types.Window]:
    """Find and return a Window object, or None if not found."""
    if window_identifier is None:
        return None

    if isinstance(window_identifier, bpy.types.Window):
        return window_identifier

    if isinstance(window_identifier, (str, int)) \
        and str(window_identifier).isdigit():
        index = int(window_identifier)
    else:
        index = None

    wm = context.window_manager
    if index is not None:
        if index < 0:
            index = len(wm.windows) + index
        index = max(0, min(index, len(wm.windows) - 1))
        return wm.windows[index]

    return None


def find_screen(
    screen_identifier: Union[str, bpy.types.Screen, None],
    context: bpy.types.Context
) -> Optional[bpy.types.Screen]:
    """Find and return a Screen object, or None if not found."""
    if screen_identifier is None:
        return None

    if isinstance(screen_identifier, bpy.types.Screen):
        return screen_identifier

    if isinstance(screen_identifier, str):
        return bpy.data.screens.get(screen_identifier, None)

    return None


class ContextOverride:
    def __init__(
        self,
        *,
        window: Union[str, bpy.types.Window, None] = None,
        screen: Union[str, bpy.types.Screen, None] = None,
        area: Union[str, bpy.types.Area, None] = None,
        region: Union[str, bpy.types.Region, None] = None,
        **kwargs: Any,
    ):
        self.window = window
        self.screen = screen
        self.area = area
        self.region = region
        self.kwargs = kwargs

    def validate(
        self,
        context: bpy.types.Context,
        *,
        # extra_priority: bool = False,
        delete_none: bool = True
    ) -> Dict[str, Any]:

        # Resolve all fields
        w = find_window(self.window, context)
        sc = find_screen(self.screen, context)
        a = find_area(self.area, sc)
        r = find_region(self.region, self.area, sc)
        # bd = self.blend_data  # or context.blend_data

        base_dict = {
            "window": w,
            "screen": sc,
            "area": a,
            "region": r,
            # "blend_data": bd,
        }

        context_params = {**base_dict, **self.kwargs}

        if delete_none:
            context_params = {k: v for k, v in context_params.items() if v is not None}

        return context_params

    def __str__(self):
        return (
            f"ContextOverride(\n"
            f"  window={self.window},\n"
            f"  screen={self.screen},\n"
            f"  area={self.area},\n"
            f"  region={self.region},\n"
            f"  kwargs={self.kwargs})\n"
        )


def get_override_args(
    area: Union[str, bpy.types.Area] = None,
    region: Union[str, bpy.types.Region] = "WINDOW",
    screen: Union[str, bpy.types.Screen] = None,
    window: Union[str, bpy.types.Window] = None,
    delete_none: bool = True,
    **kwargs,
) -> dict:
    """Get a dictionary of context override arguments."""
    override = ContextOverride(
        area=area,
        region=region,
        screen=screen,
        window=window,
        **kwargs,
    )
    return override.validate(bpy.context, delete_none=delete_none)


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


def override_context(
    area, screen=None, window=None, region='WINDOW', enter=True, **kwargs):
    context = bpy.context
    window = find_window(window, context)
    screen = find_screen(screen, context)
    area = find_area(area, screen)
    region = find_region(region, area, screen)

    if all(v is None for v in (window, screen, area, region)):
        oc = context.temp_override()
        enter and oc.__enter__()
        return oc

    oc = context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
        blend_data=context.blend_data,
        **kwargs
    )
    enter and oc.__enter__()
    return oc


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
