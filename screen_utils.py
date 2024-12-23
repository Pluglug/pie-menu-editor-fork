import bpy

from typing import Union

from . import c_utils as CTU
from . import pme
from .addon import uprefs
# from .bl_utils import ctx_dict


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


def find_area(
    area_or_type: Union[str, bpy.types.Area],
    screen_or_name: Union[str, bpy.types.Screen, None] = None,
) -> Union[bpy.types.Area, None]:
    """Find and return an Area object."""
    if area_or_type is None:
        area_or_type = bpy.context.area

    if isinstance(area_or_type, bpy.types.Area):
        return area_or_type

    screen = None
    if isinstance(screen_or_name, bpy.types.Screen):
        screen = screen_or_name
    elif isinstance(screen_or_name, str):
        screen = bpy.data.screens.get(screen_or_name, None)
    else:
        screen = bpy.context.screen

    if screen:
        for a in screen.areas:
            if a.type == area_or_type:
                return a

    return None


def find_region(
    region_or_type: Union[str, bpy.types.Region],
    area_or_type: Union[str, bpy.types.Area] = None,
    screen_or_name: Union[str, bpy.types.Screen, None] = None,
) -> Union[bpy.types.Region, None]:
    """Find and return a Region object within the specified Area."""
    if region_or_type is None:
        region_or_type = bpy.context.region.type

    area = find_area(area_or_type, screen_or_name)
    if not area:
        return None

    if isinstance(region_or_type, bpy.types.Region):
        return region_or_type

    for r in area.regions:
        if r.type == region_or_type:
            return r

    return None


def get_override_args(
    area: Union[str, bpy.types.Area] = None,
    region: Union[str, bpy.types.Region] = "WINDOW",
    screen: Union[str, bpy.types.Screen] = None,
    window: bpy.types.Window = None,
    **kwargs,
):
    """Get the override context arguments"""
    window = window or bpy.context.window
    screen = screen or bpy.context.screen

    area = find_area(area, screen)
    region = find_region(region, area)

    override_args = {
        "area": area,
        "region": region,
        "screen": screen,
        "window": window,
        "blend_data": bpy.context.blend_data,
    }

    override_args.update(kwargs)
    override_args = {k: v for k, v in override_args.items() if v is not None}

    return override_args


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
