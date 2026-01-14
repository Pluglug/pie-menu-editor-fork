# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Layout Items

各種 UI 要素（ラベル、ボタン、セパレーター等）の定義。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

from .style import GPULayoutStyle, Alignment
from .drawing import GPUDrawing, BLFDrawing, IconDrawing

if TYPE_CHECKING:
    from bpy.types import Event
    from .interactive import ItemRenderState


# ═══════════════════════════════════════════════════════════════════════════════
# Base Layout Item
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LayoutItem:
    """レイアウトアイテムの基底クラス"""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    visible: bool = True
    enabled: bool = True

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """サイズを計算して返す (width, height)"""
        return (self.width, self.height)

    def draw(self, style: GPULayoutStyle) -> None:
        """描画"""
        pass

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


# ═══════════════════════════════════════════════════════════════════════════════
# Display Items - 表示専用
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LabelItem(LayoutItem):
    """ラベル（テキスト表示）"""
    text: str = ""
    icon: str = "NONE"
    alignment: Alignment = Alignment.LEFT
    text_color: Optional[tuple[float, float, float, float]] = None
    alert: bool = False

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_size = style.scaled_icon_size()
        icon_w = icon_size + style.scaled_spacing() if self.icon != "NONE" else 0
        return (text_w + icon_w, max(text_h, style.scaled_item_height()))

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

        # テキストの利用可能幅を計算（アイコンとスペーシングを除く）
        text_area_width = self.width - icon_size - icon_spacing

        # テキストが利用可能幅を超える場合は省略記号を追加
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, text_area_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        content_w = icon_size + icon_spacing + text_w

        # alignment に応じた X 位置を計算
        if self.alignment == Alignment.CENTER:
            content_x = self.x + (self.width - content_w) / 2
        elif self.alignment == Alignment.RIGHT:
            content_x = self.x + self.width - content_w
        else:  # LEFT or EXPAND
            content_x = self.x

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

        # クリップ矩形を取得（テキスト領域用）
        clip_rect = self.get_clip_rect()

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

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        return (self.width, int(style.scaled_spacing() * self.factor * 2))

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        y = self.y - self.height / 2
        GPUDrawing.draw_line(
            self.x, y,
            self.x + self.width, y,
            style.separator_color, 1.0
        )


@dataclass
class PropDisplayItem(LayoutItem):
    """プロパティ値の表示（読み取り専用）"""
    data: Any = None
    property: str = ""
    text: str = ""
    icon: str = "NONE"

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
        label = self.text or self.property
        value = self._get_value()
        display_text = f"{label}: {value}"
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, style.scaled_text_size())
        return (text_w, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        label = self.text or self.property
        value = self._get_value()

        text_size = style.scaled_text_size()
        _, text_h = BLFDrawing.get_text_dimensions("Wg", text_size)
        text_y = self.y - (self.height + text_h) / 2

        # enabled 状態に応じた色
        label_color = style.text_color_secondary if self.enabled else style.text_color_disabled
        value_color = style.text_color if self.enabled else style.text_color_disabled

        # クリップ矩形を取得
        clip_rect = self.get_clip_rect()

        # ラベル（最大でも幅の50%に制限）
        label_text = f"{label}: "
        max_label_width = self.width * 0.5
        display_label = BLFDrawing.get_text_with_ellipsis(label_text, max_label_width, text_size)
        label_w, _ = BLFDrawing.get_text_dimensions(display_label, text_size)
        BLFDrawing.draw_text_clipped(self.x, text_y, display_label, label_color, text_size, clip_rect)

        # 値（残り幅で省略記号を追加）
        available_width = self.width - label_w
        display_value = BLFDrawing.get_text_with_ellipsis(value, available_width, text_size)
        BLFDrawing.draw_text_clipped(self.x + label_w, text_y, display_value, value_color, text_size, clip_rect)


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Items - インタラクティブ
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ButtonItem(LayoutItem):
    """クリック可能なボタン"""
    text: str = ""
    icon: str = "NONE"
    on_click: Optional[Callable[[], None]] = None

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_size = style.scaled_icon_size()
        icon_w = icon_size + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = style.scaled_padding()
        return (text_w + icon_w + padding * 2, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        if not self.visible:
            return

        # 状態から色を決定
        pressed = state.pressed if state else False
        hovered = state.hovered if state else False
        enabled = state.enabled if state else self.enabled

        # 背景色
        if pressed:
            bg_color = style.button_press_color
        elif hovered:
            bg_color = style.button_hover_color
        else:
            bg_color = style.button_color

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.scaled_border_radius(), bg_color
        )

        # テキスト
        text_color = style.button_text_color if enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        padding = style.scaled_padding()

        # ボタン内で利用可能なテキスト幅（省略記号用）
        available_width = self.width - padding * 2
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        # クリップ矩形（ボタン全体、角丸背景がテキストを制約）
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class ToggleItem(LayoutItem):
    """トグルボタン（ON/OFF）"""
    text: str = ""
    icon: str = "NONE"
    icon_on: str = "NONE"
    icon_off: str = "NONE"
    value: bool = False
    on_toggle: Optional[Callable[[bool], None]] = None

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_size = style.scaled_icon_size()
        icon_w = icon_size + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = style.scaled_padding()
        return (text_w + icon_w + padding * 2, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        if not self.visible:
            return

        # 状態から色を決定
        hovered = state.hovered if state else False
        enabled = state.enabled if state else self.enabled

        # 背景色（ON 状態で強調）
        if self.value:
            bg_color = style.highlight_color if not hovered else tuple(
                min(1.0, c * 1.2) for c in style.highlight_color[:3]
            ) + (style.highlight_color[3],)
        else:
            bg_color = style.button_hover_color if hovered else style.button_color

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.scaled_border_radius(), bg_color
        )

        # テキスト
        text_color = style.button_text_color if enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        padding = style.scaled_padding()

        # ボタン内で利用可能なテキスト幅（省略記号用）
        available_width = self.width - padding * 2
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        # クリップ矩形（ボタン全体、角丸背景がテキストを制約）
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


# ═══════════════════════════════════════════════════════════════════════════════
# Container Items - コンテナ
# ═══════════════════════════════════════════════════════════════════════════════

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
