# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Button/Toggle/Radio Items
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from ..style import GPULayoutStyle, WidgetType, ThemeWidgetColors
from ..drawing import GPUDrawing, BLFDrawing, IconDrawing
from .base import LayoutItem

if TYPE_CHECKING:
    from ..interactive import ItemRenderState


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

    def can_align(self) -> bool:
        return False

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """チェックボックスのサイズを計算"""
        text_size = style.scaled_text_size()
        text_w, _ = BLFDrawing.get_text_dimensions(self.text, text_size)
        box_size = self._get_box_size(style)
        spacing = style.scaled_spacing()
        padding = style.scaled_padding()
        # ボックス + スペース + テキスト + 左右パディング
        return (box_size + spacing + text_w + padding * 2, style.scaled_item_height())

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

        padding = style.scaled_padding()

        # ボックスの位置（垂直中央揃え、左右パディング）
        box_x = self.x + padding
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
        available_width = self.width - box_size - spacing - padding * 2
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
