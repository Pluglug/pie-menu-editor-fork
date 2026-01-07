# 9-D-3: extend_target Diagnosis Report

> **Branch**: `investigate/9d3-extend-target`
> **Related Issues**: #88, #69
> **Date**: 2026-01-07
> **Status**: Diagnosis Complete (No Code Changes)

---

## Executive Summary

`extend_target` is a **proposed new field** (D19) in JSON Schema v2 that does NOT yet exist in code.
PME1 encodes the Blender Panel/Menu/Header ID within `pm.name` using suffix conventions.
The D19 concept is sound, but **placement should be in `settings`**, not top-level.

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

### Decision: **Settings** (Revises D19 Design)

| Criteria | Settings | Top-level | Winner |
|----------|----------|-----------|--------|
| Mode-specific? | Yes (3 of 10 modes) | All 10 modes | **Settings** |
| Semantic meaning | Config/behavior | Identity | **Settings** |
| Precedent | radius, prop_type, space | uid, name, mode | **Settings** |
| Schema cleanliness | Absent for unused modes | null for 7 modes | **Settings** |
| Consistency | Matches other mode-specific fields | Exception | **Settings** |

### Rationale

1. **Mode-specific by definition**: `extend_target` is used by only 3 modes (PANEL, DIALOG, RMENU). The `settings` object is explicitly defined as "mode に応じて異なるプロパティ" — this is exactly what `extend_target` is.

2. **Consistency with existing patterns**:
   - PMENU: `radius`, `flick`, `confirm` → in settings
   - PROPERTY: `prop_type` → in settings
   - PANEL: `space`, `region`, `category` → in settings
   - `extend_target` should follow the same pattern.

3. **Schema cleanliness**: Having `extend_target: null` in 7 modes (PMENU, HPANEL, SCRIPT, MACRO, MODAL, STICKY, PROPERTY) is noise. Settings naturally handles this by omission.

4. **Semantic correction**: `extend_target` is **configuration** (which Blender UI to extend), not **identity** (like `uid`, `name`). Configuration belongs in settings.

5. **D19 core insight preserved**: The separation of display name from Blender ID is correct. Moving `extend_target` to settings doesn't change this benefit.

### Why Top-level Was Initially Considered (Rejected)

| Argument | Counter |
|----------|---------|
| "It's about identity" | No — it's about target configuration, not menu identity |
| "Related to `name`" | Related ≠ same category. `name` is identity, `extend_target` is config |
| "Explicit null is clearer" | 7 nulls is schema pollution, not clarity |

---

## Menu.name Relationship Clarification

### PME2 Schema Design (Revised)

```json
{
  "uid": "pg_abc123",
  "name": "My Custom Panel",        // Display name (user-editable)
  "mode": "PANEL",
  "settings": {
    "space": "VIEW_3D",
    "region": "UI",
    "category": "PME",
    "extend_target": "VIEW3D_PT_tools",  // Blender ID (in settings!)
    "extend_position": "append"          // or "prepend"
  }
}
```

### Role Separation

| Field | Location | Purpose | Valid Values |
|-------|----------|---------|-------------|
| `name` | top-level | Display name | Any string |
| `uid` | top-level | Internal ID | `{mode}_{random}` |
| `extend_target` | **settings** | Blender type ID | Valid bl_idname (or absent) |
| `extend_position` | **settings** | Insert position | "append" / "prepend" |

### Migration from PME1

| PME1 | PME2 | Notes |
|------|------|-------|
| `pm.name = "VIEW3D_PT_tools_pre"` | `name`: "VIEW3D_PT_tools", `settings.extend_target`: "VIEW3D_PT_tools", `settings.extend_position`: "prepend" | サフィックスを分離 |
| N/A | `name`: "My Panel", `settings.extend_target`: "VIEW3D_PT_tools" | ユーザーは自由な表示名を設定可能 |

---

## Position Encoding (F_PRE, F_RIGHT)

### Current PME1 Approach

Position is encoded in `pm.name` suffix:
- `_pre` → prepend
- `_right` → right region
- No suffix → append, default region

### PME2 Recommendation

All extend-related fields should be in `settings`:

```json
{
  "settings": {
    "extend_target": "VIEW3D_PT_tools",
    "extend_position": "prepend",   // or "append"
    "extend_region": "right"        // optional, for header right region
  }
}
```

This keeps all mode-specific configuration together and avoids suffix parsing.

---

## Conclusions

1. **D19 concept is valid**: Separating display name from Blender ID is correct
2. **Placement revised**: `extend_target` should be in **`settings`**, not top-level
3. **Position encoding**: Also move to settings (`extend_position`, `extend_region`)
4. **Schema consistency**: Matches other mode-specific fields (`radius`, `prop_type`, `space`)
5. **Migration path**: PME1 `pm.name` → PME2 `name` + `settings.extend_target`

---

## References

- `editors/base.py:139-178` - `extend_panel()` / `unextend_panel()`
- `infra/utils.py:63-73` - `extract_str_flags_b()`
- `core/constants.py:25-26` - `F_RIGHT`, `F_PRE`
- `_docs/design/design_decisions.md:409-429` - D19 specification
- `_docs/design/json_schema_v2.md:125` - `extend_target` field definition
