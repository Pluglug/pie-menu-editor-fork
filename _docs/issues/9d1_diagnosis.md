# 9-D-1: PROPERTY mode Crash Diagnosis

> **Branch**: `investigate/9d1-property-crash`
> **Related Issue**: #88
> **Status**: Diagnosis complete (no fix implemented)

---

## Summary

The PROPERTY mode crash during v2 import is caused by `poll_cmd` containing `"return True"` instead of a valid property type (`BOOL`, `INT`, `FLOAT`, `STRING`, `ENUM`).

---

## Root Cause

### Direct Cause

`pm.poll_cmd` contains `"return True"` for a PROPERTY mode menu, which is then passed to `prop_by_type()`:

```python
def prop_by_type(prop_type, is_vector=False):
    name = "VectorProperty" if is_vector else "Property"
    name = prop_type.title() + name  # "return True".title() = "Return True"
    return getattr(bpy.props, name)  # AttributeError: 'Return TrueProperty'
```

### Why poll_cmd = "return True"?

The `poll_cmd` field serves **dual purposes** in PME:

| Mode | poll_cmd contains |
|------|-------------------|
| Normal modes | Poll condition (e.g., `"return True"`) |
| PROPERTY mode | Property type (e.g., `"BOOL"`, `"INT"`) |

The default value of `poll_cmd` StringProperty is `CC.DEFAULT_POLL = "return True"`.

When a PROPERTY menu has this default value (due to initialization issues or legacy data), the export faithfully outputs it:

```python
# menu_to_schema (export)
if pm.mode == 'PROPERTY':
    settings['prop_type'] = pm.poll_cmd if pm.poll_cmd else 'BOOL'
    # If poll_cmd = "return True", settings['prop_type'] = "return True"
```

On import, without validation, this corrupted value is restored:

```python
# schema_to_menu (import)
prop_type = schema.settings.get('prop_type', 'BOOL')
pm.poll_cmd = prop_type  # "return True"
```

---

## Call Flow

```
v2 Import Flow:
──────────────────────────────────────────────────────────────

  WM_OT_pm_import._import_v2()
     │
     ├── PME2File.from_dict(data)
     │      └── MenuSchema.from_dict()
     │             └── settings = {"prop_type": "return True"}
     │
     ├── pie_menus.add()             [poll_cmd = "return True" by default]
     ├── pm.mode = 'PROPERTY'
     ├── pm.name = ...
     │
     ├── schema_to_menu(schema, pm)
     │      └── pm.poll_cmd = settings.get('prop_type', 'BOOL')
     │             └── "return True"
     │
     └── pm.ed.init_pm(pm)
            └── register_user_property(pm)
                   └── prop_by_type(pm.poll_cmd, ...)
                          └── "Return TrueProperty"  ← CRASH
```

---

## Affected Locations

| Step | File:Line | Function |
|------|-----------|----------|
| Crash | `editors/property.py:372` | `prop_by_type()` |
| Caller | `editors/property.py:400` | `register_user_property()` |
| Data set | `infra/serializer.py` | `schema_to_menu()` |
| Data source | `infra/serializer.py` | `menu_to_schema()` |

---

## Scenarios That Cause Corruption

1. **Initialization bug**: New PMItem created without `on_pm_add()` being called for PROPERTY mode
2. **Legacy data**: Old PME1 menus that weren't properly initialized
3. **v1 import fallback**: `operators/io.py:183` sets `poll_cmd = menu[7] or CC.DEFAULT_POLL`

---

## Impact

- **v2 roundtrip**: Export → Import crashes
- **Existing data**: PROPERTY menus with `poll_cmd = "return True"` crash on reload
- **Scope**: PROPERTY mode only (other modes use poll_cmd for poll conditions)

---

## Existing Mitigation

Commit `6360f21` added validation in `register_user_property()`:

```python
# Added defensive check
valid_types = {'BOOL', 'INT', 'FLOAT', 'STRING', 'ENUM'}
if prop_type not in valid_types:
    prop_type = 'STRING'  # Fallback
```

However, the **export side** (`menu_to_schema`) still lacks validation.

---

## Recommended Fixes (Reference)

### 1. Export-side validation (serializer.py)

```python
if pm.mode == 'PROPERTY':
    valid_types = {'BOOL', 'INT', 'FLOAT', 'STRING', 'ENUM'}
    prop_type = pm.poll_cmd if pm.poll_cmd in valid_types else 'BOOL'
    settings['prop_type'] = prop_type
    poll = "return True"
```

### 2. Import-side validation (serializer.py)

Already implemented in `schema_to_menu()`:

```python
valid_types = {'BOOL', 'INT', 'FLOAT', 'STRING', 'ENUM'}
if prop_type not in valid_types:
    prop_type = 'BOOL'
```

### 3. Defensive check in register_user_property()

```python
def register_user_property(pm):
    valid_types = {'BOOL', 'INT', 'FLOAT', 'STRING', 'ENUM'}
    if pm.poll_cmd not in valid_types:
        DBG_PROP and logh(f"Invalid prop_type '{pm.poll_cmd}', using BOOL")
        pm.poll_cmd = 'BOOL'
    # ... rest of function
```

---

## Investigation Notes

- Searched for "Return True" (capital R) - not found in code; produced by `.title()`
- `mode` EnumProperty has no update callback, so setting mode doesn't trigger initialization
- Default value `CC.DEFAULT_POLL = "return True"` in `core/constants.py:169`
- Validation commit: `6360f21 Fix: validate poll_cmd as property type before registration`
