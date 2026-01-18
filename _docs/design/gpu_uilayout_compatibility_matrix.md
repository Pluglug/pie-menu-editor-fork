# GPULayout UILayout Compatibility Matrix

> Version: 2.0
> Last Updated: 2026-01-18
> Blender Target: 5.0+
> Source: [Blender Python API - UILayout](https://docs.blender.org/api/current/bpy.types.UILayout.html)

---

## Overview

This document tracks the compatibility between `bpy.types.UILayout` and PME's `GPULayout`.
GPULayout aims to provide a familiar API for users migrating from standard Blender UI scripting.

Stub methods are provided via `UILayoutStubMixin` in `ui/gpu/uilayout_stubs.py`.

### Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented |
| ⚠️ | Partially implemented (see notes) |
| 🔲 | Not implemented (stub provided) |
| ➖ | Not applicable / Won't implement |

---

## 1. Layout Properties

| Property | UILayout Type | GPULayout | Notes |
|----------|---------------|-----------|-------|
| `active` | bool | ✅ | Grays out items when False |
| `active_default` | bool | ✅ | Return key activates operator (no-op) |
| `activate_init` | bool | ✅ | Auto-activate in popups (no-op) |
| `enabled` | bool | ✅ | Disables interaction when False |
| `alert` | bool | ✅ | Red highlight for warnings |
| `alignment` | enum | ✅ | EXPAND, LEFT, CENTER, RIGHT |
| `direction` | enum | ✅ | HORIZONTAL, VERTICAL (readonly) |
| `emboss` | enum | ✅ | Stored but not yet rendered differently |
| `scale_x` | float | ✅ | Horizontal scale factor |
| `scale_y` | float | ✅ | Vertical scale factor |
| `ui_units_x` | float | ✅ | Fixed width in UI units (stored, not used) |
| `ui_units_y` | float | ✅ | Fixed height in UI units (stored, not used) |
| `use_property_split` | bool | ✅ | Stored but not yet rendered differently |
| `use_property_decorate` | bool | ✅ | Stored but not yet rendered differently |
| `operator_context` | enum | ➖ | Context override for operators |

---

## 2. Layout Container Methods

| Method | Signature | GPULayout | Notes |
|--------|-----------|-----------|-------|
| `row()` | `row(*, heading='', align=False, ...)` | ⚠️ | `align` supported, `heading` ignored |
| `column()` | `column(*, heading='', align=False, ...)` | ⚠️ | `align` supported, `heading` ignored |
| `box()` | `box()` | ✅ | Background + outline |
| `split()` | `split(*, factor=0.0, align=False)` | ✅ | 2-column split |
| `panel()` | `panel(idname, *, default_closed=False)` | 🔲 | Returns `(self, self)` as fallback |
| `panel_prop()` | `panel_prop(data, property)` | 🔲 | Returns `(self, self)` as fallback |
| `grid_flow()` | `grid_flow(*, row_major=False, columns=0, ...)` | 🔲 | → `column()` fallback |
| `column_flow()` | `column_flow(*, columns=0, align=False)` | 🔲 | → `column()` fallback |
| `menu_pie()` | `menu_pie()` | 🔲 | Not applicable |

---

## 3. Display Methods

| Method | Signature | GPULayout | Notes |
|--------|-----------|-----------|-------|
| `label()` | `label(*, text='', icon='NONE', ...)` | ⚠️ | `text`, `icon` supported |
| `separator()` | `separator(*, factor=1.0, type='AUTO')` | ⚠️ | `factor` supported, `type` ignored |
| `separator_spacer()` | `separator_spacer()` | ✅ | Flexible spacer |
| `progress()` | `progress(*, text='', factor=0.0, type='BAR')` | 🔲 | → label with percentage |

---

## 4. Operator Methods

| Method | Signature | GPULayout | Notes |
|--------|-----------|-----------|-------|
| `operator()` | `operator(operator, *, text='', icon='NONE', ...)` | ⚠️ | `on_click` callback instead of bl_idname |
| `operator_enum()` | `operator_enum(operator, property, ...)` | 🔲 | → label fallback |
| `operator_menu_enum()` | `operator_menu_enum(operator, property, ...)` | 🔲 | → label fallback |
| `operator_menu_hold()` | `operator_menu_hold(operator, *, menu='', ...)` | 🔲 | → label fallback |

---

## 5. Property Methods

| Method | Signature | GPULayout | Notes |
|--------|-----------|-----------|-------|
| `prop()` | `prop(data, property, *, text='', expand=False, slider=False, toggle=-1, ...)` | ⚠️ | Core params supported |
| `prop_enum()` | `prop_enum(data, property, value, ...)` | ⚠️ | Basic display only |
| `props_enum()` | `props_enum(data, property)` | 🔲 | → label fallback |
| `prop_menu_enum()` | `prop_menu_enum(data, property, ...)` | 🔲 | → label fallback |
| `prop_tabs_enum()` | `prop_tabs_enum(data, property, ...)` | 🔲 | → `prop(expand=True)` |
| `prop_search()` | `prop_search(data, property, search_data, search_property, ...)` | 🔲 | → label fallback |
| `prop_decorator()` | `prop_decorator(data, property, ...)` | 🔲 | No visual output |
| `prop_with_popover()` | `prop_with_popover(data, property, *, panel='', ...)` | 🔲 | → `prop()` fallback |
| `prop_with_menu()` | `prop_with_menu(data, property, *, menu='', ...)` | 🔲 | → `prop()` fallback |

---

## 6. Menu Methods

| Method | Signature | GPULayout | Notes |
|--------|-----------|-----------|-------|
| `menu()` | `menu(menu, *, text='', icon='NONE', ...)` | 🔲 | → label fallback |
| `menu_contents()` | `menu_contents(menu)` | 🔲 | → label fallback |
| `popover()` | `popover(panel, *, text='', icon='NONE', ...)` | 🔲 | → label fallback |
| `popover_group()` | `popover_group(space_type, region_type, context, category)` | 🔲 | No-op |

---

## 7. Context Methods

| Method | Signature | GPULayout | Notes |
|--------|-----------|-----------|-------|
| `context_pointer_set()` | `context_pointer_set(name, data)` | 🔲 | No-op |
| `context_string_set()` | `context_string_set(name, value)` | 🔲 | No-op |

---

## 8. Class Methods (Utilities)

| Method | Signature | GPULayout | Notes |
|--------|-----------|-----------|-------|
| `icon()` | `icon(data) -> int` | 🔲 | Returns 0 |
| `enum_item_name()` | `enum_item_name(data, property, identifier) -> str` | 🔲 | Returns identifier |
| `enum_item_description()` | `enum_item_description(data, property, identifier) -> str` | 🔲 | Returns "" |
| `enum_item_icon()` | `enum_item_icon(data, property, identifier) -> int` | 🔲 | Returns 0 |
| `introspect()` | `introspect() -> list` | 🔲 | Returns [] |

---

## 9. Template Methods

All template methods are stubbed via `UILayoutStubMixin`. Most display a `[template_name]` label as fallback.

| Category | Methods | GPULayout |
|----------|---------|-----------|
| **ID Selection** | `template_ID`, `template_ID_preview`, `template_any_ID`, `template_ID_tabs` | 🔲 label |
| **Search** | `template_search`, `template_search_preview` | 🔲 label |
| **List** | `template_list` | 🔲 label with item count |
| **Color** | `template_color_picker`, `template_color_ramp`, `template_palette` | 🔲 color()/label |
| **Curve** | `template_curve_mapping`, `template_curveprofile` | 🔲 label |
| **Image/Video** | `template_image`, `template_movieclip`, `template_histogram`, etc. | 🔲 label |
| **Node** | `template_node_*` (10+ methods) | 🔲 no-op |
| **Modifiers** | `template_modifiers`, `template_constraints`, `template_shaderfx` | 🔲 no-op |
| **Special** | `template_header`, `template_preview`, `template_layers`, etc. | 🔲 no-op/label |

**Total template methods stubbed: 60+**

---

## 10. GPULayout-Specific Methods

These methods are unique to GPULayout and have no UILayout equivalent:

| Method | Description |
|--------|-------------|
| `slider()` | Standalone slider widget |
| `number()` | Number field with drag |
| `checkbox()` | Standalone checkbox |
| `toggle()` | Toggle button |
| `radio_group()` | Radio button group |
| `color()` | Color swatch display |
| `prop_display()` | Read-only property display |
| `set_title_bar()` | Panel title bar |
| `set_panel_config()` | Panel resize/persistence |
| `set_region_bounds()` | Boundary clamping |
| `sync_props()` | Reactive property sync |
| `sync_reactive()` | Reactive context sync |

---

## 11. Implementation Architecture

```
GPULayout(UILayoutStubMixin)
    │
    ├── Core methods (implemented in layout.py)
    │   ├── row(), column(), box(), split()
    │   ├── label(), separator(), operator()
    │   ├── prop(), prop_enum(), prop_display()
    │   └── GPULayout-specific methods
    │
    └── Stub methods (inherited from UILayoutStubMixin)
        ├── grid_flow(), column_flow(), panel(), panel_prop()
        ├── progress(), props_enum(), prop_menu_enum(), etc.
        ├── menu(), popover(), context_*()
        └── template_*() (60+ methods)
```

---

## 12. prop() Parameter Support Details

| Parameter | Supported | Notes |
|-----------|-----------|-------|
| `data` | ✅ | RNA object |
| `property` | ✅ | Property identifier |
| `text` | ✅ | Override label |
| `text_ctxt` | ➖ | Translation context |
| `translate` | ➖ | Translation toggle |
| `icon` | ✅ | Icon name |
| `placeholder` | 🔲 | Text field hint |
| `expand` | ✅ | Enum → RadioGroup |
| `slider` | ✅ | Number → Slider |
| `toggle` | ✅ | Bool → Toggle/Checkbox |
| `icon_only` | 🔲 | Icon-only display |
| `event` | ➖ | Key event input |
| `full_event` | ➖ | Full event input |
| `emboss` | 🔲 | Button emboss |
| `index` | 🔲 | Array index |
| `icon_value` | 🔲 | Custom icon ID |
| `invert_checkbox` | 🔲 | Inverted bool |

---

## 13. Implementation Priorities

### Phase 1: Essential (Current) ✅
- row, column, box, split
- label, separator
- prop (basic)
- Properties: active, enabled, alert, alignment, scale_x/y

### Phase 2: Enhanced Props
- 🔲 use_property_split rendering
- 🔲 use_property_decorate rendering
- 🔲 prop_decorator visual
- 🔲 emboss rendering

### Phase 3: Flow Layouts
- 🔲 grid_flow (actual grid)
- 🔲 column_flow (actual multi-column)
- 🔲 ui_units_x/y rendering
- 🔲 panel() collapsible panels

### Phase 4: Menus & Search
- 🔲 menu (dropdown)
- 🔲 prop_search (search field)
- 🔲 template_search

### Phase 5: Advanced
- 🔲 template_list (scrollable)
- 🔲 template_color_picker (wheel)
- 🔲 popover (floating panel)

---

## References

- [Blender Python API - UILayout](https://docs.blender.org/api/current/bpy.types.UILayout.html)
- [Blender UI Best Practices](https://docs.blender.org/api/current/info_best_practice.html)
- `ui/gpu/layout.py` - GPULayout implementation
- `ui/gpu/uilayout_stubs.py` - UILayoutStubMixin

---

*Last Updated: 2026-01-18*
