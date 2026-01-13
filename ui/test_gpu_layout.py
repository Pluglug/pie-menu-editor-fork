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

from .gpu_layout import (
    GPULayout, GPULayoutStyle, GPUTooltip, GPUDrawing, BLFDrawing, IconDrawing,
    Alignment
)


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

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "3D Viewport で実行してください")
            return {'CANCELLED'}

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
        try:
            margin = 20
            col1_x = 50
            col2_x = 380
            col3_x = 680
            start_y = context.region.height - 50

            # ═══════════════════════════════════════════════════════════════
            # Column 1: パネルスタイル（REGULAR）
            # ═══════════════════════════════════════════════════════════════
            y = start_y

            # パネルヘッダー風
            panel_style = GPULayoutStyle.from_blender_theme('REGULAR')

            # ドロップシャドウ付きパネル
            panel = GPULayout(x=col1_x, y=y, width=300, style=panel_style)
            panel._draw_background = True
            panel._draw_outline = True

            # シャドウを先に描画
            if panel_style.shadow_enabled:
                GPUDrawing.draw_drop_shadow(
                    col1_x, y, 300, 200,
                    panel_style.border_radius,
                    panel_style.shadow_color,
                    panel_style.shadow_offset,
                    panel_style.shadow_blur
                )

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

            panel.draw()
            y -= panel.calc_height() + margin + 20

            # ───────────────────────────────────────────────────────────────
            # メニュースタイル（MENU）
            # ───────────────────────────────────────────────────────────────
            menu_style = GPULayoutStyle.from_blender_theme('MENU')

            # ドロップシャドウ
            GPUDrawing.draw_drop_shadow(
                col1_x, y, 280, 180,
                menu_style.border_radius,
                menu_style.shadow_color,
                (6, -6), 12
            )

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

            menu.draw()
            y -= menu.calc_height() + margin + 20

            # ───────────────────────────────────────────────────────────────
            # 選択状態のカラーデモ
            # ───────────────────────────────────────────────────────────────
            sel_style = GPULayoutStyle.from_blender_theme('MENU_ITEM')

            # 通常状態
            GPUDrawing.draw_rounded_rect(
                col1_x, y, 280, 26,
                sel_style.border_radius, sel_style.bg_color
            )
            BLFDrawing.draw_text(
                col1_x + 10, y - 18, "Normal Item",
                sel_style.text_color, sel_style.text_size
            )
            y -= 30

            # 選択状態
            GPUDrawing.draw_rounded_rect(
                col1_x, y, 280, 26,
                sel_style.border_radius, sel_style.bg_color_sel
            )
            BLFDrawing.draw_text(
                col1_x + 10, y - 18, "Selected Item",
                sel_style.text_color_sel, sel_style.text_size
            )
            y -= 30

            # アイテム色
            GPUDrawing.draw_rounded_rect(
                col1_x, y, 280, 26,
                sel_style.border_radius, sel_style.item_color
            )
            BLFDrawing.draw_text(
                col1_x + 10, y - 18, "Item Color",
                sel_style.text_color, sel_style.text_size
            )

            # ═══════════════════════════════════════════════════════════════
            # Column 2: ライン描画テスト
            # ═══════════════════════════════════════════════════════════════
            y = start_y

            line_demo = GPULayout(x=col2_x, y=y, width=260, style=panel_style)
            line_demo._draw_background = True
            line_demo._draw_outline = True
            line_demo.label(text="Line Drawing Comparison")
            line_demo.draw()

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
            shadow_demo.draw()

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

                # シャドウ
                GPUDrawing.draw_drop_shadow(
                    col3_x, y, 220, 60,
                    style.border_radius, style.shadow_color,
                    (3, -3), 6
                )

                demo = GPULayout(x=col3_x, y=y, width=220, style=style)
                demo._draw_background = True
                demo._draw_outline = True

                demo.label(text=f"Style: {style_name}")
                demo.label(text=f"roundness: {style.roundness:.2f}")

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

        except Exception as e:
            import traceback
            print(f"Draw error: {e}")
            traceback.print_exc()


def register():
    bpy.utils.register_class(TEST_OT_gpu_layout)


def unregister():
    bpy.utils.unregister_class(TEST_OT_gpu_layout)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass

    register()
    bpy.ops.test.gpu_layout('INVOKE_DEFAULT')
