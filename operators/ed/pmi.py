# pyright: reportInvalidTypeForm=false
# operators/ed/pmi.py - Pie Menu Item (PMI) editing operators
# LAYER = "operators"
#
# Moved from: editors/base.py (Phase 5-A operator separation)

LAYER = "operators"

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import Operator
from ...addon import get_prefs, temp_prefs
from ...core.constants import (
    F_EXPAND,
    I_CMD,
    MAX_STR_LEN,
    MODAL_CMD_MODES,
    W_PMI_LONG_CMD,
)
from ...bl_utils import (
    message_box,
    re_operator,
    re_prop,
    re_prop_path,
    ConfirmBoxHandler,
)
from ...infra.collections import (
    AddItemOperator,
    MoveItemOperator,
    RemoveItemOperator,
)
from ...infra.debug import DBG_CMD_EDITOR
from ...ui import tag_redraw, shorten_str, gen_prop_name, gen_op_name, find_enum_args
from ...ui import screen as SU
from ...ui.layout import lh
from ...infra.property import to_py_value
from ... import pme
from ... import operator_utils
from ... import keymap_helper


def _edit_pmi(operator, text, event):
    pr = get_prefs()
    pm = pr.selected_pm
    pmi = None

    if not text and operator.text:
        text = operator.text

    if not text:
        message_box(I_CMD)
        return

    if operator.new_script:
        pm = pr.add_pm('SCRIPT')
        pmi = pm.pmis[0]

    if not operator.add:
        if pm.mode == 'DIALOG' and event.ctrl:
            pm.pmis.add()
            if not event.shift:
                operator.pm_item += 1

            pm.pmis.move(len(pm.pmis) - 1, operator.pm_item)
            pmi = pm.pmis[operator.pm_item]
            pmi.mode = 'COMMAND'

        else:
            pmi = pm.pmis[operator.pm_item]
    else:
        if pm.mode in {'RMENU', 'SCRIPT', 'MACRO', 'MODAL'}:
            pm.pmis.add()
            if operator.pm_item != -1:
                pm.pmis.move(len(pm.pmis) - 1, operator.pm_item)
            pmi = pm.pmis[operator.pm_item]
            pmi.mode = 'COMMAND'

        elif pm.mode == 'DIALOG':
            ed = pm.ed
            if ed:
                pmi = ed.add_pd_row(pm)

    if not pmi:
        return

    ed = pm.ed

    if operator.mode:
        pmi.name = operator.name
        pmi.mode = operator.mode
        pmi.text = operator.text

    else:
        lines = text.split("\n")
        if len(lines) > 1:
            filtered = []
            for line in lines:
                if re_prop.search(line) or re_operator.search(line):
                    filtered.append(line)
            lines = filtered

        len_lines = len(lines)
        if len_lines == 0:
            message_box(I_CMD)
        elif len_lines > 1:
            pmi.mode = 'COMMAND'
            pmi.text = "; ".join(lines)
            pmi.name = shorten_str(pmi.text)
        else:
            parsed = False
            mo = re_operator.search(lines[0])
            if mo:
                parsed = True
                if ed and 'CUSTOM' in ed.supported_slot_modes and find_enum_args(mo):
                    bpy.ops.wm.pmi_type_select(
                        pm_item=operator.pm_item, text=lines[0], mode="ENUM_ASK"
                    )
                    return

                else:
                    name = gen_op_name(mo)
                    pmi.name = name
                    pmi.mode = 'COMMAND'
                    pmi.text = lines[0]

            mo = not parsed and re_prop.search(lines[0])
            if mo:
                parsed = True
                if ed and 'PROP' in ed.supported_slot_modes and mo.group(4):
                    bpy.ops.wm.pmi_type_select(
                        pm_item=operator.pm_item, text=lines[0], mode="PROP_ASK"
                    )
                    return
                else:
                    pmi.name, icon = gen_prop_name(mo)
                    if icon:
                        pmi.icon = icon
                    pmi.mode = 'COMMAND'
                    pmi.text = lines[0]

            mo = not parsed and re_prop_path.search(lines[0])
            if mo:
                if ed and 'PROP' in ed.supported_slot_modes:
                    parsed = True
                    pmi.name, icon = gen_prop_name(mo, True)
                    if icon:
                        pmi.icon = icon
                    pmi.mode = 'PROP'
                    pmi.text = lines[0]

            if not parsed:
                message_box(I_CMD)

    if ed:
        ed.on_pmi_edit(pm, pmi)

    pr.update_tree()


class WM_OT_pmi_type_select(Operator):
    bl_idname = "wm.pmi_type_select"
    bl_label = ""
    bl_description = "Select type of the item"
    bl_options = {'INTERNAL'}

    pm_item: IntProperty()
    text: StringProperty()
    mode: StringProperty()

    def _draw(self, menu, context):
        pm = get_prefs().selected_pm
        lh.lt(menu.layout)

        lh.operator(
            WM_OT_pmi_type_select.bl_idname,
            "Command",
            pm_item=self.pm_item,
            text=self.text,
            mode='COMMAND',
        )

        if self.mode == 'PROP_ASK':
            lh.operator(
                WM_OT_pmi_type_select.bl_idname,
                "Property",
                pm_item=self.pm_item,
                text=self.text,
                mode='PROP',
            )

            mo = re_prop.search(self.text)
            prop_path = mo.group(1) + mo.group(2)
            obj_path, _, prop_name = prop_path.rpartition(".")
            prop = None
            try:
                tp = type(eval(obj_path, pme.context.globals))
                prop = tp.bl_rna.properties[prop_name]
            except:
                pass

            if prop and prop.type == 'ENUM':
                lh.operator(
                    WM_OT_pmi_type_select.bl_idname,
                    "Custom (Menu)",
                    pm_item=self.pm_item,
                    text=self.text,
                    mode='PROP_ENUM_MENU',
                )

                lh.operator(
                    WM_OT_pmi_type_select.bl_idname,
                    "Custom (Expand Horizontally)",
                    pm_item=self.pm_item,
                    text=self.text,
                    mode='PROP_ENUM_EXPAND_H',
                )

                lh.operator(
                    WM_OT_pmi_type_select.bl_idname,
                    "Custom (Expand Vertically)",
                    pm_item=self.pm_item,
                    text=self.text,
                    mode='PROP_ENUM_EXPAND_V',
                )

        if self.mode == 'ENUM_ASK':
            lh.operator(
                WM_OT_pmi_type_select.bl_idname,
                "Custom (Menu)",
                pm_item=self.pm_item,
                text=self.text,
                mode='ENUM_MENU',
            )

            if pm.mode != 'PMENU':
                lh.operator(
                    WM_OT_pmi_type_select.bl_idname,
                    "Custom (List)",
                    pm_item=self.pm_item,
                    text=self.text,
                    mode='ENUM',
                )

    def execute(self, context):
        if 'ASK' in self.mode:
            bpy.context.window_manager.popup_menu(self._draw, title="Select Type")
        else:
            pm = get_prefs().selected_pm
            pmi = pm.pmis[self.pm_item]

            if self.mode == 'COMMAND':
                pmi.mode = 'COMMAND'
                pmi.text = self.text
                mo = re_operator.search(self.text)
                if mo:
                    pmi.name = gen_op_name(mo)
                else:
                    mo = re_prop.search(self.text)
                    pmi.name, icon = gen_prop_name(mo)
                    if icon:
                        pmi.icon = icon

            elif self.mode == 'PROP':
                pmi.mode = 'PROP'
                mo = re_prop.search(self.text)
                pmi.text = mo.group(1) + mo.group(2)
                if pmi.text[-1] == "]":
                    pmi.text, _, _ = pmi.text.rpartition("[")
                pmi.name, icon = gen_prop_name(mo, True)
                if icon:
                    pmi.icon = icon

                if pm.mode == 'PMENU':
                    try:
                        obj, _, prop_name = pmi.text.rpartition(".")
                        prop = type(
                            eval(obj, pme.context.globals)
                        ).bl_rna.properties[prop_name]
                        if prop.type != 'BOOLEAN' or len(prop.default_array) > 1:
                            text = "slot"
                            if prop.type == 'ENUM':
                                text = "''"
                            pmi.mode = 'CUSTOM'
                            pmi.text = (
                                "L.column().prop("
                                "%s, '%s', text=%s, icon=icon, "
                                "icon_value=icon_value)"
                            ) % (obj, prop_name, text)
                    except:
                        pass

            elif self.mode == 'PROP_ENUM_MENU':
                pmi.mode = 'CUSTOM'
                mo = re_prop.search(self.text)
                prop_path = mo.group(1) + mo.group(2)
                obj_path, _, prop_name = prop_path.rpartition(".")
                pmi.text = ("L.prop_menu_enum(%s, '%s', text=text, icon=icon)") % (
                    obj_path,
                    prop_name,
                )
                pmi.name, icon = gen_prop_name(mo, True)
                if icon:
                    pmi.icon = icon

            elif 'PROP_ENUM_EXPAND' in self.mode:
                pmi.mode = 'CUSTOM'
                mo = re_prop.search(self.text)
                prop_path = mo.group(1) + mo.group(2)
                obj_path, _, prop_name = prop_path.rpartition(".")
                lt = "row" if self.mode == 'PROP_ENUM_EXPAND_H' else "column"
                pmi.text = ("L.%s(align=True).prop(%s, '%s', expand=True)") % (
                    lt,
                    obj_path,
                    prop_name,
                )
                pmi.name, icon = gen_prop_name(mo, True)
                if icon:
                    pmi.icon = icon

            elif self.mode == 'ENUM':
                pmi.mode = 'CUSTOM'
                mo = re_operator.search(self.text)
                enum_args = find_enum_args(mo)
                pmi.text = "L.operator_enum(\"%s\", \"%s\")" % (
                    mo.group(1),
                    enum_args[0],
                )
                pmi.name = gen_op_name(mo)

            elif self.mode == 'ENUM_MENU':
                pmi.mode = 'CUSTOM'
                mo = re_operator.search(self.text)
                enum_args = find_enum_args(mo)
                pmi.text = (
                    "L.operator_menu_enum(\"%s\", \"%s\", " "text=text, icon=icon)"
                ) % (mo.group(1), enum_args[0])
                pmi.name = gen_op_name(mo)

            tag_redraw()

        get_prefs().update_tree()

        return {'CANCELLED'}


class WM_OT_pmi_edit(Operator):
    bl_idname = "wm.pmi_edit"
    bl_label = ""
    bl_description = "Use selected actions"
    bl_options = {'INTERNAL'}

    pm_item: IntProperty()
    auto: BoolProperty()
    add: BoolProperty()
    new_script: BoolProperty()
    mode: StringProperty(options={'SKIP_SAVE'})
    text: StringProperty(options={'SKIP_SAVE'})
    name: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.text:
            text = self.text

        else:
            bpy.ops.info.report_copy()
            text = context.window_manager.clipboard
            if text:
                bpy.ops.info.select_all(action='DESELECT')

            text = text.strip("\n")

            if len(text) > MAX_STR_LEN:
                message_box(W_PMI_LONG_CMD)
                return {'CANCELLED'}

        _edit_pmi(self, text, event)

        return {'CANCELLED'}


class WM_OT_pmi_edit_clipboard(Operator):
    bl_idname = "wm.pmi_edit_clipboard"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    pm_item: IntProperty()
    auto: BoolProperty()
    add: BoolProperty()
    new_script: BoolProperty()
    mode: StringProperty(options={'SKIP_SAVE'})
    text: StringProperty(options={'SKIP_SAVE'})
    name: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        text = context.window_manager.clipboard
        text = text.strip("\n")

        if len(text) > MAX_STR_LEN:
            message_box(W_PMI_LONG_CMD)
            return {'CANCELLED'}

        _edit_pmi(self, text, event)

        return {'CANCELLED'}


class WM_OT_pmi_edit_auto(Operator):
    bl_idname = "wm.pmi_edit_auto"
    bl_label = ""
    bl_description = "Use previous action"
    bl_options = {'INTERNAL'}

    ignored_operators = {
        "bpy.ops.pme.pm_edit",
        "bpy.ops.wm.pme_none",
        "bpy.ops.pme.none",
        "bpy.ops.info.reports_display_update",
        "bpy.ops.info.select_all",
        "bpy.ops.info.report_copy",
        "bpy.ops.view3d.smoothview",
    }

    pm_item: IntProperty()
    add: BoolProperty()
    new_script: BoolProperty()
    mode: StringProperty(options={'SKIP_SAVE'})
    text: StringProperty(options={'SKIP_SAVE'})
    name: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        info_area = SU.find_area("INFO")
        if not info_area:
            old_type = context.area.type
            context.area.type = 'INFO'

        override_args = SU.get_override_args(area="INFO")

        bpy.ops.wm.pme_none()

        with bpy.context.temp_override(**override_args):
            bpy.ops.info.select_all(action='SELECT')
            bpy.ops.info.report_copy()

        text = context.window_manager.clipboard

        idx2 = len(text)

        while True:
            idx2 = text.rfind("\n", 0, idx2)
            if idx2 == -1:
                text = ""
                break

            idx1 = text.rfind("\n", 0, idx2 - 1)
            line = text[idx1 + 1 : idx2]
            op = line[0 : line.find("(")]
            if line.startswith("Debug mode"):
                continue
            if op not in self.ignored_operators:
                text = line
                break

        with bpy.context.temp_override(**override_args):
            bpy.ops.info.select_all(action='DESELECT')

        text = text.strip("\n")

        _edit_pmi(self, text, event)

        if not info_area:
            context.area.type = old_type

        return {'CANCELLED'}


class PME_OT_pmi_menu(Operator):
    bl_idname = "pme.pmi_menu"
    bl_label = ""
    bl_description = "Slot tools"
    bl_options = {'INTERNAL'}

    draw_func = None

    idx: IntProperty()

    def draw_menu(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')
        self.__class__.draw_func(context, self.idx)

    def execute(self, context):
        if self.__class__.draw_func:
            context.window_manager.popup_menu(self.draw_menu)
            self.__class__.draw_func = None
        return {'FINISHED'}


class PME_OT_pmi_add(AddItemOperator, Operator):
    bl_idname = "pme.pmi_add"
    bl_label = "Add Slot"
    bl_description = "Add a slot"

    def get_collection(self):
        return get_prefs().selected_pm.pmis

    def finish(self, item):
        pm = get_prefs().selected_pm
        ed = pm.ed
        if ed:
            ed.on_pmi_add(pm, item)

        tag_redraw()


class PME_OT_pmi_move(MoveItemOperator, Operator):
    bl_idname = "pme.pmi_move"

    def get_collection(self):
        return get_prefs().selected_pm.pmis

    def get_icon(self, pmi, idx):
        pm = get_prefs().selected_pm
        ed = pm.ed
        return ed.get_pmi_icon(pm, pmi, idx) if ed else 'NONE'

    def get_title(self):
        pm = get_prefs().selected_pm
        pmi = pm.pmis[self.old_idx]
        return "Move " + shorten_str(pmi.name) if pmi.name.strip() else "Move Slot"

    def finish(self):
        pm = get_prefs().selected_pm
        ed = pm.ed
        if ed:
            ed.on_pmi_move(pm)

        tag_redraw()


class PME_OT_pmi_remove(RemoveItemOperator, Operator):
    bl_idname = "pme.pmi_remove"

    def get_collection(self):
        return get_prefs().selected_pm.pmis

    def finish(self):
        pr = get_prefs()
        pm = pr.selected_pm
        ed = pm.ed
        if ed:
            ed.on_pmi_remove(pm)

        pr.update_tree()
        tag_redraw()


class PME_OT_pmi_clear(ConfirmBoxHandler, Operator):
    bl_idname = "pme.pmi_clear"
    bl_label = "Clear"
    bl_description = "Clear the slot"
    bl_options = {'INTERNAL'}

    idx: IntProperty()

    def on_confirm(self, value):
        if not value:
            return

        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]

        pmi.text = ""
        pmi.name = ""
        pmi.icon = ""
        pmi.mode = 'EMPTY'

        ed = pm.ed
        if ed:
            ed.on_pmi_remove(pm)

        pr.update_tree()
        tag_redraw()
        return {'FINISHED'}


class PME_OT_pmi_cmd_generate(Operator):
    bl_idname = "pme.pmi_cmd_generate"
    bl_label = "Generate Command"
    bl_description = "Generate command"

    clear: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        data = pr.pmi_data

        if self.clear:
            keys = list(data.kmi.properties.keys())
            for k in keys:
                del data.kmi.properties[k]

        if pr.mode == 'PMI' and data.mode in MODAL_CMD_MODES:
            op_idname, _, pos_args = operator_utils.find_operator(data.cmd)

            parsed_ctx, parsed_undo = operator_utils.parse_pos_args(pos_args)

            C_exec = data.cmd_ctx or parsed_ctx
            C_undo = data.cmd_undo if (data.cmd_undo is not None) else parsed_undo

            args = []
            for k in data.kmi.properties.keys():
                v = getattr(data.kmi.properties, k)
                value = to_py_value(data.kmi, k, v)
                if value is None or isinstance(value, dict) and not value:
                    continue
                args.append("%s=%s" % (k, repr(value)))

            pos_args_new = []

            if C_exec == 'INVOKE_DEFAULT':
                if not C_undo:
                    pos_args_new.append(repr(C_undo))
            else:
                pos_args_new.append(repr(C_exec))
                if C_undo:
                    pos_args_new.append(repr(C_undo))

            call_args = ", ".join(pos_args_new + args)
            cmd = f"bpy.ops.{op_idname}({call_args})"

            if DBG_CMD_EDITOR:
                data.cmd = cmd
            else:
                data["cmd"] = cmd

        return {'PASS_THROUGH'}


class WM_OT_pmi_data_edit(Operator):
    bl_idname = "wm.pmi_data_edit"
    bl_label = "Edit Slot"
    bl_description = "Edit the slot\n" "Enter - OK\n" "Esc - Cancel"
    bl_options = {'INTERNAL'}

    idx: IntProperty()
    ok: BoolProperty(options={'SKIP_SAVE'})
    hotkey: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        tpr = temp_prefs()

        if self.hotkey:
            if pr.mode != 'PMI' or self.ok and pr.pmi_data.has_errors():
                return {'PASS_THROUGH'}

        pm = pr.selected_pm
        data = pr.pmi_data
        data_mode = data.mode
        if data_mode in MODAL_CMD_MODES:
            data_mode = 'COMMAND'

        if self.ok:
            pr.leave_mode()
            self.idx = pme.context.edit_item_idx
            pmi = pm.pmis[self.idx]

            if not data.has_errors():
                if not pmi.name and not data.name and data.sname:
                    data.name = data.sname

                pmi.mode = data.mode
                if data_mode == 'COMMAND':
                    pmi.text = data.cmd

                elif data_mode == 'PROP':
                    pmi.text = data.prop

                elif data_mode == 'MENU':
                    pmi.text = data.menu

                    sub_pm = (
                        pmi.text and pmi.text in pr.pie_menus and pr.pie_menus[pmi.text]
                    )
                    if (
                        sub_pm
                        and sub_pm.mode in {'DIALOG', 'RMENU'}
                        and data.expand_menu
                    ):
                        from ...ui.utils import get_pme_menu_class

                        if sub_pm.mode == 'RMENU':
                            get_pme_menu_class(pmi.text)

                        if data.use_frame:
                            pmi.text = F_EXPAND + pmi.text

                        pmi.text = F_EXPAND + pmi.text

                elif data_mode == 'HOTKEY':
                    pmi.text = keymap_helper.to_hotkey(
                        data.key,
                        data.ctrl,
                        data.shift,
                        data.alt,
                        data.oskey,
                        data.key_mod,
                    )

                elif data_mode == 'CUSTOM':
                    pmi.text = data.custom

            pmi.name = data.name
            pmi.icon = data.icon

            ed = pm.ed
            if ed:
                ed.on_pmi_edit(pm, pmi)

            pr.update_tree()

            tag_redraw()
            return {'FINISHED'}

        if self.idx == -1:
            data.info()
            pr.leave_mode()
            tag_redraw()
            return {'FINISHED'}

        pmi = pm.pmis[self.idx]
        pme.context.edit_item_idx = self.idx
        pr.enter_mode('PMI')

        tpr.update_pie_menus()

        ed = pm.ed
        if ed:
            ed.on_pmi_pre_edit(pm, pmi, data)

        data.check_pmi_errors(context)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.hotkey and (
            not context.area
            or context.area.type != 'PREFERENCES'
            or get_prefs().mode != 'PMI'
        ):
            return {'PASS_THROUGH'}

        return self.execute(context)


class PME_OT_pmi_copy(Operator):
    bl_idname = "pme.pmi_copy"
    bl_label = "Copy Slot"
    bl_description = "Copy the slot"
    bl_options = {'INTERNAL'}

    idx: IntProperty(default=-1, options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm

        pmi = pm.pmis[self.idx]

        pr.pmi_clipboard.copy(pm, pmi)
        return {'FINISHED'}


class PME_OT_pmi_paste(Operator):
    bl_idname = "pme.pmi_paste"
    bl_label = "Paste Slot"
    bl_description = "Paste the slot"
    bl_options = {'INTERNAL'}

    idx: IntProperty(default=-1, options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]
        cb = pr.pmi_clipboard

        cb.paste(pm, pmi)

        ed = pm.ed
        if ed:
            ed.on_pmi_paste(pm, pmi)

        pr.update_tree()
        tag_redraw()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        pr = get_prefs()
        pm = pr.selected_pm
        ed = pm.ed
        if not ed:
            return False
        cb = pr.pmi_clipboard
        return (
            cb.has_data()
            and cb.mode in ed.supported_slot_modes
            and cb.pm_mode in ed.supported_paste_modes
        )
