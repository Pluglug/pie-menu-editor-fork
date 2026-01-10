# Prefix Standardization Analysis

> Issue: #92
> Date: 2026-01-11
> Status: Phase 1 Complete

## Overview

Standardize property name prefixes for MODAL and PROPERTY modes to eliminate exceptions.

| Mode | Current | Target |
|------|---------|--------|
| MODAL | (none) `confirm`, `block_ui`, `lock` | `md_confirm`, `md_block_ui`, `md_lock` |
| PROPERTY | (none) `vector`, `mulsel`, etc. | `pr_vector`, `pr_mulsel`, etc. |

---

## MODAL Analysis

### Variables to Change

| Variable | New Name | Risk |
|----------|----------|------|
| `confirm` | `md_confirm` | **HIGH** - Used elsewhere |
| `block_ui` | `md_block_ui` | MEDIUM |
| `lock` | `md_lock` | **HIGH** - Used elsewhere |

### Files to Modify

#### Schema Definition
- `editors/modal.py:33-35` - Schema registration
- `core/schema.py:246-248` - Default values

#### UI Properties (pme_types.py)
- `pme_types.py:710-714` - `mo_confirm_on_release` → `get_data("confirm")`
- `pme_types.py:716-720` - `mo_block_ui` → `get_data("block_ui")`
- `pme_types.py:733-738` - `mo_lock` → `get_data("lock")`

#### Property Access
- `operators/__init__.py:1050` - `prop.confirm`
- `operators/__init__.py:1087,1840` - `prop.lock`
- `infra/macro.py:77,81,90` - `pm.get_data("lock")`

### Collision Analysis: `confirm`

| File | Usage | Context | Change? |
|------|-------|---------|---------|
| `editors/modal.py:33` | `schema.BoolProperty("mo", "confirm", ...)` | MODAL schema | ✅ YES |
| `pme_types.py:713-714` | `get_data("confirm")` | MODAL property | ✅ YES |
| `core/schema.py:246` | `'confirm': False` | MODAL default | ✅ YES |
| `operators/__init__.py:1050` | `prop.confirm` | MODAL parsed data | ✅ YES |
| `bl_utils.py:494` | `confirm: BoolProperty` | Operator param | ❌ NO |
| `bl_utils.py:500,518` | `self.confirm`, `on_confirm` | ConfirmBoxHandler | ❌ NO |
| `editors/pie_menu.py` | `pm_confirm` | PMENU (prefixed) | ❌ NO |
| `operators/__init__.py` (misc) | `confirm_key`, `do_confirm` | Internal vars | ❌ NO |
| `prefs/helpers.py` | `pie_menu_confirm` | Blender pref | ❌ NO |

### Collision Analysis: `lock`

| File | Usage | Context | Change? |
|------|-------|---------|---------|
| `editors/modal.py:35` | `schema.BoolProperty("mo", "lock", ...)` | MODAL schema | ✅ YES |
| `pme_types.py:736-737` | `get_data("lock")` | MODAL property | ✅ YES |
| `core/schema.py:248` | `'lock': True` | MODAL default | ✅ YES |
| `operators/__init__.py:1087,1840` | `prop.lock` | MODAL parsed data | ✅ YES |
| `infra/macro.py:77,81,90` | `pm.get_data("lock")` | MODAL data access | ✅ YES |
| `keymap_helper.py` | `Hotkey.lock` | Class attribute | ❌ NO |
| `prefs/helpers.py` | `self.lock` | State attribute | ❌ NO |
| `prefs/tree.py` | `tree_state.locked`, `lock()` | Tree methods | ❌ NO |
| `infra/utils.py` | `Lock()` | threading.Lock | ❌ NO |

---

## PROPERTY Analysis

### Variables to Change

| Variable | New Name | Risk |
|----------|----------|------|
| `prop_type` | `pr_prop_type` | LOW |
| `vector` | `pr_vector` | LOW |
| `mulsel` | `pr_mulsel` | LOW |
| `hor_exp` | `pr_hor_exp` | LOW |
| `exp` | `pr_exp` | LOW |
| `save` | `pr_save` | LOW |

### Files to Modify

#### Schema Definition
- `editors/property.py:37-51` - Schema registration (type: `"prop"` → `"pr"`)
- `core/schema.py:255-259` - Default values

#### Data Access (editors/property.py)
Lines: 86, 92, 107, 111, 116, 120, 124, 128, 132, 137, 277, 327, 375, 385, 434, 440, 447, 660, 807, 820, 878, 967, 1134-1137

#### Data Access (operators/__init__.py)
Lines: 1257-1274 (`sub_pm.get_data("vector")`, etc.)

### Collision Analysis

No significant collisions. Variables are unique to PROPERTY mode.
- `exp` - Only conflicts with `lh.exp` which is layout expand (different context)
- `save` - Only conflicts with `lh.save()` which is method call (different context)

---

## Migration Strategy

### Phase 2: Schema Changes

1. `editors/modal.py` - Change schema registration
2. `editors/property.py` - Change schema registration + type prefix
3. `core/schema.py` - Change default value keys

### Phase 3: Code Updates

**MODAL (careful):**
- Pattern: `prop.confirm` → `prop.md_confirm`
- Pattern: `get_data("confirm")` → `get_data("md_confirm")`
- Must NOT change: `ConfirmBoxHandler.confirm`, operator `confirm=` params

**PROPERTY (safe):**
- Pattern: `get_data("vector")` → `get_data("pr_vector")`
- Pattern: `set_data("vector", v)` → `set_data("pr_vector", v)`

### Phase 4: Data Migration

Add to `infra/compat.py`:

```python
def fix_2_0_0_modal_prefix(pm):
    """Migrate MODAL properties to md_ prefix."""
    if pm.mode != 'MODAL':
        return
    # md?confirm=True → md?md_confirm=True
    pm.data = pm.data.replace("confirm=", "md_confirm=")
    pm.data = pm.data.replace("block_ui=", "md_block_ui=")
    pm.data = pm.data.replace("lock=", "md_lock=")

def fix_2_0_0_property_prefix(pm):
    """Migrate PROPERTY properties to pr_ prefix."""
    if pm.mode != 'PROPERTY':
        return
    # prop?vector=3 → pr?pr_vector=3
    pm.data = pm.data.replace("prop?", "pr?")
    pm.data = pm.data.replace("vector=", "pr_vector=")
    pm.data = pm.data.replace("mulsel=", "pr_mulsel=")
    pm.data = pm.data.replace("hor_exp=", "pr_hor_exp=")
    pm.data = pm.data.replace("exp=", "pr_exp=")
    pm.data = pm.data.replace("save=", "pr_save=")
```

---

## Change Summary

### Total Files to Modify

| Category | Files |
|----------|-------|
| Schema | `editors/modal.py`, `editors/property.py`, `core/schema.py` |
| MODAL code | `pme_types.py`, `operators/__init__.py`, `infra/macro.py` |
| PROPERTY code | `editors/property.py`, `operators/__init__.py` |
| Migration | `infra/compat.py` |
| Documentation | `_docs/design/json_schema_v2.md` |

### Risk Matrix

| Mode | Risk | Reason |
|------|------|--------|
| PROPERTY | **LOW** | No collisions, isolated usage |
| MODAL | **MEDIUM** | `confirm` and `lock` have other usages, but patterns are distinguishable |

---

## Recommended Execution Order

1. ✅ Phase 1: Analysis (this document)
2. Phase 2-A: PROPERTY schema + code changes (LOW risk)
3. Phase 2-B: MODAL schema + code changes (MEDIUM risk)
4. Phase 3: Migration functions
5. Phase 4: Test with existing data
6. Phase 5: Update JSON Schema v2 documentation
