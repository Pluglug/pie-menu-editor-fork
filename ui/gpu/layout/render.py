# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Rendering
"""

from __future__ import annotations

from ..drawing import GPUDrawing, BLFDrawing
from ..items import (
    ButtonItem,
    ToggleItem,
    SliderItem,
    NumberItem,
    CheckboxItem,
    ColorItem,
    RadioGroupItem,
)
from .constants import IS_MAC, RESIZE_HANDLE_SIZE


class LayoutRenderMixin:
    """Mixin methods."""


    def draw(self) -> None:
        """
        GPU 描画を実行

        Note:
            この関数は描画のみを行います。レイアウト計算が必要な場合は
            事前に layout() を呼び出すか、update_and_draw() を使用してください。
        """
        content_height = self.calc_height()
        total_height = content_height
        if self._show_title_bar:
            total_height += self._get_title_bar_height()

        # 描画の基準 Y 座標
        draw_y = self._get_title_bar_y() if self._show_title_bar else self.y

        # スケーリングされた値を取得
        border_radius = self.style.scaled_border_radius()

        # パネルシャドウ描画（背景の前に描画、3辺: 左、下、右）
        if self.style.shadow_enabled and self._draw_background:
            GPUDrawing.draw_panel_shadow(
                self.x, draw_y, self.width, total_height,
                border_radius,
                self.style.scaled_shadow_width(),
                self.style.shadow_alpha
            )

        # 背景描画（タイトルバー含む）
        if self._draw_background:
            GPUDrawing.draw_rounded_rect(
                self.x, draw_y, self.width, total_height,
                border_radius, self.style.bg_color
            )

        # アウトライン描画
        if self._draw_outline:
            GPUDrawing.draw_rounded_rect_outline(
                self.x, draw_y, self.width, total_height,
                border_radius, self.style.outline_color
            )

        # タイトルバー描画
        if self._show_title_bar:
            self._draw_title_bar()

        # リサイズハンドル描画
        self._draw_resize_handle()

        # 要素描画（追加順序を保持）
        # Phase 1: _elements を使用して item と child を正しい順序で描画
        for element in self._elements:
            if isinstance(element, GPULayout):
                # 子レイアウト
                element.draw()
            else:
                # LayoutItem
                if self._hit_manager and isinstance(element, (ButtonItem, ToggleItem, SliderItem, NumberItem, CheckboxItem, ColorItem, RadioGroupItem)):
                    # インタラクティブなアイテムには状態を渡す
                    layout_key = self._get_layout_key_for_item(element)
                    state = self._hit_manager.get_render_state(layout_key.as_id(), element.enabled)
                    element.draw(self.style, state)
                else:
                    element.draw(self.style)


    def update_and_draw(self) -> None:
        """
        レイアウト計算と描画を一度に実行

        便利メソッド。layout() + draw() と同等。
        """
        self.layout()
        self.draw()


    def _draw_title_bar(self) -> None:
        """タイトルバーを描画"""
        title_bar_y = self._get_title_bar_y()
        title_bar_height = self._get_title_bar_height()
        close_btn_size = self._get_close_button_size()
        close_btn_margin = int(self.style.ui_scale(6))
        border_radius = self.style.scaled_border_radius()

        # タイトルバー背景（少し暗め）
        title_bg = tuple(c * 0.8 for c in self.style.bg_color[:3]) + (self.style.bg_color[3],)
        # corners: (bottomLeft, topLeft, topRight, bottomRight)
        # タイトルバーは上の角だけ丸める
        GPUDrawing.draw_rounded_rect(
            self.x, title_bar_y, self.width, title_bar_height,
            border_radius, title_bg,
            corners=(False, True, True, False)
        )

        # タイトルバーのアウトライン（上と左右、パネルアウトラインと同じ太さ）
        # タイトルバー背景がパネルのアウトラインを上書きするため再描画
        GPUDrawing.draw_rounded_rect_outline(
            self.x, title_bar_y, self.width, title_bar_height,
            border_radius, self.style.outline_color,
            corners=(False, True, True, False)
        )

        # タイトルバー下部の境界線（パネルアウトラインと同じ太さ）
        line_y = title_bar_y - title_bar_height
        line_width = self.style.line_width()
        # 矩形として描画（ストローク方式のアウトラインと見た目を統一）
        GPUDrawing.draw_rect(
            self.x + 1, line_y + line_width / 2,
            self.width - 2, line_width,
            self.style.outline_color
        )

        # タイトルテキスト
        if self._title:
            text_x = self.x + self.style.scaled_padding_x()
            if IS_MAC and self._show_close_button:
                text_x = self.x + close_btn_size + close_btn_margin * 2 + int(self.style.ui_scale(4))
            text_y = title_bar_y - title_bar_height / 2 - int(self.style.ui_scale(4))
            text_size = self.style.scaled_text_size()

            # 利用可能なテキスト幅を計算（パディングとクローズボタンを考慮）
            padding_x = self.style.scaled_padding_x()
            if self._show_close_button:
                available_width = self.width - close_btn_size - close_btn_margin * 2 - padding_x * 2
            else:
                available_width = self.width - padding_x * 2

            # テキストが利用可能幅を超える場合は省略記号を追加
            display_title = BLFDrawing.get_text_with_ellipsis(self._title, available_width, text_size)

            # クリップ矩形を計算（タイトルバー領域内）
            clip_rect = BLFDrawing.calc_clip_rect(
                self.x + padding_x, title_bar_y,
                self.width - padding_x * 2, title_bar_height
            )

            BLFDrawing.draw_text_clipped(
                text_x, text_y, display_title,
                self.style.text_color, text_size, clip_rect
            )

        # クローズボタン
        if self._show_close_button:
            if IS_MAC:
                btn_x = self.x + close_btn_margin + close_btn_size / 2
            else:
                btn_x = self.x + self.width - close_btn_margin - close_btn_size / 2
            btn_y = title_bar_y - title_bar_height / 2

            # ホバー時は明るく
            if self._close_button_hovered:
                btn_color = (0.9, 0.3, 0.3, 1.0)  # 明るい赤
            else:
                btn_color = (0.7, 0.25, 0.25, 1.0)  # 暗めの赤

            GPUDrawing.draw_circle(btn_x, btn_y, close_btn_size / 2, btn_color)


    def _draw_resize_handle(self) -> None:
        """リサイズグリップハンドルを右下コーナーに描画"""
        if not self._show_resize_handle:
            return

        content_height = self.calc_height()
        handle_size = int(self.style.ui_scale(RESIZE_HANDLE_SIZE))

        if self._show_title_bar:
            base_y = self._get_title_bar_y()
            total_height = content_height + self._get_title_bar_height()
        else:
            base_y = self.y
            total_height = content_height

        # 右下コーナー（アウトライン内に収めるためマージンを追加）
        margin = 4
        handle_x = self.x + self.width - handle_size - margin
        handle_y = base_y - total_height + handle_size + margin

        # テーマカラーから派生（通常: 暗め、ホバー: 明るめ）
        if self._resize_handle_hovered:
            # ホバー時: text_color_secondary
            line_color = self.style.text_color_secondary
        else:
            # 通常時: text_color_secondary を暗く
            base = self.style.text_color_secondary
            line_color = (base[0] * 0.6, base[1] * 0.6, base[2] * 0.6, base[3])
        line_width = 0.8  # 細め

        # 3本の斜め線（右下から左上への対角線パターン）
        for i, factor in enumerate([0.3, 0.55, 0.8]):
            offset = int(handle_size * factor)
            GPUDrawing.draw_rounded_line(
                handle_x + handle_size - offset, handle_y - handle_size,
                handle_x + handle_size, handle_y - handle_size + offset,
                line_color, line_width
            )

    # ─────────────────────────────────────────────────────────────────────────
    # イベント処理
    # ─────────────────────────────────────────────────────────────────────────
