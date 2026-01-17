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

    # ─────────────────────────────────────────────────────────────────────────
    # Warning utility
    # ─────────────────────────────────────────────────────────────────────────

    def _stub_warn(self, method_name: str) -> None:
        """Log warning for unimplemented UILayout method."""
        if DBG_GPU:
            logi(f"[GPULayout] '{method_name}' not implemented (stub)")

    # ─────────────────────────────────────────────────────────────────────────
    # Properties (as methods for compatibility)
    # ─────────────────────────────────────────────────────────────────────────

    # Note: activate_init, active_default are bool properties in UILayout
    # GPULayout doesn't need these - they're for popup button behavior

    # ─────────────────────────────────────────────────────────────────────────
    # Layout Container Stubs
    # ─────────────────────────────────────────────────────────────────────────

    def grid_flow(self, *args, **kwargs) -> "GPULayout":
        """Stub: grid_flow() → column() fallback."""
        self._stub_warn("grid_flow")
        return self.column(align=kwargs.get("align", False))

    def column_flow(self, *args, **kwargs) -> "GPULayout":
        """Stub: column_flow() → column() fallback."""
        self._stub_warn("column_flow")
        return self.column(align=kwargs.get("align", False))

    def menu_pie(self, *args, **kwargs) -> "GPULayout":
        """Stub: menu_pie() - not applicable."""
        self._stub_warn("menu_pie")
        return self

    def panel(self, idname: str, *args, **kwargs) -> Tuple[Any, Optional[Any]]:
        """
        Stub: panel() - collapsible panel.

        Returns (header_layout, body_layout) where body is None if collapsed.
        Fallback: Always returns (self, self) as if expanded.
        """
        self._stub_warn("panel")
        # Return (header, body) - both point to self as fallback
        return (self, self)

    def panel_prop(self, data: Any, property: str, *args, **kwargs) -> Tuple[Any, Optional[Any]]:
        """
        Stub: panel_prop() - data-driven collapsible panel.

        Returns (header_layout, body_layout) where body is None if collapsed.
        Fallback: Always returns (self, self) as if expanded.
        """
        self._stub_warn("panel_prop")
        return (self, self)

    # ─────────────────────────────────────────────────────────────────────────
    # Display Stubs
    # ─────────────────────────────────────────────────────────────────────────

    def progress(self, *args, **kwargs) -> None:
        """Stub: progress() → label with percentage."""
        self._stub_warn("progress")
        text = kwargs.get("text", "")
        factor = kwargs.get("factor", 0.0)
        pct = int(factor * 100)
        display = f"{text} {pct}%" if text else f"{pct}%"
        self.label(text=display)

    # ─────────────────────────────────────────────────────────────────────────
    # Operator Stubs
    # ─────────────────────────────────────────────────────────────────────────

    def operator_enum(self, operator: str, property: str, *args, **kwargs) -> None:
        """Stub: operator_enum() → label fallback."""
        self._stub_warn("operator_enum")
        self.label(text=f"[op_enum: {operator}]")

    def operator_menu_enum(self, operator: str, property: str, *args, **kwargs) -> None:
        """Stub: operator_menu_enum() → label fallback."""
        self._stub_warn("operator_menu_enum")
        text = kwargs.get("text", "") or f"[{operator}]"
        icon = kwargs.get("icon", "NONE")
        self.label(text=text, icon=icon)

    def operator_menu_hold(self, operator: str, *args, **kwargs) -> None:
        """Stub: operator_menu_hold() → label fallback."""
        self._stub_warn("operator_menu_hold")
        text = kwargs.get("text", "") or f"[{operator}]"
        icon = kwargs.get("icon", "NONE")
        self.label(text=text, icon=icon)

    # ─────────────────────────────────────────────────────────────────────────
    # Property Stubs
    # ─────────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────────
    # Menu Stubs
    # ─────────────────────────────────────────────────────────────────────────

    def menu(self, menu: str, *args, **kwargs) -> None:
        """Stub: menu() → label fallback."""
        self._stub_warn("menu")
        text = kwargs.get("text", "") or f"[Menu: {menu}]"
        icon = kwargs.get("icon", "") or "DOWNARROW_HLT"
        self.label(text=text, icon=icon)

    def menu_contents(self, menu: str, *args, **kwargs) -> None:
        """Stub: menu_contents() → label fallback."""
        self._stub_warn("menu_contents")
        self.label(text=f"[menu_contents: {menu}]")

    def popover(self, panel: str, *args, **kwargs) -> None:
        """Stub: popover() → label fallback."""
        self._stub_warn("popover")
        text = kwargs.get("text", "") or f"[Popover: {panel}]"
        icon = kwargs.get("icon", "") or "DOWNARROW_HLT"
        self.label(text=text, icon=icon)

    def popover_group(self, *args, **kwargs) -> None:
        """Stub: popover_group() - not applicable."""
        self._stub_warn("popover_group")

    # ─────────────────────────────────────────────────────────────────────────
    # Context Stubs
    # ─────────────────────────────────────────────────────────────────────────

    def context_pointer_set(self, name: str, data: Any, *args, **kwargs) -> None:
        """Stub: context_pointer_set() - not implemented."""
        self._stub_warn("context_pointer_set")

    def context_string_set(self, name: str, value: str, *args, **kwargs) -> None:
        """Stub: context_string_set() - not implemented."""
        self._stub_warn("context_string_set")

    # ─────────────────────────────────────────────────────────────────────────
    # Class Methods (static utilities)
    # ─────────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────────
    # Template Stubs (commonly used)
    # ─────────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────────
    # Introspection
    # ─────────────────────────────────────────────────────────────────────────

    def introspect(self, *args, **kwargs) -> list:
        """Stub: introspect() → returns empty list."""
        self._stub_warn("introspect")
        return []


__all__ = ["UILayoutStubMixin"]
