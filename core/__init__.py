# core/ - Blender非依存のロジック・データ構造
# LAYER = "core"

# Re-export namespace definitions for external access
from .namespace import (
    Stability,
    NAMESPACE_CORE,
    NAMESPACE_EVENT,
    NAMESPACE_USER,
    NAMESPACE_UI,
    NAMESPACE_PUBLIC,
    NAMESPACE_INTERNAL,
    PUBLIC_NAMES,
    is_public,
    is_internal,
    get_stability,
    get_public_names_by_stability,
)
