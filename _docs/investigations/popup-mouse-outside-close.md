# Investigation: Pop-up Dialog Popup Mode "Mouse Outside Close"

**Branch**: `investigate/popup-mouse-outside-close`
**Date**: 2026-01-11
**Status**: Root Cause Identified

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

## Conclusion

**This is a missing feature, not a bug.** The documentation describes intended behavior that was never fully implemented. The `pd_auto_close` property exists as a remnant of this planned feature.

### Action Items

1. [ ] Decide: Implement feature OR update documentation
2. [ ] If implementing: Create modal wrapper for mouse tracking
3. [ ] If not implementing: Remove `pd_auto_close` and update docs
4. [ ] Update Wiki/documentation to match actual behavior
