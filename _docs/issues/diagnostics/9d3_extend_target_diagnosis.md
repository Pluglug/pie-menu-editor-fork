# 9-D-3: extend_target Diagnosis Report

> **Branch**: `investigate/9d3-extend-target`
> **Related Issues**: #88, #69
> **Date**: 2026-01-07
> **Status**: Diagnosis Complete (No Code Changes)

---

## Executive Summary

`extend_target` is a **proposed new field** (D19) in JSON Schema v2 that does NOT yet exist in code.
PME1 encodes the Blender Panel/Menu/Header ID within `pm.name` using suffix conventions.
The D19 proposal to add `extend_target` at the top level is **sound**.

---

## Diagnostic Results

### extend_target Current Status

| Aspect | Finding |
|--------|---------|
| In Code | **Does not exist** - D19 is a design proposal only |
| In Docs | Defined in `json_schema_v2.md` and `design_decisions.md` |
| PME1 Equivalent | `pm.name` serves this purpose (with suffix encoding) |

### PME1 Name Encoding Pattern

PME1 uses `pm.name` to encode multiple pieces of information:

```
pm.name = "VIEW3D_PT_tools_right_pre"
           ├─────────────┘│    │
           │              │    └── F_PRE = prepend position
           │              └─────── F_RIGHT = right region
           └────────────────────── Blender Panel ID
```

**Parsing function**: `infra/utils.py:extract_str_flags_b()`

```python
tp_name, has_right, has_pre = extract_str_flags_b(pm.name, F_RIGHT, F_PRE)
# tp_name = "VIEW3D_PT_tools" (actual Blender ID)
# has_right = True
# has_pre = True
```

### Usage Modes Summary

| Mode | Uses Extend | Uses pm.name as Blender ID | Notes |
|------|-------------|---------------------------|-------|
| PANEL | **Yes** | Yes (`_PT_`, `_HT_`) | Panel.append/prepend |
| DIALOG | **Yes** | Yes (`_PT_`, `_HT_`) | Same mechanism as PANEL |
| RMENU | **Yes** | Yes (`_MT_`) | Menu.append/prepend |
| HPANEL | No | No | Hides panels, doesn't extend |
| PMENU | No | No | Independent pie menu |
| SCRIPT | No | No | Stack key |
| MACRO | No | No | Macro operator |
| MODAL | No | No | Modal operator |
| STICKY | No | No | Sticky key |
| PROPERTY | No | No | Custom property |

### extend_panel() Implementation Analysis

Location: `editors/base.py:139-165`

```python
def extend_panel(pm):
    tp_name, right, pre = extract_str_flags_b(pm.name, F_RIGHT, F_PRE)
    tp = getattr(bpy_types, tp_name, None)  # Uses pm.name!

    if tp and issubclass(tp, (Panel, Menu, Header)):
        if '_HT_' in pm.name:
            draw_func = gen_header_draw(pm.name)
        elif '_MT_' in pm.name:
            draw_func = gen_menu_draw(pm.name)
        else:
            draw_func = gen_panel_draw(pm.name)

        f = tp.prepend if pre else tp.append
        f(draw_func)
```

**Critical Observation**: The extend mechanism depends on `pm.name` being a valid Blender type ID.

---

## The Problem (Issue #69)

### Current Behavior

1. User creates "Extend Panel" with `pm.name = "VIEW3D_PT_tools"`
2. PME calls `getattr(bpy_types, "VIEW3D_PT_tools")` → Success
3. User renames to `pm.name = "My Custom Panel"`
4. PME calls `getattr(bpy_types, "My Custom Panel")` → **Failure!**

### Root Cause

`pm.name` has **four responsibilities**:

1. **Display name**: UI labels, popup titles
2. **Blender type ID**: `getattr(bpy_types, tp_name)` for extend
3. **Dictionary key**: `EXTENDED_PANELS[pm.name]`, `kmis_map`
4. **Type classifier**: `'_HT_' in pm.name`, `'_MT_' in pm.name`

Responsibility #1 wants arbitrary user text.
Responsibilities #2-4 require valid Blender identifiers.
**These are incompatible.**

---

## Recommended Placement

### Decision: **Top-level** (Current D19 Design)

| Criteria | Settings | Top-level | Winner |
|----------|----------|-----------|--------|
| Semantic meaning | Behavior/config | Identity | **Top-level** |
| Modes using it | 3 specific modes | 3 specific modes | Tie |
| Relationship to name | Unrelated | Closely related | **Top-level** |
| Precedent | radius, width, etc. | uid, name, mode | **Top-level** |
| Null handling | Absent for unused modes | Explicit null | **Top-level** |

### Rationale

1. **Semantic fit**: `extend_target` is about **identity** (what Blender UI element to extend), not **behavior** (how to display it). It belongs with `name`, `uid`, `mode`.

2. **Multi-mode usage**: Used by PANEL, DIALOG, RMENU. Putting in settings would require documenting it in 3 places.

3. **Explicit over implicit**: Having `extend_target: null` for non-extending modes is clearer than absent keys.

4. **D19 rationale is sound**: The separation of concerns (`name` for display, `extend_target` for Blender ID) makes the design robust.

---

## Menu.name Relationship Clarification

### PME2 Schema Design

```json
{
  "uid": "pg_abc123",
  "name": "My Custom Panel",        // Display name (user-editable)
  "mode": "PANEL",
  "extend_target": "VIEW3D_PT_tools",  // Blender ID (required for extend)
  "settings": {
    "space": "VIEW_3D",
    "region": "UI",
    "category": "PME"
  }
}
```

### Role Separation

| Field | Purpose | Editable | Required | Valid Values |
|-------|---------|----------|----------|-------------|
| `name` | Display name | Yes | Yes | Any string |
| `extend_target` | Blender type ID | Yes* | No | Valid bl_idname or null |
| `uid` | Internal ID | No | Yes | `{mode}_{random}` |

\* Editable but must be valid Blender ID if set

### Migration from PME1

| PME1 | PME2 | Notes |
|------|------|-------|
| `pm.name = "VIEW3D_PT_tools_pre"` | `name`: "VIEW3D_PT_tools", `extend_target`: "VIEW3D_PT_tools" | Initial default keeps name = extend_target |
| N/A | `name`: "My Panel", `extend_target`: "VIEW3D_PT_tools" | User can now have different display name |

---

## Position Encoding (F_PRE, F_RIGHT)

### Current PME1 Approach

Position is encoded in `pm.name` suffix:
- `_pre` → prepend
- `_right` → right region
- No suffix → append, default region

### PME2 Recommendation

Consider moving position encoding to separate fields:

```json
{
  "extend_target": "VIEW3D_PT_tools",
  "extend_position": "prepend",   // or "append"
  "extend_region": "right"        // or "left" / null
}
```

**Alternative**: Keep in `extend_target` as suffixes for backward compatibility:
```json
{
  "extend_target": "VIEW3D_PT_tools_right_pre"
}
```

**Note**: This is a design question for D19 refinement, not a diagnosis finding.

---

## Conclusions

1. **D19 design is correct**: `extend_target` at top-level is appropriate
2. **No code changes needed**: `extend_target` is a schema-only concept until Phase 9-C converter implementation
3. **Position encoding**: Consider separate fields or maintain suffix convention
4. **Migration path**: Clear transformation from PME1 `pm.name` to PME2 `name` + `extend_target`

---

## References

- `editors/base.py:139-178` - `extend_panel()` / `unextend_panel()`
- `infra/utils.py:63-73` - `extract_str_flags_b()`
- `core/constants.py:25-26` - `F_RIGHT`, `F_PRE`
- `_docs/design/design_decisions.md:409-429` - D19 specification
- `_docs/design/json_schema_v2.md:125` - `extend_target` field definition
