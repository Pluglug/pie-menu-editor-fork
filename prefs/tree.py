# pyright: reportInvalidTypeForm=false
# prefs/tree.py - Tree システム
# LAYER = "prefs"
"""
Tree View システム - ツリービューの UI 状態管理

コンポーネント:
- TreeState: UI 状態シングルトン（展開/折りたたみ）
- PME_UL_pm_tree: ツリー UIList
- TreeView: ツリー操作ファサード (pr.tree)
- Tree オペレーター群

設計意図:
- TreeState は UIList のライフサイクルから独立して状態を保持
- groups は pr.pie_menus と pr.group_by から動的に算出される派生データ
- collapsed_groups / expanded_folders は tree.json に永続化される UI 設定

将来の拡張ポイント:
- update_tree() のグループ化ロジックは複雑。将来的に GroupingStrategy パターンで分離可能
- PMLink (pme_types.py) との結合が強い。TreeNode 抽象化の余地あり
- filter_items() の条件分岐が多い。フィルタリングロジックの分離を検討

詳細: @_docs/design/prefs_data_analysis.md
"""

import os
import json

from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import Operator, UIList

from ..addon import ADDON_PATH, get_prefs, temp_prefs, ic
from ..core import constants as CC
from ..infra.debug import DBG_TREE, logh, logi
from ..infra import utils as U
from ..keymap_helper import to_key_name, to_ui_hotkey
from ..pme_types import PMLink
from ..ui import tag_redraw
from ..ui.layout import lh


class TreeState:
    """PME_UL_pm_tree の状態管理を担当

    ツリーの展開/折りたたみ状態、グループ情報を一元管理する。
    UIList のライフサイクルから独立して状態を保持。

    フィールド:
    - locked: 更新中フラグ（バッチ操作時の再帰防止）
    - groups: 現在の group_by から算出されたグループ名リスト（派生）
    - collapsed_groups: 折りたたまれたグループ名 (UI 状態, tree.json)
    - expanded_folders: 展開されたフォルダパス (UI 状態, tree.json)
    - has_folders: フォルダが存在するか（派生）

    設計ノート:
    - groups はメニュー定義ではなく「現在のビューのグループ化結果」
    - P1-P8 で PME_UL_pm_tree のクラス変数から分離済み
    - シングルトンパターン: tree_state インスタンスをモジュールレベルで保持
    """

    def __init__(self):
        self.locked = False
        self.groups = []
        self.collapsed_groups = set()
        self.expanded_folders = set()
        self.has_folders = False

    def reset(self):
        """状態をリセット"""
        self.locked = False
        self.groups.clear()
        self.collapsed_groups.clear()
        self.expanded_folders.clear()
        self.has_folders = False

    def save(self):
        """ツリー状態をファイルに保存"""
        pr = get_prefs()
        if not pr.tree_mode or not pr.save_tree:
            return

        data = dict(
            group_by=pr.group_by,
            groups=[v for v in self.collapsed_groups],
            folders=[v for v in self.expanded_folders],
        )
        path = os.path.join(ADDON_PATH, "data", "tree.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb+") as f:
            f.write(
                json.dumps(
                    data, indent=2, separators=(", ", ": "), ensure_ascii=False
                ).encode("utf8")
            )

    def load(self):
        """ツリー状態をファイルから読み込み"""
        pr = get_prefs()
        if not pr.tree_mode or not pr.save_tree:
            return

        path = os.path.join(ADDON_PATH, "data", "tree.json")
        if not os.path.isfile(path):
            return

        with open(path, "rb") as f:
            data = f.read()
            try:
                data = json.loads(data)
            except:
                return

            if "group_by" in data:
                item = pr.bl_rna.properties["group_by"].enum_items.get(
                    data["group_by"], None
                )
                if item:
                    pr.group_by = item.identifier
                    pr.tree.update()

            existing_groups = set(self.groups)
            groups = data.get("groups", None)
            if groups and isinstance(groups, list):
                self.collapsed_groups.clear()
                for v in groups:
                    v = v.strip()
                    if v and v in existing_groups:
                        self.collapsed_groups.add(v)

            folders = data.get("folders", None)
            if folders and isinstance(folders, list):
                self.expanded_folders.clear()
                for v in folders:
                    v = v.strip()
                    if v:
                        elems = v.split(CC.TREE_SPLITTER)
                        for i, e in enumerate(elems):
                            if i == 0:
                                if e not in existing_groups:
                                    break
                            elif e not in pr.pie_menus:
                                break
                        else:
                            self.expanded_folders.add(v)


# モジュールレベルのシングルトンインスタンス
tree_state = TreeState()


class PME_UL_pm_tree(UIList):
    """Pie Menu ツリー表示

    グループ化、フォルダ展開、永続化をサポートする UIList。
    状態は TreeState インスタンス (tree_state) で管理。

    注: クラス変数（locked, groups, collapsed_groups, expanded_folders, has_folders）
    は tree_state に移動した。呼び出し側は tree_state.xxx を直接使用すること。
    """

    @staticmethod
    def save_state():
        tree_state.save()

    @staticmethod
    def load_state():
        tree_state.load()

    @staticmethod
    def link_is_collapsed(link):
        path = link.path
        p = link.group
        for i in range(0, len(path)):
            if p:
                p += CC.TREE_SPLITTER
            p += path[i]
            if p not in tree_state.expanded_folders:
                return True
        return False

    @staticmethod
    def update_tree():
        if tree_state.locked:
            return

        pr = get_prefs()

        if not pr.tree_mode:
            return

        tpr = temp_prefs()

        DBG_TREE and logh("Update Tree")
        num_links = len(tpr.links)
        sel_link, sel_folder = None, None
        sel_link = 0 <= tpr.links_idx < num_links and tpr.links[tpr.links_idx]
        if not sel_link or not sel_link.pm_name or sel_link.pm_name not in pr.pie_menus:
            sel_link = None
        sel_folder = sel_link and sel_link.path and sel_link.path[-1]

        tpr.links.clear()
        PMLink.clear()

        folders = {}
        groups = {}
        files = set()

        pms = [pm for pm in pr.pie_menus if not pr.use_filter or pm.filter_list(pr)]
        if pr.group_by == 'TAG':
            groups[CC.UNTAGGED] = []
            for t in tpr.tags:
                groups[t.name] = []
            pms.sort(key=lambda pm: pm.tag)
        elif pr.group_by == 'KEYMAP':
            pms.sort(key=lambda pm: pm.km_name)
        elif pr.group_by == 'TYPE':
            pms.sort(key=lambda pm: pm.ed.default_name if pm.ed else "")
        elif pr.group_by == 'KEY':
            pms.sort(key=lambda pm: to_key_name(pm.key))
        else:
            groups[CC.TREE_ROOT] = True
            pms.sort(key=lambda pm: pm.name)

        for pm in pms:
            if pr.group_by == 'TAG':
                if pm.tag:
                    tags = [s.strip() for s in pm.tag.split(",") if s.strip()]
                    for t in tags:
                        if t not in groups:
                            groups[t] = []
                        groups[t].append(pm)
                else:
                    groups[CC.UNTAGGED].append(pm)
            elif pr.group_by == 'KEYMAP':
                kms = [s.strip() for s in pm.km_name.split(CC.KEYMAP_SPLITTER) if s.strip()]
                for km in kms:
                    if km not in groups:
                        groups[km] = []
                    groups[km].append(pm)
            elif pr.group_by == 'TYPE':
                type_name = pm.ed.default_name if pm.ed else ""
                if type_name not in groups:
                    groups[type_name] = []
                groups[type_name].append(pm)
            elif pr.group_by == 'KEY':
                key_name = to_key_name(pm.key)
                if key_name not in groups:
                    groups[key_name] = []
                groups[key_name].append(pm)

            for pmi in pm.pmis:
                if pmi.mode == 'MENU':
                    name, *_ = U.extract_str_flags(pmi.text, CC.F_EXPAND, CC.F_EXPAND)
                    if (
                        name not in pr.pie_menus
                        or (pr.use_filter and not pr.pie_menus[name].filter_list(pr))
                    ):
                        continue

                    if pm.name not in folders:
                        folders[pm.name] = []

                    if name not in folders[pm.name]:
                        folders[pm.name].append(name)
                        files.add(name)

        tree_state.has_folders = len(folders) > 0

        if pr.use_groups:
            for kpms in groups.values():
                kpms.sort(key=lambda pm: pm.name)

        def add_children(files, group, path, idx, aidx):
            DBG_TREE and logi(" " * len(path) + "/".join(path))
            for file in files:
                if file in path:
                    continue
                link = PMLink.add()
                link.group = group
                link.pm_name = file
                link.folder = pm.name
                link.path.extend(path)
                if file == apm_name and (not sel_link or sel_folder == pm.name):
                    aidx = idx
                idx += 1

                if file in folders:
                    link.is_folder = True
                    path.append(file)
                    new_idx, aidx = add_children(folders[file], group, path, idx, aidx)
                    if new_idx == idx:
                        link.is_folder = False
                    idx = new_idx
                    path.pop()

            return idx, aidx

        idx = 0
        aidx = -1
        apm = pr.selected_pm
        apm_name = apm.name if apm else None

        groups_to_remove = []
        for k, v in groups.items():
            if not v or (pr.group_by == 'TAG' and pr.tag_filter and k != pr.tag_filter):
                groups_to_remove.append(k)

        for g in groups_to_remove:
            groups.pop(g)

        group_names = sorted(groups.keys())

        if (
            pr.group_by == 'TAG'
            and group_names
            and group_names[-1] != CC.UNTAGGED
            and CC.UNTAGGED in group_names
        ):
            group_names.remove(CC.UNTAGGED)
            group_names.append(CC.UNTAGGED)
        elif (
            pr.group_by == 'KEY'
            and group_names
            and group_names[-1] != "None"
            and "None" in group_names
        ):
            group_names.remove("None")
            group_names.append("None")

        tree_state.groups.clear()
        tree_state.groups.extend(group_names)

        for g in group_names:
            if pr.use_groups:
                link = PMLink.add()
                link.label = g
                idx += 1

                pms = groups[g]

            path = []
            for pm in pms:
                if pm.name in folders:
                    link = PMLink.add()
                    link.group = g
                    link.is_folder = True
                    link.pm_name = pm.name
                    if pm.name == apm_name and (not sel_link or not sel_folder):
                        aidx = idx
                    idx += 1
                    path.append(pm.name)
                    idx, aidx = add_children(folders[pm.name], g, path, idx, aidx)
                    path.pop()

                else:
                    link = PMLink.add()
                    link.group = g
                    link.pm_name = pm.name
                    if pm.name == apm_name and (not sel_link or not sel_folder):
                        aidx = idx
                    idx += 1

            pm_links = {}
            for link in tpr.links:
                if link.label:
                    continue
                if link.pm_name not in pm_links:
                    pm_links[link.pm_name] = []
                pm_links[link.pm_name].append(link)

            if pr.group_by == 'NONE':
                links_to_remove = set()
                fixed_links = set()
                for pm_name, links in pm_links.items():
                    if len(links) == 1:
                        continue
                    links.sort(key=lambda link: len(link.path), reverse=True)
                    can_be_removed = False
                    for link in links:
                        if len(link.path) == 0:
                            if can_be_removed and link.pm_name not in fixed_links:
                                links_to_remove.add(link.name)
                                DBG_TREE and logi("REMOVE", link.pm_name)
                        else:
                            if (
                                not can_be_removed
                                and link.name not in links_to_remove
                                and link.path[0] != pm_name
                            ):
                                fixed_links.add(link.path[0])
                                DBG_TREE and logi("FIXED", link.path[0])
                                can_be_removed = True

                prev_link_will_be_removed = False
                for link in tpr.links:
                    if link.label:
                        prev_link_will_be_removed = False
                        continue
                    if link.path:
                        if prev_link_will_be_removed:
                            links_to_remove.add(link.name)
                    else:
                        prev_link_will_be_removed = link.name in links_to_remove

                for link in links_to_remove:
                    tree_state.expanded_folders.discard(tpr.links[link].fullpath())
                    tpr.links.remove(tpr.links.find(link))

            aidx = -1
            for i, link in enumerate(tpr.links):
                if link.pm_name == apm_name:
                    aidx = i
                    break

            tpr.links_idx = aidx
            if 0 <= aidx < len(tpr.links):
                sel_link = tpr.links[aidx]
                if sel_link.pm_name:
                    pm = pr.selected_pm
                    if pm and pr.group_by == 'KEYMAP' and pm.km_name in tree_state.collapsed_groups:
                        tree_state.collapsed_groups.remove(pm.km_name)
            else:
                tpr.links_idx = -1

            tag_redraw()

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        pr = get_prefs()
        layout = layout.row(align=True)
        lh.lt(layout)

        if item.pm_name:
            pm = pr.pie_menus[item.pm_name]

            num_cols = (
                pr.show_names + pr.show_hotkeys + pr.show_keymap_names + pr.show_tags
            )

            use_split = num_cols > 2
            if use_split:
                layout = lh.split(factor=0.5 if pr.show_names else 0.4)
                lh.row()

            lh.prop(
                pm,
                "enabled",
                "",
                CC.ICON_ON if pm.enabled else CC.ICON_OFF,
                emboss=False,
            )

            for i in range(0, len(item.path)):
                lh.label("", icon=ic('BLANK1'))

            lh.label("", pm.ed.icon)

            if item.is_folder:
                icon = (
                    'TRIA_DOWN'
                    if item.fullpath() in tree_state.expanded_folders
                    else 'TRIA_RIGHT'
                )
                lh.operator(
                    PME_OT_tree_folder_toggle.bl_idname,
                    "",
                    icon,
                    emboss=False,
                    folder=item.fullpath(),
                    idx=index,
                )

            col = 0

            hk = to_ui_hotkey(pm)
            show_hotkeys = pr.show_hotkeys
            if pr.show_names:
                lh.prop(pm, "label", "", emboss=False)
                col += 1
            elif show_hotkeys:
                if hk:
                    lh.label(hk)
                else:
                    lh.prop(pm, "label", "", emboss=False)
                show_hotkeys = False
                col += 1

            if use_split:
                lh.lt(layout)

            if pr.show_tags:
                if col == num_cols - 1:
                    lh.row(layout, alignment='RIGHT')
                elif use_split:
                    lh.row(layout)
                tag = pm.tag
                if tag:
                    tag, _, rest = pm.tag.partition(",")
                    if rest:
                        tag += ",.."
                lh.label(tag)
                col += 1

            if pr.show_keymap_names:
                if col == num_cols - 1:
                    lh.row(layout, alignment='RIGHT')
                elif use_split:
                    lh.row(layout)
                names = [s.strip() for s in pm.km_name.split(CC.KEYMAP_SPLITTER) if s.strip()]
                km_name = names[0] if names else ""
                if len(names) > 1:
                    km_name += f" +{len(names) - 1}"
                lh.label(km_name)
                col += 1

            if show_hotkeys:
                if num_cols > 1:
                    lh.row(layout, alignment='RIGHT')

                lh.label(hk)

        else:
            lh.row()
            lh.layout.scale_y = 0.95
            icon = (
                'TRIA_RIGHT_BAR'
                if item.label in tree_state.collapsed_groups
                else 'TRIA_DOWN_BAR'
            )
            lh.operator(
                PME_OT_tree_group_toggle.bl_idname,
                item.label,
                icon,
                group=item.label,
                idx=index,
                all=False,
            )
            icon = (
                'TRIA_LEFT_BAR'
                if item.label in tree_state.collapsed_groups
                else 'TRIA_DOWN_BAR'
            )
            lh.operator(
                PME_OT_tree_group_toggle.bl_idname,
                "",
                icon,
                group=item.label,
                idx=index,
                all=True,
            )

    def draw_filter(self, context, layout):
        pr = get_prefs()

        col = layout.column(align=True)
        col.prop(pr, "list_size")
        col.prop(pr, "num_list_rows")

    def filter_items(self, context, data, propname):
        pr = get_prefs()

        links = getattr(data, propname)
        filtered = [self.bitflag_filter_item] * len(links)

        cur_group = None
        for idx, link in enumerate(links):
            pm = None
            if link.path:
                pm = pr.pie_menus[link.path[0]]
            elif link.pm_name:
                pm = pr.pie_menus[link.pm_name]

            if link.label and pr.use_groups:
                cur_group = link.label

            if not pm:
                continue

            if cur_group in tree_state.collapsed_groups:
                if pr.group_by == 'TAG':
                    if pm.has_tag(cur_group):
                        filtered[idx] = 0
                elif pr.group_by == 'KEYMAP' and cur_group in pm.km_name:
                    filtered[idx] = 0
                elif pr.group_by == 'TYPE' and cur_group == pm.ed.default_name:
                    filtered[idx] = 0
                elif pr.group_by == 'KEY' and cur_group == to_key_name(pm.key):
                    filtered[idx] = 0
            elif pr.tree_mode:
                if link.path and PME_UL_pm_tree.link_is_collapsed(link):
                    filtered[idx] = 0

        return filtered, []


class PME_OT_tree_folder_toggle(Operator):
    bl_idname = "pme.tree_folder_toggle"
    bl_label = ""
    bl_description = "Expand or collapse"
    bl_options = {'INTERNAL'}

    folder: StringProperty()
    idx: IntProperty()

    def execute(self, context):
        temp_prefs().links_idx = self.idx
        if self.folder:
            if self.folder in tree_state.expanded_folders:
                tree_state.expanded_folders.remove(self.folder)
            else:
                tree_state.expanded_folders.add(self.folder)

        PME_UL_pm_tree.save_state()
        return {'FINISHED'}


class PME_OT_tree_folder_toggle_all(Operator):
    bl_idname = "pme.tree_folder_toggle_all"
    bl_label = ""
    bl_description = "Expand or collapse all items"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if tree_state.expanded_folders:
            tree_state.expanded_folders.clear()
        else:
            for link in temp_prefs().links:
                if link.is_folder:
                    tree_state.expanded_folders.add(link.fullpath())

        PME_UL_pm_tree.save_state()
        return {'FINISHED'}


class PME_OT_tree_group_toggle(Operator):
    bl_idname = "pme.tree_group_toggle"
    bl_label = ""
    bl_description = "Expand or collapse groups"
    bl_options = {'INTERNAL'}

    group: StringProperty(options={'SKIP_SAVE'})
    idx: IntProperty(options={'SKIP_SAVE'})
    all: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        tpr = temp_prefs()

        if self.idx != -1:
            tpr.links_idx = self.idx

        if self.all:
            add = len(tree_state.collapsed_groups) != len(tree_state.groups)
            if self.group:
                add = True

            for group in tree_state.groups:
                if add:
                    tree_state.collapsed_groups.add(group)
                else:
                    tree_state.collapsed_groups.discard(group)

            if self.group and self.group in tree_state.collapsed_groups:
                tree_state.collapsed_groups.remove(self.group)

        else:
            if self.group in tree_state.collapsed_groups:
                tree_state.collapsed_groups.remove(self.group)
            else:
                tree_state.collapsed_groups.add(self.group)

        PME_UL_pm_tree.save_state()
        return {'FINISHED'}


class TreeView:
    """PME_UL_pm_tree の操作ファサード

    PMEPreferences.tree として使用される。
    """

    def expand_km(self, name):
        if name in tree_state.collapsed_groups:
            tree_state.collapsed_groups.remove(name)

    def lock(self):
        tree_state.locked = True

    def unlock(self):
        tree_state.locked = False

    def update(self):
        PME_UL_pm_tree.update_tree()
