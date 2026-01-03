# core/namespace.py - Standard namespace definitions for PME execution context
# LAYER = "core"
#
# This module defines the PUBLIC namespace variables that external tools
# can depend on when using PME as a command execution engine.
#
# IMPORTANT: This module is Blender-independent. It only defines WHAT
# variables exist, not their actual values (which are set by pme.py and
# other modules at runtime).
#
# See: _docs/design/api/pme_standard_namespace.md

LAYER = "core"


class Stability:
    """Stability levels for API symbols.

    Determines the compatibility guarantee for each symbol.
    External tools should only depend on EXPERIMENTAL or STABLE symbols.
    """

    EXPERIMENTAL = "experimental"
    """
    May change in future versions. Feedback welcome.
    All v2.0.0 APIs start at this level.
    External tools can use these, but should be prepared for changes.
    """

    INTERNAL = "internal"
    """
    Do not depend on. May change or be removed without notice.
    These exist for PME's internal implementation.
    """

    STABLE = "stable"
    """
    Compatibility guaranteed within v2.x series.
    Only assigned after proven usage in v2.1.0+.
    """


# =============================================================================
# Public Namespace Definitions
# =============================================================================
# Variables that external tools (like Gizmo Creator) can depend on.
# All are EXPERIMENTAL in v2.0.0.

NAMESPACE_CORE = {
    "bpy": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Blender Python module",
        "available": "always",
    },
    "C": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Blender context (bpy.context or proxy)",
        "available": "always",
    },
    "D": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Blender data (bpy.data)",
        "available": "always",
    },
}
"""Core Blender API shortcuts. Always available."""


NAMESPACE_EVENT = {
    "E": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Current Blender event",
        "available": "when event context exists",
    },
    "delta": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Mouse wheel delta (1, -1, or 0)",
        "available": "when event context exists",
    },
    "drag_x": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Mouse drag X offset from start",
        "available": "during drag operations",
    },
    "drag_y": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Mouse drag Y offset from start",
        "available": "during drag operations",
    },
}
"""Event-related variables. Available when event context exists."""


NAMESPACE_USER = {
    "U": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "User data container (session-only, not persisted)",
        "available": "always after registration",
    },
}
"""User data storage. Session-scoped, lost on Blender restart."""


NAMESPACE_UI = {
    "L": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Current UILayout for drawing",
        "available": "during UI drawing only",
    },
    "text": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Current item's display text",
        "available": "during PM/PMI execution",
    },
    "icon": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Current item's icon name",
        "available": "during PM/PMI execution",
    },
    "icon_value": {
        "stability": Stability.EXPERIMENTAL,
        "desc": "Current item's icon integer value",
        "available": "during PM/PMI execution",
    },
}
"""UI drawing variables. Available during specific contexts."""


# =============================================================================
# Aggregated Public Namespace
# =============================================================================

NAMESPACE_PUBLIC = {
    **NAMESPACE_CORE,
    **NAMESPACE_EVENT,
    **NAMESPACE_USER,
    **NAMESPACE_UI,
}
"""All public namespace variables that external tools can depend on."""


# Names only (for quick membership checks)
PUBLIC_NAMES = frozenset(NAMESPACE_PUBLIC.keys())


# =============================================================================
# Internal Namespace (DO NOT DEPEND ON)
# =============================================================================
# These variables exist in the execution context but are not part of
# the public API. They may change or be removed without notice.

NAMESPACE_INTERNAL = frozenset({
    # PME internal state
    "pme_context",
    "pme",
    "PME",
    "PREFS",
    "prefs",
    "_prefs",
    "get_prefs",
    "temp_prefs",
    "PMEData",

    # Blender API shortcuts (internal convenience)
    "T",            # bpy.types
    "O",            # bpy.ops
    "P",            # bpy.props
    "context",      # bpy.context alias
    "bl_context",   # Another context alias

    # Standard library modules
    "sys",
    "os",
    "re",
    "traceback",

    # Property shortcuts
    "BoolProperty",
    "IntProperty",
    "FloatProperty",
    "StringProperty",
    "EnumProperty",
    "CollectionProperty",
    "PointerProperty",
    "FloatVectorProperty",

    # UI helpers
    "lh",           # LayoutHelper
    "operator",
    "tag_redraw",
    "panel",
    "message_box",
    "input_box",
    "close_popups",
    "header_menu",
    "draw_menu",
    "open_menu",
    "execute_script",
    "toggle_menu",
    "custom_icon",
    "overlay",

    # Screen/Area helpers
    "focus_area",
    "move_header",
    "toggle_sidebar",
    "override_context",
    "redraw_screen",
    "exec_with_override",

    # Execution helpers
    "SK",           # StackKey
    "call_operator",
    "find_by",
    "keep_pie_open",
    "props",        # From editors/property.py

    # Paint helpers
    "paint_settings",
    "unified_paint_panel",
    "ups",
    "brush",

    # Autorun script functions
    "setattr",      # Custom setattr that returns True
    "try_setattr",
    "event_mods",
    "raise_error",
})
"""Internal variables. External tools MUST NOT depend on these."""


# =============================================================================
# Utilities
# =============================================================================

def is_public(name: str) -> bool:
    """Check if a variable name is part of the public namespace."""
    return name in PUBLIC_NAMES


def is_internal(name: str) -> bool:
    """Check if a variable name is internal (should not be exposed)."""
    return name in NAMESPACE_INTERNAL


def get_stability(name: str) -> str | None:
    """Get the stability level of a public variable.

    Returns None if the variable is not in the public namespace.
    """
    if name in NAMESPACE_PUBLIC:
        return NAMESPACE_PUBLIC[name]["stability"]
    return None


def get_public_names_by_stability(stability: str) -> frozenset[str]:
    """Get all public variable names with the given stability level."""
    return frozenset(
        name for name, info in NAMESPACE_PUBLIC.items()
        if info["stability"] == stability
    )
