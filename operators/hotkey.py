# operators/hotkey.py - Hotkey management operators
# LAYER = "operators"
#
# Moved from: operators/__init__.py (Phase 2-C operators reorganization)
#
# Contains:
#   - WM_OT_pme_hotkey_call: Execute operator by hotkey string
#   - PME_OT_pm_chord_add: Add or remove chord to menu
#   - PME_OT_pm_hotkey_remove: Remove hotkey from menu
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty

from ..addon import get_prefs
from .. import keymap_helper


class WM_OT_pme_hotkey_call(Operator):
    bl_idname = "wm.pme_hotkey_call"
    bl_label = "Hotkey"

    hotkey: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        keymap_helper.run_operator_by_hotkey(context, self.hotkey)
        return {'FINISHED'}


class PME_OT_pm_chord_add(Operator):
    bl_idname = "pme.pm_chord_add"
    bl_label = "Add or Remove Chord"
    bl_description = "Add or remove chord"
    bl_options = {'INTERNAL'}

    add: BoolProperty(default=True, options={'SKIP_SAVE'})

    def execute(self, context):
        pm = get_prefs().selected_pm
        if self.add:
            pm.chord = 'A'
        else:
            pm.chord = 'NONE'

        return {'FINISHED'}


class PME_OT_pm_hotkey_remove(Operator):
    bl_idname = "pme.pm_hotkey_remove"
    bl_label = ""
    bl_description = "Remove the hotkey"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        pm = get_prefs().selected_pm
        return pm and pm.key != 'NONE'

    def execute(self, context):
        pm = get_prefs().selected_pm
        pm.key = 'NONE'
        pm.ctrl = False
        pm.shift = False
        pm.alt = False
        pm.oskey = False
        pm.key_mod = 'NONE'
        pm.update_keymap_item(context)

        return {'FINISHED'}

    def invoke(self, context, event):
        if event.shift:
            if 'FINISHED' in bpy.ops.pme.pm_hotkey_convert():
                return {'FINISHED'}

        return self.execute(context)
