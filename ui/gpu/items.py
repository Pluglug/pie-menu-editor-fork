# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Layout Items

各種 UI 要素（ラベル、ボタン、セパレーター等）の定義。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

from .style import GPULayoutStyle, Alignment, WidgetType
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

    def _get_display_icon(self) -> str:
        """現在の value に応じた表示アイコンを取得"""
        if self.value and self.icon_on != "NONE":
            return self.icon_on
        elif not self.value and self.icon_off != "NONE":
            return self.icon_off
        return self.icon

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

        # 角丸半径を計算（roundness を適用）
        base_radius = style.scaled_border_radius()
        radius = int(base_radius * wcol.roundness) if wcol.roundness < 1.0 else base_radius

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
            radius, bg_color
        )

        # === 2. 値バー描画（item カラー） ===
        normalized = self._get_normalized_value()
        if normalized > 0.001:  # 0% に近い場合はスキップ
            bar_width = self.width * normalized
            # 値バーも同じ角丸だが、右端は値に応じて調整
            # 左端のみ角丸、右端は直角（値バーが背景より短い場合）
            if normalized >= 0.99:
                # 100% に近い場合は完全な角丸
                bar_radius = radius
            else:
                # それ以外は左端のみ角丸
                bar_radius = radius

            item_color = wcol.item if enabled else tuple(c * 0.5 for c in wcol.item[:3]) + (wcol.item[3],)
            GPUDrawing.draw_rounded_rect(
                self.x, self.y, bar_width, self.height,
                bar_radius, item_color
            )

        # === 3. アウトライン描画 ===
        # ドラッグ中は outline_sel を使用
        base_outline = wcol.outline_sel if dragging else wcol.outline
        outline_color = base_outline if enabled else tuple(c * 0.5 for c in base_outline[:3]) + (base_outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width()
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

        radius = style.scaled_border_radius()

        # 背景
        bg_color = style.button_press_color if dragging else (
            style.button_hover_color if hovered else style.button_color
        )
        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(self.x, self.y, self.width, self.height, radius, bg_color)

        # 値バー
        normalized = self._get_normalized_value()
        if normalized > 0.001:
            bar_width = self.width * normalized
            bar_color = style.highlight_color if enabled else tuple(c * 0.5 for c in style.highlight_color[:3]) + (style.highlight_color[3],)
            GPUDrawing.draw_rounded_rect(self.x, self.y, bar_width, self.height, radius, bar_color)

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, style.outline_color,
            line_width=style.line_width()
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
