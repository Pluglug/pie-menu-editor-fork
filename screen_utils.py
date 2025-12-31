# screen_utils.py - DEPRECATED: Thin wrapper for backward compatibility
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: ui/screen.py
#
# Existing imports like `from .screen_utils import find_area` will continue to work.

from .ui.screen import (
    # Functions
    redraw_screen,
    toggle_header,
    move_header,
    find_area,
    find_region,
    find_window,
    find_screen,
    get_override_args,
    focus_area,
    override_context,
    toggle_sidebar,
    exec_with_override,
    # Classes
    ContextOverride,
    # Lifecycle
    register,
)

# Re-export everything for `from .screen_utils import *`
__all__ = [
    "redraw_screen",
    "toggle_header",
    "move_header",
    "find_area",
    "find_region",
    "find_window",
    "find_screen",
    "get_override_args",
    "focus_area",
    "override_context",
    "toggle_sidebar",
    "exec_with_override",
    "ContextOverride",
    "register",
]
