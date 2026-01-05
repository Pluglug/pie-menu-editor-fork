# prefs/ - アドオン設定（PMEPreferences, 設定UI）
# LAYER = "prefs"
"""
PMEPreferences 関連のモジュール群

P1: helpers.py - PMIClipboard, PieMenuPrefs, PieMenuRadius
P2: temp_data.py - PMEData, update_pmi_data, update_data
P3: pmi_data.py - PMIData
P4: lists.py - WM_UL_panel_list, WM_UL_pm_list
P5: pm_ops.py - PM 操作オペレーター
P6: tree.py - TreeState, PME_UL_pm_tree, TreeView, tree_ops
"""

from .helpers import PMIClipboard, PieMenuPrefs, PieMenuRadius
from .temp_data import PMEData, update_pmi_data, update_data
from .pmi_data import PMIData
from .lists import WM_UL_panel_list, WM_UL_pm_list
from .pm_ops import (
    WM_OT_pm_duplicate,
    PME_OT_pm_remove,
    PME_OT_pm_enable_all,
    PME_OT_pm_enable_by_tag,
    PME_OT_pm_remove_by_tag,
    WM_OT_pm_move,
    WM_OT_pm_sort,
)
from .tree import (
    tree_state,
    TreeState,
    PME_UL_pm_tree,
    TreeView,
    PME_OT_tree_folder_toggle,
    PME_OT_tree_folder_toggle_all,
    PME_OT_tree_group_toggle,
)

__all__ = [
    # P1
    "PMIClipboard",
    "PieMenuPrefs",
    "PieMenuRadius",
    # P2
    "PMEData",
    "update_pmi_data",
    "update_data",
    # P3
    "PMIData",
    # P4
    "WM_UL_panel_list",
    "WM_UL_pm_list",
    # P5
    "WM_OT_pm_duplicate",
    "PME_OT_pm_remove",
    "PME_OT_pm_enable_all",
    "PME_OT_pm_enable_by_tag",
    "PME_OT_pm_remove_by_tag",
    "WM_OT_pm_move",
    "WM_OT_pm_sort",
    # P6
    "tree_state",
    "TreeState",
    "PME_UL_pm_tree",
    "TreeView",
    "PME_OT_tree_folder_toggle",
    "PME_OT_tree_folder_toggle_all",
    "PME_OT_tree_group_toggle",
]
