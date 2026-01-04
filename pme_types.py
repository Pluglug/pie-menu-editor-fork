# pyright: reportInvalidTypeForm=false
# pme_types.py - Core data models (Tag, PMItem, PMIItem, PMLink, etc.)
# LAYER = "infra"
#
# Contains the primary PropertyGroup definitions for PME's data structures.
#
# Note: This module was originally labeled as "core", but PropertyGroup
# definitions inherently depend on bpy and cannot be pure Python.
# The actual dependencies (ui, operators, panels) place this in the infra layer.
# See: _docs/guides/rc_roadmap.md (Phase 5-B)

LAYER = "infra"

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup
from . import bl_utils as BU
from .core import constants as CC
from .ui import utils as UU
from .ui import panels as PAU
from .infra import macro as MAU
from .infra import utils as U
from .addon import get_prefs, temp_prefs, ic_fb
from . import keymap_helper as KH
from . import pme
from .core.schema import schema
from .ui import tag_redraw
# NOTE: schema is now in core/schema.py (Phase 8-C rename from core/schema.py)
# Import directly from core.schema for early loading and proper initialization
from .operators import WM_OT_pme_user_pie_menu_call


class UserProperties(PropertyGroup):
    pass


class EdProperties(PropertyGroup):
    pass


class Tag(PropertyGroup):
    filtered_pms = None

    @staticmethod
    def popup_menu(
        idname, title="", icon='NONE', untagged=True, invoke=False, **kwargs
    ):
        def draw_menu(menu, context):
            tpr = temp_prefs()
            layout = menu.layout
            if invoke:
                layout.operator_context = 'INVOKE_DEFAULT'
            for t in tpr.tags:
                p = layout.operator(idname, text=t.name, icon=ic_fb(True))
                p.tag = t.name
                for k, v in kwargs.items():
                    setattr(p, k, v)

            if untagged:
                if tpr.tags:
                    layout.separator()
                p = layout.operator(idname, text=CC.UNTAGGED, icon=ic_fb(False))
                p.tag = CC.UNTAGGED
                for k, v in kwargs.items():
                    setattr(p, k, v)

        bpy.context.window_manager.popup_menu(draw_menu, title=title, icon=icon)

    @staticmethod
    def filter():
        pr = get_prefs()
        tpr = temp_prefs()
        if not tpr.tags or not pr.tag_filter:
            Tag.filtered_pms = None
            return
        elif Tag.filtered_pms is None:
            Tag.filtered_pms = set()
        else:
            Tag.filtered_pms.clear()

        for pm in pr.pie_menus:
            if pm.has_tag(pr.tag_filter):
                Tag.filtered_pms.add(pm.name)

    @staticmethod
    def check_pm(pm):
        return Tag.filtered_pms is None or pm.name in Tag.filtered_pms


class PMLink(PropertyGroup):
    pm_name: StringProperty()
    is_folder: BoolProperty()
    label: StringProperty()
    folder: StringProperty()
    group: StringProperty()

    idx = 0
    paths = {}

    @staticmethod
    def add():
        link = temp_prefs().links.add()
        link.name = str(PMLink.idx)
        PMLink.idx += 1
        return link

    @staticmethod
    def clear():
        PMLink.idx = 0
        PMLink.paths.clear()

    def __getattr__(self, attr):
        if attr == "path":
            if self.name not in PMLink.paths:
                PMLink.paths[self.name] = []
            return PMLink.paths[self.name]

    def __str__(self):
        return "%s [%s] (%r) (%s)" % (
            self.pm_name,
            "/".join(self.path),
            self.is_folder,
            self.label,
        )

    def curpath(self):
        ret = self.group + CC.TREE_SPLITTER
        ret += CC.TREE_SPLITTER.join(self.path)
        return ret

    def fullpath(self):
        ret = self.group + CC.TREE_SPLITTER
        ret += CC.TREE_SPLITTER.join(self.path)
        if self.is_folder:
            if self.path:
                ret += CC.TREE_SPLITTER
            ret += self.pm_name
        return ret


class PMIItem(PropertyGroup):
    expandable_props = {}

    mode: EnumProperty(items=CC.MODE_ITEMS, description="Type of the item")
    text: StringProperty(maxlen=CC.MAX_STR_LEN)
    icon: StringProperty(description="Icon")
    enabled: BoolProperty(
        name="Enable/Disable", description="Enable/Disable", default=True
    )

    def get_pmi_label(self):
        return self.name

    def set_pmi_label(self, value):
        if self.name == value:
            return

        pm = get_prefs().selected_pm
        pm.ed.on_pmi_rename(pm, self, self.name, value)

    label: StringProperty(
        description="Label", get=get_pmi_label, set=set_pmi_label
    )

    @property
    def rm_class(self):
        value = self.text.replace(CC.F_EXPAND, "")
        return UU.get_pme_menu_class(value)

    def from_dict(self, value):
        pass

    def to_dict(self):
        return {k: self[k] for k in self.keys()}

    def flags(self, data=None):
        if data is None:
            return int(not self.enabled and CC.PMIF_DISABLED)

        self.enabled = not bool(data & CC.PMIF_DISABLED)

    def parse(self, default_icon='NONE'):
        icon, icon_only, hidden, use_cb = self.extract_flags()
        oicon = icon
        text = self.name

        if icon_only:
            text = ""
        if hidden:
            icon = 'NONE' if not icon or not icon_only else 'BLANK1'
            if text:
                text = " " * len(text)
        elif not icon:
            icon = default_icon

        if not hidden:
            if self.mode == 'PROP':
                bl_prop = BU.bp.get(self.prop if hasattr(self, "prop") else self.text)
                if bl_prop:
                    if bl_prop.type in {'STRING', 'ENUM', 'POINTER'}:
                        text = ""
                    if (
                        bl_prop.type in {'FLOAT', 'INT', 'BOOLEAN'}
                        and len(bl_prop.default_array) > 1
                    ):
                        text = ""

            if (
                icon[0] != CC.F_EXPAND
                and not icon.startswith(CC.F_CUSTOM_ICON)
                and icon not in CC.BL_ICONS
            ):
                icon = 'CANCEL'

        return text, icon, oicon, icon_only, hidden, use_cb

    def parse_edit(self):
        text, icon, oicon, icon_only, hidden, use_cb = self.parse()

        if not text and not hidden:
            if self.mode == 'PROP' and (self.is_expandable_prop() or icon == 'NONE'):
                if icon_only:
                    text = "[%s]" % self.name if self.name else " "
                else:
                    text = self.name if self.name else " "

        return text, icon, oicon, icon_only, hidden, use_cb

    def extract_flags(self):
        icon, icon_only, hidden, use_cb = U.extract_str_flags(
            self.icon, CC.F_ICON_ONLY, CC.F_HIDDEN, CC.F_CB
        )
        return icon, icon_only, hidden, use_cb

    def parse_icon(self, default_icon='NONE'):
        icon = self.extract_flags()[0]
        if not icon:
            return default_icon

        if (
            icon[0] != CC.F_EXPAND
            and not icon.startswith(CC.F_CUSTOM_ICON)
            and icon not in CC.BL_ICONS
        ):
            return 'CANCEL'

        if icon == 'NONE':
            icon = default_icon

        return icon

    def is_expandable_prop(self):
        if self.mode != 'PROP':
            return False

        prop = self.text
        if prop in self.expandable_props:
            return self.expandable_props[prop]

        value = None
        try:
            value = eval(prop, pme.context.globals)
        except:
            return False

        self.expandable_props[prop] = not isinstance(value, bool)

        return self.expandable_props[prop]


class PMItem(PropertyGroup):
    poll_methods = {}
    kmis_map = {}
    _km_name_update_lock = False
    _prev_key_mod_map = {}


    @property
    def selected_pmi(self):
        return self.pmis[pme.context.edit_item_idx]

    @staticmethod
    def _parse_keymap(km_name, exists=True, splitter=None):
        names = []
        keymaps = bpy.context.window_manager.keyconfigs.user.keymaps
        if splitter is None:
            splitter = CC.KEYMAP_SPLITTER

        for name in km_name.split(splitter):
            name = name.strip()
            if not name:
                continue

            name_in_keymaps = name in keymaps
            if exists and not name_in_keymaps or not exists and name_in_keymaps:
                continue

            names.append(name)

        if exists and not names:
            names.append("Window")

        return names

    def parse_keymap(self, exists=True, splitter=None):
        return PMItem._parse_keymap(self.km_name, exists, splitter)

    def update_pm_km_name(self, context):
        if PMItem._km_name_update_lock:
            return
        value = self.km_name or "Window"
        value = (CC.KEYMAP_SPLITTER + " ").join(PMItem._parse_keymap(value))
        PMItem._km_name_update_lock = True
        try:
            if self.km_name != value:
                self.km_name = value
            if not self.ed.has_hotkey:
                return
            self.unregister_hotkey()
            self.register_hotkey()
            get_prefs().update_tree()
        finally:
            PMItem._km_name_update_lock = False

    km_name: StringProperty(
        default="Window",
        description="Keymap names",
        update=update_pm_km_name,
    )

    def get_pm_name(self):
        return self.name

    def set_pm_name(self, value):
        pr = get_prefs()

        value = value.replace(CC.F_EXPAND, "")

        if value == self.name or not value:
            return

        if value in pr.pie_menus:
            value = pr.unique_pm_name(value)

        self.ed.on_pm_rename(self, value)

    label: StringProperty(
        get=get_pm_name, set=set_pm_name, description="Menu name"
    )

    pmis: CollectionProperty(type=PMIItem)
    mode: EnumProperty(items=CC.PM_ITEMS)
    tag: StringProperty()

    def update_keymap_item(self, context):
        if not self.ed.has_hotkey:
            return

        pr = get_prefs()
        kmis = self.kmis_map[self.name]

        if kmis:
            for k, kmi in kmis.items():
                KH.set_kmi_type(kmi, self.key)

                if self.any:
                    kmi.any = self.any
                else:
                    kmi.ctrl = self.ctrl
                    kmi.shift = self.shift
                    kmi.alt = self.alt
                    kmi.oskey = self.oskey

                kmi.key_modifier = self.key_mod
                if hasattr(kmi, "direction"):
                    kmi.direction = self.drag_dir if self.open_mode == 'CLICK_DRAG' else 'ANY'
                kmi.value = {
                    'DOUBLE_CLICK': 'DOUBLE_CLICK',
                    'CLICK': 'CLICK',
                    'CLICK_DRAG': 'CLICK_DRAG',
                }.get(self.open_mode, 'PRESS')

                if self.key == 'NONE' or not self.enabled:
                    if pr.kh.available():
                        pr.kh.keymap(k)
                        pr.kh.remove(kmi)

            if self.key == 'NONE' or not self.enabled:
                self.kmis_map[self.name] = None
        else:
            self.register_hotkey()

    def update_open_mode(self, context):
        if self.open_mode == 'CHORDS' and self.chord == 'NONE':
            self.chord = 'A'
        if self.open_mode != 'CHORDS' and self.chord != 'NONE':
            self.chord = 'NONE'

        self.update_keymap_item(context)

    open_mode: EnumProperty(
        name="Hotkey Mode", items=CC.OPEN_MODE_ITEMS, update=update_open_mode
    )

    def update_pm_key(self, context):
        self.update_keymap_item(context)
        pr = get_prefs()
        if pr.group_by == 'KEY':
            pr.tree.update()

    key: EnumProperty(
        items=KH.key_items,
        description="Key pressed",
        update=update_pm_key,
        default='NONE',
    )

    chord: EnumProperty(items=KH.key_items, description="Chord pressed")
    any: BoolProperty(
        description="Any key pressed", update=update_keymap_item
    )
    ctrl: BoolProperty(
        description="Ctrl key pressed", update=update_keymap_item
    )
    shift: BoolProperty(
        description="Shift key pressed", update=update_keymap_item
    )
    alt: BoolProperty(
        description="Alt key pressed", update=update_keymap_item
    )
    oskey: BoolProperty(
        description="Operating system key pressed", update=update_keymap_item
    )

    drag_dir: EnumProperty(
        items=CC.DRAG_DIR_ITEMS,
        name="Direction",
        description="Direction filter for Click Drag",
        default='ANY',
        update=update_keymap_item,
    )

    def update_pm_key_mod(self, context):
        pr = get_prefs()
        prev = PMItem._prev_key_mod_map.get(self.name, 'NONE')
        curr = self.key_mod
        if prev == curr or not self.enabled:
            PMItem._prev_key_mod_map[self.name] = curr
            return

        kms = self.parse_keymap()
        if prev != 'NONE' and prev in KH.MOUSE_BUTTONS:
            for km in kms:
                KH.remove_mouse_button(prev, pr.kh, km)

        if curr != 'NONE' and curr in KH.MOUSE_BUTTONS:
            for km in kms:
                KH.add_mouse_button(curr, pr.kh, km)

        PMItem._prev_key_mod_map[self.name] = curr

    key_mod: EnumProperty(
        items=KH.key_items,
        description="Regular key pressed as a modifier",
        update=update_pm_key_mod,
        default='NONE',
    )

    def update_pm_enabled(self, context):
        self.ed.on_pm_enabled(self, self.enabled)
        self.update_keymap_item(context)

    enabled: BoolProperty(
        description="Enable or disable the menu",
        default=True,
        update=update_pm_enabled,
    )

    def update_poll_cmd(self, context):
        if self.poll_cmd == CC.DEFAULT_POLL:
            self.poll_methods.pop(self.name, None)
        else:
            try:
                co = compile(
                    "def poll(cls, context):" + self.poll_cmd, "<string>", "exec"
                )
                self.poll_methods[self.name] = co
            except:
                self.poll_methods[self.name] = None

    poll_cmd: StringProperty(
        description=("Poll method\nTest if the item can be called/displayed or not"),
        default=CC.DEFAULT_POLL,
        maxlen=CC.MAX_STR_LEN,
        update=update_poll_cmd,
    )
    data: StringProperty(maxlen=CC.MAX_STR_LEN)

    def update_panel_group(self):
        self.ed.update_panel_group(self)

    def get_panel_context(self):
        prop = schema.parse(self.data)
        for item in PAU.panel_context_items(self, bpy.context):
            if item[0] == prop.pg_context:
                return item[4]
        return 0

    def set_panel_context(self, value):
        value = PAU.panel_context_items(self, bpy.context)[value][0]
        prop = schema.parse(self.data)
        if prop.pg_context == value:
            return
        self.data = schema.encode(self.data, "pg_context", value)
        self.update_panel_group()

    panel_context: EnumProperty(
        items=PAU.panel_context_items,
        name="Context",
        description="Panel context",
        get=get_panel_context,
        set=set_panel_context,
    )

    def get_panel_category(self):
        prop = schema.parse(self.data)
        return prop.pg_category

    def set_panel_category(self, value):
        prop = schema.parse(self.data)
        if prop.pg_category == value:
            return
        self.data = schema.encode(self.data, "pg_category", value)
        self.update_panel_group()

    panel_category: StringProperty(
        default="",
        description="Panel category (tab)",
        get=get_panel_category,
        set=set_panel_category,
    )

    def get_panel_region(self):
        prop = schema.parse(self.data)
        for item in CC.REGION_ITEMS:
            if item[0] == prop.pg_region:
                return item[4]
        return 0

    def set_panel_region(self, value):
        value = CC.REGION_ITEMS[value][0]
        prop = schema.parse(self.data)
        if prop.pg_region == value:
            return
        self.data = schema.encode(self.data, "pg_region", value)
        self.update_panel_group()

    panel_region: EnumProperty(
        items=CC.REGION_ITEMS,
        name="Region",
        description="Panel region",
        get=get_panel_region,
        set=set_panel_region,
    )

    def get_panel_space(self):
        prop = schema.parse(self.data)
        for item in CC.SPACE_ITEMS:
            if item[0] == prop.pg_space:
                return item[4]
        return 0

    def set_panel_space(self, value):
        value = CC.SPACE_ITEMS[value][0]
        prop = schema.parse(self.data)
        if prop.pg_space == value:
            return
        self.data = schema.encode(self.data, "pg_space", value)
        self.update_panel_group()

    panel_space: EnumProperty(
        items=CC.SPACE_ITEMS,
        name="Space",
        description="Panel space",
        get=get_panel_space,
        set=set_panel_space,
    )

    panel_wicons: BoolProperty(
        name="Use Wide Icon Buttons",
        description="Use wide icon buttons",
        get=lambda s: s.get_data("pg_wicons"),
        set=lambda s, v: s.set_data("pg_wicons", v),
    )

    pm_radius: IntProperty(
        subtype='PIXEL',
        description="Radius of the pie menu (-1 - use default value)",
        get=lambda s: s.get_data("pm_radius"),
        set=lambda s, v: s.set_data("pm_radius", v),
        default=-1,
        step=10,
        min=-1,
        max=1000,
    )
    pm_threshold: IntProperty(
        subtype='PIXEL',
        description=(
            "Distance from center needed "
            "before a selection can be made(-1 - use default value)"
        ),
        get=lambda s: s.get_data("pm_threshold"),
        set=lambda s, v: s.set_data("pm_threshold", v),
        default=-1,
        step=10,
        min=-1,
        max=1000,
    )
    pm_confirm: IntProperty(
        subtype='PIXEL',
        description=(
            "Distance threshold after which selection is made "
            "(-1 - use default value)"
        ),
        get=lambda s: s.get_data("pm_confirm"),
        set=lambda s, v: s.set_data("pm_confirm", v),
        default=-1,
        step=10,
        min=-1,
        max=1000,
    )
    pm_flick: BoolProperty(
        name="Confirm on Release",
        description="Confirm selection when releasing the hotkey",
        get=lambda s: s.get_data("pm_flick"),
        set=lambda s, v: s.set_data("pm_flick", v),
    )
    pd_title: BoolProperty(
        name="Show Title",
        description="Show title",
        get=lambda s: s.get_data("pd_title"),
        set=lambda s, v: s.set_data("pd_title", v),
    )
    pd_box: BoolProperty(
        name="Use Frame",
        description="Use a frame",
        get=lambda s: s.get_data("pd_box"),
        set=lambda s, v: s.set_data("pd_box", v),
    )
    pd_auto_close: BoolProperty(
        name="Auto Close on Mouse Out",
        description="Auto close on mouse out",
        get=lambda s: s.get_data("pd_auto_close"),
        set=lambda s, v: s.set_data("pd_auto_close", v),
    )
    pd_expand: BoolProperty(
        name="Expand Sub Popup Dialogs",
        description=(
            "Expand all sub popup dialogs instead of using them as a button"
        ),
        get=lambda s: s.get_data("pd_expand"),
        set=lambda s, v: s.set_data("pd_expand", v),
    )
    pd_panel: EnumProperty(
        name="Mode",
        description="Popup dialog mode",
        items=CC.PD_MODE_ITEMS,
        get=lambda s: s.get_data("pd_panel"),
        set=lambda s, v: s.set_data("pd_panel", v),
    )
    pd_width: IntProperty(
        name="Width",
        description="Width of the popup",
        subtype='PIXEL',
        get=lambda s: s.get_data("pd_width"),
        set=lambda s, v: s.set_data("pd_width", v),
        min=100,
        max=2000,
    )
    rm_title: BoolProperty(
        name="Show Title",
        description="Show title",
        get=lambda s: s.get_data("rm_title"),
        set=lambda s, v: s.set_data("rm_title", v),
    )
    # s_scroll: BoolProperty(
    #     description="Use both WheelUp and WheelDown hotkeys",
    #     get=lambda s: s.get_data("s_scroll"),
    #     set=lambda s, v: s.set_data("s_scroll", v),
    #     update=update_keymap_item)
    sk_block_ui: BoolProperty(
        name="Block UI",
        description=(
            "Block other tools, while the Sticky Key is active.\n"
            "Useful when the Sticky Key is a part of Macro Operator."
        ),
        get=lambda s: s.get_data("sk_block_ui"),
        set=lambda s, v: s.set_data("sk_block_ui", v),
    )
    mo_confirm_on_release: BoolProperty(
        name="Confirm On Release",
        description="Confirm on release",
        get=lambda s: s.get_data("confirm"),
        set=lambda s, v: s.set_data("confirm", v),
    )
    mo_block_ui: BoolProperty(
        name="Block UI",
        description="Block other hotkeys",
        get=lambda s: s.get_data("block_ui"),
        set=lambda s, v: s.set_data("block_ui", v),
    )

    def mo_lock_update(self, context):
        for pm in get_prefs().pie_menus:
            if pm.mode == 'MACRO':
                for pmi in pm.pmis:
                    menu_name, *_ = U.extract_str_flags(
                        pmi.text, CC.F_EXPAND, CC.F_EXPAND
                    )
                    if menu_name == self.name:
                        MAU.update_macro(pm)

    mo_lock: BoolProperty(
        name="Lock Mouse",
        description="Lock the mouse in the current area",
        get=lambda s: s.get_data("lock"),
        set=lambda s, v: s.set_data("lock", v),
        update=mo_lock_update,
    )

    def poll(self, cls=None, context=None):
        if self.poll_cmd == CC.DEFAULT_POLL:
            return True

        if self.name not in self.poll_methods:
            self.update_poll_cmd(bpy.context)

        poll_method_co = self.poll_methods[self.name]
        if poll_method_co is None:
            return True

        exec_globals = pme.context.gen_globals()
        exec_globals.update(menu=self.name)
        if not pme.context.exe(poll_method_co, exec_globals):
            return True

        BU.bl_context.reset(bpy.context)
        return exec_globals["poll"](cls, BU.bl_context)

    @property
    def is_new(self):
        return self.name not in get_prefs().old_pms

    def register_hotkey(self, km_names=None):
        pr = get_prefs()
        if self.name not in self.kmis_map:
            self.kmis_map[self.name] = None

        if self.key == 'NONE' or not self.enabled:
            return

        if pr.kh.available():
            if km_names is None:
                km_names = self.parse_keymap()

            if self.ed.use_scroll(self):
                keys = ('WHEELUPMOUSE', 'WHEELDOWNMOUSE')
            else:
                keys = (self.key,)

            for key in keys:
                for km_name in km_names:
                    pr.kh.keymap(km_name)
                    kmi = pr.kh.operator(
                        WM_OT_pme_user_pie_menu_call,
                        None,  # hotkey
                        key,
                        self.ctrl,
                        self.shift,
                        self.alt,
                        self.oskey,
                        'NONE' if self.key_mod in KH.MOUSE_BUTTONS else self.key_mod,
                        self.any,
                    )

                    kmi.properties.pie_menu_name = self.name
                    kmi.properties.invoke_mode = 'HOTKEY'
                    kmi.properties.keymap = km_name

                    if hasattr(kmi, "direction"):
                        kmi.direction = self.drag_dir if self.open_mode == 'CLICK_DRAG' else 'ANY'
                    kmi.value = {
                        'DOUBLE_CLICK': 'DOUBLE_CLICK',
                        'CLICK': 'CLICK',
                        'CLICK_DRAG': 'CLICK_DRAG',
                    }.get(self.open_mode, 'PRESS')

                    if self.kmis_map[self.name]:
                        self.kmis_map[self.name][km_name] = kmi
                    else:
                        self.kmis_map[self.name] = {km_name: kmi}

                    if self.key_mod in KH.MOUSE_BUTTONS:
                        KH.add_mouse_button(self.key_mod, pr.kh, km_name)

    def unregister_hotkey(self):
        pr = get_prefs()
        if (
            pr.kh.available()
            and self.name in self.kmis_map
            and self.kmis_map[self.name]
        ):
            for k, v in self.kmis_map[self.name].items():
                pr.kh.keymap(k)
                if isinstance(v, list):
                    for kmi in v:
                        pr.kh.remove(kmi)
                else:
                    pr.kh.remove(v)

                if self.key_mod in KH.MOUSE_BUTTONS:
                    KH.remove_mouse_button(self.key_mod, pr.kh, k)

        if self.name in self.kmis_map:
            del self.kmis_map[self.name]

    def filter_by_mode(self, pr):
        return self.mode in pr.mode_filter

    def filter_list(self, pr):
        return (
            self.filter_by_mode(pr)
            and (not pr.show_only_new_pms or self.is_new)
            and Tag.check_pm(self)
        )

    def has_tag(self, tag):
        if not self.tag:
            return tag == CC.UNTAGGED
        tags = {t.strip() for t in self.tag.split(",")}
        return tag in tags

    def get_tags(self):
        if not self.tag:
            return None
        return [t.strip() for t in self.tag.split(",")]

    def add_tag(self, tag):
        tag = tag.strip()
        if not tag or tag == CC.UNTAGGED:
            return

        if self.tag:
            tags = {t.strip() for t in self.tag.split(",")}
        else:
            tags = set()
        tags.add(tag)
        self.tag = ", ".join(sorted(tags))

    def remove_tag(self, tag):
        if not self.tag:
            return False
        tags = {t.strip() for t in self.tag.split(",")}
        tags.discard(tag)
        self.tag = ", ".join(sorted(tags))

    def from_dict(self, value):
        pass

    def to_dict(self):
        d = {}
        return d

    def to_hotkey(self, use_key_names=False):
        return KH.to_hotkey(
            self.key,
            self.ctrl,
            self.shift,
            self.alt,
            self.oskey,
            self.key_mod,
            self.any,
            use_key_names=use_key_names,
            chord=self.chord,
        )

    def get_data(self, key):
        value = getattr(schema.parse(self.data), key)
        return value

    def set_data(self, key, value):
        self.data = schema.encode(self.data, key, value)

    def clear_data(self, *args):
        self.data = schema.clear(self.data, *args)

    @property
    def ed(self):
        # Guard: editors may not be registered yet during initialization
        prefs = get_prefs()
        if not prefs.editors:
            return None
        return prefs.editors.get(self.mode)

    def __str__(self):
        return "[%s][%s][%s] %s" % (
            "V" if self.enabled else " ",
            self.mode,
            self.to_hotkey(),
            self.label,
        )
