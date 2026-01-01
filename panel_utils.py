# panel_utils.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "ui"  (for layer violation detection)
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: ui/panels.py
#
# Existing imports like `from .panel_utils import panel` will continue to work.

LAYER = "ui"

from .ui.panels import (
    # Functions
    panel_types_sorter,
    panel_type_names_sorter,
    hide_panel,
    unhide_panel,
    unhide_panels,
    hidden_panel,
    is_panel_hidden,
    get_hidden_panels,
    bar_panel_poll,
    to_valid_name,
    gen_panel_tp_name,
    add_panel_group,
    add_panel,
    remove_panel,
    remove_panel_group,
    refresh_panel_group,
    rename_panel_group,
    move_panel,
    panel_context_items,
    bl_header_types,
    bl_menu_types,
    bl_panel_types,
    bl_panel_enum_items,
    panel_type,
    panel_label,
    panel,
    draw_callback_view,
    draw_callback_props,
    register,
    unregister,
    # Classes
    PME_OT_panel_toggle,
    PME_OT_panel_reset,
    PME_OT_panel_editor_toggle,
    PME_OT_btn_hide,
    PLayout,
    PME_OT_popup_panel_menu,
)

# Re-export everything for `from .panel_utils import *`
__all__ = [
    "panel_types_sorter",
    "panel_type_names_sorter",
    "hide_panel",
    "unhide_panel",
    "unhide_panels",
    "hidden_panel",
    "is_panel_hidden",
    "get_hidden_panels",
    "bar_panel_poll",
    "to_valid_name",
    "gen_panel_tp_name",
    "add_panel_group",
    "add_panel",
    "remove_panel",
    "remove_panel_group",
    "refresh_panel_group",
    "rename_panel_group",
    "move_panel",
    "panel_context_items",
    "bl_header_types",
    "bl_menu_types",
    "bl_panel_types",
    "bl_panel_enum_items",
    "panel_type",
    "panel_label",
    "panel",
    "draw_callback_view",
    "draw_callback_props",
    "register",
    "unregister",
    "PME_OT_panel_toggle",
    "PME_OT_panel_reset",
    "PME_OT_panel_editor_toggle",
    "PME_OT_btn_hide",
    "PLayout",
    "PME_OT_popup_panel_menu",
]
