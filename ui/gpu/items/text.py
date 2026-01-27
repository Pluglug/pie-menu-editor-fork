# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Text/Display Items
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..style import GPULayoutStyle, Alignment
from ..drawing import GPUDrawing, BLFDrawing, IconDrawing
from .base import LayoutItem


@dataclass
class LabelItem(LayoutItem):
    """ラベル（テキスト表示）"""
    text: str = ""
    icon: str = "NONE"
    alignment: Alignment = Alignment.LEFT
    text_color: Optional[tuple[float, float, float, float]] = None
    alert: bool = False
    wrap: bool = False

    def can_align(self) -> bool:
        return False

    def _label_unit_x(self, style: GPULayoutStyle) -> float:
        return float(style.scaled_item_height())

    def _label_text_padding(self, style: GPULayoutStyle) -> float:
        return self._label_unit_x(style) * 0.4

    def _label_width_margin(self, style: GPULayoutStyle) -> float:
        return self._label_unit_x(style) * 0.25

    def _label_alignment_padding(self, style: GPULayoutStyle) -> float:
        if self.alignment in (Alignment.LEFT, Alignment.RIGHT, Alignment.EXPAND):
            return self._label_text_padding(style)
        return 0.0

    def _get_wrapped_lines(self, style: GPULayoutStyle, width: float) -> list[str]:
        if not self.wrap:
            return [self.text]

        icon_size = style.scaled_icon_size() if self.icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if self.icon != "NONE" else 0
        padding = self._label_alignment_padding(style)
        text_area_width = max(0.0, width - icon_size - icon_spacing - padding)
        if text_area_width <= 0:
            return [""]

        text_size = style.scaled_text_size()
        return BLFDrawing.wrap_text(self.text, text_area_width, text_size)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_size = style.scaled_icon_size()
        icon_w = icon_size + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = self._label_alignment_padding(style)
        width_margin = self._label_width_margin(style)
        return (text_w + icon_w + padding + width_margin, max(text_h, style.scaled_item_height()))

    def calc_size_for_width(self, style: GPULayoutStyle, width: float) -> tuple[float, float]:
        if not self.wrap:
            return self.calc_size(style)

        lines = self._get_wrapped_lines(style, width)
        text_size = style.scaled_text_size()
        text_h = BLFDrawing.get_text_dimensions("Wg", text_size)[1]
        line_height = max(text_h, style.scaled_item_height())
        height = line_height * max(1, len(lines))

        max_line_width = 0.0
        for line in lines:
            line_w, _ = BLFDrawing.get_text_dimensions(line, text_size)
            max_line_width = max(max_line_width, line_w)

        icon_size = style.scaled_icon_size() if self.icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if self.icon != "NONE" else 0
        padding = self._label_alignment_padding(style)
        width_margin = self._label_width_margin(style)
        measured_width = max_line_width + icon_size + icon_spacing + padding + width_margin
        return (min(width, measured_width) if width > 0 else measured_width, height)

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 色の決定: alert > text_color > enabled/disabled
        if self.alert:
            color = style.alert_color
        elif self.text_color:
            color = self.text_color
        elif self.enabled:
            color = style.text_color
        else:
            color = style.text_color_disabled
        text_size = style.scaled_text_size()

        # コンテンツサイズを計算
        icon_size = style.scaled_icon_size() if self.icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if self.icon != "NONE" else 0
        padding = self._label_alignment_padding(style)

        clip_rect = self.get_clip_rect()

        if self.wrap:
            lines = self._get_wrapped_lines(style, self.width)
            text_h = BLFDrawing.get_text_dimensions("Wg", text_size)[1]
            line_height = max(text_h, style.scaled_item_height())

            for index, line in enumerate(lines):
                # アイコンは最初の行のみ描画
                line_icon_size = icon_size if index == 0 else 0
                line_icon_spacing = icon_spacing if index == 0 else 0

                line_w, _ = BLFDrawing.get_text_dimensions(line, text_size)
                content_w = line_icon_size + line_icon_spacing + line_w

                if self.alignment == Alignment.CENTER:
                    content_x = self.x + (self.width - content_w) / 2
                elif self.alignment == Alignment.RIGHT:
                    content_x = self.x + self.width - content_w - padding
                else:  # LEFT or EXPAND
                    content_x = self.x + padding

                line_top = self.y - line_height * index
                text_y = line_top - (line_height + text_h) / 2

                text_x = content_x
                if index == 0 and self.icon != "NONE":
                    icon_y = line_top - (line_height - icon_size) / 2
                    alpha = 1.0 if self.enabled else 0.5
                    IconDrawing.draw_icon(content_x, icon_y, self.icon, alpha=alpha)
                    text_x += icon_size + icon_spacing

                if style.text_shadow_enabled:
                    BLFDrawing.draw_text_clipped_with_shadow(
                        text_x, text_y, line, color, text_size, clip_rect,
                        style.text_shadow_color, style.text_shadow_alpha,
                        style.scaled_text_shadow_offset()
                    )
                else:
                    BLFDrawing.draw_text_clipped(text_x, text_y, line, color, text_size, clip_rect)
            return

        # テキストの利用可能幅を計算（アイコンとスペーシングを除く）
        text_area_width = self.width - icon_size - icon_spacing - padding

        # テキストが利用可能幅を超える場合は省略記号を追加
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, text_area_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        content_w = icon_size + icon_spacing + text_w

        # alignment に応じた X 位置を計算
        if self.alignment == Alignment.CENTER:
            content_x = self.x + (self.width - content_w) / 2
        elif self.alignment == Alignment.RIGHT:
            content_x = self.x + self.width - content_w - padding
        else:  # LEFT or EXPAND
            content_x = self.x + padding

        # テキスト位置（Y は baseline）
        text_y = self.y - (self.height + text_h) / 2

        # アイコン描画
        text_x = content_x
        if self.icon != "NONE":
            # アイコンを垂直方向に中央揃え
            icon_y = self.y - (self.height - icon_size) / 2
            alpha = 1.0 if self.enabled else 0.5
            IconDrawing.draw_icon(content_x, icon_y, self.icon, alpha=alpha)
            text_x += icon_size + icon_spacing

        # テキスト（クリッピング付き）
        if style.text_shadow_enabled:
            BLFDrawing.draw_text_clipped_with_shadow(
                text_x, text_y, display_text, color, text_size, clip_rect,
                style.text_shadow_color, style.text_shadow_alpha,
                style.scaled_text_shadow_offset()
            )
        else:
            BLFDrawing.draw_text_clipped(text_x, text_y, display_text, color, text_size, clip_rect)


@dataclass
class SeparatorItem(LayoutItem):
    """区切り線"""
    factor: float = 1.0

    def can_align(self) -> bool:
        return False

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        return (self.width, int(style.scaled_spacing() * self.factor * 2))

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        y = self.y - self.height / 2
        GPUDrawing.draw_line(
            self.x, y,
            self.x + self.width, y,
            style.separator_color, 1.0  # セパレーターは固定太さ
        )


@dataclass
class PropDisplayItem(LayoutItem):
    """プロパティ値の表示（読み取り専用）

    Attributes:
        data: プロパティを持つオブジェクト
        property: プロパティ名
        text: 表示ラベル（None=プロパティ名を使用、""=ラベルなし）
        icon: アイコン名
    """
    data: Any = None
    property: str = ""
    text: Optional[str] = None  # None=プロパティ名、""=ラベルなし
    icon: str = "NONE"

    def can_align(self) -> bool:
        return False

    def _get_value(self) -> str:
        """プロパティ値を文字列で取得"""
        if self.data is None:
            return "N/A"
        try:
            value = getattr(self.data, self.property)
            if isinstance(value, float):
                return f"{value:.3f}"
            elif isinstance(value, (list, tuple)):
                return ", ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in value)
            return str(value)
        except AttributeError:
            return "N/A"

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        # text=None → プロパティ名、text="" → ラベルなし
        label = self.property if self.text is None else self.text
        value = self._get_value()
        display_text = f"{label}: {value}" if label else value
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, style.scaled_text_size())
        return (text_w, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # text=None → プロパティ名、text="" → ラベルなし
        label = self.property if self.text is None else self.text
        value = self._get_value()

        text_size = style.scaled_text_size()
        _, text_h = BLFDrawing.get_text_dimensions("Wg", text_size)
        text_y = self.y - (self.height + text_h) / 2

        # enabled 状態に応じた色
        label_color = style.text_color_secondary if self.enabled else style.text_color_disabled
        value_color = style.text_color if self.enabled else style.text_color_disabled

        # クリップ矩形を取得
        clip_rect = self.get_clip_rect()

        if label:
            # ラベルあり: 「ラベル: 値」形式
            label_text = f"{label}: "
            max_label_width = self.width * 0.5
            display_label = BLFDrawing.get_text_with_ellipsis(label_text, max_label_width, text_size)
            label_w, _ = BLFDrawing.get_text_dimensions(display_label, text_size)
            BLFDrawing.draw_text_clipped(self.x, text_y, display_label, label_color, text_size, clip_rect)

            # 値（残り幅で省略記号を追加）
            available_width = self.width - label_w
            display_value = BLFDrawing.get_text_with_ellipsis(value, available_width, text_size)
            BLFDrawing.draw_text_clipped(self.x + label_w, text_y, display_value, value_color, text_size, clip_rect)
        else:
            # ラベルなし: 値のみ表示
            display_value = BLFDrawing.get_text_with_ellipsis(value, self.width, text_size)
            BLFDrawing.draw_text_clipped(self.x, text_y, display_value, value_color, text_size, clip_rect)


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Items - インタラクティブ
# ═══════════════════════════════════════════════════════════════════════════════
