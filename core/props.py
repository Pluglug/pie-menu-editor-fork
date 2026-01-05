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

# Re-export from schema for backward compatibility
from .schema import (
    SchemaProp,
    SchemaRegistry,
    schema,
    ParsedData,
)

__all__ = [
    "SchemaProp",
    "SchemaRegistry",
    "schema",
    "ParsedData",
]

# NOTE: PMEProp, PMEProps, props aliases removed in Phase 8-E
# pme.props now refers to user properties (PropertyGroup), not SchemaRegistry
