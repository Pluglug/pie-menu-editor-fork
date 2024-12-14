import os
import sys
import tomllib
import traceback

import bpy

from .debug_utils import loge


manifest_path = os.path.join(os.path.dirname(__file__), "blender_manifest.toml")
with open(manifest_path, "rb") as f:
    data = tomllib.load(f)
    VERSION_RAW = data.get('version')
    if VERSION_RAW:
        parts = []
        for part in VERSION_RAW.split('.'):
            parts.append(int(part))
        VERSION = tuple(parts)
ADDON_PATH      = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH     = os.path.join(ADDON_PATH, "resources", "scripts")
SAFE_MODE       = "--pme-safe-mode" in sys.argv
ICON_ENUM_ITEMS = \
    bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items


def uprefs(context=bpy.context):
    """Retrieves Blender's user preferences."""
    preferences = getattr(context, "preferences", None)
    if preferences is None:
        loge("Failed to retrieve user preferences.")
        return None
    return preferences


def prefs(context=bpy.context):
    """Retrieves the preferences of this addon."""
    preferences = uprefs(context)
    if preferences is None:
        loge("No preferences attribute found in the context.")
        return None

    addon_prefs = preferences.addons.get(__package__)
    if addon_prefs is None:
        loge(f"Addon preferences not found for package: {__package__}")
        raise KeyError(f"Addon preferences not found: {__package__}")

    return addon_prefs.preferences


def temp_prefs():
    wm = getattr(bpy.context, "window_manager", None)
    return getattr(wm, "pme", None)


def check_context():
    return isinstance(bpy.context, bpy.types.Context)


def print_exc(text=None):
    if not prefs().debug_mode:
        return

    if text is not None:
        print()
        print(">>>", text)

    traceback.print_exc()


def ic(icon):
    if not icon:
        return icon

    if icon in ICON_ENUM_ITEMS:
        return icon

    bl28_icons = {
        'ZOOMIN':            "ADD",
        'ZOOMOUT':           "REMOVE",
        'ROTACTIVE':         "TRIA_RIGHT",
        'ROTATE':            "TRIA_RIGHT_BAR",
        'ROTATECOLLECTION':  "NEXT_KEYFRAME",
        'NORMALIZE_FCURVES': "ANIM_DATA",
        'OOPS':              "NODETREE",
        'SPLITSCREEN':       "MOUSE_MMB",
        'GHOST':             "DUPLICATE"
    }

    if icon in bl28_icons and bl28_icons[icon] in ICON_ENUM_ITEMS:
        return bl28_icons[icon]

    return 'BLENDER'


def ic_rb(value):
    return ic('RADIOBUT_ON' if value else 'RADIOBUT_OFF')


def ic_cb(value):
    return ic('CHECKBOX_HLT' if value else 'CHECKBOX_DEHLT')


def ic_fb(value):
    return ic('SOLO_ON' if value else 'SOLO_OFF')


def ic_eye(value):
    return ic('HIDE_OFF' if value else 'HIDE_ON')
