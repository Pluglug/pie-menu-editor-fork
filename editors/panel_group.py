# pyright: reportInvalidTypeForm=false
# editors/panel_group.py - Panel Group editor
# LAYER = "editors"
#
# Moved from: ed_panel_group.py (PME2 layer separation)

LAYER = "editors"

import bpy
from bpy import types as bpy_types
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Header, Operator, Panel
from ..core.constants import PANEL_FOLDER, PANEL_FILE, F_RIGHT, F_PRE
from ..core.schema import schema
from ..infra.collections import MoveItemOperator
from .base import EditorBase, PME_OT_pm_edit, PME_OT_pm_add
from ..addon import get_prefs, ic, ic_cb
from ..ui.layout import lh, operator, draw_pme_layout
from ..ui import utitle, tag_redraw
from ..ui.utils import draw_menu
from ..bl_utils import bl_context
# NOTE: WM_OT_pme_user_pie_menu_call is needed for _draw_item method reference
from ..operators import WM_OT_pme_user_pie_menu_call
from ..ui import panels as PAU
from ..ui.panels import (
    panel,
    PLayout,
)
from .. import pme
from ..infra.utils import extract_str_flags_b

# =============================================================================
# Schema Definitions (PANEL)
# =============================================================================
schema.BoolProperty("pg", "pg_wicons")
schema.StringProperty("pg", "pg_context", "ANY")
schema.StringProperty("pg", "pg_category", "My Category")
schema.StringProperty("pg", "pg_space", "VIEW_3D")
schema.StringProperty("pg", "pg_region", "TOOLS")


class PME_OT_panel_sub_toggle(Operator):
    bl_idname = "pme.panel_sub_toggle"
    bl_label = "Toggle Panel/Sub-panel"
    bl_description = "Toggle panel/sub-panel"
    bl_options = {'INTERNAL'}

    idx: IntProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        if self.idx == 0:
            return {'FINISHED'}

        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]
        pmi.icon = PANEL_FOLDER if pmi.icon else PANEL_FILE

        pm.update_panel_group()
        return {'FINISHED'}


class PME_OT_toolbar_menu(Operator):
    bl_idname = "pme.toolbar_menu"
    bl_label = "Toolbar Menu"
    bl_description = "Toolbar menu"
    bl_options = {'INTERNAL'}

    name: StringProperty(options={'SKIP_SAVE'})

    def draw_toolbar_menu(self, menu, context):
        lh.lt(menu.layout)

        base_name = "Toolbar"
        screen_name = context.screen.name
        combined_name = f"{base_name} {screen_name}"
        position_name = PME_PT_toolbar.determine_panel_position(context)
        combined_pos_name = f"{combined_name} {position_name}"
        final_position_name = f"{base_name} {position_name}"

        lh.operator(
            self.bl_idname, "Create Toolbar (Current Screen)", 'ADD', name=combined_pos_name
        )
        lh.operator(
            self.bl_idname, "Create Toolbar (All Screens)", 'ADD', name=final_position_name
        )

    def execute(self, context):
        if not self.name:
            context.window_manager.popup_menu(
                self.draw_toolbar_menu, title="Pie Menu Editor"
            )
        else:
            pr = get_prefs()
            pr.add_pm('DIALOG', self.name)
            pr.update_tree()
            tag_redraw()
            pr.tab = 'EDITOR'
            bpy.ops.pme.popup_addon_preferences(
                'INVOKE_DEFAULT', addon="pie_menu_editor"
            )

        return {'FINISHED'}


class PME_PT_toolbar(Panel):
    bl_label = "PME Toolbar"
    bl_space_type = 'PREFERENCES'
    bl_region_type = 'WINDOW'
    bl_options = {'HIDE_HEADER'}

    @staticmethod
    def determine_panel_position(context):
        area = context.area
        center_x = context.window.width // 2
        center_y = context.window.height // 2

        if area.width > area.height:
            return "Bottom" if area.y < center_y else "Top"
        else:
            return "Left" if area.x < center_x else "Right"

    @staticmethod
    def is_area_vertical(context):
        return context.area.width <= context.area.height

    @staticmethod
    def needs_vertical_layout(panel_position):
        return panel_position in {"Left", "Right"}

    @classmethod
    def poll(cls, context):
        preferences = get_prefs()
        area = context.area
        is_narrow_width = (area.width <= preferences.toolbar_width)
        is_narrow_height = (area.height <= preferences.toolbar_height)
        return (is_narrow_width or is_narrow_height)

    def draw(self, context):
        lh.lt(self.layout)

        # Create names
        base_name = "Toolbar"
        screen_name = context.screen.name
        combined_base = f"{base_name} {screen_name}"
        panel_position = self.determine_panel_position(context)
        final_position_name = f"{base_name} {panel_position}"
        combined_position_name = f"{combined_base} {panel_position}"

        menu_exists = (
            draw_menu(combined_position_name)
            or draw_menu(final_position_name)
            or draw_menu(combined_base)
            or draw_menu(base_name)
        )

        if not menu_exists:
            is_vertical_panel = self.needs_vertical_layout(panel_position)

            lh.row()
            lh.layout.alignment = 'CENTER'
            scale_factor = 1.5 if is_vertical_panel else 1
            lh.layout.scale_x = lh.layout.scale_y = scale_factor

            operator_label = "" if is_vertical_panel else "Pie Menu Editor"

            lh.operator(PME_OT_toolbar_menu.bl_idname, operator_label, icon_id='COLOR')


def draw_pme_panel(self, context):
    pr = get_prefs()
    if self.pme_data in pr.pie_menus:
        pm = pr.pie_menus[self.pme_data]
        if issubclass(self.__class__, Header):
            if not self.__class__.poll(context):
                return
            self.layout.separator()
        scale_x = 1
        if getattr(self, "pm_name", None) in pr.pie_menus:
            pg = pr.pie_menus[self.pm_name]
            prop = schema.parse(pg.data)
            scale_x = -1 if prop.pg_wicons else 1

        draw_pme_layout(
            pm,
            self.layout.column(align=True),
            WM_OT_pme_user_pie_menu_call._draw_item,
            None,
            scale_x,
        )

    else:
        tp = PAU.hidden_panel(self.pme_data) or getattr(bpy_types, self.pme_data, None)
        if not tp:
            return
        pme.context.layout = self.layout
        panel(tp, False, False, root=True)


def poll_pme_panel(cls, context):
    pr = get_prefs()
    if cls.pm_name not in pr.pie_menus:
        return True

    pm = pr.pie_menus[cls.pm_name]
    return pm.poll(cls, context)


def find_pms_by_extend_target(extend_target, mode):
    """Find existing pms with the same extend_target.

    Args:
        extend_target: Blender Panel/Menu/Header ID
        mode: 'DIALOG' or 'RMENU'

    Returns:
        List of matching pms
    """
    pr = get_prefs()
    prefix = "pd" if mode == 'DIALOG' else "rm"
    target_key = f"{prefix}_extend_target"

    # Clean search target (remove _pre/_right suffix if present)
    clean_search_target, _, _ = extract_str_flags_b(extend_target, F_RIGHT, F_PRE)

    results = []
    for pm in pr.pie_menus:
        if pm.mode != mode:
            continue
        # TODO(Phase 9-X): Remove pm.name fallback when all data is migrated (v3.0+)
        pm_target = pm.get_data(target_key)
        if not pm_target:
            pm_target, _, _ = extract_str_flags_b(pm.name, F_RIGHT, F_PRE)
        else:
            # Also clean pm_target in case it has suffix
            pm_target, _, _ = extract_str_flags_b(pm_target, F_RIGHT, F_PRE)

        if pm_target == clean_search_target:
            results.append(pm)

    return results


class PME_OT_extend_confirm(Operator):
    """Confirm dialog when extend menu already exists for this target."""
    bl_idname = "pme.extend_confirm"
    bl_label = "Extend Menu"
    bl_options = {'INTERNAL'}

    mode: StringProperty()
    # Phase 9-X (#97): Direct extend parameters
    extend_target: StringProperty()
    extend_side: StringProperty(default="append")  # "prepend" | "append"
    extend_order: IntProperty(default=0)
    extend_is_right: BoolProperty(default=False)  # Header right region

    def _draw(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        existing = find_pms_by_extend_target(self.extend_target, self.mode)

        lh.label(f"'{self.extend_target}' already has extensions:")
        lh.sep()

        # Add New option - pass extend_target, extend_side, extend_order
        # Phase 9-X (#97): Use descriptive name "Extend <target> <side> [Right]"
        # Clean extend_target (remove _pre/_right suffix if present)
        clean_target, _, _ = extract_str_flags_b(self.extend_target, F_RIGHT, F_PRE)
        side_label = "Pre" if self.extend_side == "prepend" else "App"
        # Add "Right" suffix for TOPBAR right region
        right_suffix = " Right" if self.extend_is_right else ""
        menu_name = f"Extend {clean_target} {side_label}{right_suffix}"
        lh.operator(
            PME_OT_pm_add.bl_idname,
            "Add New Extension",
            'ADD',
            mode=self.mode,
            name=menu_name,
            extend_target=clean_target,
            extend_side=self.extend_side,
            extend_order=self.extend_order,
            extend_is_right=self.extend_is_right,
        )

        lh.sep()
        lh.label("Or go to existing:")

        # Go to existing options
        for pm in existing:
            prefix = "pd" if self.mode == 'DIALOG' else "rm"
            side = pm.get_data(f"{prefix}_extend_side") or ""
            order = pm.get_data(f"{prefix}_extend_order") or 0
            lh.operator(
                "wm.pm_select",
                f"{pm.name} ({side} {order})",
                'FORWARD',
                pm_name=pm.name
            )

    def execute(self, context):
        context.window_manager.popup_menu(self._draw, title="Extend Menu")
        return {'CANCELLED'}


class PME_OT_panel_menu(Operator):
    bl_idname = "pme.panel_menu"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    panel: StringProperty()
    is_right_region: BoolProperty()

    def extend_ui_operator(self, label, icon, mode, extend_target, is_prepend, is_right=False):
        """Draw extend UI operator button.

        Phase 9-X (#97): Uses extend_side + extend_order.

        Args:
            label: Button label
            icon: Button icon
            mode: 'DIALOG' or 'RMENU'
            extend_target: Blender Panel/Menu/Header ID
            is_prepend: True for prepend, False for append
            is_right: True for right region (Header only)
        """
        from ..infra.extend import extend_manager

        existing = find_pms_by_extend_target(extend_target, mode)
        extend_side = "prepend" if is_prepend else "append"
        # Get next order for this specific region (is_right matters for Headers)
        extend_order = extend_manager.get_next_order(
            extend_target, extend_side, is_right=is_right
        )

        if existing:
            # Show confirmation popup
            # Clean extend_target (remove _pre/_right suffix if present)
            clean_target, _, _ = extract_str_flags_b(extend_target, F_RIGHT, F_PRE)
            lh.operator(
                PME_OT_extend_confirm.bl_idname,
                label,
                icon,
                mode=mode,
                extend_target=clean_target,
                extend_side=extend_side,
                extend_order=extend_order,
                extend_is_right=is_right,
            )
        else:
            # No existing, add directly with extend parameters
            # Phase 9-X (#97): Use descriptive name "Extend <target> <side> [Right]"
            # Clean extend_target (remove _pre/_right suffix if present)
            clean_target, _, _ = extract_str_flags_b(extend_target, F_RIGHT, F_PRE)
            side_label = "Pre" if is_prepend else "App"
            # Add "Right" suffix for TOPBAR right region
            right_suffix = " Right" if is_right else ""
            menu_name = f"Extend {clean_target} {side_label}{right_suffix}"
            lh.operator(
                PME_OT_pm_add.bl_idname,
                label,
                icon,
                mode=mode,
                name=menu_name,
                extend_target=clean_target,
                extend_side=extend_side,
                extend_order=extend_order,
                extend_is_right=is_right,
            )

    def draw_header_menu(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        pr = get_prefs()
        pm = pr.selected_pm

        # Phase 9-X (#97): Pass extend_target, is_prepend, and is_right
        self.extend_ui_operator(
            "Extend Header", 'TRIA_LEFT', 'DIALOG', self.panel, True,
            is_right=self.is_right_region
        )

        self.extend_ui_operator(
            "Extend Header", 'TRIA_RIGHT', 'DIALOG', self.panel, False,
            is_right=self.is_right_region
        )

        lh.operator(
            "pme.clipboard_copy", "Copy Menu ID", 'COPYDOWN', text=self.panel
        )

        lh.sep()

        lh.operator(
            "wm.pm_select",
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )
        lh.operator("pme.pm_search_and_select", None, 'VIEWZOOM')

        lh.sep()

        lh.prop(pr, "debug_mode")
        lh.prop(pr, "interactive_panels")

    def draw_menu_menu(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        pr = get_prefs()
        pm = pr.selected_pm

        if pm:
            tp = getattr(bpy_types, self.panel, None)
            label = tp and getattr(tp, "bl_label", None) or self.panel

            if pm.mode in {'PMENU', 'RMENU', 'DIALOG'}:
                lh.operator(
                    PME_OT_pm_edit.bl_idname,
                    "Add as Menu to '%s'" % pm.name,
                    'ADD',
                    auto=False,
                    name=label,
                    mode='CUSTOM',
                    text="L.menu(menu='%s', text=slot, icon=icon, "
                    "icon_value=icon_value)" % self.panel,
                )

                lh.sep()

        # Phase 9-X (#97): Pass extend_target and is_prepend
        self.extend_ui_operator(
            "Extend Menu", 'TRIA_UP', 'RMENU', self.panel, True
        )
        self.extend_ui_operator("Extend Menu", 'TRIA_DOWN', 'RMENU', self.panel, False)

        lh.operator(
            "pme.clipboard_copy", "Copy Menu ID", 'COPYDOWN', text=self.panel
        )

        lh.sep()

        lh.operator(
            "wm.pm_select",
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )
        lh.operator("pme.pm_search_and_select", None, 'VIEWZOOM')

        lh.sep()

        lh.prop(pr, "debug_mode")
        lh.prop(pr, "interactive_panels")

    def draw_panel_menu(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        pr = get_prefs()
        pm = pr.selected_pm

        lh.operator(
            "pme.panel_hide",
            "Hide Panel",
            'GHOST_DISABLED',
            panel=self.panel,
        )

        if pm:
            tp = PAU.hidden_panel(self.panel) or getattr(bpy_types, self.panel, None)
            label = tp and getattr(tp, "bl_label", None) or self.panel

            if pm.mode in {'PMENU', 'RMENU', 'DIALOG', 'SCRIPT'}:
                lh.operator(
                    PME_OT_pm_edit.bl_idname,
                    "Add as Button to '%s'" % pm.name,
                    'ADD',
                    auto=False,
                    name=label,
                    mode='COMMAND',
                    text=(
                        "bpy.ops.pme.popup_panel(" "panel='%s', frame=True, area='%s')"
                    )
                    % (self.panel, context.area.type),
                )

                lh.operator(
                    PME_OT_pm_edit.bl_idname,
                    "Add as Popover to '%s'" % pm.name,
                    'ADD',
                    auto=False,
                    name=label,
                    mode='CUSTOM',
                    text=(
                        "L.popover("
                        "panel='%s', "
                        "text=slot, icon=icon, icon_value=icon_value)"
                    )
                    % self.panel,
                )

            if pm.mode == 'PANEL':
                lh.operator(
                    PME_OT_panel_add.bl_idname,
                    "Add as Panel to '%s'" % pm.name,
                    'ADD',
                    panel=self.panel,
                    mode='BLENDER',
                )

            elif pm.mode == 'DIALOG':
                lh.operator(
                    PME_OT_panel_add.bl_idname,
                    "Add as Panel to '%s'" % pm.name,
                    'ADD',
                    panel=self.panel,
                    mode='DIALOG',
                )

            elif pm.mode == 'PMENU':
                lh.operator(
                    PME_OT_pm_edit.bl_idname,
                    "Add as Panel to '%s'" % pm.name,
                    'ADD',
                    auto=False,
                    name=label,
                    mode='CUSTOM',
                    text="panel('%s', area='%s')" % (self.panel, context.area.type),
                )

            lh.sep()

        self.extend_ui_operator(
            "Extend Panel", 'TRIA_UP', 'DIALOG', self.panel + F_PRE, True
        )
        self.extend_ui_operator("Extend Panel", 'TRIA_DOWN', 'DIALOG', self.panel, False)

        lh.operator(
            "pme.clipboard_copy",
            "Copy Panel ID",
            'COPYDOWN',
            text=self.panel,
        )

        lh.sep()

        lh.operator(
            "wm.pm_select",
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )
        lh.operator("pme.pm_search_and_select", None, 'VIEWZOOM')

        lh.sep()

        lh.prop(pr, "debug_mode")
        lh.prop(pr, "interactive_panels")

    def execute(self, context):
        if '_HT_' in self.panel:
            context.window_manager.popup_menu(self.draw_header_menu, title=self.panel)
        elif '_MT_' in self.panel:
            context.window_manager.popup_menu(self.draw_menu_menu, title=self.panel)
        else:
            context.window_manager.popup_menu(self.draw_panel_menu, title=self.panel)
        return {'FINISHED'}


class PME_OT_interactive_panels_toggle(Operator):
    bl_idname = "pme.interactive_panels_toggle"
    bl_label = "Toggle Interactive Panels (PME)"
    bl_description = "Toggle panel tools"
    bl_options = {'REGISTER'}

    active = False
    enabled = True

    action: EnumProperty(
        items=(
            ('TOGGLE', "Toggle", ""),
            ('ENABLE', "Enable", ""),
            ('DISABLE', "Disable", ""),
        ),
        options={'SKIP_SAVE'},
    )

    @staticmethod
    def _draw(self, context):
        # if not PME_OT_interactive_panels_toggle.enabled or \
        #         PLayout.active:
        #     return
        if panel.active:
            return

        lh.lt(self.layout.row(align=True))
        lh.layout.alert = True
        # is_pg = pm.mode == 'PANEL' or pm.mode == 'HPANEL' or \
        #     pm.mode == 'DIALOG'
        # lh.operator(
        #     "wm.pm_select",
        #     "" if is_pg else "Select Item",
        #     pm.ed.icon if is_pg else 'NONE',
        #     mode={'PANEL', 'HPANEL', 'DIALOG'})

        tp = self.__class__
        tp_name = tp.bl_idname if hasattr(tp, "bl_idname") else tp.__name__

        lh.operator(PME_OT_panel_menu.bl_idname, "PME Tools", 'COLOR', panel=tp_name)

        # lh.operator(
        #     PME_OT_interactive_panels_toggle.bl_idname, "", 'QUIT',
        #     action='DISABLE')

    @staticmethod
    def _draw_menu(self, context):
        # if not PME_OT_interactive_panels_toggle.enabled or \
        #         PLayout.active:
        #     return
        if panel.active:
            return

        tp = self.__class__
        tp_name = tp.bl_idname if hasattr(tp, "bl_idname") else tp.__name__

        lh.lt(self.layout)
        lh.layout.alert = True
        lh.sep()

        lh.operator(PME_OT_panel_menu.bl_idname, "PME Tools", 'COLOR', panel=tp_name)

    @staticmethod
    def _draw_header(self, context):
        if panel.active:
            return

        tp = self.__class__
        tp_name = tp.bl_idname if hasattr(tp, "bl_idname") else tp.__name__

        lh.lt(self.layout)
        lh.layout.alert = True
        lh.sep()

        lh.operator(
            PME_OT_panel_menu.bl_idname,
            "PME Tools",
            'COLOR',
            panel=tp_name,
            is_right_region=context.region.alignment == 'RIGHT',
        )

    def execute(self, context):
        pr = get_prefs()
        if (
            self.action == 'ENABLE'
            or self.action == 'TOGGLE'
            and not pr.interactive_panels
        ):
            pr.interactive_panels = True
        else:
            pr.interactive_panels = False
            PLayout.editor = False

        # if self.__class__.ahpg and self.hpg:
        #     self.__class__.ahpg = self.hpg
        #     return {'FINISHED'}

        return {'FINISHED'}


class PME_OT_panel_add(Operator):
    bl_idname = "pme.panel_add"
    bl_label = "Add Panel"
    bl_description = "Add panel"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        if not PME_OT_panel_add.enum_items:
            enum_items = []

            if self.mode == 'BLENDER':

                def _add_item(tp_name, tp):
                    ctx, _, name = tp_name.partition("_PT_")
                    label = hasattr(tp, "bl_label") and tp.bl_label or name or tp_name
                    if name:
                        if name == label or utitle(name) == label:
                            label = "[%s] %s" % (ctx, utitle(label))
                        else:
                            label = "[%s] %s (%s)" % (ctx, label, name)

                    enum_items.append((tp_name, label, ""))

                for tp in PAU.bl_panel_types():
                    _add_item(
                        tp.bl_idname if hasattr(tp, "bl_idname") else tp.__name__, tp
                    )

                for tp_name, tp in PAU.get_hidden_panels().items():
                    _add_item(tp_name, tp)

            elif self.mode == 'PME':
                for pm in get_prefs().pie_menus:
                    if pm.mode == 'DIALOG':
                        enum_items.append((pm.name, pm.name, ""))

            PME_OT_panel_add.enum_items = enum_items

        return PME_OT_panel_add.enum_items

    item: EnumProperty(items=get_items, options={'SKIP_SAVE'})
    index: IntProperty(default=-1, options={'SKIP_SAVE'})
    mode: StringProperty(options={'SKIP_SAVE'})
    panel: StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        if not self.panel:
            self.panel = self.item

        pm = pr.selected_pm

        if self.mode == 'BLENDER' or self.mode == 'DIALOG':
            tp = PAU.hidden_panel(self.panel) or getattr(bpy_types, self.panel, None)
            if not tp:
                return {'CANCELLED'}

        if self.mode == 'DIALOG':
            pmi = pm.ed.add_pd_row(pm)
            pmi.mode = 'CUSTOM'
            pmi.text = (
                "panel(" "'%s', frame=True, header=True, expand=None, area='%s')"
            ) % (self.panel, context.area.type)
        else:
            pmi = pm.pmis.add()
            pmi.mode = 'MENU'
            pmi.text = self.panel

        if self.mode == 'BLENDER' or self.mode == 'DIALOG':
            if hasattr(tp, "bl_label") and tp.bl_label:
                pmi.name = tp.bl_label
            else:
                ctx, _, name = self.panel.partition("_PT_")
                pmi.name = utitle(name if name else ctx)

        elif self.mode == 'PME':
            pmi.name = self.panel

        idx = len(pm.pmis) - 1
        if self.index != -1 and self.index != idx:
            pm.pmis.move(idx, self.index)
            idx = self.index

        if pm.mode == 'PANEL':
            pm.update_panel_group()

        if self.mode == 'PME':
            pr.update_tree()

        tag_redraw()
        return {'FINISHED'}

    def _draw(self, menu, context):
        pr = get_prefs()
        lh.lt(menu.layout, 'INVOKE_DEFAULT')
        lh.operator(
            self.__class__.bl_idname,
            "Popup Dialog",
            pr.ed('DIALOG').icon,
            mode='PME',
            index=self.index,
        )
        lh.operator(
            self.__class__.bl_idname,
            "Panel",
            'BLENDER',
            mode='BLENDER',
            index=self.index,
        )

        lh.sep()

        lh.prop(get_prefs(), "interactive_panels")

    def invoke(self, context, event):
        if not self.mode:
            context.window_manager.popup_menu(self._draw)
        elif not self.panel:
            PME_OT_panel_add.enum_items = None
            context.window_manager.invoke_search_popup(self)
        else:
            return self.execute(context)
        return {'FINISHED'}


class PME_OT_panel_item_move(MoveItemOperator, Operator):
    bl_idname = "pme.panel_item_move"

    def get_icon(self, item, idx):
        return 'FILE' if item.icon == PANEL_FILE else 'FILE_FOLDER'

    def get_collection(self):
        return get_prefs().selected_pm.pmis

    def finish(self):
        pr = get_prefs()
        pm = pr.selected_pm
        if self.new_idx == 0:
            pm.pmis[0].icon = PANEL_FOLDER

        pm.update_panel_group()
        tag_redraw()


class PME_OT_panel_item_remove(Operator):
    bl_idname = "pme.panel_item_remove"
    bl_label = "Remove Panel"
    bl_description = "Remove the panel"
    bl_options = {'INTERNAL'}

    idx: IntProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm

        PAU.remove_panel(pm.name, self.idx)

        pm.pmis.remove(self.idx)

        pr.update_tree()
        tag_redraw()
        return {'CANCELLED'}


class Editor(EditorBase):

    def __init__(self):
        self.id = 'PANEL'
        EditorBase.__init__(self)

        self.docs = "#Panel_Group_Editor"
        self.use_preview = False
        self.sub_item = False
        self.has_hotkey = False
        self.default_pmi_data = "pg?"
        self.supported_slot_modes = {'EMPTY', 'MENU'}

    def init_pm(self, pm):
        if pm.enabled:
            PAU.add_panel_group(pm, draw_pme_panel, poll_pme_panel)

    def on_pm_remove(self, pm):
        PAU.remove_panel_group(pm.name)
        super().on_pm_remove(pm)

    def on_pm_duplicate(self, from_pm, pm):
        EditorBase.on_pm_duplicate(self, from_pm, pm)
        if pm.enabled:
            PAU.add_panel_group(pm, draw_pme_panel, poll_pme_panel)

    def on_pm_enabled(self, pm, value):
        super().on_pm_enabled(pm, value)

        if pm.enabled:
            PAU.add_panel_group(pm, draw_pme_panel, poll_pme_panel)
        else:
            PAU.remove_panel_group(pm.name)

    def on_pm_rename(self, pm, name):
        super().on_pm_rename(pm, name)
        PAU.rename_panel_group(pm.name, name)

    def on_pmi_rename(self, pm, pmi, old_name, name):
        for item in pm.pmis:
            if item == pmi:
                pmi.name = name
                pm.update_panel_group()
                break

    def draw_keymap(self, layout, data):
        row = layout.row(align=True)
        row.prop(data, "panel_space", text="")
        row.prop(data, "panel_region", text="")

        if data.panel_region != 'HEADER':
            row = layout.row(align=True)
            row.prop(data, "panel_context", text="")

            ic_items = (
                get_prefs().rna_type.properties["panel_info_visibility"].enum_items
            )
            row.prop(data, "panel_category", text="", icon=ic(ic_items['CAT'].icon))

    def draw_hotkey(self, layout, data):
        pass

    def draw_extra_settings(self, layout, pm):
        EditorBase.draw_extra_settings(self, layout, pm)
        layout.prop(pm, "panel_wicons")

    def draw_items(self, layout, pm):
        pr = get_prefs()
        col = layout.column(align=True)

        for idx, pmi in enumerate(pm.pmis):
            lh.row(col)

            if pmi.icon == PANEL_FILE:
                lh.operator("pme.panel_sub_toggle", "", 'BLANK1', idx=idx)

            lh.operator(
                "pme.panel_sub_toggle",
                "",
                'FILE' if pmi.icon == PANEL_FILE else 'FILE_FOLDER',
                idx=idx,
            )
            icon = (
                pr.ed('DIALOG').icon if pmi.text in get_prefs().pie_menus else 'BLENDER'
            )
            lh.prop(pmi, "label", "", icon)

            # lh.operator(
            #     PME_OT_panel_item_menu.bl_idname,
            #     "", 'COLLAPSEMENU',
            #     idx=idx)

            self.draw_pmi_menu_btn(pr, idx)

        lh.row(col)
        lh.operator(PME_OT_panel_add.bl_idname, "Add Panel")

    def draw_pmi_menu(self, context, idx):
        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[idx]

        text, *_ = pmi.parse()
        lh.label(
            text if text.strip() else "Menu",
            pr.ed('DIALOG').icon if pmi.text in pr.pie_menus else 'BLENDER',
        )

        lh.sep(check=True)

        lh.operator(
            "pme.panel_sub_toggle",
            "Sub-Panel",
            ic_cb(pmi.icon == PANEL_FILE),
            idx=idx,
        )

        lh.sep(check=True)

        lh.operator(PME_OT_panel_add.bl_idname, "Add Panel", 'ADD', index=idx)

        if len(pm.pmis) > 1:
            lh.operator(
                PME_OT_panel_item_move.bl_idname, "Move Panel", 'FORWARD', old_idx=idx
            )

            lh.sep(check=True)

        lh.operator(PME_OT_panel_item_remove.bl_idname, "Remove", 'X', idx=idx)

    def update_panel_group(self, pm):
        PAU.remove_panel_group(pm.name)
        PAU.add_panel_group(pm, draw_pme_panel, poll_pme_panel)


def register():
    Editor()
