# pyright: reportInvalidTypeForm=false
"""
GPU Context Tracking Utilities

Provides ContextTracker and TrackedAccess to infer context paths without
changing user scripts.
"""

from __future__ import annotations

import bpy
from typing import Any, List, Optional


class TrackedAccess:
    """Proxy object that records context access paths."""

    __slots__ = ("_tracker", "_path", "_value")

    def __init__(self, tracker: "ContextTracker", path: str, value: Any):
        self._tracker = tracker
        self._path = path
        self._value = value

    def __getattr__(self, name: str):
        new_path = f"{self._path}.{name}"
        self._tracker.last_access = new_path
        try:
            value = getattr(self._value, name)
        except Exception:
            value = None
        return TrackedAccess(self._tracker, new_path, value)

    def __call__(self, *args, **kwargs):
        if callable(self._value):
            return self._value(*args, **kwargs)
        raise TypeError(f"'{type(self._value).__name__}' is not callable")

    def __eq__(self, other: Any) -> bool:
        other_value = other._value if isinstance(other, TrackedAccess) else other
        return self._value == other_value

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __iter__(self):
        if self._value is None:
            return iter(())
        try:
            return iter(self._value)
        except TypeError:
            return iter(())

    def __len__(self) -> int:
        try:
            return len(self._value)
        except Exception:
            return 0

    def __getitem__(self, key):
        if self._value is None:
            return None
        try:
            return self._value[key]
        except Exception:
            return None

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"TrackedAccess({self._path!r}, {self._value!r})"

    @property
    def unwrapped(self) -> Any:
        """Return the raw value."""
        return self._value


class ContextTracker:
    """Wraps bl_context and records access paths like context.object.data."""

    __slots__ = ("_bl_context", "last_access", "_access_log")

    def __init__(self, bl_context: Any):
        self._bl_context = bl_context
        self.last_access: Optional[str] = None
        self._access_log: List[str] = []

    def __getattr__(self, name: str):
        path = f"context.{name}"
        self.last_access = path
        self._access_log.append(path)
        try:
            value = getattr(self._bl_context, name)
        except Exception:
            value = None
        return TrackedAccess(self, path, value)

    def clear_tracking(self) -> None:
        """Clear last_access and the access log."""
        self.last_access = None
        self._access_log.clear()

    def get_access_log(self) -> List[str]:
        """Return a copy of the access log."""
        return list(self._access_log)


class BpyContextProxy:
    """Proxy bpy module that returns a custom context."""

    __slots__ = ("_context",)

    def __init__(self, context: Any):
        self._context = context

    def __getattr__(self, name: str):
        if name == "context":
            return self._context
        return getattr(bpy, name)


__all__ = ["BpyContextProxy", "ContextTracker", "TrackedAccess"]
