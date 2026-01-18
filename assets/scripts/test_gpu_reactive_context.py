#!/usr/bin/env python3
"""Test script for GPU reactive context utilities.

Run in Blender's Python console:
    exec(open(r"E:\\0187_Pie-Menu-Editor\\MyScriptDir\\addons\\pie_menu_editor\\assets\\scripts\\test_gpu_reactive_context.py").read())
"""

import sys


def run_tests():
    print("\n" + "=" * 60)
    print("  GPU Reactive Context Test Suite")
    print("=" * 60)

    results = {
        "passed": 0,
        "failed": 0,
        "errors": [],
    }

    test_context_tracker_basic(results)
    test_context_tracker_chain(results)
    test_tracked_access_call(results)
    test_resolve_context_path_dummy(results)
    test_context_resolver_cache(results)
    test_resolve_context_path_bpy(results)

    print("\n" + "-" * 60)
    print(f"Results: {results['passed']} passed, {results['failed']} failed")

    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")

    print("=" * 60 + "\n")

    return results["failed"] == 0


def _ok(results, message):
    results["passed"] += 1
    print(f"  OK: {message}")


def _fail(results, message):
    results["failed"] += 1
    results["errors"].append(message)
    print(f"  FAIL: {message}")


def test_context_tracker_basic(results):
    print("\n[Test 1] ContextTracker basic path")
    try:
        from pie_menu_editor.bl_utils import bl_context
        from pie_menu_editor.ui.gpu.context import ContextTracker

        tracker = ContextTracker(bl_context)
        _ = tracker.object
        if tracker.last_access == "context.object":
            _ok(results, "last_access == context.object")
        else:
            _fail(results, f"last_access: {tracker.last_access}")
    except Exception as e:
        _fail(results, f"context tracker basic error: {e}")


def test_context_tracker_chain(results):
    print("\n[Test 2] ContextTracker chained path")
    try:
        from pie_menu_editor.bl_utils import bl_context
        from pie_menu_editor.ui.gpu.context import ContextTracker

        tracker = ContextTracker(bl_context)
        _ = tracker.object.data
        if tracker.last_access == "context.object.data":
            _ok(results, "last_access == context.object.data")
        else:
            _fail(results, f"last_access: {tracker.last_access}")

        tracker.clear_tracking()
        if tracker.last_access is None and tracker.get_access_log() == []:
            _ok(results, "clear_tracking() resets state")
        else:
            _fail(results, "clear_tracking() did not reset state")
    except Exception as e:
        _fail(results, f"context tracker chain error: {e}")


def test_tracked_access_call(results):
    print("\n[Test 3] TrackedAccess callable passthrough")
    try:
        from pie_menu_editor.ui.gpu.context import ContextTracker, TrackedAccess

        class DummyCallable:
            def __init__(self):
                self.calls = 0

            def __call__(self, value):
                self.calls += 1
                return value * 2

        tracker = ContextTracker(object())
        dummy = DummyCallable()
        access = TrackedAccess(tracker, "context.dummy", dummy)
        result = access(3)

        if result == 6 and dummy.calls == 1:
            _ok(results, "callable passthrough works")
        else:
            _fail(results, f"callable result={result}, calls={dummy.calls}")
    except Exception as e:
        _fail(results, f"tracked access call error: {e}")


def test_resolve_context_path_dummy(results):
    print("\n[Test 4] resolve_context_path dummy context")
    try:
        from pie_menu_editor.ui.gpu.binding import resolve_context_path

        class DummyChild:
            def __init__(self):
                self.bar = "ok"

        class DummyContext:
            def __init__(self):
                self.foo = DummyChild()

        ctx = DummyContext()
        value = resolve_context_path(ctx, "context.foo.bar")
        if value == "ok":
            _ok(results, "resolved nested path")
        else:
            _fail(results, f"resolve returned: {value}")

        invalid = resolve_context_path(ctx, "foo.bar")
        if invalid is None:
            _ok(results, "invalid path returns None")
        else:
            _fail(results, f"invalid path returned: {invalid}")
    except Exception as e:
        _fail(results, f"resolve_context_path error: {e}")


def test_context_resolver_cache(results):
    print("\n[Test 5] ContextResolverCache")
    try:
        from pie_menu_editor.ui.gpu.binding import ContextResolverCache

        class DummyContext:
            def __init__(self):
                self.calls = 0
                self._value = object()

            def __getattr__(self, name):
                self.calls += 1
                if name == "foo":
                    return self._value
                return None

        ctx = DummyContext()
        cache = ContextResolverCache()
        cache.begin_tick(1)
        v1 = cache.resolve(ctx, "context.foo")
        v2 = cache.resolve(ctx, "context.foo")

        if ctx.calls == 1 and v1 is v2:
            _ok(results, "cache hit within same tick")
        else:
            _fail(results, f"cache calls={ctx.calls}")

        cache.begin_tick(2)
        _ = cache.resolve(ctx, "context.foo")
        if ctx.calls == 2:
            _ok(results, "cache resets on new tick")
        else:
            _fail(results, f"cache reset calls={ctx.calls}")
    except Exception as e:
        _fail(results, f"context resolver cache error: {e}")


def test_resolve_context_path_bpy(results):
    print("\n[Test 6] resolve_context_path bpy.context")
    try:
        import bpy
        from pie_menu_editor.ui.gpu.binding import resolve_context_path

        if bpy.context is None or bpy.context.scene is None:
            _ok(results, "bpy.context not ready; skipped")
            return

        value = resolve_context_path(bpy.context, "context.scene")
        if value is bpy.context.scene:
            _ok(results, "resolved bpy.context.scene")
        else:
            _fail(results, "bpy.context.scene mismatch")
    except Exception as e:
        _fail(results, f"bpy resolve error: {e}")


if __name__ == "__main__" or "bpy" in sys.modules:
    run_tests()
