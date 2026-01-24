# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Menu Button Item (Enum Dropdown)
"""

from __future__ import annotations

import bpy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from ..style import GPULayoutStyle, WidgetType
from ..drawing import GPUDrawing, BLFDrawing, IconDrawing
from .base import LayoutItem

if TYPE_CHECKING:
    from ..interactive import ItemRenderState


@dataclass
class MenuButtonItem(LayoutItem):
    """
    Enum ドロップダウンメニューボタン（wcol_menu テーマ対応）

    Blender の `UILayout.prop()` で `expand=False`（デフォルト）時の
    Enum 表示に相当するウィジェット。

    クリックすると popup_menu が開き、選択肢を表示する。

    Attributes:
        text: ラベル（プロパティ名）
        icon: 左側に表示するアイコン
        value: 現在選択されている値（identifier）
        display_name: 現在値の表示名
        options: 選択肢のリスト [(identifier, name, description), ...]
        on_change: 値変更時のコールバック
        is_dynamic_enum: 動的 Enum かどうか（render.engine など）

    Note:
        - 右端にドロップダウン矢印（DOWNARROW_HLT）を表示
        - クリックで Blender の popup_menu を開く
        - 選択時に PME_OT_gpu_enum_select オペレーターを呼び出す
    """
    text: str = ""
    icon: str = "NONE"
    value: str = ""
    display_name: str = ""
    options: list[tuple[str, str, str]] = field(default_factory=list)
    on_change: Optional[Callable[[str], None]] = None
    is_dynamic_enum: bool = False

    # 状態（layout 側から設定される）
    _hovered: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """ボタンサイズを計算"""
        text_size = style.scaled_text_size()
        padding = style.scaled_padding()
        icon_size = style.scaled_icon_size()
        spacing = style.scaled_spacing()

        # アイコン幅（左側アイコン）
        left_icon_w = icon_size + spacing if self.icon != "NONE" else 0

        # ドロップダウン矢印幅（右側）
        arrow_w = icon_size + spacing

        # テキスト幅（display_name を表示）
        text_w, _ = BLFDrawing.get_text_dimensions(self.display_name, text_size)

        # 全体幅: padding + leftIcon + text + arrow + padding
        total_width = padding * 2 + left_icon_w + text_w + arrow_w

        return (total_width, style.scaled_item_height())

    def get_value(self) -> str:
        """ValueWidget Protocol 準拠"""
        return self.value

    def set_value(self, value: str) -> None:
        """ValueWidget Protocol 準拠"""
        old_value = self.value
        self.value = str(value) if value is not None else ""

        # display_name を更新
        for ident, name, _ in self.options:
            if ident == self.value:
                self.display_name = name
                break

        # コールバックを呼び出し
        if old_value != self.value and self.on_change:
            self.on_change(self.value)

    def open_menu(self) -> None:
        """
        ドロップダウンメニューを開く

        Blender の window_manager.popup_menu() を使用して
        選択肢を表示する。選択時に PME_OT_gpu_enum_select オペレーターを呼び出す。
        """
        from ..widget_factory import register_widget

        # グローバルレジストリに登録（popup_menu 終了後に参照するため）
        widget_id = register_widget(self)

        # クロージャ用の変数
        options = self.options
        current = self.value
        text = self.text

        def draw_menu(menu, context):
            layout = menu.layout
            for ident, name, desc in options:
                # 現在選択されている項目にチェックマークを表示
                icon = 'CHECKMARK' if ident == current else 'NONE'
                op = layout.operator(
                    "pme.gpu_enum_select",
                    text=name,
                    icon=icon,
                )
                op.value = ident
                op.widget_id = widget_id

        # popup_menu を表示
        bpy.context.window_manager.popup_menu(draw_menu, title=text or "Select")

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """メニューボタンを描画（wcol_menu テーマ使用）"""
        if not self.visible:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.MENU)
        if wcol is None:
            self._draw_fallback(style, state)
            return

        # 状態の判定
        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        radius = int(wcol.roundness * self.height * 0.5)

        # === 1. 背景描画 ===
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
        outline_color = wcol.outline if enabled else tuple(
            c * 0.5 for c in wcol.outline[:3]
        ) + (wcol.outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # === 3. コンテンツ描画 ===
        text_color = wcol.text if enabled else tuple(
            c * 0.5 for c in wcol.text[:3]
        ) + (wcol.text[3],)

        self._draw_content(style, text_color, enabled)

    def _draw_content(self, style: GPULayoutStyle, text_color: tuple, enabled: bool) -> None:
        """アイコン、テキスト、ドロップダウン矢印を描画"""
        text_size = style.scaled_text_size()
        padding = style.scaled_padding()
        icon_size = style.scaled_icon_size()
        spacing = style.scaled_spacing()
        alpha = 1.0 if enabled else 0.5

        # ドロップダウン矢印の幅を確保
        arrow_w = icon_size + spacing

        # テキスト開始位置
        text_x = self.x + padding

        # 左側アイコン描画
        if self.icon != "NONE":
            icon_y = self.y - (self.height - icon_size) / 2
            IconDrawing.draw_icon(text_x, icon_y, self.icon, alpha=alpha)
            text_x += icon_size + spacing

        # テキスト表示可能な幅
        available_width = self.width - padding * 2 - arrow_w
        if self.icon != "NONE":
            available_width -= icon_size + spacing

        # テキスト描画（display_name を表示）
        display_text = BLFDrawing.get_text_with_ellipsis(
            self.display_name, available_width, text_size
        )
        _, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        text_y = self.y - (self.height + text_h) / 2

        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

        # ドロップダウン矢印描画（右端）
        arrow_x = self.x + self.width - padding - icon_size
        arrow_y = self.y - (self.height - icon_size) / 2
        IconDrawing.draw_icon(arrow_x, arrow_y, 'DOWNARROW_HLT', alpha=alpha)

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        # 角丸半径（デフォルト roundness 0.4、Blender 準拠: roundness × height × 0.5）
        radius = int(0.4 * self.height * 0.5)

        # 背景色
        bg_color = style.button_hover_color if hovered else style.button_color
        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景（align=True 時は corners で角丸を制御）
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, style.outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # コンテンツ描画
        text_color = style.button_text_color if enabled else style.text_color_disabled
        self._draw_content(style, text_color, enabled)
