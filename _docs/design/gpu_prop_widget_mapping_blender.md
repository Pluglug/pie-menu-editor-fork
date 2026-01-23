# Blender UILayout.prop() Widget Mapping (Reference)

Source: `E:\0187_Pie-Menu-Editor\Blender_source\blender\source\blender\editors\interface\`

This document summarizes Blender's automatic widget selection for `UILayout.prop()` based on
`uiDefAutoButR()` and `Layout::prop()`/`ui_item_array()` logic. Use this as a baseline to
align GPULayout widget branching.

## 1) uiDefAutoButR() mapping (interface_utils.cc)

File: `interface_utils.cc`

- `PROP_BOOLEAN`
  - Array + index == -1: returns null (array handled elsewhere).
  - If icon + empty name: `IconToggle` (icon-only).
  - If icon + name: `IconToggle` (icon + text).
  - Else: `Checkbox`.
- `PROP_INT` / `PROP_FLOAT`
  - Array + index == -1:
    - Subtype `COLOR`/`COLOR_GAMMA`: `Color`.
    - Else: returns null (array handled elsewhere).
  - Subtype `PERCENTAGE`/`FACTOR`: `NumSlider`.
  - Else: `Num` (or `NumSlider` if override set).
  - `PROP_TEXTEDIT_UPDATE` flag: enable `BUT_TEXTEDIT_UPDATE`.
- `PROP_ENUM`
  - Uses `Menu` (or `SearchMenu` if override set).
  - Icon-only: `IconMenu`.
  - Icon + text: `IconTextMenu`.
  - Else: `Menu`.
- `PROP_STRING`
  - Uses `SearchMenu` if `RNA_property_string_search_flag()` is set, else `Text`.
  - Icon-only: `IconText` (search or text).
  - Icon + text: `IconText` (search or text).
  - Else: `Text` or `SearchMenu`.
  - `PROP_TEXTEDIT_UPDATE`: enable `BUT_TEXTEDIT_UPDATE` + `BUT_VALUE_CLEAR`.
- `PROP_POINTER`
  - Uses `SearchMenu` with icon inferred from pointer type.
- `PROP_COLLECTION`
  - `Label` with "N items", disabled.

## 2) Layout::prop() flags (interface_layout.cc)

File: `interface_layout.cc`

Key flags that alter widget type or layout:

- `ITEM_R_SLIDER`: forces slider rendering for numeric values.
- `ITEM_R_EXPAND`: expands enum into multiple items (radio-like); `PROP_ENUM_FLAG` forces expand.
- `ITEM_R_TOGGLE` / `ITEM_R_ICON_NEVER`: forces toggle vs checkbox for booleans.
- `ITEM_R_ICON_ONLY`: icon-only buttons.
- `ITEM_R_NO_BG`: disables emboss/background.
- `ITEM_R_COMPACT`: compact enum items in menus.
- Property split (`use_property_split`) affects label placement and row/column structure.

## 3) Array handling (ui_item_array)

Arrays are *not* handled by `uiDefAutoButR()` in most cases.

- Boolean arrays with subtype `LAYER` / `LAYER_MEMBER`:
  - Rendered as a grid of toggle buttons (layer widgets).
- Subtype `MATRIX`:
  - Rendered as a numeric grid (2D matrix).
- Subtype `DIRECTION` (non-expanded):
  - Uses `Unitvec` widget (3D direction).
- Other arrays:
  - Expanded into per-element widgets.
  - If `expand` is false, Blender still expands for arrays.
  - Labels use axis suffix (X/Y/Z/W or property-specific chars).
  - Boolean arrays in non-embossed blocks may use checkbox icons.

## 4) Enum expand behavior

- `PROP_ENUM` + `ITEM_R_EXPAND`:
  - `ui_item_enum_expand()` creates multiple buttons (Row/Column depending on layout direction).
  - `PROP_ENUM_FLAG` forces expanded layout (multi-select).
  - Icon-only mode hides labels for enum items.

## 5) Implications for GPULayout

Current GPULayout behavior (as of 2026-01-23):

- Boolean -> Checkbox/Toggle (toggle flag supported).
- Int/Float -> Number/Slider (slider flag supported).
- Enum -> RadioGroup if expand, else label fallback (menu not implemented).
- Color array -> ColorItem (handled by WidgetHint).
- Vector arrays -> currently fallback to prop_display (no vector widgets).
- String/Pointer/Collection -> fallback to prop_display.

## 6) Deferred / Non-blocking Items

The following widget types are intentionally not implemented yet and are expected to
fall back to `prop_display()` for now. This is **not a blocker** for current milestones,
but it is a blocker for full Blender UI parity.

- Text/Search (String)
- Menu/SearchMenu (Enum)
- Pointer Search
- Vector/Matrix/Direction array widgets

Remaining gaps to align with Blender:

- Enum MENU/SearchMenu widget.
- String Text/Search widget.
- Pointer Search widget.
- Vector/Array widgets (including axis labels).
- Special subtypes (Matrix, Direction, Layer, Axis-Angle).

## 7) Gap Analysis vs GPULayout (Current)

| Area | Blender behavior | GPULayout status | Notes |
| --- | --- | --- | --- |
| Boolean + icon | IconToggle when icon is set | Checkbox/Toggle only via `toggle` param | Icon presence does not affect widget choice yet |
| Enum (default) | Menu or SearchMenu | RadioGroup fallback | Dropdown not implemented |
| Enum flags | Auto expand (multi-select) | No automatic expand | Needs `PROP_ENUM_FLAG` awareness |
| String | Text or SearchMenu | `prop_display()` fallback | Text input/Search not implemented |
| Pointer | SearchMenu with type icon | `prop_display()` fallback | Pointer widget not implemented |
| Collection | Disabled Label `"N items"` | `prop_display()` fallback | Should show item count |
| Numeric array (vector) | Per-axis inputs, labels | `prop_display()` fallback | `WidgetHint.VECTOR` is not implemented |
| Matrix / Direction / Layers | Specialized array widgets | Not implemented | `ui_item_array()` cases missing |
| Property split/decorate | Split label/field + decorators | Not implemented | `use_property_split/use_property_decorate` unused |
| Flags: icon_only/compact/no_bg | Affects layout/emboss | Not implemented | Parameters exist but not used |
