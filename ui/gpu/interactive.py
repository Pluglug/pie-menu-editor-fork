# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Interactive System

ヒットテストとインタラクション状態の管理。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol

if TYPE_CHECKING:
    from bpy.types import Event


# ═══════════════════════════════════════════════════════════════════════════════
# Protocols
# ═══════════════════════════════════════════════════════════════════════════════

class Hoverable(Protocol):
    """ホバー可能なアイテムのプロトコル"""
    _hovered: bool

    def on_hover_enter(self) -> None: ...
    def on_hover_leave(self) -> None: ...


class Pressable(Protocol):
    """プレス可能なアイテムのプロトコル"""
    _pressed: bool

    def on_press(self) -> None: ...
    def on_release(self, inside: bool) -> None: ...


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
    tag: str = ""     # 識別用タグ
    enabled: bool = True
    z_index: int = 0  # 重なり順（大きいほど前面）

    # コールバック
    on_hover_enter: Optional[Callable[[], None]] = None
    on_hover_leave: Optional[Callable[[], None]] = None
    on_click: Optional[Callable[[], None]] = None
    on_press: Optional[Callable[[], None]] = None
    on_release: Optional[Callable[[bool], None]] = None  # bool = inside

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
            enabled=getattr(item, 'enabled', True)
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

    # ─────────────────────────────────────────────────────────────────────────
    # 登録・解除
    # ─────────────────────────────────────────────────────────────────────────

    def register(self, rect: HitRect) -> None:
        """HitRect を登録"""
        self._rects.append(rect)

    def register_item(self, item: Any, **callbacks) -> HitRect:
        """
        LayoutItem から HitRect を作成して登録

        Args:
            item: LayoutItem インスタンス
            **callbacks: on_hover_enter, on_hover_leave, on_click, etc.

        Returns:
            作成された HitRect
        """
        rect = HitRect.from_item(item)

        # コールバックを設定
        for key, callback in callbacks.items():
            if hasattr(rect, key):
                setattr(rect, key, callback)

        # アイテムが Hoverable/Pressable なら自動バインド
        if hasattr(item, '_hovered'):
            if rect.on_hover_enter is None:
                rect.on_hover_enter = lambda: setattr(item, '_hovered', True)
            if rect.on_hover_leave is None:
                rect.on_hover_leave = lambda: setattr(item, '_hovered', False)

        if hasattr(item, '_pressed'):
            if rect.on_press is None:
                rect.on_press = lambda: setattr(item, '_pressed', True)
            if rect.on_release is None:
                def on_release(inside: bool):
                    item._pressed = False
                    if inside and hasattr(item, 'on_click') and item.on_click:
                        item.on_click()
                rect.on_release = on_release

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

    def clear(self) -> None:
        """すべての HitRect をクリア"""
        # ホバー解除イベントを発火
        if self._state.hovered and self._state.hovered.on_hover_leave:
            self._state.hovered.on_hover_leave()

        self._rects.clear()
        self._state.hovered = None
        self._state.pressed = None

    # ─────────────────────────────────────────────────────────────────────────
    # ヒットテスト
    # ─────────────────────────────────────────────────────────────────────────

    def hit_test(self, x: float, y: float) -> Optional[HitRect]:
        """
        座標でヒットテストを実行

        Returns:
            ヒットした HitRect（複数ある場合は z_index が最大のもの）
        """
        hits = [r for r in self._rects if r.enabled and r.contains(x, y)]
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
        hits = [r for r in self._rects if r.enabled and r.contains(x, y)]
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
        new_hover = self.hit_test(x, y)
        old_hover = self._state.hovered

        if new_hover is not old_hover:
            # 旧ホバーを解除
            if old_hover:
                if old_hover.on_hover_leave:
                    old_hover.on_hover_leave()
                # アイテムの状態も更新
                if old_hover.item and hasattr(old_hover.item, '_hovered'):
                    old_hover.item._hovered = False

            # 新ホバーを設定
            if new_hover:
                if new_hover.on_hover_enter:
                    new_hover.on_hover_enter()
                # アイテムの状態も更新
                if new_hover.item and hasattr(new_hover.item, '_hovered'):
                    new_hover.item._hovered = True

            self._state.hovered = new_hover

        return new_hover is not None

    def _handle_press(self, x: float, y: float) -> bool:
        """マウスプレスを処理"""
        hit = self.hit_test(x, y)
        if hit is None:
            return False

        self._state.pressed = hit
        self._state.drag_start_x = x
        self._state.drag_start_y = y

        if hit.on_press:
            hit.on_press()

        # アイテムの状態も更新
        if hit.item and hasattr(hit.item, '_pressed'):
            hit.item._pressed = True

        return True

    def _handle_release(self, x: float, y: float) -> bool:
        """マウスリリースを処理"""
        pressed = self._state.pressed
        if pressed is None:
            return False

        inside = pressed.contains(x, y)

        if pressed.on_release:
            pressed.on_release(inside)

        # アイテムの状態も更新
        if pressed.item and hasattr(pressed.item, '_pressed'):
            pressed.item._pressed = False

        # クリック判定
        if inside and pressed.on_click:
            pressed.on_click()

        self._state.pressed = None
        self._state.is_dragging = False

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
