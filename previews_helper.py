import os

import bpy
import bpy.utils.previews

from . import pme
from .debug_utils import logh, logi, logw, loge

def custom_icon(icon):
    return ph.get_icon(icon)


class PreviewsHelper:
    def __init__(self, folder="resources\\icons"):
        self.path = os.path.join(os.path.dirname(__file__), folder)
        self.preview = None
        logh(f"PreviewsHelper.__init__ : Loading icons from {self.path}")

    def get_icon(self, name):
        logi(f"PreviewsHelper.get_icon : Looking for icon {name}")
        if self.preview is None:
            loge("PreviewsHelper.get_icon : No icons loaded")
            return None
        return self.preview[name].icon_id

    def get_icon_name_by_id(self, id):
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
        return self.preview.keys()

    def has_icon(self, name):
        if self.preview is None:
            return False
        return name in self.preview

    def refresh(self):
        if self.preview:
            self.unregister()

        self.preview = bpy.utils.previews.new()
        logh(f"PreviewsHelper.refresh : Looking for icons in {self.path}")
        if not os.path.exists(self.path):
            loge(f"PreviewsHelper.refresh : Folder not found: {self.path}")
        else:
            for f in os.listdir(self.path):
                logi(f"PreviewsHelper.refresh : Loading icon {f}")
                if not f.endswith(".png"):
                    continue
                self.preview.load(os.path.splitext(f)[0],
                                os.path.join(self.path, f),
                                'IMAGE')

            logi(f"PreviewsHelper.refresh : Loaded icons: {list(self.preview.keys())}")


    def unregister(self):
        if self.preview is None:
            return
        bpy.utils.previews.remove(self.preview)
        self.preview = None


if "ph" in globals():
    ph.unregister() # type: ignore
ph = PreviewsHelper()
ph.refresh()

# ph = None

def register():
    # global ph
    # ph = PreviewsHelper()
    # ph.refresh()
    # logw("previews_helper register: Loaded icons:", list(ph.get_names()))

    pme.context.add_global("custom_icon", custom_icon)

def unregister():
    if ph:
        ph.unregister()
