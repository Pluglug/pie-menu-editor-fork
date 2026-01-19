"""
UILayout 動作検証パネル
Blender ソースコード調査結果を実機で確認するためのテストパネル

使い方:
1. Blender のテキストエディタにこのスクリプトを貼り付け
2. 「スクリプト実行」(Alt+P)
3. 3D ビューポートの右サイドバー (N) → 「Test」タブを開く
"""

import bpy


class TEST_PT_scale_x(bpy.types.Panel):
    """テスト1: scale_x の動作確認（改良版）"""
    bl_label = "Test 1: scale_x"
    bl_idname = "TEST_PT_scale_x"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Test"

    def draw(self, context):
        layout = self.layout

        # ===== テスト 1-A: EXPAND モードでは比率が同じなら効果が見えない =====
        layout.label(text="1-A: EXPAND mode (default) - 効果が見えにくい")

        layout.label(text="Normal row:")
        row = layout.row()
        row.operator("mesh.primitive_cube_add", text="A")
        row.operator("mesh.primitive_cube_add", text="B")

        layout.label(text="scale_x=2.0 row (同じ見た目になる):")
        row = layout.row()
        row.scale_x = 2.0
        row.operator("mesh.primitive_cube_add", text="A")
        row.operator("mesh.primitive_cube_add", text="B")

        layout.separator()

        # ===== テスト 1-B: LEFT alignment で自然サイズを維持 =====
        layout.label(text="1-B: LEFT alignment - 効果が見える")

        layout.label(text="Normal row (LEFT):")
        row = layout.row()
        row.alignment = 'LEFT'
        row.operator("mesh.primitive_cube_add", text="A")
        row.operator("mesh.primitive_cube_add", text="B")

        layout.label(text="scale_x=2.0 row (LEFT):")
        row = layout.row()
        row.alignment = 'LEFT'
        row.scale_x = 2.0
        row.operator("mesh.primitive_cube_add", text="A")
        row.operator("mesh.primitive_cube_add", text="B")

        layout.separator()

        # ===== テスト 1-C: sub-row に scale_x を適用 =====
        layout.label(text="1-C: sub-row with scale_x")

        row = layout.row()
        row.operator("mesh.primitive_cube_add", text="Normal")
        sub = row.row()
        sub.scale_x = 2.0
        sub.operator("mesh.primitive_cube_add", text="2x")
        row.operator("mesh.primitive_cube_add", text="Normal")

        layout.separator()

        # 期待の説明
        box = layout.box()
        box.label(text="期待:", icon='INFO')
        box.label(text="1-A: EXPAND では比率1:1→1:1で同じ見た目")
        box.label(text="1-B: LEFT では scale_x=2.0 が2倍幅")
        box.label(text="1-C: 中央の '2x' ボタンが2倍幅")


class TEST_PT_split_behavior(bpy.types.Panel):
    """テスト2: split の暗黙 column 確認"""
    bl_label = "Test 2: split behavior"
    bl_idname = "TEST_PT_split_behavior"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Test"

    def draw(self, context):
        layout = self.layout

        # パターン1: column を明示的に使う
        layout.label(text="Pattern 1: explicit column()")
        split = layout.split(factor=0.3)
        col1 = split.column()
        col1.label(text="30% Col")
        col1.label(text="Item 2")
        col2 = split.column()
        col2.label(text="70% Col")
        col2.label(text="Item 2")

        layout.separator()

        # パターン2: 直接 label を追加
        layout.label(text="Pattern 2: direct label()")
        split = layout.split(factor=0.3)
        split.label(text="30%?")
        split.label(text="70%?")

        layout.separator()

        # パターン3: 3つの直接アイテム
        layout.label(text="Pattern 3: 3 direct items (factor=0.25)")
        split = layout.split(factor=0.25)
        split.label(text="25%")
        split.label(text="37.5%")
        split.label(text="37.5%")

        layout.separator()

        # 期待の説明
        box = layout.box()
        box.label(text="期待:", icon='INFO')
        box.label(text="Pattern 1: 縦に2行ずつ")
        box.label(text="Pattern 2: 横に2つ並ぶ（暗黙columnなし）")
        box.label(text="Pattern 3: 25% / 37.5% / 37.5%")


class TEST_PT_alignment(bpy.types.Panel):
    """テスト3: alignment と幅の関係"""
    bl_label = "Test 3: alignment"
    bl_idname = "TEST_PT_alignment"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Test"

    def draw(self, context):
        layout = self.layout

        # EXPAND (デフォルト)
        layout.label(text="alignment=EXPAND (default):")
        row = layout.row(align=False)
        row.alignment = 'EXPAND'
        row.label(text="Short")
        row.label(text="Medium Text")

        layout.separator()

        # LEFT
        layout.label(text="alignment=LEFT:")
        row = layout.row(align=False)
        row.alignment = 'LEFT'
        row.label(text="Short")
        row.label(text="Medium Text")

        layout.separator()

        # CENTER
        layout.label(text="alignment=CENTER:")
        row = layout.row(align=False)
        row.alignment = 'CENTER'
        row.label(text="Short")
        row.label(text="Medium Text")

        layout.separator()

        # RIGHT
        layout.label(text="alignment=RIGHT:")
        row = layout.row(align=False)
        row.alignment = 'RIGHT'
        row.label(text="Short")
        row.label(text="Medium Text")

        layout.separator()

        # 期待の説明
        box = layout.box()
        box.label(text="期待:", icon='INFO')
        box.label(text="EXPAND: 全幅を使う（拡大）")
        box.label(text="LEFT/CENTER/RIGHT: 自然サイズ維持")


class TEST_PT_ui_units_x(bpy.types.Panel):
    """テスト4: ui_units_x の動作"""
    bl_label = "Test 4: ui_units_x"
    bl_idname = "TEST_PT_ui_units_x"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Test"

    def draw(self, context):
        layout = self.layout

        # 通常
        layout.label(text="Normal labels:")
        row = layout.row()
        row.label(text="Label A")
        row.label(text="Label B")
        row.label(text="Label C")

        layout.separator()

        # ui_units_x で固定幅
        layout.label(text="First label with ui_units_x=5:")
        row = layout.row()
        sub = row.row()
        sub.ui_units_x = 5
        sub.label(text="Fixed")
        row.label(text="Flex 1")
        row.label(text="Flex 2")

        layout.separator()

        # 期待の説明
        box = layout.box()
        box.label(text="期待:", icon='INFO')
        box.label(text="Fixed: 約100px固定幅")
        box.label(text="Flex 1/2: 残りを推定サイズ比で分配")


# # 登録
# classes = [
#     TEST_PT_scale_x,
#     TEST_PT_split_behavior,
#     TEST_PT_alignment,
#     TEST_PT_ui_units_x,
# ]


# def register():
#     for cls in classes:
#         bpy.utils.register_class(cls)


# def unregister():
#     for cls in reversed(classes):
#         bpy.utils.unregister_class(cls)


# if __name__ == "__main__":
#     register()
