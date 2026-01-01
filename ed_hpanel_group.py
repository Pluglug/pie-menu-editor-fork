# ed_hpanel_group.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "editors"  (for layer violation detection)
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: editors/hpanel_group.py

LAYER = "editors"

from .editors.hpanel_group import *  # noqa: F401,F403
