# ed_base.py - DEPRECATED: Thin wrapper for backward compatibility
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: editors/base.py
#
# Existing imports like `from .ed_base import EditorBase` will continue to work.

from .editors.base import *  # noqa: F401,F403
