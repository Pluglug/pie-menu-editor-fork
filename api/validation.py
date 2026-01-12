# api/validation.py - JSON Validation API
# LAYER = "api"
#
# Provides validation for PME JSON data before import.
# Useful for AI-generated content, manual edits, and third-party tools.
#
# Example:
#     >>> import pme
#     >>> result = pme.validate_json(json_string)
#     >>> if not result.valid:
#     ...     print(result.format_report())

"""PME JSON Validation API.

This module provides validation for PME JSON data before import.
Supports PME1 and PME2 formats.

Example:
    >>> import pme
    >>> result = pme.validate_json(json_string)
    >>> print(result.format_report())

Stability: Experimental
"""

LAYER = "api"

import json
from typing import Any

from .pme_types import ValidationIssue, ValidationResult

__all__ = [
    "validate",
    "validate_json",
    "validate_file",
    "ValidationIssue",
    "ValidationResult",
    "ERROR_CODES",
]

# =============================================================================
# Error Codes
# =============================================================================

ERROR_CODES = {
    # Syntax (1xx)
    "E101": "Invalid JSON syntax",
    "E102": "Empty file or data",
    # Root structure (2xx)
    "E201": "Missing $schema field",
    "E202": "Missing schema_version field",
    "E203": "Unknown schema version",
    "E204": "Missing menus array",
    "E205": "menus is not an array",
    # Menu (3xx)
    "E301": "Missing uid field",
    "E302": "Invalid uid format",
    "E303": "Duplicate uid",
    "E304": "Missing name field",
    "E305": "Invalid menu mode",
    "E306": "Missing items array",
    "E307": "items is not an array",
    # Item (4xx)
    "E401": "Missing action field",
    "E402": "Invalid action type",
    "E403": "Missing action value",
    "E404": "Invalid action structure",
    # Hotkey (5xx)
    "E501": "Invalid key name",
    "E502": "Invalid activation mode",
    # Reference (6xx)
    "E601": "Menu reference not found",
    "E602": "Circular menu reference",
    # Warnings (Wxxx)
    "W101": "Deprecated field",
    "W102": "Duplicate menu name",
    "W103": "Empty items array",
    "W104": "Unknown field (will be ignored)",
    "W201": "Unknown extension vendor",
    "W301": "PME1 format detected (will be converted)",
}


# =============================================================================
# Validation API
# =============================================================================


def validate(
    data: dict[str, Any],
    *,
    strict: bool = False,
    check_references: bool = True,
) -> ValidationResult:
    """Validate parsed PME JSON data.

    Args:
        data: Already-parsed JSON dict.
        strict: If True, treat warnings as errors.
        check_references: Verify menu uid references exist within the data.

    Returns:
        ValidationResult with detailed error/warning information.

    Example:
        >>> data = json.loads(json_string)
        >>> result = pme.validation.validate(data)
        >>> if result.valid:
        ...     print("Ready to import!")

    Stability: Experimental
    """
    # Placeholder - will be implemented with Schema v2
    # For now, just do basic structure check
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    schema_version: str | None = None
    menu_count = 0

    if not data:
        errors.append(ValidationIssue(
            severity="error",
            code="E102",
            path="",
            message="Empty data",
        ))
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Detect format
    if isinstance(data, list):
        # PME1 legacy format (list of tuples)
        warnings.append(ValidationIssue(
            severity="warning",
            code="W301",
            path="",
            message="PME1 legacy format detected (will be converted on import)",
        ))
        menu_count = len(data)
    elif isinstance(data, dict):
        # PME1 dict or PME2 format
        if "$schema" in data:
            # PME2 format
            schema_version = data.get("schema_version")
        elif "menus" in data:
            # PME1 dict format
            warnings.append(ValidationIssue(
                severity="warning",
                code="W301",
                path="",
                message="PME1 format detected (will be converted on import)",
            ))

        menus = data.get("menus", [])
        if isinstance(menus, list):
            menu_count = len(menus)

    valid = len(errors) == 0
    if strict and warnings:
        valid = False

    return ValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
        schema_version=schema_version,
        menu_count=menu_count,
    )


def validate_json(
    json_string: str,
    *,
    strict: bool = False,
    check_references: bool = True,
) -> ValidationResult:
    """Validate PME JSON string before import.

    This is the main entry point for JSON validation.

    Args:
        json_string: JSON string to validate.
        strict: If True, treat warnings as errors.
        check_references: Verify menu uid references exist.

    Returns:
        ValidationResult with detailed error/warning information.

    Example:
        >>> result = pme.validate_json(json_string)
        >>> if not result.valid:
        ...     for err in result.errors:
        ...         print(f"{err.path}: {err.message}")

    Stability: Experimental
    """
    errors: list[ValidationIssue] = []

    if not json_string or not json_string.strip():
        errors.append(ValidationIssue(
            severity="error",
            code="E102",
            path="",
            message="Empty JSON string",
        ))
        return ValidationResult(valid=False, errors=errors)

    # Parse JSON
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        errors.append(ValidationIssue(
            severity="error",
            code="E101",
            path="",
            message=f"Invalid JSON: {e.msg} (line {e.lineno}, column {e.colno})",
        ))
        return ValidationResult(valid=False, errors=errors)

    return validate(data, strict=strict, check_references=check_references)


def validate_file(
    filepath: str,
    *,
    strict: bool = False,
    check_references: bool = True,
) -> ValidationResult:
    """Validate a PME JSON file.

    Convenience wrapper that handles file reading.

    Args:
        filepath: Path to the JSON file.
        strict: If True, treat warnings as errors.
        check_references: Verify menu uid references exist.

    Returns:
        ValidationResult with file-specific error handling.

    Example:
        >>> result = pme.validation.validate_file("/path/to/menu.json")
        >>> if result.valid:
        ...     print(f"Valid! {result.menu_count} menus found")

    Stability: Experimental
    """
    errors: list[ValidationIssue] = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            json_string = f.read()
    except FileNotFoundError:
        errors.append(ValidationIssue(
            severity="error",
            code="E101",
            path="",
            message=f"File not found: {filepath}",
        ))
        return ValidationResult(valid=False, errors=errors)
    except PermissionError:
        errors.append(ValidationIssue(
            severity="error",
            code="E101",
            path="",
            message=f"Permission denied: {filepath}",
        ))
        return ValidationResult(valid=False, errors=errors)
    except Exception as e:
        errors.append(ValidationIssue(
            severity="error",
            code="E101",
            path="",
            message=f"Failed to read file: {e}",
        ))
        return ValidationResult(valid=False, errors=errors)

    return validate_json(json_string, strict=strict, check_references=check_references)


# =============================================================================
# Autocomplete control
# =============================================================================


def __dir__():
    """Control what appears in dir() and autocomplete."""
    return __all__
