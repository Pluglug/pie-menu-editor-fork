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
# - This layer is a thin facade over submodules
# - Implementation lives in execution.py, menu.py, validation.py
# - Blender runtime dependencies live in infra/, not here
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

# =============================================================================
# Public API exports
# =============================================================================

__all__ = [
    # Execution (from execution.py)
    "execute",
    "evaluate",
    "check_syntax",
    "ExecuteResult",
    "SyntaxResult",
    # Menu API (from menu.py)
    "PMHandle",
    "find_pm",
    "list_pms",
    "list_tags",
    "invoke_pm",
    # Validation API (from validation.py) - top-level access
    "validate_json",
    "ValidationResult",
    # UID utilities (from core)
    "validate_uid",
    # User Properties
    "props",
    # Preferences
    "preferences",
    # Context (backward compat)
    "context",
    # Submodules
    "constants",
    "dev",
    "validation",
]

# =============================================================================
# Re-exports from submodules
# =============================================================================

# Types (public)
from ._types import (
    ExecuteResult,
    PMHandle,
    SyntaxResult,
    ValidationIssue,
    ValidationResult,
)

# Execution API
from .execution import execute, evaluate, check_syntax

# Menu API
from .menu import find_pm, list_pms, invoke_pm, list_tags

# Validation API
from .validation import validate_json
from . import validation

# Constants submodule
from . import constants

# Developer utilities submodule
from . import dev

# UID utilities (from core layer)
from ..core.uid import validate_uid

# =============================================================================
# Internal imports for backward compatibility
# =============================================================================

# Runtime context (internal, from infra layer)
# Not exported in __all__, but available for backward compatibility
from ..infra.runtime_context import (
    context as context,
    UserData as UserData,
    PMEContext as PMEContext,
)

# Schema (internal - used by debug utilities)
from ..core.schema import (
    SchemaProp,
    SchemaRegistry,
    schema,
    ParsedData,
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
        from ..addon import get_prefs
        return get_prefs()

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
        from ..addon import get_prefs
        prefs = get_prefs()
        return getattr(prefs, "props", None) if prefs else None


_proxy = _PreferencesProxy()


# =============================================================================
# Module-level __getattr__ for lazy property access
# =============================================================================


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


def _validate_public_namespace(globals_dict: dict | None = None) -> dict[str, list[str]]:
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


def __dir__():
    """Control what appears in dir() and autocomplete.

    Only show public API symbols, not internal imports like bpy, Any, etc.
    """
    return __all__
