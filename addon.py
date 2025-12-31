from __future__ import annotations

import bpy
from bpy.app import version as APP_VERSION
import os
import sys
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .preferences import PMEPreferences


VERSION = None
BL_VERSION = None
ADDON_ID = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
ADDON_PATH = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ADDON_PATH, "scripts/")
SAFE_MODE = "--pme-safe-mode" in sys.argv
ICON_ENUM_ITEMS = (
    bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
)


def get_uprefs(context: bpy.types.Context = bpy.context) -> bpy.types.Preferences:
    """
    Get user preferences

    Args:
        context: Blender context (defaults to bpy.context)

    Returns:
        bpy.types.Preferences: User preferences

    Raises:
        AttributeError: If preferences cannot be accessed
    """
    preferences = getattr(context, "preferences", None)
    if preferences is not None:
        return preferences
    raise AttributeError("Could not access preferences")


def get_prefs(context: bpy.types.Context = bpy.context) -> PMEPreferences:
    """
    Get addon preferences

    Args:
        context: Blender context (defaults to bpy.context)

    Returns:
        bpy.types.AddonPreferences: Addon preferences

    Raises:
        KeyError: If addon is not found
    """
    user_prefs = get_uprefs(context)
    addon_prefs = user_prefs.addons.get(ADDON_ID)
    if addon_prefs is not None:
        return addon_prefs.preferences
    raise KeyError(f"Addon '{ADDON_ID}' not found")


def uprefs():
    stack = traceback.extract_stack()
    caller = stack[-2]
    print(
        f"Warning: uprefs() is deprecated. Called from {caller.filename}:{caller.lineno}"
    )
    return get_uprefs()


def prefs():
    stack = traceback.extract_stack()
    caller = stack[-2]
    print(
        f"Warning: prefs() is deprecated. Called from {caller.filename}:{caller.lineno}"
    )
    return get_prefs()


def temp_prefs():
    return getattr(getattr(bpy.context, "window_manager", None), "pme", None)


def check_bl_version(version=None):
    version = version or BL_VERSION
    return APP_VERSION >= version


def check_context():
    return isinstance(bpy.context, bpy.types.Context)


def print_exc(text=None):
    if not get_prefs().show_error_trace:
        return

    if text is not None:
        print()
        print(">>>", text)

    traceback.print_exc()


def ic(icon):
    # Legacy_TODO: Remove or Enhance
    # Support for 2.79 and 2.8+
    if not icon:
        return icon

    if icon in ICON_ENUM_ITEMS:
        return icon

    bl28_icons = dict(
        ZOOMIN="ADD",
        ZOOMOUT="REMOVE",
        ROTACTIVE="TRIA_RIGHT",
        ROTATE="TRIA_RIGHT_BAR",
        ROTATECOLLECTION="NEXT_KEYFRAME",
        NORMALIZE_FCURVES="ANIM_DATA",
        OOPS="NODETREE",
        SPLITSCREEN="MOUSE_MMB",
        GHOST="DUPLICATE",
    )

    if icon in bl28_icons and bl28_icons[icon] in ICON_ENUM_ITEMS:
        return bl28_icons[icon]

    print("Icon not found:", icon)
    return 'BLENDER'


def ic_rb(value):
    return ic('RADIOBUT_ON' if value else 'RADIOBUT_OFF')


def ic_cb(value):
    return ic('CHECKBOX_HLT' if value else 'CHECKBOX_DEHLT')


def ic_fb(value):
    return ic('SOLO_ON' if value else 'SOLO_OFF')


def ic_eye(value):
    return ic('HIDE_OFF' if value else 'HIDE_ON')


# ======================================================
# Generic Module Loader (PME2)
# ======================================================
#
# This section provides a generic module loading system for PME2.
# It is NOT currently used - the existing MODULES + get_classes() system
# in __init__.py remains active.
#
# When ready to migrate, __init__.py will call:
#   addon.init_addon(module_patterns=[...])
#   addon.register_modules()
# instead of the current manual module loading.
# ======================================================

import ast
import importlib
import inspect
import pkgutil
import re
from collections import defaultdict
from typing import Dict, List, Pattern, Set

from .debug_utils import (
    DBG_DEPS,
    dbg_log,
    dbg_scope,
    DependencyGraphLogger,
    make_edges_from_graph,
    log_layer_violations,
)

# Module management globals
MODULE_NAMES: List[str] = []  # Load-order resolved module list
MODULE_PATTERNS: List[Pattern] = []  # Patterns for target modules
_class_cache: List[type] = None

# Operator prefix (for dynamic operator ID generation)
ADDON_PREFIX = "PME"
ADDON_PREFIX_PY = "pme"


def init_addon(
    module_patterns: List[str],
    use_reload: bool = False,
    background: bool = False,
    prefix: str = None,
    prefix_py: str = None,
    force_order: List[str] = None,
) -> None:
    """
    Initialize the addon module loading system.

    This function performs the following steps:
    1. Collect module names based on patterns
    2. Load/reload each module
    3. Analyze inter-module dependencies
    4. Determine load order via topological sort
    5. Store the sorted module list for registration

    Args:
        module_patterns: List of module patterns to load (e.g., ["core.*", "ui.*"])
        use_reload: Whether to reload already-loaded modules
        background: If True, skip registration in background mode
        prefix: Operator prefix override (default: "PME")
        prefix_py: Python prefix override (default: "pme")
        force_order: Force specific module load order (debugging only)

    Example:
        init_addon(
            module_patterns=[
                "core.*",
                "infra.*",
                "ui.*",
                "editors.*",
                "operators.*",
                "prefs.*",
            ],
            use_reload=True
        )
    """
    global ADDON_PREFIX, ADDON_PREFIX_PY, _class_cache

    # Reset class cache
    _class_cache = None

    # Update prefixes if provided
    if prefix:
        ADDON_PREFIX = prefix
    if prefix_py:
        ADDON_PREFIX_PY = prefix_py

    # Compile patterns
    MODULE_PATTERNS[:] = [
        re.compile(f"^{ADDON_ID}\\.{p.replace('*', '.*')}$") for p in module_patterns
    ]
    # Also include the addon module itself
    MODULE_PATTERNS.append(re.compile(f"^{ADDON_ID}$"))

    try:
        # Collect module names
        with dbg_scope("profile", "init_addon.collect_modules", location="addon.init_addon"):
            module_names = list(_collect_module_names())

        dbg_log(
            "deps",
            f"Collected {len(module_names)} modules",
            data={"patterns": [c.pattern for c in MODULE_PATTERNS]},
            location="addon.init_addon",
        )

        # Pre-load modules
        dbg_log(
            "deps",
            "Module load: start",
            data={"modules": len(module_names), "use_reload": use_reload},
            location="addon.init_addon",
        )
        load_errors = 0
        with dbg_scope("profile", "init_addon.load_modules", location="addon.init_addon"):
            for module_name in module_names:
                dbg_log(
                    "deps",
                    "Import begin",
                    data={"module": module_name},
                    location="addon.init_addon",
                )
                try:
                    do_reload = (
                        use_reload
                        and module_name in sys.modules
                        and module_name != "pie_menu_editor.debug_utils"
                    )
                    if do_reload:
                        importlib.reload(sys.modules[module_name])
                        action = "reload"
                    else:
                        importlib.import_module(module_name)
                        action = "import"
                except Exception as e:
                    load_errors += 1
                    dbg_log(
                        "deps",
                        "Import failed",
                        data={"module": module_name, "error": str(e)},
                        level="warn",
                        location="addon.init_addon",
                    )
                    print(f">>> Failed to load module {module_name}: {str(e)}")
                    traceback.print_exception(type(e), e, e.__traceback__, limit=2)
                else:
                    dbg_log(
                        "deps",
                        "Import ok",
                        data={
                            "module": module_name,
                            "action": action,
                            "index": module_names.index(module_name),
                            "total": len(module_names),
                        },
                        location="addon.init_addon",
                    )
        dbg_log(
            "deps",
            f"Module load: done (errors={load_errors})",
            data={"errors": load_errors, "modules": len(module_names)},
            location="addon.init_addon",
            level="warn" if load_errors else "info",
        )
    except Exception as e:
        dbg_log(
            "deps",
            "init_addon failed in collect/load phase",
            data={"error": str(e)},
            level="error",
            location="addon.init_addon",
        )
        raise

    # Resolve dependencies
    with dbg_scope("profile", "init_addon.sort_modules", location="addon.init_addon"):
        if force_order:
            # Debugging: forced module load order
            if force_order:
                dbg_log(
                    "deps",
                    "Using forced module load order (debugging)",
                    level="warn",
                    location="addon.init_addon",
                )
            sorted_modules = _resolve_forced_order(force_order, module_names)
            # NOTE: レイヤ違反チェックを強制順序でも実施する（アーキテクチャ整理完了後に外す想定）
            if DBG_DEPS:
                edges = list(zip(force_order[:-1], force_order[1:]))
                # 文字列 → フルモジュール名補完（_resolve_forced_order と同じルール）
                patched_edges = []
                for src, dst in edges:
                    full_src = src if src.startswith(ADDON_ID) else f"{ADDON_ID}.{src}"
                    full_dst = dst if dst.startswith(ADDON_ID) else f"{ADDON_ID}.{dst}"
                    patched_edges.append((full_src, full_dst))
                log_layer_violations(
                    patched_edges,
                    addon_id=ADDON_ID,
                    category="deps",
                    location="addon.init_addon(force_order)",
                )
        else:
            # Normal: automatic dependency resolution
            sorted_modules = _sort_modules(module_names)

    MODULE_NAMES[:] = sorted_modules

    # Log final module order
    if DBG_DEPS:
        dep_logger = DependencyGraphLogger("init_addon")
        dep_logger.add_chain(
            [_short_name(m) for m in MODULE_NAMES],
            label="load_order"
        )
        dep_logger.flush(category="deps", location="addon.init_addon")

    dbg_log(
        "deps",
        f"Final module order: {len(MODULE_NAMES)} modules",
        data={"modules": [_short_name(m) for m in MODULE_NAMES]},
        location="addon.init_addon",
    )


def register_modules() -> None:
    """
    Register all modules with Blender.

    This function:
    1. Sorts all classes by dependency order
    2. Registers each class with Blender
    3. Calls each module's register() function
    """
    if bpy.app.background:
        return

    with dbg_scope("profile", "register_modules.classes", location="addon.register_modules"):
        classes = _get_classes()

    success = True

    # Register classes
    for cls in classes:
        try:
            _validate_class(cls)
            bpy.utils.register_class(cls)
            dbg_log("deps", f"Registered: {cls.__name__}", location="addon.register_modules")
        except Exception as e:
            success = False
            print(f"Failed to register class: {cls.__name__}")
            print(f"   Reason: {str(e)}")
            print(f"   Module: {cls.__module__}")
            if hasattr(cls, "__annotations__"):
                print(f"   Annotations: {list(cls.__annotations__.keys())}")

    # Initialize modules
    with dbg_scope("profile", "register_modules.init", location="addon.register_modules"):
        for mod_name in MODULE_NAMES:
            try:
                mod = sys.modules[mod_name]
                if hasattr(mod, "register"):
                    mod.register()
                    dbg_log("deps", f"Initialized: {_short_name(mod_name)}", location="addon.register_modules")
            except Exception as e:
                success = False
                print(f"Failed to initialize module: {mod_name}")
                print(f"   Reason: {str(e)}")
                traceback.print_exc()

    if not success:
        print("Warning: Some components failed to initialize")


def unregister_modules() -> None:
    """
    Unregister all modules from Blender.

    This function:
    1. Calls each module's unregister() function (reverse order)
    2. Unregisters each class from Blender (reverse order)
    """
    if bpy.app.background:
        return

    # Unregister modules (reverse order)
    for mod_name in reversed(MODULE_NAMES):
        try:
            mod = sys.modules[mod_name]
            if hasattr(mod, "unregister"):
                mod.unregister()
        except Exception as e:
            print(f"Module unregistration error: {mod_name} - {str(e)}")

    # Unregister classes (reverse order)
    for cls in reversed(_get_classes()):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Class unregistration error: {cls.__name__} - {str(e)}")


# ======================================================
# Internal Helper Functions
# ======================================================


def _collect_module_names() -> List[str]:
    """
    Collect module names matching the configured patterns.

    Returns:
        List of fully qualified module names
    """
    # 追加観測: どのパスを走査しているかを deps ログへ
    if DBG_DEPS:
        dbg_log(
            "deps",
            "Scan modules: start",
            data={"path": ADDON_PATH, "package": ADDON_ID, "patterns": [p.pattern for p in MODULE_PATTERNS]},
            location="addon._collect_module_names",
        )

    def is_matched(name: str) -> bool:
        return any(p.match(name) for p in MODULE_PATTERNS)

    def scan(path: str, package: str) -> List[str]:
        modules = []
        try:
            entries = list(pkgutil.iter_modules([path]))
        except Exception as e:
            dbg_log(
                "deps",
                "Scan error",
                data={"path": path, "error": str(e)},
                level="error",
                location="addon._collect_module_names",
            )
            return modules

        if DBG_DEPS:
            dbg_log(
                "deps",
                "Scan entries",
                data={"path": path, "entries": len(entries)},
                location="addon._collect_module_names",
            )

        for _, name, is_pkg in entries:
            # Skip private modules
            if name.startswith("_"):
                continue

            full_name = f"{package}.{name}"
            # Recursively scan packages
            if is_pkg:
                modules.extend(scan(os.path.join(path, name), full_name))
            # Add matching modules
            if is_matched(full_name):
                modules.append(full_name)
        return modules

    found = scan(ADDON_PATH, ADDON_ID)

    if DBG_DEPS:
        dbg_log(
            "deps",
            "Scan modules: done",
            data={"found": len(found)},
            location="addon._collect_module_names",
        )

    return found


def _resolve_forced_order(force_order: List[str], module_names: List[str]) -> List[str]:
    """
    Resolve forced module order (for debugging/troubleshooting).

    Args:
        force_order: List of module names to force first
        module_names: All available module names

    Returns:
        Resolved module order with forced modules first
    """
    processed_order = []
    for mod in force_order:
        if not mod.startswith(ADDON_ID):
            full_name = f"{ADDON_ID}.{mod}"
        else:
            full_name = mod

        if full_name in module_names:
            processed_order.append(full_name)
        else:
            print(f"Warning: Specified module {full_name} not found")

    # Append remaining modules
    remaining = [m for m in module_names if m not in processed_order]
    return processed_order + remaining


def _analyze_dependencies(module_names: List[str]) -> Dict[str, Set[str]]:
    """
    Analyze inter-module dependencies.

    Sources of dependency detection:
    1. Import statements (import, from-import)
    2. Property types (PointerProperty, CollectionProperty)
    3. Explicit DEPENDS_ON attribute

    Returns:
        Dependency graph: {module: set of modules that depend on it}
    """
    import_graph = _analyze_imports(module_names)

    graph = defaultdict(set)
    pdtype = bpy.props._PropertyDeferred

    # Merge import dependencies
    # Note: import_graph is {dependent: {dependencies}}
    # We need to invert to {dependency: {dependents}} for topological sort
    for mod_name, deps in import_graph.items():
        for dep in deps:
            graph[dep].add(mod_name)

    for mod_name in module_names:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue

        # Class dependency analysis
        for _, cls in inspect.getmembers(mod, _is_bpy_class):
            for prop in getattr(cls, "__annotations__", {}).values():
                if isinstance(prop, pdtype) and prop.function in [
                    bpy.props.PointerProperty,
                    bpy.props.CollectionProperty,
                ]:
                    dep_cls = prop.keywords.get("type")
                    if not dep_cls:
                        continue

                    dep_mod = dep_cls.__module__
                    if dep_mod == mod_name:
                        continue

                    if dep_mod in module_names:
                        graph[dep_mod].add(mod_name)

        # Explicit dependencies
        if hasattr(mod, "DEPENDS_ON"):
            for dep in mod.DEPENDS_ON:
                dep_full = f"{ADDON_ID}.{dep}" if not dep.startswith(ADDON_ID) else dep
                if dep_full in module_names:
                    graph[dep_full].add(mod_name)

    return graph


def _analyze_imports(module_names: List[str]) -> Dict[str, Set[str]]:
    """
    Analyze import statements for dependency detection.

    Returns:
        Dict mapping each module to the set of modules it imports
    """
    graph = defaultdict(set)

    class ImportVisitor(ast.NodeVisitor):
        def __init__(self, mod_name, graph):
            self.mod_name = mod_name
            self.graph = graph
            self.in_type_checking_block = False

        def visit_If(self, node: ast.If):
            is_type_checking = (
                isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"
            )
            original_state = self.in_type_checking_block
            if is_type_checking:
                self.in_type_checking_block = True

            self.generic_visit(node)
            self.in_type_checking_block = original_state

        def visit_Import(self, node: ast.Import):
            if self.in_type_checking_block:
                return
            for alias in node.names:
                if alias.name.startswith(ADDON_ID):
                    self.graph[self.mod_name].add(alias.name)

        def visit_ImportFrom(self, node: ast.ImportFrom):
            if self.in_type_checking_block:
                return

            if node.module:
                module_path = node.module
                if node.level > 0:
                    # Relative import
                    parent_parts = self.mod_name.split(".")
                    if node.level > len(parent_parts) - 1:
                        return
                    base_path = ".".join(parent_parts[: -node.level])
                    module_path = f"{base_path}.{module_path}" if module_path else base_path
                else:
                    if not module_path.startswith(ADDON_ID + "."):
                        potential_full_path = f"{ADDON_ID}.{module_path}"
                        if any(m.startswith(potential_full_path) for m in module_names):
                            module_path = potential_full_path

                if module_path.startswith(ADDON_ID):
                    if module_path in module_names:
                        self.graph[self.mod_name].add(module_path)

                    for alias in node.names:
                        if alias.name != "*":
                            full_submodule = f"{module_path}.{alias.name}"
                            if full_submodule in module_names:
                                self.graph[self.mod_name].add(full_submodule)

    for mod_name in module_names:
        mod = sys.modules.get(mod_name)
        if not mod or not hasattr(mod, "__file__") or not mod.__file__:
            continue

        try:
            with open(mod.__file__, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=mod.__file__)
            visitor = ImportVisitor(mod_name, graph)
            visitor.visit(tree)
        except (FileNotFoundError, SyntaxError):
            pass
        except Exception as e:
            print(f"Import analysis error ({mod_name}): {str(e)}")

    return graph


def _sort_modules(module_names: List[str]) -> List[str]:
    """
    Sort modules by dependency order using topological sort.

    Returns:
        Sorted list of module names
    """
    dbg_log("deps", f"Analyze deps for {len(module_names)} modules", location="addon._sort_modules")
    graph = _analyze_dependencies(module_names)

    # Filter to existing modules only
    filtered_graph = {
        n: {d for d in deps if d in module_names}
        for n, deps in graph.items()
        if n in module_names
    }

    # Ensure all modules are in the graph
    for mod_name in module_names:
        if mod_name not in filtered_graph:
            filtered_graph[mod_name] = set()

    if DBG_DEPS:
        edges = make_edges_from_graph(filtered_graph)
        log_layer_violations(
            edges,
            addon_id=ADDON_ID,
            category="deps",
            location="addon._sort_modules",
        )

    try:
        sorted_modules = _topological_sort(filtered_graph)
    except ValueError as e:
        dbg_log(
            "deps",
            "Topological sort error; fallback to alternative sort",
            data={"error": str(e)},
            level="warn",
            location="addon._sort_modules",
        )
        print(f"Warning: {str(e)}")
        print("Using alternative sorting method...")
        sorted_modules = _alternative_sort(filtered_graph, module_names)

    # Add any remaining modules
    remaining = [m for m in module_names if m not in sorted_modules]
    if remaining:
        sorted_modules.extend(remaining)

    return sorted_modules


def _topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
    """
    Kahn's algorithm for topological sorting.

    Args:
        graph: {module: set of modules that depend on it}

    Returns:
        Sorted module list

    Raises:
        ValueError: If circular dependency detected
    """
    in_degree = defaultdict(int)
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1

    queue = [node for node in graph if in_degree[node] == 0]
    sorted_order = []

    while queue:
        node = queue.pop(0)
        sorted_order.append(node)

        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_order) != len(graph):
        cyclic = set(graph.keys()) - set(sorted_order)
        raise ValueError(f"Circular dependency detected: {', '.join(cyclic)}")

    return sorted_order


def _alternative_sort(graph: Dict[str, Set[str]], module_names: List[str]) -> List[str]:
    """
    Alternative sorting when circular dependencies exist.

    Uses priority-based sorting:
    1. Base addon module
    2. Utils/core modules
    3. Other modules (by out-degree)
    """
    cycles = _detect_cycles(graph)
    if cycles:
        print("\n=== Detected circular dependencies ===")
        for i, cycle in enumerate(cycles, 1):
            print(f"Cycle {i}: {' -> '.join(_short_name(m) for m in cycle)} -> {_short_name(cycle[0])}")

    base_priority = {ADDON_ID: 0}
    outdegree = {node: len(deps) for node, deps in graph.items()}

    priority_groups = defaultdict(list)
    for mod in module_names:
        if mod in base_priority:
            priority = base_priority[mod]
        elif ".utils." in mod or mod.endswith(".utils"):
            priority = 1
        elif ".core." in mod or mod.endswith(".core"):
            priority = 2
        else:
            priority = 10 + outdegree.get(mod, 0)
        priority_groups[priority].append(mod)

    result = []
    for priority in sorted(priority_groups.keys()):
        result.extend(sorted(priority_groups[priority]))

    return result


def _detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Detect circular dependencies using Tarjan's algorithm.

    Returns:
        List of cycles (each cycle is a list of module names)
    """
    visited = set()
    stack = []
    on_stack = set()
    index_map = {}
    low_link = {}
    index = 0
    cycles = []

    def strong_connect(node):
        nonlocal index
        index_map[node] = index
        low_link[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        visited.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                strong_connect(neighbor)
                low_link[node] = min(low_link[node], low_link[neighbor])
            elif neighbor in on_stack:
                low_link[node] = min(low_link[node], index_map[neighbor])

        if low_link[node] == index_map[node]:
            component = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == node:
                    break
            if len(component) > 1:
                cycles.append(component)

    for node in graph:
        if node not in visited:
            strong_connect(node)

    return cycles


def _get_classes(force: bool = True) -> List[type]:
    """
    Get all registrable classes in dependency order.

    Args:
        force: If True, rebuild the class list (ignore cache)

    Returns:
        List of classes sorted by dependency order
    """
    global _class_cache
    if not force and _class_cache:
        return _class_cache

    class_deps = defaultdict(set)
    pdtype = getattr(bpy.props, "_PropertyDeferred", tuple)

    all_classes = []
    for mod_name in MODULE_NAMES:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue

        for _, cls in inspect.getmembers(mod, _is_bpy_class):
            deps = set()
            for prop in getattr(cls, "__annotations__", {}).values():
                if isinstance(prop, pdtype):
                    pfunc = getattr(prop, "function", None) or prop[0]
                    if pfunc in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
                        if dep_cls := prop.keywords.get("type"):
                            if dep_cls.__module__.startswith(ADDON_ID):
                                deps.add(dep_cls)
            class_deps[cls] = deps
            all_classes.append(cls)

    # DFS for dependency resolution
    ordered = []
    visited = set()
    stack = []

    def visit(cls):
        if cls in stack:
            cycle = " -> ".join([c.__name__ for c in stack])
            raise ValueError(f"Circular class dependency: {cycle}")
        if cls not in visited:
            stack.append(cls)
            visited.add(cls)
            for dep in class_deps.get(cls, []):
                visit(dep)
            stack.pop()
            ordered.append(cls)

    for cls in all_classes:
        if cls not in visited:
            visit(cls)

    _class_cache = ordered
    return ordered


def _is_bpy_class(obj) -> bool:
    """
    Check if an object is a registrable Blender class.
    """
    return (
        inspect.isclass(obj)
        and issubclass(obj, bpy.types.bpy_struct)
        and obj.__base__ is not bpy.types.bpy_struct
        and obj.__module__.startswith(ADDON_ID)
    )


def _validate_class(cls: type) -> None:
    """
    Validate a class before registration.

    Raises:
        ValueError: If class is invalid for registration
    """
    if not hasattr(cls, "bl_rna"):
        raise ValueError(f"Class {cls.__name__} has no bl_rna attribute")
    if not issubclass(cls, bpy.types.bpy_struct):
        raise TypeError(f"Invalid class type: {cls.__name__}")


def _short_name(module_name: str) -> str:
    """
    Get shortened module name (without addon prefix).
    """
    prefix = f"{ADDON_ID}."
    return module_name[len(prefix):] if module_name.startswith(prefix) else module_name
