# operators/panel.py - Panel hiding operators for PME
# LAYER = "operators"
#
# Moved from: operators/__init__.py (Phase 2-C operators reorganization)
#
# Contains:
#   - PME_OT_panel_hide: Hide a single panel
#   - PME_OT_panel_hide_by: Hide panels by filter criteria
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty

from ..addon import get_prefs
from ..ui.layout import lh
from ..ui import tag_redraw
from ..panel_utils import (
    hide_panel,
    hidden_panel,
    is_panel_hidden,
    bl_panel_types,
    bl_panel_enum_items,
)
from ..constants import SPACE_ITEMS, REGION_ITEMS


class PME_OT_panel_hide(Operator):
    bl_idname = "pme.panel_hide"
    bl_label = "Hide Panel"
    bl_description = "Hide panel"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        if not PME_OT_panel_hide.enum_items:
            PME_OT_panel_hide.enum_items = bl_panel_enum_items(False)

        return PME_OT_panel_hide.enum_items

    item: EnumProperty(items=get_items, options={'SKIP_SAVE'})
    panel: StringProperty(options={'SKIP_SAVE'})
    group: StringProperty(options={'SKIP_SAVE'})

    def draw_menu(self, menu, context):
        lh.lt(menu.layout)
        pr = get_prefs()
        for pm in pr.pie_menus:
            if pm.mode == 'HPANEL':
                lh.operator(
                    PME_OT_panel_hide.bl_idname,
                    pm.name,
                    pm.ed.icon,
                    group=pm.name,
                    panel=self.panel,
                )

        lh.sep(check=True)

        lh.operator(
            PME_OT_panel_hide.bl_idname,
            "New Hidden Panel Group",
            'ADD',
            group=pr.unique_pm_name(pr.ed('HPANEL').default_name),
            panel=self.panel,
        )

    def execute(self, context):
        if not self.panel:
            self.panel = self.item

        pr = get_prefs()

        if not self.group:
            context.window_manager.popup_menu(self.draw_menu, title="Group")
            return {'FINISHED'}
        else:
            if self.group not in pr.pie_menus:
                group = pr.add_pm('HPANEL', self.group)
                pr.update_tree()
            else:
                group = pr.pie_menus[self.group]

        tp = hidden_panel(self.panel) or getattr(bpy.types, self.panel, None)

        if not tp:
            return {'CANCELLED'}

        for pmi in group.pmis:
            if pmi.text == self.panel:
                return {'CANCELLED'}

        pmi = group.pmis.add()
        pmi.mode = 'MENU'
        pmi.name = tp.bl_label if hasattr(tp, "bl_label") else self.panel
        pmi.text = self.panel

        hide_panel(self.panel)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.panel:
            PME_OT_panel_hide.enum_items = None
            context.window_manager.invoke_search_popup(self)
        else:
            return self.execute(context)
        return {'FINISHED'}


class PME_OT_panel_hide_by(Operator):
    bl_idname = "pme.panel_hide_by"
    bl_label = "Hide Panels by ..."
    bl_description = "Hide panels by ..."
    bl_options = {'INTERNAL'}

    space_items = None
    region_items = None
    ctx_items = None
    cat_items = None

    def _get_space_items(self, context):
        if not PME_OT_panel_hide_by.space_items:
            enum_items = [("ANY", "Any Space", "", 'LAYER_ACTIVE', 0)]

            for i, item in enumerate(SPACE_ITEMS):
                enum_items.append((item[0], item[1], "", item[3], i + 1))

            PME_OT_panel_hide_by.space_items = enum_items

        return PME_OT_panel_hide_by.space_items

    def _get_region_items(self, context):
        if not PME_OT_panel_hide_by.region_items:
            enum_items = [("ANY", "Any Region", "", 'LAYER_ACTIVE', 0)]

            for i, item in enumerate(REGION_ITEMS):
                enum_items.append((item[0], item[1], "", item[3], i + 1))

            PME_OT_panel_hide_by.region_items = enum_items

        return PME_OT_panel_hide_by.region_items

    def _get_context_items(self, context):
        if not PME_OT_panel_hide_by.ctx_items:
            enum_items = [("ANY", "Any Context", "", 'LAYER_ACTIVE', 0)]

            contexts = set()
            for tp in bl_panel_types():
                if hasattr(tp, "bl_context"):
                    contexts.add(tp.bl_context)

            for i, c in enumerate(sorted(contexts)):
                enum_items.append((c, c, "", 'LAYER_USED', i + 1))

            PME_OT_panel_hide_by.ctx_items = enum_items

        return PME_OT_panel_hide_by.ctx_items

    def _get_category_items(self, context):
        if not PME_OT_panel_hide_by.cat_items:
            enum_items = [("ANY", "Any Category", "", 'LAYER_ACTIVE', 0)]

            categories = set()
            for tp in bl_panel_types():
                if hasattr(tp, "bl_category"):
                    categories.add(tp.bl_category)

            for i, c in enumerate(sorted(categories)):
                enum_items.append((c, c, "", 'LAYER_USED', i + 1))

            PME_OT_panel_hide_by.cat_items = enum_items

        return PME_OT_panel_hide_by.cat_items

    space: EnumProperty(
        items=_get_space_items, name="Space", description="Space", options={'SKIP_SAVE'}
    )
    region: EnumProperty(
        items=_get_region_items,
        name="Region",
        description="Region",
        options={'SKIP_SAVE'},
    )
    context: EnumProperty(
        items=_get_context_items,
        name="Context",
        description="Context",
        options={'SKIP_SAVE'},
    )
    category: EnumProperty(
        items=_get_category_items,
        name="Category",
        description="Category",
        options={'SKIP_SAVE'},
    )
    mask: StringProperty(
        name="Mask", description="Mask", options={'SKIP_SAVE'}
    )

    def _filtered_panels(self, num=False):
        if num:
            num_panels = 0
        else:
            panels = []

        for tp in self.panel_types:
            if (
                tp.bl_space_type != 'PREFERENCES'
                and (self.space == 'ANY' or tp.bl_space_type == self.space)
                and (self.region == 'ANY' or tp.bl_region_type == self.region)
                and (
                    self.context == 'ANY'
                    or hasattr(tp, "bl_context")
                    and tp.bl_context == self.context
                )
                and (
                    self.category == 'ANY'
                    or hasattr(tp, "bl_category")
                    and tp.bl_category == self.category
                )
                and (
                    not self.mask
                    or hasattr(tp, "bl_label")
                    and self.mask.lower() in tp.bl_label.lower()
                )
            ):
                if is_panel_hidden(tp.__name__):
                    continue

                if num:
                    num_panels += 1
                else:
                    panels.append(tp)

        return num_panels if num else panels

    def check(self, context):
        return True

    def draw(self, context):
        col = self.layout.column(align=True)
        lh.row(col)
        lh.prop(self, "space", "")
        lh.prop(self, "region", "")
        lh.row(col)
        lh.prop(self, "context", "")
        lh.prop(self, "category", "")
        lh.lt(col)
        lh.prop(self, "mask", "", 'FILTER')
        lh.sep()
        lh.row(col)
        lh.layout.alignment = 'CENTER'
        lh.label("%d panel(s) will be hidden" % self._filtered_panels(True))

    def execute(self, context):
        pm = get_prefs().selected_pm

        for tp in self._filtered_panels():
            tp_name = tp.__name__
            if hasattr(tp, "bl_idname"):
                tp_name = tp.bl_idname

            pmi = pm.pmis.add()
            pmi.mode = 'MENU'
            pmi.name = tp.bl_label if hasattr(tp, "bl_label") else tp.__name__
            pmi.text = tp_name

            hide_panel(tp_name)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_panel_hide_by.space_items = None
        PME_OT_panel_hide_by.region_items = None
        PME_OT_panel_hide_by.ctx_items = None
        PME_OT_panel_hide_by.cat_items = None
        self.panel_types = bl_panel_types()
        return context.window_manager.invoke_props_dialog(self)
