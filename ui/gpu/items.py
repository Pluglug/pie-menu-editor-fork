# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Layout Items

各種 UI 要素（ラベル、ボタン、セパレーター等）の定義。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

from .style import GPULayoutStyle, Alignment, WidgetType, ThemeWidgetColors, SizingPolicy
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

    # Phase 2: 角丸制御（align=True 時に使用）
    # (bottomLeft, topLeft, topRight, bottomRight)
    # True = 角丸あり、False = 直角
    corners: tuple[bool, bool, bool, bool] = (True, True, True, True)

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
    # ラベルは EXPAND 時に自然幅を維持
    expand_width: bool = False

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
            style.separator_color, 1.0  # セパレーターは固定太さ
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

        # テーマカラーを取得（角丸計算用）
        wcol = style.get_widget_colors(WidgetType.TOOL)

        # 背景色
        if pressed:
            bg_color = style.button_press_color
        elif hovered:
            bg_color = style.button_hover_color
        else:
            bg_color = style.button_color

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        # Blender は roundness を短辺の半分に対する比率として使用
        if wcol is not None:
            radius = int(wcol.roundness * self.height * 0.5)
        else:
            radius = style.scaled_border_radius()

        # 背景（align=True 時は corners で角丸を制御）
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # アイコンとテキストのサイズ計算
        text_color = style.button_text_color if enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        padding = style.scaled_padding()

        icon_size = style.scaled_icon_size() if self.icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if self.icon != "NONE" else 0

        # ボタン内で利用可能なテキスト幅（アイコンとパディングを考慮）
        available_width = self.width - padding * 2 - icon_size - icon_spacing
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        # コンテンツ全体の幅（アイコン + スペース + テキスト）
        content_w = icon_size + icon_spacing + text_w

        # 中央揃えでコンテンツを配置
        content_x = self.x + (self.width - content_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        # アイコン描画
        text_x = content_x
        if self.icon != "NONE":
            icon_y = self.y - (self.height - icon_size) / 2
            alpha = 1.0 if enabled else 0.5
            IconDrawing.draw_icon(content_x, icon_y, self.icon, alpha=alpha)
            text_x += icon_size + icon_spacing

        # クリップ矩形（ボタン全体、角丸背景がテキストを制約）
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class ToggleItem(LayoutItem):
    """
    トグルボタン（wcol_toggle テーマ対応）

    Boolean プロパティをボタン形状で表示。ON/OFF でアイコン切り替え可能。

    Attributes:
        text: ボタンラベル
        icon: デフォルトアイコン
        icon_on: ON 状態のアイコン（指定時のみ）
        icon_off: OFF 状態のアイコン（指定時のみ）
        value: 現在値
        on_toggle: 値変更時のコールバック
    """
    text: str = ""
    icon: str = "NONE"
    icon_on: str = "NONE"
    icon_off: str = "NONE"
    value: bool = False
    on_toggle: Optional[Callable[[bool], None]] = None

    # 状態（layout 側から設定される）
    _hovered: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_size = style.scaled_icon_size()
        icon_w = icon_size + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = style.scaled_padding()
        return (text_w + icon_w + padding * 2, style.scaled_item_height())

    def _get_display_icon(self) -> str:
        """現在の value に応じた表示アイコンを取得"""
        if self.value and self.icon_on != "NONE":
            return self.icon_on
        elif not self.value and self.icon_off != "NONE":
            return self.icon_off
        return self.icon

    def toggle(self) -> None:
        """値をトグル"""
        self.value = not self.value
        if self.on_toggle:
            self.on_toggle(self.value)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """トグルボタンを描画（wcol_toggle テーマ使用）"""
        if not self.visible:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.TOGGLE)
        if wcol is None:
            # フォールバック: 従来の描画
            self._draw_fallback(style, state)
            return

        # 状態の判定
        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        radius = int(wcol.roundness * self.height * 0.5)

        # === 1. 背景描画 ===
        if self.value:
            # ON 状態: inner_sel
            bg_color = wcol.inner_sel
            if hovered:
                bg_color = tuple(min(1.0, c * 1.15) for c in bg_color[:3]) + (bg_color[3],)
        else:
            # OFF 状態: inner
            bg_color = wcol.inner
            if hovered:
                bg_color = tuple(min(1.0, c * 1.15) for c in bg_color[:3]) + (bg_color[3],)

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # === 2. アウトライン描画 ===
        outline_color = wcol.outline if enabled else tuple(c * 0.5 for c in wcol.outline[:3]) + (wcol.outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # === 3. アイコンとテキスト描画 ===
        text_color = wcol.text_sel if self.value else wcol.text
        if not enabled:
            text_color = tuple(c * 0.5 for c in text_color[:3]) + (text_color[3],)

        text_size = style.scaled_text_size()
        padding = style.scaled_padding()

        display_icon = self._get_display_icon()
        icon_size = style.scaled_icon_size() if display_icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if display_icon != "NONE" else 0

        # ボタン内で利用可能なテキスト幅
        available_width = self.width - padding * 2 - icon_size - icon_spacing
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        # コンテンツ全体の幅（アイコン + スペース + テキスト）
        content_w = icon_size + icon_spacing + text_w

        # 中央揃えでコンテンツを配置
        content_x = self.x + (self.width - content_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        # アイコン描画
        text_x = content_x
        if display_icon != "NONE":
            icon_y = self.y - (self.height - icon_size) / 2
            alpha = 1.0 if enabled else 0.5
            IconDrawing.draw_icon(content_x, icon_y, display_icon, alpha=alpha)
            text_x += icon_size + icon_spacing

        # テキスト描画
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        # 角丸半径（デフォルト roundness 0.4、Blender 準拠: roundness × height × 0.5）
        radius = int(0.4 * self.height * 0.5)

        # 背景色（ON 状態で強調）
        if self.value:
            bg_color = style.highlight_color if not hovered else tuple(
                min(1.0, c * 1.2) for c in style.highlight_color[:3]
            ) + (style.highlight_color[3],)
        else:
            bg_color = style.button_hover_color if hovered else style.button_color

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景（align=True 時は corners で角丸を制御）
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # アイコンとテキストのサイズ計算
        text_color = style.button_text_color if enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        padding = style.scaled_padding()

        display_icon = self._get_display_icon()
        icon_size = style.scaled_icon_size() if display_icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if display_icon != "NONE" else 0

        # ボタン内で利用可能なテキスト幅（アイコンとパディングを考慮）
        available_width = self.width - padding * 2 - icon_size - icon_spacing
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        # コンテンツ全体の幅（アイコン + スペース + テキスト）
        content_w = icon_size + icon_spacing + text_w

        # 中央揃えでコンテンツを配置
        content_x = self.x + (self.width - content_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        # アイコン描画
        text_x = content_x
        if display_icon != "NONE":
            icon_y = self.y - (self.height - icon_size) / 2
            alpha = 1.0 if enabled else 0.5
            IconDrawing.draw_icon(content_x, icon_y, display_icon, alpha=alpha)
            text_x += icon_size + icon_spacing

        # クリップ矩形（ボタン全体、角丸背景がテキストを制約）
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class CheckboxItem(LayoutItem):
    """
    チェックボックス（wcol_option テーマ対応）

    Boolean プロパティを四角形 + チェックマーク + ラベルで表示。

    Attributes:
        text: ラベルテキスト
        value: 現在値
        on_toggle: 値変更時のコールバック
    """
    text: str = ""
    value: bool = False
    on_toggle: Optional[Callable[[bool], None]] = None

    # 状態（layout 側から設定される）
    _hovered: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """チェックボックスのサイズを計算"""
        text_size = style.scaled_text_size()
        text_w, _ = BLFDrawing.get_text_dimensions(self.text, text_size)
        box_size = self._get_box_size(style)
        spacing = style.scaled_spacing()
        # ボックス + スペース + テキスト
        return (box_size + spacing + text_w, style.scaled_item_height())

    def _get_box_size(self, style: GPULayoutStyle) -> float:
        """チェックボックスの四角形サイズを取得"""
        # Blender 標準に近いサイズ
        return style.ui_scale(10)

    def toggle(self) -> None:
        """値をトグル"""
        self.value = not self.value
        if self.on_toggle:
            self.on_toggle(self.value)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """チェックボックスを描画（wcol_option テーマ使用）"""
        if not self.visible:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.OPTION)
        if wcol is None:
            # フォールバック
            self._draw_fallback(style, state)
            return

        # 状態の判定
        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        box_size = self._get_box_size(style)
        spacing = style.scaled_spacing()
        text_size = style.scaled_text_size()

        # ボックスの位置（垂直中央揃え）
        box_x = self.x
        box_y = self.y - (self.height - box_size) / 2

        # 角丸半径（ボックスサイズに対して roundness を適用）
        radius = int(box_size * 0.2 * wcol.roundness)

        # === 1. ボックス背景 ===
        if self.value:
            bg_color = wcol.inner_sel
        else:
            bg_color = wcol.inner

        if hovered:
            bg_color = tuple(min(1.0, c * 1.15) for c in bg_color[:3]) + (bg_color[3],)

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            box_x, box_y, box_size, box_size,
            radius, bg_color
        )

        # === 2. ボックスアウトライン ===
        outline_color = wcol.outline if enabled else tuple(c * 0.5 for c in wcol.outline[:3]) + (wcol.outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            box_x, box_y, box_size, box_size,
            radius, outline_color,
            line_width=style.line_width()
        )

        # === 3. チェックマーク描画（ON 状態のみ） ===
        if self.value:
            check_color = wcol.item if enabled else tuple(c * 0.5 for c in wcol.item[:3]) + (wcol.item[3],)
            self._draw_checkmark(box_x, box_y, box_size, check_color, style)

        # === 4. ラベル描画 ===
        text_color = wcol.text if enabled else tuple(c * 0.5 for c in wcol.text[:3]) + (wcol.text[3],)
        text_x = box_x + box_size + spacing
        _, text_h = BLFDrawing.get_text_dimensions("Wg", text_size)
        text_y = self.y - (self.height + text_h) / 2

        # 利用可能幅でテキストを省略
        available_width = self.width - box_size - spacing
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, available_width, text_size)

        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

    def _draw_checkmark(self, box_x: float, box_y: float, box_size: float,
                        color: tuple[float, float, float, float], style: GPULayoutStyle) -> None:
        """チェックマークを描画（レ字型）"""
        # 線の太さ
        line_width = 1.0

        # チェックマークのパディング
        padding = box_size * 0.2

        # チェックマークの座標（レ字型）
        # 左下 → 中央下 → 右上
        x1 = box_x + padding
        y1 = box_y - box_size * 0.5
        x2 = box_x + box_size * 0.4
        y2 = box_y - box_size + padding
        x3 = box_x + box_size - padding
        y3 = box_y - padding

        # 2本の線でチェックマークを描画
        GPUDrawing.draw_line(x1, y1, x2, y2, color, line_width)
        GPUDrawing.draw_line(x2, y2, x3, y3, color, line_width)

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        box_size = self._get_box_size(style)
        spacing = style.scaled_spacing()
        text_size = style.scaled_text_size()

        box_x = self.x
        box_y = self.y - (self.height - box_size) / 2

        radius = int(box_size * 0.2)

        # ボックス背景
        if self.value:
            bg_color = style.highlight_color
        else:
            bg_color = style.button_color

        if hovered:
            bg_color = tuple(min(1.0, c * 1.15) for c in bg_color[:3]) + (bg_color[3],)
        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(box_x, box_y, box_size, box_size, radius, bg_color)

        # ボックスアウトライン
        GPUDrawing.draw_rounded_rect_outline(
            box_x, box_y, box_size, box_size,
            radius, style.outline_color,
            line_width=style.line_width()
        )

        # チェックマーク
        if self.value:
            self._draw_checkmark(box_x, box_y, box_size, style.text_color, style)

        # ラベル
        text_color = style.text_color if enabled else style.text_color_disabled
        text_x = box_x + box_size + spacing
        _, text_h = BLFDrawing.get_text_dimensions("Wg", text_size)
        text_y = self.y - (self.height + text_h) / 2

        available_width = self.width - box_size - spacing
        display_text = BLFDrawing.get_text_with_ellipsis(self.text, available_width, text_size)

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


# ═══════════════════════════════════════════════════════════════════════════════
# Widget Items - ウィジェット（テーマカラー対応）
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SliderItem(LayoutItem):
    """
    スライダー（wcol_numslider テーマ対応）

    数値の範囲選択に使用。ドラッグで値を変更。

    Attributes:
        value: 現在値
        min_val: 最小値
        max_val: 最大値
        precision: 表示精度（小数点以下の桁数）
        text: ラベルテキスト（空の場合は値のみ表示）
        on_change: 値変更時のコールバック
    """
    value: float = 0.0
    min_val: float = 0.0
    max_val: float = 1.0
    precision: int = 2
    text: str = ""
    on_change: Optional[Callable[[float], None]] = None

    # 状態（layout 側から設定される）
    _hovered: bool = field(default=False, repr=False)
    _dragging: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """スライダーのサイズを計算"""
        text_size = style.scaled_text_size()
        display_text = self._get_display_text()
        text_w, _ = BLFDrawing.get_text_dimensions(display_text, text_size)
        padding = style.scaled_padding()
        # 最小幅を確保（テキスト + パディング、または 100px）
        min_width = max(text_w + padding * 4, style.ui_scale(100))
        return (max(self.width, min_width), style.scaled_item_height())

    def _get_display_text(self) -> str:
        """表示用テキストを生成"""
        value_str = f"{self.value:.{self.precision}f}"
        if self.text:
            return f"{self.text}: {value_str}"
        return value_str

    def _get_normalized_value(self) -> float:
        """値を 0.0〜1.0 の範囲に正規化（クランプ付き）"""
        if self.max_val == self.min_val:
            return 0.0
        normalized = (self.value - self.min_val) / (self.max_val - self.min_val)
        return max(0.0, min(1.0, normalized))  # 範囲外の値をクランプ

    def set_value_from_position(self, x: float) -> None:
        """X 座標から値を設定（ドラッグ時に使用）"""
        # 幅が 0 以下の場合は安全にスキップ
        if self.width <= 0:
            return
        # 相対位置を計算
        rel_x = (x - self.x) / self.width
        rel_x = max(0.0, min(1.0, rel_x))
        # 値に変換
        new_value = self.min_val + rel_x * (self.max_val - self.min_val)
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """スライダーを描画（wcol_numslider テーマ使用）"""
        if not self.visible:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.SLIDER)
        if wcol is None:
            # フォールバック: 通常のボタンスタイルで描画
            self._draw_fallback(style, state)
            return

        # 状態の判定
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        radius = int(wcol.roundness * self.height * 0.5)

        # === 1. 背景描画 ===
        if dragging:
            bg_color = wcol.inner_sel
        elif hovered:
            # ホバー時は inner を少し明るく
            bg_color = tuple(min(1.0, c * 1.15) for c in wcol.inner[:3]) + (wcol.inner[3],)
        else:
            bg_color = wcol.inner

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # === 2. 値バー描画（item カラー） ===
        normalized = self._get_normalized_value()
        if normalized > 0.001:  # 0% に近い場合はスキップ
            bar_width = self.width * normalized

            # 値バー用 corners を計算
            # 左側は self.corners を継承、右側は 100% 未満なら直角
            if normalized >= 0.99:
                bar_corners = self.corners  # フルなので親と同じ
            else:
                # 右側を直角に（値バーが背景より短い）
                # corners: (bottomLeft, topLeft, topRight, bottomRight)
                bar_corners = (self.corners[0], self.corners[1], False, False)

            item_color = wcol.item if enabled else tuple(c * 0.5 for c in wcol.item[:3]) + (wcol.item[3],)
            GPUDrawing.draw_rounded_rect(
                self.x, self.y, bar_width, self.height,
                radius, item_color, bar_corners
            )

        # === 3. アウトライン描画 ===
        # ドラッグ中は outline_sel を使用
        base_outline = wcol.outline_sel if dragging else wcol.outline
        outline_color = base_outline if enabled else tuple(c * 0.5 for c in base_outline[:3]) + (base_outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # === 4. テキスト描画 ===
        text_color = wcol.text_sel if dragging else wcol.text
        if not enabled:
            text_color = tuple(c * 0.5 for c in text_color[:3]) + (text_color[3],)

        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        # 中央揃え
        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径（デフォルト roundness 0.4、Blender 準拠: roundness × height × 0.5）
        radius = int(0.4 * self.height * 0.5)

        # 背景
        bg_color = style.button_press_color if dragging else (
            style.button_hover_color if hovered else style.button_color
        )
        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(self.x, self.y, self.width, self.height, radius, bg_color, self.corners)

        # 値バー
        normalized = self._get_normalized_value()
        if normalized > 0.001:
            bar_width = self.width * normalized
            bar_color = style.highlight_color if enabled else tuple(c * 0.5 for c in style.highlight_color[:3]) + (style.highlight_color[3],)

            # 値バー用 corners（左側は継承、右側は 100% 未満なら直角）
            if normalized >= 0.99:
                bar_corners = self.corners
            else:
                bar_corners = (self.corners[0], self.corners[1], False, False)

            GPUDrawing.draw_rounded_rect(self.x, self.y, bar_width, self.height, radius, bar_color, bar_corners)

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, style.outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # テキスト
        text_color = style.button_text_color if enabled else style.text_color_disabled
        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class NumberItem(LayoutItem):
    """
    数値フィールド（wcol_num テーマ対応）

    数値の表示・編集に使用。ドラッグまたは増減ボタンで値を変更。

    Attributes:
        value: 現在値
        min_val: 最小値
        max_val: 最大値
        step: ドラッグ時の変化量（ピクセルあたり）
        precision: 表示精度（小数点以下の桁数）
        text: ラベルテキスト（空の場合は値のみ表示）
        show_buttons: 増減ボタン（◀ ▶）を表示するか
        on_change: 値変更時のコールバック
    """
    value: float = 0.0
    min_val: float = -float('inf')
    max_val: float = float('inf')
    step: float = 0.01
    precision: int = 2
    text: str = ""
    show_buttons: bool = False
    on_change: Optional[Callable[[float], None]] = None

    # 状態（layout 側から設定される）
    _hovered: bool = field(default=False, repr=False)
    _dragging: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """数値フィールドのサイズを計算"""
        text_size = style.scaled_text_size()
        display_text = self._get_display_text()
        text_w, _ = BLFDrawing.get_text_dimensions(display_text, text_size)
        padding = style.scaled_padding()
        button_width = self._get_button_width(style) if self.show_buttons else 0
        # 最小幅を確保（テキスト + パディング + ボタン、または 80px）
        min_width = max(text_w + padding * 4 + button_width * 2, style.ui_scale(80))
        return (max(self.width, min_width), style.scaled_item_height())

    def _get_display_text(self) -> str:
        """表示用テキストを生成"""
        value_str = f"{self.value:.{self.precision}f}"
        if self.text:
            return f"{self.text}: {value_str}"
        return value_str

    def _get_button_width(self, style: GPULayoutStyle) -> float:
        """増減ボタンの幅を取得"""
        return style.ui_scale(16)

    def set_value_from_delta(self, dx: float) -> None:
        """ドラッグ移動量から値を設定"""
        new_value = self.value + dx * self.step
        # 範囲内にクランプ
        new_value = max(self.min_val, min(self.max_val, new_value))
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def increment(self) -> None:
        """値を1ステップ増加"""
        # step の 10 倍を増分として使用（ボタン用）
        new_value = self.value + self.step * 10
        new_value = min(self.max_val, new_value)
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def decrement(self) -> None:
        """値を1ステップ減少"""
        new_value = self.value - self.step * 10
        new_value = max(self.min_val, new_value)
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """数値フィールドを描画（wcol_num テーマ使用）"""
        if not self.visible:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.NUMBER)
        if wcol is None:
            # フォールバック: 通常のボタンスタイルで描画
            self._draw_fallback(style, state)
            return

        # 状態の判定
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        radius = int(wcol.roundness * self.height * 0.5)

        # === 1. 背景描画 ===
        if dragging:
            bg_color = wcol.inner_sel
        elif hovered:
            # ホバー時は inner を少し明るく
            bg_color = tuple(min(1.0, c * 1.15) for c in wcol.inner[:3]) + (wcol.inner[3],)
        else:
            bg_color = wcol.inner

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # === 2. アウトライン描画 ===
        base_outline = wcol.outline_sel if dragging else wcol.outline
        outline_color = base_outline if enabled else tuple(c * 0.5 for c in base_outline[:3]) + (base_outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # === 3. 増減ボタン描画（オプション） ===
        button_width = 0
        if self.show_buttons:
            button_width = self._get_button_width(style)
            self._draw_buttons(style, wcol, enabled, button_width)

        # === 4. テキスト描画 ===
        text_color = wcol.text_sel if dragging else wcol.text
        if not enabled:
            text_color = tuple(c * 0.5 for c in text_color[:3]) + (text_color[3],)

        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        # 中央揃え（ボタンを考慮）
        text_area_x = self.x + button_width
        text_area_width = self.width - button_width * 2
        text_x = text_area_x + (text_area_width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        # クリップ矩形（ボタン領域を除く）
        clip_rect = BLFDrawing.calc_clip_rect(
            text_area_x, self.y, text_area_width, self.height, 0
        )
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

    def _draw_buttons(self, style: GPULayoutStyle, wcol: ThemeWidgetColors,
                      enabled: bool, button_width: float) -> None:
        """増減ボタンを描画"""
        # ボタンの高さはアイテムの高さと同じ
        button_height = self.height

        # 左ボタン（◀ 減少）
        left_x = self.x
        left_center_x = left_x + button_width / 2
        center_y = self.y - self.height / 2

        # 右ボタン（▶ 増加）
        right_x = self.x + self.width - button_width
        right_center_x = right_x + button_width / 2

        # 三角形のサイズ
        tri_size = style.ui_scale(5)
        tri_color = wcol.text if enabled else tuple(c * 0.5 for c in wcol.text[:3]) + (wcol.text[3],)

        # 左三角形（◀）
        GPUDrawing.draw_triangle(
            left_center_x + tri_size / 2, center_y - tri_size,
            left_center_x + tri_size / 2, center_y + tri_size,
            left_center_x - tri_size / 2, center_y,
            tri_color
        )

        # 右三角形（▶）
        GPUDrawing.draw_triangle(
            right_center_x - tri_size / 2, center_y - tri_size,
            right_center_x - tri_size / 2, center_y + tri_size,
            right_center_x + tri_size / 2, center_y,
            tri_color
        )

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径（デフォルト roundness 0.4、Blender 準拠: roundness × height × 0.5）
        radius = int(0.4 * self.height * 0.5)

        # 背景
        bg_color = style.button_press_color if dragging else (
            style.button_hover_color if hovered else style.button_color
        )
        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(self.x, self.y, self.width, self.height, radius, bg_color, self.corners)

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, style.outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # テキスト
        text_color = style.button_text_color if enabled else style.text_color_disabled
        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class RadioOption:
    """RadioGroupItem の個々の選択肢"""
    value: str  # 内部値（識別子）
    label: str = ""  # 表示ラベル（空の場合は value を使用）
    icon: str = "NONE"  # アイコン名

    @property
    def display_label(self) -> str:
        """表示用ラベルを取得"""
        return self.label if self.label else self.value


@dataclass
class RadioGroupItem(LayoutItem):
    """
    ラジオボタングループ（wcol_radio テーマ対応）

    Enum プロパティを横並びのボタングループで表示。1つのみ選択可能。
    Blender の `expand=True` 時の Enum 表示に相当。

    Attributes:
        options: 選択肢のリスト (RadioOption または (value, label, icon) タプル)
        value: 現在選択されている値
        on_change: 値変更時のコールバック

    Note:
        - 左端ボタンは左側のみ角丸、右端ボタンは右側のみ角丸
        - 中間ボタンは角丸なし（連結されたボタン群の見た目）
        - 選択されたボタンは inner_sel で強調
    """
    options: list[RadioOption] = field(default_factory=list)
    value: str = ""
    on_change: Optional[Callable[[str], None]] = None

    # 状態（layout 側から設定される）
    _hovered_index: int = field(default=-1, repr=False)

    def __post_init__(self):
        """options を RadioOption に正規化"""
        normalized = []
        for opt in self.options:
            if isinstance(opt, RadioOption):
                normalized.append(opt)
            elif isinstance(opt, (list, tuple)):
                # (value,) or (value, label) or (value, label, icon)
                value = opt[0] if len(opt) > 0 else ""
                label = opt[1] if len(opt) > 1 else ""
                icon = opt[2] if len(opt) > 2 else "NONE"
                normalized.append(RadioOption(value=value, label=label, icon=icon))
            else:
                # 文字列として扱う
                normalized.append(RadioOption(value=str(opt)))
        self.options = normalized

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """グループ全体のサイズを計算"""
        if not self.options:
            return (0, style.scaled_item_height())

        text_size = style.scaled_text_size()
        padding = style.scaled_padding()
        icon_size = style.scaled_icon_size()
        spacing = style.scaled_spacing()

        total_width = 0
        for opt in self.options:
            # 各オプションの幅を計算
            text_w, _ = BLFDrawing.get_text_dimensions(opt.display_label, text_size)
            icon_w = icon_size + spacing if opt.icon != "NONE" else 0
            button_width = text_w + icon_w + padding * 2
            total_width += button_width

        return (total_width, style.scaled_item_height())

    def get_button_rects(self, style: GPULayoutStyle) -> list[tuple[float, float, float, float]]:
        """各ボタンの矩形を取得（x, y, width, height）"""
        if not self.options:
            return []

        text_size = style.scaled_text_size()
        padding = style.scaled_padding()
        icon_size = style.scaled_icon_size()
        spacing = style.scaled_spacing()

        # 各ボタンの自然幅を計算
        button_widths = []
        for opt in self.options:
            text_w, _ = BLFDrawing.get_text_dimensions(opt.display_label, text_size)
            icon_w = icon_size + spacing if opt.icon != "NONE" else 0
            button_widths.append(text_w + icon_w + padding * 2)

        # 幅が設定されている場合は均等分割
        total_natural_width = sum(button_widths)
        if self.width > total_natural_width:
            # 均等に拡張
            button_widths = [self.width / len(self.options)] * len(self.options)
        elif self.width > 0 and self.width < total_natural_width:
            # 比率を維持して縮小
            scale = self.width / total_natural_width
            button_widths = [w * scale for w in button_widths]

        # 矩形リストを作成
        rects = []
        current_x = self.x
        for width in button_widths:
            rects.append((current_x, self.y, width, self.height))
            current_x += width

        return rects

    def get_button_at(self, x: float, y: float, style: GPULayoutStyle) -> int:
        """指定座標にあるボタンのインデックスを返す（-1: なし）"""
        if not self.is_inside(x, y):
            return -1

        rects = self.get_button_rects(style)
        for i, (bx, by, bw, bh) in enumerate(rects):
            if bx <= x <= bx + bw and by - bh <= y <= by:
                return i
        return -1

    def select(self, value: str) -> None:
        """指定値を選択"""
        if value != self.value:
            self.value = value
            if self.on_change:
                self.on_change(value)

    def select_by_index(self, index: int) -> None:
        """インデックスで選択"""
        if 0 <= index < len(self.options):
            self.select(self.options[index].value)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """ラジオボタングループを描画（wcol_radio テーマ使用）"""
        if not self.visible or not self.options:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.RADIO)
        if wcol is None:
            self._draw_fallback(style, state)
            return

        # 状態の判定
        enabled = state.enabled if state else self.enabled
        hovered_index = self._hovered_index

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        radius = int(wcol.roundness * self.height * 0.5)

        # 各ボタンの矩形を取得
        rects = self.get_button_rects(style)

        # 各ボタンを描画
        for i, (bx, by, bw, bh) in enumerate(rects):
            opt = self.options[i]
            is_selected = (opt.value == self.value)
            is_hovered = (i == hovered_index)

            # 角丸の設定（左端/右端のみ角丸）
            is_first = (i == 0)
            is_last = (i == len(self.options) - 1)
            corners = (is_first, is_first, is_last, is_last)  # (top_left, bottom_left, top_right, bottom_right)

            self._draw_button(
                bx, by, bw, bh,
                opt, is_selected, is_hovered, enabled,
                radius, corners, style, wcol
            )

    def _draw_button(self, x: float, y: float, width: float, height: float,
                     opt: RadioOption, is_selected: bool, is_hovered: bool, enabled: bool,
                     radius: int, corners: tuple[bool, bool, bool, bool],
                     style: GPULayoutStyle, wcol: ThemeWidgetColors) -> None:
        """個々のボタンを描画"""
        # === 1. 背景描画 ===
        if is_selected:
            bg_color = wcol.inner_sel
            if is_hovered:
                bg_color = tuple(min(1.0, c * 1.15) for c in bg_color[:3]) + (bg_color[3],)
        else:
            bg_color = wcol.inner
            if is_hovered:
                bg_color = tuple(min(1.0, c * 1.15) for c in bg_color[:3]) + (bg_color[3],)

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            x, y, width, height,
            radius, bg_color, corners
        )

        # === 2. アウトライン描画 ===
        outline_color = wcol.outline if enabled else tuple(c * 0.5 for c in wcol.outline[:3]) + (wcol.outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            x, y, width, height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=corners
        )

        # === 3. アイコンとテキスト描画 ===
        text_color = wcol.text_sel if is_selected else wcol.text
        if not enabled:
            text_color = tuple(c * 0.5 for c in text_color[:3]) + (text_color[3],)

        text_size = style.scaled_text_size()
        padding = style.scaled_padding()

        icon_size = style.scaled_icon_size() if opt.icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if opt.icon != "NONE" else 0

        # ボタン内で利用可能なテキスト幅
        available_width = width - padding * 2 - icon_size - icon_spacing
        display_text = BLFDrawing.get_text_with_ellipsis(opt.display_label, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        # コンテンツ全体の幅（アイコン + スペース + テキスト）
        content_w = icon_size + icon_spacing + text_w

        # 中央揃えでコンテンツを配置
        content_x = x + (width - content_w) / 2
        text_y = y - (height + text_h) / 2

        # アイコン描画
        text_x = content_x
        if opt.icon != "NONE":
            icon_y = y - (height - icon_size) / 2
            alpha = 1.0 if enabled else 0.5
            IconDrawing.draw_icon(content_x, icon_y, opt.icon, alpha=alpha)
            text_x += icon_size + icon_spacing

        # テキスト描画
        clip_rect = BLFDrawing.calc_clip_rect(x, y, width, height, 0)
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        enabled = state.enabled if state else self.enabled
        hovered_index = self._hovered_index

        # 角丸半径（デフォルト roundness 0.4、Blender 準拠: roundness × height × 0.5）
        radius = int(0.4 * self.height * 0.5)
        rects = self.get_button_rects(style)

        for i, (bx, by, bw, bh) in enumerate(rects):
            opt = self.options[i]
            is_selected = (opt.value == self.value)
            is_hovered = (i == hovered_index)

            is_first = (i == 0)
            is_last = (i == len(self.options) - 1)
            corners = (is_first, is_first, is_last, is_last)

            # 背景色
            if is_selected:
                bg_color = style.highlight_color
                if is_hovered:
                    bg_color = tuple(min(1.0, c * 1.2) for c in bg_color[:3]) + (bg_color[3],)
            else:
                bg_color = style.button_hover_color if is_hovered else style.button_color

            if not enabled:
                bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

            GPUDrawing.draw_rounded_rect(bx, by, bw, bh, radius, bg_color, corners)
            GPUDrawing.draw_rounded_rect_outline(
                bx, by, bw, bh,
                radius, style.outline_color,
                line_width=style.line_width(),
                corners=corners
            )

            # テキスト
            text_color = style.button_text_color if enabled else style.text_color_disabled
            text_size = style.scaled_text_size()
            padding = style.scaled_padding()

            icon_size = style.scaled_icon_size() if opt.icon != "NONE" else 0
            icon_spacing = style.scaled_spacing() if opt.icon != "NONE" else 0

            available_width = bw - padding * 2 - icon_size - icon_spacing
            display_text = BLFDrawing.get_text_with_ellipsis(opt.display_label, available_width, text_size)
            text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

            content_w = icon_size + icon_spacing + text_w
            content_x = bx + (bw - content_w) / 2
            text_y = by - (bh + text_h) / 2

            text_x = content_x
            if opt.icon != "NONE":
                icon_y = by - (bh - icon_size) / 2
                alpha = 1.0 if enabled else 0.5
                IconDrawing.draw_icon(content_x, icon_y, opt.icon, alpha=alpha)
                text_x += icon_size + icon_spacing

            clip_rect = BLFDrawing.calc_clip_rect(bx, by, bw, bh, 0)
            BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class ColorItem(LayoutItem):
    """
    カラースウォッチ（色の表示・選択ウィジェット）

    Blender スタイルの横長カラーバーを描画。
    左側に RGB（不透明）、右側にチェッカー+RGBA（アルファ表示）。

    現在の実装:
        - use_property_split=True スタイル: ラベルを固定比率領域（split_factor）に右揃え
        - カラーバーは残りの領域に配置（整列される）

    Attributes:
        color: 表示する色 (R, G, B, A) - 各値は 0.0-1.0
        text: ラベルテキスト（空の場合はカラーバーのみ）
        on_click: クリック時のコールバック

    TODO(将来の拡張):
        - use_property_split=False スタイル: ラベル+コロンを上の行、カラーバーを下の行（2行構成）
        - layout.prop() との統合時に HitRect をカラーバー部分のみに設定（get_bar_rect() 使用）
    """
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    text: str = ""
    on_click: Optional[Callable[[], None]] = None
    _hovered: bool = field(default=False, repr=False)

    # カラーバーの高さ比率（アイテム高さに対して）
    # 1.0 = フル高さ（他のウィジェットと統一）
    BAR_HEIGHT_RATIO: float = 1.0

    def _get_bar_height(self) -> float:
        """カラーバーの高さを取得

        Note:
            self.height は layout.py で scale_y を適用済みなので、
            ここでは self.height を使用して scale_y に追従する。
        """
        return self.height * self.BAR_HEIGHT_RATIO

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """サイズを計算

        Note:
            width は親レイアウトから設定される（row 全体に広がる）。
            ラベル領域は split_factor で固定比率（約40%）として確保される。
        """
        height = style.scaled_item_height()
        # width は親レイアウトから設定される（row 全体に広がる）
        # デフォルトは最小幅として適当な値を返す
        min_width = style.scaled_item_height() * 4  # 最小幅
        return (self.width if self.width > 0 else min_width, height)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """描画

        Blender スタイル: [  RGB (不透明)  |  RGBA (チェッカー)  ]
        """
        if not self.visible:
            return

        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        # テーマカラーを取得（角丸計算用）
        wcol = style.get_widget_colors(WidgetType.REGULAR)

        bar_height = self._get_bar_height()
        spacing = style.scaled_spacing()

        # use_property_split=True スタイル: ラベルを固定比率領域に右揃え
        if self.text:
            text_size = style.scaled_text_size()
            label_text = self.text + ":"

            # 固定比率でラベル領域を確保（split_factor: 約40%）
            label_region_width = self.width * style.split_factor

            # テキストがラベル領域に収まるか確認、収まらない場合は省略
            available_width = label_region_width - spacing * 2

            # ラベル領域が十分にある場合のみテキストを描画
            if available_width > 0:
                label_text = BLFDrawing.truncate_text(label_text, text_size, available_width)
                text_w, text_h = BLFDrawing.get_text_dimensions(label_text, text_size)

                # テキスト幅がラベル領域に収まる場合のみ描画
                if text_w <= available_width:
                    text_color = style.text_color if enabled else style.text_color_disabled
                    text_y = self.y - (self.height + text_h) / 2
                    text_x = self.x + label_region_width - text_w - spacing  # 右揃え
                    # 左端を超えないようにクリップ
                    text_x = max(text_x, self.x + spacing)
                    BLFDrawing.draw_text(text_x, text_y, label_text, text_color, text_size)

            bar_x = self.x + label_region_width
            bar_width = self.width - label_region_width
        else:
            bar_x = self.x
            bar_width = self.width

        # カラーバーの位置（垂直中央揃え）
        bar_y = self.y - (self.height - bar_height) / 2

        # 角丸半径（Blender 準拠: roundness × height × 0.5）
        if wcol is not None:
            radius = int(wcol.roundness * bar_height * 0.5)
        else:
            radius = int(0.4 * bar_height * 0.5)

        # バー幅が小さすぎる場合は描画しない
        if bar_width < bar_height:
            return

        # === Blender スタイル: 左=RGB、右=RGBA(チェッカー) ===
        # 左右の分割位置（50:50）
        rgb_width = bar_width / 2
        alpha_width = bar_width - rgb_width

        # 色の計算
        rgb_color = (self.color[0], self.color[1], self.color[2], 1.0)  # 不透明
        rgba_color = self.color  # アルファ込み

        if not enabled:
            # 無効時は彩度を下げる
            gray = 0.299 * self.color[0] + 0.587 * self.color[1] + 0.114 * self.color[2]
            rgb_color = (
                self.color[0] * 0.5 + gray * 0.5,
                self.color[1] * 0.5 + gray * 0.5,
                self.color[2] * 0.5 + gray * 0.5,
                1.0
            )
            rgba_color = (
                rgb_color[0], rgb_color[1], rgb_color[2],
                self.color[3] * 0.5
            )

        # === 1. 右側: チェッカーパターン背景 ===
        alpha_x = bar_x + rgb_width
        self._draw_checker_pattern_rect(
            alpha_x, bar_y, alpha_width, bar_height,
            radius, style,
            corners=(False, False, True, True)  # 右側のみ角丸
        )

        # === 2. 右側: RGBA カラー（チェッカーの上に半透明で描画） ===
        GPUDrawing.draw_rounded_rect(
            alpha_x, bar_y, alpha_width, bar_height,
            radius, rgba_color,
            corners=(False, False, True, True)
        )

        # === 3. 左側: RGB カラー（不透明） ===
        GPUDrawing.draw_rounded_rect(
            bar_x, bar_y, rgb_width, bar_height,
            radius, rgb_color,
            corners=(True, True, False, False)  # 左側のみ角丸
        )

        # === 4. アウトライン（全体） ===
        if hovered:
            outline_color = style.highlight_color
            line_width = style.line_width() * 1.5
        else:
            outline_color = style.outline_color
            line_width = style.line_width()

        if not enabled:
            outline_color = tuple(c * 0.5 for c in outline_color[:3]) + (outline_color[3],)

        GPUDrawing.draw_rounded_rect_outline(
            bar_x, bar_y, bar_width, bar_height,
            radius, outline_color,
            line_width=line_width
        )

    def _draw_checker_pattern_rect(self, x: float, y: float, width: float, height: float,
                                    radius: int, style: GPULayoutStyle,
                                    corners: tuple[bool, bool, bool, bool] = (True, True, True, True)) -> None:
        """チェッカーパターンを矩形領域に描画"""
        cell_size = max(4, style.ui_scale(4))  # 4px (scaled)
        light_color = (0.7, 0.7, 0.7, 1.0)
        dark_color = (0.4, 0.4, 0.4, 1.0)

        # まず背景色（明るい方）で角丸矩形を塗りつぶす
        GPUDrawing.draw_rounded_rect(x, y, width, height, radius, light_color, corners)

        # 暗いセルを描画（簡易版 - 角丸クリッピングなし）
        # TODO: 正確な角丸クリッピングは将来シェーダーで実装
        margin = radius * 0.3
        inner_x = x + margin
        inner_y = y - margin
        inner_width = width - margin * 2
        inner_height = height - margin * 2

        cols = int(inner_width / cell_size) + 1
        rows = int(inner_height / cell_size) + 1

        for row in range(rows):
            for col in range(cols):
                if (row + col) % 2 == 1:
                    cell_x = inner_x + col * cell_size
                    cell_y = inner_y - row * cell_size
                    # 範囲内にクリップ
                    cell_w = min(cell_size, inner_x + inner_width - cell_x)
                    cell_h = min(cell_size, cell_y - (inner_y - inner_height))
                    if cell_w > 0 and cell_h > 0:
                        GPUDrawing.draw_rect(cell_x, cell_y, cell_w, cell_h, dark_color)

    def click(self) -> None:
        """クリック処理

        TODO(layout.prop統合):
            - ヒットポイントはカラーバー部分のみ
            - ラベル部分はクリック対象外
            - layout.py の _register_interactive_item で HitRect を調整
        """
        if self.enabled and self.on_click:
            self.on_click()

    def get_bar_rect(self, style: GPULayoutStyle) -> tuple[float, float, float, float]:
        """カラーバー部分の矩形を取得（ヒットテスト用）

        Returns:
            (x, y, width, height) - カラーバーの位置とサイズ

        TODO(layout.prop統合):
            - _register_interactive_item でこのメソッドを使って HitRect を設定
        """
        bar_height = self._get_bar_height()

        # use_property_split=True スタイル: 固定比率でバー位置を計算
        if self.text:
            label_region_width = self.width * style.split_factor
            bar_x = self.x + label_region_width
            bar_width = self.width - label_region_width
        else:
            bar_x = self.x
            bar_width = self.width

        bar_y = self.y - (self.height - bar_height) / 2

        return (bar_x, bar_y, bar_width, bar_height)
