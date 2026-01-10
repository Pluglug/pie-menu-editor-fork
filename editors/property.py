# pyright: reportInvalidTypeForm=false
# editors/property.py - Property editor
# LAYER = "editors"
#
# Moved from: ed_property.py (PME2 layer separation)

LAYER = "editors"

import bpy
from bpy import types as bpy_types
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator
from .. import pme
from ..core.schema import schema as pme_schema
from .base import (
    EditorBase,
    PME_OT_pmi_add,
    WM_OT_pmi_icon_select,
    PME_OT_pmi_move,
    WM_OT_pmi_data_edit,
)
from ..infra.debug import *
from ..addon import get_prefs, temp_prefs
from ..ui.layout import lh
from ..ui import tag_redraw, shorten_str
from ..bl_utils import uname
from ..infra.collections import MoveItemOperator
from .. import operator_utils
from ..core.constants import MAX_STR_LEN

# =============================================================================
# Schema Definitions (PROPERTY)
# =============================================================================
# NOTE: pr_prop_type is stored in pm.poll_cmd, not pm.data.
#       This schema definition is for JSON export/import consistency.
#       The converter/serializer must handle this special case.
#
# Type prefix: "pr" (matches uid prefix for PROPERTY mode)
# All properties use pr_ prefix for consistency with other modes.
pme_schema.EnumProperty(
    "pr", "pr_prop_type", "BOOL",
    [
        ('BOOL', "Boolean", ""),
        ('INT', "Integer", ""),
        ('FLOAT', "Float", ""),
        ('STRING', "String", ""),
        ('ENUM', "Enum", ""),
    ],
)
pme_schema.IntProperty("pr", "pr_vector", 1)
pme_schema.BoolProperty("pr", "pr_mulsel", False)
pme_schema.BoolProperty("pr", "pr_hor_exp", True)
pme_schema.BoolProperty("pr", "pr_exp", True)
pme_schema.BoolProperty("pr", "pr_save", True)


PROP_GETTERS = dict()
PROP_SETTERS = dict()
PROP_UPDATES = dict()
ARG_GETTERS = dict()
ARG_SETTERS = dict()

SUBTYPE_NUMBER_ARRAY_ITEMS = [
    'COLOR', 'TRANSLATION', 'DIRECTION', 'VELOCITY', 'ACCELERATION',
    'MATRIX', 'EULER', 'QUATERNION', 'AXISANGLE', 'XYZ', 'XYZ_LENGTH',
    'COLOR_GAMMA', 'COORDINATES', 'LAYER', 'LAYER_MEMBER', 'NONE'
]
SUBTYPE_NUMBER_ITEMS = [
    'PIXEL', 'UNSIGNED', 'PERCENTAGE', 'FACTOR', 'ANGLE', 'TIME',
    'TIME_ABSOLUTE', 'DISTANCE', 'DISTANCE_CAMERA', 'POWER',
    'TEMPERATURE', 'NONE'
]

PROPERTY_SUBTYPE = {
    'IntProperty': SUBTYPE_NUMBER_ITEMS,
    "IntVectorProperty": SUBTYPE_NUMBER_ARRAY_ITEMS,
    'FloatProperty': SUBTYPE_NUMBER_ITEMS,
    'FloatVectorProperty': SUBTYPE_NUMBER_ARRAY_ITEMS,
    'StringProperty': [
        'FILE_PATH', 'DIR_PATH', 'FILE_NAME', 'BYTE_STRING', 'PASSWORD', 'NONE'
    ]
}

del SUBTYPE_NUMBER_ARRAY_ITEMS
del SUBTYPE_NUMBER_ITEMS


def size_get(self):
    return get_prefs().selected_pm.get_data("pr_vector")


def size_set(self, value):
    pr = get_prefs()
    pm = pr.selected_pm
    pm.set_data("pr_vector", value)
    pmi_remove(pm, "subtype")
    pmi_remove(pm, "unit")
    pmi_remove(pm, "default")

    ARG_GETTERS.clear()
    ARG_SETTERS.clear()

    if pm.name in pr.props:
        del pr.props[pm.name]

    pm.ed.register_dynamic_props(pm)


def hor_exp_get(self):
    return get_prefs().selected_pm.get_data("pr_hor_exp")


def hor_exp_set(self, value):
    get_prefs().selected_pm.set_data("pr_hor_exp", value)
    tag_redraw()


def save_get(self):
    return not get_prefs().selected_pm.get_data("pr_save")


def save_set(self, value):
    get_prefs().selected_pm.set_data("pr_save", not value)


def exp_get(self):
    return get_prefs().selected_pm.get_data("pr_exp")


def exp_set(self, value):
    get_prefs().selected_pm.set_data("pr_exp", value)


def multiselect_get(self):
    return get_prefs().selected_pm.get_data("pr_mulsel")


def multiselect_set(self, value):
    pm = get_prefs().selected_pm
    pm.set_data("pr_mulsel", value)
    pmi_remove(pm, "default")

    pm.ed.register_default_enum_prop(pm)
    update_user_property()


def ed_text_get(self):
    return self.get("text", "")


def ed_text_set(self, value):
    try:
        if self.name == 'GET':
            compile("def _():" + value, "<string>", "exec")
        else:
            compile(value, "<string>", "exec")
        self.icon = ""
    except:
        self.icon = 'ERROR'

    self["text"] = value
    update_user_property()


def ed_type_get(self):
    return self.bl_rna.properties["ed_type"].enum_items.find(
        get_prefs().selected_pm.poll_cmd
    )


def ed_type_set(self, value):
    pm = get_prefs().selected_pm
    items = self.bl_rna.properties["ed_type"].enum_items
    v = items.find(pm.poll_cmd)
    if v == value:
        return

    pm.poll_cmd = items[value].identifier
    pm.clear_data("mulsel", "hor_exp", "vector")
    clear_arg_pmis(pm)

    ARG_GETTERS.clear()
    ARG_SETTERS.clear()

    pm.ed.register_dynamic_props(pm)
    if pm.poll_cmd == 'ENUM':
        bpy.ops.pme.pmi_add('INVOKE_DEFAULT')


def props(name=None, value=None):
    pr = get_prefs()
    if name is None:
        return pr.props

    if value is None:
        return getattr(pr.props, name, None)

    setattr(pr.props, name, value)

    return True


def gen_get(prop_name, mode):
    key = prop_name
    if key in PROP_GETTERS:
        return PROP_GETTERS[key]

    def _get(self):
        pm = get_prefs().pie_menus[prop_name]
        pmi = pm.pmis[mode]
        pme.context.pm = pm
        exec_globals = pme.context.gen_globals()
        exec_globals.update(menu=prop_name, slot=pmi.name)
        pme.context.exe(
            "def get(self):" + operator_utils.add_default_args(pmi.text), exec_globals
        )
        return exec_globals["get"](self)

    PROP_GETTERS[key] = _get
    return PROP_GETTERS[key]


def gen_set(prop_name, mode):
    key = prop_name
    if key in PROP_SETTERS:
        return PROP_SETTERS[key]

    def _set(self, value):
        pm = get_prefs().pie_menus[prop_name]
        pmi = pm.pmis[mode]
        pme.context.pm = pm
        exec_globals = pme.context.gen_globals()
        exec_globals.update(menu=prop_name, slot=pmi.name, value=value, self=self)
        pme.context.exe(operator_utils.add_default_args(pmi.text), exec_globals)

    PROP_SETTERS[key] = _set
    return PROP_SETTERS[key]


def gen_update(prop_name, mode):
    key = prop_name
    if key in PROP_UPDATES:
        return PROP_UPDATES[key]

    def _update(self, context):
        pm = get_prefs().pie_menus[prop_name]
        pmi = pm.pmis[mode]
        pme.context.pm = pm
        exec_globals = pme.context.gen_globals()
        exec_globals.update(menu=prop_name, slot=pmi.name, self=self)
        pme.context.exe(operator_utils.add_default_args(pmi.text), exec_globals)

    PROP_UPDATES[key] = _update
    return PROP_UPDATES[key]


def gen_enum_items(enum_prop):
    items = []
    for i, v in enumerate(enum_prop.enum_items):
        items.append((v.identifier, v.name, v.description, v.icon, i))

    return items


def gen_prop_subtype_enum_items(prop_type, is_vector=False):
    items = []
    prop_name = prop_type.capitalize() + ('VectorProperty' if is_vector else 'Property')
    subtypes = PROPERTY_SUBTYPE.get(prop_name, [])

    for subtype in reversed(subtypes):
        name = subtype.replace("_", " ").title()
        items.append((subtype, name, name))

    return items


def gen_pm_enum_items(pm):
    items = []
    i = 0
    enum_flag = pm.get_data("pr_mulsel")
    for pmi in pm.pmis:
        if pmi.mode != 'PROP':
            continue

        id, sep, name = pmi.name.partition("|")
        name = id if not name and not sep else name
        items.append((id, name, name, pmi.icon, 1 << i if enum_flag else i))
        i += 1

    return items


def gen_arg_getter(name, ptype, default):
    key = "%s:%s" % (ptype, name)
    if key in ARG_GETTERS:
        return ARG_GETTERS[key]

    def getter(self):
        pm = get_prefs().selected_pm
        pmi = pm.pmis.get(name, None)
        value = eval(pmi.text) if pmi else default

        prop = self.bl_rna.properties["ed_" + name]
        if prop.__class__.__name__ == "EnumProperty":
            if isinstance(value, str):
                value = prop.enum_items.find(value)
            elif isinstance(value, set):
                new_value = 0
                for v in value:
                    new_value |= prop.enum_items[v].value

                value = new_value

        return value

    ARG_GETTERS[key] = getter
    return ARG_GETTERS[key]


def gen_arg_setter(name, ptype, update_dynamic_props=False):
    key = "%s:%s" % (ptype, name)
    if key in ARG_SETTERS:
        return ARG_SETTERS[key]

    def setter(self, value):
        DBG_PROP and logh("Set: '%s' = %s" % (name, repr(value)))
        pm = get_prefs().selected_pm
        prop = self.bl_rna.properties["ed_" + name]
        if prop.__class__.__name__ == "EnumProperty":
            if pm.get_data("pr_mulsel"):
                new_value = set()
                for v in prop.enum_items:
                    if v.value & value:
                        new_value.add(v.identifier)
                value = new_value
            else:
                value = prop.enum_items[value].identifier

        if name in pm.pmis:
            if prop.default == value:
                pmi_remove(pm, name)

        else:
            if prop.default != value:
                pmi = pm.pmis.add()
                pmi.name = name
                pmi.mode = 'EMPTY'

        if name in pm.pmis:
            pmi = pm.pmis[name]
            pmi.text = repr(value)

        if update_dynamic_props:
            pm.ed.register_dynamic_props(pm)
        else:
            if pm.poll_cmd == 'ENUM':
                pm.ed.register_default_enum_prop(pm)
            else:
                pm.ed.register_default_prop(pm)

            register_user_property(pm)

    ARG_SETTERS[key] = setter
    return ARG_SETTERS[key]


def gen_default_value(pm, use_pmi=False):
    if use_pmi and "default" in pm.pmis:
        pmi = pm.pmis["default"]
        value = eval(pmi.text)
    else:
        value = 0
        if pm.poll_cmd == 'STRING':
            value = ""
        elif pm.poll_cmd == 'BOOL':
            value = False
        elif pm.poll_cmd == 'ENUM':
            if pm.get_data("pr_mulsel"):
                return set()

            for pmi in pm.pmis:
                if pmi.mode == 'PROP':
                    value, _, _ = pmi.text.partition("|")
                    break
            else:
                return None

        size = pm.get_data("pr_vector")
        if size > 1:
            value = [value] * size

    return value


def prop_by_type(prop_type, is_vector=False):
    name = "VectorProperty" if is_vector else "Property"
    name = prop_type.title() + name
    return getattr(bpy.props, name)


def pm_to_value(pm, name):
    pmi = pm.pmis.get(name, None)
    return eval(pmi.text) if pmi else None


def pmi_to_value(pmi):
    try:
        return eval(pmi.text)
    except:
        return None


def pmi_remove(pm, name):
    if name in pm.pmis:
        pm.pmis.remove(pm.pmis.find(name))


def register_user_property(pm):
    DBG_PROP and logh("Reg Prop: " + pm.name)
    if not pm.enabled:
        return

    # Validate poll_cmd contains a valid property type
    # PROPERTY mode uses poll_cmd for property type, not poll condition
    valid_prop_types = {'BOOL', 'INT', 'FLOAT', 'STRING', 'ENUM'}
    if pm.poll_cmd not in valid_prop_types:
        logw(
            "PME: invalid property type in poll_cmd",
            f"pm={pm.name}",
            f"poll_cmd={pm.poll_cmd!r}",
            "defaulting to BOOL"
        )
        pm.poll_cmd = 'BOOL'

    pr = get_prefs()

    size = pm.get_data("pr_vector")
    bpy_prop = prop_by_type(pm.poll_cmd, size > 1)
    kwargs = dict(name=pm.name)
    options = set()
    if pm.poll_cmd == 'ENUM':
        kwargs["items"] = []
        if pm.get_data("pr_mulsel"):
            options.add('ENUM_FLAG')

    if size > 1:
        kwargs["size"] = size

    i = 0
    enum_flag = pm.get_data("pr_mulsel")
    for pmi in pm.pmis:
        if pmi.mode == 'EMPTY':
            kwargs[pmi.name] = pmi_to_value(pmi)

        elif pmi.mode == 'PROP':
            id, sep, name = pmi.name.partition("|")
            name = id if not name and not sep else name
            kwargs["items"].append(
                (id, name, name, pmi.icon, 1 << i if enum_flag else i)
            )
            i += 1

    if 'GET' in pm.pmis:
        kwargs["get"] = gen_get(pm.name, 'GET')
    if 'SET' in pm.pmis:
        kwargs["set"] = gen_set(pm.name, 'SET')
    if 'UPDATE' in pm.pmis:
        kwargs["update"] = gen_update(pm.name, 'UPDATE')

    DBG_PROP and logi(pm.name, kwargs)
    DBG_PROP and logi(pm.data)

    # Sanitize EnumProperty default: set type requires ENUM_FLAG
    if pm.poll_cmd == 'ENUM' and 'default' in kwargs:
        default_val = kwargs['default']
        has_enum_flag = 'ENUM_FLAG' in options
        if isinstance(default_val, set) and not has_enum_flag:
            # User property has corrupted default (set without ENUM_FLAG)
            # Convert to single value or remove default entirely
            if default_val:
                # Use first element of the set
                kwargs['default'] = next(iter(default_val))
                logw("PME: sanitized EnumProperty default", f"pm={pm.name}", f"was_set={default_val}")
            else:
                # Empty set - remove default
                del kwargs['default']
                logw("PME: removed empty set default", f"pm={pm.name}")

    pmi = pm.pmis.get('CLASS', None)
    cls = getattr(bpy_types, pmi.text) if pmi else pr.props.__class__

    # Guard against corrupted user properties crashing the entire addon registration
    try:
        setattr(cls, pm.name, bpy_prop(options=options, **kwargs))
    except Exception as ex:
        logw("PME: failed to register user property", f"pm={pm.name}", f"error={ex}")
        # Property registration failed, but don't crash addon


def unregister_user_property(pm):
    pr = get_prefs()
    if pm.name in pr.props:
        del pr.props[pm.name]

    pmi = pm.pmis.get('CLASS', None)
    cls = getattr(bpy_types, pmi.text) if pmi else pr.props.__class__
    if hasattr(cls, pm.name):
        delattr(cls, pm.name)


def update_arg_pmi(pm, name, value):
    ep = temp_prefs().ed_props
    ep_name = "ed_" + name
    prop = ep.bl_rna.properties[ep_name]
    if name in pm.pmis:
        if prop.default == value:
            pmi_remove(pm, name)
            return

    else:
        if prop.default == value:
            return

        pmi = pm.pmis.add()
        pmi.name = name
        pmi.mode = 'EMPTY'

    pmi = pm.pmis[name]
    pmi.text = repr(value)


def clear_arg_pmis(pm):
    indices = []
    for i, pmi in enumerate(pm.pmis):
        if pmi.mode == 'EMPTY' or pmi.mode == 'PROP':
            indices.append(i)

    for i in reversed(indices):
        pm.pmis.remove(i)


def update_user_property(self=None, context=None):
    pm = get_prefs().selected_pm
    ep = temp_prefs().ed_props
    value = ep.ed_default
    if isinstance(value, bpy_types.bpy_prop_array):
        value = list(value)

    update_arg_pmi(pm, "default", value)
    if pm.poll_cmd in {'INT', 'FLOAT'}:
        update_arg_pmi(pm, "min", ep.ed_min)
        update_arg_pmi(pm, "max", ep.ed_max)
        update_arg_pmi(pm, "step", ep.ed_step)
        update_arg_pmi(pm, "subtype", ep.ed_subtype)

        if pm.poll_cmd == 'FLOAT':
            update_arg_pmi(pm, "unit", ep.ed_unit)
            update_arg_pmi(pm, "precision", ep.ed_precision)

    elif pm.poll_cmd == 'STRING':
        update_arg_pmi(pm, "subtype", ep.ed_subtype)

    register_user_property(pm)


class PME_OT_prop_class_set(Operator):
    bl_idname = "pme.prop_class_set"
    bl_label = "Internal (PME)"
    bl_description = "Where to store the data of the property"
    bl_property = "item"
    bl_options = {'INTERNAL'}

    enum_items = None

    def get_items(self, context):
        if not PME_OT_prop_class_set.enum_items:
            enum_items = []

            ID = bpy_types.ID
            for tp_name in dir(bpy_types):
                tp = getattr(bpy_types, tp_name)
                if isinstance(tp, type) and \
                        issubclass(tp, ID) and tp is not ID:
                    enum_items.append((
                        tp_name, tp_name, ""))

            PME_OT_prop_class_set.enum_items = enum_items

        return PME_OT_prop_class_set.enum_items

    item: EnumProperty(items=get_items, options={'SKIP_SAVE'})
    add: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        PME_OT_prop_class_set.enum_items = None
        pm = get_prefs().selected_pm
        pmi = pm.pmis.get('CLASS', None)
        if pmi and pmi.text == self.item:
            return {'CANCELLED'}

        unregister_user_property(pm)

        if pmi:
            pmi.text = self.item
        else:
            pmi = pm.pmis.add()
            pmi.mode = 'COMMAND'
            pmi.name = 'CLASS'
            pmi.text = self.item

        register_user_property(pm)
        pm.ed.update_preview_path(pm)
        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_prop_class_set.enum_items = None
        if self.add:
            context.window_manager.invoke_search_popup(self)
        else:
            pm = get_prefs().selected_pm
            unregister_user_property(pm)
            pmi_remove(pm, 'CLASS')

            # rename_pm(pm)
            register_user_property(pm)
            pm.ed.update_preview_path(pm)
        return {'FINISHED'}


class PME_OT_prop_script_set(Operator):
    bl_idname = "pme.prop_script_set"
    bl_label = "Internal (PME)"
    bl_description = "Add/remove the function"
    bl_options = {'INTERNAL'}

    add: BoolProperty(options={'SKIP_SAVE'})
    mode: EnumProperty(
        items=(
            ('GET', "", ""),
            ('SET', "", ""),
            ('UPDATE', "", ""),
            ('INIT', "", ""),
            ('CLASS', "", ""),
        ),
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        pr = get_prefs()
        pm = pr.selected_pm
        if self.add:
            pmi = pm.pmis.add()
            pmi.mode = 'COMMAND'
            pmi.name = self.mode
            if self.mode == 'GET':
                default_value = 0
                if pm.poll_cmd == 'STRING':
                    default_value = ""
                elif pm.poll_cmd == 'BOOL':
                    default_value = False

                size = pm.get_data("pr_vector")
                if size > 1:
                    default_value = [default_value] * size

                pmi.text = "return self.get(menu, %s)" % repr(default_value)
            elif self.mode == 'SET':
                pmi.text = "self[menu] = value"
            elif self.mode == 'UPDATE':
                pmi.text = "print('On Update', menu, '=', repr(props(menu)))"
            elif self.mode == 'INIT':
                pmi.text = "print('On Init', menu, '=', repr(props(menu)))"

        else:
            for i, pmi in enumerate(pm.pmis):
                if pmi.name == self.mode:
                    pm.pmis.remove(i)
                    break

        register_user_property(pm)
        tag_redraw()
        return {'FINISHED'}


class PME_OT_prop_pmi_move(MoveItemOperator, Operator):
    bl_idname = "pme.prop_pmi_move"

    def filter_item(self, pmi, idx):
        return pmi.mode == 'PROP'

    def get_collection(self):
        return get_prefs().selected_pm.pmis

    def get_icon(self, pmi, idx):
        pm = get_prefs().selected_pm
        return pm.ed.get_pmi_icon(pm, pmi, idx)

    def get_title(self):
        pm = get_prefs().selected_pm
        pmi = pm.pmis[self.old_idx]
        return "Move " + shorten_str(pmi.name) if pmi.name.strip() else "Move Slot"

    def finish(self):
        pm = get_prefs().selected_pm
        pm.ed.on_pmi_move(pm)

        tag_redraw()


class Editor(EditorBase):

    def __init__(self):
        self.id = 'PROPERTY'
        EditorBase.__init__(self)

        self.docs = "#Property_Editor"
        self.use_preview = False
        self.has_hotkey = False
        self.copy_paste_slot = False
        self.editable_slots = False
        self.default_pmi_data = "pr?"
        self.supported_slot_modes = {'EMPTY', 'COMMAND'}
        self.pmi_move_operator = PME_OT_prop_pmi_move.bl_idname

        self.cmd_pmis = {}

    def update_preview_path(self, pm):
        path = "props().%s" % pm.name
        v = None
        pmi = pm.pmis.get('CLASS', None)
        if pmi:
            if pmi.text == "WindowManager":
                path = "C.window_manager.%s" % pm.name
            elif pmi.text == "Object":
                path = "C.active_object.%s" % pm.name
            else:
                path = "?"
                v1 = pmi.text.lower() + "s"
                v2 = pmi.text.lower() + "es"
                v = hasattr(bpy.data, v1) and v1 or hasattr(bpy.data, v2) and v2
                if v:
                    objs = getattr(bpy.data, v)
                    if objs:
                        path = "D.%s[0].%s" % (v, pm.name)

        temp_prefs().ed_props.ed_preview_path = path

    def register_props(self, pm):
        self.unregister_props()

        self.register_temp_prop(
            "ed_preview_path", StringProperty(description="Preview path")
        )

        self.register_pmi_prop(
            "ed_text",
            StringProperty(
                get=ed_text_get, set=ed_text_set, maxlen=MAX_STR_LEN
            ),
        )

        self.register_temp_prop(
            "ed_type",
            EnumProperty(
                name="Property Type",
                description="Property type",
                items=(
                    ('BOOL', "Boolean", "Boolean property", 'MESH_PLANE', 0),
                    ('ENUM', "Enum", "Enum property", 'MESH_GRID', 1),
                    ('INT', "Int", "Int property", 'MESH_CUBE', 2),
                    ('FLOAT', "Float", "Float property", 'MESH_UVSPHERE', 3),
                    ('STRING', "String", "String property", 'MONKEY', 4),
                ),
                get=ed_type_get,
                set=ed_type_set,
            ),
        )

        self.register_temp_prop(
            "ed_save",
            BoolProperty(
                name="Restore Default Value",
                description="Restore Default Value",
                get=save_get,
                set=save_set,
            ),
        )

        self.register_temp_prop(
            "ed_exp",
            BoolProperty(
                name="Expand",
                description="Expand items",
                get=exp_get,
                set=exp_set,
            ),
        )

        self.register_dynamic_props(pm)

    def unregister_props(self):
        super().unregister_props()
        # store_ed_generated_funcs()

    def register_default_enum_prop(self, pm):
        DBG_PROP and logi("Reg Def Enum Prop")
        enum_items = gen_pm_enum_items(pm)
        options = set()
        if pm.get_data("pr_mulsel"):
            options.add('ENUM_FLAG')

        self.register_arg_prop(
            pm,
            EnumProperty,
            "default",
            "Default Value",
            items=enum_items,
            options=options,
        )

    def register_default_prop(self, pm):
        size = pm.get_data("pr_vector")
        bpy_prop = prop_by_type(pm.poll_cmd, size > 1)
        default_value = 0
        bpy_prop_name = bpy_prop.__name__
        if bpy_prop_name == "StringProperty":
            default_value = ""
        elif bpy_prop_name == "BoolProperty":
            default_value = False

        kwargs = {}

        if size > 1:
            default_value = [default_value] * size
            kwargs["size"] = size

        for pmi in pm.pmis:
            if pmi.mode == 'EMPTY' and pmi.name != "default":
                kwargs[pmi.name] = pmi_to_value(pmi)

        self.register_arg_prop(
            pm, bpy_prop, "default", "Default Value", default_value, **kwargs
        )

    def register_arg_prop(
        self,
        pm,
        bpy_prop,
        prop,
        name,
        default=None,
        use_subtype=False,
        update_dynamic_props=False,
        **kwargs
    ):
        DBG_PROP and logi("Reg arg prop: '%s'" % name)
        if default is None:
            default = 0
        else:
            kwargs["default"] = default

        if use_subtype:
            pmi = pm.pmis.get("subtype", None)
            if pmi:
                kwargs[pmi.name] = pmi_to_value(pmi)

            pmi = pm.pmis.get("unit", None)
            if pmi:
                kwargs[pmi.name] = pmi_to_value(pmi)

        get_ = gen_arg_getter(prop, bpy_prop.__name__, default)
        set_ = gen_arg_setter(prop, bpy_prop.__name__, update_dynamic_props)
        self.register_temp_prop(
            "ed_" + prop, bpy_prop(name=name, get=get_, set=set_, **kwargs)
        )

        # store_ed_generated_funcs(prop, get_, set_)

    def register_dynamic_props(self, pm):
        size = pm.get_data("pr_vector")
        bpy_prop = prop_by_type(pm.poll_cmd)

        self.update_preview_path(pm)

        if pm.poll_cmd == 'ENUM':
            self.register_default_enum_prop(pm)

            self.register_temp_prop(
                "ed_multiselect",
                BoolProperty(
                    name="Multi-Select", get=multiselect_get, set=multiselect_set
                ),
            )

        else:
            self.register_default_prop(pm)

        if pm.poll_cmd != 'STRING':
            self.register_temp_prop(
                "ed_hor_exp",
                BoolProperty(
                    name="Horizontal Layout", get=hor_exp_get, set=hor_exp_set
                ),
            )

        if pm.poll_cmd in {'INT', 'FLOAT', 'BOOL'}:
            self.register_temp_prop(
                "ed_size",
                IntProperty(
                    name="Property Size", min=1, max=32, get=size_get, set=size_set
                ),
            )

        if pm.poll_cmd in {'INT', 'FLOAT'}:
            subtype = pm_to_value(pm, "subtype") or 'NONE'
            unit = pm_to_value(pm, "unit") or 'NONE'
            self.register_arg_prop(
                pm,
                bpy_prop,
                "min",
                "Min Value",
                -(2**31),
                subtype == 'ANGLE' or unit == 'ROTATION',
            )
            self.register_arg_prop(
                pm,
                bpy_prop,
                "max",
                "Max Value",
                2**31 - 1,
                subtype == 'ANGLE' or unit == 'ROTATION',
            )
            self.register_arg_prop(
                pm, bpy_prop, "step", "Step", 1 if pm.poll_cmd == 'INT' else 3
            )
            if pm.poll_cmd == 'FLOAT':
                self.register_arg_prop(
                    pm, IntProperty, "precision", "Precision", 2, min=0, max=6
                )
                self.register_arg_prop(
                    pm,
                    EnumProperty,
                    "unit",
                    "Unit",
                    update_dynamic_props=True,
                    items=gen_enum_items(
                        bpy_types.FloatProperty.bl_rna.properties['unit']
                    ),
                )

        if pm.poll_cmd in {'INT', 'FLOAT', 'STRING'}:
            self.register_arg_prop(
                pm,
                EnumProperty,
                "subtype",
                "Subtype",
                update_dynamic_props=True,
                items=gen_prop_subtype_enum_items(pm.poll_cmd, size > 1),
            )

        register_user_property(pm)

    def init_pm(self, pm):
        super().init_pm(pm)

        register_user_property(pm)

        pr = get_prefs()
        if not pm.get_data("pr_save") and pm.name in pr.props:
            del pr.props[pm.name]

        if 'INIT' in pm.pmis:
            pme.context.pm = pm
            pmi = pm.pmis['INIT']
            exec_globals = pme.context.gen_globals()
            exec_globals.update(menu=pm.name, slot=pmi.name)
            pme.context.exe(operator_utils.add_default_args(pmi.text), exec_globals)

    def on_pm_add(self, pm):
        pm.poll_cmd = 'BOOL'

    def on_pm_remove(self, pm):
        unregister_user_property(pm)
        super().on_pm_remove(pm)

    def on_pm_duplicate(self, from_pm, pm):
        EditorBase.on_pm_duplicate(self, from_pm, pm)
        register_user_property(pm)

    def on_pm_enabled(self, pm, value):
        super().on_pm_enabled(pm, value)

        if pm.enabled:
            register_user_property(pm)
        else:
            unregister_user_property(pm)

    def on_pm_rename(self, pm, name):
        super().on_pm_rename(pm, name)
        unregister_user_property(pm)
        register_user_property(pm)
        self.update_preview_path(pm)

    def on_pmi_add(self, pm, pmi):
        pmi.mode = 'PROP'
        pmi.name = uname(pm.pmis, "Item", "", 1, False)
        if pm.poll_cmd == 'ENUM':
            self.register_default_enum_prop(pm)
            register_user_property(pm)

    def on_pmi_rename(self, pm, pmi, old_name, name):
        if name in {'GET', 'SET', 'UPDATE', 'INIT', 'CLASS'}:
            return

        pmi.name = name
        if pm.poll_cmd == 'ENUM':
            if " " in pmi.name:
                pmi.name = "%s|%s" % (pmi.name.replace(" ", "_"), pmi.name)
                bpy.ops.pme.message_box(
                    message="Enum identifiers must not contain spaces\n"
                    "Replaced with '%s'" % pmi.name
                )

            self.register_default_enum_prop(pm)
            register_user_property(pm)

    def on_pmi_move(self, pm):
        if pm.poll_cmd == 'ENUM':
            self.register_default_enum_prop(pm)
            update_user_property(self, bpy.context)

    def on_pmi_remove(self, pm):
        if pm.poll_cmd == 'ENUM':
            self.register_default_enum_prop(pm)
            register_user_property(pm)

    def on_pmi_icon_edit(self, pm, pmi):
        if pm.poll_cmd == 'ENUM':
            self.register_default_enum_prop(pm)
            register_user_property(pm)

    def get_pmi_icon(self, pm, pmi, idx):
        return pmi.parse_icon('FILE_HIDDEN')

    def draw_keymap(self, layout, data):
        pass

    def draw_hotkey(self, layout, data):
        pass

    def draw_cmd_pmi(self, pm, mode, label, icon):
        if mode not in pm.pmis:
            lh.operator(
                PME_OT_prop_script_set.bl_idname, label, icon, mode=mode, add=True
            )

        else:
            pmi = pm.pmis[mode]
            lh.save()
            lh.row()
            lh.prop(pmi, "ed_text", "", icon, alert=pmi.icon == 'ERROR')
            lh.operator(PME_OT_prop_script_set.bl_idname, "", 'X', add=False, mode=mode)
            lh.restore()

    def draw_extra_settings(self, layout, pm):
        ep = temp_prefs().ed_props
        lh.save()
        lh.column(layout)

        lh.save()
        lh.row()
        pmi = pm.pmis.get('CLASS', None)
        lh.operator(
            PME_OT_prop_class_set.bl_idname,
            "Store in %s Instances" % pmi.text if pmi else "Store in Addon Preferences",
            add=True,
        )
        if pmi:
            lh.operator(PME_OT_prop_class_set.bl_idname, "", 'X', add=False)

        lh.restore()
        if not pmi:
            lh.save()
            lh.box()
            lh.prop(ep, "ed_save")
            lh.restore()

        lh.sep()

        self.draw_cmd_pmi(pm, 'GET', "Getter", 'PASTEDOWN')
        self.draw_cmd_pmi(pm, 'SET', "Setter", 'COPYDOWN')
        self.draw_cmd_pmi(pm, 'UPDATE', "On Update", 'FILE_REFRESH')
        self.draw_cmd_pmi(pm, 'INIT', "On Init", 'PLAY')

        if pm.poll_cmd in {'INT', 'FLOAT', 'BOOL'}:
            lh.sep()
            lh.prop(ep, "ed_size")

        lh.restore()

    def draw_prop(self, prop, hide_text=True, hor=True, expand=False):
        lh.save()
        lh.split(factor=0.33)
        lh.label("%s:" % self.ep.bl_rna.properties[prop].name)
        if hor:
            lh.row()

        if prop == "ed_default":
            lh.prop_compact(self.ep, prop, "" if hide_text else None, expand=expand)

        elif hide_text:
            lh.prop(self.ep, prop, "", expand=expand)
        else:
            lh.prop(self.ep, prop, expand=expand)

        lh.restore()

    def draw_enum_item(self, pm, pmi, idx):
        lh.save()
        lh.row()
        self.draw_item(pm, pmi, idx)
        self.draw_pmi_menu_btn(self.pr, idx)
        lh.restore()

    def draw_items(self, layout, pm):
        self.pr = pr = get_prefs()
        self.tpr = tpr = temp_prefs()
        self.ep = tpr.ed_props
        pm = pr.selected_pm

        layout = lh.column(layout)
        lh.prop(self.ep, "ed_type", "")

        lh.box(layout)
        lh.column()
        enum_flag = pm.get_data("pr_mulsel")
        hor_exp = pm.get_data("pr_hor_exp")
        exp = pm.get_data("pr_exp")
        size = pm.get_data("pr_vector")
        # subtype = pm.pmis.get("subtype", "")
        # subtype = subtype and pmi_to_value(subtype)
        subtype = pm_to_value(pm, "subtype")
        hor_expand = hor_exp
        expand = exp or enum_flag

        if subtype == 'DIRECTION':
            expand = True
        elif subtype and "COLOR" in subtype:
            expand = False

        if size > 1:
            hor_expand = size <= 4

        hide_text = pm.poll_cmd != 'ENUM' or not exp
        self.draw_prop("ed_default", hide_text, hor_expand, expand)

        if pm.poll_cmd in {'INT', 'FLOAT'}:
            lh.sep()
            self.draw_prop("ed_min")
            self.draw_prop("ed_max")
            self.draw_prop("ed_step")
            if pm.poll_cmd == 'FLOAT':
                self.draw_prop("ed_precision")

            lh.sep()
            self.draw_prop("ed_subtype")

        if pm.poll_cmd == 'FLOAT':
            self.draw_prop("ed_unit")

        elif pm.poll_cmd == 'ENUM':
            self.draw_prop("ed_multiselect")
            if not self.ep.ed_multiselect:
                self.draw_prop("ed_exp")

            if self.ep.ed_multiselect or self.ep.ed_exp:
                self.draw_prop("ed_hor_exp")

        if size > 1:
            lh.sep()
            if pm.poll_cmd == 'FLOAT':
                self.draw_prop("ed_exp")

            self.draw_prop("ed_hor_exp")

        elif pm.poll_cmd == 'STRING':
            lh.sep()
            self.draw_prop("ed_subtype")

        if pm.poll_cmd == 'ENUM':
            lh.box(layout)
            lh.column()
            lh.label("Items:")
            for i, pmi in enumerate(pm.pmis):
                if pmi.mode == 'PROP':
                    self.draw_enum_item(pm, pmi, i)

            lh.operator(PME_OT_pmi_add.bl_idname, "Add Slot", 'ADD')

        lh.box(layout)
        col = lh.column()
        lh.row()
        lh.label("Preview:")
        lh.row(alignment='RIGHT')

        lh.operator(
            "pme.popup_property",
            self.ep.ed_preview_path,
            'GREASEPENCIL',
            emboss=False,
            auto_close=True,
            path="temp_prefs().ed_props.ed_preview_path",
            title="Preview Path",
        )
        # lh.label(self.ep.ed_preview_path)
        lh.lt(col)
        lh.sep()
        if hor_exp:
            lh.row()

        obj = pr.props
        if not self.ep.ed_preview_path.startswith("props()."):
            obj = None
            obj_path, _, _ = self.ep.ed_preview_path.rpartition(".")
            if obj_path:
                obj = pme.context.eval(obj_path)

        if obj and hasattr(obj.__class__, pm.name):
            lh.prop_compact(obj, pm.name, toggle=True, expand=exp)


def register():
    Editor()
    pme.context.add_global("props", props)
