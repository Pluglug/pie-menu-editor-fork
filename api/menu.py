# api/menu.py - Menu Integration API
# LAYER = "api"
#
# Provides menu discovery and invocation for external tools.
#
# Example:
#     >>> import pme
#     >>> pm = pme.find_pm("My Pie Menu")
#     >>> if pm:
#     ...     pme.invoke_pm(pm)

"""PME Menu Integration API.

This module provides menu discovery, listing, and invocation.

Example:
    >>> import pme
    >>> for pm in pme.list_pms(mode='PMENU'):
    ...     print(f"{pm.name} ({pm.uid})")

Stability: Experimental
"""

LAYER = "api"

import bpy

from ._types import PMHandle

__all__ = [
    "find_pm",
    "list_pms",
    "invoke_pm",
    "list_tags",
]


def _get_prefs():
    """Get PME addon preferences."""
    from ..addon import get_prefs
    return get_prefs()


# =============================================================================
# Menu Discovery API
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
# Menu Invocation API
# =============================================================================


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


# =============================================================================
# Autocomplete control
# =============================================================================


def __dir__():
    """Control what appears in dir() and autocomplete."""
    return __all__
