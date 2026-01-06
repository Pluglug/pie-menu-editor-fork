# pyright: reportInvalidTypeForm=false
# property_utils.py - Property parsing and manipulation utilities
# LAYER = "infra"
#
# Provides PropertyData class for introspecting and manipulating Blender properties.

LAYER = "infra"

import bpy
from bpy import types as bpy_types
from bpy.app import version as APP_VERSION
from bpy.props import BoolVectorProperty, CollectionProperty, PointerProperty
from bpy.types import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    OperatorProperties,
    PropertyGroup,
    WindowManager,
)
from types import BuiltinFunctionType
from mathutils import Euler
from math import pi as PI

from ..addon import get_prefs, temp_prefs, print_exc
from .. import operator_utils


WindowManager.pme_temp = BoolVectorProperty(size=3)
BPyPropArray = type(bpy.context.window_manager.pme_temp)
del WindowManager.pme_temp


class PropertyData:
    DEFAULT_MIN = -99999
    DEFAULT_MAX = 99999
    DEFAULT_STEP = 1

    def __init__(self):
        self.clear()

    def clear(self):
        self.path = None
        self.identifier = None
        self.rna_prop = None
        self.rna_type = None
        self.data = None
        self.data_path = None
        self.threshold = None
        self.is_float = False
        self.min = self.DEFAULT_MIN
        self.max = self.DEFAULT_MAX
        self._step = self.DEFAULT_STEP
        self.custom = ""
        self.icon = None

        tpr = temp_prefs()
        if tpr:
            tpr.modal_item_prop_step_is_set = False

    @property
    def step(self):
        if self.rna_prop and self.rna_prop.subtype == 'ANGLE':
            return PI * self._step / 180

        return self._step

    def init(self, path, exec_globals, exec_locals=None):
        if path == self.path:
            return

        if exec_locals is None:
            exec_locals = dict()

        pr = get_prefs()
        self.clear()
        self.path = path
        self.data_path, self.identifier = split_prop_path(path)
        value = None

        if self.path:
            try:
                value = eval(self.path, exec_globals, exec_locals)
            except:
                pass
                # print_exc()

        if self.data_path:
            try:
                self.data = eval(self.data_path, exec_globals, exec_locals)
            except:
                print_exc(self.data_path)

            self.rna_prop = rna_prop = get_rna_prop(self.data, self.identifier)

            if rna_prop:
                self.rna_type = rna_prop_type = type(rna_prop)

                if value is None:
                    value = rna_prop.default

                if rna_prop_type == EnumProperty:
                    self.threshold = pr.get_threshold('ENUM')

                elif rna_prop_type == IntProperty:
                    self.threshold = pr.get_threshold('INT')

                elif rna_prop_type == FloatProperty:
                    self.threshold = pr.get_threshold('FLOAT')
                    self.is_float = True

                elif rna_prop_type == BoolProperty:
                    self.threshold = pr.get_threshold('BOOL')

                if (
                    rna_prop_type == IntProperty
                    or rna_prop_type == FloatProperty
                ):
                    self.min = rna_prop.soft_min
                    self.max = rna_prop.soft_max
                    self._step = rna_prop.step

                    if rna_prop_type == FloatProperty:
                        self._step *= 0.01
                    if rna_prop.subtype == 'ANGLE':
                        self._step = 180 * self._step / PI

            else:
                self.min = self.DEFAULT_MIN
                self.max = self.DEFAULT_MAX
                self._step = self.DEFAULT_STEP

        if self.threshold is None:
            if value is not None:
                value_type = type(value)
                if value_type is int:
                    self.threshold = pr.get_threshold('INT')
                    self.rna_type = IntProperty
                elif value_type is float:
                    self.threshold = pr.get_threshold('FLOAT')
                    self.is_float = True
                    self.rna_type = FloatProperty
                elif value_type is bool:
                    self.threshold = pr.get_threshold('BOOL')
                    self.rna_type = BoolProperty
            else:
                self.threshold = pr.get_threshold()


class _PGVars:
    uid = 0
    instances = {}

    @staticmethod
    def get(item):
        if not item.name:
            _PGVars.uid += 1
            item.name = str(_PGVars.uid)

        if item.name not in _PGVars.instances:
            _PGVars.instances[item.name] = _PGVars()

        return _PGVars.instances[item.name]


class DynamicPG(PropertyGroup):

    def getvar(self, var):
        pgvars = _PGVars.get(self)
        return getattr(pgvars, var)

    def hasvar(self, var):
        if not self.name or self.name not in _PGVars.instances:
            return False
        pgvars = _PGVars.get(self)
        return hasattr(pgvars, var)

    def setvar(self, var, value):
        pgvars = _PGVars.get(self)
        setattr(pgvars, var, value)
        return getattr(pgvars, var)


def to_dict(obj):
    dct = {}

    try:
        dct["name"] = obj["name"]
    except:
        pass

    if not hasattr(obj.__class__, "__annotations__"):
        return dct

    pdtype = getattr(bpy.props, "_PropertyDeferred", tuple)
    for k in obj.__class__.__annotations__:
        pd = obj.__class__.__annotations__[k]
        pfunc = getattr(pd, "function", None) or pd[0]
        pkeywords = pd.keywords if hasattr(pd, "keywords") else pd[1]
        if (
            not isinstance(pd, pdtype)
            or (isinstance(pd, tuple) and len(pd) != 2)
            or not isinstance(pfunc, BuiltinFunctionType)
        ):
            continue

        try:
            if (
                pfunc is CollectionProperty
                or pfunc is PointerProperty
            ):
                value = getattr(obj, k)
            else:
                value = obj[k]
        except:
            if "get" in pkeywords:
                continue

            value = getattr(obj, k)

        if pfunc is PointerProperty:
            dct[k] = to_dict(value)

        elif pfunc is CollectionProperty:
            dct[k] = []
            for item in value.values():
                dct[k].append(to_dict(item))

        elif isinstance(value, (bool, int, float, str)):
            dct[k] = value

    return dct


def from_dict(obj, dct):
    for k, value in dct.items():
        if isinstance(value, dict):
            from_dict(getattr(obj, k), value)

        elif isinstance(value, list):
            col = getattr(obj, k)
            col.clear()

            for item in value:
                from_dict(col.add(), item)

        else:
            if APP_VERSION >= (5, 0, 0):
                sp = obj.bl_system_properties_get(do_create=True)
                if sp is not None:
                    sp[k] = value
            else:
                obj[k] = value

            # FIXME: Tried to delete the dictionary access for 5.0 compatibility,
            # but I encountered a problem with complex serialization, so I reverted it.
            # anns = getattr(obj.__class__, "__annotations__", None)
            # if isinstance(anns, dict) and k in anns:
            #     try:
            #         setattr(obj, k, value)
            #     except (TypeError, ValueError, AttributeError) as e:
            #         print_exc(
            #             f"from_dict: failed to set {obj.__class__.__name__}.{k} = {repr(value)}: {e}"
            #         )


def to_py_value(data, key, value):
    if isinstance(value, PropertyGroup):
        return None

    if isinstance(value, OperatorProperties):
        rna_type = operator_utils.get_rna_type(operator_utils.to_bl_idname(key))
        if not rna_type:
            return None

        d = dict()
        for k in value.keys():
            py_value = to_py_value(rna_type, k, getattr(value, k))
            if py_value is None or isinstance(py_value, dict) and not py_value:
                continue
            d[k] = py_value

        return d

    is_bool = isinstance(data.properties[key], BoolProperty)

    if hasattr(value, "to_list"):
        value = value.to_list()
        if is_bool:
            value = [bool(v) for v in value]
    elif hasattr(value, "to_tuple"):
        value = value.to_tuple()
        if is_bool:
            value = tuple(bool(v) for v in value)
    elif isinstance(value, BPyPropArray):
        value = list(value)
        if is_bool:
            value = [bool(v) for v in value]
    elif isinstance(value, Euler):
        value = (value.x, value.y, value.z)

    return value


def split_prop_path(prop_path):
    data_path, _, prop = prop_path.rpartition(".")
    return data_path, prop


def get_rna_prop(data, prop):
    if not data or not prop:
        return None

    rna_type = getattr(data, "rna_type", None)
    if not rna_type:
        return None

    return rna_type.properties[prop] if prop in rna_type.properties else None


def is_enum(data, key):
    return isinstance(data.bl_rna.properties[key], EnumProperty)


def enum_id_to_value(data, key, id):
    for item in data.bl_rna.properties[key].enum_items:
        if item.identifier == id:
            return item.value
    return -1


def enum_value_to_id(data, key, value):
    return data.bl_rna.properties[key].enum_items[value].identifier
