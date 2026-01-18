# pyright: reportInvalidTypeForm=false
"""
GPU Reactive Binding Utilities

Provides resolve_context_path, ContextResolverCache, and PropertyBinding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple

from .rna_utils import get_enum_display_name, get_property_value


def resolve_context_path(context: Any, path: str) -> Any:
    """Resolve a safe context path like 'context.object.data'."""
    if not path or not path.startswith("context."):
        return None

    obj = context
    for part in path.split(".")[1:]:
        try:
            obj = getattr(obj, part)
        except Exception:
            return None
        if obj is None:
            return None

    return obj


class ContextResolverCache:
    """Per-epoch cache for resolved context paths."""

    def __init__(self):
        self._epoch = -1
        self._cache: dict[str, Any] = {}

    def begin_tick(self, epoch: int) -> None:
        if self._epoch != epoch:
            self._epoch = epoch
            self._cache.clear()

    def resolve(self, context: Any, path: str) -> Any:
        if path in self._cache:
            return self._cache[path]
        value = resolve_context_path(context, path)
        self._cache[path] = value
        return value


@dataclass
class PropertyBinding:
    """Bind a layout widget to a context-resolved RNA property."""

    resolve_data: Callable[[Any], Any]
    set_value: Callable[[Any, Any], None]
    prop_name: str
    widget: Any
    meta: dict = field(default_factory=dict)
    _last_enum_items: Optional[Tuple[tuple, ...]] = field(
        default=None, repr=False
    )

    def sync(self, context: Any) -> tuple[bool, bool]:
        """Sync widget from context. Returns (value_changed, needs_relayout)."""
        data = self.resolve_data(context)
        if data is None:
            was_enabled = getattr(self.widget, "enabled", True)
            if hasattr(self.widget, "enabled"):
                self.widget.enabled = False
            return bool(was_enabled), False

        if hasattr(self.widget, "enabled"):
            self.widget.enabled = True

        value = get_property_value(data, self.prop_name)
        value_changed = self._update_widget(value, data)

        needs_relayout = False
        if self.meta.get("is_dynamic_enum"):
            items = self._get_enum_items(data)
            if items != self._last_enum_items:
                self._last_enum_items = items
                needs_relayout = True

        return value_changed, needs_relayout

    def _update_widget(self, value: Any, data: Any) -> bool:
        if self.meta.get("is_dynamic_enum") and hasattr(self.widget, "text"):
            prefix = self.meta.get("label_prefix", "")
            display_name = get_enum_display_name(
                data, self.prop_name, str(value)
            )
            text = f"{prefix}: {display_name}" if prefix else display_name
            if getattr(self.widget, "text", None) != text:
                self.widget.text = text
                return True
            return False

        if hasattr(self.widget, "value"):
            old_value = self.widget.value
            if isinstance(old_value, bool):
                new_value = bool(value)
            elif hasattr(self.widget, "options"):
                new_value = str(value) if value else ""
            elif isinstance(old_value, (int, float)):
                new_value = float(value) if value is not None else 0.0
            else:
                new_value = value

            if old_value != new_value:
                self.widget.value = new_value
                return True
            return False

        if hasattr(self.widget, "color"):
            new_color = None
            if isinstance(value, (list, tuple)):
                if len(value) == 3:
                    new_color = (value[0], value[1], value[2], 1.0)
                elif len(value) >= 4:
                    new_color = tuple(value[:4])
            if new_color is not None and self.widget.color != new_color:
                self.widget.color = new_color
                return True

        return False

    def _get_enum_items(self, data: Any) -> tuple:
        prop = None
        try:
            prop = data.rna_type.properties.get(self.prop_name)
        except Exception:
            prop = None
        if prop and hasattr(prop, "enum_items"):
            try:
                items = tuple(
                    (item.identifier, item.name) for item in prop.enum_items
                )
                if items:
                    return items
            except Exception:
                pass

        try:
            prop = data.bl_rna.properties.get(self.prop_name)
        except Exception:
            prop = None

        if prop and hasattr(prop, "enum_items"):
            try:
                return tuple(
                    (item.identifier, item.name) for item in prop.enum_items
                )
            except Exception:
                return ()

        return ()


__all__ = [
    "ContextResolverCache",
    "PropertyBinding",
    "resolve_context_path",
]
