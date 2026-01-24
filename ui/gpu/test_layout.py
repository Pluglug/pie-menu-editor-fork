# pyright: reportInvalidTypeForm=false
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
from .context import ContextTracker


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
            # パネルシャドウデモ（Blender スタイル: 3辺シャドウ）
            # ───────────────────────────────────────────────────────────────
            shadow_demo = GPULayout(x=col2_x, y=y, width=260, style=panel_style)
            shadow_demo._draw_background = True
            shadow_demo._draw_outline = True
            shadow_demo.label(text="Panel Shadow Demo (3-sided)")
            shadow_demo.update_and_draw()

            y -= shadow_demo.calc_height() + 30

            # 異なる shadow_width でデモ
            shadow_widths = [
                (4, "Width: 4"),
                (6, "Width: 6"),
                (10, "Width: 10"),
            ]

            for i, (shadow_width, name) in enumerate(shadow_widths):
                bx = col2_x + i * 85 + 10
                by = y

                # パネルシャドウ（上辺なし、3辺のみ）
                GPUDrawing.draw_panel_shadow(bx, by, 70, 50, 6, shadow_width, 0.2)

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

            # GPUTooltip sample
            tooltip = GPUTooltip(max_width=280)
            tooltip.title("Add Cube")
            tooltip.description("Add a cube primitive to the scene. By default, it is placed at the 3D cursor location.")
            tooltip.shortcut("Shift + A > Mesh > Cube")
            tooltip.python("bpy.ops.mesh.primitive_cube_add()")
            tooltip_height = tooltip.draw(col4_x, y)
            y -= tooltip_height + margin

            # Simple tooltip
            tooltip2 = GPUTooltip(max_width=250)
            tooltip2.title("Simple Tooltip")
            tooltip2.description("This is a short description sample.")
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
    # ラジオグループデモ用
    _radio_value: str = "OBJECT"
    _radio_item = None

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

        # prop() で作成されたウィジェットの値を RNA から同期
        if self._layout:
            self._layout.sync_props()

        # イベント処理は manager 経由
        if self._manager:
            handled = self._manager.handle_event(event, context, region)
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
        self._radio_value = "OBJECT"
        self._radio_item = None

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
            self._click_label = layout.label(text=f"Click Count: {self._click_count}")
            self._action_label = layout.label(text=f"Last Action: {self._last_action}")
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
            self._slider_label = layout.label(text=f"Value: {self._slider_value:.2f}")

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
            self._number_label = layout.label(text=f"Number: {self._number_value:.1f}")

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

            # ── Color デモ (Blender スタイル: 左=RGB、右=チェッカー+RGBA) ──
            layout.label(text="Color (Blender Style):")

            # 不透明カラー（ラベルなし - カラーバーのみ）
            layout.color(color=(1.0, 0.5, 0.2, 1.0))

            # ラベル付きカラー（use_property_split=True 風）
            layout.color(color=(0.8, 0.2, 0.9, 1.0), text="Diffuse")

            # 半透明カラー（右側にチェッカーパターン表示）
            layout.color(color=(0.2, 0.6, 1.0, 0.5), text="Alpha 50%")
            layout.color(color=(1.0, 0.8, 0.0, 0.25), text="Alpha 25%")

            # クリックコールバック付き
            def on_color_click():
                self._last_action = "Color clicked!"
            layout.color(color=(0.3, 0.9, 0.5, 1.0), text="Click me", on_click=on_color_click)

            # 無効状態
            disabled_color = layout.color(color=(0.5, 0.5, 0.5, 0.8), text="Disabled")
            disabled_color.enabled = False

            # TODO: row() 内での複数 ColorItem は別 Issue で対応
            # row = layout.row()
            # row.color(color=(1.0, 0.2, 0.2, 1.0))
            # row.color(color=(0.2, 1.0, 0.2, 1.0))

            layout.separator()

            # ── Radio Group デモ (Enum expanded スタイル) ──
            layout.label(text="Radio Group (Enum):")

            # ラジオグループコールバック
            def on_radio_change(value: str):
                self._radio_value = value
                self._last_action = f"Radio: {value}"

            # 基本的なラジオグループ
            self._radio_item = layout.radio_group(
                options=[
                    ("OBJECT", "Object"),
                    ("EDIT", "Edit"),
                    ("SCULPT", "Sculpt"),
                ],
                value=getattr(self, '_radio_value', 'OBJECT'),
                on_change=on_radio_change
            )

            # テキストのみのラジオグループ
            layout.radio_group(
                options=[("A", "Option A"), ("B", "Option B"), ("C", "Option C")],
                value="B"
            )

            # シンプルなラジオグループ（value のみ）
            layout.radio_group(
                options=["Low", "Medium", "High"],
                value="Medium"
            )

            layout.separator()

            # ── layout.prop() デモ (Blender プロパティとの双方向バインディング) ──
            layout.label(text="layout.prop() Demo:")

            # Boolean プロパティ（オブジェクトが存在する場合）
            if context.object:
                # チェックボックス（デフォルト）
                layout.prop(context.object, "hide_viewport")
                # トグルボタン（toggle=1）
                layout.prop(context.object, "hide_render", toggle=1)

            # 数値プロパティ（スライダー）
            layout.prop(context.scene.render, "resolution_percentage", slider=True)

            # Enum プロパティ（展開表示）
            layout.prop(context.scene.render, "engine", expand=True)

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


# ═══════════════════════════════════════════════════════════════════════════════
# Demo 1: Quick Viewport - モデラー向け常時表示パネル（GPUPanelMixin 使用）
# ═══════════════════════════════════════════════════════════════════════════════

from .panel_mixin import GPUPanelMixin


class DEMO_OT_quick_viewport(Operator, GPUPanelMixin):
    """Quick Viewport Settings - GPUPanelMixin デモ（モデラー向け）"""
    bl_idname = "demo.quick_viewport"
    bl_label = "Demo: Quick Viewport"
    bl_options = {'REGISTER'}

    # GPUPanelMixin 設定
    gpu_panel_uid = "demo_quick_viewport"
    gpu_title = "Quick Viewport"
    gpu_width = 220

    def modal(self, context, event):
        return self._modal_impl(context, event)

    def invoke(self, context, event):
        return self._invoke_impl(context, event)

    def cancel(self, context):
        return self._cancel_impl(context)

    def draw_panel(self, layout, context):
        """パネル内容の描画（GPUPanelMixin から呼び出される）"""
        space = context.space_data
        tool_settings = context.scene.tool_settings

        # Viewport Display Section
        layout.label(text="Display")
        layout.prop(space.overlay, "show_overlays", text="Overlays", toggle=1)
        layout.prop(space.overlay, "show_wireframes", text="Wireframes")
        layout.prop(space, "show_gizmo", text="Gizmos")

        layout.separator()

        # Snapping Section
        layout.label(text="Snapping")
        layout.prop(tool_settings, "use_snap", text="Snap", toggle=1)
        layout.prop(tool_settings, "use_proportional_edit", text="Proportional")
        layout.prop(tool_settings, "use_mesh_automerge", text="Auto Merge")


# ═══════════════════════════════════════════════════════════════════════════════
# Demo 2: Quick Render - レンダリスト向け常時表示パネル
# ═══════════════════════════════════════════════════════════════════════════════

class DEMO_OT_quick_render(Operator):
    """Quick Render Settings - 常時表示デモ（レンダリスト向け）"""
    bl_idname = "demo.quick_render"
    bl_label = "Demo: Quick Render"
    bl_options = {'REGISTER'}

    PANEL_UID = "demo_quick_render"

    _manager: GPUPanelManager = None
    _layout: GPULayout = None
    _should_close: bool = False
    _panel_x: float = None
    _panel_y: float = None

    def modal(self, context, event):
        context.area.tag_redraw()

        if self._should_close or event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout:
            self._layout.sync_props()

        if self._manager:
            handled = self._manager.handle_event(event, context, region)
            if self._layout:
                self._panel_x = self._layout.x
                self._panel_y = self._layout.y
            if handled:
                return {'RUNNING_MODAL'}

            if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'}:
                if self._manager.contains_point(event.mouse_region_x, event.mouse_region_y):
                    return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "3D Viewport で実行してください")
            return {'CANCELLED'}

        if GPUPanelManager.is_active(self.PANEL_UID):
            self.report({'INFO'}, "パネルは既に開いています")
            return {'CANCELLED'}

        self._should_close = False
        self._layout = None
        self._manager = None
        self._panel_x = None
        self._panel_y = None

        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout is None:
            self.report({'ERROR'}, "レイアウトの作成に失敗しました")
            return {'CANCELLED'}

        self._manager = GPUPanelManager(self.PANEL_UID, self._layout)
        if not self._manager.open(context, self.draw_callback, 'VIEW_3D', timer_interval=0.05):
            self.report({'ERROR'}, "パネルを開けませんでした")
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._manager:
            self._manager.close(context)
            self._manager = None
        self._layout = None

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

        scene = context.scene
        render = scene.render

        if self._panel_x is None:
            self._panel_x = 50
        if self._panel_y is None:
            self._panel_y = region.height - 50

        if self._layout is None:
            style = GPULayoutStyle.from_blender_theme('PANEL')
            layout = GPULayout(x=self._panel_x, y=self._panel_y, width=240, style=style)
            layout._draw_background = True
            layout._draw_outline = True

            def request_close():
                self._should_close = True

            layout.set_title_bar(
                title="Quick Render",
                show_close=True,
                on_close=request_close
            )
            layout.set_panel_config(uid=self.PANEL_UID, resizable=True)
            layout.set_region_bounds(region.width, region.height)

            # ──────────────────────────────────────────
            # Resolution Section
            # ──────────────────────────────────────────
            layout.label(text="Resolution")

            # 解像度%（スライダー）
            layout.prop(render, "resolution_percentage", slider=True)

            # 透過背景
            layout.prop(render, "film_transparent", text="Transparent BG", toggle=1)

            layout.separator()

            # ──────────────────────────────────────────
            # Frame Range Section
            # ──────────────────────────────────────────
            layout.label(text="Frame Range")

            # フレーム範囲
            layout.prop(scene, "frame_start", text="Start")
            layout.prop(scene, "frame_end", text="End")

            # FPS
            layout.prop(render, "fps", text="FPS")

            # layout.separator()
            # layout.label(text="ESC to close", icon='INFO')

            self._layout = layout
        else:
            self._layout.x = self._panel_x
            self._layout.y = self._panel_y
            self._layout.set_region_bounds(region.width, region.height)

        self._panel_x = self._layout.x
        self._panel_y = self._layout.y

    def draw_callback(self, manager: GPUPanelManager, context):
        if not manager.should_draw(context):
            return
        try:
            region = self._get_window_region(context)
            self._rebuild_layout(context, region)
            if self._layout:
                self._layout.update_and_draw()
        except Exception as e:
            import traceback
            print(f"Draw error: {e}")
            traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
# Demo 3: Operator Props - layout.operator demo
# ---------------------------------------------------------------------------

class DEMO_OT_operator_props(Operator):
    """Demo operator for GPULayout.operator props."""
    bl_idname = "demo.operator_props"
    bl_label = "Demo: Operator Props"
    bl_options = {'REGISTER', 'UNDO'}

    count: bpy.props.IntProperty(name="Count", default=1, min=1, max=10)
    message: bpy.props.StringProperty(name="Message", default="Hello")

    def execute(self, context):
        msg = f"execute: {self.message} (count={self.count})"
        self.report({'INFO'}, msg)
        print(msg)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

# ---------------------------------------------------------------------------
# Demo 4: Selection Tracker - reactive context demo
# ---------------------------------------------------------------------------

class DEMO_OT_selection_tracker(Operator):
    """Selection Tracker - reactive context demo"""
    bl_idname = "demo.selection_tracker"
    bl_label = "Demo: Selection Tracker"
    bl_options = {'REGISTER'}

    PANEL_UID = "demo_selection_tracker"

    _manager: GPUPanelManager = None
    _layout: GPULayout = None
    _should_close: bool = False
    _panel_x: float = None
    _panel_y: float = None
    _context_tracker: ContextTracker = None

    def modal(self, context, event):
        context.area.tag_redraw()

        if self._should_close or event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout:
            self._layout.sync_props()

        if self._manager:
            handled = self._manager.handle_event(event, context, region)
            if self._layout:
                self._panel_x = self._layout.x
                self._panel_y = self._layout.y
            if handled:
                return {'RUNNING_MODAL'}

            if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'}:
                if self._manager.contains_point(event.mouse_region_x, event.mouse_region_y):
                    return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Run in 3D Viewport")
            return {'CANCELLED'}
        if context.object is None:
            self.report({'WARNING'}, "Select an active object first")
            return {'CANCELLED'}
        if context.object.data is None:
            self.report({'WARNING'}, "Select an object with data for C.object.data demo")
            return {'CANCELLED'}

        if GPUPanelManager.is_active(self.PANEL_UID):
            self.report({'INFO'}, "Panel already open")
            return {'CANCELLED'}

        self._should_close = False
        self._layout = None
        self._manager = None
        self._panel_x = None
        self._panel_y = None
        self._context_tracker = None

        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout is None:
            self.report({'ERROR'}, "Failed to build layout")
            return {'CANCELLED'}

        self._manager = GPUPanelManager(self.PANEL_UID, self._layout)
        if not self._manager.open(context, self.draw_callback, 'VIEW_3D', timer_interval=0.05):
            self.report({'ERROR'}, "Failed to open panel")
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._manager:
            self._manager.close(context)
            self._manager = None
        self._layout = None
        self._context_tracker = None

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
        region = region or self._get_window_region(context)
        if region is None:
            return

        if self._panel_x is None:
            self._panel_x = 50
        if self._panel_y is None:
            self._panel_y = region.height - 50

        if self._layout is None:
            if self._context_tracker is None:
                from ...bl_utils import bl_context
                self._context_tracker = ContextTracker(bl_context)

            layout = GPULayout(
                x=self._panel_x,
                y=self._panel_y,
                width=260,
                style=GPULayoutStyle.from_blender_theme('PANEL'),
            )
            layout._draw_background = True
            layout._draw_outline = True
            layout._context_tracker = self._context_tracker

            def request_close():
                self._should_close = True

            layout.set_title_bar(
                title="Selection Tracker",
                show_close=True,
                on_close=request_close,
            )
            layout.set_panel_config(uid=self.PANEL_UID, resizable=True)
            layout.set_region_bounds(region.width, region.height)

            C = self._context_tracker

            layout.label(text="Active Object (C.object)")
            layout.prop(C.object, "hide_viewport", text="Hide Viewport", toggle=1)
            layout.prop(C.object, "hide_render", text="Hide Render", toggle=1)
            layout.prop(C.object, "pass_index", text="Pass Index")

            layout.separator()
            layout.label(text="Object Data (C.object.data)")
            layout.prop(C.object.data, "use_fake_user", text="Use Fake User", toggle=1)

            layout.separator()
            layout.label(text="Operator Demo (layout.operator)")
            layout.operator_context = "INVOKE_REGION_WIN"
            op = layout.operator(
                "demo.operator_props",
                text="Run Operator",
                count=2,
                message="from kwargs",
            )
            op.message = "from attr"

            layout.separator()
            layout.label(text="Delete active object to see widgets disable")

            self._layout = layout
        else:
            self._layout.x = self._panel_x
            self._layout.y = self._panel_y
            self._layout.set_region_bounds(region.width, region.height)

        self._panel_x = self._layout.x
        self._panel_y = self._layout.y

    def draw_callback(self, manager: GPUPanelManager, context):
        if not manager.should_draw(context):
            return
        try:
            region = self._get_window_region(context)
            self._rebuild_layout(context, region)
            if self._layout:
                self._layout.update_and_draw()
        except Exception as e:
            import traceback
            print(f"Draw error: {e}")
            traceback.print_exc()

def _build_layout_structure(layout, *, use_bpy_ops: bool) -> None:
    def add_op(container, text: str) -> None:
        if use_bpy_ops:
            container.operator("mesh.primitive_cube_add", text=text)
        else:
            container.operator(text=text)

    # ═══════════════════════════════════════════════════════════════
    # 1. 基本的な row() テスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="1. row() - Horizontal Layout")

    row = layout.row()
    row.label(text="Left")
    row.label(text="Center")
    row.label(text="Right")

    layout.separator()

    # ─── row(align=True) ───
    layout.label(text="row(align=True)")
    row_aligned = layout.row(align=True)
    add_op(row_aligned, "A")
    add_op(row_aligned, "B")
    add_op(row_aligned, "C")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 2. column() テスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="2. column() - Vertical Layout")

    # row の中に column を入れる
    row = layout.row()

    col1 = row.column()
    col1.label(text="Column 1")
    add_op(col1, "Btn 1-A")
    add_op(col1, "Btn 1-B")

    col2 = row.column(align=True)
    col2.label(text="Column 2 (align=True)")
    add_op(col2, "Btn 2-A")
    add_op(col2, "Btn 2-B")

    col3 = row.column()
    col3.label(text="Column 3")
    add_op(col3, "Btn 3-A")
    add_op(col3, "Btn 3-B")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 3. box() テスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="3. box() - Bordered Container")

    box = layout.box()
    box.label(text="Inside Box")
    add_op(box, "Box Button")

    box_row = box.row()
    box_row.label(text="L")
    box_row.label(text="R")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 4. split() テスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="4. split() - Proportional Split")

    split = layout.split(factor=0.3)
    split.label(text="30%")
    split.label(text="70%")

    split2 = layout.split(factor=0.5)
    add_op(split2, "Half")
    add_op(split2, "Half")

    split3 = layout.split(factor=0.25)
    split3.label(text="25%")
    split3.label(text="37.5%")
    split3.label(text="37.5%")

    split4 = layout.split(factor=0.0)
    split4.label(text="33.3%")
    split4.label(text="33.3%")
    split4.label(text="33.3%")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 5. ネストテスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="5. Nested Layout")

    outer_box = layout.box()
    outer_box.label(text="Outer Box")

    inner_row = outer_box.row()

    inner_box1 = inner_row.box()
    inner_box1.label(text="Inner 1")

    inner_box2 = inner_row.box()
    inner_box2.label(text="Inner 2")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 6. scale 系テスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="6. scale_x / scale_y")

    row = layout.row()
    row.alignment = 'LEFT'
    row.scale_x = 2.0
    add_op(row, "scale_x=2.0 (LEFT)")

    row2 = layout.row()
    row2.scale_y = 1.5
    add_op(row2, "scale_y=1.5")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 7. alignment テスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="7. alignment")

    row = layout.row()
    row.alignment = 'LEFT'
    row.label(text="LEFT align")

    row2 = layout.row()
    row2.alignment = 'CENTER'
    row2.label(text="CENTER align")

    row3 = layout.row()
    row3.alignment = 'RIGHT'
    row3.label(text="RIGHT align")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 8. ui_units_x テスト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="8. ui_units_x")

    row = layout.row()
    sub = row.row()
    sub.ui_units_x = 5
    sub.label(text="Fixed")
    row.label(text="Flex 1")
    row.label(text="Flex 2")

# Demo 5: Layout Structure Test - row, column, box のテスト
# ═══════════════════════════════════════════════════════════════════════════════

class DEMO_OT_layout_structure(Operator, GPUPanelMixin):
    """Layout Structure Test - row, column, box のテスト"""
    bl_idname = "demo.layout_structure"
    bl_label = "Demo: Layout Structure"
    bl_options = {'REGISTER'}

    # GPUPanelMixin 設定
    gpu_panel_uid = "demo_layout_structure"
    gpu_title = "Layout Structure Test"
    gpu_width = 400
    gpu_debug_hittest = True
    gpu_debug_hittest_labels = True

    def modal(self, context, event):
        return self._modal_impl(context, event)

    def invoke(self, context, event):
        return self._invoke_impl(context, event)

    def cancel(self, context):
        return self._cancel_impl(context)

    def draw_panel(self, layout, context):
        """レイアウト構造のテスト"""
        _build_layout_structure(layout, use_bpy_ops=False)


# Demo 5.2: Align Types Test - align=True での角丸挙動確認
# ═══════════════════════════════════════════════════════════════════════════════

class DEMO_OT_layout_align_types(Operator, GPUPanelMixin):
    """Align Types Test - non-alignable items break corners"""
    bl_idname = "demo.layout_align_types"
    bl_label = "Demo: Layout Align Types"
    bl_options = {'REGISTER'}

    gpu_panel_uid = "demo_layout_align_types"
    gpu_title = "Layout Align Types"
    gpu_width = 360

    def modal(self, context, event):
        return self._modal_impl(context, event)

    def invoke(self, context, event):
        return self._invoke_impl(context, event)

    def cancel(self, context):
        return self._cancel_impl(context)

    def draw_panel(self, layout, context):
        layout.label(text="Row align=True (label breaks group)")
        row = layout.row(align=True)
        row.operator(text="A")
        row.operator(text="B")
        row.label(text="Label")
        row.operator(text="C")
        row.operator(text="D")

        layout.separator()

        layout.label(text="Row align=True (checkbox breaks group)")
        row = layout.row(align=True)
        row.operator(text="A")
        row.checkbox(text="Check", value=True)
        row.operator(text="B")

        layout.separator()

        layout.label(text="Column align=True (label breaks group)")
        col = layout.column(align=True)
        col.operator(text="Top")
        col.operator(text="Mid")
        col.label(text="Label")
        col.operator(text="Bottom")


# Demo 5.25: Width-dependent height - wrapped labels in horizontal layouts
# ═══════════════════════════════════════════════════════════════════════════════

class DEMO_OT_layout_wrap_height(Operator, GPUPanelMixin):
    """Width-dependent height test - wrap labels in rows/splits"""
    bl_idname = "demo.layout_wrap_height"
    bl_label = "Demo: Layout Wrap Height"
    bl_options = {'REGISTER'}

    gpu_panel_uid = "demo_layout_wrap_height"
    gpu_title = "Width-Dependent Height"
    gpu_width = 280

    def modal(self, context, event):
        return self._modal_impl(context, event)

    def invoke(self, context, event):
        return self._invoke_impl(context, event)

    def cancel(self, context):
        return self._cancel_impl(context)

    def draw_panel(self, layout, context):
        layout.label(text="Wrapped labels should expand row height.")
        layout.separator()

        layout.label(text="Row (EXPAND):")
        row = layout.row()
        row.label(text="This label should wrap when the row is narrow.", wrap=True)
        row.label(text="Another long label to force wrapping.", wrap=True)

        layout.separator()
        layout.label(text="Split columns:")
        split = layout.split(factor=0.5)
        col1 = split.column()
        col1.label(text="Column A has a long label that wraps.", wrap=True)
        col1.label(text="Below")
        col2 = split.column()
        col2.label(text="Column B also wraps based on width.", wrap=True)
        col2.label(text="Below")


# Demo 5.5: LayoutKey Stability - 順序変更時の hover 維持テスト
# ═══════════════════════════════════════════════════════════════════════════════

class DEMO_OT_layout_key_stability(Operator, GPUPanelMixin):
    """LayoutKey Stability Test - 順序変更時の状態維持"""
    bl_idname = "demo.layout_key_stability"
    bl_label = "Demo: LayoutKey Stability"
    bl_options = {'REGISTER'}

    # GPUPanelMixin 設定
    gpu_panel_uid = "demo_layout_key_stability"
    gpu_title = "LayoutKey Stability"
    gpu_width = 360
    gpu_debug_hittest = True
    gpu_debug_hittest_labels = True

    _order_flipped = False
    _needs_rebuild = False

    def modal(self, context, event):
        return self._modal_impl(context, event)

    def invoke(self, context, event):
        return self._invoke_impl(context, event)

    def cancel(self, context):
        return self._cancel_impl(context)

    def _set_order(self, value: bool) -> None:
        if self._order_flipped == value:
            return
        self._order_flipped = value
        self._needs_rebuild = True

    def _rebuild_layout(self, context, region=None):
        super()._rebuild_layout(context, region)
        if self._layout and self._needs_rebuild:
            self._layout.reset_for_rebuild(preserve_hovered=True)
            self.draw_panel(self._layout, context)
            self._needs_rebuild = False

    def _get_order(self) -> list[str]:
        if self._order_flipped:
            return ["A", "C", "B"]
        return ["A", "B", "C"]

    def draw_panel(self, layout, context):
        layout.label(text="Hover item B, then toggle order.")
        layout.label(text="Keyed row should keep hover on B.")
        layout.separator()

        layout.toggle(
            text="Swap order (B <-> C)",
            value=self._order_flipped,
            key="swap_order",
            on_toggle=self._set_order
        )
        order = ", ".join(self._get_order())
        layout.label(text=f"Order: {order}")
        layout.separator()

        layout.label(text="No keys")
        row = layout.row(align=True)
        for name in self._get_order():
            row.operator(text=name)

        layout.separator()

        layout.label(text="With keys")
        row = layout.row(align=True)
        for name in self._get_order():
            row.operator(text=name, key=f"item_{name}")


# Demo 6: UILayout Reference - Blender 標準 UILayout との比較用
# ═══════════════════════════════════════════════════════════════════════════════

class DEMO_OT_uilayout_reference(Operator):
    """UILayout Reference - Blender 標準 UILayout での同等レイアウト（比較用）"""
    bl_idname = "demo.uilayout_reference"
    bl_label = "Demo: UILayout Reference"
    bl_options = {'REGISTER'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        # popup dialog として表示（幅 400）
        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        """Blender 標準 UILayout でのレイアウト（GPULayout と比較用）"""
        _build_layout_structure(self.layout, use_bpy_ops=True)


# Demo 7: Quick UV - UVエディタ向け常時表示パネル
# ═══════════════════════════════════════════════════════════════════════════════

class DEMO_OT_quick_uv(Operator):
    """Quick UV Settings - 常時表示デモ（UVエディタ向け）"""
    bl_idname = "demo.quick_uv"
    bl_label = "Demo: Quick UV"
    bl_options = {'REGISTER'}

    PANEL_UID = "demo_quick_uv"

    _manager: GPUPanelManager = None
    _layout: GPULayout = None
    _should_close: bool = False
    _panel_x: float = None
    _panel_y: float = None

    def modal(self, context, event):
        context.area.tag_redraw()

        if self._should_close or event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout:
            self._layout.sync_props()

        if self._manager:
            handled = self._manager.handle_event(event, context, region)
            if self._layout:
                self._panel_x = self._layout.x
                self._panel_y = self._layout.y
            if handled:
                return {'RUNNING_MODAL'}

            if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'}:
                if self._manager.contains_point(event.mouse_region_x, event.mouse_region_y):
                    return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'IMAGE_EDITOR':
            self.report({'WARNING'}, "UV/Image Editor で実行してください")
            return {'CANCELLED'}

        if GPUPanelManager.is_active(self.PANEL_UID):
            self.report({'INFO'}, "パネルは既に開いています")
            return {'CANCELLED'}

        self._should_close = False
        self._layout = None
        self._manager = None
        self._panel_x = None
        self._panel_y = None

        region = self._get_window_region(context)
        self._rebuild_layout(context, region)

        if self._layout is None:
            self.report({'ERROR'}, "レイアウトの作成に失敗しました")
            return {'CANCELLED'}

        self._manager = GPUPanelManager(self.PANEL_UID, self._layout)
        if not self._manager.open(context, self.draw_callback, 'IMAGE_EDITOR', timer_interval=0.05):
            self.report({'ERROR'}, "パネルを開けませんでした")
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._manager:
            self._manager.close(context)
            self._manager = None
        self._layout = None

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

        space = context.space_data
        tool_settings = context.scene.tool_settings

        if self._panel_x is None:
            self._panel_x = 50
        if self._panel_y is None:
            self._panel_y = region.height - 50

        if self._layout is None:
            style = GPULayoutStyle.from_blender_theme('PANEL')
            layout = GPULayout(x=self._panel_x, y=self._panel_y, width=200, style=style)
            layout._draw_background = True
            layout._draw_outline = True

            def request_close():
                self._should_close = True

            layout.set_title_bar(
                title="Quick UV",
                show_close=True,
                on_close=request_close
            )
            layout.set_panel_config(uid=self.PANEL_UID, resizable=True)
            layout.set_region_bounds(region.width, region.height)

            # ──────────────────────────────────────────
            # UV Selection Section
            # ──────────────────────────────────────────
            layout.label(text="Selection")

            # 選択同期
            layout.prop(tool_settings, "use_uv_select_sync", text="Sync Selection", toggle=1)

            layout.separator()

            # ──────────────────────────────────────────
            # Display Section
            # ──────────────────────────────────────────
            layout.label(text="Display")

            # ストレッチ表示
            layout.prop(space.uv_editor, "show_stretch", text="Stretch")

            # UDIM タイル表示
            layout.prop(space.uv_editor, "show_grid_over_image", text="Grid Over Image")

            # ピクセル座標
            layout.prop(space.uv_editor, "show_pixel_coords", text="Pixel Coords")

            layout.separator()

            # ──────────────────────────────────────────
            # Snapping Section
            # ──────────────────────────────────────────
            layout.label(text="Snapping")

            # UVスナップ
            layout.prop(tool_settings, "use_snap_uv", text="UV Snap", toggle=1)

            # layout.separator()
            # layout.label(text="ESC to close", icon='INFO')

            self._layout = layout
        else:
            self._layout.x = self._panel_x
            self._layout.y = self._panel_y
            self._layout.set_region_bounds(region.width, region.height)

        self._panel_x = self._layout.x
        self._panel_y = self._layout.y

    def draw_callback(self, manager: GPUPanelManager, context):
        if not manager.should_draw(context):
            return
        try:
            region = self._get_window_region(context)
            self._rebuild_layout(context, region)
            if self._layout:
                self._layout.update_and_draw()
        except Exception as e:
            import traceback
            print(f"Draw error: {e}")
            traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
# Demo 8: Blender Compat Test - blender_compat_todo.md の完了済み機能テスト
# ═══════════════════════════════════════════════════════════════════════════════

def _build_blender_compat_content(layout, context, *, use_bpy_ops: bool) -> None:
    """完了済み機能のテストコンテンツを構築する共通関数

    Args:
        layout: GPULayout または bpy.types.UILayout
        context: Blender context
        use_bpy_ops: True なら Blender UILayout 用、False なら GPULayout 用
    """
    # アイコン切り替え: Blender UILayout は標準アイコン、GPULayout はカスタム PNG
    def icon(blender_icon: str) -> str:
        return blender_icon if use_bpy_ops else 'roaoao'

    # ═══════════════════════════════════════════════════════════════
    # 1. VectorItem (A-2) - 配列プロパティ
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="1. VectorItem (A-2)", icon=icon('ORIENTATION_GLOBAL'))

    if context.object:
        # location (Vector3)
        layout.prop(context.object, "location")

        # scale (Vector3)
        layout.prop(context.object, "scale", text="Scale")

        # rotation_euler (Vector3) - 違う subtype
        layout.prop(context.object, "rotation_euler", text="Rotation")

    else:
        layout.label(text="(Select an object)")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 2. index パラメータ (B-1) - 配列の個別要素
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="2. index parameter (B-1)", icon=icon('LINENUMBERS_ON'))

    if context.object:
        # index=0 で X のみ
        layout.prop(context.object, "location", index=0, text="X Only")
        # index=1 で Y のみ
        layout.prop(context.object, "location", index=1, text="Y Only")
        # index=2 で Z のみ
        layout.prop(context.object, "location", index=2, text="Z Only")
    else:
        layout.label(text="(Select an object)")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 3. icon_only (B-2) - アイコンのみ表示
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="3. icon_only (B-2)", icon=icon('IMAGE_DATA'))

    if context.object:
        row = layout.row()
        # 通常表示
        row.prop(context.object, "hide_viewport", text="Normal")
        # icon_only=True
        row.prop(context.object, "hide_viewport", icon_only=True)
        row.prop(context.object, "hide_render", icon_only=True)
        row.prop(context.object, "hide_select", icon_only=True)
    else:
        layout.label(text="(Select an object)")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 4. heading パラメータ (C-1) - row/column のヘッディング
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="4. heading parameter (C-1)", icon=icon('ALIGN_JUSTIFY'))

    # row with heading
    row = layout.row(heading="Row Heading")
    row.label(text="Item 1")
    row.label(text="Item 2")

    # column with heading
    col = layout.column(heading="Column Heading")
    col.label(text="Vertical Item 1")
    col.label(text="Vertical Item 2")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 5. column_flow (C-2) - 複数列フローレイアウト
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="5. column_flow (C-2)", icon=icon('OUTLINER'))

    # 2列フロー
    flow = layout.column_flow(columns=2)
    flow.label(text="A")
    flow.label(text="B")
    flow.label(text="C")
    flow.label(text="D")
    flow.label(text="E")
    flow.label(text="F")

    layout.separator()

    # 3列フロー with align
    layout.label(text="column_flow(columns=3, align=True)")
    flow3 = layout.column_flow(columns=3, align=True)
    for i in range(9):
        if use_bpy_ops:
            flow3.operator("mesh.primitive_cube_add", text=f"Btn {i+1}")
        else:
            flow3.operator(text=f"Btn {i+1}")

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 6. use_property_split (C-3) - プロパティ分割表示
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="6. use_property_split (C-3)", icon=icon('SNAP_INCREMENT'))

    # use_property_split を有効化
    layout.use_property_split = True

    if context.object:
        layout.prop(context.object, "location")
        layout.prop(context.object, "scale")

        # heading と組み合わせ
        col = layout.column(heading="Visibility")
        col.prop(context.object, "hide_viewport")
        col.prop(context.object, "hide_render")

    else:
        layout.label(text="(Select an object)")

    # use_property_split を無効化して戻す
    layout.use_property_split = False

    layout.separator()

    # ═══════════════════════════════════════════════════════════════
    # 7. 組み合わせテスト - 複数機能の組み合わせ
    # ═══════════════════════════════════════════════════════════════
    layout.label(text="7. Combined Test", icon=icon('PREFERENCES'))

    layout.use_property_split = True

    if context.object:
        # VectorItem + use_property_split
        layout.prop(context.object, "location", text="Position")

        # index + use_property_split
        row = layout.row(heading="Individual Axes")
        row.prop(context.object, "location", index=0, text="X")
        row.prop(context.object, "location", index=1, text="Y")
        row.prop(context.object, "location", index=2, text="Z")

    else:
        layout.label(text="(Select an object)")

    layout.use_property_split = False


class DEMO_OT_blender_compat_gpulayout(Operator, GPUPanelMixin):
    """GPULayout - Blender Compat Test (blender_compat_todo.md の完了済み機能)"""
    bl_idname = "demo.blender_compat_gpulayout"
    bl_label = "Demo: Blender Compat (GPULayout)"
    bl_options = {'REGISTER'}

    # GPUPanelMixin 設定
    gpu_panel_uid = "demo_blender_compat_gpulayout"
    gpu_title = "GPULayout - Compat Test"
    gpu_width = 360

    def modal(self, context, event):
        return self._modal_impl(context, event)

    def invoke(self, context, event):
        return self._invoke_impl(context, event)

    def cancel(self, context):
        return self._cancel_impl(context)

    def draw_panel(self, layout, context):
        """完了済み機能のテスト（GPULayout版）"""
        _build_blender_compat_content(layout, context, use_bpy_ops=False)


class DEMO_OT_blender_compat_uilayout(Operator):
    """UILayout Reference - Blender Compat Test (blender_compat_todo.md の完了済み機能)"""
    bl_idname = "demo.blender_compat_uilayout"
    bl_label = "Demo: Blender Compat (UILayout)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        # popup dialog として表示
        return context.window_manager.invoke_popup(self, width=360)

    def draw(self, context):
        """完了済み機能のテスト（Blender UILayout版 - 比較用）"""
        _build_blender_compat_content(self.layout, context, use_bpy_ops=True)
