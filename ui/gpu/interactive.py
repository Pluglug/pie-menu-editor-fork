# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Interactive System

ヒットテストとインタラクション状態の管理。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from bpy.types import Event


# ═══════════════════════════════════════════════════════════════════════════════
# UIState - 集中状態管理
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UIState:
    """
    UI 状態の集中管理

    ID ベースで状態を管理し、描画時に参照する。
    これにより、各アイテムが個別に状態を持つ必要がなくなる。
    """
    hovered_id: Optional[str] = None
    pressed_id: Optional[str] = None
    focused_id: Optional[str] = None
    dragging_id: Optional[str] = None

    def clear(self) -> None:
        """すべての状態をクリア"""
        self.hovered_id = None
        self.pressed_id = None
        self.focused_id = None
        self.dragging_id = None

    def is_hovered(self, item_id: str) -> bool:
        """指定 ID がホバー中かどうか"""
        return self.hovered_id == item_id

    def is_pressed(self, item_id: str) -> bool:
        """指定 ID がプレス中かどうか"""
        return self.pressed_id == item_id

    def is_focused(self, item_id: str) -> bool:
        """指定 ID がフォーカス中かどうか"""
        return self.focused_id == item_id


@dataclass
class ItemRenderState:
    """
    描画時に参照するアイテム状態

    HitTestManager.get_render_state() で取得し、
    描画メソッドに渡す。
    """
    hovered: bool = False
    pressed: bool = False
    focused: bool = False
    enabled: bool = True

    @property
    def active(self) -> bool:
        """アクティブ状態（ホバーまたはプレス）"""
        return self.hovered or self.pressed


# ═══════════════════════════════════════════════════════════════════════════════
# HitRect - ヒット可能な矩形領域
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HitRect:
    """
    ヒットテスト用の矩形領域

    Blender の座標系（左下原点、Y上向き）に対応。
    y は矩形の「上端」を指す（GPULayout の座標系と同じ）。
    """
    x: float
    y: float  # 上端
    width: float
    height: float

    # 関連データ
    item: Any = None  # 関連付けられたアイテム
    item_id: str = ""  # 状態管理用の一意識別子（UIState で使用）
    tag: str = ""     # 識別用タグ（デバッグ表示用）
    enabled: bool = True
    visible: bool = True  # 非表示アイテムはヒットテストをスキップ
    z_index: int = 0  # 重なり順（大きいほど前面）

    # コールバック
    on_hover_enter: Optional[Callable[[], None]] = None
    on_hover_leave: Optional[Callable[[], None]] = None
    on_click: Optional[Callable[[], None]] = None
    on_press: Optional[Callable[[], None]] = None
    on_release: Optional[Callable[[bool], None]] = None  # bool = inside

    # ドラッグ
    draggable: bool = False
    on_drag: Optional[Callable[[float, float], None]] = None  # (delta_x, delta_y)

    def contains(self, px: float, py: float) -> bool:
        """点が矩形内にあるかどうか"""
        return (self.x <= px <= self.x + self.width and
                self.y - self.height <= py <= self.y)

    def intersects(self, other: HitRect) -> bool:
        """他の矩形と交差するかどうか"""
        return not (
            self.x + self.width < other.x or
            other.x + other.width < self.x or
            self.y < other.y - other.height or
            other.y < self.y - self.height
        )

    @classmethod
    def from_item(cls, item: Any) -> HitRect:
        """LayoutItem から HitRect を作成"""
        return cls(
            x=item.x,
            y=item.y,
            width=item.width,
            height=item.height,
            item=item,
            enabled=getattr(item, 'enabled', True),
            visible=getattr(item, 'visible', True)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# InteractionState - インタラクション状態
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class InteractionState:
    """
    現在のインタラクション状態

    マウスの状態とホバー/プレス中のアイテムを追跡。
    """
    mouse_x: float = 0
    mouse_y: float = 0

    # 現在の状態
    hovered: Optional[HitRect] = None
    pressed: Optional[HitRect] = None

    # ドラッグ状態
    drag_start_x: float = 0
    drag_start_y: float = 0
    is_dragging: bool = False
    dragging_rect: Optional[HitRect] = None  # ドラッグ中の HitRect

    def update_mouse(self, x: float, y: float) -> None:
        """マウス位置を更新"""
        self.mouse_x = x
        self.mouse_y = y


# ═══════════════════════════════════════════════════════════════════════════════
# HitTestManager - ヒットテスト管理
# ═══════════════════════════════════════════════════════════════════════════════

class HitTestManager:
    """
    ヒットテストの中央管理

    使用例:
        manager = HitTestManager()

        # HitRect を登録
        rect = HitRect(x=100, y=200, width=50, height=30,
                       on_click=lambda: print("Clicked!"))
        manager.register(rect)

        # または LayoutItem から自動登録
        manager.register_item(button_item)

        # イベント処理（modal オペレーター内で）
        if manager.handle_event(event):
            return {'RUNNING_MODAL'}

        # 描画前にレイアウトが変わったら再構築
        manager.clear()
        manager.register_item(...)
    """

    def __init__(self):
        self._rects: list[HitRect] = []
        self._state = InteractionState()
        self._ui_state = UIState()  # 集中状態管理

    @property
    def state(self) -> InteractionState:
        """現在のインタラクション状態"""
        return self._state

    @property
    def hovered(self) -> Optional[HitRect]:
        """現在ホバー中の HitRect"""
        return self._state.hovered

    @property
    def pressed(self) -> Optional[HitRect]:
        """現在プレス中の HitRect"""
        return self._state.pressed

    @property
    def ui_state(self) -> UIState:
        """集中状態管理（ID ベース）"""
        return self._ui_state

    def get_render_state(self, item_id: str, enabled: bool = True) -> ItemRenderState:
        """
        描画用のアイテム状態を取得

        Args:
            item_id: アイテムの一意識別子
            enabled: アイテムが有効かどうか

        Returns:
            描画時に参照する状態
        """
        return ItemRenderState(
            hovered=self._ui_state.is_hovered(item_id),
            pressed=self._ui_state.is_pressed(item_id),
            focused=self._ui_state.is_focused(item_id),
            enabled=enabled,
        )

    def get_render_state_for_rect(self, rect: HitRect) -> ItemRenderState:
        """
        HitRect から描画用の状態を取得

        Args:
            rect: HitRect インスタンス

        Returns:
            描画時に参照する状態
        """
        # item_id があればそれを使用、なければ HitRect の参照比較で判定
        if rect.item_id:
            return self.get_render_state(rect.item_id, rect.enabled)

        # フォールバック: HitRect の参照比較
        return ItemRenderState(
            hovered=self._state.hovered is rect,
            pressed=self._state.pressed is rect,
            focused=False,
            enabled=rect.enabled,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 登録・解除
    # ─────────────────────────────────────────────────────────────────────────

    def register(self, rect: HitRect) -> None:
        """HitRect を登録"""
        self._rects.append(rect)

    def register_item(self, item: Any, item_id: str = "", **callbacks) -> HitRect:
        """
        LayoutItem から HitRect を作成して登録

        Args:
            item: LayoutItem インスタンス
            item_id: 状態管理用の一意識別子（省略時は id(item) を使用）
            **callbacks: on_hover_enter, on_hover_leave, on_click, etc.

        Returns:
            作成された HitRect
        """
        rect = HitRect.from_item(item)

        # item_id を設定（UIState で使用）
        rect.item_id = item_id or str(id(item))

        # コールバックを設定
        for key, callback in callbacks.items():
            if hasattr(rect, key):
                setattr(rect, key, callback)

        # on_click コールバックがアイテムにあれば自動バインド
        if hasattr(item, 'on_click') and item.on_click and rect.on_click is None:
            rect.on_click = item.on_click

        self._rects.append(rect)
        return rect

    def unregister(self, rect: HitRect) -> None:
        """HitRect を解除"""
        if rect in self._rects:
            self._rects.remove(rect)
            # 状態もクリア
            if self._state.hovered is rect:
                self._state.hovered = None
            if self._state.pressed is rect:
                self._state.pressed = None
            # ドラッグ中の場合もクリア
            if self._state.dragging_rect is rect:
                self._state.is_dragging = False
                self._state.dragging_rect = None
            # UIState の ID ベース状態もクリア（item_id が一致する場合）
            if rect.item_id:
                if self._ui_state.hovered_id == rect.item_id:
                    self._ui_state.hovered_id = None
                if self._ui_state.pressed_id == rect.item_id:
                    self._ui_state.pressed_id = None
                if self._ui_state.dragging_id == rect.item_id:
                    self._ui_state.dragging_id = None

    def clear(self) -> None:
        """すべての HitRect をクリア"""
        # ホバー解除イベントを発火
        if self._state.hovered and self._state.hovered.on_hover_leave:
            self._state.hovered.on_hover_leave()

        self._rects.clear()

        # InteractionState を完全にリセット
        self._state.hovered = None
        self._state.pressed = None
        self._state.is_dragging = False
        self._state.dragging_rect = None
        self._state.drag_start_x = 0
        self._state.drag_start_y = 0

        # UIState もリセット
        self._ui_state.clear()

    # ─────────────────────────────────────────────────────────────────────────
    # ヒットテスト
    # ─────────────────────────────────────────────────────────────────────────

    def hit_test(self, x: float, y: float) -> Optional[HitRect]:
        """
        座標でヒットテストを実行

        Returns:
            ヒットした HitRect（複数ある場合は z_index が最大のもの）
        """
        # visible=False のアイテムはヒットテストをスキップ
        hits = [r for r in self._rects if r.visible and r.enabled and r.contains(x, y)]
        if not hits:
            return None

        # z_index でソート、最大のものを返す
        return max(hits, key=lambda r: r.z_index)

    def hit_test_all(self, x: float, y: float) -> list[HitRect]:
        """
        座標でヒットテストを実行し、すべてのヒットを返す

        Returns:
            ヒットした HitRect のリスト（z_index 降順）
        """
        # visible=False のアイテムはヒットテストをスキップ
        hits = [r for r in self._rects if r.visible and r.enabled and r.contains(x, y)]
        return sorted(hits, key=lambda r: r.z_index, reverse=True)

    # ─────────────────────────────────────────────────────────────────────────
    # イベント処理
    # ─────────────────────────────────────────────────────────────────────────

    def handle_event(self, event: Event, region=None) -> bool:
        """
        イベントを処理

        Args:
            event: Blender イベント
            region: Blender region（オプション、指定すると正確な座標計算）

        Returns:
            イベントを消費したかどうか
        """
        # Note: event.mouse_region_x/y は特定の状況で正しく動作しないことがある
        # bl_ui_widgets の実装を参考に、mouse_x - region.x を使用
        if region is not None:
            mouse_x = event.mouse_x - region.x
            mouse_y = event.mouse_y - region.y
            if (mouse_x < 0 or mouse_y < 0 or
                    mouse_x > region.width or mouse_y > region.height):
                mouse_x = event.mouse_region_x
                mouse_y = event.mouse_region_y
        else:
            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y
        self._state.update_mouse(mouse_x, mouse_y)

        if event.type == 'MOUSEMOVE':
            return self._handle_mouse_move(mouse_x, mouse_y)

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                return self._handle_press(mouse_x, mouse_y)
            elif event.value == 'RELEASE':
                return self._handle_release(mouse_x, mouse_y)

        return False

    def _handle_mouse_move(self, x: float, y: float) -> bool:
        """マウス移動を処理"""
        # ドラッグ中の処理
        if self._state.is_dragging and self._state.dragging_rect:
            dx = x - self._state.drag_start_x
            dy = y - self._state.drag_start_y

            if self._state.dragging_rect.on_drag:
                self._state.dragging_rect.on_drag(dx, dy)

            # ドラッグ開始位置を更新（累積移動のため）
            self._state.drag_start_x = x
            self._state.drag_start_y = y
            return True

        new_hover = self.hit_test(x, y)
        old_hover = self._state.hovered

        if new_hover is not old_hover:
            # 旧ホバーを解除
            if old_hover and old_hover.on_hover_leave:
                old_hover.on_hover_leave()

            # 新ホバーを設定
            if new_hover and new_hover.on_hover_enter:
                new_hover.on_hover_enter()

            self._state.hovered = new_hover
            self._ui_state.hovered_id = new_hover.item_id if new_hover else None

        return new_hover is not None

    def _handle_press(self, x: float, y: float) -> bool:
        """マウスプレスを処理"""
        hit = self.hit_test(x, y)
        if hit is None:
            return False

        self._state.pressed = hit
        self._state.drag_start_x = x
        self._state.drag_start_y = y
        self._ui_state.pressed_id = hit.item_id if hit.item_id else None

        # ドラッグ可能な場合はドラッグ開始
        if hit.draggable:
            self._state.is_dragging = True
            self._state.dragging_rect = hit
            self._ui_state.dragging_id = hit.item_id if hit.item_id else None

        if hit.on_press:
            hit.on_press()

        return True

    def _handle_release(self, x: float, y: float) -> bool:
        """マウスリリースを処理"""
        pressed = self._state.pressed
        if pressed is None:
            return False

        inside = pressed.contains(x, y)

        if pressed.on_release:
            pressed.on_release(inside)

        # クリック判定
        if inside and pressed.on_click:
            pressed.on_click()

        self._state.pressed = None
        self._state.is_dragging = False
        self._state.dragging_rect = None
        self._ui_state.pressed_id = None
        self._ui_state.dragging_id = None

        return True

    # ─────────────────────────────────────────────────────────────────────────
    # ユーティリティ
    # ─────────────────────────────────────────────────────────────────────────

    def update_positions(self) -> None:
        """
        登録済み HitRect の位置をアイテムから再取得

        レイアウト後に呼び出して位置を同期する。
        """
        for rect in self._rects:
            if rect.item is not None:
                rect.x = rect.item.x
                rect.y = rect.item.y
                rect.width = rect.item.width
                rect.height = rect.item.height
                rect.enabled = getattr(rect.item, 'enabled', True)
                rect.visible = getattr(rect.item, 'visible', True)

    def debug_draw(self) -> None:
        """デバッグ用: すべての HitRect を可視化"""
        from .drawing import GPUDrawing

        for rect in self._rects:
            if rect is self._state.hovered:
                color = (0.0, 1.0, 0.0, 0.3)  # 緑: ホバー中
            elif rect is self._state.pressed:
                color = (1.0, 0.0, 0.0, 0.3)  # 赤: プレス中
            elif not rect.enabled:
                color = (0.5, 0.5, 0.5, 0.2)  # グレー: 無効
            else:
                color = (0.0, 0.5, 1.0, 0.2)  # 青: 通常

            GPUDrawing.draw_rounded_rect(
                rect.x, rect.y, rect.width, rect.height,
                2, color
            )
