# debug_utils.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "infra"  (for layer violation detection)
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: infra/debug.py
#
# Existing imports like `from .debug_utils import DBG_INIT` will continue to work.

LAYER = "infra"

from .infra.debug import (
    # Debug flags
    DBG,
    DBG_INIT,
    DBG_LAYOUT,
    DBG_TREE,
    DBG_CMD_EDITOR,
    DBG_MACRO,
    DBG_STICKY,
    DBG_STACK,
    DBG_PANEL,
    DBG_PM,
    DBG_PROP,
    DBG_PROP_PATH,
    DBG_DEPS,
    DBG_PROFILE,
    DBG_RUNTIME,
    DBG_STRUCTURED,
    # Configuration
    DEBUG_LOG_PATH,
    DEBUG_SESSION_ID,
    DEBUG_RUN_ID,
    # Basic logging functions
    logi,
    loge,
    logh,
    logw,
    # Debug utilities
    set_debug_flag,
    enabled_categories,
    dbg_log,
    dbg_scope,
    # Classes
    DependencyGraphLogger,
    # Layer analysis
    make_edges_from_graph,
    resolve_layer,
    detect_layer_violations,
    log_layer_violations,
)

# Re-export everything for `from .debug_utils import *`
__all__ = [
    "DBG",
    "DBG_INIT",
    "DBG_LAYOUT",
    "DBG_TREE",
    "DBG_CMD_EDITOR",
    "DBG_MACRO",
    "DBG_STICKY",
    "DBG_STACK",
    "DBG_PANEL",
    "DBG_PM",
    "DBG_PROP",
    "DBG_PROP_PATH",
    "DBG_DEPS",
    "DBG_PROFILE",
    "DBG_RUNTIME",
    "DBG_STRUCTURED",
    "DEBUG_LOG_PATH",
    "DEBUG_SESSION_ID",
    "DEBUG_RUN_ID",
    "logi",
    "loge",
    "logh",
    "logw",
    "set_debug_flag",
    "enabled_categories",
    "dbg_log",
    "dbg_scope",
    "DependencyGraphLogger",
    "make_edges_from_graph",
    "resolve_layer",
    "detect_layer_violations",
    "log_layer_violations",
]
