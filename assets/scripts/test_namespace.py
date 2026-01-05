#!/usr/bin/env python3
"""Test script for pmeGlobal namespace verification.

Run this in Blender's Python console after enabling the addon:
    exec(open(r"E:\0187_Pie-Menu-Editor\MyScriptDir\addons\pie_menu_editor\scripts\test_namespace.py").read())

Or import and run:
    from pie_menu_editor.scripts import test_namespace
    test_namespace.run_tests()
"""

import sys


def run_tests():
    """Run all namespace tests and report results."""
    print("\n" + "=" * 60)
    print("  PME Namespace Test Suite")
    print("=" * 60)

    results = {
        "passed": 0,
        "failed": 0,
        "errors": [],
    }

    # Test 1: Module imports
    test_module_imports(results)

    # Test 2: Public namespace availability
    test_public_namespace(results)

    # Test 3: Context globals generation
    test_gen_globals(results)

    # Test 4: Execute/evaluate functions
    test_execute_evaluate(results)

    # Test 5: Icon path (CursorBot fix verification)
    test_icon_path(results)

    # Summary
    print("\n" + "-" * 60)
    print(f"Results: {results['passed']} passed, {results['failed']} failed")

    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")

    print("=" * 60 + "\n")

    return results["failed"] == 0


def test_module_imports(results):
    """Test that all pme submodules import correctly."""
    print("\n[Test 1] Module Imports")

    tests = [
        ("pie_menu_editor.pme", ["context", "execute", "evaluate", "schema"]),
        ("pie_menu_editor.core.namespace", ["PUBLIC_NAMES", "is_public"]),
        ("pie_menu_editor.core.schema", ["schema", "SchemaProp"]),
        ("pie_menu_editor.infra.previews", ["PreviewsHelper"]),
    ]

    for module_name, attrs in tests:
        try:
            module = __import__(module_name, fromlist=attrs)
            missing = [a for a in attrs if not hasattr(module, a)]
            if missing:
                results["failed"] += 1
                results["errors"].append(f"{module_name}: missing {missing}")
                print(f"  FAIL: {module_name} missing: {missing}")
            else:
                results["passed"] += 1
                print(f"  OK: {module_name}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{module_name}: {e}")
            print(f"  FAIL: {module_name} - {e}")


def test_public_namespace(results):
    """Test that PUBLIC_NAMES are correctly defined."""
    print("\n[Test 2] Public Namespace Definition")

    from pie_menu_editor.core.namespace import PUBLIC_NAMES, NAMESPACE_PUBLIC

    expected = {"bpy", "C", "D", "E", "delta", "drag_x", "drag_y", "U", "L", "text", "icon", "icon_value"}

    if PUBLIC_NAMES == expected:
        results["passed"] += 1
        print(f"  OK: PUBLIC_NAMES contains {len(PUBLIC_NAMES)} variables")
    else:
        results["failed"] += 1
        missing = expected - PUBLIC_NAMES
        extra = PUBLIC_NAMES - expected
        if missing:
            results["errors"].append(f"PUBLIC_NAMES missing: {missing}")
        if extra:
            results["errors"].append(f"PUBLIC_NAMES extra: {extra}")
        print(f"  FAIL: PUBLIC_NAMES mismatch")

    # Check all have stability info
    for name in PUBLIC_NAMES:
        if name not in NAMESPACE_PUBLIC:
            results["failed"] += 1
            results["errors"].append(f"{name} not in NAMESPACE_PUBLIC")


def test_gen_globals(results):
    """Test that gen_globals produces correct namespace."""
    print("\n[Test 3] gen_globals() Output")

    from pie_menu_editor import pme
    from pie_menu_editor.core.namespace import PUBLIC_NAMES

    globals_dict = pme.context.gen_globals()

    # Check that basic items are present
    required_keys = {"bpy", "pme_context", "text", "icon", "icon_value", "drag_x", "drag_y"}

    missing = required_keys - set(globals_dict.keys())
    if missing:
        results["failed"] += 1
        results["errors"].append(f"gen_globals missing: {missing}")
        print(f"  FAIL: Missing keys: {missing}")
    else:
        results["passed"] += 1
        print(f"  OK: gen_globals has {len(globals_dict)} keys")

    # Check for 'C' - may need context
    if "C" not in globals_dict:
        print(f"  WARN: 'C' not in globals (may need Blender context)")


def test_execute_evaluate(results):
    """Test execute() and evaluate() functions."""
    print("\n[Test 4] execute() / evaluate()")

    from pie_menu_editor import pme

    # Test evaluate with simple expression
    try:
        result = pme.evaluate("1 + 1")
        if result == 2:
            results["passed"] += 1
            print("  OK: evaluate('1 + 1') = 2")
        else:
            results["failed"] += 1
            results["errors"].append(f"evaluate('1 + 1') = {result}, expected 2")
            print(f"  FAIL: evaluate returned {result}")
    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"evaluate error: {e}")
        print(f"  FAIL: evaluate raised {e}")

    # Test execute with simple code
    try:
        result = pme.execute("x = 42")
        if result.success:
            results["passed"] += 1
            print("  OK: execute('x = 42') succeeded")
        else:
            results["failed"] += 1
            results["errors"].append(f"execute failed: {result.error_message}")
            print(f"  FAIL: execute failed")
    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"execute error: {e}")
        print(f"  FAIL: execute raised {e}")

    # Test with bpy access
    try:
        result = pme.evaluate("bpy.app.version[0]")
        if isinstance(result, int) and result >= 4:
            results["passed"] += 1
            print(f"  OK: evaluate('bpy.app.version[0]') = {result}")
        else:
            results["failed"] += 1
            print(f"  FAIL: unexpected version: {result}")
    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"bpy access error: {e}")
        print(f"  FAIL: bpy access raised {e}")


def test_icon_path(results):
    """Test that PreviewsHelper has correct addon root path."""
    print("\n[Test 5] Icon Path (CursorBot fix)")

    import os
    from pie_menu_editor.infra.previews import PreviewsHelper

    ph = PreviewsHelper()
    # assets/scripts/test_namespace.py → assets/scripts/ → assets/ → pie_menu_editor/
    addon_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Path should point to addon_root/assets/icons
    expected_path = os.path.join(addon_root, "assets", "icons")
    actual_path = ph.path

    # Normalize paths for comparison
    expected_norm = os.path.normpath(expected_path)
    actual_norm = os.path.normpath(actual_path)

    if expected_norm == actual_norm:
        results["passed"] += 1
        print(f"  OK: Icon path is correct")
        print(f"      {actual_path}")
    else:
        results["failed"] += 1
        results["errors"].append(f"Icon path wrong: {actual_path}")
        print(f"  FAIL: Icon path incorrect")
        print(f"      Expected: {expected_path}")
        print(f"      Actual:   {actual_path}")

    # Verify icons directory exists
    if os.path.isdir(actual_path):
        icon_count = len([f for f in os.listdir(actual_path) if f.endswith('.png')])
        print(f"      Found {icon_count} .png icons")
    else:
        print(f"  WARN: Icons directory not found at {actual_path}")


# Auto-run when executed directly
if __name__ == "__main__" or "bpy" in sys.modules:
    run_tests()
