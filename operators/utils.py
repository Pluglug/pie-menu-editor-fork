# operators/utils.py - Utility operators for PME
# LAYER = "operators"
#
# Moved from: operators/__init__.py (Phase 2-C operators reorganization)
#
# Contains:
#   - WM_OT_pme_none: Empty operator (does nothing)
#   - PME_OT_preview: Preview pie menu
#   - PME_OT_docs: Open documentation
#   - PME_OT_debug_mode_toggle: Toggle debug mode
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ..ui import tag_redraw
from ..constants import I_DEBUG


class WM_OT_pme_none(Operator):
    bl_idname = "wm.pme_none"
    bl_label = ""
    bl_options = {'INTERNAL'}

    def execute(self, context):
        return {'FINISHED'}


class PME_OT_preview(Operator):
    bl_idname = "pme.preview"
    bl_label = ""
    bl_description = "Preview"
    bl_options = {'INTERNAL'}

    pie_menu_name: StringProperty()

    def execute(self, context):
        bpy.ops.wm.pme_user_pie_menu_call(
            'INVOKE_DEFAULT', pie_menu_name=self.pie_menu_name, invoke_mode='RELEASE'
        )
        return {'FINISHED'}


class PME_OT_docs(Operator):
    bl_idname = "pme.docs"
    bl_label = "Pie Menu Editor Documentation"
    bl_description = "Documentation"
    bl_options = {'INTERNAL'}

    id: StringProperty(options={'SKIP_SAVE'})
    url: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        if self.id:
            self.url = ("https://pluglug.github.io/pme-docs/") + self.id
        bpy.ops.wm.url_open(url=self.url)
        return {'FINISHED'}


class PME_OT_debug_mode_toggle(Operator):
    bl_idname = "pme.debug_mode_toggle"
    bl_label = "Toggle Debug Mode"
    bl_description = "Toggle debug mode"

    def execute(self, context):
        bpy.app.debug_wm = not bpy.app.debug_wm
        mode = "Off"
        if bpy.app.debug_wm:
            mode = "On"
        self.report({'INFO'}, I_DEBUG % mode)
        tag_redraw()
        return {'CANCELLED'}
