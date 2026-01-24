# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Container Items
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..style import GPULayoutStyle
from ..drawing import GPUDrawing
from .base import LayoutItem

if TYPE_CHECKING:
    from bpy.types import Event


@dataclass
class BoxItem(LayoutItem):
    """ボックス（枠線付きコンテナ）"""
    items: list[LayoutItem] = field(default_factory=list)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        if not self.items:
            return (self.width, style.scaled_padding_y() * 2)

        total_height = style.scaled_padding_y() * 2
        for item in self.items:
            _, h = item.calc_size(style)
            total_height += h + style.scaled_spacing()

        return (self.width, total_height)

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        border_radius = style.scaled_border_radius()

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            border_radius, style.bg_color
        )

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            border_radius, style.outline_color
        )

        # 子アイテム
        for item in self.items:
            item.draw(style)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        for item in self.items:
            if item.handle_event(event, mouse_x, mouse_y):
                return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Widget Items - ウィジェット（テーマカラー対応）
# ═══════════════════════════════════════════════════════════════════════════════
