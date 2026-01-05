# pyright: reportInvalidTypeForm=false
# prefs/context_menu.py - Context Menu 関連
# LAYER = "prefs"
"""
Context Menu 関連のクラス群

- PME_OT_list_specials: Extra tools ポップアップメニュー
- PME_MT_button_context: ボタンコンテキストメニューの基底クラス
- PME_OT_context_menu: コンテキストメニューオペレーター
- button_context_menu: WM_MT_button_context に追加するメニュー関数
- add_rmb_menu: 右クリックメニュー登録
"""

import bpy
from bpy import types as bpy_types
from bpy.props import StringProperty
from bpy.types import Menu, Operator, WM_MT_button_context

from ..addon import get_prefs, ic
from ..bl_utils import gen_prop_path
from ..core import constants as CC
from ..infra.property import to_py_value
from ..ui.layout import operator
from .. import operator_utils
from .. import pme
from .. import operators as OPS
from ..operators.ed.tags import PME_OT_tags
from .pm_ops import (
    PME_OT_pm_enable_by_tag,
    PME_OT_pm_remove,
    PME_OT_pm_remove_by_tag,
)


class PME_OT_list_specials(Operator):
    bl_idname = "pme.list_specials"
    bl_label = ""
    bl_description = "Extra tools"
    bl_options = {'INTERNAL'}

    def draw_menu(self, menu, context):
        layout = menu.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        operator(
            layout,
            PME_OT_pm_enable_by_tag.bl_idname,
            "Enable by Tag",
            CC.ICON_ON,
            enable=True,
        )
        operator(
            layout,
            PME_OT_pm_enable_by_tag.bl_idname,
            "Disable by Tag",
            CC.ICON_OFF,
            enable=False,
        )

        layout.separator()

        operator(
            layout,
            PME_OT_tags.bl_idname,
            "Tag Enabled Items",
            'SOLO_ON',
            group=True,
            action='TAG',
        )
        operator(
            layout,
            PME_OT_tags.bl_idname,
            "Untag Enabled Items",
            'SOLO_OFF',
            group=True,
            action='UNTAG',
        )

        layout.separator()

        operator(layout, PME_OT_pm_remove_by_tag.bl_idname, "Remove Items by Tag", 'X')
        operator(
            layout,
            PME_OT_pm_remove.bl_idname,
            "Remove Enabled Items",
            'X',
            mode='ENABLED',
        )
        operator(
            layout,
            PME_OT_pm_remove.bl_idname,
            "Remove Disabled Items",
            'X',
            mode='DISABLED',
        )
        operator(
            layout, PME_OT_pm_remove.bl_idname, "Remove All Items", 'X', mode='ALL'
        )

    def execute(self, context):
        context.window_manager.popup_menu(self.draw_menu)
        return {'FINISHED'}


class PME_MT_button_context:
    bl_label = "Button Context Menu"

    def draw(self, context):
        self.layout.separator()


class PME_OT_context_menu(Operator):
    bl_idname = "pme.context_menu"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    prop: StringProperty(options={'SKIP_SAVE'})
    operator: StringProperty(options={'SKIP_SAVE'})
    name: StringProperty(options={'SKIP_SAVE'})

    def draw_menu(self, menu, context):
        layout = menu.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        pr = get_prefs()
        pm = pr.selected_pm
        if pm:
            if self.prop or self.operator:
                operator(
                    layout,
                    PME_OT_context_menu.bl_idname,
                    "Add to " + pm.name,
                    icon=ic('ADD'),
                    prop=self.prop,
                    operator=self.operator,
                    name=self.name,
                )
            else:
                row = layout.row()
                row.enabled = False
                row.label(text="Can't Add This Widget", icon=ic('ADD'))
            layout.separator()

        operator(
            layout,
            OPS.WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )
        operator(layout, OPS.PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM')

        layout.separator()

        layout.prop(pr, "debug_mode")
        layout.prop(pr, "interactive_panels")

    def execute(self, context):
        if self.prop:
            bpy.ops.pme.pm_edit(
                'INVOKE_DEFAULT', text=self.prop, name=self.name, auto=False
            )
            return {'FINISHED'}

        if self.operator:
            bpy.ops.pme.pm_edit(
                'INVOKE_DEFAULT', text=self.operator, name=self.name, auto=False
            )
            return {'FINISHED'}

        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        if button_prop and button_pointer:
            path = gen_prop_path(button_pointer, button_prop)
            if path:
                value = pme.context.eval(path)
                if value is not None:
                    path = "%s = %s" % (path, repr(value))

                self.prop = path
                # self.name = button_prop.name or utitle(
                #     button_prop.identifier)

        button_operator = getattr(context, "button_operator", None)
        if button_operator:
            tpname = button_operator.__class__.__name__
            idname = operator_utils.to_bl_idname(tpname)
            args = ""
            keys = button_operator.keys()
            if keys:
                args = []
                for k in keys:
                    v = getattr(button_operator, k)
                    value = to_py_value(button_operator.rna_type, k, v)
                    if value is None or isinstance(value, dict) and not value:
                        continue
                    args.append("%s=%s" % (k, repr(value)))

                args = ", ".join(args)
            cmd = "bpy.ops.%s(%s)" % (idname, args)

            self.operator = cmd

        context.window_manager.popup_menu(self.draw_menu, title="Pie Menu Editor")
        return {'FINISHED'}


def button_context_menu(self, context):
    layout = self.layout

    button_pointer = getattr(context, "button_pointer", None)
    button_prop = getattr(context, "button_prop", None)
    button_operator = getattr(context, "button_operator", None)

    layout.operator(
        PME_OT_context_menu.bl_idname, text="Pie Menu Editor", icon=ic('COLOR')
    )


def add_rmb_menu():
    if not hasattr(bpy_types, "WM_MT_button_context"):
        tp = type("WM_MT_button_context", (PME_MT_button_context, Menu), {})
        bpy.utils.register_class(tp)

    WM_MT_button_context.append(button_context_menu)
