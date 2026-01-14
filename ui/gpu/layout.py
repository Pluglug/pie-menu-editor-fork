# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Main Layout Class

Blender UILayout API を模した GPU 描画レイアウトシステム。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from .style import GPULayoutStyle, Direction, Alignment
from .drawing import GPUDrawing
from .items import (
    LayoutItem, LabelItem, SeparatorItem, ButtonItem, ToggleItem,
    PropDisplayItem, BoxItem
)
from .interactive import HitTestManager

if TYPE_CHECKING:
    from bpy.types import Event


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
        self._cursor_x = x + self.style.scaled_padding()
        self._cursor_y = y - self.style.scaled_padding()

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

        self._hit_manager: Optional[HitTestManager] = None

    # ─────────────────────────────────────────────────────────────────────────
    # コンテナメソッド（UILayout 互換）
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def hit_manager(self) -> Optional[HitTestManager]:
        """HitTestManager（未使用なら None）"""
        return self._hit_manager

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
        return self.width - self.style.scaled_padding() * 2

    def _get_spacing(self) -> int:
        """アイテム間のスペースを取得（align=True で 0）"""
        return 0 if self._align else self.style.scaled_spacing()

    def _add_item(self, item: LayoutItem) -> None:
        """アイテムを追加"""
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
            return self.style.scaled_padding() * 2

        spacing = self._get_spacing()
        if self.direction == Direction.VERTICAL:
            height = self.style.scaled_padding() * 2
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
            width = self.style.scaled_padding() * 2
            for item in self._items:
                w, _ = item.calc_size(self.style)
                width += w * self.scale_x + spacing
            for child in self._children:
                width += child.calc_width() + spacing
            return width
        else:
            return self.width

    # ─────────────────────────────────────────────────────────────────────────
    # レイアウト計算
    # ─────────────────────────────────────────────────────────────────────────

    def layout(self) -> None:
        """レイアウトを計算（子レイアウトの位置を確定）"""
        # 自身のアイテムを再配置
        self._relayout_items()

        spacing = self._get_spacing()

        # 子レイアウトを配置
        cursor_y = self.y - self.style.scaled_padding()
        cursor_x = self.x + self.style.scaled_padding()

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
            child.layout()

            if self.direction == Direction.VERTICAL:
                cursor_y -= child.calc_height() + spacing
            else:
                cursor_x += child.calc_width() + spacing

        if self._hit_manager:
            self._hit_manager.update_positions()

    def _relayout_items(self) -> None:
        """アイテムの位置を再計算"""
        cursor_x = self.x + self.style.scaled_padding()
        cursor_y = self.y - self.style.scaled_padding()
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
        """GPU 描画を実行"""
        # レイアウト計算
        self.layout()
        height = self.calc_height()

        # 背景描画
        if self._draw_background:
            GPUDrawing.draw_rounded_rect(
                self.x, self.y, self.width, height,
                self.style.border_radius, self.style.bg_color
            )

        # アウトライン描画
        if self._draw_outline:
            GPUDrawing.draw_rounded_rect_outline(
                self.x, self.y, self.width, height,
                self.style.border_radius, self.style.outline_color
            )

        # アイテム描画
        for item in self._items:
            item.draw(self.style)

        # 子レイアウト描画
        for child in self._children:
            child.draw()

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
