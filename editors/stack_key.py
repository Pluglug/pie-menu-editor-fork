# pyright: reportInvalidTypeForm=false
# editors/stack_key.py - Stack Key editor
# LAYER = "editors"
#
# Moved from: ed_stack_key.py (PME2 layer separation)

LAYER = "editors"

import bpy
from bpy.props import BoolProperty
from ..core.schema import schema
from .base import EditorBase

schema.BoolProperty("s", "s_undo")
schema.BoolProperty("s", "s_state")
# schema.BoolProperty("s", "s_scroll", True)


class Editor(EditorBase):

    def __init__(self):
        self.id = 'SCRIPT'
        EditorBase.__init__(self)

        self.docs = "#Stack_Key_Editor"
        self.use_slot_icon = False
        self.use_preview = False
        self.default_pmi_data = "s?"
        self.supported_slot_modes = {'COMMAND', 'HOTKEY'}

    def register_props(self, pm):
        self.register_pm_prop(
            "ed_undo",
            BoolProperty(
                name="Undo Previous Command",
                description="Undo previous command",
                get=lambda s: s.get_data("s_undo"),
                set=lambda s, v: s.set_data("s_undo", v),
            ),
        )
        self.register_pm_prop(
            "ed_state",
            BoolProperty(
                name="Remember State",
                description="Remember state",
                get=lambda s: s.get_data("s_state"),
                set=lambda s, v: s.set_data("s_state", v),
            ),
        )

    def init_pm(self, pm):
        if not pm.data.startswith("s?"):
            pm.data = self.default_pmi_data
            pmi = pm.pmis.add()
            pmi.text = pm.data
            pmi.mode = 'COMMAND'
            pmi.name = "Command 1"

    def on_pm_add(self, pm):
        pmi = pm.pmis.add()
        pmi.mode = 'COMMAND'
        pmi.name = "Command 1"

    def draw_extra_settings(self, layout, pm):
        EditorBase.draw_extra_settings(self, layout, pm)
        layout.prop(pm, "ed_undo")
        layout.prop(pm, "ed_state")


def register():
    Editor()
