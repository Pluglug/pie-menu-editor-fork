"""
GPULayout テストスクリプト

Blender のテキストエディタで実行して動作確認できます。

使い方:
1. Blender のテキストエディタにこのスクリプトを開く
2. 「Run Script」ボタン（▷）をクリック
3. 3D Viewport の左上にサンプル UI が表示される
4. 終了するには 3D Viewport で ESC キーを押す
"""

import bpy
import gpu
from bpy.types import Operator

# PME がインストールされている場合
try:
    from pie_menu_editor.ui.gpu_layout import (
        GPULayout, GPULayoutStyle, GPUTooltip, GPUDrawing, BLFDrawing, IconDrawing,
        Alignment
    )
    PME_AVAILABLE = True
except ImportError:
    PME_AVAILABLE = False
    print("PME not available, using embedded module")


# PME がない場合のフォールバック（開発用）
if not PME_AVAILABLE:
    # gpu_layout.py の内容をここに埋め込むか、
    # 直接ファイルパスから import する
    import sys
    import os

    # 開発環境のパスを追加
    addon_path = r"E:\0187_Pie-Menu-Editor\MyScriptDir\addons"
    if addon_path not in sys.path:
        sys.path.insert(0, addon_path)

    try:
        from pie_menu_editor.ui.gpu_layout import (
            GPULayout, GPULayoutStyle, GPUTooltip, GPUDrawing, BLFDrawing, IconDrawing,
            Alignment
        )
        PME_AVAILABLE = True
    except ImportError as e:
        print(f"Failed to import gpu_layout: {e}")
        PME_AVAILABLE = False


class TEST_OT_gpu_layout(Operator):
    """GPULayout テストオペレーター"""
    bl_idname = "test.gpu_layout"
    bl_label = "Test GPULayout"
    bl_options = {'REGISTER'}

    _handler = None
    _timer = None

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            return {'PASS_THROUGH'}

        # イベント処理（将来のインタラクティブ機能用）
        # if self._layout and self._layout.handle_event(event):
        #     return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "3D Viewport で実行してください")
            return {'CANCELLED'}

        if not PME_AVAILABLE:
            self.report({'ERROR'}, "gpu_layout モジュールが見つかりません")
            return {'CANCELLED'}

        # draw handler を登録
        args = (self, context)
        self._handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_PIXEL'
        )

        # タイマーを登録（再描画用）
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
        try:
            # 左列の基準位置
            left_x = 50
            left_y = context.region.height - 50
            margin = 20  # ウィジェット間のマージン

            # 右列の基準位置
            right_x = 400
            right_y = context.region.height - 50

            # ═══════════════════════════════════════════════════════════════
            # 1. ツールチップのデモ
            # ═══════════════════════════════════════════════════════════════
            tooltip = GPUTooltip(max_width=350)
            tooltip.title("Pie Menu Editor - GPULayout Demo")
            tooltip.description(
                "これは GPULayout のデモです。\n"
                "Blender の UILayout API を GPU 描画で再現しています。\n"
                "テキストの自動折り返しもサポートしています。"
            )
            tooltip.shortcut("ESC: 終了")
            tooltip.python("bpy.ops.test.gpu_layout()")

            # 高さを取得して描画
            tooltip_height = tooltip.draw(left_x, left_y)
            left_y -= tooltip_height + margin

            # ═══════════════════════════════════════════════════════════════
            # 2. レイアウトのデモ
            # ═══════════════════════════════════════════════════════════════
            layout = GPULayout(
                x=left_x,
                y=left_y,
                width=300
            )
            layout._draw_background = True
            layout._draw_outline = True

            # タイトル
            layout.label(text="GPULayout Components", icon='INFO')
            layout.separator()

            # Row レイアウト
            row = layout.row()
            row.label(text="Left")
            row.label(text="Center")
            row.label(text="Right")

            layout.separator()

            # プロパティ表示
            if context.object:
                layout.prop_display(context.object, "name", text="Object")
                layout.prop_display(context.object, "type", text="Type")

                # Location をフォーマット
                loc = context.object.location
                layout.label(text=f"Location: ({loc.x:.2f}, {loc.y:.2f}, {loc.z:.2f})")
            else:
                layout.label(text="No active object")

            layout.separator()

            # ボタン（クリックはまだ動作しない）
            layout.operator(text="Sample Button")

            layout.draw()

            # ═══════════════════════════════════════════════════════════════
            # 3. ボックスのデモ（右列）
            # ═══════════════════════════════════════════════════════════════
            box_layout = GPULayout(
                x=right_x,
                y=right_y,
                width=250
            )

            box = box_layout.box()
            box.label(text="Box Container")
            box.separator(factor=0.5)
            box.label(text="Item 1")
            box.label(text="Item 2")
            box.label(text="Item 3")

            box_layout.draw()

            # ボックスの高さを取得して次の Y 位置を計算
            right_y -= box_layout.calc_height() + margin

            # ═══════════════════════════════════════════════════════════════
            # 4. スタイルバリエーション（右列、ボックスの下）
            # ═══════════════════════════════════════════════════════════════
            styles = ['TOOLTIP', 'BOX', 'REGULAR']

            for style_name in styles:
                style = GPULayoutStyle.from_blender_theme(style_name)
                small_layout = GPULayout(
                    x=right_x,
                    y=right_y,
                    width=200,
                    style=style
                )
                small_layout._draw_background = True
                small_layout._draw_outline = True
                small_layout.label(text=f"Style: {style_name}")
                small_layout.draw()

                # 次のスタイルボックスの Y 位置を計算
                right_y -= small_layout.calc_height() + margin

            # ═══════════════════════════════════════════════════════════════
            # 5. アイコンテスト（右列）
            # ═══════════════════════════════════════════════════════════════
            icon_layout = GPULayout(
                x=right_x,
                y=right_y,
                width=250
            )
            icon_layout._draw_background = True
            icon_layout._draw_outline = True

            icon_layout.label(text="Icon Test (PME Custom Icons)")
            icon_layout.separator(factor=0.5)

            # PME カスタムアイコン名でラベル表示
            # システムアイコン: p1, p2, pPress, pHold, etc.
            icon_layout.label(text="Press Mode", icon="pPress")
            icon_layout.label(text="Hold Mode", icon="pHold")
            icon_layout.label(text="Double Click", icon="pDouble")
            icon_layout.label(text="Tweak Mode", icon="pTweak")

            icon_layout.separator(factor=0.5)

            # 直接アイコン描画テスト
            icon_layout.label(text="Direct Icon Draw:")

            icon_layout.draw()

            # アイコン単体の直接描画テスト（レイアウト外）
            icon_test_y = right_y - icon_layout.calc_height() - 10
            icon_test_x = right_x + 10
            icon_size = 24

            # PME システムアイコンを並べて描画
            for i, icon_name in enumerate(["p1", "p2", "p3", "p4", "p6", "p7"]):
                x_pos = icon_test_x + i * (icon_size + 4)
                IconDrawing.draw_custom_icon(icon_name, x_pos, icon_test_y, size=icon_size)

            # ═══════════════════════════════════════════════════════════════
            # 6. Alignment デモ（左列の下）
            # ═══════════════════════════════════════════════════════════════
            align_y = left_y - 250  # レイアウトデモの下

            # EXPAND（デフォルト）
            expand_layout = GPULayout(
                x=left_x,
                y=align_y,
                width=300
            )
            expand_layout._draw_background = True
            expand_layout._draw_outline = True
            expand_layout.alignment = Alignment.EXPAND

            expand_layout.label(text="Alignment: EXPAND")
            expand_layout.separator(factor=0.5)
            expand_layout.label(text="Short")
            expand_layout.label(text="Medium text")
            expand_layout.label(text="Longer text here")
            expand_layout.draw()

            align_y -= expand_layout.calc_height() + margin

            # CENTER
            center_layout = GPULayout(
                x=left_x,
                y=align_y,
                width=300
            )
            center_layout._draw_background = True
            center_layout._draw_outline = True
            center_layout.alignment = Alignment.CENTER

            center_layout.label(text="Alignment: CENTER")
            center_layout.separator(factor=0.5)
            center_layout.label(text="Short")
            center_layout.label(text="Medium text")
            center_layout.label(text="Longer text here")
            center_layout.draw()

            align_y -= center_layout.calc_height() + margin

            # LEFT
            left_layout = GPULayout(
                x=left_x,
                y=align_y,
                width=300
            )
            left_layout._draw_background = True
            left_layout._draw_outline = True
            left_layout.alignment = Alignment.LEFT

            left_layout.label(text="Alignment: LEFT")
            left_layout.separator(factor=0.5)
            left_layout.label(text="Short")
            left_layout.label(text="Medium text")
            left_layout.label(text="Longer text here")
            left_layout.draw()

            align_y -= left_layout.calc_height() + margin

            # RIGHT
            right_layout_align = GPULayout(
                x=left_x,
                y=align_y,
                width=300
            )
            right_layout_align._draw_background = True
            right_layout_align._draw_outline = True
            right_layout_align.alignment = Alignment.RIGHT

            right_layout_align.label(text="Alignment: RIGHT")
            right_layout_align.separator(factor=0.5)
            right_layout_align.label(text="Short")
            right_layout_align.label(text="Medium text")
            right_layout_align.label(text="Longer text here")
            right_layout_align.draw()

            # ═══════════════════════════════════════════════════════════════
            # 7. Row align=True デモ
            # ═══════════════════════════════════════════════════════════════
            row_demo_y = icon_test_y - 50

            row_demo = GPULayout(
                x=right_x,
                y=row_demo_y,
                width=250
            )
            row_demo._draw_background = True
            row_demo._draw_outline = True

            row_demo.label(text="Row Demo")
            row_demo.separator(factor=0.5)

            # align=False（デフォルト、スペースあり）
            row_demo.label(text="row(align=False):")
            row1 = row_demo.row(align=False)
            row1.label(text="A")
            row1.label(text="B")
            row1.label(text="C")

            row_demo.separator(factor=0.5)

            # align=True（スペースなし）
            row_demo.label(text="row(align=True):")
            row2 = row_demo.row(align=True)
            row2.label(text="A")
            row2.label(text="B")
            row2.label(text="C")

            row_demo.draw()

        except Exception as e:
            import traceback
            print(f"Draw error: {e}")
            traceback.print_exc()


def register():
    bpy.utils.register_class(TEST_OT_gpu_layout)


def unregister():
    bpy.utils.unregister_class(TEST_OT_gpu_layout)


if __name__ == "__main__":
    # 既に登録されていたら解除
    try:
        unregister()
    except:
        pass

    register()

    # オペレーターを実行
    bpy.ops.test.gpu_layout('INVOKE_DEFAULT')
