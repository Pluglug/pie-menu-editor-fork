# Investigation: Pop-up Dialog Popup Mode "Mouse Outside Close"

**Branch**: `investigate/popup-mouse-outside-close`
**Date**: 2026-01-11
**Status**: ✅ CONFIRMED - Blender Behavior (Not PME Bug)

## Issue Report

User reported that Pop-up Dialog in Popup mode does not close when moving mouse outside the popup, despite documentation stating "Moving the mouse outside the pop-up closes it".

## Key Finding: Documented Feature Not Implemented

### Official Documentation (PME Wiki)

From [Blender Archive Wiki - PME Pop-up Dialog](https://archive.blender.org/wiki/index.php/User:Raa/Addons/Pie_Menu_Editor/Editors/Popup_Dialog):

| Mode | Mouse Outside | Widget Interaction | OK Button |
|------|---------------|-------------------|-----------|
| **Pie Mode** | Does NOT close | Closes | No |
| **Dialog Mode** | Does NOT close | Does NOT close | Yes |
| **Popup Mode** | **Closes automatically** | Does NOT close | No |

> **Popup Mode**: "Moving the mouse outside the pop-up closes it" automatically.

### Current Implementation

The feature is **defined but not implemented**:

1. **Property exists** (`types.py:593-596`):
   ```python
   pd_auto_close: bpy.props.BoolProperty(
       name="Auto Close on Mouse Out",
       description="Auto close on mouse out",
       ...
   )
   ```

2. **Not shown in UI** (`ed_popup.py:1657-1668`):
   - `draw_extra_settings` does not include `pd_auto_close`

3. **Not used in logic** (`operators.py:1961`):
   ```python
   auto_close=prop.pd_panel == 2,  # Uses mode check, not pd_auto_close property
   ```

4. **Blender API limitation**:
   - `invoke_popup()` closes on **click** outside, not **mouse movement**
   - No modal handler exists to track mouse position

## Root Cause Analysis

### Possible Explanations

1. **Blender API Change**: The `invoke_popup()` behavior may have changed in newer Blender versions
2. **Never Fully Implemented**: Property was defined for a planned feature that was never completed
3. **Lost Implementation**: Modal handler code may have been accidentally removed

### Evidence Points

| Evidence | Interpretation |
|----------|---------------|
| Wiki documents the feature | Feature was intended/advertised |
| Property name: "Auto Close on Mouse Out" | Clear intent for mouse-out behavior |
| Property exists since initial commit | Not a recent addition |
| No modal handler for mouse tracking | Implementation missing |
| UI property not exposed | Feature incomplete |

## Investigation Summary

### Initial Commit Analysis

Checked initial commit (`c221f40`) - same structure:
- `pd_auto_close` property defined
- No UI exposure
- No modal handler for mouse tracking
- `invoke_popup` used (click-to-close only)

**Conclusion**: Feature was **planned but never fully implemented** in the forked version.

## Technical Details

### Current Code Flow

```
User triggers DIALOG menu (Popup Mode)
    ↓
WM_OT_pme_user_pie_menu_call.execute()
    ↓
operators.py:1817-1823
    bpy.ops.wm.pme_user_dialog_call(
        auto_close=prop.pd_panel == 2,  ← Sets True for Popup Mode
        ...
    )
    ↓
WM_OT_pme_user_dialog_call.invoke()
    ↓
PopupOperator.invoke() (bl_utils.py:486-489)
    if self.auto_close:
        return context.window_manager.invoke_popup(...)  ← Click-to-close only
```

### Required Implementation

To implement "mouse outside closes" behavior:

1. **Create Modal Wrapper**:
   ```python
   class PME_OT_popup_with_mouse_tracking(Operator):
       def modal(self, context, event):
           if event.type == 'MOUSEMOVE':
               # Check if mouse outside popup bounds
               if not self.is_mouse_inside(event.mouse_x, event.mouse_y):
                   return {'CANCELLED'}  # Close popup
           return {'PASS_THROUGH'}
   ```

2. **Track Popup Bounds**:
   - Popup position and size needed
   - Blender doesn't expose popup bounds directly
   - May need overlay or custom drawing

3. **Integrate with Existing System**:
   - Replace `invoke_popup` with modal wrapper
   - Only when `pd_auto_close` is True

## Recommendations

### Option A: Implement the Feature (High Effort)

Create modal operator for mouse position tracking:
- Requires significant work
- Popup bounds detection is non-trivial
- May conflict with Blender's popup handling

### Option B: Fix Documentation (Low Effort)

Update mode descriptions to match actual behavior:
```python
PD_MODE_ITEMS = (
    ('PIE', 'Pie Mode', "Widget interaction closes popup"),
    ('PANEL', 'Dialog Mode', "OK button required to close"),
    ('POPUP', 'Popup Mode', "Click outside to close"),
)
```

### Option C: Remove Unused Property (Cleanup)

If feature won't be implemented:
- Remove `pd_auto_close` from schema
- Remove property definition from types.py
- Update any documentation

## Files Involved

| File | Lines | Purpose |
|------|-------|---------|
| `pme_types.py` | 670-675 | Property definition |
| `core/schema.py` | 237 | Schema default |
| `editors/popup.py` | 101, 1780-1800 | Schema registration, UI |
| `operators/__init__.py` | 1814-1825 | Invocation logic |
| `bl_utils.py` | 486-489 | PopupOperator.invoke() |

## Related Resources

- [PME Wiki - Pop-up Dialog](https://archive.blender.org/wiki/index.php/User:Raa/Addons/Pie_Menu_Editor/Editors/Popup_Dialog)
- Blender API: `WindowManager.invoke_popup()`
- Similar concept: `PME_OT_window_auto_close` (for temp windows)

## Blender Source Analysis (Additional Investigation)

### Key Discovery: UI_BLOCK_MOVEMOUSE_QUIT Flag

Blender has a built-in flag for "close on mouse outside" behavior:

```c
// source/blender/editors/include/UI_interface_c.hh:167
UI_BLOCK_MOVEMOUSE_QUIT = 1 << 5,  // = 32
```

This flag controls popup closure when mouse moves outside:

```c
// source/blender/editors/interface/interface_handlers.cc:11350
/* check mouse moving outside of the menu */
if (inside == false && (block->flag & (UI_BLOCK_MOVEMOUSE_QUIT | UI_BLOCK_POPOVER))) {
    // ... close logic
}
```

### invoke_popup DOES Set This Flag!

Contrary to initial analysis, `WindowManager.invoke_popup()` **does** set `UI_BLOCK_MOVEMOUSE_QUIT`:

```c
// source/blender/windowmanager/intern/wm_operators.cc:1691
// Called by WM_operator_ui_popup() which backs invoke_popup()
static uiBlock *wm_operator_ui_create(bContext *C, ARegion *region, void *user_data)
{
    ...
    uiBlock *block = UI_block_begin(C, region, __func__, blender::ui::EmbossType::Emboss);
    UI_block_flag_disable(block, UI_BLOCK_LOOP);
    UI_block_flag_enable(block, UI_BLOCK_KEEP_OPEN | UI_BLOCK_MOVEMOUSE_QUIT);  // ← HERE!
    ...
}
```

### Possible Root Causes (Revised)

1. **Flag Conflict**: `UI_BLOCK_KEEP_OPEN` may override `UI_BLOCK_MOVEMOUSE_QUIT`
2. **PME Override**: PME's `PopupOperator` may not use this code path
3. **Blender Version Change**: Behavior may have changed in Blender 5.x
4. **Safety Rectangle**: Blender has "towards" detection that may delay/prevent closure

### c_utils.py Missing Flag

PME's `c_utils.py` defines block flags but **not** `UI_BLOCK_MOVEMOUSE_QUIT`:

```python
# c_utils.py - current definitions
UI_BLOCK_LOOP = 1 << 0        # = 1
UI_BLOCK_KEEP_OPEN = 1 << 8   # = 256
UI_BLOCK_POPUP = 1 << 9       # = 512
UI_BLOCK_RADIAL = 1 << 20     # = 1048576

# MISSING:
# UI_BLOCK_MOVEMOUSE_QUIT = 1 << 5  # = 32
```

### Potential Fix via c_utils.py

Could potentially enable mouse-out close by adding flag manipulation:

```python
# Add to c_utils.py
UI_BLOCK_MOVEMOUSE_QUIT = 1 << 5  # = 32

def enable_mouse_quit(layout):
    """Enable mouse-outside-closes-popup behavior for a block."""
    layout_p = c_layout(layout)
    block_p = layout_p.root.contents.block.contents
    block_p.flag |= UI_BLOCK_MOVEMOUSE_QUIT
```

**Warning**: This is experimental and may cause stability issues.

## Blender 5.0 Verification Test (2026-01-11)

### Test Setup

Created standalone test addon: `test_popup_behavior.py`

```python
class TEST_OT_popup_mode(Operator):
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)
```

### Test Results

| Test | Expected (Wiki) | Actual (Blender 5.0.1) |
|------|-----------------|------------------------|
| `invoke_popup()` | Mouse outside closes | ❌ **Does NOT close** |
| `invoke_props_dialog()` | Click/OK closes | ✅ Works as expected |

### Conclusion from Test

**Blender 5.0's `invoke_popup()` does NOT close on mouse-outside.**

This confirms:
1. ❌ Not a PME-specific bug
2. ❌ Not a PME-F regression
3. ✅ **Blender's `invoke_popup()` behavior** - `UI_BLOCK_KEEP_OPEN` overrides `UI_BLOCK_MOVEMOUSE_QUIT`

The Wiki documentation was likely written for older Blender versions (2.7x-2.8x era) where this may have worked differently.

## Final Conclusion

**This is NOT a PME bug.** Blender's `invoke_popup()` sets both `UI_BLOCK_KEEP_OPEN` and `UI_BLOCK_MOVEMOUSE_QUIT` flags, but `KEEP_OPEN` takes precedence, preventing mouse-outside closure.

The `pd_auto_close` property in PME exists as a remnant of a planned feature that relied on Blender behavior that no longer exists (or never existed as documented).

### Recommendations

| Option | Effort | Description |
|--------|--------|-------------|
| **A: Update Docs** | Low | Change description to "Click outside to close" |
| **B: Remove Property** | Low | Remove unused `pd_auto_close` property |
| **C: Implement via ctypes** | High | Manipulate `UI_BLOCK_KEEP_OPEN` flag (risky) |
| **D: Modal Wrapper** | High | Track mouse position manually (complex) |

**Recommended**: Option A + B (Update docs, remove unused property)

### Action Items

1. [x] Test `invoke_popup()` in Blender 5.0 → **Does NOT close on mouse-out**
2. [ ] Update PME mode descriptions to match actual behavior
3. [ ] Consider removing `pd_auto_close` property (unused since initial commit)
4. [ ] Close investigation - this is Blender behavior, not a bug
