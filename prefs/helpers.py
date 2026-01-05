# prefs/helpers.py - ヘルパークラス
# LAYER = "prefs"
"""
PMIClipboard, PieMenuPrefs, PieMenuRadius
preferences.py から分離された純粋なヘルパークラス群
"""

from ..addon import get_uprefs
from ..infra.debug import DBG_PM, logi


class PMIClipboard:
    """メニューアイテムのコピー＆ペースト用クリップボード"""

    def __init__(self):
        self.clear()

    def copy(self, pm, pmi):
        self.pm_mode = pm.mode
        self.mode = pmi.mode
        self.icon = pmi.icon
        self.text = pmi.text
        self.name = pmi.name

    def paste(self, pm, pmi):
        pmi.name = self.name
        pmi.icon = self.icon
        pmi.mode = self.mode
        pmi.text = self.text

    def clear(self):
        self.pm_mode = None
        self.mode = None
        self.icon = None
        self.text = None
        self.name = None

    def has_data(self):
        return self.mode is not None


class PieMenuPrefs:
    """パイメニューの設定（confirm, threshold）の保存・復元"""

    def __init__(self):
        self.num_saves = 0
        self.lock = False
        self.confirm = 0
        self.threshold = 12
        self.animation_timeout = 0

    def save(self):
        self.num_saves += 1
        DBG_PM and logi("SAVE PM Prefs", self.num_saves, self.lock)
        if not self.lock:
            v = get_uprefs().view
            self.confirm = v.pie_menu_confirm
            self.threshold = v.pie_menu_threshold
            self.lock = True

    def restore(self):
        self.num_saves -= 1
        DBG_PM and logi("RESTORE", self.num_saves)
        if self.lock and self.num_saves == 0:
            v = get_uprefs().view
            v.pie_menu_confirm = self.confirm
            v.pie_menu_threshold = self.threshold
            self.lock = False


class PieMenuRadius:
    """パイメニューの radius と animation_timeout の保存・復元"""

    def __init__(self):
        self.radius = -1
        self.num_saves = 0

    @property
    def is_saved(self):
        return self.radius != -1

    def save(self):
        self.num_saves += 1
        if self.radius != -1:
            return

        v = get_uprefs().view
        self.animation_timeout = v.pie_animation_timeout
        self.radius = v.pie_menu_radius

    def restore(self):
        self.num_saves -= 1
        if self.num_saves == 0:
            v = get_uprefs().view
            v.pie_menu_radius = self.radius
            v.pie_animation_timeout = self.animation_timeout
            self.radius = -1
