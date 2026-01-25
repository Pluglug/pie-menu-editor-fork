# pyright: reportInvalidTypeForm=false
"""
GPULayout - Blender-style align pass (2D proximity based).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import fabs, inf
from typing import Any, Optional

from ..items import LayoutItem

LEFT = 0
TOP = 1
RIGHT = 2
DOWN = 3

SIDE1 = {LEFT: TOP, TOP: RIGHT, RIGHT: DOWN, DOWN: LEFT}
SIDE2 = {LEFT: DOWN, DOWN: RIGHT, RIGHT: TOP, TOP: LEFT}
OPPOSITE = {LEFT: RIGHT, RIGHT: LEFT, TOP: DOWN, DOWN: TOP}


def _stitch_flag(side: int) -> int:
    return 1 << side


@dataclass
class AlignItem:
    item: LayoutItem
    borders: list[float]  # [LEFT, TOP, RIGHT, DOWN]
    can_align: bool
    neighbors: list[Optional["AlignItem"]] = field(default_factory=lambda: [None, None, None, None])
    dists: list[float] = field(default_factory=lambda: [inf, inf, inf, inf])
    flags: list[int] = field(default_factory=lambda: [0, 0, 0, 0])


def _item_borders(item: LayoutItem) -> list[float]:
    left = float(item.x)
    top = float(item.y)
    right = float(item.x + item.width)
    bottom = float(item.y - item.height)
    return [left, top, right, bottom]


def _assign_align_groups(layout: Any) -> dict[int, list[LayoutItem]]:
    groups: dict[int, list[LayoutItem]] = {}
    group_id = 0

    def next_group() -> int:
        nonlocal group_id
        group_id += 1
        return group_id

    def walk(node: Any, inherited_group: int | None) -> None:
        group = inherited_group
        if getattr(node, "_align", False):
            if group is None:
                group = next_group()

        for element in getattr(node, "_elements", []):
            if isinstance(element, LayoutItem):
                element.align_group = group
                if group is not None:
                    groups.setdefault(group, []).append(element)
            else:
                # Do not propagate align across non-align layouts, but still traverse.
                child_inherited = group if getattr(element, "_align", False) else None
                walk(element, child_inherited)

    walk(layout, None)
    return groups


def _block_align_proximity_compute(butal: AlignItem, other: AlignItem, max_delta: float) -> None:
    min_delta = 1e-6
    butal_can = butal.can_align
    other_can = other.can_align

    share_line = not (butal.borders[DOWN] >= other.borders[TOP] or
                      butal.borders[TOP] <= other.borders[DOWN])
    share_col = not (butal.borders[LEFT] >= other.borders[RIGHT] or
                     butal.borders[RIGHT] <= other.borders[LEFT])

    if not (share_line or share_col) or not (butal_can or other_can):
        return

    for base_side in (LEFT, TOP):
        if base_side == LEFT and not share_line:
            continue
        if base_side == TOP and not share_col:
            continue

        side = base_side
        side_opp = OPPOSITE[side]

        delta = max(fabs(butal.borders[side] - other.borders[side_opp]), min_delta)
        delta_side_opp = max(fabs(butal.borders[side_opp] - other.borders[side]), min_delta)

        if delta_side_opp < delta:
            side, side_opp = side_opp, side
            delta = delta_side_opp

        if delta < max_delta:
            if delta <= butal.dists[side]:
                if butal_can and other_can:
                    butal.neighbors[side] = other
                    other.neighbors[side_opp] = butal
                elif butal_can and (delta < butal.dists[side]):
                    butal.neighbors[side] = None
                elif other_can and (delta < other.dists[side_opp]):
                    other.neighbors[side_opp] = None

                butal.dists[side] = delta
                other.dists[side_opp] = delta

                if butal_can and other_can:
                    side_s1 = SIDE1[side]
                    side_s2 = SIDE2[side]
                    stitch = _stitch_flag(side)
                    stitch_opp = _stitch_flag(side_opp)

                    if butal.neighbors[side] is None:
                        butal.neighbors[side] = other
                    if other.neighbors[side_opp] is None:
                        other.neighbors[side_opp] = butal

                    if fabs(butal.borders[side_s1] - other.borders[side_s1]) < max_delta:
                        butal.flags[side_s1] |= stitch
                        other.flags[side_s1] |= stitch_opp
                    if fabs(butal.borders[side_s2] - other.borders[side_s2]) < max_delta:
                        butal.flags[side_s2] |= stitch
                        other.flags[side_s2] |= stitch_opp
            return


def _block_align_stitch_neighbors(butal: AlignItem,
                                  side: int,
                                  side_opp: int,
                                  side_s1: int,
                                  side_s2: int,
                                  co: float) -> None:
    stitch_s1 = _stitch_flag(side_s1)
    stitch_s2 = _stitch_flag(side_s2)

    while (butal.flags[side] & stitch_s1) and (butal := butal.neighbors[side_s1]) and \
            (butal.flags[side] & stitch_s2):
        neighbor = butal.neighbors[side]

        if neighbor:
            butal.borders[side] = co
            butal.dists[side] = 0.0
            neighbor.borders[side_opp] = co
            neighbor.dists[side_opp] = 0.0
        else:
            butal.borders[side] = co
            butal.dists[side] = 0.0

        # Clear one flag to avoid re-running on same column/side.
        butal.flags[side] &= ~stitch_s2


def _block_align_calc(items: list[AlignItem], max_delta: float) -> None:
    if len(items) < 2:
        return

    # Sort by vertical position descending, then horizontal ascending.
    items.sort(key=lambda it: (-it.borders[TOP], it.borders[LEFT]))

    # Proximity compute.
    for i, butal in enumerate(items):
        for other in items[i + 1:]:
            if (butal.borders[DOWN] - other.borders[TOP]) > max_delta:
                break
            _block_align_proximity_compute(butal, other, max_delta)

    # Stitch and border adjust.
    for butal in items:
        for side in (LEFT, TOP, RIGHT, DOWN):
            other = butal.neighbors[side]
            if not other:
                continue

            side_opp = OPPOSITE[side]
            side_s1 = SIDE1[side]
            side_s2 = SIDE2[side]

            if butal.dists[side] != 0.0:
                delta = butal.dists[side] * 0.5
                if butal.borders[side] >= other.borders[side_opp]:
                    delta *= -1.0

                co = butal.borders[side] + delta
                butal.borders[side] = co
                butal.dists[side] = 0.0

                if other.dists[side_opp] != 0.0:
                    other.borders[side_opp] = co
                    other.dists[side_opp] = 0.0
            else:
                co = butal.borders[side]

            _block_align_stitch_neighbors(butal, side, side_opp, side_s1, side_s2, co)
            _block_align_stitch_neighbors(butal, side, side_opp, side_s2, side_s1, co)


def _apply_rects_and_corners(items: list[AlignItem]) -> None:
    for butal in items:
        item = butal.item
        left = butal.borders[LEFT]
        top = butal.borders[TOP]
        right = butal.borders[RIGHT]
        bottom = butal.borders[DOWN]

        item.x = left
        item.y = top
        item.width = max(0.0, right - left)
        item.height = max(0.0, top - bottom)

        if getattr(item, "corners_locked", False):
            continue

        if not butal.can_align:
            item.corners = (True, True, True, True)
            continue

        left_n = butal.neighbors[LEFT] is not None and butal.neighbors[LEFT].can_align
        right_n = butal.neighbors[RIGHT] is not None and butal.neighbors[RIGHT].can_align
        top_n = butal.neighbors[TOP] is not None and butal.neighbors[TOP].can_align
        down_n = butal.neighbors[DOWN] is not None and butal.neighbors[DOWN].can_align

        item.corners = (
            not (left_n or down_n),   # bottomLeft
            not (left_n or top_n),    # topLeft
            not (right_n or top_n),   # topRight
            not (right_n or down_n),  # bottomRight
        )


def run_align_pass(root_layout: Any) -> None:
    groups = _assign_align_groups(root_layout)
    if not groups:
        return

    unit = root_layout.style.scaled_item_height()
    max_delta = 0.45 * max(unit, unit)

    for _group_id, items in groups.items():
        align_items: list[AlignItem] = []
        for item in items:
            borders = _item_borders(item)
            can_align = bool(item.visible and item.can_align() and item.width > 0 and item.height > 0)
            align_items.append(AlignItem(item=item, borders=borders, can_align=can_align))

        if len(align_items) < 2:
            continue

        _block_align_calc(align_items, max_delta)
        _apply_rects_and_corners(align_items)

