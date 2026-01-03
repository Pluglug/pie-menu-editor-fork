# operators/ed/poll.py - Poll condition operators and menus
# LAYER = "operators"
#
# Moved from: editors/base.py (Phase 5-A operator separation)

LAYER = "operators"

import bpy
from bpy.types import Menu, Object, Operator
from ...addon import ic
from ...operators import PME_OT_exec, PME_OT_script_open


class PME_MT_poll_mesh(Menu):
    bl_label = "Mesh Select Mode"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            PME_OT_exec.bl_idname, text="Vertex Select Mode", icon=ic('VERTEXSEL')
        ).cmd = (
            "get_prefs().selected_pm.poll_cmd = "
            "'return C.scene.tool_settings.mesh_select_mode[0]'"
        )
        layout.operator(
            PME_OT_exec.bl_idname, text="Edge Select Mode", icon=ic('EDGESEL')
        ).cmd = (
            "get_prefs().selected_pm.poll_cmd = "
            "'return C.scene.tool_settings.mesh_select_mode[1]'"
        )
        layout.operator(
            PME_OT_exec.bl_idname, text="Face Select Mode", icon=ic('FACESEL')
        ).cmd = (
            "get_prefs().selected_pm.poll_cmd = "
            "'return C.scene.tool_settings.mesh_select_mode[2]'"
        )


class PME_MT_poll_object(Menu):
    bl_label = "Active Object Type"

    def draw(self, context):
        layout = self.layout

        icon = ic('NODE_SEL')
        for item in sorted(
            Object.bl_rna.properties["type"].enum_items,
            key=lambda item: item.name,
        ):
            layout.operator(
                PME_OT_exec.bl_idname, text=item.name + " Object", icon=icon
            ).cmd = (
                "get_prefs().selected_pm.poll_cmd = "
                "\"return C.active_object and "
                "C.active_object.type == '%s'\""
            ) % item.identifier


class PME_MT_poll_workspace(Menu):
    bl_label = "Active Workspace"

    def draw(self, context):
        layout = self.layout

        icon = ic('WORKSPACE')
        for item in sorted(bpy.data.workspaces, key=lambda item: item.name):
            layout.operator(PME_OT_exec.bl_idname, text=item.name, icon=icon).cmd = (
                "get_prefs().selected_pm.poll_cmd = "
                "\"return C.workspace.name == '%s'\""
            ) % item.name


class PME_OT_poll_specials_call(Operator):
    bl_idname = "pme.poll_specials_call"
    bl_label = "Menu"
    bl_description = "Menu"
    bl_options = {'INTERNAL'}

    def _poll_specials_call_menu(self, menu, context):
        layout = menu.layout
        layout.operator_context = 'INVOKE_DEFAULT'

        layout.operator(
            PME_OT_script_open.bl_idname,
            text="External Script",
            icon=ic('FILE_FOLDER'),
        )

        layout.separator()

        layout.label(text="Examples:", icon=ic('NODE_SEL'))
        layout.menu("PME_MT_poll_mesh", icon=ic('VERTEXSEL'))
        layout.menu("PME_MT_poll_object", icon=ic('OBJECT_DATAMODE'))
        layout.menu("PME_MT_poll_workspace", icon=ic('WORKSPACE'))

        layout.separator()

        layout.operator(PME_OT_exec.bl_idname, text="Reset", icon=ic('X')).cmd = (
            "get_prefs().selected_pm.poll_cmd = 'return True'"
        )

    def execute(self, context):
        context.window_manager.popup_menu(self._poll_specials_call_menu)
        return {'FINISHED'}
