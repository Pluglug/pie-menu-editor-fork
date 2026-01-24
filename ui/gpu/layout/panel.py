# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Panel Chrome
"""

from __future__ import annotations

import bpy
from typing import Callable, Optional

from ..interactive import HitRect
from .constants import MIN_PANEL_WIDTH, RESIZE_HANDLE_SIZE, CLAMP_MARGIN, IS_MAC


class LayoutPanelMixin:
    """Mixin methods."""


    def set_title_bar(self, title: str = "", show_close: bool = True,
                      on_close: Optional[Callable[[], None]] = None) -> None:
        """
        タイトルバーを有効化

        Args:
            title: タイトル文字列
            show_close: クローズボタンを表示するか
            on_close: クローズボタンのコールバック
        """
        self._show_title_bar = True
        self._title = title
        self._show_close_button = show_close
        self._on_close = on_close


    def set_panel_config(self, uid: str = None,
                         resizable: bool = False,
                         min_width: float = MIN_PANEL_WIDTH) -> None:
        """
        パネルのリサイズと永続化を設定

        Args:
            uid: 永続化用の一意識別子（pm.uid）
            resizable: 右下コーナーでリサイズ可能にする
            min_width: 最小幅の制約

        Note:
            重複起動防止は GPUPanelManager が担当します。
            このメソッドは位置・サイズの永続化とリサイズ機能のみを設定します。
        """
        self._panel_uid = uid
        self._show_resize_handle = resizable
        self._min_width = min_width

        if uid:
            self._restore_panel_state()


    def _restore_panel_state(self) -> None:
        """window_manager から位置・サイズを復元"""
        if not self._panel_uid:
            return
        try:
            wm = bpy.context.window_manager
            states = wm.get('_gpu_layout_states', {})
            if self._panel_uid in states:
                state = states[self._panel_uid]
                self.x = state.get('x', self.x)
                self.y = state.get('y', self.y)
                self.width = max(state.get('width', self.width), self._min_width)
                self.mark_dirty()
        except Exception:
            pass


    def _save_panel_state(self) -> None:
        """window_manager に位置・サイズを保存"""
        if not self._panel_uid:
            return
        try:
            wm = bpy.context.window_manager
            states = wm.get('_gpu_layout_states', None)
            if states is None:
                states = {}
                wm['_gpu_layout_states'] = states
            states[self._panel_uid] = {
                'x': self.x,
                'y': self.y,
                'width': self.width,
            }
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # 境界クランプ
    # ─────────────────────────────────────────────────────────────────────────


    def set_region_bounds(self, width: float, height: float) -> None:
        """
        境界クランプ用のリージョンサイズを設定

        Args:
            width: リージョンの幅
            height: リージョンの高さ

        Note:
            この設定後、パネルは自動的にリージョン内にクランプされます。
            - タイトルバーは常にリージョン内に表示
            - ドラッグ終了時に位置を補正
            - リージョンリサイズ時も位置を維持
        """
        old_width = self._region_width
        old_height = self._region_height

        self._region_width = width
        self._region_height = height

        # リージョンサイズが変わった場合はクランプを実行
        if old_width != width or old_height != height:
            self._clamp_position()


    def _clamp_position(self) -> None:
        """
        パネル位置をリージョン境界内にクランプ

        タイトルバー全体（閉じるボタン含む）が常に見えるように位置を調整します。
        コンテンツ部分は下側にはみ出すことを許容します。

        座標系:
            - Blender は左下原点、Y 上向き
            - self.y はコンテンツ領域の上端
            - title_bar_y = self.y + title_bar_height（タイトルバー上端）
        """
        if self._region_width is None or self._region_height is None:
            return

        margin = int(self.style.ui_scale(CLAMP_MARGIN))
        title_bar_height = self._get_title_bar_height() if self._show_title_bar else 0

        # X 座標のクランプ（タイトルバー全体が見える範囲）
        # 左端: パネル左端がマージン以上
        min_x = margin
        # 右端: パネル右端がリージョン幅 - マージン以下
        max_x = self._region_width - margin - self.width

        # パネル幅がリージョン幅より大きい場合は左寄せ
        if max_x < min_x:
            max_x = min_x

        # Y 座標のクランプ（タイトルバー基準）
        # 下端: タイトルバー上端がマージン以上（title_bar_y >= margin）
        min_y = margin - title_bar_height if self._show_title_bar else margin
        # 上端: タイトルバー上端がリージョン高さ - マージン以下
        max_y = self._region_height - margin - title_bar_height if self._show_title_bar else self._region_height - margin

        # クランプを適用
        clamped = False
        old_x, old_y = self.x, self.y

        self.x = max(min_x, min(self.x, max_x))
        self.y = max(min_y, min(self.y, max_y))

        if self.x != old_x or self.y != old_y:
            clamped = True

        if clamped:
            self._save_panel_state()
            self.mark_dirty()


    def _get_title_bar_height(self) -> int:
        """スケーリングされたタイトルバーの高さを取得"""
        return self.style.scaled_title_bar_height()


    def _get_close_button_size(self) -> int:
        """スケーリングされたクローズボタンのサイズを取得"""
        return int(self.style.ui_scale(16))


    def _get_title_bar_y(self) -> float:
        """タイトルバーの Y 座標（上端）を取得"""
        return self.y + self._get_title_bar_height()


    def _get_content_y(self) -> float:
        """コンテンツ領域の Y 座標（上端）を取得"""
        if self._show_title_bar:
            return self.y  # タイトルバーの下
        return self.y


    def contains_point(self, x: float, y: float) -> bool:
        """
        指定した点がパネル境界内（タイトルバー含む）にあるかどうか

        Args:
            x: X 座標（リージョン座標系）
            y: Y 座標（リージョン座標系）

        Returns:
            境界内なら True

        Note:
            リサイズハンドルやドロップシャドウ領域は含みません。
            タイトルバーがある場合はタイトルバーも含みます。
        """
        # 上端: タイトルバーがあればその上端、なければコンテンツ上端
        if self._show_title_bar:
            top_y = self._get_title_bar_y()
            total_height = self.calc_height() + self._get_title_bar_height()
        else:
            top_y = self.y
            total_height = self.calc_height()

        # 下端
        bottom_y = top_y - total_height

        # 境界判定
        return (self.x <= x <= self.x + self.width and
                bottom_y <= y <= top_y)


    def _register_title_bar(self) -> None:
        """タイトルバーの HitRect を登録"""
        if not self._show_title_bar:
            return

        manager = self._ensure_hit_manager()
        title_bar_y = self._get_title_bar_y()
        title_bar_height = self._get_title_bar_height()
        base_path = self._layout_path or "root"
        title_bar_key = self._make_layout_key(f"{base_path}.title_bar")
        close_button_key = self._make_layout_key(f"{base_path}.close_button")

        # クローズボタン領域を除いたタイトルバー
        close_btn_size = self._get_close_button_size()
        close_btn_margin = int(self.style.ui_scale(6))

        if self._show_close_button:
            if IS_MAC:
                # Mac: 左側にクローズボタン
                drag_x = self.x + close_btn_size + close_btn_margin * 2
                drag_width = self.width - close_btn_size - close_btn_margin * 2
            else:
                # Windows/Linux: 右側にクローズボタン
                drag_x = self.x
                drag_width = self.width - close_btn_size - close_btn_margin * 2
        else:
            drag_x = self.x
            drag_width = self.width

        # タイトルバーのドラッグ領域
        if self._title_bar_rect is None:
            def on_drag(dx: float, dy: float, abs_x: float, abs_y: float):
                self.x += dx
                self.y += dy
                self._save_panel_state()
                self.mark_dirty()

            def on_drag_end(inside: bool):
                # ドラッグ終了時に境界内にクランプ
                self._clamp_position()

            self._title_bar_rect = HitRect(
                x=drag_x,
                y=title_bar_y,
                width=drag_width,
                height=title_bar_height,
                tag="title_bar",
                draggable=True,
                on_drag=on_drag,
                on_release=on_drag_end,
                z_index=100  # 他の要素より優先
            )
            self._title_bar_rect.layout_key = title_bar_key
            manager.register(self._title_bar_rect)
        else:
            # 位置とサイズを更新
            self._title_bar_rect.x = drag_x
            self._title_bar_rect.y = title_bar_y
            self._title_bar_rect.width = drag_width
            self._title_bar_rect.height = title_bar_height
            self._title_bar_rect.layout_key = title_bar_key

        # クローズボタン
        if self._show_close_button and self._close_button_rect is None:
            if IS_MAC:
                close_x = self.x + close_btn_margin
            else:
                close_x = self.x + self.width - close_btn_size - close_btn_margin

            close_y = title_bar_y - (title_bar_height - close_btn_size) / 2

            def on_close_hover_enter():
                self._close_button_hovered = True

            def on_close_hover_leave():
                self._close_button_hovered = False

            def on_close_click():
                if self._on_close:
                    self._on_close()

            self._close_button_rect = HitRect(
                x=close_x,
                y=close_y,
                width=close_btn_size,
                height=close_btn_size,
                tag="close_button",
                on_hover_enter=on_close_hover_enter,
                on_hover_leave=on_close_hover_leave,
                on_click=on_close_click,
                z_index=101  # タイトルバーより優先
            )
            self._close_button_rect.layout_key = close_button_key
            manager.register(self._close_button_rect)
        elif self._close_button_rect is not None:
            # 位置とサイズを更新
            if IS_MAC:
                self._close_button_rect.x = self.x + close_btn_margin
            else:
                self._close_button_rect.x = self.x + self.width - close_btn_size - close_btn_margin
            self._close_button_rect.y = title_bar_y - (title_bar_height - close_btn_size) / 2
            self._close_button_rect.width = close_btn_size
            self._close_button_rect.height = close_btn_size
            self._close_button_rect.layout_key = close_button_key


    def _register_resize_handle(self) -> None:
        """リサイズハンドルの HitRect を右下コーナーに登録"""
        if not self._show_resize_handle:
            return

        manager = self._ensure_hit_manager()
        content_height = self.calc_height()
        handle_size = int(self.style.ui_scale(RESIZE_HANDLE_SIZE))

        # タイトルバーを含む全体高さを計算
        if self._show_title_bar:
            base_y = self._get_title_bar_y()
            total_height = content_height + self._get_title_bar_height()
        else:
            base_y = self.y
            total_height = content_height

        # 右下コーナーの位置（アウトライン内に収めるためマージンを追加）
        margin = 4
        handle_x = self.x + self.width - handle_size - margin
        handle_y = base_y - total_height + handle_size + margin

        if self._resize_handle_rect is None:
            def on_resize_drag(dx: float, dy: float, abs_x: float, abs_y: float):
                new_width = self.width + dx
                self.width = max(new_width, self._min_width)
                self._save_panel_state()
                self.mark_dirty()

            def on_hover_enter():
                self._resize_handle_hovered = True

            def on_hover_leave():
                self._resize_handle_hovered = False

            self._resize_handle_rect = HitRect(
                x=handle_x,
                y=handle_y,
                width=handle_size,
                height=handle_size,
                tag="resize_handle",
                draggable=True,
                on_drag=on_resize_drag,
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                z_index=102  # タイトルバー(100)、クローズボタン(101)より上
            )
            base_path = self._layout_path or "root"
            self._resize_handle_rect.layout_key = self._make_layout_key(f"{base_path}.resize_handle")
            manager.register(self._resize_handle_rect)
        else:
            # 位置更新
            self._resize_handle_rect.x = handle_x
            self._resize_handle_rect.y = handle_y
            self._resize_handle_rect.width = handle_size
            self._resize_handle_rect.height = handle_size
            base_path = self._layout_path or "root"
            self._resize_handle_rect.layout_key = self._make_layout_key(f"{base_path}.resize_handle")

    # ─────────────────────────────────────────────────────────────────────────
    # 2-pass レイアウトアルゴリズム（Phase 1）
    # ─────────────────────────────────────────────────────────────────────────
