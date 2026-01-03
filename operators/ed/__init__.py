# operators/ed/ - Editor-related operators
# LAYER = "operators"
#
# This subpackage contains operators that were previously in editors/base.py.
# They are organized by functionality for better maintainability.
#
# Phase 5-A operator separation (Issue #74)

LAYER = "operators"

# Tags operators
from .tags import (
    PME_OT_tags_filter,
    PME_OT_tags,
)

# Icon operators
from .icon import (
    WM_OT_pmi_icon_tag_toggle,
    WM_OT_pmi_icon_select,
)

# PMI (Pie Menu Item) operators
from .pmi import (
    WM_OT_pmi_type_select,
    WM_OT_pmi_edit,
    WM_OT_pmi_edit_clipboard,
    WM_OT_pmi_edit_auto,
    PME_OT_pmi_menu,
    PME_OT_pmi_add,
    PME_OT_pmi_move,
    PME_OT_pmi_remove,
    PME_OT_pmi_clear,
    PME_OT_pmi_cmd_generate,
    WM_OT_pmi_data_edit,
    PME_OT_pmi_copy,
    PME_OT_pmi_paste,
)

# PM (Pie Menu) operators
from .pm import (
    PME_MT_select_menu,
    PME_MT_pm_new,
    PME_OT_pm_add,
    PME_OT_pm_edit,
    PME_OT_pm_toggle,
    PME_OT_pmi_toggle,
)

# Poll operators
from .poll import (
    PME_MT_poll_mesh,
    PME_MT_poll_object,
    PME_MT_poll_workspace,
    PME_OT_poll_specials_call,
)

# Settings menus
from .settings import (
    PME_MT_header_menu_set,
    PME_MT_screen_set,
    PME_MT_brush_set,
)

# Keymap operators
from .keymap import (
    PME_OT_keymap_add,
    PME_OT_pm_open_mode_select,
    PME_OT_pm_hotkey_convert,
)

__all__ = [
    # Tags
    "PME_OT_tags_filter",
    "PME_OT_tags",
    # Icon
    "WM_OT_pmi_icon_tag_toggle",
    "WM_OT_pmi_icon_select",
    # PMI
    "WM_OT_pmi_type_select",
    "WM_OT_pmi_edit",
    "WM_OT_pmi_edit_clipboard",
    "WM_OT_pmi_edit_auto",
    "PME_OT_pmi_menu",
    "PME_OT_pmi_add",
    "PME_OT_pmi_move",
    "PME_OT_pmi_remove",
    "PME_OT_pmi_clear",
    "PME_OT_pmi_cmd_generate",
    "WM_OT_pmi_data_edit",
    "PME_OT_pmi_copy",
    "PME_OT_pmi_paste",
    # PM
    "PME_MT_select_menu",
    "PME_MT_pm_new",
    "PME_OT_pm_add",
    "PME_OT_pm_edit",
    "PME_OT_pm_toggle",
    "PME_OT_pmi_toggle",
    # Poll
    "PME_MT_poll_mesh",
    "PME_MT_poll_object",
    "PME_MT_poll_workspace",
    "PME_OT_poll_specials_call",
    # Settings
    "PME_MT_header_menu_set",
    "PME_MT_screen_set",
    "PME_MT_brush_set",
    # Keymap
    "PME_OT_keymap_add",
    "PME_OT_pm_open_mode_select",
    "PME_OT_pm_hotkey_convert",
]
