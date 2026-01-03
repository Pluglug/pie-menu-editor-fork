# core/props.py - Property schema management
# LAYER = "core"
#
# This module provides the property schema system for PME.
# It handles registration, parsing, and encoding of PM/PMI properties.
#
# Moved from: pme.py (Phase 4-A: Core Layer separation)
#
# Contains:
#   - PMEProp: Single property metadata
#   - PMEProps: Property registry and parser
#   - ParsedData: Parsed property container
#   - props: Global PMEProps instance
#
# Design note:
#   This module is in the core layer to ensure early loading.
#   Editors register properties here during module load, and
#   the execution layer (pme.py) uses these for runtime operations.

LAYER = "core"

# NOTE: This is a pragmatic layer violation (core → infra) for debug logging.
# infra/debug.py is pure Python and has no heavy dependencies.
# The alternative would be to lose valuable debug information.
try:
    from ..infra.debug import logw, DBG_RUNTIME
except ImportError:
    # Fallback for standalone testing or if debug module isn't available
    DBG_RUNTIME = False
    def logw(*args): pass


class PMEProp:
    """Single property metadata.

    Stores the definition of a PME property including:
    - type: The data type this property belongs to (pm, rm, pd, etc.)
    - name: Property name
    - default: Default value
    - ptype: Python type (STR, BOOL, INT)
    - items: Enum items (for EnumProperty)
    """

    def __init__(self, type, name, default, ptype='STR', items=None):
        self.name = name
        self.default = default
        self.items = items
        self.type = type
        self.ptype = ptype

    def decode_value(self, value):
        """Decode a string value to the appropriate Python type."""
        if self.ptype == 'STR':
            return value
        elif self.ptype == 'BOOL':
            return value == "True" or value == "1"
        elif self.ptype == 'INT':
            return int(value) if value else 0


class PMEProps:
    """Property schema registry and parser.

    This class manages all PME property definitions and provides
    methods to parse/encode the data string format used by PM/PMI.

    Data format: "type?key1=value1&key2=value2"
    Example: "pm?pm_radius=100&pm_flick=False"

    Note: prop_map is a class variable (shared across instances).
    This is intentional - there's only one global registry.
    """

    prop_map = {}

    def IntProperty(self, type, name, default=0):
        """Register an integer property."""
        self.prop_map[name] = PMEProp(type, name, default, 'INT')

    def BoolProperty(self, type, name, default=False):
        """Register a boolean property."""
        self.prop_map[name] = PMEProp(type, name, default, 'BOOL')

    def StringProperty(self, type, name, default=""):
        """Register a string property."""
        self.prop_map[name] = PMEProp(type, name, default, 'STR')

    def EnumProperty(self, type, name, default, items):
        """Register an enum property."""
        self.prop_map[name] = PMEProp(type, name, default, 'STR', items)

    def __init__(self):
        self.parsed_data = {}

    def get(self, name):
        """Get a property definition by name."""
        return self.prop_map.get(name, None)

    def parse(self, text):
        """Parse a data string into a ParsedData object.

        Results are cached. If the prop_map has grown since parsing,
        missing properties are added with their defaults.
        """
        if text not in self.parsed_data:
            self.parsed_data[text] = ParsedData(text)

        pd = self.parsed_data[text]
        for k, prop in self.prop_map.items():
            if prop.type == pd.type and not hasattr(pd, k):
                setattr(pd, k, prop.default)
                DBG_RUNTIME and logw("PME: defaulted missing prop", f"type={pd.type}", f"prop={k}")

        return pd

    def encode(self, text, prop, value):
        """Encode a property value into a data string.

        Only stores values that differ from defaults.
        """
        tp, _, data = text.partition("?")

        data = data.split("&")
        lst = []
        has_prop = False
        for pr in data:
            if not pr:
                continue

            k, v = pr.split("=")
            if k not in self.prop_map:
                continue

            if k == prop:
                v = value
                has_prop = True

            if v != self.get(k).default:
                lst.append("%s=%s" % (k, v))

        if not has_prop and value != self.prop_map[prop].default:
            lst.append("%s=%s" % (prop, value))

        lst.sort()

        text = "%s?%s" % (tp, "&".join(lst))
        return text

    def clear(self, text, *args):
        """Clear specified properties from a data string."""
        tp, _, data = text.partition("?")

        data = data.split("&")
        lst = []
        for pr in data:
            if not pr:
                continue

            k, v = pr.split("=")
            if k not in self.prop_map or k in args:
                continue

            if v != self.get(k).default:
                lst.append(pr)

        lst.sort()

        text = "%s?%s" % (tp, "&".join(lst))
        return text


# Global props instance - must be defined before ParsedData
props = PMEProps()


class ParsedData:
    """Container for parsed property data.

    Created from a data string like "pm?pm_radius=100".
    Properties are accessed as attributes (e.g., pd.pm_radius).

    Includes fallback defaults for Reload Scripts safety.
    """

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
            # use __dict__ to avoid triggering __getattr__ for other types
            if k not in self.__dict__:
                continue
            if getattr(self, k) != prop.default:
                self.is_empty = False
                break

        self._initialized = bool(props.prop_map)

    # Fallback defaults for known properties when prop_map is empty (Reload Scripts hotfix)
    # These MUST match the defaults registered in editors/*.py
    # See: grep -r "pme\.props\.(Enum|String|Int|Bool)Property" for all registrations
    _FALLBACK_DEFAULTS = {
        # editors/pie_menu.py (type: pm)
        'pm_radius': -1,
        'pm_confirm': -1,
        'pm_threshold': -1,
        'pm_flick': True,
        # editors/menu.py (type: rm)
        'rm_title': True,
        # editors/popup.py (type: row)
        'align': 'CENTER',
        'size': 'NORMAL',
        'vspacer': 'NORMAL',
        'fixed_col': False,
        'fixed_but': False,
        # editors/popup.py (type: spacer)
        'hsep': 'NONE',
        'subrow': 'NONE',
        # editors/popup.py (type: pd)
        'pd_title': True,
        'pd_box': True,
        'pd_expand': False,
        'pd_panel': 1,
        'pd_auto_close': False,
        'pd_width': 300,
        # editors/panel_group.py (type: pg)
        'pg_wicons': False,
        'pg_context': "ANY",
        'pg_category': "My Category",
        'pg_space': "VIEW_3D",
        'pg_region': "TOOLS",
        # ed_modal.py (type: mo)
        'confirm': False,
        'block_ui': True,
        'lock': True,
        # ed_stack_key.py (type: s)
        's_undo': False,
        's_state': False,
        # ed_sticky_key.py (type: sk)
        'sk_block_ui': False,
        # editors/property.py (type: prop)
        'vector': 1,
        'mulsel': False,
        'hor_exp': True,
        'exp': True,
        'save': True,
        # Legacy properties (may be used in old menu data)
        'layout': 'COLUMN',
        'width': 300,
        'poll': "",
        'column': 'ONE',
        'pd_row': 'TWO',
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
        """Get the index value for an enum property."""
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
