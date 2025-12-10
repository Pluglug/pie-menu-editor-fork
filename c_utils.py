import bpy
from bpy.app import version as APP_VERSION
from bpy.props import StringProperty
import re
from itertools import islice

from ctypes import (
    Structure,
    POINTER,
    cast,
    addressof,
    pointer,
    c_short,
    c_uint,
    c_int,
    c_float,
    c_bool,
    c_char,
    c_char_p,
    c_void_p,
    c_uint32,  # For session_uid and other uint32 fields
)
from . import pme


# Constants from Blender 4.x source
# Source: /home/myname/blender/blender/source/blender/makesdna/DNA_ID.h
MAX_ID_NAME = 258  # Updated from 66 to 258 in Blender 4.x

# Source: Various DNA files
BKE_ST_MAXNAME = 64
UI_MAX_DRAW_STR = 400
UI_MAX_NAME_STR = 128
UI_BLOCK_LOOP = 1 << 0
UI_BLOCK_KEEP_OPEN = 1 << 8
UI_BLOCK_POPUP = 1 << 9
UI_BLOCK_RADIAL = 1 << 20
UI_EMBOSS = 0

re_field = re.compile(r"(\*?)(\w+)([\[\d\]]+)?$")


def struct(name, bases=None):
    bases = ((Structure,) + bases) if bases else (Structure,)
    return type(name, bases, {})


def gen_fields(*args):
    ret = []
    cur_tp = None

    def parse_str(arg):
        mo = re_field.match(arg)
        p, f, n = mo.groups()
        tp = POINTER(cur_tp) if p else cur_tp

        if n:
            for n in reversed(re.findall(r"\[(\d+)\]", n)):
                tp *= int(n)

        ret.append((f, tp))

    for a in args:
        if isinstance(a, tuple):
            if (a[0] and APP_VERSION < a[1]) or (not a[0] and APP_VERSION >= a[1]):
                continue

            cur_tp = a[2]
            for t_arg in islice(a, 3, None):
                parse_str(t_arg)

        elif isinstance(a, str):
            parse_str(a)

        else:
            cur_tp = a

    return ret


def gen_pointer(obj, tp=None):
    if not tp:
        tp = Link

    if obj is None or isinstance(obj, int):
        return cast(obj, POINTER(tp))
    else:
        return pointer(obj)


class _ListBase:
    def __len__(self):
        ret = 0
        link_lp = cast(self.first, POINTER(Link))
        while link_lp:
            ret += 1
            link_lp = link_lp.contents.next

        return ret

    def insert(self, prevlink, newlink):
        if prevlink:
            a = prevlink if isinstance(prevlink, int) else addressof(prevlink)
            prevlink_p = cast(a, POINTER(Link)).contents
        else:
            prevlink_p = None

        if newlink:
            a = newlink if isinstance(newlink, int) else addressof(newlink)
            newlink_p = cast(a, POINTER(Link)).contents
        else:
            newlink_p = None

        if not newlink_p:
            return

        if not self.first:
            self.first = self.last = addressof(newlink_p)
            return

        if not prevlink_p:
            newlink_p.prev = None
            newlink_p.next = gen_pointer(self.first)
            newlink_p.next.contents.prev = gen_pointer(newlink_p)
            self.first = addressof(newlink_p)
            return

        if self.last == addressof(prevlink_p):
            self.last = addressof(newlink_p)

        newlink_p.next = prevlink_p.next
        newlink_p.prev = gen_pointer(prevlink_p)
        prevlink_p.next = gen_pointer(newlink_p)
        if newlink_p.next:
            newlink_p.next.contents.prev = gen_pointer(newlink_p)

    def remove(self, link):
        if link:
            a = link if isinstance(link, int) else addressof(link)
            link_p = cast(a, POINTER(Link)).contents
        else:
            return

        if link_p.next:
            link_p.next.contents.prev = link_p.prev
        if link_p.prev:
            link_p.prev.contents.next = link_p.next

        if self.last == addressof(link_p):
            self.last = cast(link_p.prev, c_void_p)
        if self.first == addressof(link_p):
            self.first = cast(link_p.next, c_void_p)

    def find(self, idx):
        if idx < 0:
            return None

        link_lp = cast(self.first, POINTER(Link))
        for i in range(idx):
            link_lp = link_lp.contents.next

        return link_lp.contents if link_lp else None


ID = struct("ID")
Link = struct("Link")
ListBase = struct("ListBase", (_ListBase,))
rctf = struct("rctf")
rcti = struct("rcti")
uiItem = struct("uiItem")
uiLayout = struct("uiLayout")
uiLayoutRoot = struct("uiLayoutRoot")
uiStyle = struct("uiStyle")
uiFontStyle = struct("uiFontStyle")
uiBlock = struct("uiBlock")
# uiBut = struct("uiBut")  # see #18
vec2s = struct("vec2s")
ScrVert = struct("ScrVert")
ScrArea = struct("ScrArea")
ScrArea_Runtime = struct("ScrArea_Runtime")
ScrAreaMap = struct("ScrAreaMap")
ARegion = struct("ARegion")
bScreen = struct("bScreen")
bContext = struct("bContext")
bContext_wm = struct("bContext_wm")
bContext_data = struct("bContext_data")
wmWindow = struct("wmWindow")
wmEventHandler_KeymapFn = struct("wmEventHandler_KeymapFn")
wmEventHandler = struct("wmEventHandler")
wmOperator = struct("wmOperator")
# wmEvent = struct("wmEvent")

# ID structure definition for Blender 4.x
# Source: /home/myname/blender/blender/source/blender/makesdna/DNA_ID.h (lines 402-480)
# Last verified: 2024-06-26
# Changes from old version:
# - name field changed from char[66] to char[258] (MAX_ID_NAME)
# - Added asset_data field
# - recalc type changed from int to unsigned int
# - Added recalc_up_to_undo_push, recalc_after_undo_push fields
# - Added session_uid field
# - Added system_properties field
# - Added _pad1 padding
# - Added override_library field
# - Added orig_id field
# - Added py_instance field
# - Added library_weak_reference field
# - Added runtime field
ID._fields_ = gen_fields(
    c_void_p, "*next", "*prev",           # void *next, *prev;
    ID, "*newid",                         # struct ID *newid;
    c_void_p, "*lib",                     # struct Library *lib;
    c_void_p, "*asset_data",              # struct AssetMetaData *asset_data;
    c_char, f"name[{MAX_ID_NAME}]",       # char name[258]; (was char[66])
    c_short, "flag",                      # short flag;
    c_int, "tag",                         # int tag;
    c_int, "us",                          # int us;
    c_int, "icon_id",                     # int icon_id;
    c_uint, "recalc",                     # unsigned int recalc; (was int)
    c_uint, "recalc_up_to_undo_push",     # unsigned int recalc_up_to_undo_push;
    c_uint, "recalc_after_undo_push",     # unsigned int recalc_after_undo_push;
    c_uint32, "session_uid",              # unsigned int session_uid;
    c_void_p, "*properties",              # IDProperty *properties;
    c_void_p, "*system_properties",       # IDProperty *system_properties;
    c_void_p, "_pad1",                    # void *_pad1;
    c_void_p, "*override_library",        # IDOverrideLibrary *override_library;
    ID, "*orig_id",                       # struct ID *orig_id;
    c_void_p, "*py_instance",             # void *py_instance;
    c_void_p, "*library_weak_reference",  # struct LibraryWeakReference *library_weak_reference;
    c_void_p, "runtime",                  # struct ID_Runtime runtime; (opaque pointer)
)

rcti._fields_ = gen_fields(
    c_int, "xmin", "xmax",
    c_int, "ymin", "ymax",
)

rctf._fields_ = gen_fields(
    c_float, 'xmin', 'xmax',
    c_float, 'ymin', 'ymax',
)

uiFontStyle._fields_ = gen_fields(
    c_short, "uifont_id",
    c_short, "points",
    c_short, "kerning",
    c_char, "word_wrap",
    c_char, "pad[5]",
    c_short, "italic", "bold",
    c_short, "shadow",
    c_short, "shadx", "shady",
    c_short, "align",
    c_float, "shadowalpha",
    c_float, "shadowcolor",
)

# source/blender/makesdna/DNA_listBase.h
Link._fields_ = gen_fields(
    Link, '*next', '*prev',
)

# source/blender/makesdna/DNA_listBase.h
ListBase._fields_ = gen_fields(
    c_void_p, "first", "last",
)

uiItem._fields_ = gen_fields(
    c_void_p, "*next", "*prev",
    c_int, "type",
    c_int, "flag",
)

# source/blender/editors/interface/interface_layout.c
uiLayout._fields_ = gen_fields(
    uiItem, "item",
    uiLayoutRoot, "*root",
    c_void_p, "*context",
    uiLayout, "*parent",
    ListBase, "items",
    c_char * UI_MAX_NAME_STR, "heading",
    uiLayout, "*child_items_layout",
    c_int, "x", "y", "w", "h",
    c_float, "scale[2]",
    c_short, "space",
    c_bool, "align",
    c_bool, "active",
    c_bool, "active_default",
    c_bool, "active_init",
    c_bool, "enabled",
    c_bool, "redalert",
    c_bool, "keepaspect",
    c_bool, "variable_size",
    c_char, "alignment",
)

uiLayoutRoot._fields_ = gen_fields(
    uiLayoutRoot, "*next", "*prev",
    c_int, "type",
    c_int, "opcontext",
    c_int, "emw", "emh",
    c_int, "padding",
    c_void_p, "handlefunc",
    c_void_p, "*argv",
    uiStyle, "*style",
    uiBlock, "*block",
    uiLayout, "*layout",
)

# uiStyle structure definition for Blender 4.x
# Source: /home/myname/blender/blender/source/blender/makesdna/DNA_userdef_types.h (lines 88-115)
# Last verified: 2024-06-26
# Changes from old version:
# - Removed widgetlabel field
# - Added tooltip field (uiFontStyle)
# - Field order unchanged for remaining fields
uiStyle._fields_ = gen_fields(
    uiStyle, "*next", "*prev",           # struct uiStyle *next, *prev;
    c_char, "name[64]",                  # char name[64];
    uiFontStyle, "paneltitle",           # uiFontStyle paneltitle;
    uiFontStyle, "grouplabel",           # uiFontStyle grouplabel;
    uiFontStyle, "widget",               # uiFontStyle widget;
    uiFontStyle, "tooltip",              # uiFontStyle tooltip; (NEW)
    c_float, "panelzoom",                # float panelzoom;
    c_short, "minlabelchars",            # short minlabelchars;
    c_short, "minwidgetchars",           # short minwidgetchars;
    c_short, "columnspace",              # short columnspace;
    c_short, "templatespace",            # short templatespace;
    c_short, "boxspace",                 # short boxspace;
    c_short, "buttonspacex",             # short buttonspacex;
    c_short, "buttonspacey",             # short buttonspacey;
    c_short, "panelspace",               # short panelspace;
    c_short, "panelouter",               # short panelouter;
    c_char, "_pad0[2]",                  # char _pad0[2];
)

uiBlock._fields_ = gen_fields(
    uiBlock, "*next", "*prev",
    ListBase, "buttons",
    c_void_p, "*panel",
    uiBlock, "*oldblock",
    ListBase, "butstore",
    ListBase, "layouts",
    c_void_p, "*curlayout",
    ListBase, "contexts",
    c_char * UI_MAX_NAME_STR, "name",
    c_float, "winmat[4][4]",
    rctf, "rect",
    c_float, "aspect",
    c_uint, "puphash",
    c_void_p, "func",
    c_void_p, "*func_arg1",
    c_void_p, "*func_arg2",
    c_void_p, "funcN",
    c_void_p, "*func_argN",
    c_void_p, "butm_func",
    c_void_p, "*butm_func_arg",
    c_void_p, "handle_func",
    c_void_p, "*handle_func_arg",
    c_void_p, "*block_event_func",
    c_void_p, "*drawextra",
    c_void_p, "*drawextra_arg1",
    c_void_p, "*drawextra_arg2",
    c_int, "flag",
    # c_short, "alignnr",
    # c_short, "content_hints",
    # c_char, "direction",
    # c_char, "theme_style",
    # c_char, "dt",
)

# uiBut._fields_ = gen_fields( # see #18
#     uiBut, "*next", "*prev",
#     c_int, "flag", "drawflag",
#     c_int, "type",
#     c_int, "pointype",
#     c_short, "bit", "bitnr", "retval", "strwidth", "alignnr",
#     c_short, "ofs", "pos", "selsta", "selend",
#     c_char, "*str",
#     c_char * UI_MAX_NAME_STR, "strdata",
#     c_char * UI_MAX_DRAW_STR, "drawstr",
#     rctf, "rect",
# )

bContext_wm._fields_ = gen_fields(
    c_void_p, "*manager",
    c_void_p, "*window",
    c_void_p, "*workspace",
    c_void_p, "*screen",
    ScrArea, "*area",
    ARegion, "*region",
    c_void_p, "*menu",
    c_void_p, "*gizmo_group",
    c_void_p, "*store",
    c_char_p, "*operator_poll_msg",
)

bContext_data._fields_ = gen_fields(
    c_void_p, "*main",
    c_void_p, "*scene",
    c_int, "recursion",
    c_int, "py_init",
    c_void_p, "py_context",
)

bContext._fields_ = gen_fields(
    c_int, "thread",
    bContext_wm, "wm",
    bContext_data, "data",
)

vec2s._fields_ = gen_fields(
    c_short, "x", "y"
)

ScrVert._fields_ = gen_fields(
    ScrVert, "*next", "*prev", "*newv",
    vec2s, "vec"
)

# ScrArea_Runtime structure definition for Blender 4.x
# Source: /home/myname/blender/blender/source/blender/makesdna/DNA_screen_types.h (lines 423-427)
# Last verified: 2024-06-26
# This structure is embedded in ScrArea, not referenced by pointer
ScrArea_Runtime._fields_ = gen_fields(
    c_void_p, "*tool",           # struct bToolRef *tool;
    c_char, "is_tool_set",       # char is_tool_set;
    c_char, "_pad0[7]",          # char _pad0[7];
)

# ScrArea structure definition for Blender 4.x  
# Source: /home/myname/blender/blender/source/blender/makesdna/DNA_screen_types.h (lines 430-496)
# Last verified: 2024-06-26
# Total size: 184 bytes (was incorrectly calculated as 176 bytes)
# Changes from old version:
# - headertype field marked as DNA_DEPRECATED (but still present)
# - Added regionbase, handlers, actionzones ListBase fields
# - Added ScrArea_Runtime runtime field (16 bytes, not 8-byte pointer)
# - _pad changed from char[2] to char[2] (no change but documented)
# - global field type changed to ScrGlobalAreaData*
# Note: DNA_DEFINE_CXX_METHODS macro is compile-time only, not in runtime struct
ScrArea._fields_ = gen_fields(
    ScrArea, "*next", "*prev",           # struct ScrArea *next, *prev;
    ScrVert, "*v1", "*v2", "*v3", "*v4", # ScrVert *v1, *v2, *v3, *v4;
    c_void_p, "*full",                   # bScreen *full;
    rcti, "totrct",                      # rcti totrct;
    c_char, "spacetype",                 # char spacetype;
    c_char, "butspacetype",              # char butspacetype;
    c_short, "butspacetype_subtype",     # short butspacetype_subtype;
    c_short, "winx", "winy",             # short winx, winy;
    c_char, "headertype",                # char headertype DNA_DEPRECATED;
    c_char, "do_refresh",                # char do_refresh;
    c_short, "flag",                     # short flag;
    c_short, "region_active_win",        # short region_active_win;
    c_char, "_pad[2]",                   # char _pad[2];
    c_void_p, "*type",                   # struct SpaceType *type;
    c_void_p, "*global",                 # ScrGlobalAreaData *global;
    ListBase, "spacedata",               # ListBase spacedata;
    ListBase, "regionbase",              # ListBase regionbase;
    ListBase, "handlers",                # ListBase handlers;
    ListBase, "actionzones",             # ListBase actionzones;
    ScrArea_Runtime, "runtime",          # ScrArea_Runtime runtime;
)

# source/blender/makesdna/DNA_screen_types.h
ScrAreaMap._fields_ = gen_fields(
    ListBase, "vertbase",
    ListBase, "edgebase",
    ListBase, "areabase",
)

# bScreen structure definition for Blender 4.x
# Source: /home/myname/blender/blender/source/blender/makesdna/DNA_screen_types.h (lines 52-107)
# Last verified: 2024-06-26
# Changes from old version:
# - scene field marked as DNA_DEPRECATED (but still present)
# - Added state, do_draw, do_refresh, do_draw_gesture, do_draw_paintcursor, do_draw_drag fields
# - Added skip_handling, scrubbing fields
# - Added _pad[1] padding
# - Added active_region, animtimer, context, tool_tip, preview fields
# Note: C++ constexpr id_type field is compile-time only, not in runtime struct
bScreen._fields_ = gen_fields(
    ID, "id",                            # ID id;
    ListBase, "vertbase",                # ListBase vertbase;
    ListBase, "edgebase",                # ListBase edgebase;
    ListBase, "areabase",                # ListBase areabase;
    ListBase, "regionbase",              # ListBase regionbase;
    c_void_p, "*scene",                  # struct Scene *scene DNA_DEPRECATED;
    c_short, "flag",                     # short flag;
    c_short, "winid",                    # short winid;
    c_short, "redraws_flag",             # short redraws_flag;
    c_char, "temp",                      # char temp;
    c_char, "state",                     # char state;
    c_char, "do_draw",                   # char do_draw;
    c_char, "do_refresh",                # char do_refresh;
    c_char, "do_draw_gesture",           # char do_draw_gesture;
    c_char, "do_draw_paintcursor",       # char do_draw_paintcursor;
    c_char, "do_draw_drag",              # char do_draw_drag;
    c_char, "skip_handling",             # char skip_handling;
    c_char, "scrubbing",                 # char scrubbing;
    c_char, "_pad[1]",                   # char _pad[1];
    c_void_p, "*active_region",          # struct ARegion *active_region;
    c_void_p, "*animtimer",              # struct wmTimer *animtimer;
    c_void_p, "*context",                # void *context;
    c_void_p, "*tool_tip",               # struct wmTooltipState *tool_tip;
    c_void_p, "*preview",                # PreviewImage *preview;
)

'''
wmEvent._fields_ = gen_fields(
    wmEvent, "*next", "*prev",
    c_short, "type",
    c_short, "val",
    c_int, "x", "y",
    c_int, "mval[2]",
    c_char, "utf8_buf[6]",
    c_char, "ascii",
    c_char, "pad",
    c_short, "prevtype",
    c_short, "prevval",
    c_int, "prevx", "prevy",
    c_double, "prevclicktime",
    c_int, "prevclickx", "prevclicky",
    c_short, "shift", "ctrl", "alt", "oskey",
    c_short, "keymodifier",
)
'''

wmWindow._fields_ = gen_fields(
    wmWindow, "*next", "*prev",
    c_void_p, "*ghostwin",
    c_void_p, "*gpuctx",
    wmWindow, "*parent",
    c_void_p, "*scene",
    c_void_p, "*new_scene",
    c_char, "view_layer_name[64]",
    c_void_p, "*workspace_hook",
    ScrAreaMap, "global_areas",
    bScreen, "*screen",
    c_short, "posx", "posy", "sizex", "sizey",
    c_short, "windowstate",
    c_short, "monitor",
    c_short, "active",
    c_short, "cursor",
    c_short, "lastcursor",
    c_short, "modalcursor",
    c_short, "grabcursor",
    c_short, "addmousemove",
    c_short, "pad[4]",
    c_int, "winid",
    c_short, "lock_pie_event",
    c_short, "last_pie_event",
    c_void_p, "*eventstate",
    c_void_p, "*tweak",
    c_void_p, "*ime_data",
    ListBase, "queue",
    ListBase, "handlers",
    ListBase, "modalhandlers",
)

wmEventHandler_KeymapFn._fields_ = gen_fields(
    c_void_p, "*handle_post_fn",
    c_void_p, "*user_data"
)

wmEventHandler._fields_ = gen_fields(
    wmEventHandler, "*next", "*prev",
    c_char, "type",
    c_char, "flag",
    c_void_p, "*keymap",
    c_void_p, "*bblocal", "*bbwin",
    wmEventHandler_KeymapFn, "keymap_callback",
    c_void_p, "*keymap_tool",
    wmOperator, "*op",
)

wmOperator._fields_ = gen_fields(
    wmOperator, "*next", "*prev",
    c_char, "idname[64]",
)

del re_field
del struct
del gen_fields


class HeadModalHandler:
    key: StringProperty(default="ESC", options={'SKIP_SAVE'})

    def finish(self):
        pass

    def modal(self, context, event):
        if event.value == 'RELEASE':
            if event.type == self.key:
                self.finished = True
                return {'PASS_THROUGH'}

        if self.move_flag:
            self.move_flag = False
            if not move_modal_handler(context.window, self):
                self.finished = True

        if event.type != 'TIMER':
            self.move_flag = True
        elif self.finished:
            context.window_manager.event_timer_remove(self.timer)
            self.timer = None
            self.finish()
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        self.move_flag = False
        self.finished = False

        self.timer = context.window_manager.event_timer_add(
            0.001, window=context.window
        )
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        return self.execute(context)


def c_layout(layout):
    ret = cast(layout.as_pointer(), POINTER(uiLayout)).contents
    return ret


# def c_last_btn(clayout):
#     ret = cast(
#         clayout.root.contents.block.contents.buttons.last, POINTER(uiBut)  # see #18
#     ).contents
#     return ret


def c_style(clayout):
    return clayout.root.contents.style.contents


def c_context(context):
    ret = cast(context.as_pointer(), POINTER(bContext)).contents
    return ret


# def c_event(event):
#     ret = cast(event.as_pointer(), POINTER(wmEvent)).contents
#     return ret


def c_window(v):
    return cast(v.as_pointer(), POINTER(wmWindow)).contents


def c_handler(v):
    return cast(v, POINTER(wmEventHandler)).contents


def c_operator(v):
    return cast(v, POINTER(wmOperator)).contents


def c_area(v):
    return cast(v.as_pointer(), POINTER(ScrArea)).contents


def set_area(context, area=None):
    C = c_context(context)
    if area:
        set_area.area = C.wm.area
        C.wm.area = cast(area.as_pointer(), POINTER(ScrArea))

    elif hasattr(set_area, "area"):
        C.wm.area = set_area.area


def set_region(context, region=None):
    C = c_context(context)
    if region:
        set_region.region = C.wm.region
        C.wm.region = cast(region.as_pointer(), POINTER(ARegion))

    elif hasattr(set_region, "region"):
        C.wm.region = set_region.region


def area_rect(area):
    carea = cast(area.as_pointer(), POINTER(ScrArea))
    return carea.contents.totrct


def set_temp_screen(screen):
    cscreen = cast(screen.as_pointer(), POINTER(bScreen))
    cscreen.contents.temp = 1


def is_row(layout):
    clayout = cast(layout.as_pointer(), POINTER(uiLayout))
    croot = cast(clayout, POINTER(uiLayoutRoot))
    return croot.contents.type == 1


def swap_spaces(from_area, to_area, to_area_space_type):
    idx = -1
    for i, s in enumerate(to_area.spaces):
        if s.type == to_area_space_type:
            idx = i
            break
    else:
        return

    from_area_p = c_area(from_area)
    to_area_p = c_area(to_area)

    from_space_a = from_area_p.spacedata.first
    to_space_p = to_area_p.spacedata.find(idx)
    to_space_a = addressof(to_space_p)
    to_prev_space_a = addressof(to_space_p.prev.contents)

    from_area_p.spacedata.remove(from_space_a)
    to_area_p.spacedata.remove(to_space_a)

    from_area_p.spacedata.insert(None, to_space_a)
    to_area_p.spacedata.insert(to_prev_space_a, from_space_a)


def resize_area(area, width, direction='RIGHT'):
    # Clamp incoming sizes to avoid corrupting the screen layout when callers
    # request widths that exceed the window (can happen with custom operators).
    area_p = c_area(area)

    min_size = 32
    window = getattr(bpy.context, "window", None)
    max_size = None

    if window:
        if direction in ('LEFT', 'RIGHT'):
            max_size = max(min_size, int(window.width * 0.95))
        elif direction in ('TOP', 'BOTTOM'):
            max_size = max(min_size, int(window.height * 0.95))

    if max_size is not None:
        width = max(min_size, min(int(width), max_size))
    else:
        width = max(min_size, int(width))

    if direction in ('LEFT', 'RIGHT'):
        dx = width - area.width
        if direction == 'LEFT':
            area_p.v1.contents.vec.x -= dx
            area_p.v2.contents.vec.x -= dx
        elif direction == 'RIGHT':
            area_p.v3.contents.vec.x += dx
            area_p.v4.contents.vec.x += dx
    elif direction in ('TOP', 'BOTTOM'):
        dy = width - area.height
        if direction == 'TOP':
            # Move the top edge (v2, v3)
            area_p.v2.contents.vec.y += dy
            area_p.v3.contents.vec.y += dy
        elif direction == 'BOTTOM':
            # Move the bottom edge (v1, v4)
            area_p.v1.contents.vec.y -= dy
            area_p.v4.contents.vec.y -= dy


def move_modal_handler(window, operator):
    a_operator = operator.as_pointer()
    w = cast(window.as_pointer(), POINTER(wmWindow)).contents
    p_eh = POINTER(wmEventHandler)
    p_op = POINTER(wmOperator)
    p_h_first = cast(w.modalhandlers.first, p_eh)

    if not p_h_first:
        return False

    h_first = h = p_h_first.contents

    p_o = cast(h.op, p_op)
    if p_o:
        o = p_o.contents
        if addressof(o) == a_operator:
            return True

    while h:
        p_o = cast(h.op, p_op)
        if p_o:
            o = p_o.contents
            if addressof(o) == a_operator:
                p_h_prev = cast(h.prev, p_eh)
                p_h_next = cast(h.next, p_eh)
                if p_h_prev:
                    p_h_prev.contents.next = p_h_next
                if p_h_next:
                    p_h_next.contents.prev = p_h_prev
                h.prev = None
                h.next = p_h_first
                w.modalhandlers.first = addressof(h)
                h_first.prev = cast(w.modalhandlers.first, p_eh)
                return True

        h = cast(h.next, p_eh)
        h = h and h.contents

    return False


def keep_pie_open(layout):
    layout_p = c_layout(layout)
    block_p = layout_p.root.contents.block.contents
    block_p.flag |= UI_BLOCK_KEEP_OPEN
    # block_p.dt = UI_EMBOSS


def register():
    pme.context.add_global("keep_pie_open", keep_pie_open)
