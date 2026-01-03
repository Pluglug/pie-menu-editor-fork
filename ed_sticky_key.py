# ed_sticky_key.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "editors"  (for layer violation detection)
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: editors/sticky_key.py

LAYER = "editors"

from .editors.sticky_key import *  # noqa: F401,F403
