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
        icon_w = IconDrawing.ICON_SIZE + style.scaled_spacing() if self.icon != "NONE" else 0
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
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, text_size)
        icon_size = IconDrawing.ICON_SIZE if self.icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if self.icon != "NONE" else 0
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

        # テキスト
        if style.text_shadow_enabled:
            BLFDrawing.draw_text_with_shadow(
                text_x, text_y, self.text, color, text_size,
                style.text_shadow_color, style.text_shadow_alpha,
                style.text_shadow_offset
            )
        else:
            BLFDrawing.draw_text(text_x, text_y, self.text, color, text_size)


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

        # ラベル
        BLFDrawing.draw_text(self.x, text_y, f"{label}: ", label_color, text_size)

        # 値
        label_w, _ = BLFDrawing.get_text_dimensions(f"{label}: ", text_size)
        BLFDrawing.draw_text(self.x + label_w, text_y, value, value_color, text_size)


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Items - インタラクティブ
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ButtonItem(LayoutItem):
    """クリック可能なボタン"""
    text: str = ""
    icon: str = "NONE"
    on_click: Optional[Callable[[], None]] = None

    # 状態
    _hovered: bool = field(default=False, repr=False)
    _pressed: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_w = IconDrawing.ICON_SIZE + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = style.scaled_padding()
        return (text_w + icon_w + padding * 2, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 背景色
        if self._pressed:
            bg_color = style.button_press_color
        elif self._hovered:
            bg_color = style.button_hover_color
        else:
            bg_color = style.button_color

        if not self.enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.border_radius, bg_color
        )

        # テキスト
        text_color = style.button_text_color if self.enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, text_size)

        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        BLFDrawing.draw_text(text_x, text_y, self.text, text_color, text_size)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        if not self.enabled:
            return False

        inside = self.is_inside(mouse_x, mouse_y)

        if event.type == 'MOUSEMOVE':
            self._hovered = inside
            return inside

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and inside:
                self._pressed = True
                return True
            elif event.value == 'RELEASE':
                if self._pressed and inside and self.on_click:
                    self.on_click()
                self._pressed = False
                return inside

        return False


@dataclass
class ToggleItem(LayoutItem):
    """トグルボタン（ON/OFF）"""
    text: str = ""
    icon: str = "NONE"
    icon_on: str = "NONE"
    icon_off: str = "NONE"
    value: bool = False
    on_toggle: Optional[Callable[[bool], None]] = None

    _hovered: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_w = IconDrawing.ICON_SIZE + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = style.scaled_padding()
        return (text_w + icon_w + padding * 2, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 背景色（ON 状態で強調）
        if self.value:
            bg_color = style.highlight_color if not self._hovered else tuple(
                min(1.0, c * 1.2) for c in style.highlight_color[:3]
            ) + (style.highlight_color[3],)
        else:
            bg_color = style.button_hover_color if self._hovered else style.button_color

        if not self.enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.border_radius, bg_color
        )

        # テキスト
        text_color = style.button_text_color if self.enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, text_size)

        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        BLFDrawing.draw_text(text_x, text_y, self.text, text_color, text_size)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        if not self.enabled:
            return False

        inside = self.is_inside(mouse_x, mouse_y)

        if event.type == 'MOUSEMOVE':
            self._hovered = inside
            return inside

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and inside:
            self.value = not self.value
            if self.on_toggle:
                self.on_toggle(self.value)
            return True

        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Container Items - コンテナ
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BoxItem(LayoutItem):
    """ボックス（枠線付きコンテナ）"""
    items: list[LayoutItem] = field(default_factory=list)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        if not self.items:
            return (self.width, style.scaled_padding() * 2)

        total_height = style.scaled_padding() * 2
        for item in self.items:
            _, h = item.calc_size(style)
            total_height += h + style.scaled_spacing()

        return (self.width, total_height)

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.border_radius, style.bg_color
        )

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            style.border_radius, style.outline_color
        )

        # 子アイテム
        for item in self.items:
            item.draw(style)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        for item in self.items:
            if item.handle_event(event, mouse_x, mouse_y):
                return True
        return False
