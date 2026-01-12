# pyright: reportInvalidTypeForm=false
# preferences.py - PMEPreferences and addon settings UI
# LAYER = "prefs"

import bpy
from bpy import app, types as bpy_types
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import (
    AddonPreferences,
    Menu,
    Operator,
    Panel,
    PropertyGroup,
    UIList,
    UILayout,
    UI_UL_list,
    USERPREF_PT_addons,
    # WM_MT_button_context: use getattr() at runtime for portable Blender compatibility
    WindowManager,
)
import os
import json
import re
from types import MethodType
from bpy_extras.io_utils import ExportHelper, ImportHelper

LAYER = "prefs"

from .addon import (
    ADDON_ID,
    ADDON_PATH,
    SCRIPT_PATH,
    SAFE_MODE,
    prefs,
    get_prefs,
    get_uprefs,
    temp_prefs,
    print_exc,
    ic,
    ic_fb,
    ic_cb,
    ic_eye,
)
from .core import constants as CC
from . import operators as OPS
from .operators import extras as EOPS
from .bl_utils import (
    bp,
    uname,
    bl_context,
    gen_prop_path,
    ConfirmBoxHandler,
    message_box,
)
from .infra.collections import BaseCollectionItem, sort_collection
from .ui.layout import lh, operator, split
from .infra.debug import *
from .ui.panels import (
    hide_panel,
    unhide_panel,
    add_panel,
    hidden_panel,
    rename_panel_group,
    remove_panel_group,
    panel_context_items,
    bl_panel_types,
    bl_menu_types,
    bl_header_types,
)
from .infra.macro import add_macro, remove_macro, update_macro
from .infra.modal import encode_modal_data
from . import addon
from . import keymap_helper
from . import pme
from . import operator_utils
from .infra.compat import fix_json, fix
from .infra.io import (
    read_import_file,
    write_export_file,
    parse_json_data,
    BackupManager,
    get_user_exports_dir,
    get_user_icons_dir,
    iter_script_dirs,
)
from .keymap_helper import (
    KeymapHelper,
    MOUSE_BUTTONS,
    add_mouse_button,
    remove_mouse_button,
    to_key_name,
    to_ui_hotkey,
)
from .infra.previews import ph
from .infra.overlay import OverlayPrefs
from .ui import tag_redraw, draw_addons_maximized, is_userpref_maximized
from .ui.utils import get_pme_menu_class, execute_script
from .infra import utils as U
from .infra.property import PropertyData, to_py_value
from .pme_types import Tag, PMItem, PMIItem, PMLink, EdProperties, UserProperties
# Editor operators (moved to operators/ed/ in Phase 5-A)
from .operators.ed import (
    WM_OT_pmi_icon_select,
    WM_OT_pmi_data_edit,
    PME_OT_pm_edit,
    PME_OT_pmi_cmd_generate,
    PME_OT_tags_filter,
    PME_OT_tags,
    PME_OT_pm_add,
    WM_OT_pmi_icon_tag_toggle,
)
from .editors.panel_group import (
    PME_OT_interactive_panels_toggle,
    draw_pme_panel,
    poll_pme_panel,
)
from .editors.sticky_key import PME_OT_sticky_key_edit
from .editors.modal import PME_OT_prop_data_reset

# IO operators (moved to operators/io.py in Phase 2-C)
from .operators.io import (
    WM_OT_pm_import,
    WM_OT_pm_export,
    PME_OT_backup,
    import_filepath,
    export_filepath,
)

# P1: Helper classes (moved to prefs/helpers.py)
from .prefs.helpers import PMIClipboard, PieMenuPrefs, PieMenuRadius

# P2: Session data (moved to prefs/temp_data.py)
from .prefs.temp_data import PMEData, update_pmi_data, update_data

# P3: PMI data (moved to prefs/pmi_data.py)
from .prefs.pmi_data import PMIData

# P4: UIList classes (moved to prefs/lists.py)
from .prefs.lists import WM_UL_panel_list, WM_UL_pm_list

# P5: PM operators (moved to prefs/pm_ops.py)
from .prefs.pm_ops import (
    WM_OT_pm_duplicate,
    PME_OT_pm_remove,
    PME_OT_pm_enable_all,
    PME_OT_pm_enable_by_tag,
    PME_OT_pm_remove_by_tag,
    WM_OT_pm_move,
    WM_OT_pm_sort,
)

# P6: Tree system (moved to prefs/tree.py)
from .prefs.tree import (
    tree_state,
    TreeState,
    PME_UL_pm_tree,
    TreeView,
    PME_OT_tree_folder_toggle,
    PME_OT_tree_folder_toggle_all,
    PME_OT_tree_group_toggle,
)

# P7: Context menu (moved to prefs/context_menu.py)
from .prefs.context_menu import (
    PME_OT_list_specials,
    PME_MT_button_context,
    PME_OT_context_menu,
    button_context_menu,
    add_rmb_menu,
)

# P8: Small operators and panel (moved to prefs/operators.py)
from .prefs.operators import (
    PME_OT_pmi_name_apply,
    PME_OT_icons_refresh,
    InvalidPMEPreferences,
    PME_PT_preferences,
)

# update_pmi_data, update_data moved to prefs/temp_data.py


# WM_OT_pm_import moved to operators/io.py
# WM_OT_pm_export moved to operators/io.py
# PME_OT_backup moved to operators/io.py



# PM operators moved to prefs/pm_ops.py
# PME_OT_pmi_name_apply, PME_OT_icons_refresh moved to prefs/operators.py
# PMEData moved to prefs/temp_data.py
# WM_UL_panel_list, WM_UL_pm_list moved to prefs/lists.py
# PME_UL_pm_tree, TreeView, tree_ops moved to prefs/tree.py
# PMIClipboard moved to prefs/helpers.py
# PME_OT_list_specials moved to prefs/context_menu.py
# PMIData moved to prefs/pmi_data.py
# PieMenuPrefs, PieMenuRadius moved to prefs/helpers.py
# InvalidPMEPreferences moved to prefs/operators.py


class PMEPreferences(AddonPreferences):
    bl_idname = ADDON_ID

    _mode = 'ADDON'
    editors = {}
    mode_history = []
    unregistered_pms = []
    old_pms = set()
    missing_kms = {}
    pie_menu_prefs = PieMenuPrefs()
    pie_menu_radius = PieMenuRadius()
    tree = TreeView()
    pmi_clipboard = PMIClipboard()
    pdr_clipboard = []
    rmc_clipboard = []
    window_kmis = []

    version: IntVectorProperty(size=3)
    pie_menus: CollectionProperty(type=PMItem)
    props: PointerProperty(type=UserProperties)

    def update_active_pie_menu_idx(self, context):
        self.pmi_data.info()
        temp_prefs().hidden_panels_idx = 0
        # Ignore invalid/empty selection
        if 0 <= self.active_pie_menu_idx < len(self.pie_menus):
            # Valid index only - guard for initialization phase
            ed = self.selected_pm.ed
            if ed:
                ed.on_pm_select(self.selected_pm)

    active_pie_menu_idx: IntProperty(
        default=0, update=update_active_pie_menu_idx
    )

    overlay: PointerProperty(type=OverlayPrefs)
    list_size: IntProperty(
        name="List Width",
        description="Width of the list",
        default=40,
        min=20,
        max=80,
        subtype='PERCENTAGE',
    )
    num_list_rows: IntProperty(
        name="List Rows Number",
        description="Number of list rows",
        default=10,
        min=5,
        max=50,
    )

    def update_interactive_panels(self, context=None):
        if PME_OT_interactive_panels_toggle.active == self.interactive_panels:
            return

        PME_OT_interactive_panels_toggle.active = self.interactive_panels

        for tp in bl_header_types():
            if self.interactive_panels:
                if isinstance(tp.append, MethodType) and hasattr(tp, "draw"):
                    tp.append(PME_OT_interactive_panels_toggle._draw_header)
            else:
                if isinstance(tp.remove, MethodType) and hasattr(tp, "draw"):
                    tp.remove(PME_OT_interactive_panels_toggle._draw_header)

        for tp in bl_menu_types():
            if self.interactive_panels:
                if isinstance(tp.append, MethodType) and hasattr(tp, "draw"):
                    tp.append(PME_OT_interactive_panels_toggle._draw_menu)
            else:
                if isinstance(tp.remove, MethodType) and hasattr(tp, "draw"):
                    tp.remove(PME_OT_interactive_panels_toggle._draw_menu)

        for tp in bl_panel_types():
            if getattr(tp, "bl_space_type", None) == 'PREFERENCES':
                continue

            if tp.__name__ == "PROPERTIES_PT_navigation_bar":
                continue

            if self.interactive_panels:
                if isinstance(tp.append, MethodType):
                    tp.append(PME_OT_interactive_panels_toggle._draw)
            else:
                if isinstance(tp.remove, MethodType):
                    tp.remove(PME_OT_interactive_panels_toggle._draw)

        tag_redraw(True)

    interactive_panels: BoolProperty(
        name="Interactive Panels",
        description="Interactive panels",
        update=update_interactive_panels,
    )

    auto_backup: BoolProperty(
        name="Auto Backup", description="Auto backup menus", default=True
    )
    expand_item_menu: BoolProperty(
        name="Expand Slot Tools", description="Expand slot tools"
    )
    icon_filter: StringProperty(
        description="Filter", options={'TEXTEDIT_UPDATE'}
    )
    hotkey: PointerProperty(type=keymap_helper.Hotkey)
    hold_time: IntProperty(
        name="Hold Mode Timeout",
        description="Hold timeout (ms)",
        default=200,
        min=50,
        max=1000,
        step=10,
    )
    chord_time: IntProperty(
        name="Chord Mode Timeout",
        description="Chord timeout (ms)",
        default=300,
        min=50,
        max=1000,
        step=10,
    )
    use_chord_hint: BoolProperty(
        name="Show Next Key Chord",
        description="Show next key chord in the sequence",
        default=True,
    )
    tab: EnumProperty(
        items=(
            ('EDITOR', "Editor", ""),
            ('SETTINGS', "Settings", ""),
        ),
        options={'HIDDEN'},
    )

    def update_show_names(self, context):
        if not self.show_names and not self.show_hotkeys:
            self.show_hotkeys = True

    show_names: BoolProperty(
        default=True, description="Show names", update=update_show_names
    )

    def update_show_hotkeys(self, context):
        if not self.show_hotkeys and not self.show_names:
            self.show_names = True

    show_hotkeys: BoolProperty(
        default=True, description="Show hotkeys", update=update_show_hotkeys
    )

    def update_tree(self, context=None):
        self.tree.update()

    # def update_show_keymap_names(self, context=None):
    #     if self.tree_mode:
    #         if self.show_tags:
    #             self["show_tags"] = False
    #             PME_UL_pm_tree.collapsed_groups.clear()
    #         self.tree.update()

    show_keymap_names: BoolProperty(
        name="Keymap Names", default=False, description="Show keymap names"
    )

    # def update_show_tags(self, context=None):
    #     if self.tree_mode:
    #         if self.show_keymap_names:
    #             self["show_keymap_names"] = False
    #             PME_UL_pm_tree.collapsed_groups.clear()
    #         self.tree.update()

    show_tags: BoolProperty(
        name="Tags", default=False, description="Show tags"
    )

    def update_group_by(self, context=None):
        if self.tree_mode:
            tree_state.expanded_folders.clear()
            tree_state.collapsed_groups.clear()
            self.tree.update()
            if self.group_by != 'NONE':
                bpy.ops.pme.tree_group_toggle(all=True)

            PME_UL_pm_tree.save_state()

    group_by: EnumProperty(
        name="Group by",
        description="Group items by",
        items=(
            ('NONE', "None", "", ic('CHECKBOX_DEHLT'), 0),
            ('KEYMAP', "Keymap", "", ic('MOUSE_MMB'), 1),
            ('TYPE', "Type", "", ic('PROP_CON'), 2),
            ('TAG', "Tag", "", ic('SOLO_OFF'), 3),
            ('KEY', "Key", "", ic('FILE_FONT'), 4),
        ),
        update=update_group_by,
    )

    num_icons_per_row: IntProperty(
        name="Icons per Row", description="Icons per row", default=30, min=1, max=100
    )
    pie_extra_slot_gap_size: IntProperty(
        name="Extra Pie Slot Gap Size",
        description="Extra pie slot gap size",
        default=5,
        min=3,
        max=100,
    )
    show_custom_icons: BoolProperty(
        default=False, description="Show custom icons"
    )
    show_advanced_settings: BoolProperty(
        default=False, description="Advanced settings"
    )
    show_experimental_open_modes: BoolProperty(
        name="Show Experimental Hotkey Modes",
        description="Reveal experimental Click/Click Drag modes in Hotkey Mode picker",
        default=False,
    )
    show_list: BoolProperty(default=True, description="Show the list")
    show_sidepanel_prefs: BoolProperty(
        name="Show PME Preferences in 3DView's N-panel",
        description="Show PME preferences in 3D View N-panel",
    )

    use_filter: BoolProperty(description="Use filters", update=update_tree)
    mode_filter: EnumProperty(
        items=CC.PM_ITEMS_M,
        default=CC.PM_ITEMS_M_DEFAULT,
        description="Show items",
        options={'ENUM_FLAG'},
        update=update_tree,
    )
    tag_filter: StringProperty(update=update_tree)
    auto_tag_on_add: BoolProperty(
        name="Tag New Menus with Active Filter",
        default=False,
        description="When a tag filter is active, automatically assign that tag to newly created menus",
    )
    show_only_new_pms: BoolProperty(
        description="Show only new menus", update=update_tree
    )
    cache_scripts: BoolProperty(
        name="Cache External Scripts",
        description="Cache external scripts",
        default=True,
    )
    panel_info_visibility: EnumProperty(
        name="Panel Info",
        description="Show panel info",
        items=(
            ('NAME', "Name", "", 'SYNTAX_OFF', 1),
            ('CLASS', "Class", "", 'COPY_ID', 2),
            ('CTX', "Context", "", 'WINDOW', 4),
            ('CAT', "Category", "", 'MENU_PANEL', 8),
        ),
        default={'NAME', 'CLASS'},
        options={'ENUM_FLAG'},
    )
    show_pm_title: BoolProperty(
        name="Show Title", description="Show pie menu title", default=True
    )
    restore_mouse_pos: BoolProperty(
        name="Restore Mouse Position",
        description=("Restore mouse position " "after releasing the pie menu's hotkey"),
    )
    use_spacer: BoolProperty(
        name="Use 'Spacer' Separator by Default",
        description="Use 'Spacer' separator by default",
        default=False,
    )
    default_popup_mode: EnumProperty(
        description="Default popup mode",
        items=CC.PD_MODE_ITEMS,
        default='PANEL',
        update=lambda s, c: s.ed('DIALOG').update_default_pmi_data(),
    )
    use_cmd_editor: BoolProperty(
        name="Use Operator Properties Editor",
        description="Use operator properties editor in Command tab",
        default=True,
    )

    toolbar_width: IntProperty(
        name="Max Width",
        description="Maximum width of vertical toolbars",
        subtype='PIXEL',
        default=60,
    )
    toolbar_height: IntProperty(
        name="Max Height",
        description="Maximum height of horizontal toolbars",
        subtype='PIXEL',
        default=60,
    )

    def get_debug_mode(self):
        return app.debug_wm

    def set_debug_mode(self, value):
        app.debug_wm = value

    debug_mode: BoolProperty(
        name="Debug Mode",
        description=(
            "Enables extended debug information (via app.debug_wm),\n"
            "including operator logs for building custom PMEs."
        ),
        get=get_debug_mode,
        set=set_debug_mode,
    )
    show_error_trace: BoolProperty(
        name="Show Error Trace",
        description=(
            "Displays error traces for custom items and more.\n"
            "View them in the System Console to quickly identify and fix issues."
        ),
        default=True,
    )

    def update_tree_mode(self, context):
        if self.tree_mode:
            # if self.show_keymap_names and self.show_tags:
            #     self["show_keymap_names"] = False
            if self.save_tree:
                # Build tree first to populate groups, then restore saved state
                PME_UL_pm_tree.update_tree()
                PME_UL_pm_tree.load_state()
            else:
                # No saved state, start fresh
                tree_state.collapsed_groups.clear()
                tree_state.expanded_folders.clear()
                PME_UL_pm_tree.update_tree()
        else:
            # Save state when tree_mode is turned OFF
            if self.save_tree:
                PME_UL_pm_tree.save_state()

    tree_mode: BoolProperty(description="Tree Mode", update=update_tree_mode)

    def save_tree_update(self, context):
        if self.save_tree and self.tree_mode:
            PME_UL_pm_tree.save_state()

    save_tree: BoolProperty(
        name="Save and Restore Tree View State",
        description=("Save and restore tree view state\n" "from %s/data/tree.json file")
        % ADDON_ID,
        default=False,
        update=save_tree_update,
    )

    def get_maximize_prefs(self):
        return USERPREF_PT_addons.draw == draw_addons_maximized

    def set_maximize_prefs(self, value):
        if value and not is_userpref_maximized():
            bpy.ops.pme.userpref_show(addon="pie_menu_editor")

        elif not value and is_userpref_maximized():
            bpy.ops.pme.userpref_restore()

    maximize_prefs: BoolProperty(
        description="Maximize preferences area",
        get=get_maximize_prefs,
        set=set_maximize_prefs,
    )

    # use_square_buttons: BoolProperty(
    #     name="Use Square Icon-Only Buttons",
    #     description="Use square icon-only buttons")
    pmi_data: PointerProperty(type=PMIData)
    scripts_filepath: StringProperty(subtype='FILE_PATH', default=SCRIPT_PATH)

    def _update_mouse_threshold(self, context):
        OPS.PME_OT_modal_base.prop_data.clear()

    mouse_threshold_float: IntProperty(
        name="Slider (Float)",
        description="Slider (Float)",
        subtype='PIXEL',
        default=10,
        update=_update_mouse_threshold,
    )
    mouse_threshold_int: IntProperty(
        name="Slider (Int)",
        description="Slider (Integer)",
        subtype='PIXEL',
        default=20,
        update=_update_mouse_threshold,
    )
    mouse_threshold_bool: IntProperty(
        name="Checkbox (Bool)",
        description="Checkbox (Boolean)",
        subtype='PIXEL',
        default=40,
        update=_update_mouse_threshold,
    )
    mouse_threshold_enum: IntProperty(
        name="Drop-Down List (Enum)",
        description="Drop-down list (Enum)",
        subtype='PIXEL',
        default=40,
        update=_update_mouse_threshold,
    )
    use_mouse_threshold_bool: BoolProperty(
        description="Use mouse movement to change the value", default=True
    )
    use_mouse_threshold_enum: BoolProperty(
        description="Use mouse movement to change the value", default=True
    )
    mouse_dir_mode: EnumProperty(
        name="Mode",
        description="Mode",
        items=(
            ('H', "Horizontal", ""),
            ('V', "Vertical", ""),
        ),
    )

    @property
    def tree_ul(self):
        return PME_UL_pm_tree

    @property
    def selected_pm(self):
        if 0 <= self.active_pie_menu_idx < len(self.pie_menus):
            return self.pie_menus[self.active_pie_menu_idx]
        return None

    @property
    def mode(self):
        return PMEPreferences._mode

    @mode.setter
    def mode(self, value):
        PMEPreferences._mode = value

    def enter_mode(self, mode):
        self.mode_history.append(PMEPreferences._mode)
        PMEPreferences._mode = mode

    def leave_mode(self):
        PMEPreferences._mode = self.mode_history.pop()

    def is_edit_mode(self):
        return 'PMI' in PMEPreferences.mode_history

    @property
    def use_groups(self):
        return self.tree_mode and self.group_by != 'NONE'

    def get_threshold(self, prop_type=None):
        if prop_type == 'FLOAT':
            return self.mouse_threshold_float
        elif prop_type == 'INT':
            return self.mouse_threshold_int
        elif prop_type == 'ENUM':
            return self.mouse_threshold_enum
        elif prop_type == 'BOOL':
            return self.mouse_threshold_bool

        return 20

    def enable_window_kmis(self, value=True):
        for kmi in self.window_kmis:
            kmi.active = value

    def add_pm(self, mode='PMENU', name=None, duplicate=False,
               extend_target='', extend_side='', extend_order=0):
        """Add a new pie menu.

        Args:
            mode: Menu mode (PMENU, RMENU, DIALOG, etc.)
            name: Menu name (auto-generated if None)
            duplicate: Whether this is a duplicate operation
            extend_target: Phase 9-X (#97) - Blender Panel/Menu/Header ID to extend
            extend_side: Phase 9-X (#97) - "prepend" or "append"
            extend_order: Phase 9-X (#97) - Order within same target+side (0 = innermost)
        """
        link = None
        pr = get_prefs()
        tpr = temp_prefs()

        if self.active_pie_menu_idx < 0:
            self.active_pie_menu_idx = 0

        if self.tree_mode and len(tpr.links):
            link = tpr.links[tpr.links_idx]
            if link.path:
                self.active_pie_menu_idx = self.pie_menus.find(link.path[0])

        tpr.links_idx = -1

        self.pie_menus.add()
        if self.active_pie_menu_idx < len(self.pie_menus) - 1:
            self.active_pie_menu_idx +=1
        self.pie_menus.move(len(self.pie_menus) - 1, self.active_pie_menu_idx)
        pm = self.selected_pm

        pm.mode = mode

        # Generate uid (Phase 9-X: uid implementation)
        # Always generate new uid, even for duplicates
        from .core.uid import generate_uid
        pm.uid = generate_uid(mode)

        pm.name = self.unique_pm_name(name or pm.ed.default_name)

        if self.tree_mode and self.show_keymap_names and not duplicate and link:
            if link.label:
                pm.km_name = link.label
            elif link.path and link.path[0] in self.pie_menus:
                pm.km_name = self.pie_menus[link.path[0]].km_name
            elif link.pm_name and link.pm_name in self.pie_menus:
                pm.km_name = self.pie_menus[link.pm_name].km_name

            if pm.km_name in tree_state.collapsed_groups:
                tree_state.collapsed_groups.remove(pm.km_name)

        pm.data = pm.ed.default_pmi_data

        # Phase 9-X (#97): Set extend_target, extend_side, extend_order BEFORE on_pm_add()
        # This eliminates the need to parse from pm.name
        if extend_target and extend_side:
            if mode == 'DIALOG':
                pm.set_data("pd_extend_target", extend_target)
                pm.set_data("pd_extend_side", extend_side)
                pm.set_data("pd_extend_order", extend_order)
            elif mode == 'RMENU':
                pm.set_data("rm_extend_target", extend_target)
                pm.set_data("rm_extend_side", extend_side)
                pm.set_data("rm_extend_order", extend_order)

        if duplicate:
            apm = pr.pie_menus[name]

            pm.mode = apm.mode
            pm.km_name = apm.km_name
            if pm.km_name in tree_state.collapsed_groups:
                tree_state.collapsed_groups.remove(pm.km_name)

            pm.data = apm.data
            pm.open_mode = apm.open_mode
            pm.poll_cmd = apm.poll_cmd
            pm.tag = apm.tag

            # Phase 9-X: Register extend panel for duplicated menus
            if pm.mode in ('DIALOG', 'RMENU'):
                from .editors.base import extend_panel
                extend_panel(pm)

        else:
            pm.ed.on_pm_add(pm)

            if self.auto_tag_on_add and self.tag_filter and self.tag_filter != CC.UNTAGGED:
                pm.add_tag(self.tag_filter)
                Tag.filter()

        pm.register_hotkey()

        pm.ed.on_pm_select(pm)

        return pm

    def remove_pm(self, pm=None):
        tpr = temp_prefs()
        idx = 0

        if pm:
            idx = self.pie_menus.find(pm.name)
        else:
            idx = self.active_pie_menu_idx

        if idx < 0 or idx >= len(self.pie_menus):
            return

        apm = self.pie_menus[idx]
        new_idx = -1
        num_links = len(tpr.links)
        if pm is None and self.tree_mode and num_links:
            d = 1
            i = tpr.links_idx + d
            while True:
                if i >= num_links:
                    d = -1
                    i = tpr.links_idx + d
                    continue
                if i < 0:
                    break
                link = tpr.links[i]
                if not link.label and not link.path and link.pm_name != apm.name:
                    tpr.links_idx = i
                    new_idx = self.pie_menus.find(link.pm_name)
                    break
                i += d
        elif pm is not None:
            if idx + 1 < len(self.pie_menus):
                new_idx = idx + 1
            else:
                new_idx = idx

        apm.key_mod = 'NONE'

        apm.ed.on_pm_remove(apm)

        apm.unregister_hotkey()

        if apm.name in self.old_pms:
            self.old_pms.remove(apm.name)

        self.pie_menus.remove(idx)

        if new_idx >= idx:
            new_idx -= 1

        if new_idx >= 0:
            self.active_pie_menu_idx = new_idx
        elif (
            self.active_pie_menu_idx >= len(self.pie_menus)
            and self.active_pie_menu_idx > 0
        ):
            self.active_pie_menu_idx -= 1

    def unique_pm_name(self, name):
        return uname(self.pie_menus, name)

    def is_uid_unique(self, uid: str) -> bool:
        """Check if uid is unique among existing menus."""
        for pm in self.pie_menus:
            if pm.uid == uid:
                return False
        return True

    def get_all_uids(self) -> set:
        """Get set of all existing uids."""
        return {pm.uid for pm in self.pie_menus if pm.uid}

    def from_dict(self, value):
        pass

    def to_dict(self):
        d = {}
        return d

    def _draw_pm_item(self, context, layout):
        pr = get_prefs()
        tpr = temp_prefs()
        pm = pr.selected_pm

        lh.lt(layout)
        split = lh.split(None, 0.75, False)
        lh.row()

        data = pr.pmi_data
        icon = data.parse_icon('FILE_HIDDEN')

        if pm.ed.use_slot_icon:
            lh.operator(
                WM_OT_pmi_icon_select.bl_idname,
                "",
                icon,
                idx=pme.context.edit_item_idx,
                icon="",
            )

        lh.prop(data, "name", "")

        if data.name != data.sname and data.sname:
            lh.operator(
                PME_OT_pmi_name_apply.bl_idname,
                "",
                'BACK',
                idx=pme.context.edit_item_idx,
            )

            lh.prop(data, "sname", "", enabled=False)

        lh.lt(split)
        lh.operator(
            WM_OT_pmi_data_edit.bl_idname,
            "OK",
            idx=pme.context.edit_item_idx,
            ok=True,
            enabled=not data.has_errors(),
        )
        lh.operator(WM_OT_pmi_data_edit.bl_idname, "Cancel", idx=-1)

        lh.lt(layout)

        mode_col = lh.column(layout)
        lh.row(mode_col)
        pm.ed.draw_slot_modes(lh.layout, pm, data, pme.context.edit_item_idx)
        lh.operator(OPS.PME_OT_pmidata_specials_call.bl_idname, "", 'COLLAPSEMENU')

        lh.box(mode_col)
        subcol = lh.column()

        data_mode = data.mode
        if data_mode in CC.MODAL_CMD_MODES:
            data_mode = 'COMMAND'

        if data_mode == 'COMMAND':
            lh.row(subcol)
            if pm.mode == 'MODAL' and data.mode == 'COMMAND':
                lh.prop(tpr, "modal_item_show", "", ic_eye(tpr.modal_item_show))

            icon = 'ERROR' if data.has_errors(CC.W_PMI_SYNTAX) else 'NONE'
            lh.prop(data, "cmd", "", icon)

            if (
                pm.mode == 'STICKY'
                and PME_OT_sticky_key_edit.pmi_prop
                and pme.context.edit_item_idx == 0
                and not data.has_errors()
            ):
                lh.lt(subcol)
                lh.operator(PME_OT_sticky_key_edit.bl_idname)

        elif data_mode == 'PROP':
            lh.row(subcol)
            if pm.mode == 'MODAL':
                lh.prop(tpr, "modal_item_show", "", ic_eye(tpr.modal_item_show))

            icon = 'ERROR' if data.has_errors(CC.W_PMI_SYNTAX) else 'NONE'
            lh.prop(data, "prop", "", icon)

            lh.lt(subcol)
            lh.sep()
            lh.row(alignment='LEFT')
            # lh.prop(data, "use_cb", label)
            lh.operator(
                WM_OT_pmi_icon_tag_toggle.bl_idname,
                "Use Checkboxes instead of Toggle Buttons",
                ic_cb(CC.F_CB in data.icon),
                idx=-1,
                tag=CC.F_CB,
                emboss=False,
            )

        elif data_mode == 'MENU':
            icon = 'ERROR' if data.has_errors(CC.W_PMI_MENU) else 'NONE'
            if data.menu in pr.pie_menus:
                icon = pr.pie_menus[data.menu].ed.icon
            row = lh.row(subcol)
            row.prop_search(data, "menu", tpr, "pie_menus", text="", icon=ic(icon))

            sub_pm = data.menu and data.menu in pr.pie_menus and pr.pie_menus[data.menu]
            if sub_pm:
                label = None
                if sub_pm.mode == 'RMENU':
                    label = "Open on Mouse Over"
                elif sub_pm.mode == 'DIALOG' and pm.mode != 'RMENU':
                    label = "Expand Popup Dialog"
                if label:
                    lh.lt(subcol)
                    lh.sep()
                    lh.prop(data, "expand_menu", label)

                if sub_pm.mode == 'DIALOG' and pm.mode == 'PMENU' and data.expand_menu:
                    lh.prop(data, "use_frame")
                    lh.operator(
                        "pme.exec",
                        "Make Popup Wider",
                        cmd=(
                            "d =get_prefs().pmi_data; "
                            "d.mode = 'CUSTOM'; "
                            "d.custom = '"
                            "col = L.%s(); "
                            "col.scale_x = 1.01; "
                            "draw_menu(\"%s\", layout=col)'"
                        )
                        % ("box" if data.use_frame else "column", data.menu),
                    )

        elif data_mode == 'HOTKEY':
            row = lh.row(subcol)
            icon = 'ERROR' if data.has_errors(CC.W_PMI_HOTKEY) else 'NONE'
            row.alert = icon == 'ERROR'
            lh.prop(data, "key", "", icon, event=True)

            lh.row(subcol)
            lh.prop(data, "ctrl", "Ctrl", toggle=True)
            lh.prop(data, "shift", "Shift", toggle=True)
            lh.prop(data, "alt", "Alt", toggle=True)
            lh.prop(data, "oskey", "OSkey", toggle=True)
            lh.prop(data, "key_mod", "", event=True)

        elif data_mode == 'CUSTOM':
            lh.row(subcol)
            icon = 'ERROR' if data.has_errors(CC.W_PMI_SYNTAX) else 'NONE'
            lh.prop(data, "custom", "", icon)

        if (
            pr.use_cmd_editor
            and data_mode == 'COMMAND'
            and data.kmi.idname
            and not data.has_errors(CC.W_PMI_SYNTAX)
        ):
            lh.lt(mode_col.box().column(align=True))

            lh.save()
            lh.label(operator_utils.operator_label(data.kmi.idname) + " Operator:")
            lh.sep()
            lh.row(align=False)
            lh.prop(data, "cmd_ctx", "")
            lh.prop(data, "cmd_undo", toggle=True)
            lh.restore()

            lh.template_keymap_item_properties(data.kmi)

            lh.sep()

            lh.row(align=False)
            lh.operator(PME_OT_pmi_cmd_generate.bl_idname, "Clear", clear=True)
            lh.operator(PME_OT_pmi_cmd_generate.bl_idname, "Apply", 'FILE_TICK')

        if pm.mode == 'MODAL':
            if data.mode == 'COMMAND':
                lh.row(subcol)

                if tpr.modal_item_custom != 'HIDDEN':
                    if tpr.modal_item_custom:
                        lh.layout.alert = data.has_errors(CC.W_PMI_EXPR)
                        lh.prop(tpr, "modal_item_custom", "")
                        lh.operator(
                            OPS.PME_OT_exec.bl_idname,
                            "",
                            'X',
                            cmd="temp_prefs().modal_item_custom = ''",
                        )
                    else:
                        lh.operator(
                            OPS.PME_OT_exec.bl_idname,
                            "Display Custom Value",
                            cmd="temp_prefs().modal_item_custom = "
                            "'\"Path or string\"'",
                        )

                lh.lt(layout.column(align=True))
                lh.layout.prop_enum(tpr, "modal_item_prop_mode", 'KEY')

                lh.box()
                # lh.prop(tpr, "modal_item_hk", "", event=True)
                tpr.modal_item_hk.draw(lh.layout, key_mod=False, alert=True)

            elif data.mode == 'PROP':
                # lh.lt(mode_col.box().column(align=True))
                if tpr.prop_data.path:
                    lh.row(subcol)
                    pd = tpr.prop_data
                    min_active = not U.isclose(pd.min, tpr.modal_item_prop_min)
                    max_active = not U.isclose(pd.max, tpr.modal_item_prop_max)
                    step_active = tpr.modal_item_prop_step_is_set
                    lh.prop(tpr, "modal_item_prop_min", active=min_active)
                    lh.prop(tpr, "modal_item_prop_max", active=max_active)
                    lh.prop(tpr, "modal_item_prop_step", active=step_active)
                    if min_active or max_active or step_active:
                        lh.operator(PME_OT_prop_data_reset.bl_idname, "", 'X')

                    lh.row(subcol)
                    if tpr.modal_item_custom != 'HIDDEN':
                        if tpr.modal_item_custom:
                            lh.layout.alert = data.has_errors(CC.W_PMI_EXPR)
                            lh.prop(tpr, "modal_item_custom", "")
                            lh.operator(
                                OPS.PME_OT_exec.bl_idname,
                                "",
                                'X',
                                cmd="temp_prefs().modal_item_custom = ''",
                            )
                        else:
                            lh.operator(
                                OPS.PME_OT_exec.bl_idname,
                                "Display Custom Value",
                                cmd="temp_prefs().modal_item_custom = "
                                "'\"Path or string\"'",
                            )

                lh.lt(layout)
                lh.column()
                lh.save()
                lh.row()
                lh.prop(tpr, "modal_item_prop_mode", expand=True)
                lh.restore()

                if tpr.modal_item_prop_mode == 'KEY':
                    lh.box()
                    tpr.modal_item_hk.draw(lh.layout, key_mod=False, alert=True)
                elif tpr.modal_item_prop_mode == 'WHEEL':
                    lh.box()
                    tpr.modal_item_hk.draw(lh.layout, key=False, key_mod=False)

        if data.has_info():
            lh.box(layout)
            lh.column()
            for error in data.errors:
                lh.label(error, icon='INFO')
            for info in data.infos:
                lh.label(info, icon='QUESTION')

    def _draw_icons(self, context, layout):
        pr = get_prefs()
        tpr = temp_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[pme.context.edit_item_idx]

        lh.lt(layout)
        split = lh.split(None, 0.75, False)
        lh.row()

        data = pmi
        if pr.is_edit_mode():
            data = pr.pmi_data

        icon = data.parse_icon('FILE_HIDDEN')

        lh.prop(data, "name", "", icon)
        lh.sep()
        lh.prop(pr, "icon_filter", "", icon='VIEWZOOM')
        # if pr.icon_filter:
        #     lh.operator(WM_OT_icon_filter_clear.bl_idname, "", 'X')

        lh.lt(split)
        lh.operator(
            WM_OT_pmi_icon_select.bl_idname,
            "None",
            idx=pme.context.edit_item_idx,
            icon='NONE',
        )

        lh.operator(WM_OT_pmi_icon_select.bl_idname, "Cancel", idx=-1)

        icon_filter = pr.icon_filter.upper()

        layout = layout.column(align=True)
        row = layout.row(align=True)
        row.prop(tpr, "icons_tab", expand=True)

        if tpr.icons_tab == 'CUSTOM':
            # row.prop(
            #     pr, "show_custom_icons", text="Custom Icons", toggle=True)

            row.operator(
                PME_OT_icons_refresh.bl_idname, text="", icon=ic('FILE_REFRESH')
            )

            p = row.operator("wm.path_open", text="", icon=ic('FILE_FOLDER'))
            p.filepath = get_user_icons_dir(create=True)

        if tpr.icons_tab == 'BLENDER':
            box = layout.box()
            column = box.column(align=True)
            row = column.row(align=True)
            row.alignment = 'CENTER'
            idx = 0

            for k, i in (
                UILayout.bl_rna.functions["prop"]
                .parameters["icon"]
                .enum_items.items()
            ):
                icon = i.identifier
                if k == 'NONE':
                    continue
                if icon_filter != "" and icon_filter not in icon:
                    continue

                p = row.operator(
                    WM_OT_pmi_icon_select.bl_idname,
                    text="",
                    icon=ic(icon),
                    emboss=False,
                )
                p.idx = pme.context.edit_item_idx
                p.icon = icon
                idx += 1
                if idx > pr.num_icons_per_row - 1:
                    idx = 0
                    row = column.row(align=True)
                    row.alignment = 'CENTER'

            if idx != 0:
                while idx < pr.num_icons_per_row:
                    row.label(text="", icon=ic('BLANK1'))
                    idx += 1

        elif tpr.icons_tab == 'CUSTOM':
            icon_filter = pr.icon_filter

            box = layout.box()
            column = box.column(align=True)
            row = column.row(align=True)
            row.alignment = 'CENTER'
            idx = 0

            for icon in sorted(ph.get_names()):
                if icon_filter != "" and icon_filter not in icon:
                    continue

                p = row.operator(
                    WM_OT_pmi_icon_select.bl_idname,
                    text="",
                    icon_value=ph.get_icon(icon),
                    emboss=False,
                )
                p.idx = pme.context.edit_item_idx
                p.icon = CC.F_CUSTOM_ICON + icon
                idx += 1
                if idx > pr.num_icons_per_row - 1:
                    idx = 0
                    row = column.row(align=True)
                    row.alignment = 'CENTER'

            if idx != 0:
                while idx < pr.num_icons_per_row:
                    row.label(text="", icon=ic('BLANK1'))
                    idx += 1

        layout.prop(pr, "num_icons_per_row", slider=True)

    def _draw_tab_editor(self, context, layout):
        pr = get_prefs()
        tpr = temp_prefs()
        pm = None
        link = None
        if pr.tree_mode and tpr.links_idx >= 0:
            if len(tpr.links) > 0:
                link = tpr.links[tpr.links_idx]
                if link.pm_name:
                    pm = pr.pie_menus[link.pm_name]
        else:
            if len(pr.pie_menus):
                pm = pr.selected_pm

        if pr.show_list:
            spl = split(layout, pr.list_size / 100)
            row = spl.row()
            column1 = row.column(align=True)
            row = spl.row()
            column2 = row.column(align=True)
        else:
            row = layout

        column3 = row.column()

        if pr.show_list:
            subrow = column1

            if pr.use_filter:
                subrow = column1.row()
                subcol = subrow.column(align=True)

                subcol.prop(
                    pr, "show_only_new_pms", text="", icon=ic('FILE_NEW'), toggle=True
                )
                subcol.separator()

                subcol.prop(pr, "mode_filter", text="", expand=True, icon_only=True)

                subcol.separator()
                icon = 'SOLO_ON' if pr.tag_filter else 'SOLO_OFF'
                subcol.operator(PME_OT_tags_filter.bl_idname, text="", icon=ic(icon))

                column1 = subrow.column(align=True)

            if pr.tree_mode:
                column1.template_list(
                    "PME_UL_pm_tree",
                    "",
                    tpr,
                    "links",
                    tpr,
                    "links_idx",
                    rows=pr.num_list_rows,
                )
            else:
                column1.template_list(
                    "WM_UL_pm_list",
                    "",
                    self,
                    "pie_menus",
                    self,
                    "active_pie_menu_idx",
                    rows=pr.num_list_rows,
                )

            row = column1.row(align=True)
            p = row.operator(WM_OT_pm_import.bl_idname, text="Import")
            p.mode = ""

            if pm or link:
                p = row.operator(WM_OT_pm_export.bl_idname, text="Export")
                p.mode = ""

            lh.lt(column2)

            if len(pr.pie_menus):
                lh.operator(OPS.PME_OT_pm_search_and_select.bl_idname, "", 'VIEWZOOM')

                lh.sep()

            lh.operator(PME_OT_pm_add.bl_idname, "", 'ADD', mode="")

            if pm:
                lh.operator(WM_OT_pm_duplicate.bl_idname, "", 'DUPLICATE')
                lh.operator(PME_OT_pm_remove.bl_idname, "", 'REMOVE')

            lh.sep()

            if pm and not pr.tree_mode:
                if not link or not link.path:
                    lh.operator(WM_OT_pm_move.bl_idname, "", 'TRIA_UP', direction=-1)
                    lh.operator(WM_OT_pm_move.bl_idname, "", 'TRIA_DOWN', direction=1)
                lh.operator(WM_OT_pm_sort.bl_idname, "", 'SORTALPHA')

                lh.sep()

            lh.operator(PME_OT_pm_enable_all.bl_idname, "", CC.ICON_ON).enable = True
            lh.operator(PME_OT_pm_enable_all.bl_idname, "", CC.ICON_OFF).enable = False

            if pr.tree_mode and tree_state.has_folders:
                lh.sep(group='EXP_COL_ALL')
                icon = 'TRIA_RIGHT' if tree_state.expanded_folders else 'TRIA_DOWN'
                lh.operator(PME_OT_tree_folder_toggle_all.bl_idname, "", icon)

            if pr.use_groups and len(pr.pie_menus):
                lh.sep(group='EXP_COL_ALL')
                icon = (
                    'TRIA_LEFT_BAR'
                    if len(tree_state.collapsed_groups)
                    != len(tree_state.groups)
                    else 'TRIA_DOWN_BAR'
                )
                lh.operator(
                    PME_OT_tree_group_toggle.bl_idname,
                    "",
                    icon,
                    group="",
                    idx=-1,
                    all=True,
                )

            lh.sep(group='SPEC')
            lh.operator(PME_OT_list_specials.bl_idname, "", 'COLLAPSEMENU')

        if not pm:
            if link and link.label:
                subcol = column3.box().column(align=True)
                subrow = subcol.row()
                subrow.enabled = False
                subrow.scale_y = pr.num_list_rows + CC.LIST_PADDING
                subrow.alignment = 'CENTER'
                subrow.label(text=link.label)
                subcol.row(align=True)
            else:
                subcol = column3.box().column(align=True)
                subrow = subcol.row()
                subrow.enabled = False
                subrow.scale_y = pr.num_list_rows + CC.LIST_PADDING
                subrow.alignment = 'CENTER'
                subrow.label(text=" ")
                subcol.row(align=True)
            return

        pm.ed.draw_pm_name(column3, pm)

        column = column3.column(align=True)
        pm.ed.draw_keymap(column, pm)
        pm.ed.draw_hotkey(column, pm)
        pm.ed.draw_items(column3, pm)

    def _draw_hprop(self, layout, data, prop, url=None):
        row = layout.row(align=True)
        row.prop(data, prop)
        if url:
            operator(
                row, OPS.PME_OT_docs.bl_idname, "", 'QUESTION', emboss=False, url=url
            )

    def _draw_hlabel(self, layout, text, url=None):
        row = layout.row(align=True)
        row.label(text=text)
        if url:
            operator(
                row, OPS.PME_OT_docs.bl_idname, "", 'QUESTION', emboss=False, url=url
            )

    def _draw_tab_settings(self, context, layout):
        pr = get_prefs()
        tpr = temp_prefs()

        col = layout.column(align=True)

        col.row(align=True).prop(tpr, "settings_tab", expand=True)
        box = col.box()
        if tpr.settings_tab == 'GENERAL':
            # box = self._offset_column(box)
            row = box.row()
            row.scale_x = 1.2
            row.alignment = 'CENTER'

            col = row.column()
            subcol = col.column(align=True)
            self._draw_hprop(subcol, pr, "show_sidepanel_prefs")
            self._draw_hprop(subcol, pr, "show_experimental_open_modes")
            self._draw_hprop(
                subcol,
                pr,
                "expand_item_menu",
                # "https://en.blender.org/uploads/b/b7/"
                # "Pme1.14.0_expand_item_menu.gif"  # DOC_TODO: Create Content
            )
            self._draw_hprop(
                subcol,
                pr,
                "use_cmd_editor",
                # "https://en.blender.org/uploads/f/f4/Pme_item_edit.png"  # DOC_TODO: Create Content
            )
            self._draw_hprop(subcol, pr, "cache_scripts")
            self._draw_hprop(subcol, pr, "save_tree")
            self._draw_hprop(subcol, pr, "auto_tag_on_add")
            self._draw_hprop(subcol, pr, "auto_backup")
            self._draw_hprop(subcol, pr, "show_error_trace")
            subcol.separator()
            self._draw_hprop(subcol, pr, "list_size")
            self._draw_hprop(subcol, pr, "num_list_rows")

        elif tpr.settings_tab == 'HOTKEYS':
            # box = self._offset_column(col.box())

            row = box.row()
            row.scale_x = 0.3
            row.alignment = 'CENTER'
            col = row.column()

            self._draw_hlabel(col, "PME Hotkey:")
            subcol = col.column(align=True)
            pr.hotkey.draw(subcol)

            col.separator()

            self._draw_hlabel(col, "Hotkey Modes:")
            subcol = col.column(align=True)
            subcol.prop(
                get_uprefs().inputs,
                "drag_threshold",
                text="Tweak Mode Threshold",
            )
            subcol.prop(pr, "hold_time")
            subcol.prop(pr, "chord_time")

            subcol = col.column(align=True)
            subcol.prop(pr, "use_chord_hint")

        elif tpr.settings_tab == 'OVERLAY':
            row = box.row()
            row.scale_x = 0.6
            row.alignment = 'CENTER'

            col = row.column()

            pr.overlay.draw(col)

        elif tpr.settings_tab == 'PIE':
            row = box.row()
            row.scale_x = 1.5
            row.alignment = 'CENTER'

            col = row.column()

            subcol = col.column(align=True)
            subcol.prop(pr, "show_pm_title")
            subcol.prop(pr, "restore_mouse_pos")

            subcol = col.column(align=True)
            subcol.prop(pr, "pie_extra_slot_gap_size")

            view = get_uprefs().view
            subcol = col.column(align=True)
            subcol.prop(view, "pie_animation_timeout")
            subcol.prop(view, "pie_initial_timeout")
            subcol.prop(view, "pie_menu_radius")
            subcol.prop(view, "pie_menu_threshold")
            subcol.prop(view, "pie_menu_confirm")

        elif tpr.settings_tab == 'MENU':
            row = box.row()
            row.scale_x = 1.5
            row.alignment = 'CENTER'

            col = row.column()

            view = get_uprefs().view
            col.prop(view, "use_mouse_over_open")

            subcol = col.column(align=True)
            subcol.active = view.use_mouse_over_open
            subcol.prop(view, "open_toplevel_delay", text="Top Level")
            subcol.prop(view, "open_sublevel_delay", text="Sub Level")

        elif tpr.settings_tab == 'POPUP':
            row = box.row()
            row.scale_x = 0.5
            row.alignment = 'CENTER'

            col = row.column()

            sub = col.column(align=True)
            # self._draw_hprop(sub, pr, "use_square_buttons")
            self._draw_hprop(sub, pr, "use_spacer")

            col.separator()

            self._draw_hlabel(
                col,
                "Default Mode:",
                # "https://en.blender.org/index.php/User:Raa/Addons/"
                # "Pie_Menu_Editor/Editors/Popup_Dialog#Mode"  # DOC_TODO: Create Content
            )
            sub = col.row(align=True)
            sub.prop(pr, "default_popup_mode", expand=True)

            col.separator()

            self._draw_hlabel(col, "Toolbars:")
            sub = col.column(align=True)
            sub.prop(pr, "toolbar_width")
            sub.prop(pr, "toolbar_height")

        elif tpr.settings_tab == 'MODAL':
            row = box.row()
            row.scale_x = 1.5
            row.alignment = 'CENTER'

            col = row.column()

            col.label(text="Mouse Movement Direction and Threshold:")
            subcol = col.column(align=True)
            subcol.prop(self, "mouse_dir_mode", text="")
            subcol.prop(self, "mouse_threshold_int")
            subcol.prop(self, "mouse_threshold_float")
            subrow = subcol.row(align=True)
            subrow.prop(
                self,
                "use_mouse_threshold_bool",
                text="",
                toggle=True,
                icon=ic_cb(self.use_mouse_threshold_bool),
            )
            subrow.prop(self, "mouse_threshold_bool")
            subrow = subcol.row(align=True)
            subrow.prop(
                self,
                "use_mouse_threshold_enum",
                text="",
                toggle=True,
                icon=ic_cb(self.use_mouse_threshold_enum),
            )
            subrow.prop(self, "mouse_threshold_enum")

    def _draw_preferences(self, context, layout):
        pr = get_prefs()
        row = layout.row()

        sub = row.row(align=True)
        sub.prop(pr, "show_list", text="", icon=ic('COLLAPSEMENU'))

        if pr.show_list:
            sub.prop(pr, "use_filter", text="", icon=ic('FILTER'))
            sub.prop(pr, "tree_mode", text="", icon=ic('OUTLINER'))
            sub.separator()
            sub.prop(pr, "show_names", text="", icon=ic('SYNTAX_OFF'))
            sub.prop(pr, "show_hotkeys", text="", icon=ic('FILE_FONT'))
            sub.prop(pr, "show_keymap_names", text="", icon=ic('MOUSE_MMB'))
            sub.prop(pr, "show_tags", text="", icon=ic_fb(False))
            if pr.tree_mode:
                sub.prop(pr, "group_by", text="", icon_only=True)

        row.prop(pr, "tab", expand=True)

        sub = row.row(align=True)
        sub.prop(pr, "interactive_panels", text="", icon=ic('WINDOW'))
        # sub.prop(pr, "show_error_trace", text="", icon=ic('CONSOLE'))
        sub.prop(pr, "debug_mode", text="", icon=ic('SCRIPT'))

        # row.separator()

        row.prop(pr, "maximize_prefs", text="", icon=ic('FULLSCREEN_ENTER'))

        if pr.tab == 'EDITOR':
            self._draw_tab_editor(context, layout)

        elif pr.tab == 'SETTINGS':
            self._draw_tab_settings(context, layout)

    def draw_prefs(self, context, layout):
        if self.mode == 'ADDON':
            self._draw_preferences(context, layout)
        elif self.mode == 'ICONS':
            self._draw_icons(context, layout)
        elif self.mode == 'PMI':
            self._draw_pm_item(context, layout)

    def draw(self, context):
        self.draw_prefs(context, self.layout)

    def init_menus(self):
        pr = get_prefs()
        DBG and logh("Init Menus")

        if len(self.pie_menus) == 0:
            self.add_pm()
            return

        for pm in self.pie_menus:
            self.old_pms.add(pm.name)

            pm.ed.init_pm(pm)

            if 'MENU' in pm.ed.supported_slot_modes:
                for pmi in pm.pmis:
                    if pmi.mode == 'MENU':
                        menu_name, mouse_over, _ = U.extract_str_flags(
                            pmi.text, CC.F_EXPAND, CC.F_EXPAND
                        )
                        if (
                            mouse_over
                            and menu_name in pr.pie_menus
                            and pr.pie_menus[menu_name].mode == 'RMENU'
                        ):
                            get_pme_menu_class(menu_name)

            km_names = pm.parse_keymap(False)
            if km_names:
                for km_name in km_names:
                    if km_name not in self.missing_kms:
                        self.missing_kms[km_name] = []
                    self.missing_kms[km_name].append(pm.name)
            else:
                pm.register_hotkey()

    def backup_menus(self, operator=None):
        DBG_INIT and logh("Backup")

        # Use BackupManager from infra.io (uses Blender standard user config path)
        backup_mgr = BackupManager()

        # Get export data
        data = self.get_export_data()

        # Create backup
        backup_path, message = backup_mgr.create_backup(data, check_changes=True)

        if backup_path:
            DBG_INIT and logi("New backup", backup_path)
            if operator:
                bpy.ops.pme.message_box(
                    title="Backup Menus",
                    message="New backup: " + backup_path
                )
        else:
            # Determine reason for not creating backup
            if "No changes" in message:
                DBG_INIT and logi("No changes")
            elif "already exists" in message:
                DBG_INIT and logi("Backup exists")
            if operator:
                bpy.ops.pme.message_box(title="Backup Menus", message=message)

    def get_export_data(self, export_tags=True, mode='ALL', tag="", compat=False, mark_schema=True):
        pr = self
        tpr = temp_prefs()
        menus = []
        apm = pr.selected_pm
        apm_name = apm and apm.name

        pms_to_export = []
        parsed_pms = set()

        def parse_children(pmis):
            for pmi in pmis:
                if pmi.mode == 'MENU':
                    menu_name, _, _ = U.extract_str_flags(
                        pmi.text, CC.F_EXPAND, CC.F_EXPAND
                    )
                    if menu_name in pr.pie_menus:
                        if menu_name not in pms_to_export:
                            pms_to_export.append(menu_name)

                        if menu_name not in parsed_pms:
                            parsed_pms.add(menu_name)
                            parse_children(pr.pie_menus[menu_name].pmis)

        def gen_pms():
            if pr.tree_mode:
                pm_names = set()
                for link in tpr.links:
                    if link.pm_name and link.pm_name not in pm_names:
                        pm_names.add(link.pm_name)
                        yield pr.pie_menus[link.pm_name]
            else:
                for pm in pr.pie_menus:
                    yield pm

        for pm in gen_pms():
            if mode == 'ENABLED' and not pm.enabled:
                continue
            elif mode == 'ACTIVE' and pm.name != apm_name:
                continue
            elif mode == 'TAG' and not pm.has_tag(tag):
                continue

            pms_to_export.append(pm.name)
            parsed_pms.add(pm.name)

            if mode != 'ALL':
                parse_children(pm.pmis)

        for pm_name in pms_to_export:
            pm = pr.pie_menus[pm_name]
            items = []

            for pmi in pm.pmis:
                if pmi.mode == 'EMPTY':
                    if pmi.name:
                        item = (pmi.name, pmi.icon, pmi.text)
                    else:
                        item = (pmi.text,)
                else:
                    item = (pmi.name, pmi.mode, pmi.icon, pmi.text, pmi.flags())
                items.append(item)

            # Compatible JSON
            open_mode = pm.open_mode
            drag_dir = getattr(pm, 'drag_dir', 'ANY') if open_mode == 'CLICK_DRAG' else ""
            if compat:
                # Normalize experimental modes to vanilla equivalents
                if open_mode == 'CLICK':
                    open_mode = 'PRESS'
                elif open_mode == 'CLICK_DRAG':
                    open_mode = 'TWEAK'
                drag_dir = ""

            # For PME1 compatibility, PROPERTY mode exports prop_type to menu[7]
            # instead of poll_cmd. prop_type is stored in pm.data as pr_prop_type.
            if pm.mode == 'PROPERTY':
                poll_or_prop_type = pm.get_data("pr_prop_type")
            else:
                poll_or_prop_type = "" if pm.poll_cmd == CC.DEFAULT_POLL else pm.poll_cmd

            base = [
                pm.name,
                pm.km_name,
                pm.to_hotkey(),
                items,
                pm.mode,
                pm.data,
                open_mode,  # Compat
                poll_or_prop_type,
                pm.tag if export_tags else "",
            ]
            if not compat:
                base.append(pm.enabled)
                base.append(drag_dir)
            menus.append(tuple(base))

        data = dict(version=".".join(str(i) for i in addon.VERSION), menus=menus)
        # Mark Schema
        if not compat and mark_schema:
            data["schema"] = "PME-F"
        return data

    def ed(self, id):
        return self.editors[id]


# PME_PT_preferences moved to prefs/operators.py

# PME_MT_button_context, PME_OT_context_menu, button_context_menu, add_rmb_menu
# moved to prefs/context_menu.py


def register():
    if not hasattr(WindowManager, "pme"):
        WindowManager.pme = PointerProperty(type=PMEData)
        bpy.context.window_manager.pme.modal_item_hk.setvar(
            "update", PMEData.update_modal_item_hk
        )

    PMEPreferences.kh = KeymapHelper()

    add_rmb_menu()

    pr = get_prefs()
    pr.tree.lock()
    # NOTE: init_menus() and pr.ed() moved to deferred_init()
    # Called from __init__.py after all editors are registered

    tpr = temp_prefs()
    tpr.init_tags()

    # TODO: 'prefs' will be migrated to 'get_prefs' in the future.
    # Kept for now to support user setup and external scripts.
    pme.context.add_global("_prefs", prefs)
    pme.context.add_global("prefs", prefs)
    pme.context.add_global("get_prefs", get_prefs)
    pme.context.add_global("temp_prefs", temp_prefs)
    pme.context.add_global("pme", pme)
    pme.context.add_global("os", os)
    pme.context.add_global("PMEData", PMEData)

    pr.interactive_panels = False
    pr.icon_filter = ""
    pr.show_custom_icons = False
    pr.tab = 'EDITOR'
    pr.use_filter = False
    pr.show_only_new_pms = False
    pr.maximize_prefs = False
    pr.show_advanced_settings = False
    pr.mode_filter = CC.PM_ITEMS_M_DEFAULT
    if hasattr(pr,"tag_filter"):
        pr.tag_filter = ""
    Tag.filter()

    h = pr.hotkey
    if h.key == 'NONE':
        h.key = 'ACCENT_GRAVE'
        h.ctrl = True
        h.shift = True

    if pr.kh.available():
        pr.kh.keymap("Screen Editing")

        h.add_kmi(pr.kh.operator(PME_OT_pm_edit, h, auto=True))

        pr.kh.operator(WM_OT_pmi_icon_select, key='ESC', idx=-1).properties.hotkey = True
        pr.kh.operator(WM_OT_pmi_data_edit, key='RET', ok=True).properties.hotkey = True
        pr.kh.operator(WM_OT_pmi_data_edit, key='ESC', idx=-1).properties.hotkey = True

        pr.window_kmis.append(
            pr.kh.operator(EOPS.PME_OT_window_auto_close, 'Any+LEFTMOUSE')
        )
        pr.window_kmis.append(
            pr.kh.operator(EOPS.PME_OT_window_auto_close, 'Any+RIGHTMOUSE')
        )
        pr.window_kmis.append(
            pr.kh.operator(EOPS.PME_OT_window_auto_close, 'Any+MIDDLEMOUSE')
        )
        pr.enable_window_kmis(False)

    # NOTE: pr.selected_pm.ed.register_props() moved to deferred_init()

    pr.tree.unlock()
    pr.tree.update()
    PME_UL_pm_tree.load_state()

    # Run autorun scripts (system first, then user)
    for script_dir in iter_script_dirs(ADDON_PATH, "autorun"):
        for root, dirs, files in os.walk(script_dir, followlinks=True):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith('.py'):
                    execute_script(os.path.join(root, file))

    # Run register scripts (system first, then user)
    for script_dir in iter_script_dirs(ADDON_PATH, "register"):
        for root, dirs, files in os.walk(script_dir, followlinks=True):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith('.py'):
                    execute_script(os.path.join(root, file))


def unregister():
    pr = get_prefs()
    pr.kh.unregister()
    pr.window_kmis.clear()

    PMIData._kmi = None

    if hasattr(bpy_types, "WM_MT_button_context"):
        getattr(bpy_types, "WM_MT_button_context").remove(button_context_menu)

    # Run unregister scripts (system first, then user)
    for script_dir in iter_script_dirs(ADDON_PATH, "unregister"):
        for root, dirs, files in os.walk(script_dir, followlinks=True):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith('.py'):
                    execute_script(os.path.join(root, file))


def deferred_init():
    """Initialize editor-dependent functionality.

    Called from __init__.py after all modules (including editors) are registered.
    This ensures pr.editors dict is populated before init_menus() accesses it.
    """
    pr = get_prefs()
    pr.init_menus()
    if pr.auto_backup:
        pr.backup_menus()

    pr.ed('DIALOG').update_default_pmi_data()
    pr.selected_pm.ed.register_props(pr.selected_pm)
