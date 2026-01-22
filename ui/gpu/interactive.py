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
        """指定キーがホバー中かどうか"""
        return self.hovered_id == item_id

    def is_pressed(self, item_id: str) -> bool:
        """指定キーがプレス中かどうか"""
        return self.pressed_id == item_id

    def is_focused(self, item_id: str) -> bool:
        """指定キーがフォーカス中かどうか"""
        return self.focused_id == item_id


@dataclass(frozen=True)
class LayoutKey:
    """
    LayoutKey = (panel_uid, layout_path, explicit_key)
    """
    panel_uid: str
    layout_path: str
    explicit_key: Optional[str] = None

    def as_id(self) -> str:
        if self.explicit_key:
            # explicit_key は順序変更でも安定する ID として扱う
            return f"{self.panel_uid}:{self.explicit_key}"
        return f"{self.panel_uid}:{self.layout_path}"


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
    layout_key: Optional[LayoutKey] = None
    enabled: bool = True
    visible: bool = True  # 非表示アイテムはヒットテストをスキップ
    z_index: int = 0  # 重なり順（大きいほど前面）

    # コールバック
    on_hover_enter: Optional[Callable[[], None]] = None
    on_hover_leave: Optional[Callable[[], None]] = None
    on_move: Optional[Callable[[float, float], None]] = None  # (mouse_x, mouse_y) - ホバー中のマウス移動
    on_click: Optional[Callable[[], None]] = None
    on_press: Optional[Callable[[float, float], None]] = None  # (mouse_x, mouse_y)
    on_release: Optional[Callable[[bool], None]] = None  # bool = inside

    # ドラッグ
    draggable: bool = False
    on_drag: Optional[Callable[[float, float, float, float], None]] = None  # (dx, dy, abs_x, abs_y)

    def contains(self, px: float, py: float) -> bool:
        """点が矩形内にあるかどうか"""
        return (self.x <= px <= self.x + self.width and
                self.y - self.height <= py <= self.y)

    def state_key(self) -> str:
        """UIState に渡すキーを取得"""
        if self.layout_key is not None:
            return self.layout_key.as_id()
        if self.tag:
            return self.tag
        if self.item_id:
            return self.item_id
        return ""

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
        self._panel_uid: Optional[str] = None
        self._rects: list[HitRect] = []
        self._state = InteractionState()
        self._ui_state = UIState()  # 集中状態管理

    # パネル間ドラッグのグローバルロック
    _drag_owner_uid: Optional[str] = None

    @classmethod
    def get_drag_owner_uid(cls) -> Optional[str]:
        return cls._drag_owner_uid

    @classmethod
    def _set_drag_owner_uid(cls, uid: Optional[str]) -> None:
        cls._drag_owner_uid = uid

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

    def get_render_state(self, state_key: str, enabled: bool = True) -> ItemRenderState:
        """
        描画用のアイテム状態を取得

        Args:
            state_key: 状態管理用のキー
            enabled: アイテムが有効かどうか

        Returns:
            描画時に参照する状態
        """
        return ItemRenderState(
            hovered=self._ui_state.is_hovered(state_key),
            pressed=self._ui_state.is_pressed(state_key),
            focused=self._ui_state.is_focused(state_key),
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
        # state_key があればそれを使用、なければ HitRect の参照比較で判定
        state_key = rect.state_key()
        if state_key:
            return self.get_render_state(state_key, rect.enabled)

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
        if rect.layout_key and self._panel_uid is None:
            self._panel_uid = rect.layout_key.panel_uid
        self._rects.append(rect)

    def register_item(
        self,
        item: Any,
        item_id: str = "",
        layout_key: Optional[LayoutKey] = None,
        **callbacks,
    ) -> HitRect:
        """
        LayoutItem から HitRect を作成して登録

        Args:
            item: LayoutItem インスタンス
            item_id: 状態管理用の一意識別子（省略時は id(item) を使用）
            layout_key: LayoutKey（指定時は状態管理に使用）
            **callbacks: on_hover_enter, on_hover_leave, on_click, etc.

        Returns:
            作成された HitRect
        """
        rect = HitRect.from_item(item)

        # item_id を設定（UIState で使用）
        rect.item_id = item_id or str(id(item))
        if layout_key is not None:
            rect.layout_key = layout_key
            if self._panel_uid is None:
                self._panel_uid = layout_key.panel_uid

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
            # UIState の ID ベース状態もクリア（key が一致する場合）
            state_key = rect.state_key()
            if state_key:
                if self._ui_state.hovered_id == state_key:
                    self._ui_state.hovered_id = None
                if self._ui_state.pressed_id == state_key:
                    self._ui_state.pressed_id = None
                if self._ui_state.dragging_id == state_key:
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
        if self._panel_uid and self._drag_owner_uid == self._panel_uid:
            self._set_drag_owner_uid(None)

    def reset_rects(self, *, preserve_hovered: bool = False) -> None:
        """
        HitRect のみをリセット（UIState を必要に応じて維持）

        Args:
            preserve_hovered: True の場合、hovered_id を保持する
        """
        hovered_id = self._ui_state.hovered_id if preserve_hovered else None

        self._rects.clear()
        self._state.hovered = None
        self._state.pressed = None
        self._state.is_dragging = False
        self._state.dragging_rect = None
        self._state.drag_start_x = 0
        self._state.drag_start_y = 0

        self._ui_state.clear()
        if preserve_hovered:
            self._ui_state.hovered_id = hovered_id
        if self._panel_uid and self._drag_owner_uid == self._panel_uid:
            self._set_drag_owner_uid(None)

    def _locked_by_other_panel(self) -> bool:
        if not self._drag_owner_uid:
            return False
        return self._panel_uid != self._drag_owner_uid

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
        if self._locked_by_other_panel():
            return False
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
                self._state.dragging_rect.on_drag(dx, dy, x, y)

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
            self._ui_state.hovered_id = new_hover.state_key() if new_hover else None

        # ホバー中のマウス移動を通知（RadioGroupItem などで使用）
        if new_hover and new_hover.on_move:
            new_hover.on_move(x, y)

        return new_hover is not None

    def _handle_press(self, x: float, y: float) -> bool:
        """マウスプレスを処理"""
        hit = self.hit_test(x, y)
        if hit is None:
            return False

        self._state.pressed = hit
        self._state.drag_start_x = x
        self._state.drag_start_y = y
        self._ui_state.pressed_id = hit.state_key() if hit else None

        # ドラッグ可能な場合はドラッグ開始
        if hit.draggable:
            self._state.is_dragging = True
            self._state.dragging_rect = hit
            self._ui_state.dragging_id = hit.state_key() if hit else None
            if self._panel_uid:
                self._set_drag_owner_uid(self._panel_uid)

        if hit.on_press:
            hit.on_press(x, y)

        return True

    def _handle_release(self, x: float, y: float) -> bool:
        """マウスリリースを処理"""
        pressed = self._state.pressed
        if pressed is None:
            return False
        was_dragging = self._state.is_dragging

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
        if was_dragging and self._panel_uid and self._drag_owner_uid == self._panel_uid:
            self._set_drag_owner_uid(None)

        return True

    # ─────────────────────────────────────────────────────────────────────────
    # ユーティリティ
    # ─────────────────────────────────────────────────────────────────────────

    def update_positions(self, style=None) -> None:
        """
        登録済み HitRect の位置をアイテムから再取得

        レイアウト後に呼び出して位置を同期する。

        Args:
            style: GPULayoutStyle（ColorItem の get_bar_rect() に必要）
        """
        for rect in self._rects:
            if rect.item is not None:
                # ColorItem の場合はカラーバー部分のみをヒット領域に
                if getattr(rect, '_is_color_bar', False) and style is not None:
                    bar_x, bar_y, bar_width, bar_height = rect.item.get_bar_rect(style)
                    rect.x = bar_x
                    rect.y = bar_y
                    rect.width = bar_width
                    rect.height = bar_height
                else:
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
