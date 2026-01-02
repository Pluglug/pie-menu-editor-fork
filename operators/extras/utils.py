# operators/extras/utils.py - Utility operators for PME
# LAYER = "operators"
#
# Moved from: extra_operators.py (Phase 2-C operators reorganization)
#
# Contains:
#   - PME_OT_dummy: Empty operator that does nothing
#   - PME_OT_modal_dummy: Modal operator for simple confirmations
#   - PME_OT_none: Operator that returns CANCELLED or PASS_THROUGH
#   - PME_OT_screen_set: Set screen/workspace by name
#   - PME_OT_clipboard_copy: Copy text to clipboard
#
# Also includes save_pre_handler for clearing temp screens before save.
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, StringProperty
from bpy.app.handlers import persistent

from ...bl_utils import area_header_text_set
from ...core.constants import PME_TEMP_SCREEN


class PME_OT_dummy(Operator):
    bl_idname = "pme.dummy"
    bl_label = ""
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return {'FINISHED'}


class PME_OT_modal_dummy(Operator):
    bl_idname = "pme.modal_dummy"
    bl_label = "Dummy Modal"

    message: StringProperty(
        name="Message",
        options={'SKIP_SAVE'},
        default="OK: Enter/LClick, Cancel: Esc/RClick)",
    )

    def modal(self, context, event):
        if event.value == 'PRESS':
            if event.type in {'ESC', 'RIGHTMOUSE'}:
                area_header_text_set()
                return {'CANCELLED'}
            elif event.type in {'RET', 'LEFTMOUSE'}:
                area_header_text_set()
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        area_header_text_set(self.message)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class PME_OT_none(Operator):
    bl_idname = "pme.none"
    bl_label = ""
    bl_options = {'INTERNAL'}

    pass_through: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        return {'PASS_THROUGH' if self.pass_through else 'CANCELLED'}

    def invoke(self, context, event):
        return {'PASS_THROUGH' if self.pass_through else 'CANCELLED'}


class PME_OT_screen_set(Operator):
    bl_idname = "pme.screen_set"
    bl_label = "Set Screen/Workspace By Name"

    name: StringProperty(
        name="Screen Layout/Workspace Name",
        description="Screen layout/workspace name",
    )

    def execute(self, context):
        if self.name not in bpy.data.workspaces:
            return {'CANCELLED'}

        if context.screen.show_fullscreen:
            bpy.ops.screen.back_to_previous()

        if context.screen.show_fullscreen:
            bpy.ops.screen.back_to_previous()

        context.window.workspace = bpy.data.workspaces[self.name]

        return {'FINISHED'}


class PME_OT_clipboard_copy(Operator):
    bl_idname = "pme.clipboard_copy"
    bl_label = "Copy"
    bl_options = {'INTERNAL'}

    text: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        context.window_manager.clipboard = self.text
        return {'FINISHED'}


@persistent
def save_pre_handler(_):
    for s in bpy.data.screens:
        if s.name.startswith(PME_TEMP_SCREEN) and s.users > 0:
            s.user_clear()


def register():
    bpy.app.handlers.save_pre.append(save_pre_handler)


def unregister():
    if save_pre_handler in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(save_pre_handler)
