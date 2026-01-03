# pyright: reportInvalidTypeForm=false
# operators/ed/keymap.py - Keymap and hotkey operators
# LAYER = "operators"
#
# Moved from: editors/base.py (Phase 5-A operator separation)

LAYER = "operators"

from bpy.props import EnumProperty
from bpy.types import Operator
from ...addon import get_prefs
from ...core.constants import KEYMAP_SPLITTER
from ...ui import tag_redraw
from ... import keymap_helper


class PME_OT_keymap_add(Operator):
    bl_idname = "pme.keymap_add"
    bl_label = ""
    bl_description = "Add a keymap"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    items = None

    def get_items(self, context):
        cl = PME_OT_keymap_add
        if not cl.items:
            it1 = []
            it2 = []
            pr = get_prefs()
            pm = pr.selected_pm

            for km in context.window_manager.keyconfigs.user.keymaps:
                has_hotkey = False
                for kmi in km.keymap_items:
                    if (
                        kmi.idname
                        and kmi.type != 'NONE'
                        and kmi.type == pm.key
                        and kmi.ctrl == pm.ctrl
                        and kmi.shift == pm.shift
                        and kmi.alt == pm.alt
                        and kmi.oskey == pm.oskey
                        and kmi.key_modifier == pm.key_mod
                    ):
                        has_hotkey = True
                        break

                if has_hotkey:
                    it1.append((km.name, "%s (%s)" % (km.name, kmi.name), ""))
                else:
                    it2.append((km.name, km.name, ""))

            it1.sort()
            it2.sort()

            cl.items = [t for t in it1]
            cl.items.extend([t for t in it2])

        return cl.items

    enumprop: EnumProperty(items=get_items)

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm
        km_names = pm.parse_keymap()
        if self.enumprop not in km_names:
            names = list(km_names)
            if len(names) == 1 and names[0] == "Window":
                names.clear()
            names.append(self.enumprop)
            names.sort()
            pm.km_name = (KEYMAP_SPLITTER + " ").join(names)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_keymap_add.items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_pm_open_mode_select(Operator):
    bl_idname = "pme.pm_open_mode_select"
    bl_label = "Hotkey Mode"
    bl_description = "Select hotkey mode"

    def draw(self, context):
        layout = self.layout
        pr = get_prefs()
        pm = pr.selected_pm
        col = layout.column(align=True)
        col.label(text="Hotkey Mode:")
        col.separator(type='LINE')
        visible = {'PRESS', 'HOLD', 'DOUBLE_CLICK', 'TWEAK', 'CHORDS'}
        if getattr(pr, "show_experimental_open_modes", False) or pm.open_mode in {'CLICK', 'CLICK_DRAG'}:
            visible |= {'CLICK', 'CLICK_DRAG'}
        pd = pm.__annotations__["open_mode"]
        pkeywords = pd.keywords if hasattr(pd, "keywords") else pd[1]
        for ident, name, desc, icon, _ in pkeywords['items']:
            if ident in visible:
                row = col.row(align=True)
                row.prop_enum(pm, "open_mode", ident, text=name)

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=150)

    def execute(self, context):
        return {'FINISHED'}


class PME_OT_pm_hotkey_convert(Operator):
    bl_idname = "pme.pm_hotkey_convert"
    bl_label = ""
    bl_options = {'INTERNAL'}
    bl_description = "Replace the key with ActionMouse/SelectMouse"

    def execute(self, context):
        pm = get_prefs().selected_pm
        if pm and (pm.key == 'LEFTMOUSE' or pm.key == 'RIGHTMOUSE'):
            pm.key = keymap_helper.to_blender_mouse_key(pm.key, context)
            return {'FINISHED'}
        return {'CANCELLED'}
