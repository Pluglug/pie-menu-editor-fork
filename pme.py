# pme.py - PME execution context (command execution layer)
# LAYER = "infra"
#
# This module provides the execution environment for user scripts.
# It will serve as the external API facade in the future.
#
# Phase 4-A changes:
#   - PMEProp, PMEProps, ParsedData moved to core/props.py
#   - Re-exported here for backward compatibility
#   - PMEContext and UserData remain here (runtime dependencies)
#
# Phase 8-C changes:
#   - core/props.py renamed to core/schema.py
#   - PMEProps → SchemaRegistry, props → schema
#   - Old names kept as deprecated aliases

LAYER = "infra"

from dataclasses import dataclass
from typing import Any

import bpy

from .addon import get_prefs, temp_prefs, print_exc

# Import and re-export schema classes from core layer
# New preferred names (Phase 8-C):
#   from . import pme; pme.schema.parse(...)
from .core.schema import (
    # New names (preferred)
    SchemaProp,
    SchemaRegistry,
    schema,
    ParsedData,
    # Deprecated aliases (backward compatibility)
    PMEProp,
    PMEProps,
    props,
)

# Import and re-export namespace definitions for external API
# External tools can use: from pie_menu_editor import pme; pme.is_public("C")
from .core.namespace import (
    Stability,
    NAMESPACE_CORE,
    NAMESPACE_EVENT,
    NAMESPACE_USER,
    NAMESPACE_UI,
    NAMESPACE_PUBLIC,
    NAMESPACE_INTERNAL,
    PUBLIC_NAMES,
    is_public,
    is_internal,
    get_stability,
    get_public_names_by_stability,
)


class UserData:
    """User data container for scripts.

    Accessible as 'U' in the standard namespace.
    Allows users to store arbitrary data during a session.
    """

    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def update(self, **kwargs):
        self.__dict__.update(**kwargs)

    def __getattr__(self, name):
        return self.__dict__.get(name, None)


class PMEContext:
    """Execution context for PME scripts.

    Manages the global namespace and provides eval/exec capabilities
    for user-defined scripts in PM/PMI items.

    Accessible as 'pme.context' or 'pme_context' in scripts.
    """

    def __init__(self):
        self._globals = dict(
            bpy=bpy,
            pme_context=self,
            drag_x=0,
            drag_y=0,
        )
        self.pm = None
        self.pmi = None
        self.index = None
        self.icon = None
        self.icon_value = None
        self.text = None
        self.region = None
        self.last_operator = None
        self.is_first_draw = True
        self.exec_globals = None
        self.exec_locals = None
        self.exec_user_locals = dict()
        self._layout = None
        self._event = None
        self.edit_item_idx = None

    def __getattr__(self, name):
        return self._globals.get(name, None)

    def item_id(self):
        pmi = self.pmi
        id = self.pm.name
        id += pmi.name if pmi.name else pmi.text
        id += str(self.index)
        return id

    def reset(self):
        self.is_first_draw = True
        self.exec_globals = None
        self.exec_locals = None

    def add_global(self, key, value):
        """Add a variable to the global namespace."""
        self._globals[key] = value

    @property
    def layout(self):
        return self._layout

    @layout.setter
    def layout(self, value):
        self._layout = value
        self._globals["L"] = value

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, value):
        self._event = value
        self._globals["E"] = value

        if self._event:
            if self._event.type == 'WHEELUPMOUSE':
                self._globals["delta"] = 1
            elif self._event.type == 'WHEELDOWNMOUSE':
                self._globals["delta"] = -1

    @property
    def globals(self):
        # Ensure "D" is set (may be missing after Reload Scripts)
        if "D" not in self._globals or self._globals["D"].__class__.__name__ == "_RestrictData":
            self._globals["D"] = bpy.data
        return self._globals

    def gen_globals(self, **kwargs):
        """Generate the globals dict for script execution."""
        ret = dict(
            text=self.text,
            icon=self.icon,
            icon_value=self.icon_value,
            PME=temp_prefs(),
            PREFS=get_prefs(),
            **kwargs
        )

        ret.update(self.exec_user_locals)
        ret.update(self.globals)

        return ret

    def eval(self, expression, globals=None, menu=None, slot=None):
        """Evaluate an expression and return the result."""
        if globals is None:
            globals = self.gen_globals()

        value = None
        try:
            value = eval(expression, globals)
        except:
            print_exc(expression)

        return value

    def exe(self, data, globals=None, menu=None, slot=None, use_try=True):
        """Execute Python code.

        Returns True on success, False on error.
        """
        if globals is None:
            globals = self.gen_globals()

        if not use_try:
            exec(data, globals)
            return True

        try:
            exec(data, globals)
        except:
            print_exc(data)
            return False

        return True


context = PMEContext()


# =============================================================================
# Public API Facades (Experimental)
# =============================================================================
# These functions provide a stable interface for external tools.
# They wrap the internal PMEContext methods with cleaner signatures.


@dataclass
class ExecuteResult:
    """Result of code execution.

    Attributes:
        success: True if execution completed without errors.
        error_message: Error description if execution failed, None otherwise.

    Stability: Experimental
    """

    success: bool
    error_message: str | None = None


def execute(code: str, *, extra_globals: dict[str, Any] | None = None) -> ExecuteResult:
    """Execute arbitrary Python code with PME's standard namespace.

    The standard namespace includes: C, D, bpy, E, L, U, delta, drag_x, drag_y,
    and other PME-provided variables. See NAMESPACE_PUBLIC for the full list.

    Args:
        code: Python code to execute (can be multi-line).
        extra_globals: Additional variables to inject into the namespace.
            These override standard namespace variables if names conflict.

    Returns:
        ExecuteResult with success status and optional error message.

    Example:
        >>> result = pme.execute("print(C.mode)")
        >>> if not result.success:
        ...     print(f"Error: {result.error_message}")

        >>> result = pme.execute(
        ...     "print(gizmo.name)",
        ...     extra_globals={"gizmo": my_gizmo}
        ... )

    Stability: Experimental
    """
    globals_dict = context.gen_globals()
    if extra_globals:
        globals_dict.update(extra_globals)

    try:
        exec(code, globals_dict)
        return ExecuteResult(success=True)
    except Exception as e:
        return ExecuteResult(success=False, error_message=str(e))


def evaluate(expr: str, *, extra_globals: dict[str, Any] | None = None) -> Any:
    """Evaluate an expression and return the result.

    Unlike execute(), this function raises exceptions on failure.
    This is intentional: silent failures hide bugs. If you need
    fallback behavior, wrap the call in try-except.

    The standard namespace includes: C, D, bpy, E, L, U, delta, drag_x, drag_y,
    and other PME-provided variables.

    Args:
        expr: Python expression to evaluate (single expression, not statements).
        extra_globals: Additional variables to inject into the namespace.

    Returns:
        The result of evaluating the expression.

    Raises:
        SyntaxError: If the expression has invalid syntax.
        NameError: If the expression references undefined variables.
        Any other exception that occurs during evaluation.

    Example:
        >>> mode = pme.evaluate("C.mode")
        >>> print(mode)  # 'OBJECT', 'EDIT_MESH', etc.

        >>> # For poll-like usage, handle exceptions explicitly:
        >>> try:
        ...     visible = pme.evaluate("C.mode == 'EDIT_MESH'")
        ... except Exception:
        ...     visible = True  # Safe fallback

    Stability: Experimental
    """
    globals_dict = context.gen_globals()
    if extra_globals:
        globals_dict.update(extra_globals)

    return eval(expr, globals_dict)


# =============================================================================
# Menu Integration API (Experimental)
# =============================================================================
# These functions provide access to PME's menu system.
# External tools can find and invoke menus programmatically.


@dataclass
class PMHandle:
    """Read-only handle to a Pie Menu.

    This is a lightweight wrapper that provides safe access to PM metadata
    without exposing the internal PMItem object directly.

    Attributes:
        name: The unique name of the menu.
        mode: The menu type ('PMENU', 'RMENU', 'DIALOG', etc.)
        enabled: Whether the menu is enabled.

    Note:
        More fields (hotkey, tag, etc.) may be added in future versions.

    Stability: Experimental
    """

    name: str
    mode: str | None = None
    enabled: bool = True


def find_pm(name: str) -> PMHandle | None:
    """Find a Pie Menu by name.

    Args:
        name: The exact name of the menu to find.

    Returns:
        PMHandle if found, None otherwise.

    Example:
        >>> pm = pme.find_pm("My Pie Menu")
        >>> if pm:
        ...     print(f"Found: {pm.name} ({pm.mode})")

    Stability: Experimental
    """
    prefs = get_prefs()
    if prefs is None:
        return None

    pie_menus = getattr(prefs, "pie_menus", None)
    if pie_menus is None or name not in pie_menus:
        return None

    pm = pie_menus[name]
    return PMHandle(
        name=pm.name,
        mode=getattr(pm, "mode", None),
        enabled=getattr(pm, "enabled", True),
    )


def list_pms(mode: str | None = None) -> list[PMHandle]:
    """List all Pie Menus, optionally filtered by mode.

    Args:
        mode: Filter by menu type ('PMENU', 'RMENU', 'DIALOG', etc.)
              If None, returns all menus.

    Returns:
        List of PMHandle objects.

    Example:
        >>> all_menus = pme.list_pms()
        >>> pie_menus = pme.list_pms(mode='PMENU')

    Stability: Experimental
    """
    prefs = get_prefs()
    if prefs is None:
        return []

    pie_menus = getattr(prefs, "pie_menus", None)
    if pie_menus is None:
        return []

    result = []
    for pm in pie_menus:
        pm_mode = getattr(pm, "mode", None)
        if mode is None or pm_mode == mode:
            result.append(PMHandle(
                name=pm.name,
                mode=pm_mode,
                enabled=getattr(pm, "enabled", True),
            ))
    return result


def invoke_pm(pm_or_name: PMHandle | str) -> bool:
    """Invoke (show) a Pie Menu.

    This opens the specified menu as if the user triggered its hotkey.

    Args:
        pm_or_name: Either a PMHandle or the menu name as string.

    Returns:
        True if the menu was invoked successfully, False otherwise.

    Example:
        >>> # By name
        >>> pme.invoke_pm("My Pie Menu")

        >>> # By handle
        >>> pm = pme.find_pm("My Pie Menu")
        >>> if pm:
        ...     pme.invoke_pm(pm)

    Note:
        The menu must exist and be enabled. The current context must be
        appropriate for the menu (e.g., correct editor type).

    Stability: Experimental
    """
    name = pm_or_name.name if isinstance(pm_or_name, PMHandle) else pm_or_name

    try:
        bpy.ops.wm.pme_user_pie_menu_call('INVOKE_DEFAULT', pie_menu_name=name)
        return True
    except Exception:
        return False


# =============================================================================
# Namespace Validation (Debug Utilities)
# =============================================================================
# These functions help verify that the namespace is correctly configured.
# Use with DBG_DEPS or during development to catch configuration issues.


def validate_public_namespace(globals_dict: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """Validate that the public namespace is correctly configured.

    Checks:
    1. All PUBLIC_NAMES variables are present in the globals dict
    2. No INTERNAL variables are accidentally exposed with public-looking names

    Args:
        globals_dict: The globals dict to validate. If None, uses gen_globals().

    Returns:
        A dict with 'missing' and 'warnings' lists:
        - missing: Public variables that should be present but aren't
        - warnings: Potential issues (e.g., internal vars that might confuse users)

    Example:
        >>> issues = pme.validate_public_namespace()
        >>> if issues['missing']:
        ...     print(f"Missing public vars: {issues['missing']}")

    Stability: Internal (debug utility)
    """
    if globals_dict is None:
        globals_dict = context.gen_globals()

    present_names = set(globals_dict.keys())

    # Check for missing public variables
    missing = [name for name in PUBLIC_NAMES if name not in present_names]

    # Check for potential confusion (internal vars that look important)
    # These are not errors, just warnings for documentation purposes
    warnings = []
    suspicious_internal = {"PME", "PREFS", "pme_context"}
    for name in suspicious_internal:
        if name in present_names and is_internal(name):
            warnings.append(f"'{name}' is internal but exposed (document as internal)")

    return {"missing": missing, "warnings": warnings}


def get_namespace_report() -> str:
    """Generate a human-readable report of the current namespace configuration.

    Useful for debugging and documentation.

    Returns:
        Multi-line string describing the namespace state.

    Stability: Internal (debug utility)
    """
    globals_dict = context.gen_globals()
    present = set(globals_dict.keys())

    lines = ["=== PME Namespace Report ===", ""]

    # Public variables
    lines.append("Public (Experimental):")
    for name in sorted(PUBLIC_NAMES):
        status = "✓" if name in present else "✗ MISSING"
        info = NAMESPACE_PUBLIC.get(name, {})
        desc = info.get("desc", "")
        lines.append(f"  {status} {name}: {desc}")

    lines.append("")

    # Internal variables present
    lines.append("Internal (present in globals):")
    internal_present = [n for n in present if is_internal(n)]
    for name in sorted(internal_present)[:10]:  # Limit to first 10
        lines.append(f"  - {name}")
    if len(internal_present) > 10:
        lines.append(f"  ... and {len(internal_present) - 10} more")

    lines.append("")
    lines.append(f"Total variables in namespace: {len(present)}")
    lines.append(f"Public: {len(PUBLIC_NAMES)}, Internal: {len(internal_present)}")

    return "\n".join(lines)


def register():
    context.add_global("U", UserData())
