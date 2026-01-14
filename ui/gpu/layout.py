# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Main Layout Class

Blender UILayout API を模した GPU 描画レイアウトシステム。
"""

from __future__ import annotations

import bpy
import sys
from typing import TYPE_CHECKING, Any, Callable, Optional

from .style import GPULayoutStyle, Direction, Alignment
from .drawing import GPUDrawing, BLFDrawing
from .items import (
    LayoutItem, LabelItem, SeparatorItem, ButtonItem, ToggleItem,
    PropDisplayItem, BoxItem
)
from .interactive import HitTestManager, HitRect

if TYPE_CHECKING:
    from bpy.types import Event

# プラットフォーム検出
IS_MAC = sys.platform == 'darwin'

# パネルリサイズ定数
MIN_PANEL_WIDTH = 200
MIN_PANEL_HEIGHT = 100  # 将来用（高さリサイズ時）
RESIZE_HANDLE_SIZE = 16  # UI スケーリング前のピクセル


class GPULayout:
    """
    Blender UILayout を模した GPU 描画レイアウトシステム

    使用例:
        layout = GPULayout(x=100, y=500, width=300)
        layout.label(text="Title", icon='INFO')

        row = layout.row()
        row.label(text="Left")
        row.label(text="Right")

        layout.separator()
        layout.prop_display(context.object, "name", text="Object")

        layout.operator(text="Click Me", on_click=lambda: print("Clicked!"))

        # 描画
        layout.draw()

        # イベント処理（modal オペレーター内で）
        layout.handle_event(event)
    """

    def __init__(self, x: float, y: float, width: float,
                 style: Optional[GPULayoutStyle] = None,
                 direction: Direction = Direction.VERTICAL,
                 parent: Optional[GPULayout] = None):
        """
        Args:
            x: 左上 X 座標
            y: 左上 Y 座標（Blender は左下原点なので注意）
            width: 幅
            style: スタイル（None の場合は Blender テーマから自動取得）
            direction: レイアウト方向
            parent: 親レイアウト
        """
        self.x = x
        self.y = y
        self.width = width
        self.style = style or GPULayoutStyle.from_blender_theme()
        self.direction = direction
        self.parent = parent

        # アイテムと子レイアウト
        self._items: list[LayoutItem] = []
        self._children: list[GPULayout] = []

        # カーソル位置
        self._cursor_x = x + self.style.scaled_padding_x()
        self._cursor_y = y - self.style.scaled_padding_y()

        # 状態プロパティ（UILayout 互換）
        self.active: bool = True
        self.enabled: bool = True
        self.alert: bool = False
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.alignment: Alignment = Alignment.EXPAND

        # アイテム間スペースを制御（align=True で 0）
        self._align: bool = False

        # split 用（0.0 = 自動計算、0.0-1.0 = 最初の column の割合）
        self._split_factor: float = 0.0
        self._split_column_index: int = 0  # column() が呼ばれるたびにインクリメント

        # ボックス描画フラグ
        self._draw_background: bool = False
        self._draw_outline: bool = False

        # タイトルバー
        self._show_title_bar: bool = False
        self._title: str = ""
        self._show_close_button: bool = False
        self._on_close: Optional[Callable[[], None]] = None
        self._title_bar_rect: Optional[HitRect] = None
        self._close_button_rect: Optional[HitRect] = None
        self._close_button_hovered: bool = False

        self._hit_manager: Optional[HitTestManager] = None

        # Dirty Flag: レイアウト再計算が必要かどうか
        self._dirty: bool = True

        # リサイズハンドル
        self._show_resize_handle: bool = False
        self._resize_handle_rect: Optional[HitRect] = None
        self._resize_handle_hovered: bool = False
        self._panel_uid: Optional[str] = None
        self._min_width: float = MIN_PANEL_WIDTH

    # ─────────────────────────────────────────────────────────────────────────
    # コンテナメソッド（UILayout 互換）
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def hit_manager(self) -> Optional[HitTestManager]:
        """HitTestManager（未使用なら None）"""
        return self._hit_manager

    @property
    def dirty(self) -> bool:
        """レイアウト再計算が必要かどうか"""
        return self._dirty

    def mark_dirty(self) -> None:
        """レイアウトの再計算が必要であることをマーク"""
        self._dirty = True
        for child in self._children:
            child.mark_dirty()

    def row(self, align: bool = False) -> GPULayout:
        """
        水平レイアウトを作成

        Args:
            align: True の場合、アイテム間のスペースをなくす
        """
        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=self._get_available_width(),
            style=self.style,
            direction=Direction.HORIZONTAL,
            parent=self
        )
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child._align = align  # アイテム間スペースを制御
        self._children.append(child)
        return child

    def column(self, align: bool = False) -> GPULayout:
        """
        垂直レイアウトを作成

        Args:
            align: True の場合、アイテム間のスペースをなくす

        Note:
            split() 内で呼ばれた場合、factor に基づいて幅が計算される。
            - factor > 0: 最初の column が factor 割合、残りは均等分割
            - factor == 0: 全ての column を均等分割
        """
        available_width = self._get_available_width()

        # split の中で呼ばれた場合、factor に基づいて幅を計算
        if self._split_factor > 0.0 and self._split_column_index == 0:
            # 最初の column: factor 割合
            col_width = available_width * self._split_factor
        elif self._split_factor > 0.0 and self._split_column_index == 1:
            # 2番目の column: 残り全部（単純化のため 2 列のみサポート）
            col_width = available_width * (1.0 - self._split_factor)
        else:
            # 自動計算または 3 列目以降: 利用可能幅をそのまま使用
            col_width = available_width

        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=col_width,
            style=self.style,
            direction=Direction.VERTICAL,
            parent=self
        )
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child._align = align
        self._children.append(child)

        # split 用インデックスをインクリメント
        self._split_column_index += 1

        return child

    def box(self) -> GPULayout:
        """ボックス付きレイアウトを作成"""
        child = self.column()
        child._draw_background = True
        child._draw_outline = True
        return child

    def split(self, *, factor: float = 0.0, align: bool = False) -> GPULayout:
        """
        分割レイアウトを作成

        Args:
            factor: 最初の column の幅の割合 (0.0-1.0)
                    0.0 の場合は自動計算（均等分割）
            align: True の場合、column 間のスペースをなくす

        使用例:
            split = layout.split(factor=0.3)
            col1 = split.column()
            col1.label(text="Left (30%)")
            col2 = split.column()
            col2.label(text="Right (70%)")
        """
        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=self._get_available_width(),
            style=self.style,
            direction=Direction.HORIZONTAL,
            parent=self
        )
        child._split_factor = factor
        child._align = align
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        self._children.append(child)
        return child

    # ─────────────────────────────────────────────────────────────────────────
    # 表示メソッド（UILayout 互換）
    # ─────────────────────────────────────────────────────────────────────────

    def label(self, *, text: str = "", icon: str = "NONE") -> None:
        """ラベルを追加"""
        item = LabelItem(
            text=text,
            icon=icon,
            enabled=self.enabled and self.active,
            alert=self.alert
        )
        self._add_item(item)

    def separator(self, factor: float = 1.0) -> None:
        """区切り線を追加"""
        item = SeparatorItem(factor=factor)
        self._add_item(item)

    def separator_spacer(self) -> None:
        """スペーサーを追加（separator のエイリアス）"""
        self.separator(factor=0.5)

    def operator(self, operator: str = "", *, text: str = "", icon: str = "NONE",
                 on_click: Optional[Callable[[], None]] = None) -> ButtonItem:
        """
        オペレーターボタンを追加

        Note: 実際の Blender オペレーターは呼び出せないため、
              on_click コールバックで代替する
        """
        item = ButtonItem(
            text=text or operator,
            icon=icon,
            on_click=on_click,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    # ─────────────────────────────────────────────────────────────────────────
    # プロパティメソッド
    # ─────────────────────────────────────────────────────────────────────────

    def prop(self, data: Any, property: str, *, text: str = "",
             icon: str = "NONE", expand: bool = False, slider: bool = False,
             toggle: int = -1, icon_only: bool = False) -> None:
        """
        プロパティを表示（読み取り専用）

        Note: GPU 版では編集不可。表示のみ。
              toggle=1 の場合は ToggleItem を使用。
        """
        if toggle == 1:
            # トグルボタン
            try:
                value = getattr(data, property)
            except AttributeError:
                value = False

            def on_toggle(new_value: bool):
                try:
                    setattr(data, property, new_value)
                except AttributeError:
                    pass

            item = ToggleItem(
                text=text or property,
                icon=icon,
                value=bool(value),
                on_toggle=on_toggle,
                enabled=self.enabled and self.active
            )
            self._add_item(item)
        else:
            # 読み取り専用表示
            self.prop_display(data, property, text=text, icon=icon)

    def prop_display(self, data: Any, property: str, *,
                     text: str = "", icon: str = "NONE") -> None:
        """プロパティ値を表示（明示的に読み取り専用）"""
        item = PropDisplayItem(
            data=data,
            property=property,
            text=text,
            icon=icon,
            enabled=self.enabled and self.active
        )
        self._add_item(item)

    def prop_enum(self, data: Any, property: str, value: str, *,
                  text: str = "", icon: str = "NONE") -> None:
        """Enum プロパティの特定値を表示"""
        try:
            current = getattr(data, property)
            is_active = current == value
        except AttributeError:
            is_active = False

        display_text = text or value
        if is_active:
            display_text = f"● {display_text}"
        else:
            display_text = f"○ {display_text}"

        self.label(text=display_text, icon=icon)

    # ─────────────────────────────────────────────────────────────────────────
    # ユーティリティメソッド
    # ─────────────────────────────────────────────────────────────────────────

    def _get_available_width(self) -> float:
        """利用可能な幅を取得"""
        return self.width - self.style.scaled_padding_x() * 2

    def _get_spacing(self) -> int:
        """アイテム間のスペースを取得（align=True で 0）"""
        return 0 if self._align else self.style.scaled_spacing()

    def _add_item(self, item: LayoutItem) -> None:
        """アイテムを追加"""
        self._dirty = True  # アイテム追加でレイアウト再計算が必要
        item_width, item_height = item.calc_size(self.style)
        available_width = self._get_available_width()

        if self.direction == Direction.VERTICAL:
            # alignment に応じて幅と位置を計算
            if self.alignment == Alignment.EXPAND:
                # EXPAND: 利用可能幅いっぱいに拡張
                item.width = available_width * self.scale_x
                item.x = self._cursor_x
            else:
                # LEFT/CENTER/RIGHT: 自然サイズを維持
                item.width = item_width * self.scale_x
                if self.alignment == Alignment.CENTER:
                    item.x = self._cursor_x + (available_width - item.width) / 2
                elif self.alignment == Alignment.RIGHT:
                    item.x = self._cursor_x + available_width - item.width
                else:  # LEFT
                    item.x = self._cursor_x

            item.y = self._cursor_y
            item.height = item_height * self.scale_y

            # LabelItem に alignment を継承
            if hasattr(item, 'alignment'):
                item.alignment = self.alignment

            self._cursor_y -= item.height + self._get_spacing()
        else:
            # 水平レイアウト
            item.x = self._cursor_x
            item.y = self._cursor_y
            item.width = item_width * self.scale_x
            item.height = item_height * self.scale_y

            self._cursor_x += item.width + self._get_spacing()

        self._register_interactive_item(item)
        self._items.append(item)

    def calc_height(self) -> float:
        """合計高さを計算"""
        if not self._items and not self._children:
            return self.style.scaled_padding_y() * 2

        spacing = self._get_spacing()
        if self.direction == Direction.VERTICAL:
            height = self.style.scaled_padding_y() * 2
            for item in self._items:
                _, h = item.calc_size(self.style)
                height += h * self.scale_y + spacing
            for child in self._children:
                height += child.calc_height() + spacing
            return height
        else:
            # 水平レイアウト - 最大の高さ
            max_height = 0
            for item in self._items:
                _, h = item.calc_size(self.style)
                max_height = max(max_height, h * self.scale_y)
            for child in self._children:
                max_height = max(max_height, child.calc_height())
            return max_height + spacing

    def calc_width(self) -> float:
        """合計幅を計算"""
        if not self._items and not self._children:
            return self.width

        spacing = self._get_spacing()
        if self.direction == Direction.HORIZONTAL:
            width = self.style.scaled_padding_x() * 2
            for item in self._items:
                w, _ = item.calc_size(self.style)
                width += w * self.scale_x + spacing
            for child in self._children:
                width += child.calc_width() + spacing
            return width
        else:
            return self.width

    # ─────────────────────────────────────────────────────────────────────────
    # タイトルバー設定
    # ─────────────────────────────────────────────────────────────────────────

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

    def _register_title_bar(self) -> None:
        """タイトルバーの HitRect を登録"""
        if not self._show_title_bar:
            return

        manager = self._ensure_hit_manager()
        title_bar_y = self._get_title_bar_y()
        title_bar_height = self._get_title_bar_height()

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
            def on_drag(dx: float, dy: float):
                self.x += dx
                self.y += dy
                self._save_panel_state()
                self.mark_dirty()

            self._title_bar_rect = HitRect(
                x=drag_x,
                y=title_bar_y,
                width=drag_width,
                height=title_bar_height,
                tag="title_bar",
                draggable=True,
                on_drag=on_drag,
                z_index=100  # 他の要素より優先
            )
            manager.register(self._title_bar_rect)
        else:
            # 位置とサイズを更新
            self._title_bar_rect.x = drag_x
            self._title_bar_rect.y = title_bar_y
            self._title_bar_rect.width = drag_width
            self._title_bar_rect.height = title_bar_height

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
            def on_resize_drag(dx: float, dy: float):
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
            manager.register(self._resize_handle_rect)
        else:
            # 位置更新
            self._resize_handle_rect.x = handle_x
            self._resize_handle_rect.y = handle_y
            self._resize_handle_rect.width = handle_size
            self._resize_handle_rect.height = handle_size

    # ─────────────────────────────────────────────────────────────────────────
    # レイアウト計算
    # ─────────────────────────────────────────────────────────────────────────

    def layout(self, *, force: bool = False) -> None:
        """
        レイアウトを計算（子レイアウトの位置を確定）

        Args:
            force: True の場合、Dirty Flag に関係なく再計算
        """
        if not self._dirty and not force:
            return  # 変更がなければスキップ

        # 自身のアイテムを再配置
        self._relayout_items()

        spacing = self._get_spacing()

        # 子レイアウトを配置
        cursor_y = self.y - self.style.scaled_padding_y()
        cursor_x = self.x + self.style.scaled_padding_x()

        # 既存アイテムの後からカーソル位置を取得
        if self._items:
            if self.direction == Direction.VERTICAL:
                last_item = self._items[-1]
                cursor_y = last_item.y - last_item.height - spacing
            else:
                last_item = self._items[-1]
                cursor_x = last_item.x + last_item.width + spacing

        for child in self._children:
            child.x = cursor_x
            child.y = cursor_y
            child.layout(force=force)

            if self.direction == Direction.VERTICAL:
                cursor_y -= child.calc_height() + spacing
            else:
                cursor_x += child.calc_width() + spacing

        # タイトルバーの HitRect を登録（handle_event で呼ばれた場合も対応）
        self._register_title_bar()
        self._register_resize_handle()

        if self._hit_manager:
            self._hit_manager.update_positions()

        self._dirty = False  # レイアウト完了

    def _relayout_items(self) -> None:
        """アイテムの位置を再計算"""
        cursor_x = self.x + self.style.scaled_padding_x()
        cursor_y = self.y - self.style.scaled_padding_y()
        available_width = self._get_available_width()
        spacing = self._get_spacing()

        for item in self._items:
            item_width, item_height = item.calc_size(self.style)

            if self.direction == Direction.VERTICAL:
                # alignment に応じて幅と位置を計算
                if self.alignment == Alignment.EXPAND:
                    item.width = available_width * self.scale_x
                    item.x = cursor_x
                else:
                    item.width = item_width * self.scale_x
                    if self.alignment == Alignment.CENTER:
                        item.x = cursor_x + (available_width - item.width) / 2
                    elif self.alignment == Alignment.RIGHT:
                        item.x = cursor_x + available_width - item.width
                    else:  # LEFT
                        item.x = cursor_x

                item.y = cursor_y
                item.height = item_height * self.scale_y
                cursor_y -= item.height + spacing
            else:
                # 水平レイアウト
                item.x = cursor_x
                item.y = cursor_y
                item.width = item_width * self.scale_x
                item.height = item_height * self.scale_y
                cursor_x += item.width + spacing

    # ─────────────────────────────────────────────────────────────────────────
    # 描画
    # ─────────────────────────────────────────────────────────────────────────

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

        # ドロップシャドウ描画（背景の前に描画）
        if self.style.shadow_enabled and self._draw_background:
            GPUDrawing.draw_drop_shadow(
                self.x, draw_y, self.width, total_height,
                border_radius,
                self.style.shadow_color,
                self.style.scaled_shadow_offset(),
                self.style.scaled_shadow_blur()
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

        # アイテム描画
        for item in self._items:
            # インタラクティブなアイテムには状態を渡す
            if self._hit_manager and isinstance(item, (ButtonItem, ToggleItem)):
                # item_id を取得（登録時に設定される）
                item_id = str(id(item))
                state = self._hit_manager.get_render_state(item_id, item.enabled)
                item.draw(self.style, state)
            else:
                item.draw(self.style)

        # 子レイアウト描画
        for child in self._children:
            child.draw()

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

        # タイトルバー下部の境界線
        line_y = title_bar_y - title_bar_height
        GPUDrawing.draw_line(
            self.x + 1, line_y,
            self.x + self.width - 1, line_y,
            self.style.outline_color, 1.0
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

    def handle_event(self, event: Event, region=None) -> bool:
        """
        イベントを処理

        Args:
            event: Blender イベント
            region: Blender region（オプション）

        Returns:
            イベントを消費したかどうか
        """
        self.layout()
        return self._handle_event(event, region)

    def _handle_event(self, event: Event, region=None) -> bool:
        # 子レイアウトを先に処理
        for child in self._children:
            if child._handle_event(event, region):
                return True

        if self._hit_manager:
            return self._hit_manager.handle_event(event, region)

        # region 座標からマウス位置を取得
        # Note: 呼び出し側で region.x, region.y を引く必要がある場合あり
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        # アイテムを処理
        for item in self._items:
            if item.handle_event(event, mouse_x, mouse_y):
                return True

        return False

    def is_inside(self, x: float, y: float) -> bool:
        """座標がレイアウト内かどうか"""
        height = self.calc_height()
        return (self.x <= x <= self.x + self.width and
                self.y - height <= y <= self.y)

    def _ensure_hit_manager(self) -> HitTestManager:
        if self._hit_manager is None:
            self._hit_manager = HitTestManager()
        return self._hit_manager

    def _register_interactive_item(self, item: LayoutItem) -> None:
        if not isinstance(item, (ButtonItem, ToggleItem)):
            return

        manager = self._ensure_hit_manager()

        if isinstance(item, ToggleItem):
            def on_click():
                item.value = not item.value
                if item.on_toggle:
                    item.on_toggle(item.value)

            rect = manager.register_item(item, on_click=on_click)
        else:
            rect = manager.register_item(item)

        if hasattr(item, 'text') and item.text:
            rect.tag = item.text
