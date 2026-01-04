# previews_helper.py - Icon and preview management
# LAYER = "infra"

import bpy
import bpy.utils.previews
import os

LAYER = "infra"

from .. import pme
from .debug import logw
from .io import get_user_icons_dir, get_system_icons_dir


class PreviewsHelper:

    def __init__(self, folder="icons"):
        # Legacy: single path (system icons only)
        self.path = os.path.join(os.path.dirname(__file__), folder)
        # New: dual-path support (system + user icons)
        self._addon_path = os.path.dirname(__file__)
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

    def _load_icons_from_dir(self, icon_dir):
        """Load all .png icons from a directory."""
        if not os.path.isdir(icon_dir):
            return

        for f in os.listdir(icon_dir):
            if not f.endswith(".png"):
                continue

            name = os.path.splitext(f)[0]
            # User icons override system icons with same name
            if name in self.preview:
                # Remove existing to allow override
                del self.preview[name]

            self.preview.load(name, os.path.join(icon_dir, f), 'IMAGE')

    def refresh(self):
        """Reload icons from disk.

        If preview collection already exists, it is destroyed and recreated.
        Use this when user has added/changed icon files.

        NOTE: Enum-based icons (e.g. OPEN_MODE_ITEMS in constants.py) cache their
        icon_value at class definition time, so refreshing will NOT update those
        enums - they require Blender restart.
        """
        # Clear existing preview collection
        if self.preview is not None:
            try:
                bpy.utils.previews.remove(self.preview)
            except Exception as e:
                logw("PME: previews remove failed during refresh", str(e))
            self.preview = None

        # Load fresh icons
        try:
            self.preview = bpy.utils.previews.new()

            # Load system icons first (bundled with addon)
            system_dir = get_system_icons_dir(self._addon_path)
            self._load_icons_from_dir(system_dir)

            # Load user icons second (overrides system icons with same name)
            user_dir = get_user_icons_dir()
            self._load_icons_from_dir(user_dir)

        except Exception as e:
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
