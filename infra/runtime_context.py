# infra/runtime_context.py - PME Execution Context
# LAYER = "infra"
#
# This module contains the execution context for PME scripts.
# It manages the global namespace and provides eval/exec capabilities
# for user-defined scripts in PM/PMI items.
#
# This is the canonical location for PMEContext, UserData, and context.
# The api/ layer wraps these with higher-level functions.
#
# Phase 8-D: Issue #85

"""PME Execution Context.

This module provides the runtime execution environment for PME scripts.
External tools should use pme.execute() / pme.evaluate() instead of
accessing this directly.
"""

LAYER = "infra"

import bpy

from ..addon import get_prefs, temp_prefs, print_exc


class UserData:
    """User data container for scripts.

    Accessible as 'U' in the standard namespace.
    Allows users to store arbitrary data during a session.
    """

    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def update(self, **kwargs):
        self.__dict__.update(**kwargs)

    def __getattr__(self, name):
        return self.__dict__.get(name, None)


class PMEContext:
    """Execution context for PME scripts.

    Manages the global namespace and provides eval/exec capabilities
    for user-defined scripts in PM/PMI items.

    Note:
        This class is internal to PME. External tools should use:
        - pme.execute() for running code
        - pme.evaluate() for evaluating expressions
    """

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
        """Add a variable to the global namespace."""
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
        # Ensure "D" is set (may be missing after Reload Scripts)
        if "D" not in self._globals or self._globals["D"].__class__.__name__ == "_RestrictData":
            self._globals["D"] = bpy.data
        return self._globals

    def gen_globals(self, **kwargs):
        """Generate the globals dict for script execution."""
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
        """Evaluate an expression and return the result."""
        if globals is None:
            globals = self.gen_globals()

        value = None
        try:
            value = eval(expression, globals)
        except:
            print_exc(expression)

        return value

    def exe(self, data, globals=None, menu=None, slot=None, use_try=True):
        """Execute Python code.

        Returns True on success, False on error.
        """
        if globals is None:
            globals = self.gen_globals()

        if not use_try:
            exec(data, globals)
            return True

        try:
            exec(data, globals)
        except:
            print_exc(data)
            return False

        return True


# Singleton instance
context = PMEContext()


# =============================================================================
# Registration
# =============================================================================


def register():
    """Register the runtime context.

    Initializes the 'U' (UserData) global.
    """
    context.add_global("U", UserData())


def unregister():
    """Unregister the runtime context."""
    pass
