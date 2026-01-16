"""
GPULayout テストスクリプト

PME 開発中に自動で読み込まれます。
3D Viewport で F3 → "Test GPULayout" を実行してください。

使い方:
1. 3D Viewport で F3 キーを押してオペレーター検索
2. "Test GPULayout" を実行
3. 3D Viewport の左上にサンプル UI が表示される
4. 終了するには 3D Viewport で ESC キーを押す
"""

import bpy
from bpy.types import Operator

from . import (
    GPULayout, GPULayoutStyle, GPUTooltip, GPUDrawing, BLFDrawing, IconDrawing,
    Alignment, GPUPanelManager
)
from .items import SliderItem


class TEST_OT_gpu_layout(Operator):
    """GPULayout テストオペレーター"""
    bl_idname = "test.gpu_layout"
    bl_label = "Test GPULayout"
    bl_options = {'REGISTER'}

    _handler = None
    _timer = None
    _target_region_pointer: int = 0  # 描画対象リージョンのポインタ

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "3D Viewport で実行してください")
            return {'CANCELLED'}

        # 呼び出し時のリージョンを記憶（他のリージョンでは描画しない）
        self._target_region_pointer = context.region.as_pointer()

        args = (self, context)
        self._handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_PIXEL'
        )

        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)

        self.report({'INFO'}, "GPULayout テスト開始 - ESC で終了")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._handler:
            bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
            self._handler = None

        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        self.report({'INFO'}, "GPULayout テスト終了")

    @staticmethod
    def draw_callback(self, context):
        """描画コールバック"""
        # 対象リージョン以外では描画しない（マルチビューポート対応）
        if context.region.as_pointer() != self._target_region_pointer:
            return

        try:
            margin = 20
            col1_x = 50
            col2_x = 380
            col3_x = 680
            col4_x = 940  # 追加: ツールチップ列
            start_y = context.region.height - 50

            # ═══════════════════════════════════════════════════════════════
            # Column 1: パネルスタイル（REGULAR）
            # ═══════════════════════════════════════════════════════════════
            y = start_y

            # パネルヘッダー風
            panel_style = GPULayoutStyle.from_blender_theme('REGULAR')

            # ドロップシャドウ付きパネル - まずレイアウトを構築して高さを取得
            panel = GPULayout(x=col1_x, y=y, width=300, style=panel_style)
            panel._draw_background = True
            panel._draw_outline = True

            panel.label(text="Panel Style (REGULAR)", icon='PROPERTIES')
            panel.separator()

            # オブジェクト情報
            if context.object:
                panel.prop_display(context.object, "name", text="Object")
                panel.prop_display(context.object, "type", text="Type")
                loc = context.object.location
                panel.label(text=f"Location: ({loc.x:.2f}, {loc.y:.2f}, {loc.z:.2f})")
            else:
                panel.label(text="No active object")

            panel.separator()
            panel.operator(text="Sample Button")

            # レイアウト計算と描画（影は draw() 内で自動描画）
            panel.layout()
            panel.draw()
            y -= panel.calc_height() + margin + 20

            # ───────────────────────────────────────────────────────────────
            # メニュースタイル（MENU）
            # ───────────────────────────────────────────────────────────────
            menu_style = GPULayoutStyle.from_blender_theme('MENU')

            menu = GPULayout(x=col1_x, y=y, width=280, style=menu_style)
            menu._draw_background = True
            menu._draw_outline = True

            menu.label(text="Menu Style (MENU)")
            menu.separator(factor=0.5)

            # メニューアイテム風
            menu.label(text="Add Cube", icon='MESH_CUBE')
            menu.label(text="Add Sphere", icon='MESH_UVSPHERE')
            menu.label(text="Add Cylinder", icon='MESH_CYLINDER')
            menu.separator(factor=0.5)
            menu.label(text="Delete", icon='X')

            # レイアウト計算と描画（影は draw() 内で自動描画）
            menu.layout()
            menu.draw()
            y -= menu.calc_height() + margin + 20

            # ───────────────────────────────────────────────────────────────
            # 選択状態のカラーデモ
            # ───────────────────────────────────────────────────────────────
            sel_style = GPULayoutStyle.from_blender_theme('MENU_ITEM')
            sel_border_radius = sel_style.scaled_border_radius()
            sel_item_height = sel_style.scaled_item_height()
            sel_text_size = sel_style.scaled_text_size()

            # 通常状態
            GPUDrawing.draw_rounded_rect(
                col1_x, y, 280, sel_item_height,
                sel_border_radius, sel_style.bg_color
            )
            BLFDrawing.draw_text(
                col1_x + 10, y - sel_item_height + 8, "Normal Item",
                sel_style.text_color, sel_text_size
            )
            y -= sel_item_height + 4

            # 選択状態
            GPUDrawing.draw_rounded_rect(
                col1_x, y, 280, sel_item_height,
                sel_border_radius, sel_style.bg_color_sel
            )
            BLFDrawing.draw_text(
                col1_x + 10, y - sel_item_height + 8, "Selected Item",
                sel_style.text_color_sel, sel_text_size
            )
            y -= sel_item_height + 4

            # アイテム色
            GPUDrawing.draw_rounded_rect(
                col1_x, y, 280, sel_item_height,
                sel_border_radius, sel_style.item_color
            )
            BLFDrawing.draw_text(
                col1_x + 10, y - sel_item_height + 8, "Item Color",
                sel_style.text_color, sel_text_size
            )

            # ═══════════════════════════════════════════════════════════════
            # Column 2: ライン描画テスト
            # ═══════════════════════════════════════════════════════════════
            y = start_y

            line_demo = GPULayout(x=col2_x, y=y, width=260, style=panel_style)
            line_demo._draw_background = True
            line_demo._draw_outline = True
            line_demo.label(text="Line Drawing Comparison")
            line_demo.update_and_draw()

            y -= line_demo.calc_height() + 10

            # ライン太さ比較
            line_widths = [1.0, 2.0, 3.0, 4.0]
            line_color = panel_style.text_color

            for i, w in enumerate(line_widths):
                lx = col2_x + 10
                ly = y - i * 40

                # ラベル
                BLFDrawing.draw_text(lx, ly - 12, f"width={w}:", line_color, 11)

                # 通常の線（先端が平ら）
                BLFDrawing.draw_text(lx, ly - 28, "Normal:", (0.7, 0.7, 0.7, 1.0), 10)
                GPUDrawing.draw_line(lx + 60, ly - 22, lx + 140, ly - 22, line_color, w)

                # 丸い線
                BLFDrawing.draw_text(lx + 150, ly - 28, "Rounded:", (0.7, 0.7, 0.7, 1.0), 10)
                GPUDrawing.draw_rounded_line(lx + 210, ly - 22, lx + 290, ly - 22, line_color, w)

            y -= len(line_widths) * 40 + margin

            # ───────────────────────────────────────────────────────────────
            # ドロップシャドウデモ
            # ───────────────────────────────────────────────────────────────
            shadow_demo = GPULayout(x=col2_x, y=y, width=260, style=panel_style)
            shadow_demo._draw_background = True
            shadow_demo._draw_outline = True
            shadow_demo.label(text="Drop Shadow Demo")
            shadow_demo.update_and_draw()

            y -= shadow_demo.calc_height() + 30

            shadow_colors = [
                ((0.0, 0.0, 0.0, 0.5), "Black"),
                ((0.0, 0.2, 0.5, 0.4), "Blue"),
                ((0.5, 0.2, 0.0, 0.4), "Orange"),
            ]

            for i, (color, name) in enumerate(shadow_colors):
                bx = col2_x + i * 85 + 10
                by = y

                # シャドウ
                GPUDrawing.draw_drop_shadow(bx, by, 70, 50, 6, color, (4, -4), 8)

                # ボックス
                GPUDrawing.draw_rounded_rect(bx, by, 70, 50, 6, panel_style.bg_color)
                GPUDrawing.draw_rounded_rect_outline(bx, by, 70, 50, 6, panel_style.outline_color)
                BLFDrawing.draw_text(bx + 8, by - 30, name, panel_style.text_color, 10)

            y -= 80

            # ═══════════════════════════════════════════════════════════════
            # Column 3: スタイルバリエーション
            # ═══════════════════════════════════════════════════════════════
            y = start_y

            styles = ['MENU', 'PIE_MENU', 'PANEL', 'BOX', 'TOOL', 'TOGGLE']

            for style_name in styles:
                style = GPULayoutStyle.from_blender_theme(style_name)

                demo = GPULayout(x=col3_x, y=y, width=220, style=style)
                demo._draw_background = True
                demo._draw_outline = True

                demo.label(text=f"Style: {style_name}")
                demo.label(text=f"roundness: {style.roundness:.2f}")

                # レイアウト計算と描画（影は draw() 内で自動描画）
                demo.layout()
                demo.draw()
                y -= demo.calc_height() + margin + 10

            # ───────────────────────────────────────────────────────────────
            # roundness テスト
            # ───────────────────────────────────────────────────────────────
            y -= 10
            BLFDrawing.draw_text(col3_x, y - 12, "Roundness Test:", panel_style.text_color, 12)
            y -= 30

            for roundness in [0.0, 0.25, 0.5, 0.75, 1.0]:
                radius = int(roundness * 10)
                GPUDrawing.draw_rounded_rect(
                    col3_x, y, 40, 30,
                    radius, panel_style.item_color
                )
                BLFDrawing.draw_text(
                    col3_x + 50, y - 20,
                    f"r={roundness:.2f}",
                    panel_style.text_color_secondary, 10
                )
                y -= 40

            # ═══════════════════════════════════════════════════════════════
            # Column 4: ツールチップスタイル（TOOLTIP）
            # ═══════════════════════════════════════════════════════════════
            y = start_y

            # ツールチップヘッダー
            BLFDrawing.draw_text(col4_x, y - 12, "Tooltip Style", panel_style.text_color, 14)
            y -= 40

            # GPUTooltip を使用したサンプル
            tooltip = GPUTooltip(max_width=280)
            tooltip.title("Add Cube")
            tooltip.description("シーンに立方体プリミティブを追加します。デフォルトでは 3D カーソル位置に配置されます。")
            tooltip.shortcut("Shift + A > Mesh > Cube")
            tooltip.python("bpy.ops.mesh.primitive_cube_add()")
            tooltip_height = tooltip.draw(col4_x, y)
            y -= tooltip_height + margin

            # シンプルなツールチップ
            tooltip2 = GPUTooltip(max_width=250)
            tooltip2.title("Simple Tooltip")
            tooltip2.description("これは短い説明文のサンプルです。")
            tooltip2_height = tooltip2.draw(col4_x, y)
            y -= tooltip2_height + margin

            # TOOLTIP スタイルの直接使用例
            tooltip_style = GPULayoutStyle.from_blender_theme('TOOLTIP')
            tip_panel = GPULayout(x=col4_x, y=y, width=260, style=tooltip_style)
            tip_panel._draw_background = True
            tip_panel._draw_outline = True

            tip_panel.label(text="Direct TOOLTIP Style")
            tip_panel.separator(factor=0.5)
            tip_panel.label(text="Tooltip uses wcol_tooltip")
            tip_panel.label(text=f"roundness: {tooltip_style.roundness:.2f}")
            tip_panel.label(text=f"border_radius: {tooltip_style.border_radius}")

            # レイアウト計算と描画（影は draw() 内で自動描画）
            tip_panel.layout()
            tip_panel.draw()

        except Exception as e:
            import traceback
            print(f"Draw error: {e}")
            traceback.print_exc()


class TEST_OT_gpu_interactive(Operator):
    """GPULayout インタラクティブテスト"""
    bl_idname = "test.gpu_interactive"
    bl_label = "Test GPU Interactive"
    bl_options = {'REGISTER'}

    # パネルの uid（重複チェックに使用）
    PANEL_UID = "test_interactive_panel"

    # インスタンス変数（オペレーター実行ごとに初期化）
    _manager: GPUPanelManager = None
    _layout: GPULayout = None
    _click_label = None
    _action_label = None
    _click_count: int = 0
    _last_action: str = ""
    _debug_mode: bool = True
    _should_close: bool = False  # クローズボタンで閉じるフラグ
    _panel_x: float | None = None
    _panel_y: float | None = None
    # スライダーデモ用
    _slider_value: float = 0.5
    _slider_label = None
    _slider_item: SliderItem = None
    # 数値フィールドデモ用
    _number_value: float = 10.0
    _number_label = None
    _number_item = None
    # チェックボックス/トグルデモ用
    _checkbox_value: bool = True
    _toggle_value: bool = False
    _checkbox_item = None
    _toggle_item = None

    # パネル内で消費すべきマウスイベント
    _CONSUME_EVENTS = {
        'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE',
        'WHEELUPMOUSE', 'WHEELDOWNMOUSE',
    }

    def modal(self, context, event):
        context.area.tag_redraw()

        # クローズボタンまたは ESC で終了
        if self._should_close or event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        # D キーでデバッグモード切り替え
        if event.type == 'D' and event.value == 'PRESS':
            self._debug_mode = not self._debug_mode
            return {'RUNNING_MODAL'}

        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        # イベント処理は manager 経由
        if self._manager:
            handled = self._manager.handle_event(event, context)
            if self._layout:
                self._panel_x = self._layout.x
                self._panel_y = self._layout.y
            if handled:
                return {'RUNNING_MODAL'}

            # パネル内でのマウスイベントは消費（View3D への貫通を防止）
            if event.type in self._CONSUME_EVENTS:
                if self._manager.contains_point(event.mouse_region_x, event.mouse_region_y):
                    return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "3D Viewport で実行してください")
            return {'CANCELLED'}

        # 重複チェック: 同じパネルが既に開いていれば何もしない
        if GPUPanelManager.is_active(self.PANEL_UID):
            self.report({'INFO'}, "パネルは既に開いています")
            return {'CANCELLED'}

        # インスタンス変数の初期化
        self._click_count = 0
        self._last_action = "Ready"
        self._debug_mode = True
        self._should_close = False
        self._layout = None
        self._manager = None
        self._click_label = None
        self._action_label = None
        self._panel_x = None
        self._panel_y = None
        self._slider_value = 0.5
        self._slider_label = None
        self._slider_item = None
        self._number_value = 10.0
        self._number_label = None
        self._number_item = None
        self._checkbox_value = True
        self._toggle_value = False
        self._checkbox_item = None
        self._toggle_item = None

        # レイアウトを事前構築
        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout is None:
            self.report({'ERROR'}, "レイアウトの作成に失敗しました")
            return {'CANCELLED'}

        # GPUPanelManager を作成してパネルを開く
        self._manager = GPUPanelManager(self.PANEL_UID, self._layout)

        if not self._manager.open(context, self.draw_callback, 'VIEW_3D', timer_interval=0.05):
            self.report({'ERROR'}, "パネルを開けませんでした")
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "インタラクティブテスト開始 - ESC で終了, D でデバッグ表示切替")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        # GPUPanelManager がハンドラとタイマーをクリーンアップ
        if self._manager:
            self._manager.close(context)
            self._manager = None

        self._layout = None
        self.report({'INFO'}, "インタラクティブテスト終了")

    @staticmethod
    def _get_window_region(context):
        region = context.region
        if region and region.type == 'WINDOW':
            return region
        area = context.area
        if area:
            for r in area.regions:
                if r.type == 'WINDOW':
                    return r
        return None

    def _rebuild_layout(self, context, region=None) -> None:
        """レイアウトを再構築"""
        region = region or self._get_window_region(context)
        if region is None:
            return

        style = GPULayoutStyle.from_blender_theme('PANEL')
        x = 50
        y = region.height - 50
        width = 300

        if self._panel_x is None:
            self._panel_x = x
        if self._panel_y is None:
            self._panel_y = y

        if self._layout is None:
            layout = GPULayout(x=self._panel_x, y=self._panel_y, width=width, style=style)
            layout._draw_background = True
            layout._draw_outline = True

            # タイトルバーとクローズボタンを有効化
            # Note: on_close はフラグを立てるだけ。実際の cancel は modal() で処理
            def request_close():
                self._should_close = True

            layout.set_title_bar(
                title="Interactive Test",
                show_close=True,
                on_close=request_close
            )

            # リサイズと位置の永続化を有効化
            layout.set_panel_config(
                uid=self.PANEL_UID,
                resizable=True
            )

            # リージョン境界クランプを有効化
            layout.set_region_bounds(region.width, region.height)

            layout.separator()

            # クリックカウンター
            layout.label(text=f"Click Count: {self._click_count}")
            self._click_label = layout._items[-1]
            layout.label(text=f"Last Action: {self._last_action}")
            self._action_label = layout._items[-1]
            layout.separator()

            # ボタン 1
            def on_click_1():
                self._click_count += 1
                self._last_action = "Button 1 clicked!"

            layout.operator(text="Click Me!", on_click=on_click_1)

            # ボタン 2
            def on_click_2():
                self._click_count += 1
                self._last_action = "Button 2 clicked!"

            layout.operator(text="Me Too!", on_click=on_click_2)

            # ボタン 3 (disabled)
            btn3 = layout.operator(text="Disabled Button")
            btn3.enabled = False

            layout.separator()

            # スライダーセクション
            layout.label(text="Slider Demo (wcol_numslider)")

            # スライダー値の表示
            layout.label(text=f"Value: {self._slider_value:.2f}")
            self._slider_label = layout._items[-1]

            # スライダーコールバック
            def on_slider_change(value: float):
                self._slider_value = value
                self._last_action = f"Slider: {value:.2f}"

            # スライダー追加
            self._slider_item = layout.slider(
                value=self._slider_value,
                min_val=0.0,
                max_val=1.0,
                precision=2,
                text="Opacity",
                on_change=on_slider_change
            )

            # 2つ目のスライダー（範囲指定）
            layout.slider(
                value=50,
                min_val=0,
                max_val=100,
                precision=0,
                text="Size"
            )

            layout.separator()

            # ── Number フィールドデモ ──
            layout.label(text="Number Fields:")

            # 数値フィールド値の表示
            layout.label(text=f"Number: {self._number_value:.1f}")
            self._number_label = layout._items[-1]

            # 数値フィールドコールバック
            def on_number_change(value: float):
                self._number_value = value
                self._last_action = f"Number: {value:.1f}"

            # 数値フィールド追加（ドラッグで値変更）
            self._number_item = layout.number(
                value=self._number_value,
                min_val=0.0,
                max_val=100.0,
                step=0.1,
                precision=1,
                text="Count",
                on_change=on_number_change
            )

            # 増減ボタン付き数値フィールド
            layout.number(
                value=5,
                min_val=0,
                max_val=20,
                step=0.05,
                precision=0,
                text="Level",
                show_buttons=True
            )

            layout.separator()

            # ── Checkbox / Toggle デモ ──
            layout.label(text="Checkbox & Toggle:")

            # チェックボックスコールバック
            def on_checkbox_toggle(value: bool):
                self._checkbox_value = value
                self._last_action = f"Checkbox: {value}"

            # チェックボックス追加
            self._checkbox_item = layout.checkbox(
                text="Enable Feature",
                value=self._checkbox_value,
                on_toggle=on_checkbox_toggle
            )

            # もう1つのチェックボックス（無効状態）
            disabled_checkbox = layout.checkbox(
                text="Disabled Option",
                value=False
            )
            disabled_checkbox.enabled = False

            # トグルボタンコールバック
            def on_toggle_change(value: bool):
                self._toggle_value = value
                self._last_action = f"Toggle: {value}"

            # トグルボタン追加
            self._toggle_item = layout.toggle(
                text="Preview Mode",
                value=self._toggle_value,
                on_toggle=on_toggle_change
            )

            # もう1つのトグル
            layout.toggle(
                text="Auto Save",
                value=True
            )

            layout.separator()

            # ── Color デモ ──
            layout.label(text="Color Swatches:")

            # 基本的なカラー（不透明）
            row = layout.row()
            row.color(color=(1.0, 0.2, 0.2, 1.0))  # 赤
            row.color(color=(0.2, 1.0, 0.2, 1.0))  # 緑
            row.color(color=(0.2, 0.4, 1.0, 1.0))  # 青

            # ラベル付きカラー
            layout.color(color=(1.0, 0.8, 0.2, 1.0), text="Diffuse Color")

            # 半透明カラー（チェッカーパターン表示）
            row2 = layout.row()
            row2.color(color=(1.0, 0.0, 0.0, 0.5), text="50%")
            row2.color(color=(0.0, 0.5, 1.0, 0.25), text="25%")

            # クリックコールバック付き
            def on_color_click():
                self._last_action = "Color clicked!"
            layout.color(color=(0.8, 0.3, 0.9, 1.0), text="Click me!", on_click=on_color_click)

            # 無効状態
            disabled_color = layout.color(color=(0.5, 0.5, 0.5, 1.0), text="Disabled")
            disabled_color.enabled = False

            layout.separator()
            layout.label(text="Press D to toggle debug view")
            layout.label(text="Press ESC to exit")

            self._layout = layout
        else:
            self._layout.x = self._panel_x
            self._layout.y = self._panel_y
            # リージョンサイズ変更時のクランプ対応
            self._layout.set_region_bounds(region.width, region.height)

        # クランプ後の位置を保持（次のフレームで使用）
        self._panel_x = self._layout.x
        self._panel_y = self._layout.y

        if self._click_label:
            self._click_label.text = f"Click Count: {self._click_count}"
        if self._action_label:
            self._action_label.text = f"Last Action: {self._last_action}"
        if self._slider_label:
            self._slider_label.text = f"Value: {self._slider_value:.2f}"
        if self._number_label:
            self._number_label.text = f"Number: {self._number_value:.1f}"

    def draw_callback(self, manager: GPUPanelManager, context):
        """描画コールバック（GPUPanelManager から呼び出される）"""
        # 対象リージョン以外では描画しない（マルチビューポート対応）
        if not manager.should_draw(context):
            return

        try:
            region = self._get_window_region(context)
            self._rebuild_layout(context, region)

            if self._layout is None:
                return

            # メインレイアウト描画（layout() + draw()）
            # Note: 影描画は GPULayout.draw() 内で自動的に行われる
            self._layout.update_and_draw()

            # デバッグ表示
            if self._debug_mode and self._layout.hit_manager:
                hit_manager = self._layout.hit_manager
                hit_manager.debug_draw()

                # 状態表示
                state = hit_manager.state
                debug_y = self._layout.y - self._layout.calc_height() - 30
                debug_style = GPULayoutStyle.from_blender_theme('TOOLTIP')

                info_lines = [
                    f"Mouse: ({state.mouse_x:.0f}, {state.mouse_y:.0f})",
                    f"Hovered: {hit_manager.hovered.tag if hit_manager.hovered else 'None'}",
                    f"Pressed: {hit_manager.pressed.tag if hit_manager.pressed else 'None'}",
                    f"HitRects: {len(hit_manager._rects)}",
                ]

                # 各 HitRect の座標も表示
                for i, rect in enumerate(hit_manager._rects):
                    info_lines.append(
                        f"  [{i}] x={rect.x:.0f} y={rect.y:.0f} w={rect.width:.0f} h={rect.height:.0f}"
                    )

                for i, line in enumerate(info_lines):
                    BLFDrawing.draw_text(
                        60, debug_y - i * 18, line,
                        debug_style.text_color, 11
                    )

        except Exception as e:
            import traceback
            print(f"Draw error: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass

    register()
    # bpy.ops.test.gpu_layout('INVOKE_DEFAULT')
    bpy.ops.test.gpu_interactive('INVOKE_DEFAULT')
