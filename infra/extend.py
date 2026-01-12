from __future__ import annotations

# pyright: reportInvalidTypeForm=false
# infra/extend.py - Blender Panel/Menu/Header extension manager
# LAYER = "infra"
#
# Issue #97: ExtendManager for multi-registration and ordering
#
# This module provides a centralized manager for extending Blender's
# Panel/Menu/Header types with PME content. The key innovation is using
# "combined draw functions" to control ordering independently of
# Blender's registration order.
#
# ## Why Combined Draw Functions?
#
# When you call tp.prepend(draw_A) and then tp.prepend(draw_B),
# Blender shows B before A (stack-like behavior). This makes
# order management difficult when you need to reorder items.
#
# The solution is to register ONE combined function per target+side:
#
#   def combined_draw(self, context):
#       for entry in sorted_entries:
#           entry.draw_func(self, context)
#
#   tp.prepend(combined_draw)  # Only one registration
#
# Now reordering just changes the internal sort order, without
# needing to unregister/re-register with Blender.

LAYER = "infra"

import weakref
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import bpy
from bpy import types as bpy_types
from bpy.types import Header, Menu, Panel

from ..ui import screen as SU
from ..infra.utils import extract_str_flags_b
from ..core.constants import F_PRE, F_RIGHT
from .debug import DBG_INIT, logi

if TYPE_CHECKING:
    from ..pme_types import PMItem


@dataclass
class ExtendEntry:
    """An entry representing a single PM extending a Blender type.

    Attributes:
        pm_uid: The PM's unique identifier.
        target: Blender type ID (e.g., "VIEW3D_PT_tools").
        side: "prepend" or "append".
        order: Sort order within same target+side. 0 = innermost.
        draw_func: The individual draw function for this PM.
    """
    pm_uid: str
    target: str
    side: str  # "prepend" | "append"
    order: int
    draw_func: Callable


class ExtendManager:
    """Manager for Blender Panel/Menu/Header extensions.

    Uses combined draw functions to control ordering independently
    of Blender's registration order.

    Attributes:
        _entries: Mapping from pm_uid to ExtendEntry.
        _combined_funcs: Mapping from (target, side) to combined draw function.
        _blender_registered: Set of (target, side) that are registered with Blender.
    """

    def __init__(self):
        self._entries: dict[str, ExtendEntry] = {}
        self._combined_funcs: dict[tuple[str, str], Callable] = {}
        self._blender_registered: set[tuple[str, str]] = set()

    def register(self, pm: PMItem) -> bool:
        """Register a PM's extension.

        Args:
            pm: The PMItem to register.

        Returns:
            True if registered, False if skipped (no extend_target, etc.)
        """
        # Get extend_target and side from pm.data
        prefix = self._get_prefix(pm.mode)
        if not prefix:
            return False

        extend_target = pm.get_data(f"{prefix}_extend_target")
        extend_side = pm.get_data(f"{prefix}_extend_side") or ""
        extend_order = pm.get_data(f"{prefix}_extend_order") or 0
        # Read is_right from pm.data (DIALOG only, default False)
        is_right = pm.get_data(f"{prefix}_extend_is_right") if prefix == "pd" else False

        # Fallback: parse from pm.name (backward compatibility with PME1)
        if not extend_target:
            extend_target, name_is_right, is_prepend = extract_str_flags_b(
                pm.name, F_RIGHT, F_PRE
            )
            if is_prepend:
                extend_side = "prepend"
            elif extend_target:
                extend_side = "append"
            # Use name flag if is_right not explicitly set
            if not is_right and name_is_right:
                is_right = name_is_right

        # Defensive: strip suffix from extend_target if present
        # (handles case where migration didn't run or old data)
        if extend_target:
            clean_target, target_is_right, is_prepend = extract_str_flags_b(
                extend_target, F_RIGHT, F_PRE
            )
            if clean_target != extend_target:
                # Update pm.data with clean target
                pm.set_data(f"{prefix}_extend_target", clean_target)
                extend_target = clean_target
                # Also derive extend_side from suffix if not set
                if not extend_side and is_prepend:
                    extend_side = "prepend"
                    pm.set_data(f"{prefix}_extend_side", extend_side)
                elif not extend_side:
                    extend_side = "append"
                    pm.set_data(f"{prefix}_extend_side", extend_side)
                # Use target flag if is_right not explicitly set
                if not is_right and target_is_right:
                    is_right = target_is_right

        if not extend_target or not extend_side:
            return False

        # Skip PME's own panels
        if extend_target.startswith("PME_"):
            return False

        # Verify target exists in Blender
        tp = getattr(bpy_types, extend_target, None)
        if not tp or not issubclass(tp, (Panel, Menu, Header)):
            return False

        # Get pm key (uid or name fallback)
        pm_uid = pm.uid if pm.uid else pm.name

        # Already registered?
        if pm_uid in self._entries:
            return True

        # Generate draw function
        draw_func = self._gen_draw_func(pm_uid, extend_target, is_right)

        # Create entry
        entry = ExtendEntry(
            pm_uid=pm_uid,
            target=extend_target,
            side=extend_side,
            order=extend_order,
            draw_func=draw_func,
        )
        self._entries[pm_uid] = entry

        # Refresh combined function for this target+side
        self._refresh_combined(extend_target, extend_side)

        DBG_INIT and logi(
            f"extend.register: pm={pm.name!r}, target={extend_target}, side={extend_side}"
        )
        return True

    def unregister(self, pm_uid: str) -> bool:
        """Unregister a PM's extension.

        Args:
            pm_uid: The PM's unique identifier.

        Returns:
            True if unregistered, False if not found.
        """
        entry = self._entries.pop(pm_uid, None)
        if not entry:
            return False

        # Refresh combined function (or unregister if no entries left)
        self._refresh_combined(entry.target, entry.side)

        return True

    def unregister_all(self) -> None:
        """Unregister all extensions."""
        # Collect all target+side pairs
        pairs = set()
        for entry in self._entries.values():
            pairs.add((entry.target, entry.side))

        # Clear entries
        self._entries.clear()

        # Unregister from Blender
        for target, side in pairs:
            self._unregister_from_blender(target, side)

    def get_entries(self, target: str, side: str) -> list[ExtendEntry]:
        """Get all entries for a target+side, sorted by order.

        Args:
            target: Blender type ID.
            side: "prepend" or "append".

        Returns:
            List of ExtendEntry sorted by order (ascending).
        """
        entries = [
            e for e in self._entries.values()
            if e.target == target and e.side == side
        ]
        entries.sort(key=lambda e: e.order)
        return entries

    def get_entry(self, pm_uid: str) -> ExtendEntry | None:
        """Get an entry by pm_uid.

        Args:
            pm_uid: The PM's unique identifier.

        Returns:
            ExtendEntry if found, None otherwise.
        """
        return self._entries.get(pm_uid)

    def normalize_orders(self, target: str, side: str) -> None:
        """Normalize orders to consecutive integers starting from 0.

        Args:
            target: Blender type ID.
            side: "prepend" or "append".
        """
        self._normalize_orders(target, side)

    def change_side(self, pm_uid: str, new_side: str) -> dict[str, int]:
        """Change an entry's side and handle all related updates.

        This method:
        1. Updates the entry's side
        2. Resets order to innermost (0) on new side
        3. Refreshes combined draw functions for both sides
        4. Normalizes orders on the old side (fills gaps)
        5. Returns affected pm_uids with their new orders for pm.data sync

        Args:
            pm_uid: The PM's unique identifier.
            new_side: New side value ("prepend" or "append").

        Returns:
            Dict of {pm_uid: new_order} for all affected entries.
            Includes entries from both old and new sides.
            Empty dict if entry not found or side unchanged.
        """
        entry = self._entries.get(pm_uid)
        if not entry:
            return {}

        old_side = entry.side
        target = entry.target

        # No change needed
        if old_side == new_side:
            return {}

        # Update entry
        entry.side = new_side
        entry.order = 0  # Innermost on new side

        changes = {pm_uid: 0}

        # Refresh old side and normalize orders
        self._refresh_combined(target, old_side)
        self._normalize_orders(target, old_side)

        # Collect order changes from old side
        for e in self.get_entries(target, old_side):
            changes[e.pm_uid] = e.order

        # Shift existing entries on new side to make room
        new_side_entries = self.get_entries(target, new_side)
        for e in new_side_entries:
            if e.pm_uid != pm_uid:
                e.order += 1
                changes[e.pm_uid] = e.order

        # Refresh new side
        self._refresh_combined(target, new_side)

        return changes

    def get_next_order(self, target: str, side: str) -> int:
        """Get the next order value for a new entry (outer position).

        Args:
            target: Blender type ID.
            side: "prepend" or "append".

        Returns:
            Next order value (max + 1, or 0 if no entries).
        """
        # Primary path: use ExtendManager entries (normal operation)
        entries = self.get_entries(target, side)
        if entries:
            return max(e.order for e in entries) + 1

        # Fallback: scan pm.data directly
        # This path is rarely used - mainly as a safety net for edge cases
        # like addon reload or registration failures. In most cases,
        # extend_all() has already registered all extend pms at startup.
        from ..addon import get_prefs
        pr = get_prefs()
        max_order = -1
        for pm in pr.pie_menus:
            prefix = self._get_prefix(pm.mode)
            if not prefix:
                continue
            pm_target = pm.get_data(f"{prefix}_extend_target")
            pm_side = pm.get_data(f"{prefix}_extend_side")
            if pm_target == target and pm_side == side:
                pm_order = pm.get_data(f"{prefix}_extend_order") or 0
                if pm_order > max_order:
                    max_order = pm_order

        return max_order + 1

    def set_order(self, pm_uid: str, new_order: int) -> dict[str, int]:
        """Set a PM's order and adjust other entries accordingly.

        Uses insertion-based logic:
        1. Remove self from the order sequence
        2. Insert at new_order position
        3. Normalize all orders to 0, 1, 2...

        Args:
            pm_uid: The PM's unique identifier.
            new_order: The desired order position.

        Returns:
            Dict of {pm_uid: new_order} for all affected entries.
            Caller should update pm.data for each affected pm.
        """
        entry = self._entries.get(pm_uid)
        if not entry:
            return {}

        target = entry.target
        side = entry.side
        entries = self.get_entries(target, side)

        if len(entries) <= 1:
            # Only one entry, just set order to 0
            entry.order = 0
            return {pm_uid: 0}

        # Clamp new_order to valid range
        max_order = len(entries) - 1
        new_order = max(0, min(new_order, max_order))

        # Build new order list: remove self, insert at new position
        other_entries = [e for e in entries if e.pm_uid != pm_uid]
        other_entries.insert(new_order, entry)

        # Assign consecutive orders and collect changes
        changes = {}
        for i, e in enumerate(other_entries):
            if e.order != i:
                changes[e.pm_uid] = i
            e.order = i

        # Refresh display
        self._refresh_combined(target, side)

        return changes

    def sync_pm_data_orders(self, changes: dict[str, int]) -> None:
        """Sync pm.data with order changes from set_order() or change_side().

        Args:
            changes: Dict of {pm_uid: new_order} from set_order()/change_side().
        """
        if not changes:
            return

        from ..addon import get_prefs
        pr = get_prefs()

        # Build uid → pm lookup table once (O(M) where M = total menus)
        pm_by_uid: dict[str, object] = {}
        for pm in pr.pie_menus:
            key = pm.uid if pm.uid else pm.name
            pm_by_uid[key] = pm

        # Update pm.data for each change (O(N) where N = changes)
        for pm_uid, new_order in changes.items():
            pm = pm_by_uid.get(pm_uid)
            if not pm:
                continue

            prefix = self._get_prefix(pm.mode)
            if prefix:
                pm.set_data(f"{prefix}_extend_order", new_order)

    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------

    def _get_prefix(self, mode: str) -> str | None:
        """Get the data prefix for a mode."""
        if mode == 'DIALOG':
            return "pd"
        elif mode == 'RMENU':
            return "rm"
        return None

    def _gen_draw_func(
        self, pm_uid: str, extend_target: str, is_right: bool = False
    ) -> Callable:
        """Generate a draw function for a single PM.

        This is the individual draw function that will be called
        from the combined draw function.
        """
        # Import here to avoid circular imports
        from ..addon import get_prefs
        from ..ui.layout import draw_pme_layout
        from ..operators import WM_OT_pme_user_pie_menu_call

        def get_pm():
            """Get PM by uid, with name fallback."""
            pr = get_prefs()
            # Try uid first
            for pm in pr.pie_menus:
                if pm.uid == pm_uid:
                    return pm
            # Fallback to name
            try:
                return pr.pie_menus[pm_uid]
            except Exception:
                return None

        if '_HT_' in extend_target:
            # Header draw
            def _draw(self, context):
                is_right_region = context.region.alignment == 'RIGHT'
                if is_right_region != is_right:
                    return
                pm = get_pm()
                if not pm or not pm.enabled:
                    return
                draw_pme_layout(
                    pm,
                    self.layout.column(align=True),
                    WM_OT_pme_user_pie_menu_call._draw_item,
                    icon_btn_scale_x=1,
                )
            return _draw

        elif '_MT_' in extend_target:
            # Menu draw
            def _draw(self, context):
                pm = get_pm()
                if not pm or not pm.enabled:
                    return
                WM_OT_pme_user_pie_menu_call.draw_rm(pm, self.layout)
            return _draw

        else:
            # Panel draw
            def _draw(self, context):
                pm = get_pm()
                if not pm or not pm.enabled:
                    return
                draw_pme_layout(
                    pm,
                    self.layout.column(align=True),
                    WM_OT_pme_user_pie_menu_call._draw_item,
                )
            return _draw

    def _create_combined_draw(self, target: str, side: str) -> Callable:
        """Create a combined draw function for a target+side.

        This function is registered with Blender and internally
        iterates through all entries for this target+side.
        """
        manager_ref = weakref.ref(self)

        def combined_draw(self, context):
            mgr = manager_ref()
            if not mgr:
                return
            for entry in mgr.get_entries(target, side):
                try:
                    entry.draw_func(self, context)
                except Exception as e:
                    print(f"PME extend draw error ({entry.pm_uid}): {e}")

        return combined_draw

    def _refresh_combined(self, target: str, side: str) -> None:
        """Refresh the combined draw function for a target+side.

        This unregisters the old function (if any) and registers
        a new one if there are entries.
        """
        key = (target, side)
        entries = self.get_entries(target, side)

        # Unregister old
        if key in self._blender_registered:
            self._unregister_from_blender(target, side)

        # Register new if there are entries
        if entries:
            self._register_to_blender(target, side)

    def _register_to_blender(self, target: str, side: str) -> None:
        """Register combined draw function with Blender."""
        key = (target, side)
        if key in self._blender_registered:
            return

        tp = getattr(bpy_types, target, None)
        if not tp:
            return

        combined_func = self._create_combined_draw(target, side)
        self._combined_funcs[key] = combined_func

        if side == "prepend":
            tp.prepend(combined_func)
        else:
            tp.append(combined_func)

        self._blender_registered.add(key)
        SU.redraw_screen()

    def _unregister_from_blender(self, target: str, side: str) -> None:
        """Unregister combined draw function from Blender."""
        key = (target, side)
        if key not in self._blender_registered:
            return

        combined_func = self._combined_funcs.get(key)
        if not combined_func:
            return

        tp = getattr(bpy_types, target, None)
        if tp:
            try:
                tp.remove(combined_func)
            except Exception:
                pass

        self._blender_registered.discard(key)
        self._combined_funcs.pop(key, None)
        SU.redraw_screen()

    def _normalize_orders(self, target: str, side: str) -> None:
        """Internal: normalize orders to consecutive integers."""
        entries = self.get_entries(target, side)
        for i, entry in enumerate(entries):
            entry.order = i


# Module-level singleton instance
extend_manager = ExtendManager()


def unregister():
    """Unregister all extensions from Blender.

    Called by addon.unregister_modules() during addon unload or Reload Scripts.
    This ensures Blender's Panel/Menu/Header prepend/append registrations
    are properly cleaned up before module reload.
    """
    entry_count = len(extend_manager._entries)
    registered_count = len(extend_manager._blender_registered)
    DBG_INIT and logi(
        f"extend.unregister: entries={entry_count}, blender_registered={registered_count}"
    )
    extend_manager.unregister_all()
    DBG_INIT and logi("extend.unregister: done")
