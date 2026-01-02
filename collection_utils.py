# collection_utils.py - DEPRECATED: Thin wrapper for backward compatibility
# LAYER = "infra"  (for layer violation detection)
#
# This file is scheduled for removal in a future PME2 release.
# All functionality has been moved to: infra/collections.py
#
# Existing imports like `from .collection_utils import AddItemOperator` will continue to work.

LAYER = "infra"

from .infra.collections import (
    # Functions
    sort_collection,
    move_item,
    remove_item,
    find_by,
    # Classes
    AddItemOperator,
    MoveItemOperator,
    RemoveItemOperator,
    BaseCollectionItem,
    # Lifecycle
    register,
)

# Re-export everything for `from .collection_utils import *`
__all__ = [
    "sort_collection",
    "move_item",
    "remove_item",
    "find_by",
    "AddItemOperator",
    "MoveItemOperator",
    "RemoveItemOperator",
    "BaseCollectionItem",
    "register",
]
