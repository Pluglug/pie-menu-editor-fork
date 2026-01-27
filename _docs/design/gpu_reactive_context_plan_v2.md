# PME GPU Layout Reactive Context Plan v2
#
# Purpose:
# - Provide a predictable execution model for user scripts in PME
# - Enable GPU layout to track bpy.context in real time
# - Avoid stale references and crashes on deleted data
#
# Status: Draft
# Created: 2026-01-17
# Related: Issue #104 (GPU Panel)
# Source context:
# - infra/runtime_context.py
# - core/namespace.py
# - editors/base.py
# - bl_utils.py (BlContext)
# - ui/gpu/*
# - _docs/design/gpu_reactive_context_plan_v2_review.md

## 1. Background

PME exposes a Python execution namespace for user-defined commands and custom
tabs. The namespace currently includes:

- L: UILayout-like object for drawing
- C: Blender context (or proxy)
- E: Event
- text, icon, icon_value, U, etc.

The GPU layout system in ui/gpu aims to replace Blender UILayout for custom
tabs by providing a GPU-based layout object (L) that users can draw into.
We also want C (context) to be up to date and predictable while scripts run.
Long-term, L should be interchangeable with bpy.types.UILayout in user code,
so users do not need to detect or special-case GPU layout.

Current pain points:

- The GPU draw handler receives a context argument only once, so it does not
  update automatically.
- ui/gpu bindings hold concrete data objects, so selection changes lead to
  stale references.
- Sync logic has no epoch cache and may repeat work within the same tick.

This plan focuses on a "resync, not rebuild" model with explicit, predictable
execution frames.

## 2. Goals

- Real-time tracking of bpy.context for GPU layout
- Predictable script execution:
  - During one script run, C and L are stable and consistent
  - Between runs, C reflects latest bpy.context
- Avoid stale references to data that can be deleted
- Minimize rebuilds; resync should be the default
- Keep namespace behavior consistent with core/namespace.py
- Long-term: GPU layout covers the full bpy.types.UILayout method surface so
  users do not need to change scripts
- No new public API for reactive bindings; L.prop(...) remains the user entry

## 3. Non-goals

- Immediate full parity with all Blender UILayout widgets (phased delivery)
- Guarantee of zero per-frame work (resync is acceptable)
- Replacing bpy.context; users can still access bpy.context directly

## 4. Constraints

- GPU draw handlers do not provide live context; must resolve bpy.context
  inside draw and modal paths.
- Modal events and draw calls are not in lockstep.
- User scripts can run arbitrary Python, so the execution environment must
  be stable and explicit.

## 5. Terminology

- Execution Frame: A single PME script execution with stable C/L/E.
- Draw Frame: A single GPU draw callback.
- Epoch (tick): An incremented counter per update cycle; used for caching.
- Resolver: A callable that maps (context) -> data (no stored object).

## 6. Design Overview

We introduce four core concepts:

1) ExecutionFrame: sets L/C/E (and an optional bpy proxy) for a single script run.
2) ContextTracker + TrackedAccess: wraps bl_context and records "context.*" access paths.
3) ContextResolverCache: resolves "context.*" against live bpy.context with per-epoch caching.
4) PropertyBinding: stores resolver + setter + widget meta; never stores data objects.

BlContext is left unchanged. GPU-specific behavior is added via wrappers.

### 6.1 ExecutionFrame

Goal: make L/C/E stable and predictable while a user script runs.

Pseudo:

```
class ExecutionFrame:
    def __init__(self, pme_context, context, event=None, layout=None,
                 context_tracker=None, bpy_proxy=None):
        self.pme_context = pme_context
        self.context = context
        self.event = event
        self.layout = layout
        self.context_tracker = context_tracker
        self.bpy_proxy = bpy_proxy

    def __enter__(self):
        self._saved_layout = self.pme_context.layout
        self._saved_event = self.pme_context.event
        self._saved_C = self.pme_context._globals.get("C")
        self._saved_bpy = self.pme_context._globals.get("bpy")

        self.pme_context.layout = self.layout
        self.pme_context.event = self.event

        if self.context_tracker:
            self.pme_context._globals["C"] = self.context_tracker

        if self.bpy_proxy:
            self.pme_context._globals["bpy"] = self.bpy_proxy

        return self

    def __exit__(self, exc_type, exc, tb):
        self.pme_context.layout = self._saved_layout
        self.pme_context.event = self._saved_event
        self.pme_context._globals["C"] = self._saved_C
        self.pme_context._globals["bpy"] = self._saved_bpy
```

Rules:
- C and bpy.context are aligned during a single execution frame.
- We restore previous globals; do not leave L/C/E set after execution.
- The context passed to ExecutionFrame is a hint; reactive sync still
  uses the current bpy.context per tick.
Note:
- bpy_proxy can mirror bl_utils.BlBpy but return ContextTracker for "context"

### 6.2 ContextTracker (no BlContext changes)

Goal: keep user code unchanged while inferring resolvers from C access.

Facts:
- bl_utils.BlContext always resolves via _bpy.context and has no "_ctx".
- Modifying BlContext is invasive and global; avoid unless required.

Approach:
- ContextTracker wraps bl_context for attribute access (preserves fallback
  behavior like brush/material_slot).
- Each access records a "context.*" path for resolver inference.
- TrackedAccess behaves like the underlying object (callable, bool,
  comparisons, iteration) so user code keeps working.

Pseudo (simplified):

```
class TrackedAccess:
    def __init__(self, tracker, path, value):
        self._tracker = tracker
        self._path = path
        self._value = value

    def __getattr__(self, name):
        new_path = f"{self._path}.{name}"
        self._tracker.last_access = new_path
        return TrackedAccess(self._tracker, new_path, getattr(self._value, name, None))

    def __call__(self, *args, **kwargs):
        if callable(self._value):
            return self._value(*args, **kwargs)
        raise TypeError(...)

    def __bool__(self): return bool(self._value)
    def __eq__(self, other): ...
    def __iter__(self): return iter(self._value)
    def __getitem__(self, key): return self._value[key]
    # plus __len__, __ne__, __str__, __repr__

class ContextTracker:
    def __init__(self, bl_context):
        self._bl_context = bl_context
        self.last_access = None

    def __getattr__(self, name):
        path = f"context.{name}"
        self.last_access = path
        value = getattr(self._bl_context, name, None)
        return TrackedAccess(self, path, value)
```

### 6.3 ContextResolverCache

Goal: resolve "context.*" safely and cheaply without eval.

```
class ContextResolverCache:
    def __init__(self):
        self._epoch = -1
        self._cache = {}

    def begin_tick(self, epoch):
        if self._epoch != epoch:
            self._epoch = epoch
            self._cache.clear()

    def resolve(self, context, path):
        if path in self._cache:
            return self._cache[path]
        value = resolve_context_path(context, path)
        self._cache[path] = value
        return value
```

### 6.4 PropertyBinding

Goal: never hold references to data objects that can become stale.

```
@dataclass
class PropertyBinding:
    resolve_data: Callable[[bpy.types.Context], Any]
    set_value: Callable[[bpy.types.Context, Any], None]
    prop_name: str
    widget: LayoutItem
    meta: dict
    _last_enum_items: tuple | None = None

    def sync(self, context) -> tuple[bool, bool]:
        data = self.resolve_data(context)
        if data is None:
            was_enabled = self.widget.enabled
            self.widget.enabled = False
            return was_enabled, False

        self.widget.enabled = True
        value = get_property_value(data, self.prop_name)
        value_changed = self._update_widget(value)

        needs_relayout = False
        if self.meta.get("is_dynamic_enum"):
            items = self._get_enum_items(data)
            if items != self._last_enum_items:
                self._last_enum_items = items
                needs_relayout = True

        return value_changed, needs_relayout
```

## 7. Context Resolution for "All of bpy.context"

We must support arbitrary context paths while avoiding eval.
Resolver inference uses ContextTracker when possible and falls back to a
static binding when no path can be determined.

```
def resolve_context_path(context, path: str):
    if not path or not path.startswith("context."):
        return None
    obj = context
    for part in path.split(".")[1:]:
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj
```

This allows:
- "context.object"
- "context.scene.render"
- "context.tool_settings"

Notes:
- ContextTracker provides the last access path; GPULayout.prop consumes and clears it.
- ContextResolverCache stores per-epoch results for the same path.
- For reactive sync, always pass the current bpy.context (not the draw handler
  context snapshot). If we later rebuild a region-specific context, it can
  be injected here.

## 8. UILayout Compatibility Strategy

Goal: GPU layout must converge on full bpy.types.UILayout compatibility so
users do not need to change scripts.

### 8.1 Method Surface Coverage

- Build and maintain a compatibility matrix of UILayout methods and properties
- Generate the list from bpy.types.UILayout at runtime in dev builds
- Provide stubs for unimplemented methods with debug warnings

### 8.2 Signature and Behavior Parity

- Match method names, parameters, and defaults
- Preserve layout semantics (row/column/split/align) and property split rules
- Ensure text/icon behavior matches Blender defaults

### 8.3 Fallbacks and Degraded Modes

- If a GPU method is not implemented:
  - In debug: warn and no-op
  - In release: no-op and mark coverage gap for later
- For templates (template_list, template_ID, etc), either:
  - Implement GPU equivalents, or
  - Use a compatibility fallback when running in standard UI contexts

### 8.4 Transparent L vs Optional GL

- Phase 1: allow optional GL for early adopters and debugging
- Phase 2: L is auto-switched to GPU layout in custom tab mode
- End state: user code uses L and does not care about GPU vs UI layout

## 9. GPULayout Integration

### 9.1 Transparent reactive bindings (no new API)

User code remains unchanged:

```
L.prop(C.object, "hide_viewport")
```

Internal behavior:
- GPULayout.prop() infers a resolver from ContextTracker
- If inference fails, fallback to static binding (no crash, but no reactivity)
- Debug builds log resolver failures for coverage tracking
- GPULayout owns _bindings, _static_bindings, and a ContextResolverCache
- _infer_resolver uses TrackedAccess or ContextTracker.last_access and clears it
- _make_setter resolves data on write; if data is missing, no-op safely

Pseudo:

```
def prop(self, data, property, **kwargs):
    resolver = self._infer_resolver(data)
    set_value = self._make_setter(resolver, data, property)
    widget, meta = self._create_prop_widget(data, property, set_value, **kwargs)
    if resolver:
        binding = PropertyBinding(
            resolve_data=resolver,
            set_value=set_value,
            prop_name=property,
            widget=widget,
            meta=meta,
        )
        self._bindings.append(binding)
    else:
        self._static_bindings.append((data, property, widget, meta))
    return widget
```

Resolver inference (simplified):

```
def _infer_resolver(self, data):
    if isinstance(data, TrackedAccess):
        path = data._path
    elif self._context_tracker and self._context_tracker.last_access:
        path = self._context_tracker.last_access
        self._context_tracker.last_access = None
    else:
        return None

    return lambda ctx: self._context_cache.resolve(ctx, path)
```

### 9.2 sync_reactive

```
def sync_reactive(self, context, epoch):
    self._context_cache.begin_tick(epoch)
    any_changed = False
    for binding in self._bindings:
        changed, relayout = binding.sync(context)
        any_changed |= changed
        if relayout:
            self.mark_dirty()
    return any_changed
```

### 9.3 Draw and Modal Flow

```
def modal(self, context, event):
    self._epoch += 1
    live_context = bpy.context
    self._layout.sync_reactive(live_context, self._epoch)
    if self._layout.dirty:
        self._layout.layout()
    self._layout.draw()
```

Rules:
- Resync always runs per tick.
- Rebuild only on structure changes (enum items change, placeholder switch).
- Do not trust draw-handler context for reactive sync; use live bpy.context.

## 10. Predictability Guarantees

- During a single ExecutionFrame, L/E are stable and C/bpy.context are aligned.
- Between frames, C resolves from live bpy.context (not draw-handler snapshots).
- Bindings never keep stale data references.
- If data is missing, widgets disable instead of crashing.

## 11. Performance Strategy

- Epoch-based cache, not frame_current.
- Resolver results cached only within a tick (ContextResolverCache).
- Relayout only when required.

## 12. Migration Plan

Phase 0: Add new GPU context modules (no integration).
- ui/gpu/context.py: ContextTracker + TrackedAccess
- ui/gpu/binding.py: PropertyBinding + resolve_context_path + ContextResolverCache
- ui/gpu/execution.py: ExecutionFrame
- Unit tests for ContextTracker and resolve_context_path

Phase 1: Integrate into GPULayout.
- Replace _prop_bindings with _bindings and _static_bindings
- Add _context_cache (ContextResolverCache)
- Update prop() to infer resolver, build setter, and register PropertyBinding
- Add sync_reactive(); keep sync_props() as a wrapper for compatibility

Phase 2: Wire ExecutionFrame into GPU custom tab execution.
- Set C to ContextTracker during script execution
- Override bpy to keep bpy.context aligned with C
- Ensure sync_reactive uses live bpy.context, not draw-handler snapshots

Phase 3: Introduce optional GL for early GPU testing and coverage tracking.
Phase 4: Auto-switch L to GPU layout in custom tab mode.
Phase 5: Expand UILayout method coverage to full parity.

## 13. Testing Plan

Core cases:
- ContextTracker records paths for C.object and C.object.data
- TrackedAccess supports callable and bool usage (C.evaluated_depsgraph_get, if C.object)
- Resolver inference uses last_access and clears it per prop()
- Same-frame selection change updates UI
- Deleting active object disables widget, no crash
- context.scene == None does not break provider
- Dynamic enum updates cause relayout
- HitRect updates after relayout
- Multi-region: draw only in correct region
- UILayout method coverage matrix matches bpy.types.UILayout

Manual steps:
- Open GPU panel, switch selected object repeatedly
- Delete object while panel is open
- Switch workspace and verify C updates

## 14. Risks and Mitigations

- Risk: Overhead from resync on large UIs
  Mitigation: cache per tick, avoid relayout
- Risk: C and bpy.context diverge during GPU execution
  Mitigation: set a bpy proxy in ExecutionFrame to keep them aligned
- Risk: Live bpy.context may not match draw region in multi-area setups
  Mitigation: keep region gating and plan a region-specific context override
- Risk: Resolver inference fails when users store context data in locals
  Mitigation: fallback to static binding; log resolver failures in debug builds
- Risk: BlContext/ContextTracker hides errors or returns None silently
  Mitigation: explicit logging in debug builds
- Risk: UILayout parity gaps break existing user scripts
  Mitigation: compatibility matrix, method stubs, phased rollout (GL -> L)

## 15. Open Questions

- Do we need a region-specific context override to avoid active-area drift?
- Should sync_props remain as a public alias of sync_reactive?
- How do we validate UILayout method parity (coverage matrix and tests)?
- Which template_* methods need GPU-first implementations vs staged fallback?

## 16. References

- infra/runtime_context.py
- core/namespace.py
- editors/base.py
- bl_utils.py (BlContext)
- ui/gpu/context.py (planned)
- ui/gpu/binding.py (planned)
- ui/gpu/execution.py (planned)
- ui/gpu/layout.py
- ui/gpu/interactive.py
- ui/gpu/panel_manager.py
- _docs/design/gpu_reactive_context_plan_v2_review.md
- _docs/design/gpu_reactive_context_implementation_guide.md
