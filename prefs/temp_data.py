# pyright: reportInvalidTypeForm=false
# prefs/temp_data.py - セッションデータ（PMEData）
# LAYER = "prefs"
"""
PMEData PropertyGroup と関連する update 関数

temp_prefs() で取得される一時データを管理する。

責務分類:
- 派生キャッシュ: tags (pie_menus から算出), pie_menus (サブメニュー候補)
- UI 状態: links, links_idx, settings_tab, icons_tab
- セッション状態: modal_item_*, ed_props, prop_data

設計意図:
- PMEData は「編集セッション」のコンテナ
- tags と pie_menus はメニュー定義から派生するキャッシュ（init_tags(), update_pie_menus()）
- links は TreeState と連携してツリービューを構成

将来の拡張ポイント:
- modal_item_* 系フィールドが多い。ModalEditingState クラスへの分離で可読性向上
- update_pmi_data() の責務が広い。編集モード別の処理分離を検討
- tags/pie_menus の更新タイミングが散在。一元管理の余地あり

詳細: @_docs/design/prefs_data_analysis.md
"""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from ..addon import get_prefs, temp_prefs
from ..core import constants as CC
from ..infra.collections import BaseCollectionItem, sort_collection
from ..infra.modal import encode_modal_data
from ..infra.property import PropertyData
from ..pme_types import Tag, PMLink, EdProperties
from .. import keymap_helper
from .. import operator_utils
from .. import pme


def update_pmi_data(self, context, reset_prop_data=True):
    """PMI データの更新処理（コマンドエディタ、モーダルプロパティなど）"""
    pr = get_prefs()
    pm = pr.selected_pm
    pmi_data = pr.pmi_data
    pmi_data.check_pmi_errors(context)

    data_mode = pmi_data.mode
    if data_mode in CC.MODAL_CMD_MODES:
        data_mode = 'COMMAND'

    if data_mode == 'COMMAND' and pr.use_cmd_editor:
        op_idname, args, pos_args = operator_utils.find_operator(pmi_data.cmd)

        pmi_data.kmi.idname = ""
        pmi_data.cmd_ctx = 'INVOKE_DEFAULT'
        pmi_data.cmd_undo = True

        if not op_idname:
            return
        else:
            mod, _, op = op_idname.partition(".")
            mod = getattr(bpy.ops, mod, None)
            if not mod or not hasattr(mod, op):
                return

        pmi_data.kmi.idname = op_idname

        has_exec_ctx = False
        has_undo = False
        for i, arg in enumerate(pos_args):
            if i > 2:
                break
            try:
                value = eval(arg)
            except:
                continue
            try:
                if isinstance(value, str):
                    pmi_data.cmd_ctx = value
                    has_exec_ctx = True
                    continue
            except:
                pmi_data.cmd_ctx = 'INVOKE_DEFAULT'
                continue

            if isinstance(value, bool):
                has_undo = True
                pmi_data.cmd_undo = value

        if has_undo and not has_exec_ctx:
            pmi_data.cmd_ctx = 'EXEC_DEFAULT'

        keys = list(pmi_data.kmi.properties.keys())
        for k in keys:
            del pmi_data.kmi.properties[k]

        operator_utils.apply_properties(pmi_data.kmi.properties, args, pm, pmi_data)

    if pm.mode == 'MODAL':
        if data_mode == 'PROP':
            tpr = temp_prefs()
            tpr.prop_data.init(pmi_data.prop, pme.context.globals)
            if reset_prop_data:
                tpr.modal_item_prop_min = tpr.prop_data.min
                tpr.modal_item_prop_max = tpr.prop_data.max
                tpr.modal_item_prop_step = tpr.prop_data.step
                tpr.modal_item_prop_step_is_set = False


def update_data(self, context):
    """update_pmi_data の簡易ラッパー"""
    update_pmi_data(self, context, reset_prop_data=True)


class PMEData(PropertyGroup):
    """セッション/一時データを保持する PropertyGroup

    temp_prefs() で取得される。モーダル編集、タグ、リンクなどの状態を管理。

    フィールド分類:
    - 派生キャッシュ: tags, pie_menus (メニュー定義から算出)
    - UI 状態: links, links_idx, hidden_panels_idx, settings_tab, icons_tab
    - セッション状態: modal_item_*, ed_props, prop_data

    設計ノート:
    - update_lock はクラス変数（全インスタンス共有）で再帰防止
    - tags は Collection だが、init_tags() で毎回再構築される
    - links は PMLink (pme_types.py) の Collection で、tree.py と密結合
    """

    update_lock = False
    prop_data = PropertyData()

    ed_props: PointerProperty(type=EdProperties)

    def update_links_idx(self, context):
        if PMEData.update_lock:
            return
        PMEData.update_lock = True
        try:
            idx = self.links_idx
            if idx < 0 or idx >= len(self.links):
                return
            link = self.links[idx]
            if link.pm_name:
                pr = get_prefs()
                pr.active_pie_menu_idx = pr.pie_menus.find(link.pm_name)
        finally:
            PMEData.update_lock = False

    def update_modal_item_hk(self, context):
        pmi_data = get_prefs().pmi_data
        encode_modal_data(pmi_data)
        pmi_data.check_pmi_errors(context)

        if PMEData.update_lock:
            return
        PMEData.update_lock = True

        tpr = temp_prefs()
        if pmi_data.mode == 'PROP':
            if tpr.modal_item_hk.key == 'WHEELUPMOUSE':
                tpr.modal_item_prop_mode = 'WHEEL'
            elif tpr.modal_item_hk.key == 'WHEELDOWNMOUSE':
                tpr.modal_item_prop_mode = 'WHEEL'
                tpr.modal_item_hk.key = 'WHEELUPMOUSE'

        PMEData.update_lock = False

    def update_modal_item_prop_mode(self, context):
        if PMEData.update_lock:
            return
        PMEData.update_lock = True

        if self.modal_item_prop_mode == 'KEY':
            self.modal_item_hk.key = 'NONE'
        elif self.modal_item_prop_mode == 'MOVE':
            self.modal_item_hk.key = 'MOUSEMOVE'
        elif self.modal_item_prop_mode == 'WHEEL':
            self.modal_item_hk.key = 'WHEELUPMOUSE'

        PMEData.update_lock = False

    tags: CollectionProperty(type=Tag)
    links: CollectionProperty(type=PMLink)
    links_idx: IntProperty(default=0, update=update_links_idx)
    hidden_panels_idx: IntProperty()
    pie_menus: CollectionProperty(type=BaseCollectionItem)
    modal_item_hk: PointerProperty(type=keymap_helper.Hotkey)
    modal_item_prop_mode: EnumProperty(
        items=(
            (
                'KEY',
                "Hotkey",
                (
                    "Command tab: Press the hotkey\n"
                    "Property tab: Press and hold the hotkey and move the mouse "
                    "to change the value"
                ),
            ),
            ('MOVE', "Move Mouse", "Move mouse to change the value"),
            ('WHEEL', "Mouse Wheel", "Scroll mouse wheel to change the value"),
        ),
        update=update_modal_item_prop_mode,
    )
    modal_item_prop_min: FloatProperty(name="Min Value", step=100)
    modal_item_prop_max: FloatProperty(name="Max Value", step=100)

    def update_modal_item_prop_step(self, context):
        self.modal_item_prop_step_is_set = True

    modal_item_prop_step: FloatProperty(
        name="Step",
        min=0,
        step=100,
        update=update_modal_item_prop_step,
    )
    modal_item_prop_step_is_set: BoolProperty()

    def modal_item_custom_update(self, context):
        update_pmi_data(self, context, reset_prop_data=False)

    modal_item_custom: StringProperty(
        description="Custom value to display", update=modal_item_custom_update
    )

    def modal_item_show_get(self):
        return self.modal_item_custom != 'HIDDEN'

    def modal_item_show_set(self, value):
        self.modal_item_custom = "" if value else 'HIDDEN'

    modal_item_show: BoolProperty(
        description="Show the hotkey", get=modal_item_show_get, set=modal_item_show_set
    )

    settings_tab: EnumProperty(
        items=CC.SETTINGS_TAB_ITEMS,
        name="Settings",
        description="Settings",
        default=CC.SETTINGS_TAB_DEFAULT,
    )
    icons_tab: EnumProperty(
        name="Icons",
        description="Icons",
        items=(
            ('BLENDER', "Blender", ""),
            ('CUSTOM', "Custom", ""),
        ),
    )

    def init_tags(self):
        pr = get_prefs()
        tpr = temp_prefs()
        self.tags.clear()
        for pm in pr.pie_menus:
            tags = pm.get_tags()
            if not tags:
                continue
            for t in tags:
                if t in self.tags:
                    continue
                tag = self.tags.add()
                tag.name = t
        sort_collection(tpr.tags, lambda t: t.name)
        Tag.filter()

    def update_pie_menus(self):
        pr = get_prefs()
        spm = pr.selected_pm
        supported_sub_menus = spm.ed.supported_sub_menus
        pms = set()

        for pm in pr.pie_menus:
            if pm.name == spm.name:
                continue
            if pm.mode in supported_sub_menus:
                pms.add(pm.name)

        self.pie_menus.clear()
        for pm in sorted(pms):
            item = self.pie_menus.add()
            item.name = pm
