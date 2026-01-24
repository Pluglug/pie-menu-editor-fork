# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Interaction
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..interactive import HitRect, HitTestManager
from ..items import (
    LayoutItem,
    ButtonItem,
    ToggleItem,
    SliderItem,
    NumberItem,
    CheckboxItem,
    ColorItem,
    RadioGroupItem,
    MenuButtonItem,
)

if TYPE_CHECKING:
    from bpy.types import Event


class LayoutInteractionMixin:
    """Mixin methods."""


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
        # このレイアウトでドラッグ中なら最優先で処理（リサイズ/タイトルバーの捕捉）
        if self._hit_manager and self._hit_manager.state.is_dragging:
            return self._hit_manager.handle_event(event, region)

        # 子レイアウトを先に処理
        for element in self._elements:
            if isinstance(element, GPULayout) and element._handle_event(event, region):
                return True

        if self._hit_manager:
            return self._hit_manager.handle_event(event, region)

        # region 座標からマウス位置を取得
        # Note: 呼び出し側で region.x, region.y を引く必要がある場合あり
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        # アイテムを処理
        for element in self._elements:
            if isinstance(element, LayoutItem) and element.handle_event(event, mouse_x, mouse_y):
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
        if not isinstance(item, (ButtonItem, ToggleItem, SliderItem, NumberItem, CheckboxItem, ColorItem, RadioGroupItem, MenuButtonItem)):
            return

        manager = self._ensure_hit_manager()
        layout_key = self._get_layout_key_for_item(item)

        if isinstance(item, ColorItem):
            # カラースウォッチ: カラーバー部分のみをヒット領域に設定
            bar_x, bar_y, bar_width, bar_height = item.get_bar_rect(self.style)

            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_click():
                item.click()

            rect = HitRect(
                x=bar_x,
                y=bar_y,
                width=bar_width,
                height=bar_height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "color",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_click=on_click,
            )
            rect.layout_key = layout_key
            manager.register(rect)
            rect.item_id = str(id(item))
            # ColorItem用のフラグを設定（update_positions()で使用）
            rect._is_color_bar = True
        elif isinstance(item, RadioGroupItem):
            # ラジオボタングループ: ホバーとクリックで個々のボタンを判定
            # style への参照をクロージャでキャプチャ
            style = self.style

            def on_hover_enter():
                pass  # on_move で詳細な処理

            def on_hover_leave():
                item._hovered_index = -1

            def on_move(x: float, y: float):
                # ホバー中のボタンを判定
                item._hovered_index = item.get_button_at(x, y, style)

            def on_click():
                # クリックされたボタンを選択
                # 最後のホバーインデックスを使用
                if item._hovered_index >= 0:
                    item.select_by_index(item._hovered_index)

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag="radio_group",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_move=on_move,
                on_click=on_click,
            )
            rect.layout_key = layout_key
            manager.register(rect)
            rect.item_id = str(id(item))
        elif isinstance(item, CheckboxItem):
            # チェックボックス: クリックでトグル
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_click():
                item.toggle()

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "checkbox",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_click=on_click,
            )
            rect.layout_key = layout_key
            manager.register(rect)
            rect.item_id = str(id(item))
        elif isinstance(item, ToggleItem):
            # トグルボタン: クリックでトグル
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_click():
                item.toggle()

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "toggle",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_click=on_click,
            )
            rect.layout_key = layout_key
            manager.register(rect)
            rect.item_id = str(id(item))
        elif isinstance(item, SliderItem):
            # スライダー: ドラッグで値を変更
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_drag_start(mouse_x: float, mouse_y: float):
                item._dragging = True
                # ドラッグ開始時にクリック位置から値を設定
                item.set_value_from_position(mouse_x)

            def on_drag(dx: float, dy: float, mouse_x: float, mouse_y: float):
                # ドラッグ中は絶対位置から値を更新
                item.set_value_from_position(mouse_x)

            def on_drag_end(inside: bool):
                item._dragging = False

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "slider",
                draggable=True,
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_press=on_drag_start,
                on_drag=on_drag,
                on_release=on_drag_end,
            )
            rect.layout_key = layout_key
            manager.register(rect)
            # item_id を保存（状態取得用）
            rect.item_id = str(id(item))
        elif isinstance(item, NumberItem):
            # 数値フィールド: ドラッグで値を変更（dx に応じて）
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_drag_start(mouse_x: float, mouse_y: float):
                item._dragging = True

            def on_drag(dx: float, dy: float, mouse_x: float, mouse_y: float):
                # ドラッグ移動量から値を更新
                item.set_value_from_delta(dx)

            def on_drag_end(inside: bool):
                item._dragging = False

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "number",
                draggable=True,
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_press=on_drag_start,
                on_drag=on_drag,
                on_release=on_drag_end,
            )
            rect.layout_key = layout_key
            manager.register(rect)
            rect.item_id = str(id(item))
        elif isinstance(item, MenuButtonItem):
            # メニューボタン: クリックでドロップダウンを開く
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_click():
                item.open_menu()

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "menu",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_click=on_click,
            )
            rect.layout_key = layout_key
            manager.register(rect)
            rect.item_id = str(id(item))
        else:
            rect = manager.register_item(item, layout_key=layout_key)

        if hasattr(item, 'text') and item.text:
            rect.tag = item.text
