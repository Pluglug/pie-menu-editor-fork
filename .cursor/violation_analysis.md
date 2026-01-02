# PME2 Layer Violation Analysis

Generated from: `.cursor/debug.log` (DBG_DEPS=True, DBG_STRUCTURED=True)
Analysis date: 2026-01-01
Total modules loaded: 54
Load order: Topologically sorted by new loader

---

## Violation Summary

```
Total violations: 49
By severity:
  - High (cross >2 layers): 0
  - Medium (cross 1-2 layers): 49
  - Low (within layer): 0
```

**Note**: All violations are classified as Medium because they cross 1-2 layers. The PME2 layer structure considers these violations acceptable during the migration period.

---

## Violations by Pattern

### Pattern 1: `legacy → *` (32 violations)

Legacy wrapper modules importing from new layer structure. **Intentionally allowed** for backward compatibility.

#### `addon` → (21 violations)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `addon` | `editors.panel_group` | legacy | editors | Low (wrapper) |
| `addon` | `editors.popup` | legacy | infra | Low (wrapper) |
| `addon` | `property_utils` | legacy | infra | Low (wrapper) |
| `addon` | `editors.base` | legacy | infra | Low (wrapper) |
| `addon` | `ui.layout` | legacy | infra | Low (wrapper) |
| `addon` | `ui.utils` | legacy | ui | Low (wrapper) |
| `addon` | `core.constants` | legacy | core | Low (wrapper) |
| `addon` | `editors.hpanel_group` | legacy | operators | Low (wrapper) |
| `addon` | `ui.screen` | legacy | ui | Low (wrapper) |
| `addon` | `editors.property` | legacy | infra | Low (wrapper) |
| `addon` | `ui.panels` | legacy | infra | Low (wrapper) |
| `addon` | `preferences` | legacy | infra | Low (wrapper) |
| `addon` | `macro_utils` | legacy | infra | Low (wrapper) |
| `addon` | `compatibility_fixes` | legacy | infra | Low (wrapper) |
| `addon` | `keymap_helper` | legacy | infra | Low (wrapper) |
| `addon` | `bl_utils` | legacy | infra | Low (wrapper) |
| `addon` | `pme_types` | legacy | core | Low (wrapper) |
| `addon` | `editors.pie_menu` | legacy | editors | Low (wrapper) |
| `addon` | `editors.menu` | legacy | editors | Low (wrapper) |

#### `previews_helper` → (3 violations)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `previews_helper` | `core.constants` | legacy | core | Low (wrapper) |
| `previews_helper` | `preferences` | legacy | infra | Low (wrapper) |
| `previews_helper` | `ui.layout` | legacy | infra | Low (wrapper) |

#### `modal_utils` → (1 violation)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `modal_utils` | `preferences` | legacy | infra | Low (wrapper) |

#### `extra_operators` → (2 violations)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `extra_operators` | `editors.property` | legacy | infra | Low (wrapper) |
| `extra_operators` | `editors.panel_group` | legacy | editors | Low (wrapper) |

#### `utils` → (1 violation)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `utils` | `ui.layout` | legacy | infra | Low (wrapper) |

#### `pme` → (1 violation)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `pme` | `pme_types` | legacy | core | Low (wrapper) |

#### `overlay` → (1 violation)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `overlay` | `preferences` | legacy | infra | Low (wrapper) |

#### `ed_modal` → (1 violation)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `ed_modal` | `preferences` | legacy | infra | Low (wrapper) |

#### `ed_sticky_key` → (1 violation)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `ed_sticky_key` | `preferences` | legacy | infra | Low (wrapper) |

#### `layout_helper` → (1 violation)

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `layout_helper` | `ui.utils` | legacy | ui | Low (wrapper) |

---

### Pattern 2: `infra → ui` (2 violations)

Infrastructure layer importing from UI layer. **Medium risk** - genuine layer violation.

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `bl_utils` | `ui.screen` | infra | ui | Medium |
| `editors.base` | `ui.screen` | infra | ui | Medium |

**Root cause**: `ui.screen` (screen manipulation utilities) should be in `infra` layer.

**Proposed fix** (Phase 2-B candidate):
1. Move `ui.screen` → `infra.screen`
2. Update imports in `bl_utils`, `editors.base`
3. Add re-export wrapper in `ui.screen` for backward compatibility

---

### Pattern 3: `editors → operators` (5 violations)

Editors importing from operators layer. **Currently allowed** per `rules/architecture.md`, but should be reviewed in Phase 3.

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `editors.panel_group` | `operators` | editors | operators | Medium |
| `editors.popup` | `operators` | editors | operators | Medium |
| `editors.base` | `operators` | editors | operators | Medium |
| `pme_types` | `operators` | core | operators | High (!) |
| `ui.utils` | `operators` | ui | operators | Medium |

**Root cause**: Editors use operator helper functions for UI drawing.

**Proposed fix** (Phase 3):
- Extract operator interfaces to `ui/operator_ui.py`
- Editors depend on `ui/operator_ui.py`, not `operators` directly

---

### Pattern 4: `infra → ui` via `editors.base` (7 violations)

Editors base class (mis-classified as `infra`) importing from UI layer.

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `editors.property` | `ui` | infra | ui | Medium |
| `editors.popup` | `ui` | infra | ui | Medium |
| `editors.base` | `ui` | infra | ui | Medium |
| `pme_types` | `ui` | core | ui | High (!) |
| `ui.panels` | `ui` | infra | ui | Low |
| `preferences` | `ui` | infra | ui | Medium |

**Root cause**: `editors.base`, `editors.property`, `editors.popup` are classified as `infra` by the layer resolver, but should be `editors`.

**Proposed fix** (Phase 2-B):
- Update `resolve_layer()` in `infra/debug.py` to correctly classify `editors.*` as `editors` layer

---

### Pattern 5: `core → *` (5 violations)

Core layer importing from higher layers. **High risk** - genuine violations.

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `pme_types` | `operators` | core | operators | High |
| `pme_types` | `ui` | core | ui | High |
| `pme_types` | `ui.utils` | core | ui | High |
| `ui.panels` | `pme_types` | infra | core | Low (reverse) |

**Root cause**: `pme_types` (core model) imports UI/operator utilities for drawing methods.

**Proposed fix** (Phase 3):
1. Move drawing methods from `pme_types` to `ui/model_ui.py`
2. `pme_types` becomes pure data model (no UI dependencies)
3. UI layer uses `model_ui.py` for drawing

---

### Pattern 6: `ed_panel_group` → `preferences` (1 violation)

Legacy wrapper importing from preferences.

| Source | Target | Layer Source | Layer Target | Risk |
|--------|--------|-------------|--------------|------|
| `ed_panel_group` | `preferences` | editors | infra | Medium |

**Root cause**: Legacy wrapper path. Should be removed in RC phase.

---

## Violations by Source Module

### High Priority (Phase 2-B)

#### `pme_types` (core layer) → 4 violations

**Imports from higher layers** (core → operators, core → ui):

```python
# pme_types.py imports:
from .operators import ...        # core → operators (HIGH RISK)
from .ui import ...               # core → ui (HIGH RISK)
from .ui.utils import ...         # core → ui (HIGH RISK)
```

**Fix**: Extract UI/operator logic to separate modules. Phase 3 task.

---

#### `bl_utils`, `editors.base` (infra layer) → 2 violations

**Imports from ui.screen**:

```python
# bl_utils.py, editors/base.py import:
from .ui.screen import ...        # infra → ui (MEDIUM RISK)
```

**Fix**: Move `ui.screen` → `infra.screen`. **Phase 2-B candidate** (Low risk).

---

### Medium Priority (Phase 3)

#### `editors/*` → operators (5 violations)

Editors importing operator helpers for UI drawing.

**Fix**: Interface separation. Phase 3 task.

---

### Low Priority (Cleanup after RC)

#### `addon`, `previews_helper`, etc. → * (32 violations)

Legacy wrappers for backward compatibility. **Intentionally allowed**.

**Fix**: Remove in RC after confirming no external dependencies.

---

## Dependency Cycles

**None detected**. Topological sort succeeded without `force_order` intervention.

---

## Load Order Summary

**Linear load sequence** (54 modules, topologically sorted):

```
Layer: core (0)
  1. core.constants
  2. core

Layer: infra (1)
  3. addon
  4. bl_utils
  5. c_utils
  6. collection_utils
  7. compatibility_fixes
  8. constants (legacy wrapper)
  9. debug_utils (legacy wrapper)
  10. layout_helper (legacy wrapper)
  11. screen_utils (legacy wrapper)
  12. panel_utils (legacy wrapper)
  13. ui_utils (legacy wrapper)
  14. collection_utils (legacy wrapper)
  15. infra.debug
  16. infra.collections
  17. pme_types (core model, mis-classified)
  18. property_utils
  19. pme
  20. keymap_helper
  21. macro_utils
  22. modal_utils
  23. selection_state
  24. operator_utils
  25. previews_helper

Layer: ui (2)
  26. ui
  27. ui.screen
  28. ui.panels
  29. ui.layout
  30. ui.utils
  31. ui.lists

Layer: editors (3)
  32. editors
  33. editors.base
  34. editors.pie_menu
  35. editors.menu
  36. editors.popup
  37. editors.panel_group
  38. editors.hpanel_group
  39. editors.property
  40. ed_base (legacy wrapper)
  41. ed_pie_menu (legacy wrapper)
  42. ed_menu (legacy wrapper)
  43. ed_popup (legacy wrapper)
  44. ed_panel_group (legacy wrapper)
  45. ed_hpanel_group (legacy wrapper)
  46. ed_property (legacy wrapper)
  47. ed_sticky_key (legacy wrapper)
  48. ed_stack_key (legacy wrapper)
  49. ed_macro (legacy wrapper)
  50. ed_modal (legacy wrapper)

Layer: operators (4)
  51. operators
  52. extra_operators

Layer: prefs (5)
  53. preferences
  54. __init__
```

**Note**: `force_order` was empty during this run. All modules were sorted purely by dependency analysis.

---

## Recommendations

### Phase 2-B (alpha.2) — Low Risk Fixes (3-5 violations)

**Candidate fixes** (based on `rules/dependency_cleanup_plan.md`):

1. **Move `ui.screen` → `infra.screen`** (2 violations)
   - Risk: Low (pure refactoring)
   - Impact: `bl_utils`, `editors.base`
   - Add backward compatibility wrapper at `ui.screen`

2. **Fix `resolve_layer()` classification** (7 violations)
   - Risk: Very Low (debug tool only)
   - Update `infra/debug.py` to correctly classify `editors.*` as `editors` layer
   - This will reduce false-positive violations

3. **Add explicit imports in `editors/hpanel_group.py`** (1 violation)
   - Replace `from ..operators import *` with explicit imports
   - Risk: Very Low
   - Reference: `rules/dependency_cleanup_plan.md`

**Total**: 10 violations resolved (3-5 is the target, so pick 1-2 of these)

---

### Phase 3-A (beta.1) — props/ParsedData周辺 (5-10 violations)

1. **Extract `pme_types` UI logic** (4 violations)
   - Move drawing methods from `pme_types` to `ui/model_ui.py`
   - Risk: Medium (requires careful testing)
   - Resolves: `pme_types → operators`, `pme_types → ui`

2. **Interface separation for `editors → operators`** (5 violations)
   - Extract operator UI helpers to `ui/operator_ui.py`
   - Risk: Medium
   - Resolves: `editors.* → operators`

**Total**: 9 violations resolved

---

### Phase 3-B (beta.2) — handlers/previews周辺 (5-10 violations)

No direct violations related to handlers/previews in this snapshot.

**Cleanup tasks**:
- Remove legacy wrappers (`ed_*.py`, `addon → *` re-exports)
- Document remaining intentional violations in `rules/allowed_violations.md`

---

### RC — 残りを棚卸し

**Remaining violations to document as "allowed"**:

| Pattern | Count | Reason |
|---------|-------|--------|
| `legacy → *` | 32 | Backward compatibility wrappers (remove in v2.1) |
| `prefs → *` | Various | `prefs` is the hub layer (allowed by design) |

**Final target**: <20 violations (excluding intentional wrappers)

---

## Context from Rules

### Layer Structure (from `rules/architecture.md`)

```
prefs      (5) ← アドオン設定、全体のハブ
operators  (4) ← 編集・検索・ユーティリティ系オペレーター
editors    (3) ← 各モード（PMENU/RMENU/DIALOG等）のエディタロジック
ui         (2) ← LayoutHelper, UIList, menus, popups
infra      (1) ← Blender 依存の基盤（pme.context, overlay, keymap）
core       (0) ← Blender 非依存のロジック・データ構造
```

**Allowed**: 上位 → 下位のみ
**Forbidden**: 下位 → 上位

---

## Caveats

1. **Layer classification issues**: Some modules (`editors.base`, `pme_types`) are mis-classified by `resolve_layer()`. This inflates the violation count artificially.

2. **Legacy wrappers dominate**: 32/49 (65%) violations are legacy wrapper imports, intentionally allowed for backward compatibility.

3. **Actual structural violations**: ~10-15 violations are genuine architectural issues requiring Phase 3 fixes.

---

## How to Update This Analysis

```bash
# In Blender Python console:
from pie_menu_editor.infra.debug import set_debug_flag
set_debug_flag("deps", True)
set_debug_flag("structured", True)

# Restart Blender or reload addon
# Then run this analysis script
```

---

## References

- `rules/architecture.md` — Layer structure definition
- `rules/dependency_cleanup_plan.md` — Violation cleanup roadmap
- `rules/milestones.md` — Phase plan
- `infra/debug.py` — `detect_layer_violations()`, `resolve_layer()`
