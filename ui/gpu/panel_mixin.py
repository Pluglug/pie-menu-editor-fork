# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Panel Mixin

GPU 描画によるオーバーレイパネルの Mixin クラス。
開発者は draw_panel() メソッドのみ実装すれば、ドラッグ移動・リサイズ・
閉じるボタンなどの機能を持つパネルを作成できる。

Note:
    このクラスは Operator を直接継承しない。
    addon.py のローダーで Operator と合成される。

Usage:
    from pme.types import GPUPanelOperator

    class MY_OT_panel(GPUPanelOperator):
        bl_idname = "my.panel"
        bl_label = "My Panel"

        gpu_panel_uid = "my_panel"
        gpu_title = "My Panel"

        def draw_panel(self, layout, context):
            layout.label(text="Hello World")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    import bpy
    from bpy.types import Context, Event, Region
    from .layout import GPULayout
    from .panel_manager import GPUPanelManager
else:
    # Blender's typing.get_type_hints evaluates forward refs at runtime.
    # Provide fallbacks to avoid NameError during operator registration.
    try:
        from bpy.types import Context, Event, Region  # type: ignore
    except Exception:
        Context = Event = Region = object  # type: ignore
    try:
        from .layout import GPULayout  # type: ignore
    except Exception:
        GPULayout = object  # type: ignore
    try:
        from .panel_manager import GPUPanelManager  # type: ignore
    except Exception:
        GPUPanelManager = object  # type: ignore


class GPUPanelMixin:
    """GPU 描画パネルの Mixin クラス

    test_layout.py の DEMO_OT_* から抽出した共通パターン。

    Attributes:
        gpu_panel_uid: パネルの一意識別子（必須）
        gpu_space_type: パネルを表示するエディタタイプ
        gpu_width: パネルの初期幅
        gpu_style: GPULayoutStyle のプリセット名
        gpu_title: タイトルバーのテキスト
        gpu_resizable: リサイズ可能かどうか
        gpu_show_close: 閉じるボタンを表示するか
        gpu_default_x: 初期位置 X
        gpu_default_y_offset: 初期位置 Y（リージョン上端からのオフセット）
        gpu_close_on: パネルを閉じるイベントタイプのセット
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # クラス変数（サブクラスでオーバーライド）
    # ═══════════════════════════════════════════════════════════════════════════

    gpu_panel_uid: str = ""
    """パネルの一意識別子（必須）。
    重複チェックに使用。同一 uid のパネルは同時に1つしか開けない。
    """

    gpu_space_type: str = 'VIEW_3D'
    """パネルを表示するエディタタイプ。
    'VIEW_3D', 'IMAGE_EDITOR', 'NODE_EDITOR', etc.
    """

    gpu_width: int = 250
    """Initial width in UI units (scaled by system.ui_scale)."""

    gpu_style: str = 'PANEL'
    """GPULayoutStyle のプリセット名。
    'PANEL', 'MENU', 'TOOLTIP', 'BOX', etc.
    """

    gpu_title: str = ""
    """タイトルバーのテキスト。空文字ならタイトルバー非表示。"""

    gpu_resizable: bool = True
    """リサイズ可能かどうか。"""

    gpu_show_close: bool = True
    """閉じるボタンを表示するか。gpu_title が空の場合は無視。"""

    gpu_default_x: int = 50
    """初期位置 X（リージョン左端からのオフセット）。"""

    gpu_default_y_offset: int = 50
    """初期位置 Y（リージョン上端からのオフセット）。"""

    gpu_close_on: ClassVar[set[str]] = {'ESC'}
    """パネルを閉じるイベントタイプのセット。
    空セットなら閉じるボタンまたはトグル操作のみで閉じる。
    例: {'ESC'}, {'ESC', 'RIGHTMOUSE'}, set()
    """

    gpu_debug_hittest: bool = False
    """HitTest のデバッグ表示を有効化するか。"""

    gpu_debug_hittest_labels: bool = False
    """HitRect に紐づくラベルを描画するか。"""

    gpu_debug_hittest_toggle_key: str = 'D'
    """HitTest デバッグの切替キー。"""

    # ═══════════════════════════════════════════════════════════════════════════
    # 内部状態（Mixin で管理）
    # ═══════════════════════════════════════════════════════════════════════════

    _manager: Optional['GPUPanelManager'] = None
    _layout: Optional['GPULayout'] = None
    _should_close: bool = False
    _panel_x: Optional[float] = None
    _panel_y: Optional[float] = None
    _debug_hittest: bool = False

    # パネル内で消費すべきマウスイベント
    _CONSUME_EVENTS: ClassVar[set[str]] = {
        'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE',
        'WHEELUPMOUSE', 'WHEELDOWNMOUSE',
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # 抽象メソッド（サブクラスでオーバーライド）
    # ═══════════════════════════════════════════════════════════════════════════

    def draw_panel(self, layout: 'GPULayout', context: 'Context') -> None:
        """パネルの内容を描画（必須）

        Args:
            layout: GPULayout インスタンス。UILayout 風の API を持つ。
            context: bpy.context

        Example:
            def draw_panel(self, layout, context):
                layout.label(text="Settings")
                layout.prop(context.scene.render, "resolution_percentage")
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════════
    # 実装メソッド（Operator から呼び出される）
    # ═══════════════════════════════════════════════════════════════════════════

    def _modal_impl(self, context: 'Context', event: 'Event') -> set[str]:
        """modal() の実装

        Args:
            context: Blender コンテキスト
            event: Blender イベント

        Returns:
            Operator の戻り値（{'RUNNING_MODAL'}, {'PASS_THROUGH'}, {'CANCELLED'}）
        """
        context.area.tag_redraw()

        # クローズ要求チェック
        if self._should_close:
            self._cancel_impl(context)
            return {'CANCELLED'}

        # gpu_close_on で指定されたイベントで閉じる
        if event.type in self.gpu_close_on and event.value == 'PRESS':
            self._cancel_impl(context)
            return {'CANCELLED'}

        if (self.gpu_debug_hittest_toggle_key and
                event.type == self.gpu_debug_hittest_toggle_key and
                event.value == 'PRESS'):
            # NOTE: #117 global debug toggle is deferred to avoid premature design coupling.
            self._debug_hittest = not self._debug_hittest
            return {'RUNNING_MODAL'}

        # レイアウト再構築
        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        # prop() ウィジェットの値を RNA から同期
        if self._layout:
            self._layout.sync_props()

        # イベント処理
        if self._manager:
            handled = self._manager.handle_event(event, context, region)
            if self._layout:
                self._panel_x = self._layout.x
                self._panel_y = self._layout.y
            if handled:
                return {'RUNNING_MODAL'}

            # パネル内でのマウスイベントは消費
            if event.type in self._CONSUME_EVENTS:
                if self._manager.contains_point(event.mouse_region_x, event.mouse_region_y):
                    return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def _invoke_impl(self, context: 'Context', event: 'Event') -> set[str]:
        """invoke() の実装

        Args:
            context: Blender コンテキスト
            event: Blender イベント

        Returns:
            Operator の戻り値（{'RUNNING_MODAL'}, {'CANCELLED'}）
        """
        # 遅延インポート（循環参照回避）
        from .panel_manager import GPUPanelManager

        # エリアタイプチェック
        if context.area.type != self.gpu_space_type:
            self.report({'WARNING'}, f"{self.gpu_space_type} で実行してください")
            return {'CANCELLED'}

        # 重複チェック → トグル動作
        if GPUPanelManager.is_active(self.gpu_panel_uid):
            GPUPanelManager.close_by_uid(self.gpu_panel_uid, context)
            return {'CANCELLED'}

        # 初期化
        self._should_close = False
        self._layout = None
        self._manager = None
        self._debug_hittest = self.gpu_debug_hittest
        self._restore_position()  # 永続化された位置を復元

        # レイアウト構築
        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout is None:
            self.report({'ERROR'}, "レイアウトの作成に失敗しました")
            return {'CANCELLED'}

        # マネージャー作成
        self._manager = GPUPanelManager(self.gpu_panel_uid, self._layout)
        if not self._manager.open(context, self._draw_callback, self.gpu_space_type):
            self.report({'ERROR'}, "パネルを開けませんでした")
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _cancel_impl(self, context: 'Context') -> None:
        """cancel() の実装

        Args:
            context: Blender コンテキスト
        """
        self._save_position()  # 位置を永続化

        if self._manager:
            self._manager.close(context)
            self._manager = None

        self._layout = None

    # ═══════════════════════════════════════════════════════════════════════════
    # プライベートヘルパー
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _get_window_region(context: 'Context') -> Optional['Region']:
        """WINDOW タイプのリージョンを取得

        Args:
            context: Blender コンテキスト

        Returns:
            WINDOW リージョン、または None（見つからない場合）

        Note:
            context.region は modal() 呼び出し時に HEADER など別のリージョンを
            指している場合があるため、明示的に WINDOW リージョンを検索する。
        """
        region = context.region
        if region and region.type == 'WINDOW':
            return region
        area = context.area
        if area:
            for r in area.regions:
                if r.type == 'WINDOW':
                    return r
        return None

    def _rebuild_layout(self, context: 'Context', region: Optional['Region'] = None) -> None:
        """GPULayout を再構築し、draw_panel() を呼び出す

        Args:
            context: Blender コンテキスト
            region: WINDOW リージョン（None の場合は自動取得）

        Side Effects:
            - self._layout を新規作成または更新
            - self._layout.x/y を self._panel_x/_panel_y から復元
            - self.draw_panel() を呼び出してウィジェットを追加
            - self._layout.build() を呼び出してレイアウト計算

        Note:
            毎フレーム呼ばれる。パネル内容が動的に変化する場合に対応。
        """
        # 遅延インポート（循環参照回避）
        from .layout import GPULayout
        from .style import GPULayoutStyle

        region = region or self._get_window_region(context)
        if region is None:
            return

        # デフォルト位置の計算
        if self._panel_x is None:
            self._panel_x = self.gpu_default_x
        if self._panel_y is None:
            self._panel_y = region.height - self.gpu_default_y_offset

        if self._layout is None:
            # 新規作成
            style = GPULayoutStyle.from_blender_theme(self.gpu_style)
            scaled_width = style.ui_scale(self.gpu_width)
            layout = GPULayout(
                x=self._panel_x,
                y=self._panel_y,
                width=scaled_width,
                style=style
            )
            layout._draw_background = True
            layout._draw_outline = True

            # タイトルバー
            if self.gpu_title:
                def request_close():
                    self._should_close = True

                layout.set_title_bar(
                    title=self.gpu_title,
                    show_close=self.gpu_show_close,
                    on_close=request_close
                )

            # パネル設定
            layout.set_panel_config(
                uid=self.gpu_panel_uid,
                resizable=self.gpu_resizable
            )

            # リージョン境界クランプ
            layout.set_region_bounds(region.width, region.height)

            # サブクラスのコンテンツ描画
            self.draw_panel(layout, context)

            self._layout = layout
        else:
            # 位置更新
            self._layout.x = self._panel_x
            self._layout.y = self._panel_y
            self._layout.set_region_bounds(region.width, region.height)

        # クランプ後の位置を保持
        self._panel_x = self._layout.x
        self._panel_y = self._layout.y

    def _draw_callback(self, manager: 'GPUPanelManager', context: 'Context') -> None:
        """GPU 描画コールバック（SpaceView3D.draw_handler で呼ばれる）

        Args:
            manager: GPUPanelManager インスタンス
            context: 描画時のコンテキスト（modal 時と異なる場合あり）

        Side Effects:
            - self._layout.draw() を呼び出してパネルを描画

        Note:
            draw_handler_add() に渡されるコールバック。
            manager.should_draw(context) で描画判定を行う。
        """
        # 対象リージョン以外では描画しない（マルチビューポート対応）
        if not manager.should_draw(context):
            return

        try:
            region = self._get_window_region(context)
            self._rebuild_layout(context, region)

            if self._layout is None:
                return

            # メインレイアウト描画
            self._layout.update_and_draw()
            if self._debug_hittest:
                self._debug_draw_hit_test()

        except Exception as e:
            import traceback
            print(f"GPUPanelMixin draw error: {e}")
            traceback.print_exc()

    def _debug_draw_hit_test(self) -> None:
        layout = self._layout
        if not layout:
            return
        self._debug_draw_layout_hits(layout)

    def _debug_draw_layout_hits(self, layout: 'GPULayout') -> None:
        hit_manager = layout.hit_manager
        if hit_manager:
            hit_manager.debug_draw()
            if self.gpu_debug_hittest_labels:
                from .drawing import BLFDrawing
                from .style import GPULayoutStyle

                debug_style = GPULayoutStyle.from_blender_theme('TOOLTIP')
                for rect in hit_manager._rects:
                    label = rect.tag
                    if not label and rect.layout_key:
                        if rect.layout_key.explicit_key:
                            label = f"{rect.layout_key.layout_path}:{rect.layout_key.explicit_key}"
                        else:
                            label = rect.layout_key.layout_path
                    if not label and rect.item is not None:
                        label = getattr(rect.item, 'text', '') or ""
                    if not label:
                        continue
                    BLFDrawing.draw_text(
                        rect.x + 2, rect.y - 2,
                        label, debug_style.text_color, 11
                    )

        from .layout import GPULayout
        for element in layout._elements:
            if isinstance(element, GPULayout):
                self._debug_draw_layout_hits(element)

    def _restore_position(self) -> None:
        """永続化された位置を self._panel_x/y に復元"""
        from .state import get_panel_state

        state = get_panel_state(self.gpu_panel_uid)
        if state.has_position:
            self._panel_x = state.x
            self._panel_y = state.y
        # else: デフォルト位置を使用（gpu_default_x, gpu_default_y_offset）

    def _save_position(self) -> None:
        """現在の位置を永続化ストレージに保存"""
        from .state import GPUPanelState, set_panel_state

        if self._panel_x is not None and self._panel_y is not None:
            state = GPUPanelState(x=self._panel_x, y=self._panel_y)
            set_panel_state(self.gpu_panel_uid, state)

    # ═══════════════════════════════════════════════════════════════════════════
    # クラスメソッド
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def is_open(cls) -> bool:
        """このパネルが現在開いているかを返す

        Returns:
            パネルが開いていれば True
        """
        from .panel_manager import GPUPanelManager
        return GPUPanelManager.is_active(cls.gpu_panel_uid)
