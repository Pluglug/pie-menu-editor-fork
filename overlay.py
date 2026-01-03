# overlay.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "infra"  (for layer violation detection)
#
# Backward compatibility wrapper - implementation moved to infra/overlay.py
# This file re-exports all symbols for existing imports

LAYER = "infra"

from .infra import overlay as _overlay
from .infra.overlay import *  # noqa: F401,F403

__all__ = _overlay.__all__
