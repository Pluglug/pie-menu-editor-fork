# operators/script.py - Script file operations
# LAYER = "operators"
#
# Moved from: operators/__init__.py (Phase 2-C operators reorganization)
#
# Contains:
#   - PME_OT_script_open: Open external Python script for menu items
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false

LAYER = "operators"

import os

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, EnumProperty

from ..addon import get_prefs, ADDON_PATH
from ..infra.io import get_user_scripts_dir


class PME_OT_script_open(Operator):
    bl_idname = "pme.script_open"
    bl_label = "Open Script"
    bl_description = (
        "Command tab:\n"
        "  Execute external script when the user clicks the button\n"
        "Custom tab:\n"
        "  Use external script to draw custom layout of widgets"
    )
    bl_options = {'INTERNAL'}

    filename_ext = ".py"
    filepath: StringProperty(subtype='FILE_PATH', default="")
    filter_glob: StringProperty(default="*.py", options={'HIDDEN'})
    idx: IntProperty(default=-1, options={'SKIP_SAVE'})
    mode: EnumProperty(
        name="Tab",
        items=(
            ('COMMAND', "Command", ""),
            ('CUSTOM', "Custom", ""),
        ),
    )

    def draw(self, context):
        if self.idx != -1:
            col = self.layout.column(align=True)
            col.label(text="Tab:")
            col.prop(self, "mode", text="")

    def execute(self, context):
        pr = get_prefs()

        filepath = os.path.normpath(self.filepath)
        pr.scripts_filepath = filepath

        if filepath.startswith(ADDON_PATH):
            filepath = os.path.relpath(filepath, ADDON_PATH)

        filename = os.path.basename(filepath)
        filename, _, _ = filename.rpartition(".")
        name = filename.replace("_", " ").strip().title()

        filepath = filepath.replace("\\", "/")
        cmd = "execute_script(\"%s\")" % filepath

        pm = pr.selected_pm
        if self.idx == -1:
            pm.poll_cmd = "return " + cmd

        else:
            pmi = pm.pmis[self.idx]

            if pr.mode == 'PMI':
                pr.pmi_data.mode = self.mode
                if pr.pmi_data.mode == 'COMMAND':
                    pr.pmi_data.cmd = cmd
                elif pr.pmi_data.mode == 'CUSTOM':
                    pr.pmi_data.custom = cmd

                pr.pmi_data.sname = name
            else:
                pmi.mode = self.mode
                pmi.text = cmd
                pmi.name = name

        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.filepath:
            stored_path = get_prefs().scripts_filepath
            # Use user scripts directory if no stored path or stored path doesn't exist
            if not stored_path or not os.path.exists(stored_path):
                self.filepath = get_user_scripts_dir(create=True)
            else:
                self.filepath = stored_path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
