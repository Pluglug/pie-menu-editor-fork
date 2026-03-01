from __future__ import annotations

import bpy
from bpy.app import version as APP_VERSION
import os
import sys
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .preferences import PMEPreferences


VERSION = None
BL_VERSION = None
ADDON_ID = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
ADDON_PATH = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ADDON_PATH, "scripts/")
SAFE_MODE = "--pme-safe-mode" in sys.argv
ICON_ENUM_ITEMS = (
    bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
)


def get_uprefs(context: bpy.types.Context = bpy.context) -> bpy.types.Preferences:
    """
    Get user preferences

    Args:
        context: Blender context (defaults to bpy.context)

    Returns:
        bpy.types.Preferences: User preferences

    Raises:
        AttributeError: If preferences cannot be accessed
    """
    preferences = getattr(context, "preferences", None)
    if preferences is not None:
        return preferences
    raise AttributeError("Could not access preferences")


def get_prefs(context: bpy.types.Context = bpy.context) -> PMEPreferences:
    """
    Get addon preferences

    Args:
        context: Blender context (defaults to bpy.context)

    Returns:
        bpy.types.AddonPreferences: Addon preferences

    Raises:
        KeyError: If addon is not found
    """
    user_prefs = get_uprefs(context)
    addon_prefs = user_prefs.addons.get(ADDON_ID)
    if addon_prefs is not None:
        return addon_prefs.preferences
    raise KeyError(f"Addon '{ADDON_ID}' not found")


def uprefs():
    stack = traceback.extract_stack()
    caller = stack[-2]
    print(
        f"Warning: uprefs() is deprecated. Called from {caller.filename}:{caller.lineno}"
    )
    return get_uprefs()


def prefs():
    stack = traceback.extract_stack()
    caller = stack[-2]
    print(
        f"Warning: prefs() is deprecated. Called from {caller.filename}:{caller.lineno}"
    )
    return get_prefs()


def temp_prefs():
    return getattr(getattr(bpy.context, "window_manager", None), "pme", None)


def check_bl_version(version=None):
    version = version or BL_VERSION
    return APP_VERSION >= version


def check_context():
    return isinstance(bpy.context, bpy.types.Context)


def print_exc(text=None):
    if not get_prefs().show_error_trace:
        return

    if text is not None:
        print()
        print(">>>", text)

    traceback.print_exc()


def ic(icon):
    # Legacy_TODO: Remove or Enhance
    # Support for 2.79 and 2.8+
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

    print("Icon not found:", icon)
    return 'BLENDER'


def ic_rb(value):
    return ic('RADIOBUT_ON' if value else 'RADIOBUT_OFF')


def ic_cb(value):
    return ic('CHECKBOX_HLT' if value else 'CHECKBOX_DEHLT')


def ic_fb(value):
    return ic('SOLO_ON' if value else 'SOLO_OFF')


def ic_eye(value):
    return ic('HIDE_OFF' if value else 'HIDE_ON')
