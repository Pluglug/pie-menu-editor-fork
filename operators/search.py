# operators/search.py - Search operators for PME
# LAYER = "operators"
#
# Moved from: operators/__init__.py (Phase 2-C operators reorganization)
#
# Contains:
#   - SearchOperator: Base mixin for search popup operators
#   - PME_OT_pm_search_and_select: PM search and selection
#   - PME_OT_addonpref_search: Addon preferences search
#   - PME_OT_pmi_pm_search: PMI PM search
#   - PME_OT_pmi_operator_search: Operator search
#   - PME_OT_pmi_panel_search: Panel search
#   - PME_OT_pmi_area_search: Area search
#   - PME_OT_pmi_menu_search: Menu search (uses SearchOperator mixin)
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from inspect import isclass

from ..addon import get_prefs, get_uprefs
from ..ui import tag_redraw, utitle
from ..ui.layout import operator
from ..keymap_helper import to_ui_hotkey
from ..ui.panels import hidden_panel, bl_panel_enum_items
from .. import operator_utils
from ..core import constants as CC
from ..core.constants import PM_ITEMS_M, MODAL_CMD_MODES


class PME_OT_pm_search_and_select(Operator):
    bl_idname = "pme.pm_search_and_select"
    bl_label = "Search and Select Item"
    bl_description = "Search and select an item"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        pr = get_prefs()

        if not PME_OT_pm_search_and_select.enum_items:
            enum_items = []

            for k in sorted(pr.pie_menus.keys()):
                pm = pr.pie_menus[k]
                if self.mode and pm.mode not in self.mode:
                    continue
                enum_items.append((pm.name, "%s|%s" % (pm.name, to_ui_hotkey(pm)), ""))

            PME_OT_pm_search_and_select.enum_items = enum_items

        return PME_OT_pm_search_and_select.enum_items

    item: EnumProperty(items=get_items)
    mode: EnumProperty(
        items=PM_ITEMS_M, default=set(), options={'SKIP_SAVE', 'ENUM_FLAG'}
    )

    def execute(self, context):
        bpy.ops.wm.pm_select(pm_name=self.item)
        PME_OT_pm_search_and_select.enum_items = None
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_pm_search_and_select.enum_items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_addonpref_search(Operator):
    bl_idname = "pme.addonpref_search"
    bl_label = ""
    bl_description = "Open addon preferences in a popup"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    items = None

    def get_items(self, context):
        cl = PME_OT_addonpref_search
        if not cl.items:
            cl.items = []
            import addon_utils

            for addon in get_uprefs().addons:
                if hasattr(addon.preferences, "draw"):
                    mod = addon_utils.addons_fake_modules.get(addon.module)
                    if not mod:
                        continue
                    info = addon_utils.module_bl_info(mod)
                    cl.items.append((addon.module, info["name"], ""))

        return cl.items

    enumprop: EnumProperty(items=get_items)

    def execute(self, context):
        pr = get_prefs()
        if pr.pmi_data.mode not in MODAL_CMD_MODES:
            pr.pmi_data.mode = 'COMMAND'
        pr.pmi_data.cmd = ""
        pr.pmi_data.cmd += (
            "bpy.ops.pme.popup_addon_preferences(" "addon='%s', center=True)"
        ) % self.enumprop

        sname = ""
        for item in PME_OT_addonpref_search.items:
            if item[0] == self.enumprop:
                sname = item[1]
                break

        pr.pmi_data.sname = sname

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        self.__class__.items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_pmi_pm_search(Operator):
    bl_idname = "pme.pmi_pm_search"
    bl_label = ""
    bl_description = "Open/execute/draw a menu, popup or operator"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    items = None

    def get_items(self, context):
        pr = get_prefs()
        if not PME_OT_pmi_pm_search.items:
            if PME_OT_pmi_pm_search.items is None:
                PME_OT_pmi_pm_search.items = []

            items = PME_OT_pmi_pm_search.items
            for pm in sorted(pr.pie_menus.keys()):
                if self.custom and pr.pie_menus[pm].mode != 'DIALOG':
                    continue
                items.append((pm, pm, ""))

            PME_OT_pmi_pm_search.items = items

        return PME_OT_pmi_pm_search.items

    enumprop: EnumProperty(items=get_items)
    custom: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()

        if self.custom:
            pr.pmi_data.mode = 'CUSTOM'
            pr.pmi_data.custom = "draw_menu(\"%s\")" % self.enumprop
        else:
            if pr.pmi_data.mode not in MODAL_CMD_MODES:
                pr.pmi_data.mode = 'COMMAND'
            pr.pmi_data.cmd = "open_menu(\"%s\")" % self.enumprop

        pr.pmi_data.sname = self.enumprop

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        if PME_OT_pmi_pm_search.items:
            PME_OT_pmi_pm_search.items.clear()
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_pmi_operator_search(Operator):
    bl_idname = "pme.pmi_operator_search"
    bl_label = ""
    bl_description = (
        "Command tab:\n"
        "  Execute operator when the user clicks the button"
    )
    bl_options = {'INTERNAL'}
    bl_property = "operator"

    idx: IntProperty(options={'SKIP_SAVE'})

    items = []

    def get_items(self, context):
        if not PME_OT_pmi_operator_search.items:
            items = []
            for op_module_name in dir(bpy.ops):
                op_module = getattr(bpy.ops, op_module_name)
                for op_submodule_name in dir(op_module):
                    op = getattr(op_module, op_submodule_name)
                    op_name = operator_utils.get_rna_type(op).bl_rna.name

                    label = op_name or op_submodule_name
                    label = "%s|%s" % (utitle(label), op_module_name.upper())

                    items.append(
                        ("%s.%s" % (op_module_name, op_submodule_name), label, "")
                    )

            PME_OT_pmi_operator_search.items = items

        return PME_OT_pmi_operator_search.items

    operator: EnumProperty(items=get_items)

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]

        op_name = operator_utils.operator_label(self.operator)

        if pr.mode == 'PMI':
            if pr.pmi_data.mode not in MODAL_CMD_MODES:
                pr.pmi_data.mode = 'COMMAND'

            pr.pmi_data.cmd = "bpy.ops.%s()" % self.operator
            pr.pmi_data.sname = op_name or self.operator
        else:
            if pmi.mode not in MODAL_CMD_MODES:
                pmi.mode = 'COMMAND'

            pmi.text = "bpy.ops.%s()" % self.operator
            pmi.name = op_name or self.operator

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_pmi_panel_search(Operator):
    bl_idname = "pme.pmi_panel_search"
    bl_label = "Panel"
    bl_description = "Open or draw the panel in a popup"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    items = None

    def get_items(self, context):
        if not PME_OT_pmi_panel_search.items:
            PME_OT_pmi_panel_search.items = bl_panel_enum_items()

        return PME_OT_pmi_panel_search.items

    enumprop: EnumProperty(items=get_items)
    custom: BoolProperty(options={'SKIP_SAVE'})
    popover: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        tp = hidden_panel(self.enumprop) or getattr(bpy.types, self.enumprop, None)

        if not tp:
            return {'CANCELLED'}

        pr.pmi_data.mode = 'CUSTOM' if self.custom or self.popover else 'COMMAND'

        if self.popover:
            pr.pmi_data.custom = (
                "L.popover("
                "panel='%s', "
                "text=slot, icon=icon, icon_value=icon_value)"
            ) % self.enumprop

        elif pr.pmi_data.mode == 'COMMAND':
            pr.pmi_data.cmd = ("bpy.ops.pme.popup_panel(" "panel='%s')") % self.enumprop

        elif pr.pmi_data.mode == 'CUSTOM':
            frame = header = True
            if (
                self.enumprop == "DATA_PT_modifiers"
                or self.enumprop == "OBJECT_PT_constraints"
                or self.enumprop == "BONE_PT_constraints"
            ):
                frame = header = False

            pr.pmi_data.custom = "panel(\"%s\", frame=%r, header=%r, expand=None)" % (
                self.enumprop,
                frame,
                header,
            )

        sname = (
            tp.bl_label if hasattr(tp, "bl_label") and tp.bl_label else self.enumprop
        )
        if "_PT_" in sname:
            _, _, sname = sname.partition("_PT_")
            sname = utitle(sname)
        pr.pmi_data.sname = sname

        return {'CANCELLED'}

    def invoke(self, context, event):
        PME_OT_pmi_panel_search.items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_pmi_area_search(Operator):
    bl_idname = "pme.pmi_area_search"
    bl_label = "Area"
    bl_description = "Open/toggle area"
    bl_options = {'INTERNAL'}

    area: EnumProperty(
        items=CC.AreaEnumHelper.gen_items_with_current, options={'SKIP_SAVE'}
    )
    cmd: StringProperty(
        default="bpy.ops.pme.popup_area(area='%s')", options={'SKIP_SAVE'}
    )

    def draw_pmi_area_search(self, menu, context):
        for item in CC.AreaEnumHelper.gen_items(context=context):
            operator(
                menu.layout,
                self.bl_idname,
                text=item[1],
                icon='NONE',
                icon_value=item[3],
                area=item[0],
                cmd=self.cmd,
            )

    def execute(self, context):
        pr = get_prefs()

        for item in CC.AreaEnumHelper.gen_items_with_current():
            if item[0] == self.area:
                break

        pr.pmi_data.mode = 'COMMAND'
        pr.pmi_data.cmd = self.cmd % self.area

        pr.pmi_data.sname = item[1]

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.popup_menu(self.draw_pmi_area_search, title="Area")
        return {'FINISHED'}


class SearchOperator:
    """Base mixin for search popup operators.

    Subclasses should:
    - Inherit from both SearchOperator and Operator
    - Set bl_property = "value"
    - Override fill_enum_items(self, items) to populate the items list
    """

    use_cache = False

    def fill_enum_items(self, items):
        pass

    def get_enum_items(self, context):
        cls = getattr(bpy.types, self.__class__.__name__)
        if not hasattr(cls, "enum_items"):
            return tuple()

        if cls.enum_items is None:
            cls.enum_items = []
            cls.fill_enum_items(self, cls.enum_items)

        return cls.enum_items

    value: EnumProperty(name="Value", items=get_enum_items)

    def invoke(self, context, event):
        cls = getattr(bpy.types, self.__class__.__name__)
        if not hasattr(cls, "enum_items"):
            cls.enum_items = None
        elif not self.use_cache and cls.enum_items:
            cls.enum_items.clear()
            cls.enum_items = None

        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_pmi_menu_search(SearchOperator, Operator):
    bl_idname = "pme.pmi_menu_search"
    bl_label = ""
    bl_description = "Call menu"
    bl_options = {'INTERNAL'}
    bl_property = "value"

    idx: IntProperty(options={'SKIP_SAVE'})
    mouse_over: BoolProperty(options={'SKIP_SAVE'})
    pie: BoolProperty(options={'SKIP_SAVE'})

    def fill_enum_items(self, items):
        for tp_name in dir(bpy.types):
            tp = getattr(bpy.types, tp_name)
            if not isclass(tp):
                continue

            if issubclass(tp, bpy.types.Menu) and hasattr(tp, "bl_label"):
                ctx, _, name = tp_name.partition("_MT_")
                label = hasattr(tp, "bl_label") and tp.bl_label or name or tp_name
                label = "%s|%s" % (utitle(label), ctx)

                items.append((tp_name, label, ""))

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]

        if self.pie:
            cmd = "bpy.ops.wm.call_menu_pie(name=\"%s\")" % self.value
            mode = 'COMMAND'

        elif self.mouse_over:
            cmd = (
                "L.menu(\"%s\", text=text, icon=icon, icon_value=icon_value, "
                "use_mouse_over_open=True)"
            ) % self.value
            mode = 'CUSTOM'
        else:
            cmd = "bpy.ops.wm.call_menu(name=\"%s\")" % self.value
            mode = 'COMMAND'

        typ = getattr(bpy.types, self.value)
        name = typ.bl_label if typ.bl_label else self.value

        if pr.mode == 'PMI':
            pr.pmi_data.mode = mode
            if self.mouse_over:
                pr.pmi_data.custom = cmd
            else:
                pr.pmi_data.cmd = cmd
            pr.pmi_data.sname = name
        else:
            pmi.mode = mode
            pmi.text = cmd
            pmi.name = name

        tag_redraw()
        return {'FINISHED'}
