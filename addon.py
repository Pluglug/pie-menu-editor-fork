import os
import sys
import tomllib
import traceback

import bpy


manifest_path = os.path.join(os.path.dirname(__file__), "blender_manifest.toml")
with open(manifest_path, "rb") as f:
    data = tomllib.load(f)
    version = data.get('version')
    if version:
        parts = []
        for part in version.split('.'):
            parts.append(int(part))
        VERSION = tuple(parts)
ADDON_ID = __package__
ADDON_PATH = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ADDON_PATH, "scripts/")
SAFE_MODE = "--pme-safe-mode" in sys.argv
ICON_ENUM_ITEMS = \
    bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items


def uprefs():
    return getattr(bpy.context, "user_preferences", None) or \
        getattr(bpy.context, "preferences", None)


def prefs():
    return uprefs().addons[ADDON_ID].preferences


def temp_prefs():
    wm = getattr(bpy.context, "window_manager", None)
    pme = getattr(wm, "pme", None)
    return pme


def check_bl_version(version=None):
    version = version or bpy.app.version
    if version >= (2, 80, 0) and bpy.app.version < (2, 80, 0):
        return True

    return bpy.app.version >= version


def check_context():
    return isinstance(bpy.context, bpy.types.Context)


def print_exc(text=None):
    if not prefs().debug_mode:
        return

    if text is not None:
        print()
        print(">>>", text)

    traceback.print_exc()


def is_28():
    return bpy.app.version >= (2, 80, 0)


def ic(icon):
    if not icon:
        return icon

    if icon in ICON_ENUM_ITEMS:
        return icon

    bl28_icons = dict(
        ZOOMIN="ADD",
        ZOOMOUT="REMOVE",
        ROTACTIVE="TRIA_RIGHT",
        ROTATE="TRIA_RIGHT_BAR",
        ROTATECOLLECTION="NEXT_KEYFRAME",
        NORMALIZE_FCURVES="ANIM_DATA",
        OOPS="NODETREE",
        SPLITSCREEN="MOUSE_MMB",
        GHOST="DUPLICATE",
    )

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
