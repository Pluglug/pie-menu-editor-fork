# pme.py - PME execution context and props
# LAYER = "infra"

import bpy

LAYER = "infra"

from .addon import get_prefs, temp_prefs, print_exc
from .infra.debug import logw, DBG_RUNTIME


class UserData:
    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def update(self, **kwargs):
        self.__dict__.update(**kwargs)

    def __getattr__(self, name):
        return self.__dict__.get(name, None)


class PMEContext:

    def __init__(self):
        self._globals = dict(
            bpy=bpy,
            pme_context=self,
            drag_x=0,
            drag_y=0,
        )
        self.pm = None
        self.pmi = None
        self.index = None
        self.icon = None
        self.icon_value = None
        self.text = None
        self.region = None
        self.last_operator = None
        self.is_first_draw = True
        self.exec_globals = None
        self.exec_locals = None
        self.exec_user_locals = dict()
        self._layout = None
        self._event = None
        self.edit_item_idx = None

    def __getattr__(self, name):
        return self._globals.get(name, None)

    def item_id(self):
        pmi = self.pmi
        id = self.pm.name
        id += pmi.name if pmi.name else pmi.text
        id += str(self.index)
        return id

    def reset(self):
        self.is_first_draw = True
        self.exec_globals = None
        self.exec_locals = None

    def add_global(self, key, value):
        self._globals[key] = value

    @property
    def layout(self):
        return self._layout

    @layout.setter
    def layout(self, value):
        self._layout = value
        self._globals["L"] = value

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, value):
        self._event = value
        self._globals["E"] = value

        if self._event:
            if self._event.type == 'WHEELUPMOUSE':
                self._globals["delta"] = 1
            elif self._event.type == 'WHEELDOWNMOUSE':
                self._globals["delta"] = -1

    @property
    def globals(self):
        if self._globals["D"].__class__.__name__ == "_RestrictData":
            # self._globals["C"] = bpy.context
            self._globals["D"] = bpy.data
        return self._globals

    def gen_globals(self, **kwargs):
        ret = dict(
            text=self.text,
            icon=self.icon,
            icon_value=self.icon_value,
            PME=temp_prefs(),
            PREFS=get_prefs(),
            **kwargs
        )

        ret.update(self.exec_user_locals)
        ret.update(self.globals)

        return ret

    def eval(self, expression, globals=None, menu=None, slot=None):
        if globals is None:
            globals = self.gen_globals()

        # globals["menu"] = menu
        # globals["slot"] = slot

        value = None
        try:
            value = eval(expression, globals)
        except:
            print_exc(expression)

        return value

    def exe(self, data, globals=None, menu=None, slot=None, use_try=True):
        if globals is None:
            globals = self.gen_globals()

        # globals["menu"] = menu
        # globals["slot"] = slot

        if not use_try:
            exec(data, globals)
            return True

        try:
            exec(data, globals)
        except:
            print_exc(data)
            return False

        return True


context = PMEContext()


class PMEProp:
    def __init__(self, type, name, default, ptype='STR', items=None):
        self.name = name
        self.default = default
        self.items = items
        self.type = type
        self.ptype = ptype

    def decode_value(self, value):
        if self.ptype == 'STR':
            return value
        elif self.ptype == 'BOOL':
            return value == "True" or value == "1"
        elif self.ptype == 'INT':
            return int(value) if value else 0


class PMEProps:
    prop_map = {}

    def IntProperty(self, type, name, default=0):
        # default = "" if default == 0 else str(default)
        self.prop_map[name] = PMEProp(type, name, default, 'INT')

    def BoolProperty(self, type, name, default=False):
        # default = "1" if default else ""
        self.prop_map[name] = PMEProp(type, name, default, 'BOOL')

    def StringProperty(self, type, name, default=""):
        self.prop_map[name] = PMEProp(type, name, default, 'STR')

    def EnumProperty(self, type, name, default, items):
        self.prop_map[name] = PMEProp(type, name, default, 'STR', items)

    def __init__(self):
        self.parsed_data = {}

    def get(self, name):
        return self.prop_map.get(name, None)

    def parse(self, text):
        if text not in self.parsed_data:
            self.parsed_data[text] = ParsedData(text)

        pd = self.parsed_data[text]
        for k, prop in self.prop_map.items():
            if prop.type == pd.type and not hasattr(pd, k):
                setattr(pd, k, prop.default)
                DBG_RUNTIME and logw("PME: defaulted missing prop", f"type={pd.type}", f"prop={k}")

        return pd

    def encode(self, text, prop, value):
        tp, _, data = text.partition("?")

        data = data.split("&")
        lst = []
        has_prop = False
        for pr in data:
            if not pr:
                continue

            k, v = pr.split("=")
            if k not in props.prop_map:
                continue

            if k == prop:
                # v = props.prop_map[k].decode_value(value)
                v = value
                has_prop = True

            if v != props.get(k).default:
                lst.append("%s=%s" % (k, v))

        if not has_prop and value != props.prop_map[prop].default:
            lst.append("%s=%s" % (prop, value))

        lst.sort()

        text = "%s?%s" % (tp, "&".join(lst))
        return text

    def clear(self, text, *args):
        tp, _, data = text.partition("?")

        data = data.split("&")
        lst = []
        for pr in data:
            if not pr:
                continue

            k, v = pr.split("=")
            if k not in props.prop_map or k in args:
                continue

            if v != props.get(k).default:
                lst.append(pr)

        lst.sort()

        text = "%s?%s" % (tp, "&".join(lst))
        return text


props = PMEProps()


class ParsedData:

    def __init__(self, text):
        self.type, _, data = text.partition("?")
        self._initialized = False  # Track if prop_map was available

        for k, prop in props.prop_map.items():
            if prop.type == self.type:
                setattr(self, k, prop.default)

        data = data.split("&")
        for prop in data:
            if not prop:
                continue
            k, v = prop.split("=")
            if k in props.prop_map:
                setattr(self, k, props.prop_map[k].decode_value(v))

        self.is_empty = True
        for k, prop in props.prop_map.items():
            if not hasattr(self, k):
                continue
            if getattr(self, k) != prop.default:
                self.is_empty = False
                break

        self._initialized = bool(props.prop_map)

    # Fallback defaults for known properties when prop_map is empty (Reload Scripts hotfix)
    # These MUST match the defaults registered in editors/*.py
    _FALLBACK_DEFAULTS = {
        # editors/pie_menu.py
        'pm_radius': -1,
        'pm_confirm': -1,
        'pm_threshold': -1,
        'pm_flick': True,
        # editors/menu.py
        'rm_title': True,
        # editors/popup.py
        'layout': 'COLUMN',
        'width': 300,
        'poll': "",
        'fixed_col': False,
        'fixed_but': False,
        'align': False,
        'column': 'ONE',
        'pd_row': 'TWO',
        'pd_box': False,
        'pd_panel': False,
        'pd_expand': True,
        # editors/panel_group.py
        'pg_wicons': False,
        'pg_context': "",
        'pg_category': "",
        'pg_space': 'CURRENT',
        'pg_region': 'UI',
        # ed_modal.py
        'confirm': True,
        'block_ui': True,
        'lock': False,
        # ed_stack_key.py
        's_undo': False,
        's_state': 'PRESS',
        # ed_sticky_key.py
        'sk_block_ui': True,
        # editors/property.py
        'vector': 1,
        'mulsel': False,
        'hor_exp': True,
        'exp': True,
        'save': True,
    }

    def __getattr__(self, name):
        # Safety net for Reload Scripts: return sensible defaults if prop_map was empty
        if name.startswith('_'):
            raise AttributeError(name)

        # Try to find the property in prop_map now (it may have been populated after __init__)
        prop = props.prop_map.get(name)
        if prop:
            default = prop.default
            object.__setattr__(self, name, default)
            DBG_RUNTIME and logw("PME: late-bound prop via __getattr__", f"type={self.type}", f"prop={name}")
            return default

        # Use hardcoded fallback defaults for known properties
        if name in self._FALLBACK_DEFAULTS:
            default = self._FALLBACK_DEFAULTS[name]
            object.__setattr__(self, name, default)
            DBG_RUNTIME and logw("PME: fallback default used", f"type={self.type}", f"prop={name}", f"default={default}")
            return default

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def value(self, name):
        prop = props.get(name)
        if not prop:
            DBG_RUNTIME and logw("PME: value() missing prop in map", f"type={self.type}", f"prop={name}")
            return 0

        has_attr = hasattr(self, name)
        current_value = getattr(self, name, prop.default)
        if not has_attr:
            DBG_RUNTIME and logw("PME: value() defaulted missing prop", f"type={self.type}", f"prop={name}")

        items = getattr(prop, "items", None)
        if not items:
            return 0

        for item in items:
            if current_value == item[0]:
                return item[2]

        return 0


def register():
    context.add_global("U", UserData())
