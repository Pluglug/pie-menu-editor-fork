# api/pme_types.py - Public API type definitions
# LAYER = "api"
#
# This module contains data classes used by the public API.
# These are intentionally simple and stable.
#
# File is named pme_types.py to avoid collision with stdlib 'types'.
# Aliased as 'types' in __init__.py for clean access: pme.types.ExecuteResult

"""PME Public Types.

This module provides data classes for API return values.
Similar to bpy.types, but for PME-specific types.

Example:
    >>> import pme
    >>> result = pme.execute("print('hello')")
    >>> isinstance(result, pme.types.ExecuteResult)
    True

Stability: Experimental
"""

LAYER = "api"

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ExecuteResult",
    "SyntaxResult",
    "PMHandle",
    "ValidationIssue",
    "ValidationResult",
]


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
class SyntaxResult:
    """Result of syntax validation.

    Attributes:
        valid: True if syntax is valid.
        error: Error message if invalid, None otherwise.
        line: Line number where error occurred (1-indexed), None if valid.
        column: Column number where error occurred (1-indexed), None if valid.

    Example:
        >>> result = pme.check_syntax("print('hello')")
        >>> result.valid
        True

        >>> result = pme.check_syntax("print(")
        >>> result.valid
        False
        >>> result.error
        'unexpected EOF while parsing'

    Stability: Experimental
    """

    valid: bool
    error: str | None = None
    line: int | None = None
    column: int | None = None


@dataclass
class PMHandle:
    """Read-only handle to a Pie Menu.

    This is a lightweight wrapper that provides safe access to PM metadata
    without exposing the internal PMItem object directly.

    Attributes:
        name: The display name of the menu (can be changed by user).
        mode: The menu type ('PMENU', 'RMENU', 'DIALOG', etc.)
        enabled: Whether the menu is enabled.
        uid: Unique identifier (stable reference, e.g., "pm_9f7c2k3h").
        tag: Comma-separated tags (e.g., "Modeling, Sculpt").

    Note:
        More fields (hotkey, etc.) may be added in future versions.
        Use `uid` for stable references; `name` can change.

    Stability: Experimental
    """

    name: str
    mode: str | None = None
    enabled: bool = True
    uid: str = ""
    tag: str = ""


# =============================================================================
# JSON Validation Types (Experimental)
# =============================================================================


@dataclass
class ValidationIssue:
    """A single validation issue found in JSON data.

    Attributes:
        severity: Issue severity - "error" (blocks import) or "warning" (importable).
        code: Machine-readable error code (e.g., "E301", "W102").
        path: JSON path to the problematic field (e.g., "menus[0].items[2].action").
        message: Human-readable description of the issue.
        suggestion: Optional fix suggestion.

    Example:
        >>> issue = ValidationIssue(
        ...     severity="error",
        ...     code="E305",
        ...     path="menus[0].mode",
        ...     message="Invalid menu mode: 'PIE'",
        ...     suggestion="Use 'PMENU' instead of 'PIE'"
        ... )

    Stability: Experimental
    """

    severity: str  # "error" | "warning"
    code: str
    path: str
    message: str
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Result of JSON validation.

    Attributes:
        valid: True if no errors found (warnings are acceptable).
        errors: List of critical issues that prevent import.
        warnings: List of non-critical issues (import possible but not ideal).
        schema_version: Detected schema version, if parseable.
        menu_count: Number of menus found in the data.

    Example:
        >>> result = pme.validate_json(json_string)
        >>> if result.valid:
        ...     print(f"Valid! {result.menu_count} menus")
        ... else:
        ...     for err in result.errors:
        ...         print(f"{err.path}: {err.message}")

    Stability: Experimental
    """

    valid: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    schema_version: str | None = None
    menu_count: int = 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def issue_count(self) -> int:
        """Total number of issues (errors + warnings)."""
        return len(self.errors) + len(self.warnings)

    def format_report(self, *, include_warnings: bool = True, max_issues: int = 50) -> str:
        """Format a human-readable validation report.

        Args:
            include_warnings: Whether to include warnings in the report.
            max_issues: Maximum number of issues to show (0 = unlimited).

        Returns:
            Formatted multi-line string report.
        """
        lines = []

        if self.valid:
            lines.append(f"✓ Valid ({self.menu_count} menus)")
            if self.schema_version:
                lines.append(f"  Schema version: {self.schema_version}")
        else:
            lines.append(f"✗ Invalid ({len(self.errors)} errors)")

        if self.errors:
            lines.append("")
            lines.append("Errors:")
            shown = 0
            for err in self.errors:
                if max_issues and shown >= max_issues:
                    lines.append(f"  ... and {len(self.errors) - shown} more errors")
                    break
                lines.append(f"  [{err.code}] {err.path}: {err.message}")
                if err.suggestion:
                    lines.append(f"         → {err.suggestion}")
                shown += 1

        if include_warnings and self.warnings:
            lines.append("")
            lines.append("Warnings:")
            shown = 0
            for warn in self.warnings:
                if max_issues and shown >= max_issues:
                    lines.append(f"  ... and {len(self.warnings) - shown} more warnings")
                    break
                lines.append(f"  [{warn.code}] {warn.path}: {warn.message}")
                if warn.suggestion:
                    lines.append(f"         → {warn.suggestion}")
                shown += 1

        return "\n".join(lines)


# =============================================================================
# Autocomplete control
# =============================================================================


def __dir__():
    """Control what appears in dir() and autocomplete."""
    return __all__
