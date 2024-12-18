import os

import bpy
import bpy.utils.previews

from . import pme


def custom_icon(icon):
    return ph.get_icon_id(icon)


class PreviewsHelper:
    def __init__(self, folder="resources\\icons") -> None:
        self.path = os.path.join(os.path.dirname(__file__), folder)
        self.preview = None

    def get_icon_id(self, name) -> int:
        return self.preview[name].icon_id

    def get_icon_name(self, index) -> int | None:
        name = None
        min_id = 99999999
        for icon_id, idx in self.preview.items():
            if idx.icon_id == index:
                return icon_id
            if min_id > idx.icon_id:
                min_id = idx.icon_id
                name = icon_id
        return name

    def get_names(self) -> list[int]:
        return self.preview.keys()

    def has_icon(self, name) -> bool:
        if self.preview is None:
            return False
        return name in self.preview

    def refresh(self) -> None:
        if self.preview:
            self.unregister()

        self.preview = bpy.utils.previews.new()
        for f in os.listdir(self.path):
            if not f.endswith(".png"):
                continue
            self.preview.load(os.path.splitext(f)[0],
                              os.path.join(self.path, f),
                              'IMAGE')

    def unregister(self) -> None:
        if self.preview is None:
            return
        bpy.utils.previews.remove(self.preview)
        self.preview = None


if "ph" in globals():
    ph.unregister() # type: ignore
ph = PreviewsHelper()
ph.refresh()


def register():
    pme.context.add_global("custom_icon", custom_icon)

def unregister():
    ph.unregister()
