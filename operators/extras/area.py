# operators/extras/area.py - Area and Window management operators for PME
# LAYER = "operators"
#
# Moved from: extra_operators.py (Phase 2-C operators reorganization)
#
# Contains:
#   - PME_OT_window_auto_close: Close temp windows when clicking outside
#   - PME_OT_area_move: Move area edge by delta
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, IntProperty

from ...addon import get_prefs
from ...core import constants as CC
from ...core.constants import PME_TEMP_SCREEN


class PME_OT_window_auto_close(Operator):
    bl_idname = "pme.window_auto_close"
    bl_label = "Close Temp Windows (PME)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        # Refactor_TODO: Revisit roaoao's original code and consider refactoring it.
        #                If you do ctx_override, use temp_override

        # if context.window.screen.name.startswith(PME_SCREEN) or \
        #         context.window.screen.name.startswith(PME_TEMP_SCREEN):
        #     bpy.ops.wm.window_close(dict(window=context.window))

        # return {'PASS_THROUGH'}

        if not context.window.screen.name.startswith(PME_TEMP_SCREEN):
            # delete_flag = False
            # window = context.window

            wm = context.window_manager
            # used_pme_screens = set()
            for w in wm.windows:
                if w.screen.name.startswith(PME_TEMP_SCREEN):
                    with context.temp_override(window=w):
                        bpy.ops.screen.new()

                    bpy.ops.pme.timeout(
                        cmd=f"p = {w.as_pointer()}; "
                            "w = [w for w in C.window_manager.windows "
                            "if w.as_pointer() == p][0]; "
                            "oc = C.temp_override(window=w); oc.__enter__(); "
                            "bpy.ops.wm.window_close(); oc.__exit__()")

                # elif w.screen.name.startswith(PME_SCREEN):
                #     used_pme_screens.add(w.screen.name)

            # screens = [w.screen for w in wm.windows]

            # for s in bpy.data.screens:
            #     if s.name.startswith(PME_TEMP_SCREEN):
            #         delete_flag = True
            #         bpy.ops.screen.delete(dict(window=window, screen=s))

            #     elif s.name.startswith(PME_SCREEN) and \
            #             s.name not in used_pme_screens:
            #         delete_flag = True
            #         bpy.ops.screen.delete(dict(window=window, screen=s))

            # if delete_flag:
            #     for s, w in zip(screens, wm.windows):
            #         bpy.ops.pme.screen_set(
            #             dict(window=w, screen=s),
            #             'INVOKE_DEFAULT', name=s.name)

            get_prefs().enable_window_kmis(False)

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        return self.execute(context)


class PME_OT_area_move(Operator):
    bl_idname = "pme.area_move"
    bl_label = "Move Area"
    bl_description = "Move area"
    bl_options = {'INTERNAL'}

    area: EnumProperty(
        name="Area Type",
        description="Area type",
        items=CC.AreaEnumHelper.gen_items_with_current,
        options={'SKIP_SAVE'},
    )
    edge: EnumProperty(
        name="Area Edge",
        description="Edge of the area to move",
        items=(
            ('TOP', "Top", "", 'TRIA_TOP_BAR', 0),
            ('BOTTOM', "Bottom", "", 'TRIA_BOTTOM_BAR', 1),
            ('LEFT', "Left", "", 'TRIA_LEFT_BAR', 2),
            ('RIGHT', "Right", "", 'TRIA_RIGHT_BAR', 3),
        ),
        options={'SKIP_SAVE'},
    )
    delta: IntProperty(
        name="Delta", description="Delta", default=300, options={'SKIP_SAVE'}
    )
    move_cursor: BoolProperty(
        name="Move Cursor", description="Move cursor", options={'SKIP_SAVE'}
    )

    def get_target_area(self, context):
        if self.area == 'CURRENT':
            return context.area

        for area in reversed(context.screen.areas):
            if area.ui_type == self.area:
                return area

        return None

    def calculate_cursor_positions(self, area, event):
        mx, my = event.mouse_x, event.mouse_y
        x, y = mx, my

        if self.edge == 'TOP':
            y = area.y + area.height
            my += self.delta * self.move_cursor
        elif self.edge == 'BOTTOM':
            y = area.y
            my += self.delta * self.move_cursor
        elif self.edge == 'RIGHT':
            x = area.x + area.width
            mx += self.delta * self.move_cursor
        elif self.edge == 'LEFT':
            x = area.x
            mx += self.delta * self.move_cursor

        return x, y, mx, my

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        area = self.get_target_area(context)
        if not area:
            self.report({'WARNING'}, "Target area not found")
            return {'CANCELLED'}

        x, y, mx, my = self.calculate_cursor_positions(area, event)
        bpy.context.window.cursor_warp(x, y)

        bpy.ops.pme.timeout(
            delay=0.0001,
            cmd=(
                "bpy.ops.screen.area_move(x=%d, y=%d, delta=%d);"
                "bpy.context.window.cursor_warp(%d, %d);"
            ) % (x, y, self.delta, mx, my)
        )
        return {'FINISHED'}
