"""
Pluglug support module for Pie Menu Editor.

This module adds a donation button to the addon preferences.

To disable:
    1. Delete this file (pluglug.py)
    2. Restart Blender
"""

import bpy

_original_draw = None


def draw_with_support(self, context):
    """Draw support button, then call original draw."""
    layout = self.layout

    row = layout.row()
    # Left: info message
    sub = row.row()
    sub.alignment = 'LEFT'
    sub.label(
        text="PME2 is in the works — stay tuned!",
        icon='INFO',
    )
    # Right: support button
    sub = row.row()
    sub.alignment = 'RIGHT'
    op = sub.operator(
        "wm.url_open",
        text="Support on Ko-fi",
        icon='FUND',
    )
    op.url = "https://ko-fi.com/Pluglug"

    # Call original draw
    if _original_draw is not None:
        _original_draw(self, context)


def register():
    global _original_draw
    from .preferences import PMEPreferences
    _original_draw = PMEPreferences.draw
    PMEPreferences.draw = draw_with_support


def unregister():
    global _original_draw
    if _original_draw is not None:
        from .preferences import PMEPreferences
        PMEPreferences.draw = _original_draw
        _original_draw = None
