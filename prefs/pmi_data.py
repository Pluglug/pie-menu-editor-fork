# pyright: reportInvalidTypeForm=false
# prefs/pmi_data.py - メニューアイテム編集用データ
# LAYER = "prefs"
"""
PMIData PropertyGroup - メニューアイテムの編集バッファ

選択中のメニューアイテムを編集するための「フォーム」データ。
View Model / Edit Buffer パターンを使用:

    [PMIItem]  ────load────>  [PMIData]  ────save────>  [PMIItem]
    (永続定義)               (編集バッファ)            (永続定義)

ユーザーが PMI を選択すると、その値が PMIData にロードされ、
UI で編集後、保存時に PMIItem に書き戻される。

設計意図:
- PMIData は「編集中の一時状態」を保持するビューモデル
- 永続定義 (PMIItem) と分離することで、編集のキャンセルが可能
- エラー/インフォはクラス変数で全インスタンス共有（単一編集を前提）

将来の拡張ポイント:
- mode 別の編集フィールドが混在。ModeSpecificFields への分離で可読性向上
- check_pmi_errors() は pm.ed.on_pmi_check() に委譲。バリデーション戦略の統一を検討
- _kmi はオペレーター引数編集用の特殊ケース。より明示的な分離が望ましい

詳細: @_docs/design/prefs_data_analysis.md
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

    フィールド分類:
    - 編集バッファ: mode, cmd, custom, prop, menu, icon, name, sname,
                    key, ctrl, shift, alt, oskey, key_mod, any,
                    expand_menu, use_cb, use_frame, cmd_ctx, cmd_undo
    - エフェメラル: errors, infos (バリデーション結果)
    - ランタイム: _kmi (オペレーター引数編集用)

    設計ノート:
    - _kmi は KeymapHelper 経由で生成される一時的な KeyMapItem
    - errors/infos はクラス変数（複数インスタンス間で共有）
    - update_data() は temp_data.py の update_pmi_data() を呼び出す
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

    # Phase 9-X (#102): description field for COMMAND mode fallback tooltip
    description: StringProperty(
        name="Description",
        description="Tooltip text for this item (COMMAND mode only)",
        maxlen=CC.MAX_STR_LEN,
    )

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
