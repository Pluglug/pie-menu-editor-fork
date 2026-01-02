# operators/extras/popup.py - Popup operators for PME
# LAYER = "operators"
#
# Moved from: extra_operators.py (Phase 2-C operators reorganization)
#
# Contains:
#   - PME_OT_popup_property: Property popup
#   - PME_OT_popup_user_preferences: User preferences popup
#   - PME_OT_popup_addon_preferences: Addon preferences popup
#   - PME_OT_popup_panel: Panel popup
#   - PME_OT_select_popup_panel: Select and open panel popup
#   - PME_OT_popup_area: Open area in new window
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

LAYER = "operators"

import bpy
import addon_utils
from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty

from ...addon import ADDON_ID, get_prefs, get_uprefs
from ...bl_utils import PopupOperator, popup_area, ctx_dict
from ...ui.panels import panel, panel_label, bl_panel_enum_items
from ...ui.layout import lh, split
from ...ui import screen as SU
from ...core import constants as CC
from ...core.constants import (
    PME_TEMP_SCREEN,
    PME_SCREEN,
    MAX_STR_LEN,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)
from ... import pme


class PME_OT_popup_property(PopupOperator, Operator):
    bl_idname = "pme.popup_property"
    bl_label = "Property"
    bl_description = "Edit property"
    bl_options = {'INTERNAL'}

    path: StringProperty(options={'SKIP_SAVE'})

    def draw(self, context):
        super().draw(context)
        lh.lt(self.layout)
        obj, sep, prop = self.path.rpartition(".")
        if sep:
            obj = pme.context.eval(obj)
            if obj:
                lh.prop_compact(obj, prop)


class PME_OT_popup_user_preferences(PopupOperator, Operator):
    bl_idname = "pme.popup_user_preferences"
    bl_label = "User Preferences"
    bl_description = "Open the user preferences in a popup"
    bl_options = {'INTERNAL'}

    tab: EnumProperty(
        name="Tab",
        description="Tab",
        options={'SKIP_SAVE'},
        items=(
            ('CURRENT', "Current", ""),
            ('INTERFACE', "Interface", ""),
            ('EDITING', "Editing", ""),
            ('INPUT', "Input", ""),
            ('ADDONS', "Add-ons", ""),
            ('THEMES', "Themes", ""),
            ('FILES', "File", ""),
            ('SYSTEM', "System", ""),
        ),
    )
    width: IntProperty(
        name="Width",
        description="Width of the popup",
        default=800,
        options={'SKIP_SAVE'},
    )
    center: BoolProperty(
        name="Center", description="Center", default=True, options={'SKIP_SAVE'}
    )

    def draw(self, context):
        PopupOperator.draw(self, context)

        upr = get_uprefs()
        col = self.layout.column(align=True)
        col.row(align=True).prop(upr, "active_section", expand=True)

        tp = None
        if upr.active_section == 'INTERFACE':
            tp = bpy.types.USERPREF_PT_interface
        elif upr.active_section == 'EDITING':
            tp = bpy.types.USERPREF_PT_edit
        elif upr.active_section == 'INPUT':
            tp = bpy.types.USERPREF_PT_input
        elif upr.active_section == 'ADDONS':
            tp = bpy.types.USERPREF_PT_addons
        elif upr.active_section == 'THEMES':
            tp = bpy.types.USERPREF_PT_theme
        elif upr.active_section == 'FILES':
            tp = bpy.types.USERPREF_PT_file
        elif upr.active_section == 'SYSTEM':
            tp = getattr(bpy.types, "USERPREF_PT_system", None) or getattr(
                bpy.types, "USERPREF_PT_system_general", None
            )

        pme.context.layout = col
        if tp:
            panel(tp, frame=True, header=False, poll=False)

    def invoke(self, context, event):
        if self.tab != 'CURRENT':
            try:
                get_uprefs().active_section = self.tab
            except:
                pass

        return PopupOperator.invoke(self, context, event)


class PME_OT_popup_addon_preferences(PopupOperator, Operator):
    bl_idname = "pme.popup_addon_preferences"
    bl_label = "Addon Preferences"
    bl_description = "Open the addon preferences in a popup"
    bl_options = {'INTERNAL'}

    addon: StringProperty(
        name="Add-on", description="Add-on", options={'SKIP_SAVE'}
    )
    width: IntProperty(
        name="Width",
        description="Width of the popup",
        default=800,
        options={'SKIP_SAVE'},
    )
    center: BoolProperty(
        default=True, name="Center", description="Center", options={'SKIP_SAVE'}
    )
    auto_close: BoolProperty(
        default=False,
        name="Auto Close",
        description="Auto close the popup",
        options={'SKIP_SAVE'},
    )

    def draw(self, context):
        title = None
        if self.auto_close:
            mod = addon_utils.addons_fake_modules.get(self.addon)
            if not mod:
                return
            info = addon_utils.module_bl_info(mod)
            title = info["name"]  # pylint: disable=unsubscriptable-object

        PopupOperator.draw(self, context, title)

        addon_prefs = None
        for addon in get_uprefs().addons:
            if addon.module == self.addon:
                addon_prefs = addon.preferences
                break

        if addon_prefs and hasattr(addon_prefs, "draw"):
            col = self.layout.column(align=True)
            addon_prefs.layout = col.box()
            addon_prefs.draw(context)
            addon_prefs.layout = None

            row = col.row(align=True)
            row.operator_context = 'INVOKE_DEFAULT'
            row.operator("wm.save_userpref")

    def invoke(self, context, event):
        if not self.addon:
            self.addon = ADDON_ID
        return PopupOperator.invoke(self, context, event)


class PME_OT_popup_panel(PopupOperator, Operator):
    bl_idname = "pme.popup_panel"
    bl_label = "Pie Menu Editor"
    bl_description = "Open the panel in a popup"
    bl_options = {'INTERNAL'}

    panel: StringProperty(
        name="Panel(s)",
        description=(
            "Comma/semicolon separated panel ID(s).\n"
            "  Use a semicolon to add columns.\n"
        ),
        options={'SKIP_SAVE'},
    )
    frame: BoolProperty(
        name="Frame", description="Frame", default=True, options={'SKIP_SAVE'}
    )
    header: BoolProperty(
        name="Header", description="Header", default=True, options={'SKIP_SAVE'}
    )
    area: EnumProperty(
        name="Area Type",
        description="Area type",
        items=CC.AreaEnumHelper.gen_items_with_current,
        options={'SKIP_SAVE'},
    )
    width: IntProperty(
        name="Width",
        description="Width of the popup",
        default=-1,
        options={'SKIP_SAVE'},
    )

    def draw(self, context):
        title = None
        panel_groups = self.panel.split(";")
        if len(panel_groups) == 1:
            panels = panel_groups[0].split(",")
            if len(panels) == 1:
                p = panels[0]
                if p[0] == "!":
                    p = p[1:]
                title = panel_label(p)
        PopupOperator.draw(self, context, title)

        layout = self.layout

        if len(panel_groups) > 1:
            layout = split(layout)

        for group in panel_groups:
            panels = group.split(",")
            col = layout.column()
            pme.context.layout = col
            for p in panels:
                expand = None
                if p[0] == "!":
                    expand = False
                    p = p[1:]
                panel(
                    p.strip(),
                    frame=self.frame,
                    header=self.header,
                    area=self.area,
                    expand=expand,
                )

    def cancel(self, context):
        PopupOperator.cancel(self, context)

    def execute(self, context):
        PopupOperator.execute(self, context)
        return {'FINISHED'}

    def invoke(self, context, event):
        pme.context.reset()

        if self.width == -1:
            panel_groups = self.panel.split(";")
            self.width = 300 * len(panel_groups)

        return PopupOperator.invoke(self, context, event)


class PME_OT_select_popup_panel(Operator):
    bl_idname = "pme.select_popup_panel"
    bl_label = "Select and Open Panel"
    bl_description = "Select and open the panel in a popup"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        if not PME_OT_select_popup_panel.enum_items:
            PME_OT_select_popup_panel.enum_items = bl_panel_enum_items()

        return PME_OT_select_popup_panel.enum_items

    item: EnumProperty(items=get_items, options={'SKIP_SAVE', 'HIDDEN'})

    def execute(self, context):
        PME_OT_select_popup_panel.enum_items = None
        bpy.ops.pme.popup_panel('INVOKE_DEFAULT', panel=self.item)
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_select_popup_panel.enum_items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_popup_area(Operator):
    bl_idname = "pme.popup_area"
    bl_label = "Popup Area"
    bl_description = "Open the area in a new window"
    bl_options = {'INTERNAL'}

    width: IntProperty(
        name="Width",
        description="Width of the window (-1 - auto)",
        subtype='PIXEL',
        default=-1,
        min=WINDOW_MIN_WIDTH,
        soft_min=-1,
        options={'SKIP_SAVE'},
    )
    height: IntProperty(
        name="Height",
        description="Height of the window (-1 - auto)",
        subtype='PIXEL',
        default=-1,
        min=WINDOW_MIN_HEIGHT,
        soft_min=-1,
        options={'SKIP_SAVE'},
    )
    center: BoolProperty(
        name="Center", description="Center", options={'SKIP_SAVE'}
    )
    area: EnumProperty(
        name="Area",
        description="Area",
        items=CC.AreaEnumHelper.gen_items_with_current,
        options={'SKIP_SAVE'},
    )
    auto_close: BoolProperty(
        default=True,
        name="Auto Close",
        description="Click outside to close the window",
        options={'SKIP_SAVE'},
    )
    header: EnumProperty(
        name="Header",
        description="Header options",
        items=CC.header_action_enum_items(),
        options={'SKIP_SAVE'},
    )
    cmd: StringProperty(
        name="Exec on Open",
        description="Execute python code on window open",
        maxlen=MAX_STR_LEN,
        options={'SKIP_SAVE'},
    )

    def update_header(self, context, on_top, visible, d):
        if self.header == 'DEFAULT':
            return

        if 'TOP' in self.header:
            if not on_top:
                with context.temp_override(**d):
                    bpy.ops.screen.region_flip()
        else:
            if on_top:
                with context.temp_override(**d):
                    bpy.ops.screen.region_flip()

        if 'HIDE' in self.header:
            if visible:
                with context.temp_override(**d):
                    bpy.ops.screen.header()
        else:
            if not visible:
                with context.temp_override(**d):
                    bpy.ops.screen.header()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        # Setup area
        if self.area == 'CURRENT':
            if not context.area:
                return {'CANCELLED'}

            self.area = context.area.ui_type

        # Setup Screen Name
        area_name = next(
            (item[1] for item in CC.AreaEnumHelper.gen_items_with_current()
             if item[0] == self.area), ""
        )
        screen_name = PME_TEMP_SCREEN if self.auto_close else PME_SCREEN
        screen_name += area_name

        area = context.area or context.screen.areas[0]

        rh, rw = None, None
        for r in area.regions:
            if r.type == 'HEADER':
                rh = r
            elif r.type == 'WINDOW':
                rw = r

        header_dict = ctx_dict(area=area, region=rh)
        header_visible = rh.height > 1
        if header_visible:
            header_on_top = rw.y == area.y
        else:
            header_on_top = rh.y > area.y

        self.update_header(context, header_on_top, header_visible, header_dict)

        window = context.window
        windows = [w for w in context.window_manager.windows]

        if self.width == -1:
            if self.area == 'PROPERTIES':
                self.width = round(350 * get_uprefs().view.ui_scale)
            elif self.area == 'OUTLINER':
                self.width = round(400 * get_uprefs().view.ui_scale)
            else:
                self.width = round(window.width * 0.8)

        if self.width < WINDOW_MIN_WIDTH:
            self.width = WINDOW_MIN_WIDTH
        elif self.width > window.width:
            self.width = window.width

        if self.height == -1:
            self.height = round(window.height * 0.8)
        elif self.height < WINDOW_MIN_HEIGHT:
            self.height = WINDOW_MIN_HEIGHT

        x, y = event.mouse_x, event.mouse_y
        if self.center:
            x = window.width >> 1
            y = window.height - (window.height - self.height >> 1)
            context.window.cursor_warp(x, y)

        popup_area(area, self.width, self.height, x, y)

        new_window = None
        if context.window_manager.windows[-1] not in windows:
            new_window = context.window_manager.windows[-1]

        if new_window:
            reused = screen_name in bpy.data.screens
            if reused:
                new_window.screen = bpy.data.screens[screen_name]
            else:
                new_window.screen.name = screen_name
                new_window.screen.user_clear()

            target_area = (
                new_window.screen.areas[0] if new_window.screen.areas else None
            )
            if target_area:
                target_area.ui_type = self.area

            if (not reused) and self.cmd:
                SU.exec_with_override(
                    cmd=self.cmd,
                    window=new_window,
                    screen=new_window.screen,
                    area=target_area,
                )

        self.update_header(context, header_on_top, header_visible, header_dict)

        get_prefs().enable_window_kmis()

        return {'FINISHED'}
