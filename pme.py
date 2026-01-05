# pme.py - PME Legacy Shim (backward compatibility)
# LAYER = "infra"
#
# This module is a backward-compatibility shim for `from pie_menu_editor import pme`.
# New code should use `import pme` (which returns the api/ package via sys.modules alias).
#
# The canonical public API is now in api/__init__.py.
# The execution context lives in infra/runtime_context.py.
# This module re-exports from both for backward compatibility.
#
# Phase 8-D: Issue #85
# https://github.com/Pluglug/pie-menu-editor-fork/issues/85
#
# DEPRECATION NOTICE:
# - Direct use of pme.context is deprecated. Use pme.execute() / pme.evaluate() instead.
# - pme.context.add_global() still works for backward compatibility.
# - NAMESPACE_*, PUBLIC_NAMES, validate_public_namespace, get_namespace_report
#   are not recommended for external use.

"""PME Legacy Shim.

This module provides backward compatibility for code that uses:
    from pie_menu_editor import pme

New code should use:
    import pme

The canonical public API is in pie_menu_editor.api.
The execution context is in pie_menu_editor.infra.runtime_context.
"""

LAYER = "infra"

# =============================================================================
# Re-export from api/ package (public API)
# =============================================================================

# Public API functions
from .api import (
    # Execution
    execute,
    evaluate,
    ExecuteResult,
    # Menu API
    PMHandle,
    find_pm,
    list_pms,
    invoke_pm,
    # Schema
    schema,
    SchemaRegistry,
    SchemaProp,
    ParsedData,
    # Deprecated aliases (backward compat)
    props,
    PMEProp,
    PMEProps,
    # Stability / Namespace introspection
    Stability,
    get_stability,
    is_public,
    is_internal,
    get_public_names_by_stability,
)

# =============================================================================
# Re-export from infra/runtime_context.py (execution context)
# =============================================================================
# These are deprecated for external use, but needed for backward compatibility
# and internal PME code.

from .infra.runtime_context import context, UserData, PMEContext

# =============================================================================
# Namespace re-exports (for backward compatibility)
# =============================================================================
# These are not recommended for external use, but some internal code
# may depend on them being available via pme.NAMESPACE_*

from .core.namespace import (
    NAMESPACE_CORE,
    NAMESPACE_EVENT,
    NAMESPACE_USER,
    NAMESPACE_UI,
    NAMESPACE_PUBLIC,
    NAMESPACE_INTERNAL,
    PUBLIC_NAMES,
)


# =============================================================================
# Debug utilities (deprecated, use api._validate_public_namespace instead)
# =============================================================================

def validate_public_namespace(globals_dict=None):
    """Validate that the public namespace is correctly configured.

    DEPRECATED: This function is for internal debugging only.
    """
    from .api import _validate_public_namespace
    return _validate_public_namespace(globals_dict)


def get_namespace_report():
    """Generate a human-readable report of the current namespace configuration.

    DEPRECATED: This function is for internal debugging only.
    """
    from .api import _get_namespace_report
    return _get_namespace_report()


# =============================================================================
# Registration
# =============================================================================


def register():
    """Register the pme module.

    NOTE: This is intentionally empty. The actual registration is handled by
    api.register() which is called directly by the module loader.

    pme.py is a legacy shim for backward compatibility and will be removed
    in a future version.
    """
    pass


def unregister():
    """Unregister the pme module."""
    pass
