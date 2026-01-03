# operators/ed/tags.py - Tag management operators
# LAYER = "operators"
#
# Moved from: editors/base.py (Phase 5-A operator separation)

LAYER = "operators"

import bpy
from ...addon import get_prefs, temp_prefs, ic_rb, ic
from ...core import constants as CC
from ...bl_utils import uname
from ...infra.collections import sort_collection
from ...ui import tag_redraw
from ...ui.layout import operator
from ...pme_types import Tag


class PME_OT_tags_filter(bpy.types.Operator):
    bl_idname = "pme.tags_filter"
    bl_label = "Filter by Tag"
    bl_description = "Filter by tag"
    bl_options = {'INTERNAL'}

    ask: bpy.props.BoolProperty(default=True, options={'SKIP_SAVE'})
    tag: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def draw_menu(self, menu, context):
        pr = get_prefs()
        tpr = temp_prefs()
        layout = menu.layout
        operator(
            layout,
            self.bl_idname,
            "Disable",
            icon=ic_rb(not pr.tag_filter),
            tag="",
            ask=False,
        )
        layout.separator()

        for t in tpr.tags:
            operator(
                layout,
                self.bl_idname,
                t.name,
                icon=ic_rb(t.name == pr.tag_filter),
                tag=t.name,
                ask=False,
            )

        operator(
            layout,
            self.bl_idname,
            CC.UNTAGGED,
            icon=ic_rb(pr.tag_filter == CC.UNTAGGED),
            tag=CC.UNTAGGED,
            ask=False,
        )

    def execute(self, context):
        if self.ask:
            context.window_manager.popup_menu(self.draw_menu, title=self.bl_label)
        else:
            pr = get_prefs()
            pr.tag_filter = self.tag
            Tag.filter()
            pr.update_tree()
            tag_redraw()

        return {'FINISHED'}


class PME_OT_tags(bpy.types.Operator):
    bl_idname = "pme.tags"
    bl_label = ""
    bl_description = "Manage tags"
    bl_options = {'INTERNAL'}
    bl_property = "tag"

    idx: bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})
    action: bpy.props.EnumProperty(
        items=(
            ('MENU', "Menu", ""),
            ('TAG', "Tag", ""),
            ('UNTAG', "Untag", ""),
            ('ADD', "Add", ""),
            ('REMOVE', "Remove", ""),
            ('RENAME', "Rename", ""),
        ),
        options={'SKIP_SAVE'},
    )
    tag: bpy.props.StringProperty(maxlen=50, options={'SKIP_SAVE'})
    group: bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def draw_menu(self, menu, context):
        pr = get_prefs()
        tpr = temp_prefs()
        pm = pr.selected_pm
        layout = menu.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        i = 0
        for i, tag in enumerate(tpr.tags):
            icon = CC.ICON_OFF
            action = 'TAG'
            if pm.has_tag(tag.name):
                icon = CC.ICON_ON
                action = 'UNTAG'
            if self.action != 'MENU':
                action = self.action
                icon = 'NONE'
            operator(
                layout,
                PME_OT_tags.bl_idname,
                tag.name,
                icon,
                idx=i,
                action=action,
                group=self.group,
            )

        if self.action not in {'MENU', 'TAG'}:
            return

        if tpr.tags:
            layout.separator()

        operator(
            layout,
            PME_OT_tags.bl_idname,
            "Assign New Tag",
            'ADD',
            action='ADD',
            group=self.group,
        )

        if self.action != 'MENU':
            return

        if not tpr.tags:
            return

        operator(
            layout,
            PME_OT_tags.bl_idname,
            "Rename Tag",
            'OUTLINER_DATA_FONT',
            action='RENAME',
        )
        operator(layout, PME_OT_tags.bl_idname, "Remove Tag", 'REMOVE', action='REMOVE')

    def draw(self, context):
        self.layout.prop(self, "tag", text="", icon=ic('SOLO_OFF'))

    def execute(self, context):
        pr = get_prefs()
        tpr = temp_prefs()
        pm = pr.selected_pm

        self.tag = self.tag.replace(",", "").strip()
        if not self.tag:
            return {'CANCELLED'}
        if self.tag == CC.UNTAGGED:
            self.tag += ".001"

        if self.action == 'ADD':
            tag = tpr.tags.add()
            tag.name = uname(tpr.tags, self.tag)
            if self.group:
                for v in pr.pie_menus:
                    if v.enabled:
                        v.add_tag(tag.name)
            else:
                pm.add_tag(tag.name)
            sort_collection(tpr.tags, lambda t: t.name)

        elif self.action == 'RENAME':
            tag = tpr.tags[self.idx]
            if tag.name == self.tag:
                return {'CANCELLED'}

            self.tag = uname(tpr.tags, self.tag)
            for pm in pr.pie_menus:
                if pm.has_tag(tag.name):
                    pm.remove_tag(tag.name)
                    pm.add_tag(self.tag)
            tag.name = self.tag

        Tag.filter()
        pr.update_tree()
        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        pr = get_prefs()
        tpr = temp_prefs()
        pm = pr.selected_pm

        tag = None
        if self.idx >= 0:
            tag = tpr.tags[self.idx]

        if self.action == 'MENU':
            context.window_manager.popup_menu(
                self.draw_menu, title=pm.name, icon=pm.ed.icon if pm.ed else 'NONE'
            )

        elif self.action == 'ADD':
            self.tag = "Tag"
            return context.window_manager.invoke_props_dialog(self)

        elif self.action == 'RENAME':
            if self.idx == -1:
                context.window_manager.popup_menu(
                    self.draw_menu, title="Rename Tag", icon='OUTLINER_DATA_FONT'
                )
            else:
                self.tag = tag.name
                return context.window_manager.invoke_props_dialog(self)

        elif self.action == 'REMOVE':
            if self.idx == -1:
                context.window_manager.popup_menu(
                    self.draw_menu, title="Remove Tag", icon='REMOVE'
                )
            else:
                for pm in pr.pie_menus:
                    pm.remove_tag(tag.name)
                tpr.tags.remove(self.idx)

        elif self.action == 'TAG':
            if tag is None:
                context.window_manager.popup_menu(
                    self.draw_menu, title="Tag Enabled Menus", icon='SOLO_ON'
                )
            else:
                if self.group:
                    for v in pr.pie_menus:
                        if v.enabled:
                            v.add_tag(tag.name)
                else:
                    pm.add_tag(tag.name)

        elif self.action == 'UNTAG':
            if tag is None:
                context.window_manager.popup_menu(
                    self.draw_menu, title="Untag Enabled Menus", icon='SOLO_OFF'
                )
            else:
                if self.group:
                    for v in pr.pie_menus:
                        if v.enabled:
                            v.remove_tag(tag.name)
                else:
                    pm.remove_tag(tag.name)

        Tag.filter()
        pr.update_tree()
        tag_redraw()
        return {'FINISHED'}
