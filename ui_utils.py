# ui_utils.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "ui"  (for layer violation detection)
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: ui/utils.py
#
# Existing imports like `from .ui_utils import draw_menu` will continue to work.

LAYER = "ui"

from .ui.utils import (
    # Classes
    WM_MT_pme,
    # Module-level variables
    pme_menu_classes,
    # Functions
    get_pme_menu_class,
    accordion,
    header_menu,
    execute_script,
    draw_menu,
    open_menu,
    toggle_menu,
    register,
    unregister,
)

# Re-export everything for `from .ui_utils import *`
__all__ = [
    "WM_MT_pme",
    "pme_menu_classes",
    "get_pme_menu_class",
    "accordion",
    "header_menu",
    "execute_script",
    "draw_menu",
    "open_menu",
    "toggle_menu",
    "register",
    "unregister",
]
