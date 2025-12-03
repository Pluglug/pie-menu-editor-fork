# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pie Menu Editor (PME) is a Blender add-on that allows users to create custom UI elements: pie menus, regular menus, popup dialogs, panel groups, sticky keys, stack keys, macro operators, modal operators, and custom properties.

This is a **maintenance fork** of the original PME created by roaoao, maintained by Pluglug with the original developer's approval.

- **Blender Compatibility**: 3.2.0+
- **License**: GPL v3
- **Documentation**: https://pluglug.github.io/pme-docs

## Architecture

### Module Loading Order

The `MODULES` tuple in `__init__.py` defines the import order. Order matters because later modules depend on earlier ones:

```
addon → pme → c_utils → previews_helper → constants → utils → debug_utils →
bl_utils → compatibility_fixes → operator_utils → property_utils → layout_helper →
overlay → modal_utils → macro_utils → ui → panel_utils → screen_utils →
selection_state → keymap_helper → collection_utils → operators → extra_operators →
ui_utils → types → ed_base → ed_* (editors) → preferences
```

### Core Components

- **`pme.py`**: Global execution context (`PMEContext`), property parsing system (`PMEProps`/`ParsedData`). The singleton `pme.context` stores current menu/item state during execution.

- **`types.py`**: Blender PropertyGroups defining data structures:
  - `PMItem`: Menu definition (hotkey, keymap, mode, items collection)
  - `PMIItem`: Menu item (mode, text/command, icon, enabled state)
  - `PMLink`: Tree view node for folder structure
  - `Tag`: Filtering/categorization

- **`preferences.py`**: `PMEPreferences` (AddonPreferences) - stores all menus in `pie_menus` collection, manages editors via `self.ed(mode)`.

### Editor Pattern

Each menu type has a dedicated editor module (`ed_*.py`) that subclasses `EditorBase` from `ed_base.py`:

| Mode | Module | Description |
|------|--------|-------------|
| PMENU | `ed_pie_menu.py` | Pie menus (8+2 fixed slots) |
| RMENU | `ed_menu.py` | Regular dropdown menus |
| DIALOG | `ed_popup.py` | Popup dialogs |
| SCRIPT | `ed_stack_key.py` | Stack keys (sequential actions) |
| PANEL | `ed_panel_group.py` | Panel groups |
| HPANEL | `ed_hpanel_group.py` | Hidden panel groups |
| STICKY | `ed_sticky_key.py` | Sticky key modifiers |
| MACRO | `ed_macro.py` | Macro operators |
| MODAL | `ed_modal.py` | Modal operators |
| PROPERTY | `ed_property.py` | Custom properties |

Editors register via `Editor()` call in their `register()` function. The base class provides:
- `on_pm_add(pm)`: Initialize new menu
- `on_pm_rename(pm, new_name)`: Handle menu rename
- `on_pmi_rename(pm, pmi, old_name, new_name)`: Handle item rename
- `draw_items(layout, pm)`: Draw editor UI

### Item Modes (EMODE_ITEMS)

Menu items can be one of:
- **COMMAND**: Python code executed on click
- **PROP**: Property widget (path evaluated at runtime)
- **MENU**: Submenu or operator reference
- **HOTKEY**: Execute operator bound to a hotkey
- **CUSTOM**: Custom layout drawing code
- **INVOKE/FINISH/CANCEL/UPDATE**: Modal operator callbacks

### Key Utilities

- **`addon.py`**: `get_prefs()` returns PMEPreferences, `temp_prefs()` returns WindowManager.pme
- **`keymap_helper.py`**: `KeymapHelper` class for hotkey registration/management
- **`layout_helper.py`**: `lh` singleton for simplified UI layout building
- **`bl_utils.py`**: Blender API utilities, property parsing, context handling
- **`property_utils.py`**: Serialization (`to_dict`/`from_dict`) for preferences backup

### Data Encoding

Menu data uses URL-like encoding in `PMItem.data`:
```
type?prop1=value1&prop2=value2
```
Parsed via `pme.props.parse(data)` which returns a `ParsedData` object with typed attributes.

### Version Migration

`compatibility_fixes.py` contains versioned fix functions (`fix_X_Y_Z`) that automatically run when upgrading from older versions. JSON import uses `fix_json_X_Y_Z` functions.

## Debugging

Toggle debug flags in `debug_utils.py`:
```python
DBG_INIT = True   # Initialization logging
DBG_LAYOUT = True # UI layout debugging
DBG_TREE = True   # Tree view debugging
# etc.
```

Colored console output: `logi()` (blue), `logw()` (yellow), `loge()` (red), `logh()` (green header)

## Addon Conventions

### Naming
- Operators: `PME_OT_*` or `WM_OT_*`
- Panels: `PME_PT_*`
- Menus: `PME_MT_*`
- PropertyGroups: CamelCase without prefix

### Icons
- Custom icons in `icons/` directory, loaded via `previews_helper.py`
- Icon helper functions: `ic()`, `ic_rb()` (radio), `ic_cb()` (checkbox), `ic_fb()` (folder), `ic_eye()` (visibility)

### Constants
- `CC` alias for `constants` module (common import pattern)
- String length limit: `MAX_STR_LEN = 1024`
- Special flags: `F_EXPAND = "@"`, `F_ICON_ONLY = "#"`, `F_HIDDEN = "!"`

## Safe Mode

Launch Blender with `--pme-safe-mode` to disable menu registration (for debugging crashes).

## Behavior & Safety Rules for Claude

When editing or proposing changes in this repo, you MUST follow these rules:

1. **Do not change external behavior by default.**
   - Do not change user-visible behavior, shortcuts, menu structure, or data formats
     unless the user explicitly requests it.
   - Assume existing PME users have complex setups that must keep working.

2. **No large-scale rewrites.**
   - Do NOT propose redesigning the architecture from scratch.
   - Prefer small, incremental refactors that:
     - keep public APIs and operator names intact
     - keep JSON/config formats compatible

3. **Treat Blender API usage as fragile.**
   - Any code touching `bpy`, contexts, keymaps, handlers, overrides, or custom props
     is HIGH RISK.
   - Prefer to introduce small wrapper functions/modules and refactor call sites
     gradually, rather than changing all call sites at once.

4. **Patch style.**
   - Provide minimal diffs, not full-file rewrites.
   - For each change, state:
     - what problem it solves
     - risk level (low/medium/high)
     - how to manually test it in Blender.

5. **Refactor in steps.**
   - First: understand and summarize the current behavior.
   - Second: propose a step-by-step refactor plan.
   - Third: implement ONE small step at a time as a patch.

## Recommended Workflows (Slash Commands)

The maintainer may start a request with commands like:

### `/pme-overview`
- Summarize main modules and their roles.
- Show a simple dependency diagram.
- Highlight potential design bottlenecks (without changing code).

### `/pme-risks`
- List risky areas:
  - long functions (>200 lines)
  - global state
  - heavy Blender API usage
  - `exec` / `eval`
- For each, explain why it's risky and how to refactor it safely (in theory).

### `/pme-refactor-plan <file-or-module>`
- For a given file (e.g. `addon.py`), propose:
  - step-by-step refactor plan
  - each step small and independently reviewable
- Do NOT output code, only the plan.

### `/pme-refactor-step <file-or-module> <step-id>`
- Implement exactly one step from an existing plan.
- Output a minimal patch (diff-like), with short comments.

### `/pme-api-wrapper-plan`
- Identify Blender API usage hotspots.
- Propose thin wrapper interfaces to isolate version-dependent logic.

### `/pme-tests`
- Suggest which pure-Python parts to test first.
- Provide pytest skeletons for 2–3 critical functions.