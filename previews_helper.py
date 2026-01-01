import bpy
import bpy.utils.previews
import os
from . import pme
from .infra.debug import logw


class PreviewsHelper:

    def __init__(self, folder="icons"):
        self.path = os.path.join(os.path.dirname(__file__), folder)
        self.preview = None

    def get_icon(self, name):
        if self.preview is None or name not in self.preview:
            return 0
        return self.preview[name].icon_id

    def get_icon_name_by_id(self, id):
        if self.preview is None:
            return None
        name = None
        min_id = 99999999
        for k, i in self.preview.items():
            if i.icon_id == id:
                return k
            if min_id > i.icon_id:
                min_id = i.icon_id
                name = k

        return name

    def get_names(self):
        if self.preview is None:
            return []
        return self.preview.keys()

    def has_icon(self, name):
        return self.preview is not None and name in self.preview

    def refresh(self):
        # NOTE:
        # - This currently initializes previews only once per session.
        # - Enum-based icons (e.g. OPEN_MODE_ITEMS in constants.py) cache their
        #   icon_value at class definition time, so calling this again will NOT
        #   update those enums. A true "icon refresh" would require either
        #   re-registering the affected classes or switching to a dynamic
        #   draw-time lookup instead of static enum icon_values.
        if self.preview is not None:
            return

        try:
            self.preview = bpy.utils.previews.new()
            for f in os.listdir(self.path):
                if not f.endswith(".png"):
                    continue

                self.preview.load(
                    os.path.splitext(f)[0], os.path.join(self.path, f), 'IMAGE'
                )
        except Exception as e:
            # Hotfix: Reload Scripts may leave previews in unstable state
            logw("PME: previews refresh failed (icons may not display)", str(e))
            self.preview = None

    def unregister(self):
        if not self.preview:
            return
        try:
            bpy.utils.previews.remove(self.preview)
        except Exception as e:
            # Hotfix: Reload Scripts may leave previews in unstable state
            logw("PME: previews unregister failed", str(e))
        self.preview = None


def custom_icon(icon):
    return ph.get_icon(icon)


# HOTFIX (Phase 2-B): Reload Scripts のサイクルで unregister() を呼ぶと
# bpy.utils.previews の内部状態が壊れて警告がスパムする問題を回避。
# Reload 後に古い ph インスタンスが残っていても、新しい ph.refresh() が
# 「既に self.preview がある」とみなして再初期化しない（line 49 の early return）。
# アイコンは一度目のロードで登録され、Reload しても維持される。
# Phase 3 でライフサイクルを正しく再設計する予定。
#
# if "ph" in globals():
#     ph.unregister()

ph = PreviewsHelper()
ph.refresh()


def register():
    pme.context.add_global("custom_icon", custom_icon)
