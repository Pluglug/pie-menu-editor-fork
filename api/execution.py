# api/execution.py - Code Execution API
# LAYER = "api"
#
# Provides code execution and syntax validation with PME's standard namespace.
#
# Example:
#     >>> import pme
#     >>> result = pme.execute("print(C.mode)")
#     >>> if not result.success:
#     ...     print(result.error_message)

"""PME Code Execution API.

This module provides code execution and syntax validation
with PME's standard namespace (C, D, bpy, E, L, U, etc.).

Example:
    >>> import pme
    >>> result = pme.execute("overlay('Hello!')")
    >>> mode = pme.evaluate("C.mode")

Stability: Experimental
"""

LAYER = "api"

import ast
from typing import Any

from ._types import ExecuteResult, SyntaxResult

__all__ = [
    "execute",
    "evaluate",
    "check_syntax",
]


# =============================================================================
# Execution API
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
    # Import here to avoid circular imports and allow lazy loading
    from ..infra.runtime_context import context

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
    from ..infra.runtime_context import context

    globals_dict = context.gen_globals()
    if extra_globals:
        globals_dict.update(extra_globals)

    return eval(expr, globals_dict)


# =============================================================================
# Syntax Validation API
# =============================================================================


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
        ast.parse(code, mode=mode)
        return SyntaxResult(valid=True)
    except SyntaxError as e:
        return SyntaxResult(
            valid=False,
            error=e.msg,
            line=e.lineno,
            column=e.offset,
        )
