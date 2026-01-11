# pyright: reportInvalidTypeForm=false
# operators/ed/pm.py - Pie Menu (PM) management operators
# LAYER = "operators"
#
# Moved from: editors/base.py (Phase 5-A operator separation)

LAYER = "operators"

import bpy
from bpy import app
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Menu, Operator
from ...addon import get_prefs, ic
from ...core.constants import ARROW_ICONS, ED_DATA
from ...bl_utils import PME_OT_message_box
from ...ui import tag_redraw
from ...ui.layout import lh, operator, draw_pme_layout
from ...ui.utils import toggle_menu
from ...operators import (
    popup_dialog_pie,
    WM_OT_pm_select,
    PME_OT_pm_search_and_select,
    PME_OT_debug_mode_toggle,
)

# Import from pmi.py for operator references
from .pmi import WM_OT_pmi_edit, WM_OT_pmi_edit_clipboard, WM_OT_pmi_edit_auto


class PME_MT_select_menu(Menu):
    bl_label = "Select Menu"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'

        operator(
            layout,
            WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )

        operator(layout, PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM')


class PME_MT_pm_new(Menu):
    bl_label = "New"

    def draw_items(self, layout):
        lh.lt(layout)

        for id, name, icon in ED_DATA:
            lh.operator(PME_OT_pm_add.bl_idname, name, icon, mode=id)

    def draw(self, context):
        self.draw_items(self.layout)


class PME_OT_pm_add(Operator):
    bl_idname = "wm.pm_add"
    bl_label = ""
    bl_description = "Add an item"
    bl_options = {'INTERNAL'}

    mode: StringProperty()
    name: StringProperty(options={'SKIP_SAVE'})
    # Phase 9-X: Extend parameters passed directly (not parsed from name)
    extend_target: StringProperty(options={'SKIP_SAVE'})
    extend_position: IntProperty(default=0, options={'SKIP_SAVE'})

    def _draw(self, menu, context):
        PME_MT_pm_new.draw_items(self, menu.layout)

    def execute(self, context):
        if not self.mode:
            context.window_manager.popup_menu(
                self._draw, title=PME_OT_pm_add.bl_description
            )
        else:
            pr = get_prefs()
            # Phase 9-X: Pass extend parameters directly to add_pm
            pr.add_pm(
                self.mode,
                self.name or None,
                extend_target=self.extend_target,
                extend_position=self.extend_position,
            )
            pr.update_tree()
            tag_redraw()

        return {'CANCELLED'}


class PME_OT_pm_edit(Operator):
    bl_idname = "pme.pm_edit"
    bl_label = "Edit Menu (PME)"
    bl_description = "Edit the menu"

    auto: BoolProperty(default=True, options={'SKIP_SAVE'})
    clipboard: BoolProperty(options={'SKIP_SAVE'})
    mode: StringProperty(options={'SKIP_SAVE'})
    text: StringProperty(options={'SKIP_SAVE'})
    name: StringProperty(options={'SKIP_SAVE'})

    def _draw_pm(self, menu, context):
        pm = get_prefs().selected_pm

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        for idx, pmi in enumerate(pm.pmis):
            text, icon, *_ = pmi.parse()
            if pmi.mode == 'EMPTY':
                text = ". . ."

            lh.operator(
                self.op_bl_idname,
                text,
                ARROW_ICONS[idx],
                pm_item=idx,
                mode=self.mode,
                text=self.text,
                name=self.name,
                add=False,
                new_script=False,
            )

        lh.sep()

        lh.operator(
            WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )

        lh.operator(PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM')

    def _draw_rm(self, menu, context):
        pm = get_prefs().selected_pm

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')
        row = lh.row()
        lh.column(row)
        lh.label(pm.name, icon='MOD_BOOLEAN')
        lh.operator(
            WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )
        lh.operator(PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM')
        lh.sep()

        idx = -1
        for pmi in pm.pmis:
            idx += 1
            name = pmi.name
            icon = pmi.parse_icon()

            if pmi.mode == 'EMPTY':
                if pmi.text == "column":
                    lh.operator(
                        self.op_bl_idname,
                        "Add Item",
                        'ADD',
                        pm_item=idx,
                        mode=self.mode,
                        text=self.text,
                        name=self.name,
                        add=True,
                        new_script=False,
                    )
                    lh.column(row)
                    lh.label(" ")
                    lh.label(" ")
                    lh.label(" ")
                    lh.sep()

                elif pmi.text == "":
                    lh.sep()

                elif pmi.text == "spacer":
                    lh.label(" ")

                elif pmi.text == "label":
                    lh.label(name, icon=icon)

                continue

            lh.operator(
                self.op_bl_idname,
                name,
                icon,
                pm_item=idx,
                mode=self.mode,
                text=self.text,
                name=self.name,
                add=False,
                new_script=False,
            )

        lh.operator(
            self.op_bl_idname,
            "Add Item",
            'ADD',
            pm_item=-1,
            mode=self.mode,
            text=self.text,
            name=self.name,
            add=True,
            new_script=False,
        )

    def _draw_debug(self, menu, context):
        lh.lt(menu.layout)
        lh.operator(PME_OT_debug_mode_toggle.bl_idname, "Enable Debug Mode")

    def _draw_pd(self, menu, context):
        pr = get_prefs()
        pm = pr.selected_pm
        ed = pm.ed

        layout = menu.layout.menu_pie()
        layout.separator()
        layout.separator()
        column = layout.column(align=True)
        row = column.box().row(align=True)
        row.label(text=pm.name, icon=ic(ed.icon if ed else 'NONE'))
        sub = row.row(align=True)
        sub.alignment = 'LEFT'
        operator(
            sub,
            PME_OT_message_box.bl_idname,
            emboss=False,
            title="Hotkeys",
            icon=ic('INFO'),
            message="Ctrl+LMB - Add Button to the Right\n"
            "Ctrl+Shift+LMB - Add Button to the Left",
        )
        sub.menu("PME_MT_select_menu", text="", icon=ic('COLLAPSEMENU'))

        col = column.box().column(align=True)
        lh.lt(col, operator_context='INVOKE_DEFAULT')

        def draw_pmi(pr, pm, pmi, idx):
            text, icon, _, icon_only, hidden, _ = pmi.parse_edit()

            lh.operator(
                self.op_bl_idname,
                text,
                icon,
                pm_item=idx,
                mode=self.mode,
                text=self.text,
                name=self.name,
                add=False,
                new_script=False,
            )

        draw_pme_layout(pm, col, draw_pmi)

        operator(
            column,
            self.op_bl_idname,
            "Add New Row",
            'ADD',
            pm_item=-1,
            mode=self.mode,
            name=self.name,
            add=True,
            new_script=False,
        ).text = self.text

    def _draw_script(self, menu, context):
        pm = get_prefs().selected_pm

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        for idx, pmi in enumerate(pm.pmis):
            text, *_ = pmi.parse()
            lh.operator(
                self.op_bl_idname,
                text,
                'MOD_SKIN',
                pm_item=idx,
                mode=self.mode,
                text=self.text,
                name=self.name,
                add=False,
                new_script=False,
            )

        lh.operator(
            self.op_bl_idname,
            "New Command",
            'ADD',
            pm_item=-1,
            mode=self.mode,
            text=self.text,
            name=self.name,
            add=True,
            new_script=False,
        )

        lh.sep()

        lh.operator(
            WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )

        lh.operator(PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM')

    def _draw_sticky(self, menu, context):
        pm = get_prefs().selected_pm

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        for idx, pmi in enumerate(pm.pmis):
            text, *_ = pmi.parse()
            lh.operator(
                self.op_bl_idname,
                text,
                'MESH_CIRCLE' if idx == 0 else 'MESH_UVSPHERE',
                pm_item=idx,
                mode=self.mode,
                text=self.text,
                name=self.name,
                add=False,
                new_script=False,
            )

        lh.sep()

        lh.operator(
            WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )

        lh.operator(PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM')

    def _draw_panel(self, menu, context):
        lh.lt(menu.layout)

        lh.operator(
            WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )

        lh.operator(PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM')

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.area and context.area.type == 'INFO':
            self.auto = False

        pr = get_prefs()
        if len(pr.pie_menus) == 0:
            bpy.ops.wm.pm_select(pm_name="")
            return {'CANCELLED'}
        pm = pr.selected_pm

        self.op_bl_idname = WM_OT_pmi_edit.bl_idname
        if self.clipboard:
            self.op_bl_idname = WM_OT_pmi_edit_clipboard.bl_idname
        elif self.auto:
            self.op_bl_idname = WM_OT_pmi_edit_auto.bl_idname

        if not self.text and not app.debug_wm:
            bpy.context.window_manager.popup_menu(self._draw_debug, title="Debug Mode")

        elif pm.mode == 'DIALOG':
            popup_dialog_pie(event, self._draw_pd)

        elif pm.mode == 'PMENU':
            bpy.context.window_manager.popup_menu(self._draw_pm, title=pm.name)

        elif pm.mode == 'RMENU':
            bpy.context.window_manager.popup_menu(self._draw_rm)

        elif pm.mode == 'SCRIPT':
            bpy.context.window_manager.popup_menu(self._draw_script, title=pm.name)

        elif pm.mode == 'STICKY':
            bpy.context.window_manager.popup_menu(self._draw_sticky, title=pm.name)

        elif pm.mode == 'MACRO':
            bpy.context.window_manager.popup_menu(self._draw_script, title=pm.name)

        elif pm.mode == 'MODAL':
            ed = pm.ed
            if ed:
                ed.popup_edit_menu(pm, self)

        elif pm.mode == 'PANEL' or pm.mode == 'HPANEL':
            bpy.context.window_manager.popup_menu(self._draw_panel, title=pm.name)

        return {'FINISHED'}


class PME_OT_pm_toggle(Operator):
    bl_idname = "pme.pm_toggle"
    bl_label = "Enable or Disable Item"
    bl_description = "Enable or disable the active item"
    bl_options = {'INTERNAL'}

    name: StringProperty(options={'SKIP_SAVE'})
    action: EnumProperty(
        items=(
            ('TOGGLE', "Toggle", ""),
            ('ENABLE', "Enable", ""),
            ('DISABLE', "Disable", ""),
        ),
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        value = None
        if self.action == 'ENABLE':
            value = True
        elif self.action == 'DISABLE':
            value = False
        toggle_menu(self.name, value)
        return {'FINISHED'}


class PME_OT_pmi_toggle(Operator):
    bl_idname = "pme.pmi_toggle"
    bl_label = "Enable or Disable Menu Slot"
    bl_description = "Enable or disable the slot"
    bl_options = {'INTERNAL'}

    pm: StringProperty(options={'SKIP_SAVE'})
    pmi: IntProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        pm = pr.pie_menus[self.pm]
        pmi = pm.pmis[self.pmi]
        pmi.enabled = not pmi.enabled
        ed = pm.ed
        if ed:
            ed.on_pmi_toggle(pm, pmi)
        tag_redraw()
        return {'FINISHED'}
