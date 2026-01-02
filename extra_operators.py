# extra_operators.py - Backward-compatible wrapper for extra operators
# LAYER = "operators"
#
# NOTE: This file is now a thin wrapper for backward compatibility.
# All operators have been moved to operators/extras/ subpackage.
#
# Phase 2-C operators reorganization:
#   - Sidebar operators -> operators/extras/sidearea.py
#   - Popup operators -> operators/extras/popup.py
#   - Area operators -> operators/extras/area.py
#   - Utility operators -> operators/extras/utils.py

LAYER = "operators"

# Re-export all operators from the new location
from .operators.extras import (
    # Sidearea
    WM_OT_pme_sidebar_toggle,
    PME_OT_sidebar_toggle,
    PME_OT_sidearea_toggle,
    # Popup
    PME_OT_popup_property,
    PME_OT_popup_user_preferences,
    PME_OT_popup_addon_preferences,
    PME_OT_popup_panel,
    PME_OT_select_popup_panel,
    PME_OT_popup_area,
    # Area
    PME_OT_window_auto_close,
    PME_OT_area_move,
    # Utils
    PME_OT_dummy,
    PME_OT_modal_dummy,
    PME_OT_none,
    PME_OT_screen_set,
    PME_OT_clipboard_copy,
)

# Re-export register/unregister from utils module
from .operators.extras.utils import register, unregister

__all__ = [
    # Sidearea
    "WM_OT_pme_sidebar_toggle",
    "PME_OT_sidebar_toggle",
    "PME_OT_sidearea_toggle",
    # Popup
    "PME_OT_popup_property",
    "PME_OT_popup_user_preferences",
    "PME_OT_popup_addon_preferences",
    "PME_OT_popup_panel",
    "PME_OT_select_popup_panel",
    "PME_OT_popup_area",
    # Area
    "PME_OT_window_auto_close",
    "PME_OT_area_move",
    # Utils
    "PME_OT_dummy",
    "PME_OT_modal_dummy",
    "PME_OT_none",
    "PME_OT_screen_set",
    "PME_OT_clipboard_copy",
    # Functions
    "register",
    "unregister",
]
