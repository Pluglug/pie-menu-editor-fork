# api/dev.py - PME Developer Utilities
# LAYER = "api"
#
# This module provides developer-facing utilities for:
# - External tool authors (Gizmo Creator, etc.)
# - PME contributors
# - Advanced users who need namespace introspection
#
# Access via: pme.dev.*
#
# Example:
#     >>> import pme
#     >>> pme.dev.is_public("C")
#     True
#     >>> pme.dev.get_stability("C")
#     <Stability.EXPERIMENTAL: 'experimental'>

"""PME Developer Utilities.

This module provides tools for PME developers and external tool authors.

Example:
    >>> import pme
    >>> pme.dev.is_public("C")      # Check if variable is public
    True
    >>> pme.dev.get_stability("C")  # Get stability level
    <Stability.EXPERIMENTAL: 'experimental'>
    >>> print(pme.dev.namespace_report())  # Debug output
"""

LAYER = "api"

from typing import Any

# Re-export from core.namespace
from ..core.namespace import (
    Stability,
    is_public,
    is_internal,
    get_stability,
    get_public_names_by_stability,
    PUBLIC_NAMES,
    NAMESPACE_PUBLIC,
    NAMESPACE_INTERNAL,
)

__all__ = [
    # Stability enum
    "Stability",
    # Introspection functions
    "is_public",
    "is_internal",
    "get_stability",
    "get_public_names_by_stability",
    # Debug utilities
    "validate_namespace",
    "namespace_report",
    # Constants (for advanced use)
    "PUBLIC_NAMES",
]


def __dir__():
    """Control what appears in dir() and autocomplete."""
    return __all__


def validate_namespace(globals_dict: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """Validate that the public namespace is correctly configured.

    Args:
        globals_dict: Optional globals dict to validate. If None, uses
                      the current PME context globals.

    Returns:
        Dict with 'missing' and 'warnings' lists.

    Example:
        >>> result = pme.dev.validate_namespace()
        >>> if result['missing']:
        ...     print(f"Missing: {result['missing']}")
    """
    from ..infra.runtime_context import context

    if globals_dict is None:
        globals_dict = context.gen_globals()

    present_names = set(globals_dict.keys())

    # Check for missing public variables
    missing = [name for name in PUBLIC_NAMES if name not in present_names]

    # Check for potential confusion (internal vars that look important)
    warnings = []
    suspicious_internal = {"PME", "PREFS", "pme_context"}
    for name in suspicious_internal:
        if name in present_names and is_internal(name):
            warnings.append(f"'{name}' is internal but exposed (document as internal)")

    return {"missing": missing, "warnings": warnings}


def namespace_report() -> str:
    """Generate a human-readable report of the current namespace configuration.

    Returns:
        Multi-line string with namespace status.

    Example:
        >>> print(pme.dev.namespace_report())
        === PME Namespace Report ===
        ...
    """
    from ..infra.runtime_context import context

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
