# pyright: reportInvalidTypeForm=false
# prefs/operators.py - 小オペレーターとパネル
# LAYER = "prefs"
"""
小規模オペレーター群とパネル

- PME_OT_pmi_name_apply: 提案名を適用
- PME_OT_icons_refresh: アイコンリロード
- InvalidPMEPreferences: 無効な Preferences（旧 Blender 用）
- PME_PT_preferences: サイドパネル設定
"""

from bpy.props import IntProperty
from bpy.types import Operator, Panel

from ..addon import ADDON_ID, get_prefs, ic
from ..infra.previews import ph


class PME_OT_pmi_name_apply(Operator):
    bl_idname = "pme.pmi_name_apply"
    bl_label = ""
    bl_description = "Apply the suggested name"
    bl_options = {'INTERNAL'}

    idx: IntProperty()

    def execute(self, context):
        data = get_prefs().pmi_data
        data.name = data.sname
        return {'FINISHED'}


class PME_OT_icons_refresh(Operator):
    bl_idname = "pme.icons_refresh"
    bl_label = ""
    bl_description = (
        "Reload icons from disk.\n"
        "Use this after adding or changing icon files"
    )
    bl_options = {'INTERNAL'}

    def execute(self, context):
        ph.refresh()
        return {'FINISHED'}


class InvalidPMEPreferences:
    """旧バージョンの Blender 用のダミー Preferences"""
    bl_idname = ADDON_ID

    def draw(self, context):
        col = self.layout.column(align=True)
        row = col.row()
        row.alignment = 'CENTER'
        row.label(text="Please update Blender to the latest version", icon=ic('ERROR'))


class PME_PT_preferences(Panel):
    """サイドパネルに表示する PME 設定パネル"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Pie Menu Editor"
    bl_category = "PME"

    @classmethod
    def poll(cls, context):
        return get_prefs().show_sidepanel_prefs

    def draw(self, context):
        get_prefs().draw_prefs(context, self.layout)
