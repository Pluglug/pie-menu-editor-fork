# editors/base.py - Base editor class and common editor functionality
# LAYER = "editors"
#
# Moved from: ed_base.py (PME2 layer separation)
# Phase 5-A: Operators moved to operators/ed/ (Issue #74)

LAYER = "editors"

import bpy
from bpy import types as bpy_types
from bpy.types import Header, Menu, Panel
from ..addon import get_prefs, temp_prefs, ic_cb, ic_eye, ic_fb, ic
from ..core.constants import (
    ED_DATA,
    EMODE_ITEMS,
    F_EXPAND,
    F_PRE,
    F_RIGHT,
    KEYMAP_SPLITTER,
    MODAL_CMD_MODES,
    W_PMI_HOTKEY,
    W_PMI_MENU,
    W_PMI_SYNTAX,
)
from ..infra.debug import *
from ..bl_utils import re_operator, re_prop, bp, uname
from ..ui import shorten_str, gen_prop_name, gen_op_name, utitle
from ..keymap_helper import MOUSE_BUTTONS, parse_hotkey, remove_mouse_button, to_ui_hotkey
from ..infra.utils import extract_str_flags, extract_str_flags_b
from ..ui import screen as SU
from ..ui.utils import get_pme_menu_class, pme_menu_classes
from ..ui.layout import lh, operator, split, draw_pme_layout, L_SEP, L_LABEL
from ..pme_types import Tag, PMItem, PMIItem
from ..operators import (
    PME_OT_docs,
    PME_OT_preview,
    PME_OT_pm_hotkey_remove,
    WM_OT_pm_select,
    WM_OT_pme_user_pie_menu_call,
)

# Re-export operators from operators/ed/ for backward compatibility
from ..operators.ed import (
    # Tags
    PME_OT_tags_filter,
    PME_OT_tags,
    # Icon
    WM_OT_pmi_icon_tag_toggle,
    WM_OT_pmi_icon_select,
    # PMI
    WM_OT_pmi_type_select,
    WM_OT_pmi_edit,
    WM_OT_pmi_edit_clipboard,
    WM_OT_pmi_edit_auto,
    PME_OT_pmi_menu,
    PME_OT_pmi_add,
    PME_OT_pmi_move,
    PME_OT_pmi_remove,
    PME_OT_pmi_clear,
    PME_OT_pmi_cmd_generate,
    WM_OT_pmi_data_edit,
    PME_OT_pmi_copy,
    PME_OT_pmi_paste,
    # PM
    PME_MT_select_menu,
    PME_MT_pm_new,
    PME_OT_pm_add,
    PME_OT_pm_edit,
    PME_OT_pm_toggle,
    PME_OT_pmi_toggle,
    # Poll
    PME_MT_poll_mesh,
    PME_MT_poll_object,
    PME_MT_poll_workspace,
    PME_OT_poll_specials_call,
    # Settings
    PME_MT_header_menu_set,
    PME_MT_screen_set,
    PME_MT_brush_set,
    # Keymap
    PME_OT_keymap_add,
    PME_OT_pm_open_mode_select,
    PME_OT_pm_hotkey_convert,
)

EXTENDED_PANELS = {}


def get_pm_by_uid(uid):
    """Get pm by uid. Returns None if not found."""
    if not uid:
        return None
    pr = get_prefs()
    for pm in pr.pie_menus:
        if pm.uid == uid:
            return pm
    return None


def _get_extend_key(pm):
    """Get the key for EXTENDED_PANELS. Uses uid if available, falls back to name."""
    return pm.uid if pm.uid else pm.name


def gen_header_draw(pm_uid_or_name, is_right_pm=False):
    """Generate header draw function.

    Args:
        pm_uid_or_name: pm.uid (preferred) or pm.name (fallback)
        is_right_pm: Whether this is for right region
    """
    def _draw(self, context):
        is_right_region = context.region.alignment == 'RIGHT'
        if is_right_region and is_right_pm or not is_right_region and not is_right_pm:
            # Try uid first, then fall back to name
            pm = get_pm_by_uid(pm_uid_or_name)
            if not pm:
                try:
                    pm = get_prefs().pie_menus[pm_uid_or_name]
                except Exception:
                    return

            draw_pme_layout(
                pm,
                self.layout.column(align=True),
                WM_OT_pme_user_pie_menu_call._draw_item,
                icon_btn_scale_x=1,
            )
    return _draw


def gen_menu_draw(pm_uid_or_name):
    """Generate menu draw function."""
    def _draw(self, context):
        pm = get_pm_by_uid(pm_uid_or_name)
        if not pm:
            try:
                pm = get_prefs().pie_menus[pm_uid_or_name]
            except Exception:
                return

        WM_OT_pme_user_pie_menu_call.draw_rm(pm, self.layout)
    return _draw


def gen_panel_draw(pm_uid_or_name):
    """Generate panel draw function."""
    def _draw(self, context):
        pm = get_pm_by_uid(pm_uid_or_name)
        if not pm:
            try:
                pm = get_prefs().pie_menus[pm_uid_or_name]
            except Exception:
                return

        draw_pme_layout(
            pm,
            self.layout.column(align=True),
            WM_OT_pme_user_pie_menu_call._draw_item,
        )
    return _draw


def extend_panel(pm):
    """Extend a Blender panel/menu/header with PME content.

    Phase 9-X: Uses pm.data for extend_target, with pm.name fallback for compatibility.

    Args:
        pm: PMItem to extend from
    """
    key = _get_extend_key(pm)
    if key in EXTENDED_PANELS:
        return

    # Get extend_target from pm.data (Phase 9-X)
    # Use appropriate prefix based on mode: pd for DIALOG, rm for RMENU
    if pm.mode == 'DIALOG':
        extend_target = pm.get_data("pd_extend_target")
    elif pm.mode == 'RMENU':
        extend_target = pm.get_data("rm_extend_target")
    else:
        extend_target = None

    # Fallback: parse from pm.name (backward compatibility)
    is_right = False
    is_prepend = False
    if not extend_target:
        extend_target, is_right, is_prepend = extract_str_flags_b(pm.name, F_RIGHT, F_PRE)
    else:
        # Get position from pm.data
        if pm.mode == 'DIALOG':
            extend_position = pm.get_data("pd_extend_position", 0)
        elif pm.mode == 'RMENU':
            extend_position = pm.get_data("rm_extend_position", 0)
        else:
            extend_position = 0
        is_prepend = extend_position < 0
        # Note: is_right is deprecated, always False for new menus

    if not extend_target:
        return

    # Skip PME's own panels
    if extend_target.startswith("PME_"):
        return

    tp = getattr(bpy_types, extend_target, None)
    if not tp:
        return

    if not issubclass(tp, (Panel, Menu, Header)):
        return

    # Generate draw function using uid (or name as fallback)
    if '_HT_' in extend_target:
        EXTENDED_PANELS[key] = gen_header_draw(key, is_right)
    elif '_MT_' in extend_target:
        EXTENDED_PANELS[key] = gen_menu_draw(key)
    else:
        EXTENDED_PANELS[key] = gen_panel_draw(key)

    f = tp.prepend if is_prepend else tp.append
    f(EXTENDED_PANELS[key])
    SU.redraw_screen()


def unextend_panel(pm):
    """Remove extension from a Blender panel/menu/header.

    Phase 9-X: Uses pm.uid as key, with pm.name fallback for compatibility.
    """
    key = _get_extend_key(pm)
    if key not in EXTENDED_PANELS:
        return

    # Get extend_target from pm.data or pm.name
    if pm.mode == 'DIALOG':
        extend_target = pm.get_data("pd_extend_target")
    elif pm.mode == 'RMENU':
        extend_target = pm.get_data("rm_extend_target")
    else:
        extend_target = None

    if not extend_target:
        extend_target, _, _ = extract_str_flags_b(pm.name, F_RIGHT, F_PRE)

    tp = getattr(bpy_types, extend_target, None)
    if tp:
        tp.remove(EXTENDED_PANELS[key])
        del EXTENDED_PANELS[key]
        SU.redraw_screen()



class EditorBase:
    def __init__(self):
        get_prefs().editors[self.id] = self

        for id, name, icon in ED_DATA:
            if id == self.id:
                self.default_name = name
                self.icon = icon
                break

        self.docs = None
        self.editable_slots = True
        self.use_slot_icon = True
        self.copy_paste_slot = True
        self.use_preview = True
        self.sub_item = True
        self.has_hotkey = True
        self.has_extra_settings = True
        self.default_pmi_data = ""
        self.fixed_num_items = False
        self.movable_items = True
        self.use_swap = False
        self.pmi_move_operator = PME_OT_pmi_move.bl_idname
        self.toggleable_slots = True

        self.supported_slot_modes = {
            'EMPTY',
            'COMMAND',
            'PROP',
            'MENU',
            'HOTKEY',
            'CUSTOM',
        }
        self.supported_open_modes = {'PRESS', 'HOLD', 'DOUBLE_CLICK', 'ONE_SHOT'}
        self.supported_sub_menus = {
            'PMENU',
            'RMENU',
            'DIALOG',
            'SCRIPT',
            'STICKY',
            'MACRO',
            'MODAL',
            'PROPERTY',
        }
        self.supported_paste_modes = {
            'PMENU',
            'RMENU',
            'DIALOG',
            'SCRIPT',
            'STICKY',
            'MACRO',
        }

    def register_temp_prop(self, id, prop):
        tpr = temp_prefs()
        try:
            del tpr.ed_props[id]
        except:
            pass

        setattr(tpr.ed_props.__class__, id, prop)

    def register_pm_prop(self, id, prop):
        setattr(PMItem, id, prop)

    def register_pmi_prop(self, id, prop):
        setattr(PMIItem, id, prop)

    def register_props(self, pm):
        pass

    def unregister_props(self):
        def del_ed_props(cls):
            for k in dir(cls):
                if k.startswith("ed_"):
                    delattr(cls, k)

        del_ed_props(temp_prefs().ed_props.__class__)
        del_ed_props(PMItem)
        del_ed_props(PMIItem)

    def init_pm(self, pm):
        if not pm.data:
            pm.data = self.default_pmi_data

    def on_pm_select(self, pm):
        self.register_props(pm)

    def on_pm_add(self, pm):
        pass

    def on_pm_remove(self, pm):
        pass

    def on_pm_duplicate(self, from_pm, pm):
        for from_pmi in from_pm.pmis:
            pmi = pm.pmis.add()
            pmi.name = from_pmi.name
            pmi.icon = from_pmi.icon
            pmi.mode = from_pmi.mode
            pmi.text = from_pmi.text

    def on_pm_enabled(self, pm, value):
        if self.has_hotkey:
            pm.update_keymap_item(bpy.context)

            if pm.key_mod in MOUSE_BUTTONS:
                kms = pm.parse_keymap()
                for km in kms:
                    if pm.enabled:
                        pass
                    else:
                        remove_mouse_button(pm.key_mod, get_prefs().kh, km)

    def on_pm_rename(self, pm, name):
        pr = get_prefs()
        tpr = temp_prefs()

        old_name = pm.name

        for link in tpr.links:
            if link.pm_name == old_name:
                link.pm_name = name

        if pm.mode == 'RMENU' and old_name in pme_menu_classes:
            del pme_menu_classes[old_name]
            get_pme_menu_class(name)

        for v in pr.pie_menus:
            if v == pm:
                continue

            for pmi in v.pmis:
                if pmi.mode == 'MENU':
                    menu_name, mouse_over, _ = extract_str_flags(
                        pmi.text, F_EXPAND, F_EXPAND
                    )
                    if menu_name == old_name:
                        pmi.text = F_EXPAND + name if mouse_over else name

        if old_name in pm.kmis_map:
            if pm.kmis_map[old_name]:
                pm.unregister_hotkey()
            else:
                pm.kmis_map[name] = pm.kmis_map[old_name]
                del pm.kmis_map[old_name]

        if old_name in pr.tree_ul.expanded_folders:
            pr.tree_ul.expanded_folders.remove(old_name)
            pr.tree_ul.expanded_folders.add(name)

        if old_name in pr.old_pms:
            pr.old_pms.remove(old_name)
            pr.old_pms.add(name)

        for link in tpr.links:
            if link.pm_name == old_name:
                link.pm_name = name
            for i in range(0, len(link.path)):
                if link.path[i] == old_name:
                    link.path[i] = name

        pm.name = name

        if pm.name not in pm.kmis_map:
            pm.register_hotkey()

        Tag.filter()
        pr.update_tree()

    def on_pmi_check(self, pm, pmi_data):
        pr = get_prefs()

        data = pmi_data
        data.info()
        pmi_mode = 'COMMAND' if data.mode in MODAL_CMD_MODES else data.mode

        if pmi_mode == 'COMMAND':
            if data.cmd:
                try:
                    compile(data.cmd, '<string>', 'exec')
                except:
                    data.info(W_PMI_SYNTAX)

            data.sname = ""
            if not data.has_errors():
                mo = re_operator.search(data.cmd)
                if mo:
                    data.sname = gen_op_name(mo, True)
                else:
                    mo = re_prop.search(data.cmd)
                    if mo:
                        data.sname, icon = gen_prop_name(mo, False, True)
                    else:
                        data.sname = shorten_str(data.cmd, 20)

        elif pmi_mode == 'PROP':
            if data.prop:
                try:
                    compile(data.prop, '<string>', 'eval')
                except:
                    data.info(W_PMI_SYNTAX)

            data.sname = ""
            if not data.has_errors():
                prop = bp.get(data.prop)
                if prop:
                    data.sname = prop.name or utitle(prop.identifier)
                else:
                    data.sname = utitle(data.prop.rpartition(".")[2])

        elif pmi_mode == 'MENU':
            data.sname = data.menu
            pr = get_prefs()
            if not data.menu or data.menu not in pr.pie_menus:
                data.info(W_PMI_MENU)

        elif pmi_mode == 'HOTKEY':
            data.sname = to_ui_hotkey(data)
            if data.key == 'NONE':
                data.info(W_PMI_HOTKEY)

        elif pmi_mode == 'CUSTOM':
            data.sname = ""

            if data.custom:
                try:
                    compile(data.custom, '<string>', 'exec')
                    data.sname = shorten_str(data.custom, 20)
                except:
                    data.info(W_PMI_SYNTAX)

    def on_pmi_add(self, pm, pmi):
        pmi.mode = 'COMMAND'
        pmi.name = uname(pm.pmis, "Command", " ", 1, False)

    def on_pmi_move(self, pm):
        pass

    def on_pmi_remove(self, pm):
        pass

    def on_pmi_paste(self, pm, pmi):
        pmi.icon, *_ = pmi.extract_flags()

    def on_pmi_pre_edit(self, pm, pmi, data):
        data.sname = ""
        data.kmi.idname = ""
        data.mode = pmi.mode if pmi.mode != 'EMPTY' else 'COMMAND'
        data.name = pmi.name
        data.icon = pmi.icon

        data_mode = 'COMMAND' if data.mode in MODAL_CMD_MODES else data.mode

        data.cmd = pmi.text if data_mode == 'COMMAND' else ""
        data.custom = pmi.text if data_mode == 'CUSTOM' else ""
        data.prop = pmi.text if data_mode == 'PROP' else ""
        data.menu = pmi.text if data_mode == 'MENU' else ""
        data.menu, data.expand_menu, data.use_frame = extract_str_flags(
            data.menu, F_EXPAND, F_EXPAND
        )

        data.key, data.ctrl, data.shift, data.alt, data.oskey, data.key_mod = (
            'NONE',
            False,
            False,
            False,
            False,
            'NONE',
        )

        if pmi.mode == 'HOTKEY':
            (
                data.key,
                data.ctrl,
                data.shift,
                data.alt,
                data.oskey,
                data.any,
                data.key_mod,
                _,
            ) = parse_hotkey(pmi.text)

    def on_pmi_rename(self, pm, pmi, old_name, name):
        pmi.name = name

    def on_pmi_toggle(self, pm, pmi):
        pass

    def on_pmi_edit(self, pm, pmi):
        pass

    def on_pmi_icon_edit(self, pm, pmi):
        pass

    def draw_extra_settings(self, layout, pm):
        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.alert = pm.name in pm.poll_methods and pm.poll_methods[pm.name] is None
        sub.prop(pm, "poll_cmd", text="", icon=ic('NODE_SEL'))
        row.operator(
            PME_OT_poll_specials_call.bl_idname, text="", icon=ic('COLLAPSEMENU')
        )

    def draw_pm_name(self, layout, pm):
        pr = get_prefs()
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'
        row.operator(
            PME_OT_pm_toggle.bl_idname, text="", icon=ic_cb(pm.enabled)
        ).name = pm.name

        if self.use_preview:
            p = row.operator(PME_OT_preview.bl_idname, text="", icon=ic('HIDE_OFF'))
            p.pie_menu_name = pm.name

        p = row.operator(WM_OT_pm_select.bl_idname, text="", icon=ic(self.icon))
        p.pm_name = ""
        p.use_mode_icons = True
        row.prop(pm, "label", text="")

        row.operator(PME_OT_tags.bl_idname, text="", icon=ic_fb(pm.tag))

        if self.docs:
            p = row.operator(PME_OT_docs.bl_idname, text="", icon=ic('HELP'))
            p.id = self.docs

        if self.has_extra_settings:
            row.prop(pr, "show_advanced_settings", text="", icon=ic('SETTINGS'))

            if pr.show_advanced_settings:
                self.draw_extra_settings(col.box().column(), pm)

    def draw_keymap(self, layout, data):
        row = layout.row(align=True)
        if KEYMAP_SPLITTER in data.km_name:
            row.prop(data, "km_name", text="", icon=ic('MOUSE_MMB'))
        else:
            row.prop_search(
                data,
                "km_name",
                bpy.context.window_manager.keyconfigs.user,
                "keymaps",
                text="",
                icon=ic('MOUSE_MMB'),
                results_are_suggestions=True,
            )
        row.operator(PME_OT_keymap_add.bl_idname, text="", icon=ic('ADD'))

    def draw_hotkey(self, layout, data):
        row = layout.row(align=True)
        row.operator_context = 'INVOKE_DEFAULT'
        item = None
        pd = data.__annotations__["open_mode"]
        pkeywords = pd.keywords if hasattr(pd, "keywords") else pd[1]
        for i in pkeywords['items']:
            if i[0] == data.open_mode:
                item = i
                break

        subcol = row.column(align=True)
        subcol.scale_y = 2
        subcol.operator(
            PME_OT_pm_open_mode_select.bl_idname, text="", icon_value=item[3]
        )

        subcol = row.column(align=True)
        if data.open_mode != 'CHORDS':
            subrow = subcol.row(align=True)
        else:
            subrow = split(subcol, 5 / 6, align=True)
        subrow.prop(data, "key", text="", event=True)
        if data.open_mode == 'CHORDS':
            subrow.prop(data, "chord", text="", event=True)

        if data.any:
            subrow = split(subcol, 5 / 6, align=True)
            subrow.prop(data, "any", text="Any", toggle=True)
        else:
            subrow = subcol.row(align=True)
            subrow.prop(data, "any", text="Any", toggle=True)
            subrow.prop(data, "ctrl", text="Ctrl", toggle=True)
            subrow.prop(data, "shift", text="Shift", toggle=True)
            subrow.prop(data, "alt", text="Alt", toggle=True)
            subrow.prop(data, "oskey", text="OSkey", toggle=True)
        subrow.prop(data, "key_mod", text="", event=True)

        if data.open_mode == 'CLICK_DRAG':
            subrow.prop(data, "drag_dir", text="")

        subcol = row.column(align=True)
        subcol.scale_y = 2
        subcol.operator(PME_OT_pm_hotkey_remove.bl_idname, icon=ic('X'))

    def draw_items(self, layout, pm):
        pr = get_prefs()
        column = layout.column(align=True)

        for idx, pmi in enumerate(pm.pmis):
            lh.row(column, active=pmi.enabled)

            self.draw_item(pm, pmi, idx)
            self.draw_pmi_menu_btn(pr, idx)

        if not self.fixed_num_items:
            lh.lt(column)
            lh.operator(PME_OT_pmi_add.bl_idname, "Add Item")

    def draw_item(self, pm, pmi, idx):
        if self.editable_slots:
            lh.operator(
                WM_OT_pmi_data_edit.bl_idname,
                "",
                self.get_pmi_icon(pm, pmi, idx),
                idx=idx,
                ok=False,
            )

        if self.get_use_slot_icon(pm, pmi, idx):
            icon = pmi.parse_icon('FILE_HIDDEN')

            lh.operator(WM_OT_pmi_icon_select.bl_idname, "", icon, idx=idx, icon="")

        lh.prop(pmi, "label", "")

    def draw_pmi_menu_btn(self, pr, idx):
        if pr.expand_item_menu:
            lh.icon_only = True
            lh.skip(L_SEP | L_LABEL)
            self.draw_pmi_menu(bpy.context, idx)
            lh.icon_only = False
            lh.skip()
        else:
            PME_OT_pmi_menu.draw_func = self.draw_pmi_menu
            lh.operator(PME_OT_pmi_menu.bl_idname, "", 'COLLAPSEMENU', idx=idx)

    def draw_pmi_menu(self, context, idx):
        pr = get_prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[idx]

        text, *_ = pmi.parse()
        icon = self.get_pmi_icon(pm, pmi, idx)
        lh.label(shorten_str(text) if text.strip() else "Slot", icon)

        lh.sep(check=True)

        if self.editable_slots:
            lh.operator(
                WM_OT_pmi_data_edit.bl_idname, "Edit Slot", 'TEXT', idx=idx, ok=False
            )

        if not self.fixed_num_items:
            lh.operator(PME_OT_pmi_add.bl_idname, "Add Slot", 'ADD', idx=idx)

        if self.copy_paste_slot:
            lh.sep(check=True)

            lh.operator(
                PME_OT_pmi_copy.bl_idname,
                None,
                'COPYDOWN',
                enabled=(pmi.mode != 'EMPTY'),
                idx=idx,
            )

            if pr.pmi_clipboard.has_data():
                lh.operator(PME_OT_pmi_paste.bl_idname, None, 'PASTEDOWN', idx=idx)

        if self.movable_items and len(pm.pmis) > 1:
            lh.sep(check=True)

            lh.operator(
                self.pmi_move_operator,
                "Move Slot",
                'ARROW_LEFTRIGHT' if self.use_swap else 'FORWARD',
                old_idx=idx,
                swap=self.use_swap,
            )

        if self.toggleable_slots:
            lh.sep(check=True)
            lh.operator(
                PME_OT_pmi_toggle.bl_idname,
                "Enabled" if pmi.enabled else "Disabled",
                ic_eye(pmi.enabled),
                pm=pm.name,
                pmi=idx,
            )

        if self.fixed_num_items:
            if 'EMPTY' in self.supported_slot_modes:
                lh.sep(check=True)

                lh.operator(PME_OT_pmi_clear.bl_idname, "Clear", 'X', idx=idx)
        elif len(pm.pmis) > 1:
            lh.sep(check=True)

            lh.operator(
                PME_OT_pmi_remove.bl_idname,
                "Remove",
                'X',
                idx=idx,
                confirm=lh.icon_only,
            )

    def get_supported_slot_modes(self, pm, slot, idx):
        return self.supported_slot_modes

    def get_use_slot_icon(self, pm, slot, idx):
        return self.use_slot_icon

    def draw_slot_modes(self, layout, pm, slot, idx):
        for mode, _, _ in EMODE_ITEMS:
            if mode in self.get_supported_slot_modes(pm, slot, idx):
                layout.prop_enum(slot, "mode", mode)

    def get_pmi_icon(self, pm, pmi, idx):
        return 'MOD_SKIN'

    def draw_edit_menu(self, menu, context):
        pm = get_prefs().selected_pm

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        for idx, pmi in enumerate(pm.pmis):
            text, *_ = pmi.parse()
            lh.operator(
                self.op.op_bl_idname,
                text,
                self.get_pmi_icon(pm, pmi, idx),
                pm_item=idx,
                mode=self.op.mode,
                text=self.op.text,
                name=self.op.name,
                add=False,
                new_script=False,
            )

        lh.sep()

        lh.operator(
            self.op.op_bl_idname,
            "New Command",
            'ADD',
            mode=self.op.mode,
            text=self.op.text,
            name=self.op.name,
            pm_item=-1,
            add=True,
            new_script=False,
        )

        lh.operator(
            WM_OT_pm_select.bl_idname,
            None,
            'COLLAPSEMENU',
            pm_name="",
            use_mode_icons=False,
        )

    def popup_edit_menu(self, pm, operator):
        self.op = operator
        bpy.context.window_manager.popup_menu(self.draw_edit_menu, title=pm.name)

    def use_scroll(self, pm):
        return False
