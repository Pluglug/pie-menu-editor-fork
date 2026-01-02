# layout_helper.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "ui"  (for layer violation detection)
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: ui/layout.py
#
# Existing imports like `from .layout_helper import lh` will continue to work.

LAYER = "ui"

from .ui.layout import (
    # Constants
    L_SEP,
    L_LABEL,
    # Classes
    CLayout,
    LayoutHelper,
    Row,
    Col,
    # Module-level instances
    cur_col,
    lh,
    # Module-level variables (for draw_pme_layout state)
    cur_column,
    cur_subrow,
    prev_row_has_columns,
    num_btns,
    num_spacers,
    max_btns,
    max_spacers,
    al_split,
    al_l,
    al_r,
    has_aligners,
    # Functions
    draw_pme_layout,
    operator,
    split,
    register,
)

# Re-export everything for `from .layout_helper import *`
__all__ = [
    "L_SEP",
    "L_LABEL",
    "CLayout",
    "LayoutHelper",
    "Row",
    "Col",
    "cur_col",
    "lh",
    "cur_column",
    "cur_subrow",
    "prev_row_has_columns",
    "num_btns",
    "num_spacers",
    "max_btns",
    "max_spacers",
    "al_split",
    "al_l",
    "al_r",
    "has_aligners",
    "draw_pme_layout",
    "operator",
    "split",
    "register",
]
