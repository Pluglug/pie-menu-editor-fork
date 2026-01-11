# Investigation: Pop-up Dialog Popup Mode "Mouse Outside Close"

**Branch**: `investigate/popup-mouse-outside-close`
**Date**: 2026-01-11
**Status**: ✅ CLOSED - WONTFIX (Blender Behavior + Blender 5.0 Breaking Change)
**Issue**: #96
**Reporter**: [cartorolle's blog](https://note.com/cartorolle/n/n70dd6de8c33e)

## Summary

Pop-up Dialog in Popup mode does not close when moving mouse outside the popup, despite the original PME Wiki documentation stating "Moving the mouse outside the pop-up closes it".

**Root Cause**: This feature was never fully implemented in the original PME. Additionally, Blender 5.0 introduced breaking changes to internal C structures that make ctypes-based workarounds impossible.

**Resolution**: WONTFIX - Document the actual behavior.

---

## Investigation Timeline

### Phase 1: Initial Analysis

**Objective**: Determine if this is a PME bug or missing feature.

**Findings**:
1. **Property exists but unused** (`pme_types.py:670-675`):
   ```python
   pd_auto_close: bpy.props.BoolProperty(
       name="Auto Close on Mouse Out",
       description="Auto close on mouse out",
   )
   ```

2. **Property never shown in UI** - `draw_extra_settings` does not include `pd_auto_close`

3. **Logic uses mode check, not property** (`operators/__init__.py:1817-1823`):
   ```python
   auto_close=prop.pd_panel == 2,  # Mode check, not pd_auto_close
   ```

4. **Initial commit analysis** (`c221f40`) - Same structure since fork began:
   - Property defined but not used
   - No modal handler for mouse tracking
   - `invoke_popup` used (click-to-close only)

**Conclusion**: Feature was **planned but never implemented** in the forked version.

### Phase 2: Blender Source Analysis

**Objective**: Understand Blender's popup mechanism and potential workarounds.

**Key Discovery**: `UI_BLOCK_MOVEMOUSE_QUIT` flag exists in Blender:

```c
// source/blender/editors/include/UI_interface_c.hh:167
UI_BLOCK_MOVEMOUSE_QUIT = 1 << 5,  // = 32
```

**invoke_popup behavior**:
```c
// source/blender/windowmanager/intern/wm_operators.cc:1691
UI_block_flag_enable(block, UI_BLOCK_KEEP_OPEN | UI_BLOCK_MOVEMOUSE_QUIT);
```

Both flags are set, but `UI_BLOCK_KEEP_OPEN` takes precedence, preventing mouse-outside closure.

### Phase 3: Blender 5.0 Testing

**Objective**: Verify actual behavior and test ctypes workaround.

**Test Addon Created**: `test_popup_behavior.py`

**Results**:

| Test | Expected (Wiki) | Actual (Blender 5.0.1) |
|------|-----------------|------------------------|
| `invoke_popup()` | Mouse outside closes | ❌ **Does NOT close** |
| `invoke_props_dialog()` | Click/OK closes | ✅ Works as expected |

**ctypes Test Result**: **HARD CRASH** - Access violation in `_ctypes.pyd`

### Phase 4: Blender 5.0 Structure Analysis (Critical Finding)

**Objective**: Investigate ctypes crash cause.

**Discovery**: Blender 5.0 has **C++ modernized** the `uiBlock` structure!

**Blender 4.x (PME c_utils.py assumes)**:
```c
struct uiBlock {
    uiBlock *next, *prev;
    ListBase buttons;              // C struct, 16 bytes
    Panel *panel;
    uiBlock *oldblock;
    ListBase butstore;
    ListBase layouts;
    void *curlayout;
    ListBase contexts;             // C struct, 16 bytes
    char name[128];                // Fixed size array
    float winmat[4][4];
    rctf rect;
    float aspect;
    uint puphash;
    // ... function pointers ...
    int flag;                      // ← Target field
};
```

**Blender 5.0 (Actual)**:
```cpp
struct uiBlock {
    uiBlock *next, *prev;
    blender::Vector<std::unique_ptr<uiBut>> buttons;  // C++ STL!
    Panel *panel;
    uiBlock *oldblock;
    ListBase butstore;
    blender::Vector<uiButtonGroup> button_groups;     // NEW!
    ListBase layouts;
    blender::ui::Layout *curlayout;
    blender::Vector<std::unique_ptr<bContextStore>> contexts;  // C++ STL!
    ListBase views;                                   // NEW!
    ListBase dynamic_listeners;                       // NEW!
    std::string name;                                 // Variable size!
    float winmat[4][4];
    rctf rect;
    float aspect;
    uiBlockAlertLevel alert_level;                    // NEW!
    uint puphash;
    // ... function pointers ...
    std::function<void(...)> drawextra;               // C++ std::function!
    int flag;                                         // ← Offset completely changed!
};
```

**Impact**:
- `std::string`, `blender::Vector`, `std::function` are **variable-size** C++ types
- Field offsets are **completely different** from Blender 4.x
- **ctypes cannot safely access `uiBlock.flag`** in Blender 5.0
- PME's `c_utils.py` functions like `keep_pie_open()` are **broken** in Blender 5.0

---

## Official Documentation (PME Wiki)

From [Blender Archive Wiki - PME Pop-up Dialog](https://archive.blender.org/wiki/index.php/User:Raa/Addons/Pie_Menu_Editor/Editors/Popup_Dialog):

| Mode | Mouse Outside | Widget Interaction | OK Button |
|------|---------------|-------------------|-----------|
| **Pie Mode** | Does NOT close | Closes | No |
| **Dialog Mode** | Does NOT close | Does NOT close | Yes |
| **Popup Mode** | **Closes automatically** | Does NOT close | No |

> **Popup Mode**: "Moving the mouse outside the pop-up closes it" automatically.

**Note**: This documentation was written for Blender 2.7x-2.8x era. The feature may have worked differently in older versions, or the documentation described intended behavior that was never fully implemented.

---

## Final Conclusion

### Root Causes

1. **Never Implemented**: The `pd_auto_close` property exists since the original fork but was never connected to actual functionality
2. **Blender Behavior**: Even if attempted via ctypes, `UI_BLOCK_KEEP_OPEN` overrides `UI_BLOCK_MOVEMOUSE_QUIT`
3. **Blender 5.0 Breaking Change**: C++ modernization of `uiBlock` makes ctypes workarounds impossible

### Why WONTFIX

| Approach | Feasibility | Reason |
|----------|-------------|--------|
| ctypes flag manipulation | ❌ Impossible | Blender 5.0 broke structure compatibility |
| Modal mouse tracking | ⚠️ High effort | Complex, popup bounds not exposed, may conflict with Blender |
| Blender API change | ❌ Not feasible | Would require Blender core changes |
| Documentation update | ✅ Recommended | Match docs to actual behavior |

### Recommendations

1. **Update documentation**: Change Popup Mode description from "mouse outside closes" to "click outside to close"
2. **Consider removing `pd_auto_close`**: Unused property since initial commit
3. **Note for c_utils.py**: Blender 5.0 compatibility requires full structure audit

---

## Files Involved

| File | Lines | Purpose |
|------|-------|---------|
| `pme_types.py` | 670-675 | `pd_auto_close` property definition |
| `core/schema.py` | 237 | Schema default |
| `editors/popup.py` | 101, 1780-1800 | Schema registration, UI |
| `operators/__init__.py` | 1814-1825 | Invocation logic |
| `bl_utils.py` | 486-489 | `PopupOperator.invoke()` |
| `c_utils.py` | 816-820 | `keep_pie_open()` - **broken in Blender 5.0** |

## Related Resources

- [PME Wiki - Pop-up Dialog](https://archive.blender.org/wiki/index.php/User:Raa/Addons/Pie_Menu_Editor/Editors/Popup_Dialog)
- [User report (cartorolle's blog)](https://note.com/cartorolle/n/n70dd6de8c33e)
- Blender API: `WindowManager.invoke_popup()`
- Blender Source: `source/blender/editors/interface/interface_intern.hh:592` (uiBlock struct)

## Test Artifacts

- `test_popup_behavior.py` - Standalone test addon (in addons folder, can be deleted)
- Branch: `investigate/popup-mouse-outside-close`
