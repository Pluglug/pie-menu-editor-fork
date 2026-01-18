# pyright: reportInvalidTypeForm=false
"""
GPU Execution Utilities

ExecutionFrame provides a stable L/C/E namespace during a script run.
"""

from __future__ import annotations

from typing import Any, Optional


class ExecutionFrame:
    """Context manager for stable script execution globals."""

    def __init__(
        self,
        pme_context: Any,
        context: Any,
        event: Optional[Any] = None,
        layout: Optional[Any] = None,
        context_tracker: Optional[Any] = None,
        bpy_proxy: Optional[Any] = None,
    ):
        self.pme_context = pme_context
        self.context = context
        self.event = event
        self.layout = layout
        self.context_tracker = context_tracker
        self.bpy_proxy = bpy_proxy

        self._saved_layout = None
        self._saved_event = None
        self._saved_C = None
        self._saved_bpy = None

    def __enter__(self):
        self._saved_layout = self.pme_context.layout
        self._saved_event = self.pme_context.event
        self._saved_C = self.pme_context._globals.get("C")
        self._saved_bpy = self.pme_context._globals.get("bpy")

        self.pme_context.layout = self.layout
        self.pme_context.event = self.event

        if self.context_tracker is not None:
            self.pme_context._globals["C"] = self.context_tracker

        if self.bpy_proxy is not None:
            self.pme_context._globals["bpy"] = self.bpy_proxy

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pme_context.layout = self._saved_layout
        self.pme_context.event = self._saved_event
        self.pme_context._globals["C"] = self._saved_C
        self.pme_context._globals["bpy"] = self._saved_bpy
        return False


__all__ = ["ExecutionFrame"]
