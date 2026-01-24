# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Vector Widget

配列プロパティ（location, rotation, scale など）を複数の NumberItem として
表示するコンポジットウィジェット。水平・垂直両方のレイアウトに対応。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from ..style import GPULayoutStyle
from ..drawing import BLFDrawing
from .base import LayoutItem
from .inputs import NumberItem

if TYPE_CHECKING:
    from ..interactive import ItemRenderState


@dataclass
class VectorItem(LayoutItem):
    """
    ベクトル入力 (XYZ 等)

    複数の NumberItem を配置して配列プロパティを編集。
    vertical=False (デフォルト) で水平、vertical=True で垂直に配置。

    Attributes:
        value: 現在値 (タプル)
        labels: 各要素のラベル ('X', 'Y', 'Z' など)
        min_val: 最小値
        max_val: 最大値
        step: ドラッグ時の変化量
        precision: 表示精度
        text: 全体のラベル（空の場合はラベルなし）
        vertical: True で垂直配置（column レイアウト用）
        on_change: 値変更時のコールバック（全体のタプルを渡す）
    """
    value: tuple[float, ...] = (0.0, 0.0, 0.0)
    labels: tuple[str, ...] = ("X", "Y", "Z")
    min_val: float = -float('inf')
    max_val: float = float('inf')
    step: float = 0.01
    precision: int = 3
    text: str = ""
    vertical: bool = False
    on_change: Optional[Callable[[tuple[float, ...]], None]] = None

    # 内部: 各要素の NumberItem（描画時に生成）
    _items: list[NumberItem] = field(default_factory=list, repr=False)
    _items_initialized: bool = field(default=False, repr=False)

    def __post_init__(self):
        # ラベル数と値の長さを一致させる
        if len(self.labels) < len(self.value):
            self.labels = self.labels + tuple(
                str(i) for i in range(len(self.labels), len(self.value))
            )

    def _ensure_items(self, style: GPULayoutStyle) -> None:
        """内部 NumberItem を初期化"""
        if self._items_initialized and len(self._items) == len(self.value):
            return

        self._items = []
        for i, (val, label) in enumerate(zip(self.value, self.labels)):
            def make_on_change(index: int):
                def on_change(new_val: float):
                    self._update_element(index, new_val)
                return on_change

            item = NumberItem(
                value=float(val),
                min_val=self.min_val,
                max_val=self.max_val,
                step=self.step,
                precision=self.precision,
                text=label,
                on_change=make_on_change(i),
                enabled=self.enabled,
            )
            self._items.append(item)

        self._items_initialized = True

    def _update_element(self, index: int, new_val: float) -> None:
        """特定要素を更新し、全体のコールバックを呼ぶ"""
        value_list = list(self.value)
        if 0 <= index < len(value_list):
            value_list[index] = new_val
            self.value = tuple(value_list)
            if self.on_change:
                self.on_change(self.value)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """サイズを計算"""
        self._ensure_items(style)

        item_height = style.scaled_item_height()
        spacing = style.scaled_spacing()
        item_count = len(self._items)

        if self.vertical:
            # 垂直: 幅はそのまま、高さは要素数分
            total_height = item_height * item_count + spacing * max(0, item_count - 1)
            return (self.width, total_height)
        else:
            # 水平: 高さは1行分
            # 全体のラベル幅
            label_width = 0.0
            if self.text:
                text_size = style.scaled_text_size()
                label_w, _ = BLFDrawing.get_text_dimensions(self.text + ":", text_size)
                label_width = label_w + style.scaled_padding() * 2

            # 最小幅: ラベル + (NumberItem × n) + spacing × (n-1)
            min_item_width = style.ui_scale(60)  # 各要素の最小幅
            total_width = (
                label_width
                + min_item_width * item_count
                + spacing * max(0, item_count - 1)
            )

            return (max(self.width, total_width), item_height)

    def get_value(self) -> tuple[float, ...]:
        """ValueWidget Protocol 準拠"""
        return self.value

    def set_value(self, value: tuple[float, ...]) -> None:
        """ValueWidget Protocol 準拠"""
        self.value = tuple(float(v) for v in value)
        # 内部 NumberItem も更新
        for i, item in enumerate(self._items):
            if i < len(self.value):
                item.value = self.value[i]

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """描画"""
        if not self.visible:
            return

        self._ensure_items(style)

        enabled = state.enabled if state else self.enabled

        if self.vertical:
            self._draw_vertical(style, state, enabled)
        else:
            self._draw_horizontal(style, state, enabled)

    def _draw_horizontal(
        self, style: GPULayoutStyle, state: Optional[ItemRenderState], enabled: bool
    ) -> None:
        """水平レイアウトで描画"""
        # 全体のラベルを描画
        current_x = self.x
        item_height = style.scaled_item_height()

        if self.text:
            text_size = style.scaled_text_size()
            label_text = self.text + ":"
            text_w, text_h = BLFDrawing.get_text_dimensions(label_text, text_size)
            text_color = style.text_color if enabled else style.text_color_disabled
            text_y = self.y - (item_height + text_h) / 2
            BLFDrawing.draw_text(current_x, text_y, label_text, text_color, text_size)
            current_x += text_w + style.scaled_padding() * 2

        # 残り幅を NumberItem で分割
        remaining_width = self.width - (current_x - self.x)
        spacing = style.scaled_spacing()
        item_count = len(self._items)

        if item_count > 0:
            item_width = (remaining_width - spacing * (item_count - 1)) / item_count

            for i, item in enumerate(self._items):
                # 位置とサイズを設定
                item.x = current_x
                item.y = self.y
                item.width = item_width
                item.height = item_height
                item.enabled = enabled

                # 値を同期
                if i < len(self.value):
                    item.value = self.value[i]

                # corners を設定（align=True スタイル: 端のみ角丸）
                if item_count == 1:
                    item.corners = self.corners
                elif i == 0:
                    # 最初の要素: 左側のみ角丸
                    item.corners = (self.corners[0], self.corners[1], False, False)
                elif i == item_count - 1:
                    # 最後の要素: 右側のみ角丸
                    item.corners = (False, False, self.corners[2], self.corners[3])
                else:
                    # 中間要素: 角丸なし
                    item.corners = (False, False, False, False)

                # 描画
                item.draw(style, state)

                current_x += item_width + spacing

    def _draw_vertical(
        self, style: GPULayoutStyle, state: Optional[ItemRenderState], enabled: bool
    ) -> None:
        """垂直レイアウトで描画"""
        item_height = style.scaled_item_height()
        spacing = style.scaled_spacing()
        item_count = len(self._items)
        current_y = self.y

        for i, item in enumerate(self._items):
            # 位置とサイズを設定
            item.x = self.x
            item.y = current_y
            item.width = self.width
            item.height = item_height
            item.enabled = enabled

            # 値を同期
            if i < len(self.value):
                item.value = self.value[i]

            # corners を設定（align=True スタイル: 上下の端のみ角丸）
            if item_count == 1:
                item.corners = self.corners
            elif i == 0:
                # 最初の要素: 上側のみ角丸
                item.corners = (False, self.corners[1], self.corners[2], False)
            elif i == item_count - 1:
                # 最後の要素: 下側のみ角丸
                item.corners = (self.corners[0], False, False, self.corners[3])
            else:
                # 中間要素: 角丸なし
                item.corners = (False, False, False, False)

            # 描画
            item.draw(style, state)

            current_y -= item_height + spacing

    def get_child_items(self) -> list[LayoutItem]:
        """子ウィジェットを返す（イベント処理用）"""
        return list(self._items)
