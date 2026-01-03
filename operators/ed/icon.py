# operators/ed/icon.py - Icon selection and toggle operators
# LAYER = "operators"
#
# Moved from: editors/base.py (Phase 5-A operator separation)

LAYER = "operators"

import bpy
from ...addon import get_prefs
from ...core import constants as CC
from ...bl_utils import bp, message_box
from ...ui import tag_redraw
from ... import pme


class WM_OT_pmi_icon_tag_toggle(bpy.types.Operator):
    bl_idname = "wm.pmi_icon_tag_toggle"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    idx: bpy.props.IntProperty()
    tag: bpy.props.StringProperty()

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pr.pmi_data if self.idx < 0 else pm.pmis[self.idx]

        icon, icon_only, hidden, use_cb = pmi.extract_flags()
        if self.tag == CC.F_ICON_ONLY:
            if not icon or icon == 'NONE':
                icon = 'FILE_HIDDEN'
            icon_only = not icon_only

        elif self.tag == CC.F_HIDDEN:
            hidden = not hidden

        elif self.tag == CC.F_CB:
            use_cb = not use_cb

        if icon_only:
            icon = CC.F_ICON_ONLY + icon
        if hidden:
            icon = CC.F_HIDDEN + icon
        if use_cb:
            icon = CC.F_CB + icon

        pmi.icon = icon

        tag_redraw()
        return {'FINISHED'}


class WM_OT_pmi_icon_select(bpy.types.Operator):
    bl_idname = "wm.pmi_icon_select"
    bl_label = "Select Icon"
    bl_description = "Select an icon\n" "Esc - Cancel"
    bl_options = {'INTERNAL'}

    idx: bpy.props.IntProperty()
    icon: bpy.props.StringProperty(options={'SKIP_SAVE'})
    hotkey: bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()

        if self.hotkey and pr.mode != 'ICONS':
            return {'PASS_THROUGH'}

        if self.idx == -1:  # Cancel
            pr.leave_mode()
            tag_redraw()
            return {'FINISHED'}

        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]

        data = pmi
        if pr.is_edit_mode():
            data = pr.pmi_data

        if not self.icon:
            if data.mode == 'PROP':
                text = data.prop if hasattr(data, "prop") else data.text
                bl_prop = bp.get(text)
                if bl_prop and bl_prop.icon != 'NONE':
                    message_box("Unable to change icon for this property")
                    return {'FINISHED'}
            pme.context.edit_item_idx = self.idx
            pr.enter_mode('ICONS')

            tag_redraw()
            return {'FINISHED'}
        else:
            icon = self.icon
            _, icon_only, hidden, use_cb = data.extract_flags()
            if icon_only:
                icon = CC.F_ICON_ONLY + icon
            if hidden:
                icon = CC.F_HIDDEN + icon
            if use_cb:
                icon = CC.F_CB + icon
            data.icon = icon if self.icon != 'NONE' else ""
            if pr.mode == 'ICONS':
                pr.leave_mode()

        if not pr.is_edit_mode():
            ed = pm.ed
            if ed:
                ed.on_pmi_icon_edit(pm, pmi)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.hotkey and (
            not context.area
            or context.area.type != 'PREFERENCES'
            or get_prefs().mode != 'ICONS'
        ):
            return {'PASS_THROUGH'}

        return self.execute(context)
