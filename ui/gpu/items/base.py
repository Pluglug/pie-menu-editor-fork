# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Base Layout Item
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..style import GPULayoutStyle, SizingPolicy
from ..drawing import BLFDrawing

if TYPE_CHECKING:
    from bpy.types import Event


@dataclass
class LayoutItem:
    """レイアウトアイテムの基底クラス"""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    visible: bool = True
    enabled: bool = True
    # Phase 2: LayoutKey support
    layout_path: str = ""
    key: str = ""

    # Phase 2: 角丸制御（align=True 時に使用）
    # (bottomLeft, topLeft, topRight, bottomRight)
    # True = 角丸あり、False = 直角
    corners: tuple[bool, bool, bool, bool] = (True, True, True, True)

    # corners が明示的に設定され、レイアウト計算で上書きしない
    corners_locked: bool = False

    # Phase 1 v3: width sizing policy (measure results, fixed width)
    sizing: SizingPolicy = field(default_factory=SizingPolicy)

    # Phase 1 v3: estimated height (measure phase)
    estimated_height: float = 0.0

    # Phase 1 v3: EXPAND 時に幅を拡張するかどうか
    # False = 自然幅を維持（ラベル等）、True = 幅を拡張（ボタン等）
    expand_width: bool = True

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """サイズを計算して返す (width, height)"""
        return (self.width, self.height)

    def calc_size_for_width(self, style: GPULayoutStyle, width: float) -> tuple[float, float]:
        """幅制約に基づくサイズを計算して返す (width, height)"""
        return self.calc_size(style)

    def draw(self, style: GPULayoutStyle) -> None:
        """描画"""
        pass

    def can_align(self) -> bool:
        """Whether this item participates in align-group corner stitching."""
        return True

    def is_inside(self, x: float, y: float) -> bool:
        """座標がアイテム内かどうか"""
        return (self.x <= x <= self.x + self.width and
                self.y - self.height <= y <= self.y)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        """イベント処理"""
        return False

    def get_clip_rect(self, padding: int = 0) -> tuple[float, float, float, float]:
        """
        このアイテムのクリップ矩形を取得

        Args:
            padding: 内側のパディング

        Returns:
            (xmin, ymin, xmax, ymax) - blf.clipping 用の矩形
        """
        return BLFDrawing.calc_clip_rect(self.x, self.y, self.width, self.height, padding)
