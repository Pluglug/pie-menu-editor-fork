# pyright: reportInvalidTypeForm=false
"""
UILayout Compatibility Stubs for GPULayout

Provides stub methods for bpy.types.UILayout API compatibility.
These methods log warnings and provide sensible fallbacks.

Usage:
    class GPULayout(UILayoutStubMixin):
        ...

See: _docs/design/gpu_uilayout_compatibility_matrix.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple

from ...infra.debug import DBG_GPU, logi

if TYPE_CHECKING:
    from .layout import GPULayout


# -----------------------------------------------------------------------------
# Dummy OperatorProperties for UILayout.operator() compatibility
# -----------------------------------------------------------------------------

class OperatorProperties:
    """
    Dummy OperatorProperties for UILayout.operator() compatibility.

    Accepts any attribute assignment (op.foo = value) and stores them
    internally. This allows PME scripts using the typical pattern:
        op = layout.operator("mesh.primitive_cube_add")
        op.size = 2.0
    to work without AttributeError.

    Note:
        These properties are stored but not actually used by GPULayout.
        For real operator execution, use on_click callback instead.
    """

    def __init__(self, bl_idname: str = ""):
        # Use object.__setattr__ to avoid triggering our custom __setattr__
        object.__setattr__(self, "_props", {})
        object.__setattr__(self, "_bl_idname", bl_idname)

    def __setattr__(self, name: str, value: Any) -> None:
        """Accept any attribute assignment."""
        self._props[name] = value

    def __getattr__(self, name: str) -> Any:
        """Return stored property or None."""
        props = object.__getattribute__(self, "_props")
        if name in props:
            return props[name]
        # Return None for undefined properties (like Blender does)
        return None

    def __repr__(self) -> str:
        bl_idname = object.__getattribute__(self, "_bl_idname")
        props = object.__getattribute__(self, "_props")
        return f"<OperatorProperties({bl_idname}) {props}>"


# -----------------------------------------------------------------------------
# Dummy Layout for panel() body=None emulation
# -----------------------------------------------------------------------------

class NullLayout:
    """
    Dummy layout that discards all operations.

    Used when panel() returns body=None (collapsed state).
    Any method call on this layout is silently ignored.
    """

    def __getattr__(self, name: str) -> Any:
        """Return a no-op function for any method call."""
        return self._noop

    def _noop(self, *args, **kwargs) -> "NullLayout":
        """No-op that returns self for method chaining."""
        return self


# Singleton instance
_null_layout = NullLayout()


# -----------------------------------------------------------------------------
# UILayoutStubMixin
# -----------------------------------------------------------------------------

class UILayoutStubMixin:
    """
    Mixin class providing UILayout API compatibility stubs.

    All stub methods use *args, **kwargs to accept any signature,
    log a warning, and provide a sensible fallback.
    """

    # These will be available from the inheriting GPULayout class
    if TYPE_CHECKING:
        def label(self, *, text: str = "", icon: str = "NONE") -> None: ...
        def row(self, align: bool = False) -> "GPULayout": ...
        def column(self, align: bool = False) -> "GPULayout": ...
        def prop(self, data: Any, property: str, **kwargs) -> Any: ...
        def color(self, **kwargs) -> Any: ...

    # -------------------------------------------------------------------------
    # Warning utility
    # -------------------------------------------------------------------------

    def _stub_warn(self, method_name: str) -> None:
        """Log warning for unimplemented UILayout method."""
        if DBG_GPU:
            logi(f"[GPULayout] '{method_name}' not implemented (stub)")

    # -------------------------------------------------------------------------
    # Layout Container Stubs
    # -------------------------------------------------------------------------

    def grid_flow(self, *args, **kwargs) -> "GPULayout":
        """
        Stub: grid_flow() -> column() fallback.

        Creates a grid-based layout. Falls back to column() since
        GPU layout doesn't support grid flow.
        """
        self._stub_warn("grid_flow")
        return self.column(align=kwargs.get("align", False))

    def column_flow(self, *args, **kwargs) -> "GPULayout":
        """
        Stub: column_flow() -> column() fallback.

        Creates a multi-column flow layout. Falls back to single column.
        """
        self._stub_warn("column_flow")
        return self.column(align=kwargs.get("align", False))

    def menu_pie(self, *args, **kwargs) -> "GPULayout":
        """Stub: menu_pie() - not applicable for GPU panels."""
        self._stub_warn("menu_pie")
        return self

    def panel(self, idname: str, *args, **kwargs) -> Tuple[Any, Optional[Any]]:
        """
        Stub: panel() - collapsible panel.

        Args:
            idname: Panel identifier
            default_closed: If True, panel starts collapsed (body=None)
            **kwargs: Other UILayout.panel() parameters

        Returns:
            (header_layout, body_layout) where body is None if collapsed.

        Note:
            When body is None, callers typically skip drawing panel contents:
                header, body = layout.panel("MY_PT_panel", default_closed=True)
                header.label(text="Panel Title")
                if body:
                    body.label(text="Panel Contents")

            GPULayout respects default_closed by returning NullLayout
            (a no-op layout) instead of None, so code that doesn't check
            for None won't crash.
        """
        self._stub_warn("panel")
        default_closed = kwargs.get("default_closed", False)
        header = self.row()
        if default_closed:
            # Return NullLayout which silently discards all operations
            return (header, _null_layout)
        return (header, self)

    def panel_prop(self, data: Any, property: str, *args, **kwargs) -> Tuple[Any, Optional[Any]]:
        """
        Stub: panel_prop() - data-driven collapsible panel.

        Args:
            data: Object containing the boolean property
            property: Name of the boolean property controlling open/closed state
            **kwargs: Other UILayout.panel_prop() parameters

        Returns:
            (header_layout, body_layout) where body is NullLayout if collapsed.

        Note:
            Reads the property value to determine collapsed state.
            If property is False, body is NullLayout (collapsed).
        """
        self._stub_warn("panel_prop")
        # Try to read the property to determine state
        is_open = True
        try:
            is_open = bool(getattr(data, property, True))
        except Exception:
            pass

        header = self.row()
        if not is_open:
            return (header, _null_layout)
        return (header, self)

    # -------------------------------------------------------------------------
    # Display Stubs
    # -------------------------------------------------------------------------

    def progress(self, *args, **kwargs) -> None:
        """Stub: progress() → label with percentage."""
        self._stub_warn("progress")
        text = kwargs.get("text", "")
        factor = kwargs.get("factor", 0.0)
        pct = int(factor * 100)
        display = f"{text} {pct}%" if text else f"{pct}%"
        self.label(text=display)

    # -------------------------------------------------------------------------
    # Operator Stubs
    # -------------------------------------------------------------------------

    def operator_enum(self, operator: str, property: str, *args, **kwargs) -> OperatorProperties:
        """
        Stub: operator_enum() - enum expansion for operators.

        Returns OperatorProperties so callers can set additional properties.
        """
        self._stub_warn("operator_enum")
        self.label(text=f"[op_enum: {operator}]")
        return OperatorProperties(operator)

    def operator_menu_enum(self, operator: str, property: str, *args, **kwargs) -> OperatorProperties:
        """
        Stub: operator_menu_enum() - enum menu for operators.

        Returns OperatorProperties so callers can set additional properties.
        """
        self._stub_warn("operator_menu_enum")
        text = kwargs.get("text", "") or f"[{operator}]"
        icon = kwargs.get("icon", "NONE")
        self.label(text=text, icon=icon)
        return OperatorProperties(operator)

    def operator_menu_hold(self, operator: str, *args, **kwargs) -> OperatorProperties:
        """
        Stub: operator_menu_hold() - hold menu for operators.

        Returns OperatorProperties so callers can set additional properties.
        """
        self._stub_warn("operator_menu_hold")
        text = kwargs.get("text", "") or f"[{operator}]"
        icon = kwargs.get("icon", "NONE")
        self.label(text=text, icon=icon)
        return OperatorProperties(operator)

    # -------------------------------------------------------------------------
    # Property Stubs
    # -------------------------------------------------------------------------

    def props_enum(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: props_enum() → label fallback."""
        self._stub_warn("props_enum")
        try:
            value = getattr(data, property, "?")
            self.label(text=f"{property}: {value}")
        except Exception:
            self.label(text=f"[props_enum: {property}]")

    def prop_menu_enum(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: prop_menu_enum() → label fallback."""
        self._stub_warn("prop_menu_enum")
        try:
            value = getattr(data, property, "?")
            text = kwargs.get("text", "") or property
            icon = kwargs.get("icon", "NONE")
            self.label(text=f"{text}: {value}", icon=icon)
        except Exception:
            self.label(text=f"[prop_menu_enum: {property}]")

    def prop_tabs_enum(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: prop_tabs_enum() → prop(expand=True) fallback."""
        self._stub_warn("prop_tabs_enum")
        self.prop(data, property, expand=True)

    def prop_search(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: prop_search() → label fallback."""
        self._stub_warn("prop_search")
        try:
            value = getattr(data, property, "")
            text = kwargs.get("text", "") or property
            self.label(text=f"{text}: {value}", icon="VIEWZOOM")
        except Exception:
            self.label(text=f"[prop_search: {property}]", icon="VIEWZOOM")

    def prop_decorator(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: prop_decorator() - no visual output (animation dot)."""
        self._stub_warn("prop_decorator")
        # No fallback - decorators are optional visual elements

    def prop_with_popover(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: prop_with_popover() → prop() fallback."""
        self._stub_warn("prop_with_popover")
        text = kwargs.get("text", "")
        icon = kwargs.get("icon", "NONE")
        self.prop(data, property, text=text, icon=icon)

    def prop_with_menu(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: prop_with_menu() → prop() fallback."""
        self._stub_warn("prop_with_menu")
        text = kwargs.get("text", "")
        icon = kwargs.get("icon", "NONE")
        self.prop(data, property, text=text, icon=icon)

    # -------------------------------------------------------------------------
    # Menu Stubs
    # -------------------------------------------------------------------------

    def menu(self, menu: str, *args, **kwargs) -> None:
        """
        Stub: menu() - dropdown menu.

        Args:
            menu: Menu class name (bl_idname)
            text: Button text (default: menu name)
            icon: Icon name (e.g., "DOWNARROW_HLT")
            icon_value: Custom icon ID (currently logged but not displayed)
            **kwargs: Other UILayout.menu() parameters

        Note:
            icon_value is accepted for compatibility but custom icons
            are not rendered in GPU layout.
        """
        self._stub_warn("menu")
        text = kwargs.get("text", "") or f"[Menu: {menu}]"
        icon = kwargs.get("icon", "") or "DOWNARROW_HLT"
        icon_value = kwargs.get("icon_value", 0)
        if icon_value and DBG_GPU:
            logi(f"[GPULayout] menu() icon_value={icon_value} ignored")
        self.label(text=text, icon=icon)

    def menu_contents(self, menu: str, *args, **kwargs) -> None:
        """Stub: menu_contents() - inline menu contents."""
        self._stub_warn("menu_contents")
        self.label(text=f"[menu_contents: {menu}]")

    def popover(self, panel: str, *args, **kwargs) -> None:
        """
        Stub: popover() - popover panel.

        Args:
            panel: Panel class name (bl_idname)
            text: Button text (default: panel name)
            icon: Icon name (e.g., "DOWNARROW_HLT")
            icon_value: Custom icon ID (currently logged but not displayed)
            **kwargs: Other UILayout.popover() parameters

        Note:
            icon_value is accepted for compatibility but custom icons
            are not rendered in GPU layout.
        """
        self._stub_warn("popover")
        text = kwargs.get("text", "") or f"[Popover: {panel}]"
        icon = kwargs.get("icon", "") or "DOWNARROW_HLT"
        icon_value = kwargs.get("icon_value", 0)
        if icon_value and DBG_GPU:
            logi(f"[GPULayout] popover() icon_value={icon_value} ignored")
        self.label(text=text, icon=icon)

    def popover_group(self, *args, **kwargs) -> None:
        """Stub: popover_group() - not applicable for GPU layout."""
        self._stub_warn("popover_group")

    # -------------------------------------------------------------------------
    # Context Stubs
    # -------------------------------------------------------------------------

    def context_pointer_set(self, name: str, data: Any, *args, **kwargs) -> None:
        """Stub: context_pointer_set() - not implemented."""
        self._stub_warn("context_pointer_set")

    def context_string_set(self, name: str, value: str, *args, **kwargs) -> None:
        """Stub: context_string_set() - not implemented."""
        self._stub_warn("context_string_set")

    # -------------------------------------------------------------------------
    # Class Methods (static utilities)
    # -------------------------------------------------------------------------

    @classmethod
    def icon(cls, data: Any, *args, **kwargs) -> int:
        """Stub: icon() → returns 0 (no icon)."""
        if DBG_GPU:
            logi("[GPULayout] 'icon' classmethod not implemented (stub)")
        return 0

    @classmethod
    def enum_item_name(cls, data: Any, property: str, identifier: str,
                       *args, **kwargs) -> str:
        """Stub: enum_item_name() → returns identifier."""
        if DBG_GPU:
            logi("[GPULayout] 'enum_item_name' classmethod not implemented (stub)")
        return identifier

    @classmethod
    def enum_item_description(cls, data: Any, property: str, identifier: str,
                              *args, **kwargs) -> str:
        """Stub: enum_item_description() → returns empty string."""
        if DBG_GPU:
            logi("[GPULayout] 'enum_item_description' classmethod not implemented (stub)")
        return ""

    @classmethod
    def enum_item_icon(cls, data: Any, property: str, identifier: str,
                       *args, **kwargs) -> int:
        """Stub: enum_item_icon() → returns 0 (no icon)."""
        if DBG_GPU:
            logi("[GPULayout] 'enum_item_icon' classmethod not implemented (stub)")
        return 0

    # -------------------------------------------------------------------------
    # Template Stubs (commonly used)
    # -------------------------------------------------------------------------

    def template_header(self, *args, **kwargs) -> None:
        """Stub: template_header() - not applicable."""
        self._stub_warn("template_header")

    def template_ID(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_ID() → label fallback."""
        self._stub_warn("template_ID")
        try:
            value = getattr(data, property, None)
            name = getattr(value, "name", "None") if value else "None"
            self.label(text=f"{property}: {name}", icon="OBJECT_DATA")
        except Exception:
            self.label(text=f"[template_ID: {property}]", icon="OBJECT_DATA")

    def template_ID_preview(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_ID_preview() → template_ID fallback."""
        self._stub_warn("template_ID_preview")
        self.template_ID(data, property)

    def template_any_ID(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_any_ID() → template_ID fallback."""
        self._stub_warn("template_any_ID")
        self.template_ID(data, property)

    def template_ID_tabs(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_ID_tabs() → template_ID fallback."""
        self._stub_warn("template_ID_tabs")
        self.template_ID(data, property)

    def template_search(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_search() → prop_search fallback."""
        self._stub_warn("template_search")
        search_data = args[0] if args else kwargs.get("search_data")
        search_property = args[1] if len(args) > 1 else kwargs.get("search_property", "")
        self.prop_search(data, property, search_data, search_property)

    def template_search_preview(self, *args, **kwargs) -> None:
        """Stub: template_search_preview() → template_search fallback."""
        self._stub_warn("template_search_preview")
        self.template_search(*args, **kwargs)

    def template_list(self, listtype_name: str, list_id: str,
                      dataptr: Any, propname: str, *args, **kwargs) -> None:
        """Stub: template_list() → label fallback."""
        self._stub_warn("template_list")
        try:
            items = getattr(dataptr, propname, [])
            count = len(items) if hasattr(items, "__len__") else "?"
            self.label(text=f"[List: {propname} ({count} items)]", icon="COLLAPSEMENU")
        except Exception:
            self.label(text=f"[template_list: {propname}]", icon="COLLAPSEMENU")

    def template_icon(self, icon_value: int, *args, **kwargs) -> None:
        """Stub: template_icon() - not implemented."""
        self._stub_warn("template_icon")

    def template_icon_view(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_icon_view() → label fallback."""
        self._stub_warn("template_icon_view")
        self.label(text=f"[icon_view: {property}]", icon="IMAGE_DATA")

    def template_color_picker(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_color_picker() → color() fallback."""
        self._stub_warn("template_color_picker")
        try:
            value = getattr(data, property, (1, 1, 1, 1))
            if len(value) == 3:
                value = (*value, 1.0)
            self.color(color=value, text=property)
        except Exception:
            self.color(color=(1, 1, 1, 1), text=property)

    def template_color_ramp(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_color_ramp() → label fallback."""
        self._stub_warn("template_color_ramp")
        self.label(text=f"[color_ramp: {property}]", icon="COLOR")

    def template_curve_mapping(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_curve_mapping() → label fallback."""
        self._stub_warn("template_curve_mapping")
        self.label(text=f"[curve_mapping: {property}]", icon="CURVE_DATA")

    def template_curveprofile(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_curveprofile() → label fallback."""
        self._stub_warn("template_curveprofile")
        self.label(text=f"[curveprofile: {property}]", icon="CURVE_DATA")

    def template_palette(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_palette() → label fallback."""
        self._stub_warn("template_palette")
        self.label(text=f"[palette: {property}]", icon="COLOR")

    def template_histogram(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_histogram() → label fallback."""
        self._stub_warn("template_histogram")
        self.label(text=f"[histogram]", icon="FCURVE")

    def template_waveform(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_waveform() → label fallback."""
        self._stub_warn("template_waveform")
        self.label(text=f"[waveform]", icon="FCURVE")

    def template_vectorscope(self, data: Any, property: str, *args, **kwargs) -> None:
        """Stub: template_vectorscope() → label fallback."""
        self._stub_warn("template_vectorscope")
        self.label(text=f"[vectorscope]", icon="FCURVE")

    def template_layers(self, *args, **kwargs) -> None:
        """Stub: template_layers() → label fallback."""
        self._stub_warn("template_layers")
        self.label(text="[layers]", icon="RENDERLAYERS")

    def template_preview(self, *args, **kwargs) -> None:
        """Stub: template_preview() - not implemented."""
        self._stub_warn("template_preview")

    def template_modifiers(self, *args, **kwargs) -> None:
        """Stub: template_modifiers() - not applicable."""
        self._stub_warn("template_modifiers")

    def template_constraints(self, *args, **kwargs) -> None:
        """Stub: template_constraints() - not applicable."""
        self._stub_warn("template_constraints")

    def template_shaderfx(self, *args, **kwargs) -> None:
        """Stub: template_shaderfx() - not applicable."""
        self._stub_warn("template_shaderfx")

    # --- Less common templates (catch-all) ---

    def template_action(self, *args, **kwargs) -> None:
        self._stub_warn("template_action")

    def template_path_builder(self, *args, **kwargs) -> None:
        self._stub_warn("template_path_builder")

    def template_matrix(self, *args, **kwargs) -> None:
        self._stub_warn("template_matrix")

    def template_image(self, *args, **kwargs) -> None:
        self._stub_warn("template_image")

    def template_image_settings(self, *args, **kwargs) -> None:
        self._stub_warn("template_image_settings")

    def template_image_stereo_3d(self, *args, **kwargs) -> None:
        self._stub_warn("template_image_stereo_3d")

    def template_image_views(self, *args, **kwargs) -> None:
        self._stub_warn("template_image_views")

    def template_image_layers(self, *args, **kwargs) -> None:
        self._stub_warn("template_image_layers")

    def template_movieclip(self, *args, **kwargs) -> None:
        self._stub_warn("template_movieclip")

    def template_track(self, *args, **kwargs) -> None:
        self._stub_warn("template_track")

    def template_marker(self, *args, **kwargs) -> None:
        self._stub_warn("template_marker")

    def template_movieclip_information(self, *args, **kwargs) -> None:
        self._stub_warn("template_movieclip_information")

    def template_running_jobs(self, *args, **kwargs) -> None:
        self._stub_warn("template_running_jobs")

    def template_operator_search(self, *args, **kwargs) -> None:
        self._stub_warn("template_operator_search")

    def template_menu_search(self, *args, **kwargs) -> None:
        self._stub_warn("template_menu_search")

    def template_header_3D_mode(self, *args, **kwargs) -> None:
        self._stub_warn("template_header_3D_mode")

    def template_edit_mode_selection(self, *args, **kwargs) -> None:
        self._stub_warn("template_edit_mode_selection")

    def template_reports_banner(self, *args, **kwargs) -> None:
        self._stub_warn("template_reports_banner")

    def template_input_status(self, *args, **kwargs) -> None:
        self._stub_warn("template_input_status")

    def template_status_info(self, *args, **kwargs) -> None:
        self._stub_warn("template_status_info")

    def template_node_link(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_link")

    def template_node_view(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_view")

    def template_node_asset_menu_items(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_asset_menu_items")

    def template_modifier_asset_menu_items(self, *args, **kwargs) -> None:
        self._stub_warn("template_modifier_asset_menu_items")

    def template_node_operator_asset_menu_items(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_operator_asset_menu_items")

    def template_node_operator_asset_root_items(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_operator_asset_root_items")

    def template_texture_user(self, *args, **kwargs) -> None:
        self._stub_warn("template_texture_user")

    def template_keymap_item_properties(self, *args, **kwargs) -> None:
        self._stub_warn("template_keymap_item_properties")

    def template_component_menu(self, *args, **kwargs) -> None:
        self._stub_warn("template_component_menu")

    def template_colorspace_settings(self, *args, **kwargs) -> None:
        self._stub_warn("template_colorspace_settings")

    def template_colormanaged_view_settings(self, *args, **kwargs) -> None:
        self._stub_warn("template_colormanaged_view_settings")

    def template_node_socket(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_socket")

    def template_cache_file(self, *args, **kwargs) -> None:
        self._stub_warn("template_cache_file")

    def template_cache_file_velocity(self, *args, **kwargs) -> None:
        self._stub_warn("template_cache_file_velocity")

    def template_cache_file_time_settings(self, *args, **kwargs) -> None:
        self._stub_warn("template_cache_file_time_settings")

    def template_cache_file_layers(self, *args, **kwargs) -> None:
        self._stub_warn("template_cache_file_layers")

    def template_recent_files(self, *args, **kwargs) -> int:
        self._stub_warn("template_recent_files")
        return 0

    def template_file_select_path(self, *args, **kwargs) -> None:
        self._stub_warn("template_file_select_path")

    def template_event_from_keymap_item(self, *args, **kwargs) -> None:
        self._stub_warn("template_event_from_keymap_item")

    def template_light_linking_collection(self, *args, **kwargs) -> None:
        self._stub_warn("template_light_linking_collection")

    def template_bone_collection_tree(self, *args, **kwargs) -> None:
        self._stub_warn("template_bone_collection_tree")

    def template_grease_pencil_layer_tree(self, *args, **kwargs) -> None:
        self._stub_warn("template_grease_pencil_layer_tree")

    def template_node_tree_interface(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_tree_interface")

    def template_node_inputs(self, *args, **kwargs) -> None:
        self._stub_warn("template_node_inputs")

    def template_asset_shelf_popover(self, *args, **kwargs) -> None:
        self._stub_warn("template_asset_shelf_popover")

    def template_popup_confirm(self, *args, **kwargs) -> None:
        self._stub_warn("template_popup_confirm")

    def template_shape_key_tree(self, *args, **kwargs) -> None:
        self._stub_warn("template_shape_key_tree")

    def template_strip_modifiers(self, *args, **kwargs) -> None:
        self._stub_warn("template_strip_modifiers")

    def template_collection_exporters(self, *args, **kwargs) -> None:
        self._stub_warn("template_collection_exporters")

    def template_greasepencil_color(self, *args, **kwargs) -> None:
        self._stub_warn("template_greasepencil_color")

    def template_constraint_header(self, *args, **kwargs) -> None:
        self._stub_warn("template_constraint_header")

    # -------------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------------

    def introspect(self, *args, **kwargs) -> list:
        """Stub: introspect() → returns empty list."""
        self._stub_warn("introspect")
        return []


__all__ = ["UILayoutStubMixin", "OperatorProperties", "NullLayout"]
