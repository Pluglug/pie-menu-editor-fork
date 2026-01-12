# api/__init__.py - PME Public API Facade
# LAYER = "api"
#
# This module provides the canonical public API for PME.
# External tools should use `import pme` to access this module.
#
# The sys.modules["pme"] alias is installed in register() so that
# `import pme` works regardless of the underlying package path
# (including Blender Extensions).
#
# Design principles:
# - This layer is a thin facade over infra/runtime_context.py
# - Blender runtime dependencies live in infra/, not here
# - PMEContext is NOT exposed in __all__ (internal implementation)
#
# Example:
#     >>> import pme
#     >>> pme.execute("print(C.mode)")
#     >>> pm = pme.find_pm("My Pie Menu")
#     >>> if pm:
#     ...     pme.invoke_pm(pm)
#
# Phase 8-D: Issue #85
# https://github.com/Pluglug/pie-menu-editor-fork/issues/85

"""PME Public API Facade.

This module provides a stable interface for external tools and user scripts.
Use `import pme` to access this API.

Example:
    >>> import pme
    >>> result = pme.execute("print(C.mode)")
    >>> if not result.success:
    ...     print(f"Error: {result.error_message}")

Stability: All APIs in v2.0.0 are Experimental.
"""

LAYER = "api"

from typing import Any

import bpy

# =============================================================================
# Public API exports
# =============================================================================

__all__ = [
    # Execution
    "execute",
    "evaluate",
    "ExecuteResult",
    # Syntax validation
    "check_syntax",
    "SyntaxResult",
    # Menu API
    "PMHandle",
    "find_pm",
    "list_pms",
    "list_tags",
    "invoke_pm",
    # UID utilities
    "validate_uid",
    # User Properties
    "props",  # User-defined properties container (PropertyGroup)
    # Preferences
    "preferences",  # PME preferences access
    # Context (backward compat)
    "context",  # PMEContext singleton for add_global()
    # Constants (submodule)
    "constants",  # pme.constants.* - menu modes, item modes
    # Developer utilities (submodule)
    "dev",  # pme.dev.* - namespace introspection, debugging
]

# =============================================================================
# Internal imports
# =============================================================================

# Types (public)
from ._types import ExecuteResult, PMHandle, SyntaxResult

# Constants submodule (public)
from . import constants

# UID utilities (public, from core layer)
from ..core.uid import validate_uid

# Runtime context (internal, from infra layer)
# Not exported in __all__, but available for backward compatibility
from ..infra.runtime_context import (
    context as context,  # For pme.context backward compat
    UserData as UserData,  # For pme.UserData backward compat
    PMEContext as PMEContext,  # For pme.PMEContext backward compat
)

# Schema (internal - used by debug utilities)
from ..core.schema import (
    SchemaProp,
    SchemaRegistry,
    schema,
    ParsedData,
)

# Addon utilities (internal)
from ..addon import get_prefs as _get_prefs

# Developer utilities submodule
from . import dev


# =============================================================================
# Execution API (Experimental)
# =============================================================================


def execute(code: str, *, extra_globals: dict[str, Any] | None = None) -> ExecuteResult:
    """Execute arbitrary Python code with PME's standard namespace.

    The standard namespace includes: C, D, bpy, E, L, U, delta, drag_x, drag_y,
    and other PME-provided variables.

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


def find_pm(name: str | None = None, *, uid: str | None = None) -> PMHandle | None:
    """Find a Pie Menu by name or uid.

    Args:
        name: The exact name of the menu to find.
        uid: The unique identifier of the menu (e.g., "pm_9f7c2k3h").
             If both name and uid are provided, uid takes precedence.

    Returns:
        PMHandle if found, None otherwise.

    Example:
        >>> # By name
        >>> pm = pme.find_pm("My Pie Menu")
        >>> if pm:
        ...     print(f"Found: {pm.name} ({pm.mode})")

        >>> # By uid (stable reference)
        >>> pm = pme.find_pm(uid="pm_9f7c2k3h")

    Stability: Experimental
    """
    prefs = _get_prefs()
    if prefs is None:
        return None

    pie_menus = getattr(prefs, "pie_menus", None)
    if pie_menus is None:
        return None

    pm = None

    # Search by uid first (stable reference)
    if uid:
        for p in pie_menus:
            if getattr(p, "uid", "") == uid:
                pm = p
                break
    # Fall back to name search
    elif name and name in pie_menus:
        pm = pie_menus[name]

    if pm is None:
        return None

    return PMHandle(
        name=pm.name,
        mode=getattr(pm, "mode", None),
        enabled=getattr(pm, "enabled", True),
        uid=getattr(pm, "uid", ""),
        tag=getattr(pm, "tag", ""),
    )


def list_pms(mode: str | None = None, *, enabled_only: bool = False) -> list[PMHandle]:
    """List all Pie Menus, optionally filtered by mode and enabled state.

    Args:
        mode: Filter by menu type ('PMENU', 'RMENU', 'DIALOG', etc.)
              If None, returns all menus.
        enabled_only: If True, only return enabled menus.

    Returns:
        List of PMHandle objects (includes uid, tag for stable references).

    Example:
        >>> all_menus = pme.list_pms()
        >>> for pm in all_menus:
        ...     print(f"{pm.name} ({pm.uid}) tags={pm.tag}")

        >>> pie_menus = pme.list_pms(mode='PMENU', enabled_only=True)

    Stability: Experimental
    """
    prefs = _get_prefs()
    if prefs is None:
        return []

    pie_menus = getattr(prefs, "pie_menus", None)
    if pie_menus is None:
        return []

    result = []
    for pm in pie_menus:
        pm_mode = getattr(pm, "mode", None)
        pm_enabled = getattr(pm, "enabled", True)

        # Apply filters
        if mode is not None and pm_mode != mode:
            continue
        if enabled_only and not pm_enabled:
            continue

        result.append(PMHandle(
            name=pm.name,
            mode=pm_mode,
            enabled=pm_enabled,
            uid=getattr(pm, "uid", ""),
            tag=getattr(pm, "tag", ""),
        ))
    return result


def invoke_pm(
    pm_or_name: PMHandle | str | None = None,
    *,
    name: str | None = None,
    uid: str | None = None,
) -> bool:
    """Invoke (show) a Pie Menu.

    This opens the specified menu as if the user triggered its hotkey.

    Args:
        pm_or_name: PMHandle, menu name, or None (for backward compatibility).
        name: The menu name to invoke (keyword argument).
        uid: The menu uid to invoke (keyword argument, e.g., "pm_9f7c2k3h").
             If uid is provided, it takes precedence over name.

    Returns:
        True if the menu was invoked successfully, False otherwise.

    Example:
        >>> # By name (positional - backward compatible)
        >>> pme.invoke_pm("My Pie Menu")

        >>> # By name (keyword)
        >>> pme.invoke_pm(name="My Pie Menu")

        >>> # By uid (stable reference)
        >>> pme.invoke_pm(uid="pm_9f7c2k3h")

        >>> # By handle
        >>> pm = pme.find_pm("My Pie Menu")
        >>> if pm:
        ...     pme.invoke_pm(pm)

    Note:
        The menu must exist and be enabled. The current context must be
        appropriate for the menu (e.g., correct editor type).

    Stability: Experimental
    """
    menu_name = None

    # Resolve the menu name
    if isinstance(pm_or_name, PMHandle):
        menu_name = pm_or_name.name
    elif isinstance(pm_or_name, str):
        menu_name = pm_or_name
    elif uid:
        # Search by uid
        pm = find_pm(uid=uid)
        if pm:
            menu_name = pm.name
    elif name:
        menu_name = name

    if not menu_name:
        return False

    try:
        bpy.ops.wm.pme_user_pie_menu_call('INVOKE_DEFAULT', pie_menu_name=menu_name)
        return True
    except Exception:
        return False


def list_tags() -> list[str]:
    """List all tags currently used by menus.

    Returns:
        Sorted list of unique tag names. Does not include 'Untagged'.

    Example:
        >>> tags = pme.list_tags()
        >>> print(tags)
        ['Modeling', 'Sculpt', 'UV']

    Stability: Experimental
    """
    prefs = _get_prefs()
    if prefs is None:
        return []

    pie_menus = getattr(prefs, "pie_menus", None)
    if pie_menus is None:
        return []

    tags = set()
    for pm in pie_menus:
        pm_tag = getattr(pm, "tag", "")
        if pm_tag:
            for t in pm_tag.split(","):
                t = t.strip()
                if t:
                    tags.add(t)

    return sorted(tags)


# =============================================================================
# Syntax Validation API (Experimental)
# =============================================================================

import ast as _ast


def check_syntax(code: str, *, mode: str = "exec") -> SyntaxResult:
    """Check Python code syntax without executing it.

    Uses ast.parse() for Pythonic syntax validation.

    Args:
        code: Python code to validate.
        mode: Parsing mode - 'exec' for statements (default), 'eval' for expressions.

    Returns:
        SyntaxResult with validation status and error details if invalid.

    Example:
        >>> result = pme.check_syntax("print('hello')")
        >>> result.valid
        True

        >>> result = pme.check_syntax("x = ", mode="exec")
        >>> result.valid
        False
        >>> result.error
        'invalid syntax'
        >>> result.line
        1

        >>> # For expressions only
        >>> result = pme.check_syntax("2 + 2", mode="eval")
        >>> result.valid
        True

    Stability: Experimental
    """
    if not code.strip():
        return SyntaxResult(valid=True)

    try:
        _ast.parse(code, mode=mode)
        return SyntaxResult(valid=True)
    except SyntaxError as e:
        return SyntaxResult(
            valid=False,
            error=e.msg,
            line=e.lineno,
            column=e.offset,
        )



# =============================================================================
# Preferences & Properties Access (Experimental)
# =============================================================================


class _PreferencesProxy:
    """Lazy proxy for PME preferences access.

    This allows `pme.preferences` and `pme.props` to work even when
    the addon is not yet fully registered.
    """

    @property
    def preferences(self):
        """Access PME addon preferences.

        Returns:
            PMEPreferences object, or None if addon not registered.

        Example:
            >>> prefs = pme.preferences
            >>> prefs.debug_mode = True

        Stability: Experimental
        """
        return _get_prefs()

    @property
    def props(self):
        """Access user-defined properties container.

        This is the PropertyGroup where user-defined properties
        (created via Property Editor) are stored.

        Returns:
            PropertyGroup with user properties, or None if addon not registered.

        Example:
            >>> pme.props.MyCounter = 10
            >>> value = pme.props.MyCounter

        Stability: Experimental
        """
        prefs = _get_prefs()
        return getattr(prefs, "props", None) if prefs else None


_proxy = _PreferencesProxy()

# Module-level properties (accessed as pme.preferences, pme.props)
# These are defined as module attributes that delegate to the proxy


def __getattr__(name: str):
    """Module-level __getattr__ for lazy property access."""
    if name == "preferences":
        return _proxy.preferences
    if name == "props":
        return _proxy.props
    raise AttributeError(f"module 'pme' has no attribute '{name}'")


# =============================================================================
# Debug Utilities - moved to dev submodule
# =============================================================================
# Use pme.dev.validate_namespace() and pme.dev.namespace_report() instead.
# Legacy aliases for backward compatibility:

def _validate_public_namespace(globals_dict: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """DEPRECATED: Use pme.dev.validate_namespace() instead."""
    return dev.validate_namespace(globals_dict)


def _get_namespace_report() -> str:
    """DEPRECATED: Use pme.dev.namespace_report() instead."""
    return dev.namespace_report()


# =============================================================================
# Registration
# =============================================================================


def register():
    """Register the API module.

    NOTE: This is intentionally empty. The actual registration is handled by
    infra.runtime_context.register() which is called directly by the module loader.

    api/ is a thin facade and does not need its own registration logic.
    """
    pass


def unregister():
    """Unregister the API module."""
    pass


# =============================================================================
# Autocomplete control
# =============================================================================
# Override __dir__ to control what appears in autocomplete.
# This keeps the module namespace clean for external users.


def __dir__():
    """Control what appears in dir() and autocomplete.

    Only show public API symbols, not internal imports like bpy, Any, etc.
    """
    return __all__
