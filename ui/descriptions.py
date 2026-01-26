# SPDX-License-Identifier: GPL-2.0-or-later

"""
Slot Editor field descriptions for bl_description.

These constants provide mini-references as tooltips, supporting:
- Immediate trial: Users can try functions without opening docs
- Discovery: Beginners learn what's available

Format:
- Variable shortcuts (C, D, O, E, L, U)
- Frequently used functions with full signatures and types
"""

# =============================================================================
# Command Tab
# =============================================================================

SLOT_CMD = """\
Python code to execute.
C=context, D=data, O=ops, E=event, U=user data
---
open_menu(name: str, slot: str|int = None)
overlay(text: str, alignment: str = 'TOP', duration: float = 2.0)
message_box(text: str, icon: str = 'INFO', title: str = "...")
input_box(func: callable = None, prop: str = None)
tag_redraw(area: str = None, region: str = None)
close_popups()
---
props(name: str = None, value = None) -> value | container
find_by(collection, key: str, value) -> item | None
execute_script(path: str, **kwargs) -> return_value
---
CSM.from_context(C, prefix="", suffix="").open_menu()\
"""

# =============================================================================
# Custom Tab (UI Layout)
# =============================================================================

SLOT_CUSTOM = """\
UI layout code. L=layout
C=context, D=data, U=user data
---
operator(L, op: str, text: str = "", icon: str = 'NONE', **props)
panel(pt: str|type, frame: bool = True, header: bool = True, expand: bool = None)
draw_menu(name: str, frame: bool = True, dx: int = 0, dy: int = 0)
custom_icon(filename: str) -> int
---
props(name: str = None, value = None) -> value | container
find_by(collection, key: str, value) -> item | None
---
CSM.from_context(C, prefix="", suffix="").draw_menu(layout=L)\
"""

# =============================================================================
# Property Path
# =============================================================================

SLOT_PROP = """\
Full data path to a Blender property.
Examples:
  C.object.location
  C.object.modifiers["Subsurf"].levels
  D.objects["Cube"].scale\
"""

# =============================================================================
# Poll Command
# =============================================================================

SLOT_POLL = """\
Return True to enable, False to disable.
C=context, D=data
Examples:
  return C.mode == 'EDIT_MESH'
  return C.active_object and C.active_object.type == 'MESH'\
"""

# =============================================================================
# Description Field
# =============================================================================

SLOT_DESCRIPTION = """\
Tooltip text shown on hover.
Use \\n for line breaks.
With 'expr' enabled: return str (C=context, D=data, U=user data)\
"""

# For the expression toggle button (BoolProperty)
SLOT_DESCRIPTION_IS_EXPR = "Enable expression mode (Python code returning str)"
