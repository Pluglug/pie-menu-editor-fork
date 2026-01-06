# pyright: reportInvalidTypeForm=false
# prefs/pm_ops.py - PM 操作オペレーター
# LAYER = "prefs"
"""
Pie Menu の操作オペレーター群

- WM_OT_pm_duplicate: 複製
- PME_OT_pm_remove: 削除
- PME_OT_pm_enable_all: 全有効/無効
- PME_OT_pm_enable_by_tag: タグで有効/無効
- PME_OT_pm_remove_by_tag: タグで削除
- WM_OT_pm_move: 移動
- WM_OT_pm_sort: ソート
"""

from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator, UILayout

from ..addon import get_prefs, temp_prefs
from ..bl_utils import ConfirmBoxHandler
from ..keymap_helper import to_key_name
from ..pme_types import Tag
from ..ui import tag_redraw
from ..ui.layout import lh


class WM_OT_pm_duplicate(Operator):
    bl_idname = "wm.pm_duplicate"
    bl_label = ""
    bl_description = "Duplicate the active item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        pr = get_prefs()
        if len(pr.pie_menus) == 0:
            return {'FINISHED'}

        apm = pr.selected_pm
        apm_name = apm.name

        pm = pr.add_pm(apm.mode, apm_name, True)

        pm.ed.on_pm_duplicate(apm, pm)

        Tag.filter()
        pr.update_tree()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(get_prefs().pie_menus) > 0


class PME_OT_pm_remove(ConfirmBoxHandler, Operator):
    bl_idname = "pme.pm_remove"
    bl_label = "Remove Item(s)"
    bl_description = "Remove item(s)"
    bl_options = {'INTERNAL'}

    mode: EnumProperty(
        items=(
            ('ACTIVE', "Remove Active Item", "Remove active item"),
            ('ALL', "Remove All Items", "Remove all items"),
            ('ENABLED', "Remove Enabled Items", "Remove enabled items"),
            ('DISABLED', "Remove Disabled Items", "Remove disabled items"),
        ),
        options={'SKIP_SAVE'},
    )

    def on_confirm(self, value):
        if not value:
            return

        pr = get_prefs()
        if self.mode == 'ACTIVE':
            pr.remove_pm()
        elif self.mode == 'ALL':
            while len(pr.pie_menus):
                pr.remove_pm(pm=pr.pie_menus[0])
        elif self.mode in {'ENABLED', 'DISABLED'}:
            i = 0
            while i < len(pr.pie_menus):
                pm = pr.pie_menus[i]
                if (
                    (pm.enabled and self.mode == 'ENABLED')
                    or (not pm.enabled and self.mode == 'DISABLED')
                ):
                    pr.remove_pm(pm=pm)
                else:
                    i += 1

        # Lazy import to avoid circular dependency
        from .tree import PME_UL_pm_tree
        PME_UL_pm_tree.update_tree()
        tag_redraw()

    @classmethod
    def poll(cls, context):
        return len(get_prefs().pie_menus) > 0

    def invoke(self, context, event):
        self.box = True
        self.title = UILayout.enum_item_name(self, "mode", self.mode)
        return ConfirmBoxHandler.invoke(self, context, event)


class PME_OT_pm_enable_all(Operator):
    bl_idname = "wm.pm_enable_all"
    bl_label = ""
    bl_description = "Enable or disable all items"
    bl_options = {'INTERNAL'}

    enable: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        for pm in get_prefs().pie_menus:
            pm.enabled = self.enable
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return get_prefs().pie_menus


class PME_OT_pm_enable_by_tag(Operator):
    bl_idname = "pme.pm_enable_by_tag"
    bl_label = ""
    bl_description = "Enable or disable items by tag"
    bl_options = {'INTERNAL'}

    enable: BoolProperty(options={'SKIP_SAVE'})
    tag: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        if not self.tag:
            Tag.popup_menu(
                self.bl_idname,
                "Enable by Tag" if self.enable else "Disable by Tag",
                enable=self.enable,
            )
        else:
            for pm in get_prefs().pie_menus:
                if pm.has_tag(self.tag):
                    pm.enabled = self.enable
            tag_redraw()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return get_prefs().pie_menus


class PME_OT_pm_remove_by_tag(Operator):
    bl_idname = "pme.pm_remove_by_tag"
    bl_label = ""
    bl_description = "Remove items by tag"
    bl_options = {'INTERNAL'}

    tag: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        if not self.tag:
            Tag.popup_menu(self.bl_idname, "Remove by Tag")
        else:
            pr = get_prefs()
            pm_names = []
            for pm in get_prefs().pie_menus:
                if pm.has_tag(self.tag):
                    pm_names.append(pm.name)

            for pm_name in pm_names:
                pr.remove_pm(pr.pie_menus[pm_name])

            # Lazy import to avoid circular dependency
            from .tree import PME_UL_pm_tree
            PME_UL_pm_tree.update_tree()
            tag_redraw()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return get_prefs().pie_menus


class WM_OT_pm_move(Operator):
    bl_idname = "wm.pm_move"
    bl_label = ""
    bl_description = "Move the active item"
    bl_options = {'INTERNAL'}

    direction: IntProperty()

    def execute(self, context):
        pr = get_prefs()
        tpr = temp_prefs()
        if pr.tree_mode:
            link = tpr.links[tpr.links_idx]
            if link.label:
                return {'CANCELLED'}

            new_idx = tpr.links_idx + self.direction
            num_links = len(tpr.links)
            if 0 <= new_idx <= num_links - 1:
                new_link = tpr.links[new_idx]
                if link.is_folder or not link.path:
                    while 0 <= new_idx < num_links:
                        new_link = tpr.links[new_idx]
                        if new_link.label:
                            return {'CANCELLED'}
                        elif not new_link.path:
                            break

                        new_idx += self.direction

                    if new_idx < 0 or new_idx >= num_links:
                        return {'CANCELLED'}

                else:
                    if new_link.label or new_link.is_folder or not new_link.path:
                        return {'CANCELLED'}

                pm_idx = pr.pie_menus.find(new_link.pm_name)
                pr.pie_menus.move(pr.active_pie_menu_idx, pm_idx)
                pr.active_pie_menu_idx = pm_idx
                # Lazy import to avoid circular dependency
                from .tree import PME_UL_pm_tree
                PME_UL_pm_tree.update_tree()

            else:
                return {'CANCELLED'}

        else:
            new_idx = pr.active_pie_menu_idx + self.direction
            if 0 <= new_idx <= len(pr.pie_menus) - 1:
                pr.pie_menus.move(pr.active_pie_menu_idx, new_idx)
                pr.active_pie_menu_idx = new_idx

            # Lazy import to avoid circular dependency
            from .tree import PME_UL_pm_tree
            PME_UL_pm_tree.update_tree()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(get_prefs().pie_menus) > 1


class WM_OT_pm_sort(Operator):
    bl_idname = "wm.pm_sort"
    bl_label = ""
    bl_description = "Sort items by"
    bl_options = {'INTERNAL'}

    mode: EnumProperty(
        items=(
            ('NONE', "None", ""),
            ('NAME', "Name", ""),
            ('HOTKEY', "Hotkey", ""),
            ('KEYMAP', "Keymap", ""),
            ('TYPE', "Type", ""),
            ('TAG', "Tag", ""),
        ),
        options={'SKIP_SAVE'},
    )

    def _draw(self, menu, context):
        lh.lt(menu.layout)
        lh.operator(WM_OT_pm_sort.bl_idname, "Name", 'SORTALPHA', mode='NAME')

        lh.operator(WM_OT_pm_sort.bl_idname, "Hotkey", 'FILE_FONT', mode='HOTKEY')

        lh.operator(WM_OT_pm_sort.bl_idname, "Keymap Name", 'MOUSE_MMB', mode='KEYMAP')

        lh.operator(WM_OT_pm_sort.bl_idname, "Type", 'PROP_CON', mode='TYPE')

        lh.operator(WM_OT_pm_sort.bl_idname, "Tag", 'SOLO_OFF', mode='TAG')

    def execute(self, context):
        if self.mode == 'NONE':
            context.window_manager.popup_menu(
                self._draw, title=WM_OT_pm_sort.bl_description
            )
            return {'FINISHED'}

        pr = get_prefs()
        if len(pr.pie_menus) == 0:
            return {'FINISHED'}

        items = [pm for pm in pr.pie_menus]

        if self.mode == 'NAME':
            items.sort(key=lambda pm: pm.name)
        elif self.mode == 'KEYMAP':
            items.sort(key=lambda pm: (pm.km_name, pm.name))
        elif self.mode == 'HOTKEY':
            items.sort(
                key=lambda pm: (
                    to_key_name(pm.key) if pm.key != 'NONE' else '_',
                    pm.ctrl,
                    pm.shift,
                    pm.alt,
                    pm.oskey,
                    pm.key_mod if pm.key_mod != 'NONE' else '_',
                )
            )
        elif self.mode == 'TYPE':
            items.sort(key=lambda pm: (pm.mode, pm.ed.default_name))
        elif self.mode == 'TAG':
            items.sort(key=lambda pm: (pm.tag, pm.name))

        items = [pm.name for pm in items]
        apm = pr.selected_pm
        apm_name = apm.name

        idx = len(items) - 1
        aidx = 0
        while idx > 0:
            k = items[idx]
            if pr.pie_menus[idx] != pr.pie_menus[k]:
                k_idx = pr.pie_menus.find(k)
                pr.pie_menus.move(k_idx, idx)
            if apm_name == k:
                aidx = idx
            idx -= 1
        pr.active_pie_menu_idx = aidx

        # Lazy import to avoid circular dependency
        from .tree import PME_UL_pm_tree
        PME_UL_pm_tree.update_tree()

        tag_redraw()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(get_prefs().pie_menus) > 1
