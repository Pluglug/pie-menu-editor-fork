# api/_types.py - Public API type definitions
# LAYER = "api"
#
# This module contains data classes used by the public API.
# These are intentionally simple and stable.

LAYER = "api"

from dataclasses import dataclass
from typing import Any


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
