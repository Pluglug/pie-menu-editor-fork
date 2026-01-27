# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Operators

GPU Layout ウィジェットのインタラクションを処理するオペレーター群。
"""

from __future__ import annotations

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty


class PME_OT_gpu_enum_select(Operator):
    """
    GPU Enum 選択用内部オペレーター

    MenuButtonItem の popup_menu から呼び出され、
    ウィジェットの値を更新する。

    Note:
        - このオペレーターは内部用（bl_options = {'INTERNAL'}）
        - widget_id でグローバルレジストリからウィジェットを参照
        - 処理完了後にレジストリからウィジェットを削除
    """
    bl_idname = "pme.gpu_enum_select"
    bl_label = "Select Enum Value"
    bl_options = {'INTERNAL'}

    value: StringProperty(
        name="Value",
        description="Selected enum value (identifier)",
        default="",
    )

    widget_id: IntProperty(
        name="Widget ID",
        description="Internal widget ID for callback",
        default=0,
    )

    def execute(self, context):
        from ...ui.gpu.widget_factory import get_widget, unregister_widget

        # レジストリからウィジェットを取得
        widget = get_widget(self.widget_id)
        if widget is not None:
            # 値を設定（set_value 内でコールバックが呼ばれる）
            widget.set_value(self.value)

        # レジストリからウィジェットを削除
        unregister_widget(self.widget_id)

        return {'FINISHED'}
