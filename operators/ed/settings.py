# operators/ed/settings.py - Settings menu operators
# LAYER = "operators"
#
# Moved from: editors/base.py (Phase 5-A operator separation)

LAYER = "operators"

import bpy
from bpy.types import Menu
from ...addon import ic
from ...core.constants import PME_SCREEN, PME_TEMP_SCREEN, SPACE_ITEMS
from ...ui.layout import lh


class PME_MT_header_menu_set(Menu):
    bl_label = "Menu"

    def draw(self, context):
        lh.save()
        lh.lt(self.layout)

        for id, name, _, icon, _ in SPACE_ITEMS:
            lh.operator(
                "pme.exec",
                name,
                icon,
                cmd=(
                    "d =get_prefs().pmi_data; "
                    "d.mode = 'CUSTOM'; "
                    "d.custom = 'header_menu([\"{0}\"])'; "
                    "d.sname = '{1}'"
                ).format(id, name, icon),
            )

        lh.sep()
        lh.operator(
            "pme.exec",
            "Current",
            'BLANK1',
            cmd=(
                "d =get_prefs().pmi_data; "
                "d.mode = 'CUSTOM'; "
                "d.custom = 'header_menu([\"CURRENT\"])'; "
                "d.sname = 'Current Area'"
            ),
        )

        lh.restore()


class PME_MT_screen_set(Menu):
    bl_label = "Menu"

    def draw(self, context):
        lh.save()
        lh.lt(self.layout)

        icons = {
            "Layout": 'MENU_PANEL',
            "Modeling": 'VIEW3D',
            "Sculpting": 'SCULPTMODE_HLT',
            "UV Editing": 'UV',
            "Texture Paint": 'TPAINT_HLT',
            "Shading": 'SHADING_RENDERED',
            "Animation": 'NLA',
            "Rendering": 'RENDER_ANIMATION',
            "Compositing": 'NODETREE',
            "Scripting": 'TEXT',
            "3D View Full": 'FULLSCREEN',
            "Default": 'VIEW3D',
            "Game Logic": 'AUTO',
            "Motion Tracking": 'RENDER_ANIMATION',
            "Video Editing": 'SEQUENCE',
        }

        for name in sorted(bpy.data.workspaces.keys()):
            if (
                name == "temp"
                or name.startswith(PME_TEMP_SCREEN)
                or name.startswith(PME_SCREEN)
            ):
                continue
            icon = icons.get(name, 'LAYER_USED')

            lh.operator(
                "pme.exec",
                name,
                icon,
                cmd=(
                    "d =get_prefs().pmi_data; "
                    "d.mode = 'COMMAND'; "
                    "d.cmd = 'bpy.ops.pme.screen_set(name=\"{0}\")'; "
                    "d.sname = '{0}'; "
                    "d.icon = '{1}'"
                ).format(name, icon),
            )

        lh.restore()


class PME_MT_brush_set(Menu):
    bl_label = "Menu"

    def draw(self, context):
        brushes = bpy.data.brushes
        lh.save()

        def add_brush(col, brush):
            brush = brushes[brush]

            col.operator(
                "pme.exec",
                text=brush.name, icon=ic('LAYER_ACTIVE')).cmd = (
                "d =get_prefs().pmi_data; "
                "d.mode = 'COMMAND'; "
                "d.cmd = 'paint_settings(C).brush = D.brushes[\"{0}\"]'; "
                "d.sname = '{0}'; "
                "d.icon = '{1}'"
            ).format(brush.name, 'BRUSH_DATA')

        image_brushes = []
        sculpt_brushes = []
        vertex_brushes = []
        weight_brushes = []
        for name in sorted(brushes.keys()):
            brush = brushes[name]
            brush.use_paint_image and image_brushes.append(brush.name)
            brush.use_paint_sculpt and sculpt_brushes.append(brush.name)
            brush.use_paint_vertex and vertex_brushes.append(brush.name)
            brush.use_paint_weight and weight_brushes.append(brush.name)

        row = self.layout.row()
        col_image = row.column()
        col_image.label(text="Image", icon=ic('TPAINT_HLT'))
        col_image.separator()
        for brush in image_brushes:
            add_brush(col_image, brush)

        col_vertex = row.column()
        col_vertex.label(text="Vertex", icon=ic('VPAINT_HLT'))
        col_vertex.separator()
        for brush in vertex_brushes:
            add_brush(col_vertex, brush)

        col_weight = row.column()
        col_weight.label(text="Weight", icon=ic('WPAINT_HLT'))
        col_weight.separator()
        for brush in weight_brushes:
            add_brush(col_weight, brush)

        col_sculpt = row.column()
        col_sculpt.label(text="Sculpt", icon=ic('SCULPTMODE_HLT'))
        col_sculpt.separator()
        for brush in sculpt_brushes:
            add_brush(col_sculpt, brush)

        lh.restore()
