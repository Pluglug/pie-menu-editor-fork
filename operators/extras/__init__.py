# operators/extras/__init__.py - Extra operators package
# LAYER = "operators"
#
# Extra utility operators moved from extra_operators.py (Phase 2-C)
#
# Submodules:
#   - sidearea: Sidebar and SideArea toggle operators
#   - popup: Popup operators (property, preferences, panel, area)
#   - area: Window/Area management operators
#   - utils: Utility operators (dummy, none, clipboard, screen_set)
#

LAYER = "operators"

from .sidearea import (
    WM_OT_pme_sidebar_toggle,
    PME_OT_sidebar_toggle,
    PME_OT_sidearea_toggle,
)

from .popup import (
    PME_OT_popup_property,
    PME_OT_popup_user_preferences,
    PME_OT_popup_addon_preferences,
    PME_OT_popup_panel,
    PME_OT_select_popup_panel,
    PME_OT_popup_area,
)

from .area import (
    PME_OT_window_auto_close,
    PME_OT_area_move,
)

from .utils import (
    PME_OT_dummy,
    PME_OT_modal_dummy,
    PME_OT_none,
    PME_OT_screen_set,
    PME_OT_clipboard_copy,
)

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
]
