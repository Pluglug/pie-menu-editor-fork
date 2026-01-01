# overlay.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "infra"  (for layer violation detection)
#
# Backward compatibility wrapper - implementation moved to infra/overlay.py
# This file re-exports all symbols for existing imports

LAYER = "infra"

from .infra.overlay import (
    # Constants
    OVERLAY_ALIGNMENT_ITEMS,
    # Classes
    Timer,
    SpaceGroup,
    Painter,
    Style,
    Text,
    Col,
    TablePainter,
    Overlay,
    OverlayPrefs,
    PME_OT_overlay,
    # Module-level objects
    space_groups,
    # Functions
    overlay,
    register,
)

# Re-export all for star imports
__all__ = [
    'OVERLAY_ALIGNMENT_ITEMS',
    'Timer',
    'SpaceGroup',
    'Painter',
    'Style',
    'Text',
    'Col',
    'TablePainter',
    'Overlay',
    'OverlayPrefs',
    'PME_OT_overlay',
    'space_groups',
    'overlay',
    'register',
]
