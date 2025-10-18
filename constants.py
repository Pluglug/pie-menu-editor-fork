import bpy
import re
from .addon import ic
from .previews_helper import ph

MAX_STR_LEN = 1024
UNTAGGED = "Untagged"
TREE_SPLITTER = '→'
KEYMAP_SPLITTER = ';'
TREE_ROOT = "root"
F_ICON_ONLY = "#"
F_HIDDEN = "!"
F_CB = "^"
F_EXPAND = "@"
F_CUSTOM_ICON = "@"
F_RIGHT = "_right"
F_PRE = "_pre"
PMIF_DISABLED = 1
PANEL_FILE = "sub"
PANEL_FOLDER = ""
BL_TIMER_STEP = 0.01

PME_TEMP_SCREEN = "PME Temp "
PME_SCREEN = "PME "

POPUP_PADDING = 10
WINDOW_MARGIN = 32
WINDOW_MIN_WIDTH = 320
WINDOW_MIN_HEIGHT = 240


ED_DATA = (
    ('PMENU', "Pie Menu", 'MOD_SUBSURF'),
    ('RMENU', "Regular Menu", 'MOD_BOOLEAN'),
    ('DIALOG', "Popup Dialog", 'MOD_BUILD'),
    ('SCRIPT', "Stack Key", 'MOD_MIRROR'),
    ('PANEL', "Panel Group", 'MOD_MULTIRES'),
    ('HPANEL', "Hidden Panel Group", 'MOD_TRIANGULATE'),
    ('STICKY', "Sticky Key", 'MOD_WARP'),
    ('MACRO', "Macro Operator", 'MOD_ARRAY'),
    ('MODAL', "Modal Operator", 'MOD_BEVEL'),
    ('PROPERTY', "Property", 'MOD_SCREW'),
)

EMODE_ITEMS = [
    (
        'COMMAND',
        "Command",
        "Python code that will be executed when the user clicks the button",
    ),
    (
        'PROP',
        "Property",
        "Path to the object's property which will be displayed as a widget",
    ),
    (
        'MENU',
        "Menu",
        "Open/execute the menu, popup or operator\n"
        "  when the user clicks the button\n"
        "Or draw a popup dialog inside the current popup dialog or pie menu",
    ),
    (
        'HOTKEY',
        "Hotkey",
        "Blender's hotkey that will be used "
        "to find and execute the operator assigned to it\n"
        "  when the user clicks the button",
    ),
    (
        'CUSTOM',
        "Custom",
        "Python code that will be used to draw custom layout of widgets",
    ),
    (
        'INVOKE',
        "On Invoke",
        "Python code that will be executed\n"
        "  when the user invokes the modal operator",
    ),
    (
        'FINISH',
        "On Confirm",
        "Python code that will be executed\n"
        "  when the user confirms the modal operator",
    ),
    (
        'CANCEL',
        "On Cancel",
        "Python code that will be executed\n"
        "  when the user cancels the modal operator",
    ),
    (
        'UPDATE',
        "On Update",
        "Python code that will be executed\n"
        "  when the user interacts with the modal operator",
    ),
]
MODE_ITEMS = [('EMPTY', "Empty", "Don't use the item")]
MODE_ITEMS.extend(EMODE_ITEMS)

PD_MODE_ITEMS = (
    ('PIE', 'Pie Mode', ""),
    ('PANEL', 'Dialog Mode', ""),
    ('POPUP', 'Popup Mode', ""),
)

MODAL_CMD_MODES = {
    EMODE_ITEMS[0][0],
    EMODE_ITEMS[5][0],
    EMODE_ITEMS[6][0],
    EMODE_ITEMS[7][0],
    EMODE_ITEMS[8][0],
}

PM_ITEMS = tuple((id, name, "", icon, i) for i, (id, name, icon) in enumerate(ED_DATA))

PM_ITEMS_M = tuple(
    (id, name, "", icon, 1 << i) for i, (id, name, icon) in enumerate(ED_DATA)
)

PM_ITEMS_M_DEFAULT = set(id for id, name, icon in ED_DATA)

SETTINGS_TAB_ITEMS = (
    ('GENERAL', "General", ""),
    ('HOTKEYS', "Hotkeys", ""),
    ('OVERLAY', "Overlay", ""),
    ('PIE', "Pie Menu", ""),
    ('MENU', "Regular Menu", ""),
    ('POPUP', "Popup Dialog", ""),
    ('MODAL', "Modal Operator", ""),
)

SETTINGS_TAB_DEFAULT = SETTINGS_TAB_ITEMS[0][0]
# SETTINGS_TAB_DEFAULT = set(id for id, name, icon in SETTINGS_TAB_ITEMS)

OP_CTX_ITEMS = (
    ('INVOKE_DEFAULT', "Invoke (Default)", "", 'OUTLINER_OB_LAMP', 0),
    ('INVOKE_REGION_WIN', "Invoke Window Region", "", 'OUTLINER_OB_LAMP', 1),
    ('INVOKE_REGION_CHANNELS', "Invoke Channels Region", "", 'OUTLINER_OB_LAMP', 2),
    ('INVOKE_REGION_PREVIEW', "Invoke Preview Region", "", 'OUTLINER_OB_LAMP', 3),
    ('INVOKE_AREA', "Invoke Area", "", 'OUTLINER_OB_LAMP', 4),
    ('INVOKE_SCREEN', "Invoke Screen", "", 'OUTLINER_OB_LAMP', 5),
    ('EXEC_DEFAULT', "Exec", "", 'LAMP_DATA', 6),
    ('EXEC_REGION_WIN', "Exec Window Region", "", 'LAMP_DATA', 7),
    ('EXEC_REGION_CHANNELS', "Exec Channels Region", "", 'LAMP_DATA', 8),
    ('EXEC_REGION_PREVIEW', "Exec Preview Region", "", 'LAMP_DATA', 9),
    ('EXEC_AREA', "Exec Area", "", 'LAMP_DATA', 10),
    ('EXEC_SCREEN', "Exec Screen", "", 'LAMP_DATA', 11),
)

ICON_ON = 'CHECKBOX_HLT'
ICON_OFF = 'CHECKBOX_DEHLT'

BL_ICONS = {
    item.identifier for item in bpy.types.Property.bl_rna.properties['icon'].enum_items
}

DEFAULT_POLL = "return True"

LIST_PADDING = 0.5
SCALE_X = 1.5
SEPARATOR_SCALE_Y = 11 / 18
SPACER_SCALE_Y = 0.3

I_CLIPBOARD = "Clipboard is empty"
I_CMD = "Bad command"
I_DEBUG = "Debug mode: %s"
I_NO_ERRORS = "No errors were found"
I_MODAL_PROP_MOVE = "Mouse Move mode blocks all Command and Property hotkeys"
W_CMD = "PME: Bad command: %s"
W_FILE = "PME: Bad file"
W_JSON = "PME: Bad json"
W_KEY = "PME: Bad key: %s"
W_PM = "Menu '%s' was not found"
W_PROP = "PME: Bad property: %s"
W_PMI_HOTKEY = "Hotkey is not specified"
W_PMI_EXPR = "Invalid expression"
W_PMI_SYNTAX = "Invalid syntax"
W_PMI_MENU = "Select the item"
W_PMI_ADD_BTN = "Can't add this button"
W_PMI_LONG_CMD = "The command is too long"


ARROW_ICONS = ("@p4", "@p6", "@p2", "@p8", "@p7", "@p9", "@p1", "@p3", "@pA", "@pB")

SPACE_ITEMS = (
    ('VIEW_3D', "3D Viewport", "", 'VIEW3D', 0),
    ('DOPESHEET_EDITOR', "Dope Sheet", "", 'ACTION', 1),
    ('FILE_BROWSER', "File Browser", "", 'FILEBROWSER', 2),
    ('GRAPH_EDITOR', "Graph Editor/Drivers", "", 'GRAPH', 3),
    ('INFO', "Info", "", 'INFO', 4),
    ('LOGIC_EDITOR', "Logic Editor", "", 'ERROR', 5),
    ('CLIP_EDITOR', "Movie Clip Editor", "", 'TRACKER', 6),
    ('NLA_EDITOR', "NLA Editor", "", 'NLA', 7),
    ('NODE_EDITOR', "Node Editor", "", 'NODETREE', 8),
    ('OUTLINER', "Outliner", "", 'OUTLINER', 9),
    ('PROPERTIES', "Properties", "", 'PROPERTIES', 10),
    ('CONSOLE', "Python Console", "", 'CONSOLE', 11),
    ('TEXT_EDITOR', "Text Editor", "", 'TEXT', 12),
    ('TIMELINE', "Timeline", "", 'TIME', 13),
    ('PREFERENCES', "Preferences", "", 'PREFERENCES', 14),
    ('IMAGE_EDITOR', "Image/UV Editor", "", 'IMAGE', 15),
    ('SEQUENCE_EDITOR', "Video Sequencer", "", 'SEQUENCE', 16),
    ('SPREADSHEET', "Spreadsheet", "", 'SPREADSHEET', 17),
    ('TOPBAR', "Top Bar", "", 'TRIA_UP_BAR', 18),
    ('STATUSBAR', "Status Bar", "", 'TRIA_DOWN_BAR', 19),
)

REGION_ITEMS = (
    ('TOOLS', "Tools (Side Panel)", "T-panel", 'TRIA_LEFT_BAR', 0),
    ('UI', "UI (Side Panel)", "N-panel", 'TRIA_RIGHT_BAR', 1),
    ('WINDOW', "Window", "Center Area", 'MESH_PLANE', 2),
    ('HEADER', "Header", "Top or bottom bar", 'TRIA_DOWN_BAR', 3),
)

OPEN_MODE_ITEMS = (
    ('PRESS', "Press", "Press the key", ph.get_icon("pPress"), 0),
    ('HOLD', "Hold", "Hold down the key", ph.get_icon("pHold"), 1),
    ('DOUBLE_CLICK', "Double Click", "Double click the key", ph.get_icon("pDouble"), 2),
    (
        'TWEAK',
        "Click Drag",
        "Hold down the key and move the mouse",
        ph.get_icon("pTweak"),
        3,
    ),
    ('CHORDS', "Key Chords", "Click sequence of 2 keys", ph.get_icon("pChord"), 4),
    ('CLICK', "Click (Experimental)", "Click the key", ph.get_icon("pClick"), 5),
    ('CLICK_DRAG', "Click Drag (Experimental)", "Click and drag the key", ph.get_icon("pDrag"), 6),
)


DRAG_DIR_ITEMS = (
    ('ANY', "Any", "Any direction", '', 0),
    ('NORTH', "N", "North", '', 1),
    ('NORTH_EAST', "NE", "North-East", '', 2),
    ('EAST', "E", "East", '', 3),
    ('SOUTH_EAST', "SE", "South-East", '', 4),
    ('SOUTH', "S", "South", '', 5),
    ('SOUTH_WEST', "SW", "South-West", '', 6),
    ('WEST', "W", "West", '', 7),
    ('NORTH_WEST', "NW", "North-West", '', 8),
)


def header_action_enum_items():
    yield ('DEFAULT', "Default", "", '', 0)
    yield ('TOP', "Top", "", '', 1)
    yield ('BOTTOM', "Bottom", "", '', 2)
    yield ('TOP_HIDE', "Top Hidden", "", '', 3)
    yield ('BOTTOM_HIDE', "Bottom Hidden", "", '', 4)


# class EnumItems:
#     def __init__(self):
#         self._items = []

#     def add_item(self, id, name, icon, desc=""):
#         self._items.append((id, name, desc, ic(icon), len(self._items)))

#     def retrieve_items(self):
#         if self._items is None:
#             raise ValueError("Items are already retrieved")

#         ret = self._items
#         self._items = None

#         return ret


# def area_type_enum_items(current=True, none=False):
#     ei = EnumItems()

#     if current:
#         ei.add_item('CURRENT', "Current", 'BLENDER')

#     if none:
#         ei.add_item('NONE', "None", 'HANDLETYPE_FREE_VEC')

#     ei.add_item('VIEW_3D', "3D View", 'VIEW3D')
#     ei.add_item('TIMELINE', "Timeline", 'TIME')
#     ei.add_item('FCURVES', "Graph Editor", 'GRAPH')
#     ei.add_item('DRIVERS', "Drivers", 'DRIVER')
#     ei.add_item('DOPESHEET', "Dope Sheet", 'ACTION')
#     ei.add_item('NLA_EDITOR', "NLA Editor", 'NLA')
#     ei.add_item('VIEW', "Image Editor", 'IMAGE')
#     ei.add_item('UV', "UV Editor", 'UV')
#     ei.add_item('CLIP_EDITOR', "Movie Clip Editor", 'TRACKER')
#     ei.add_item('SEQUENCE_EDITOR', "Video Sequence Editor", 'SEQUENCE')
#     ei.add_item('ShaderNodeTree', "Shader Editor", 'NODE_MATERIAL')
#     ei.add_item('CompositorNodeTree', "Compositing", 'NODE_COMPOSITING')
#     ei.add_item('TextureNodeTree', "Texture Node Editor", 'NODE_TEXTURE')
#     ei.add_item('GeometryNodeTree', "Geometry Node Editor", 'NODETREE')
#     ei.add_item('TEXT_EDITOR', "Text Editor", 'TEXT')
#     ei.add_item('PROPERTIES', "Properties", 'PROPERTIES')
#     ei.add_item('OUTLINER', "Outliner", 'OUTLINER')
#     ei.add_item('PREFERENCES', "Preferences", 'PREFERENCES')
#     ei.add_item('INFO', "Info", 'INFO')
#     ei.add_item('FILE_BROWSER', "File Browser", 'FILEBROWSER')
#     ei.add_item('ASSETS', "Asset Browser", 'ASSET_MANAGER')
#     ei.add_item('SPREADSHEET', "Spreadsheet", 'SPREADSHEET')
#     ei.add_item('CONSOLE', "Python Console", 'CONSOLE')

#     return ei.retrieve_items()


class AreaEnumHelper:
    """Area type enum generator for Blender EnumProperty (uses dynamic detection + caching)."""

    _cache = {}

    @staticmethod
    def _build_dynamic_items(current=True, none=False):
        """Build area type enum items from Blender's runtime (no cache)."""
        items = []

        if current:
            items.append(('CURRENT', 'Current', '', ic('BLENDER'), len(items)))
        if none:
            items.append(('NONE', 'None', '', ic('HANDLETYPE_FREE_VEC'), len(items)))

        # Get available area types by triggering TypeError with invalid value
        enums = []
        area = None
        try:
            wm = bpy.context.window_manager
            if wm and wm.windows:
                wnd = wm.windows[0]
                if wnd and wnd.screen and wnd.screen.areas:
                    area = wnd.screen.areas[0]
                    try:
                        area.ui_type = ''  # Intentionally trigger TypeError
                    except TypeError as e:
                        # Parse enum options from error message: "not found in ('VIEW_3D', 'UV', ...)"
                        m = re.search(r"not found in \((.*)\)", str(e))
                        if m:
                            enums = [s.strip("'") for s in m.group(1).split(', ')]
        except (AttributeError, RuntimeError):
            # AttributeError: context/window_manager not available
            # RuntimeError: Blender context issues
            return None

        if not area or not enums:
            return None

        # Build enum items with proper names, descriptions, and icons
        for enum_id in enums:
            try:
                name = bpy.types.UILayout.enum_item_name(area, 'ui_type', enum_id)
                desc = bpy.types.UILayout.enum_item_description(area, 'ui_type', enum_id)
                icon_val = bpy.types.UILayout.enum_item_icon(area, 'ui_type', enum_id)
                items.append((enum_id, name, desc, icon_val, len(items)))
            except (AttributeError, RuntimeError):
                # Fallback if UILayout methods fail
                items.append((enum_id, enum_id, '', ic('INFO'), len(items)))

        return tuple(items)

    @classmethod
    def _get_items(cls, with_current: bool, with_none: bool):
        """Get area type enum items with caching."""
        key = (with_current, with_none)
        if key in cls._cache:
            return cls._cache[key]

        items = cls._build_dynamic_items(current=with_current, none=with_none)
        if items:
            cls._cache[key] = items
            return items

        # Dynamic generation failed; return empty fallback
        return ()

    @staticmethod
    def gen_items(self=None, context=None): # pylint: disable=unused-argument, bad-staticmethod-argument
        """EnumProperty callback: area types only."""
        return AreaEnumHelper._get_items(with_current=False, with_none=False)

    @staticmethod
    def gen_items_with_current(self=None, context=None): # pylint: disable=unused-argument, bad-staticmethod-argument
        """EnumProperty callback: area types + 'CURRENT'."""
        return AreaEnumHelper._get_items(with_current=True, with_none=False)

    @staticmethod
    def gen_items_with_none(self=None, context=None): # pylint: disable=unused-argument, bad-staticmethod-argument
        """EnumProperty callback: area types + 'NONE'."""
        return AreaEnumHelper._get_items(with_current=False, with_none=True)
