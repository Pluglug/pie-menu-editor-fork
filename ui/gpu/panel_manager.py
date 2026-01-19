# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Panel Manager

GPU パネルのライフサイクル管理を担当するマネージャークラス。

責務:
- アクティブパネルの追跡（重複起動防止）
- リージョンポインタの管理
- 描画ハンドラ/タイマーの登録・解除
- Blender ライフサイクルとの同期
"""

from __future__ import annotations

import weakref
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Optional

import bpy
from bpy.app.handlers import persistent

if TYPE_CHECKING:
    from bpy.types import Context, Event
    from .layout import GPULayout


class PanelState(Enum):
    """パネルの状態"""
    CLOSED = auto()
    OPENING = auto()
    OPEN = auto()
    CLOSING = auto()


class GPUPanelManager:
    """
    GPU パネルのライフサイクル管理

    責務:
    - アクティブパネルの追跡（重複起動防止）
    - リージョンポインタの管理
    - 描画ハンドラ/タイマーの登録・解除
    - Blender ライフサイクルとの同期

    使用例:
        # オペレーター invoke
        def invoke(self, context, event):
            if GPUPanelManager.is_active("my_panel"):
                return {'CANCELLED'}  # 既に開いている

            self._layout = GPULayout(...)
            self._manager = GPUPanelManager("my_panel", self._layout)

            if not self._manager.open(context, self._draw_callback):
                return {'CANCELLED'}

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        # オペレーター cancel
        def cancel(self, context):
            if self._manager:
                self._manager.close(context)
    """

    # === クラス変数 ===
    _active: dict[str, GPUPanelManager] = {}
    _handlers_registered: bool = False

    # === インスタンス変数 ===
    def __init__(self, uid: str, layout: GPULayout):
        """
        Args:
            uid: パネルの一意識別子
            layout: 管理対象の GPULayout
        """
        self.uid = uid
        self._layout_ref: Callable[[], Optional[GPULayout]] = weakref.ref(layout)
        self._state = PanelState.CLOSED
        self.region_pointer: int = 0
        self._draw_handler: Any = None
        self._timer: Any = None
        self._space_type: str = ''

        # Blender ハンドラを確実に登録
        self.__class__.ensure_handlers()

    # ─────────────────────────────────────────────────────────────────────────
    # プロパティ
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def layout(self) -> Optional[GPULayout]:
        """管理対象の GPULayout（GC されていれば None）"""
        return self._layout_ref()

    @property
    def is_open(self) -> bool:
        """パネルが開いているかどうか"""
        return self._state == PanelState.OPEN

    @property
    def state(self) -> PanelState:
        """パネルの状態"""
        return self._state

    # ─────────────────────────────────────────────────────────────────────────
    # クラスメソッド
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def get(cls, uid: str) -> Optional[GPUPanelManager]:
        """既存のマネージャーを取得"""
        return cls._active.get(uid)

    @classmethod
    def is_active(cls, uid: str) -> bool:
        """指定 uid のパネルがアクティブかどうか"""
        return uid in cls._active

    @classmethod
    def list_active_uids(cls) -> list[str]:
        """アクティブなパネルの uid リストを返す"""
        return list(cls._active.keys())

    @classmethod
    def close_by_uid(cls, uid: str, context: Optional[Context] = None) -> bool:
        """
        uid でパネルを閉じる

        Args:
            uid: パネルの一意識別子
            context: Blender コンテキスト（None の場合は bpy.context を使用）

        Returns:
            パネルが存在して閉じられたかどうか
        """
        manager = cls._active.get(uid)
        if manager:
            ctx = context or bpy.context
            manager.close(ctx)
            return True
        return False

    @classmethod
    def close_all(cls, context: Optional[Context] = None) -> None:
        """全パネルを閉じる"""
        ctx = context or bpy.context
        for manager in list(cls._active.values()):
            try:
                manager.close(ctx)
            except Exception:
                pass
        cls._active.clear()

    @classmethod
    def ensure_handlers(cls) -> None:
        """Blender ハンドラを登録（一度だけ）"""
        if cls._handlers_registered:
            return

        @persistent
        def on_load_post(dummy):
            # ファイル読み込み時に全パネルを閉じる
            cls._active.clear()

        # 既に登録されていないか確認
        if on_load_post not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(on_load_post)

        cls._handlers_registered = True

    @classmethod
    def unregister_handlers(cls) -> None:
        """Blender ハンドラを解除（アドオン無効化時に呼び出し）"""
        # ハンドラを探して削除
        handlers_to_remove = []
        for handler in bpy.app.handlers.load_post:
            # 関数名で識別（persistent デコレーター後も名前は保持される）
            if hasattr(handler, '__name__') and handler.__name__ == 'on_load_post':
                handlers_to_remove.append(handler)

        for handler in handlers_to_remove:
            try:
                bpy.app.handlers.load_post.remove(handler)
            except ValueError:
                pass

        cls._handlers_registered = False
        cls._active.clear()

    # ─────────────────────────────────────────────────────────────────────────
    # ライフサイクル管理
    # ─────────────────────────────────────────────────────────────────────────

    def open(self, context: Context,
             draw_callback: Callable,
             space_type: str = 'VIEW_3D',
             timer_interval: float = 0.05) -> bool:
        """
        パネルを開く

        Args:
            context: Blender コンテキスト
            draw_callback: 描画コールバック関数 (manager, context) を受け取る
            space_type: スペースタイプ ('VIEW_3D', 'IMAGE_EDITOR', etc.)
            timer_interval: タイマー間隔（秒）。0 以下でタイマー無効。

        Returns:
            成功したかどうか（既に開いている場合は False）

        Note:
            modal_handler_add() はオペレーター側で呼び出す必要があります。
            この関数は描画ハンドラとタイマーのみを登録します。
        """
        if self._state != PanelState.CLOSED:
            return False

        if self.uid in self._active:
            return False  # 別インスタンスが既にアクティブ

        self._state = PanelState.OPENING

        try:
            # リージョンポインタを取得
            self.region_pointer = context.region.as_pointer()
            self._space_type = space_type

            # 描画ハンドラを登録
            space_class = self._get_space_class(space_type)
            self._draw_handler = space_class.draw_handler_add(
                draw_callback, (self, context), 'WINDOW', 'POST_PIXEL'
            )

            # タイマーを登録（オプション）
            if timer_interval > 0:
                self._timer = context.window_manager.event_timer_add(
                    timer_interval, window=context.window
                )

            # 成功 - 登録
            self._active[self.uid] = self
            self._state = PanelState.OPEN
            return True

        except Exception:
            self._cleanup_partial(context)
            self._state = PanelState.CLOSED
            raise

    def close(self, context: Context) -> None:
        """パネルを閉じてクリーンアップ"""
        if self._state == PanelState.CLOSED:
            return

        self._state = PanelState.CLOSING

        try:
            # 描画ハンドラを解除
            if self._draw_handler and self._space_type:
                try:
                    space_class = self._get_space_class(self._space_type)
                    space_class.draw_handler_remove(self._draw_handler, 'WINDOW')
                except Exception:
                    pass
                self._draw_handler = None

            # タイマーを解除
            if self._timer:
                try:
                    context.window_manager.event_timer_remove(self._timer)
                except Exception:
                    pass
                self._timer = None

            # 辞書から削除
            if self.uid in self._active:
                del self._active[self.uid]

            # リージョンを再描画
            self._redraw_region(context)

        finally:
            self.region_pointer = 0
            self._space_type = ''
            self._state = PanelState.CLOSED

    # ─────────────────────────────────────────────────────────────────────────
    # 描画ヘルパー
    # ─────────────────────────────────────────────────────────────────────────

    def should_draw(self, context: Context) -> bool:
        """
        このリージョンで描画すべきかどうか

        draw_callback 内で呼び出して、別のリージョンでの描画をスキップ。
        マルチビューポート環境で必須。
        """
        if not self.region_pointer:
            return False
        return context.region.as_pointer() == self.region_pointer

    def tag_redraw(self, context: Context) -> None:
        """リージョンの再描画をリクエスト"""
        self._redraw_region(context)

    # ─────────────────────────────────────────────────────────────────────────
    # イベント処理ヘルパー
    # ─────────────────────────────────────────────────────────────────────────

    def handle_event(self, event: Event, context: Context) -> bool:
        """
        イベントを GPULayout に転送

        Args:
            event: Blender イベント
            context: Blender コンテキスト

        Returns:
            イベントが処理されたかどうか
        """
        layout = self.layout
        if layout is None:
            return False

        region = context.region
        if region is None:
            return False

        return layout.handle_event(event, region)

    def contains_point(self, x: float, y: float) -> bool:
        """
        指定した点がパネル境界内にあるかどうか

        Args:
            x: X 座標（リージョン座標系）
            y: Y 座標（リージョン座標系）

        Returns:
            パネル境界内なら True

        Note:
            パネルが開いていない、または layout が GC されている場合は False
        """
        layout = self.layout
        if layout is None:
            return False
        return layout.contains_point(x, y)

    # ─────────────────────────────────────────────────────────────────────────
    # プライベートメソッド
    # ─────────────────────────────────────────────────────────────────────────

    def _get_space_class(self, space_type: str):
        """スペースタイプからクラスを取得"""
        mapping = {
            'VIEW_3D': bpy.types.SpaceView3D,
            'IMAGE_EDITOR': bpy.types.SpaceImageEditor,
            'NODE_EDITOR': bpy.types.SpaceNodeEditor,
            'TEXT_EDITOR': bpy.types.SpaceTextEditor,
            'PROPERTIES': bpy.types.SpaceProperties,
            'OUTLINER': bpy.types.SpaceOutliner,
            'DOPESHEET_EDITOR': bpy.types.SpaceDopeSheetEditor,
            'GRAPH_EDITOR': bpy.types.SpaceGraphEditor,
            'NLA_EDITOR': bpy.types.SpaceNLA,
            'SEQUENCE_EDITOR': bpy.types.SpaceSequenceEditor,
            'CLIP_EDITOR': bpy.types.SpaceClipEditor,
            'CONSOLE': bpy.types.SpaceConsole,
            'INFO': bpy.types.SpaceInfo,
            'FILE_BROWSER': bpy.types.SpaceFileBrowser,
            'PREFERENCES': bpy.types.SpacePreferences,
        }
        return mapping.get(space_type, bpy.types.SpaceView3D)

    def _cleanup_partial(self, context: Context) -> None:
        """部分的なクリーンアップ（エラー時）"""
        if self._draw_handler and self._space_type:
            try:
                space_class = self._get_space_class(self._space_type)
                space_class.draw_handler_remove(self._draw_handler, 'WINDOW')
            except Exception:
                pass
            self._draw_handler = None

        if self._timer:
            try:
                context.window_manager.event_timer_remove(self._timer)
            except Exception:
                pass
            self._timer = None

        self.region_pointer = 0

    def _redraw_region(self, context: Context) -> None:
        """リージョンを再描画"""
        if not self._space_type:
            return

        try:
            for area in context.screen.areas:
                if area.type == self._space_type:
                    area.tag_redraw()
        except Exception:
            pass
