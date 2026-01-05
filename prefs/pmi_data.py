# pyright: reportInvalidTypeForm=false
# prefs/pmi_data.py - メニューアイテム編集用データ
# LAYER = "prefs"
"""
PMIData PropertyGroup

メニューアイテムの編集状態を保持する
"""

from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from ..addon import get_prefs, temp_prefs
from ..core import constants as CC
from ..operators import extras as EOPS
from ..pme_types import PMIItem
from .. import keymap_helper
from .temp_data import update_data


class PMIData(PropertyGroup):
    """メニューアイテムの編集状態を保持する PropertyGroup

    pr.pmi_data で取得される。アイテムの mode, cmd, icon などの編集状態を管理。
    """

    _kmi = None
    errors = []
    infos = []

    @property
    def kmi(self):
        pr = get_prefs()
        if not PMIData._kmi:
            pr.kh.keymap()
            PMIData._kmi = pr.kh.operator(EOPS.PME_OT_none)
            PMIData._kmi.active = False

        return PMIData._kmi

    def check_pmi_errors(self, context):
        pr = get_prefs()
        pm = pr.selected_pm
        pm.ed.on_pmi_check(pm, self)

    def mode_update(self, context):
        tpr = temp_prefs()
        if get_prefs().selected_pm.mode == 'MODAL':
            if self.mode == 'COMMAND' and tpr.modal_item_prop_mode != 'KEY':
                tpr["modal_item_prop_mode"] = 0
                tpr.modal_item_hk.key = 'NONE'

        self.check_pmi_errors(context)

    mode: EnumProperty(
        items=CC.EMODE_ITEMS, description="Type of the item", update=mode_update
    )
    cmd: StringProperty(
        description="Python code", maxlen=CC.MAX_STR_LEN, update=update_data
    )
    cmd_ctx: EnumProperty(
        items=CC.OP_CTX_ITEMS, name="Execution Context", description="Execution context"
    )
    cmd_undo: BoolProperty(
        name="Undo Flag", description="'Undo' positional argument"
    )
    custom: StringProperty(
        description="Python code", maxlen=CC.MAX_STR_LEN, update=update_data
    )
    prop: StringProperty(description="Property", update=update_data)
    menu: StringProperty(description="Menu's name", update=update_data)
    expand_menu: BoolProperty(description="Expand Menu")
    use_cb: BoolProperty(
        name="Use Checkboxes instead of Toggle Buttons",
        description="Use checkboxes instead of toggle buttons",
    )
    use_frame: BoolProperty(name="Use Frame", description="Use frame")
    icon: StringProperty(description="Icon")
    name: StringProperty(description="Name")

    def sname_update(self, context):
        if not self.name:
            self.name = self.sname

    sname: StringProperty(description="Suggested name", update=sname_update)
    key: EnumProperty(
        items=keymap_helper.key_items, description="Key pressed", update=update_data
    )
    any: BoolProperty(description="Any key pressed", update=update_data)
    ctrl: BoolProperty(description="Ctrl key pressed", update=update_data)
    shift: BoolProperty(description="Shift key pressed", update=update_data)
    alt: BoolProperty(description="Alt key pressed", update=update_data)
    oskey: BoolProperty(
        description="Operating system key pressed", update=update_data
    )
    key_mod: EnumProperty(
        items=keymap_helper.key_items,
        description="Regular key pressed as a modifier",
        update=update_data,
    )

    def info(self, text=None, is_error=True):
        if text:
            if text not in self.errors:
                lst = self.errors if is_error else self.infos
                lst.append(text)
        else:
            self.errors.clear()
            self.infos.clear()

    def has_info(self):
        return self.errors or self.infos

    def has_errors(self, text=None):
        if not self.errors:
            return False
        if text:
            return text in self.errors
        return bool(self.errors)

    def extract_flags(self):
        return PMIItem.extract_flags(self)

    def parse_icon(self, default_icon='NONE'):
        return PMIItem.parse_icon(self, default_icon)
