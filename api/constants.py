# api/constants.py - Public constants for PME API
# LAYER = "api"
#
# This module exposes menu and item mode constants for external tools.
# These are stable and unlikely to change.

"""PME Public Constants.

This module provides stable constants for menu types and item modes.

Example:
    >>> import pme
    >>> pme.constants.MENU_MODES
    ('PMENU', 'RMENU', 'DIALOG', 'SCRIPT', 'PANEL', 'HPANEL', 'STICKY', 'MACRO', 'MODAL', 'PROPERTY')

    >>> # Filter by mode
    >>> pie_menus = pme.list_pms(mode=pme.constants.PMENU)

Stability: Stable
"""

LAYER = "api"

# =============================================================================
# Menu Mode Constants
# =============================================================================

# Individual menu modes
PMENU = "PMENU"
RMENU = "RMENU"
DIALOG = "DIALOG"
SCRIPT = "SCRIPT"
PANEL = "PANEL"
HPANEL = "HPANEL"
STICKY = "STICKY"
MACRO = "MACRO"
MODAL = "MODAL"
PROPERTY = "PROPERTY"

# All menu modes as a tuple (for iteration/validation)
MENU_MODES = (
    PMENU,
    RMENU,
    DIALOG,
    SCRIPT,
    PANEL,
    HPANEL,
    STICKY,
    MACRO,
    MODAL,
    PROPERTY,
)

# Menu mode metadata: (id, label, icon)
MENU_MODE_DATA = (
    (PMENU, "Pie Menu", "MOD_SUBSURF"),
    (RMENU, "Regular Menu", "MOD_BOOLEAN"),
    (DIALOG, "Popup Dialog", "MOD_BUILD"),
    (SCRIPT, "Stack Key", "MOD_MIRROR"),
    (PANEL, "Panel Group", "MOD_MULTIRES"),
    (HPANEL, "Hidden Panel Group", "MOD_TRIANGULATE"),
    (STICKY, "Sticky Key", "MOD_WARP"),
    (MACRO, "Macro Operator", "MOD_ARRAY"),
    (MODAL, "Modal Operator", "MOD_BEVEL"),
    (PROPERTY, "Property", "MOD_SCREW"),
)

# =============================================================================
# Item Mode Constants
# =============================================================================

# Individual item modes
COMMAND = "COMMAND"
PROP = "PROP"
MENU = "MENU"
HOTKEY = "HOTKEY"
CUSTOM = "CUSTOM"
EMPTY = "EMPTY"

# Modal-specific item modes
INVOKE = "INVOKE"
FINISH = "FINISH"
CANCEL = "CANCEL"
UPDATE = "UPDATE"

# All item modes as a tuple
ITEM_MODES = (
    EMPTY,
    COMMAND,
    PROP,
    MENU,
    HOTKEY,
    CUSTOM,
    INVOKE,
    FINISH,
    CANCEL,
    UPDATE,
)

# =============================================================================
# Tag Constants
# =============================================================================

UNTAGGED = "Untagged"


# =============================================================================
# Helper Functions
# =============================================================================

def get_mode_label(mode: str) -> str:
    """Get the human-readable label for a menu mode.

    Args:
        mode: Menu mode identifier (e.g., 'PMENU', 'RMENU')

    Returns:
        Human-readable label, or the mode itself if not found.

    Example:
        >>> pme.constants.get_mode_label('PMENU')
        'Pie Menu'
    """
    for id_, label, _ in MENU_MODE_DATA:
        if id_ == mode:
            return label
    return mode


def get_mode_icon(mode: str) -> str:
    """Get the icon name for a menu mode.

    Args:
        mode: Menu mode identifier (e.g., 'PMENU', 'RMENU')

    Returns:
        Blender icon name, or 'NONE' if not found.

    Example:
        >>> pme.constants.get_mode_icon('PMENU')
        'MOD_SUBSURF'
    """
    for id_, _, icon in MENU_MODE_DATA:
        if id_ == mode:
            return icon
    return "NONE"


def is_valid_mode(mode: str) -> bool:
    """Check if a string is a valid menu mode.

    Args:
        mode: String to check

    Returns:
        True if valid menu mode, False otherwise.
    """
    return mode in MENU_MODES
