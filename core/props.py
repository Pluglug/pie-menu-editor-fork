# core/props.py - Backward compatibility re-exports
# LAYER = "core"
#
# DEPRECATED: This module is kept for backward compatibility.
# New code should import from core.schema instead:
#
#   from ..core.schema import schema
#   schema.IntProperty("pm", "pm_radius", -1)
#
# This file will be removed in v3.0.
#
# Renamed to: core/schema.py (Phase 8-C: Schema Rename)

LAYER = "core"

# Re-export everything from schema for backward compatibility
from .schema import (
    # New names (preferred)
    SchemaProp,
    SchemaRegistry,
    schema,
    ParsedData,
    # Old names (deprecated aliases)
    PMEProp,
    PMEProps,
    props,
)

__all__ = [
    # New names
    "SchemaProp",
    "SchemaRegistry",
    "schema",
    "ParsedData",
    # Deprecated names
    "PMEProp",
    "PMEProps",
    "props",
]
