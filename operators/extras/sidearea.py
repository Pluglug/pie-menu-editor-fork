# operators/extras/sidearea.py - Sidebar and Side Area toggle operators for PME
# LAYER = "operators"
#
# Moved from: extra_operators.py (Phase 2-C operators reorganization)
#
# Contains:
#   - WM_OT_pme_sidebar_toggle: Toggle sidebar (simple)
#   - PME_OT_sidebar_toggle: Toggle sidebar with options
#   - PME_OT_sidearea_toggle: Toggle side area (complex area management)
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.app import version as APP_VERSION

from ...addon import get_uprefs
from ...ui import screen as SU
from ...core import constants as CC
from ... import c_utils as CTU
from ... import operator_utils


class WM_OT_pme_sidebar_toggle(Operator):
    bl_idname = "wm.pme_sidebar_toggle"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    tools: BoolProperty()

    def execute(self, context):
        SU.toggle_sidebar(tools=self.tools)
        return {'FINISHED'}


class PME_OT_sidebar_toggle(Operator):
    bl_idname = "pme.sidebar_toggle"
    bl_label = "Toggle Sidebar"
    bl_description = "Toggle sidebar"

    sidebar: EnumProperty(
        name="Sidebar",
        description="Sidebar",
        items=(
            ('TOOLS', "Tools", "", 'PREFERENCES', 0),
            ('PROPERTIES', "Properties", "", 'BUTS', 1),
        ),
        options={'SKIP_SAVE'},
    )

    action: EnumProperty(
        name="Action",
        description="Action",
        items=(
            ('TOGGLE', "Toggle", ""),
            ('SHOW', "Show", ""),
            ('HIDE', "Hide", ""),
        ),
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        value = None
        if self.action == 'SHOW':
            value = True
        elif self.action == 'HIDE':
            value = False

        SU.toggle_sidebar(tools=self.sidebar == 'TOOLS', value=value)

        return {'FINISHED'}


class PME_OT_sidearea_toggle(Operator):
    bl_idname = "pme.sidearea_toggle"
    bl_label = "Toggle Side Area"
    bl_description = "Toggle side area"
    bl_options = {"INTERNAL"}

    _tolerance_cache = None
    _cache_ui_scale = None
    _cache_ui_line_width = None

    sidebars_state = None

    action: EnumProperty(
        name="Action",
        description="Action",
        items=(
            ("TOGGLE", "Toggle", ""),
            ("SHOW", "Show", ""),
            ("HIDE", "Hide", ""),
        ),
        options={"SKIP_SAVE"},
    )
    main_area: EnumProperty(
        name="Main Area Type",
        description="Main area type",
        items=CC.AreaEnumHelper.gen_items,
        default=0,  # VIEW_3D
        options={"SKIP_SAVE"},
    )
    area: EnumProperty(
        name="Side Area Type",
        description="Side area type",
        items=CC.AreaEnumHelper.gen_items,
        default=1,  # IMAGE_EDITOR
        options={"SKIP_SAVE"},
    )
    ignore_area: EnumProperty(
        name="Ignore Area Type",
        description="Area type to ignore",
        items=CC.AreaEnumHelper.gen_items_with_none,
        default=0,  # NONE
        options={"SKIP_SAVE"},
    )
    side: EnumProperty(
        name="Side",
        description="Side",
        items=(
            ("LEFT", "Left", "", "TRIA_LEFT_BAR", 0),
            ("RIGHT", "Right", "", "TRIA_RIGHT_BAR", 1),
            ("TOP", "Top", "", "TRIA_UP_BAR", 2),
            ("BOTTOM", "Bottom", "", "TRIA_DOWN_BAR", 3),
        ),
        options={"SKIP_SAVE"},
    )
    width: IntProperty(
        name="Width", default=300, subtype="PIXEL", options={"SKIP_SAVE"}
    )
    header: EnumProperty(
        name="Header",
        description="Header options",
        items=CC.header_action_enum_items(),
        options={"SKIP_SAVE"},
    )
    ignore_areas: StringProperty(
        name="Ignore Area Types",
        description="Comma separated area types to ignore",
        options={"SKIP_SAVE"},
    )

    @staticmethod
    def _get_blender_area_gap():
        """Calculate actual Blender area gap based on UI settings."""
        prefs = get_uprefs()
        ui_scale = prefs.view.ui_scale
        ui_line_width = prefs.view.ui_line_width
        system_dpi = getattr(prefs.system, "dpi", 72.0)
        pixel_size = getattr(prefs.system, "pixel_size", 1.0)
        if ui_line_width == "THIN":
            border_width = 1
        elif ui_line_width == "THICK":
            border_width = 3
        else:  # 'AUTO'
            border_width = max(1, round(2 * ui_scale))
        effective_dpi = system_dpi * pixel_size
        dpi = effective_dpi * ui_scale * (72.0 / 96.0)
        scale_factor = dpi / 72.0
        edge_thickness = float(border_width) * scale_factor

        return {
            "gap": edge_thickness,
            "scale_factor": scale_factor,
            "ui_scale": ui_scale,
            "border_width": border_width,
            "ui_line_width": ui_line_width,
            "system_dpi": system_dpi,
            "pixel_size": pixel_size,
            "effective_dpi": effective_dpi,
        }

    @classmethod
    def _learn_gap_patterns_horizontal(cls, areas):
        """Learn horizontal gap patterns from current area layout."""
        if len(areas) < 2:
            return None

        horizontal_gaps = []

        for i, area_a in enumerate(areas):
            for j, area_b in enumerate(areas):
                if i >= j:
                    continue

                if (
                    abs(area_a.height - area_b.height) <= 5
                    and abs(area_a.y - area_b.y) <= 5
                ):
                    if area_a.x < area_b.x:
                        gap = area_b.x - (area_a.x + area_a.width)
                    else:
                        gap = area_a.x - (area_b.x + area_b.width)

                    if 0 < gap < 50:
                        horizontal_gaps.append(gap)

        if horizontal_gaps:
            h_gaps = sorted(horizontal_gaps)
            return {
                "gaps": h_gaps,
                "median": h_gaps[len(h_gaps) // 2],
                "mean": sum(h_gaps) / len(h_gaps),
                "min": min(h_gaps),
                "max": max(h_gaps),
                "count": len(h_gaps),
            }

        return None

    @classmethod
    def _learn_gap_patterns_vertical(cls, areas):
        """Learn vertical gap patterns from current area layout."""
        if len(areas) < 2:
            return None

        vertical_gaps = []

        for i, area_a in enumerate(areas):
            for j, area_b in enumerate(areas):
                if i >= j:
                    continue

                width_match = abs(area_a.width - area_b.width) <= 5
                x_match = abs(area_a.x - area_b.x) <= 5

                if width_match and x_match:
                    if area_a.y < area_b.y:
                        gap = area_b.y - (area_a.y + area_a.height)
                    else:
                        gap = area_a.y - (area_b.y + area_b.height)

                    if 0 < gap < 50:
                        vertical_gaps.append(gap)

        if vertical_gaps:
            v_gaps = sorted(vertical_gaps)
            return {
                "gaps": v_gaps,
                "median": v_gaps[len(v_gaps) // 2],
                "mean": sum(v_gaps) / len(v_gaps),
                "min": min(v_gaps),
                "max": max(v_gaps),
                "count": len(v_gaps),
            }

        return None

    @classmethod
    def _get_cached_tolerance(cls):
        """Fallback tolerance calculation."""
        try:
            gap_info = cls._get_blender_area_gap()
            actual_gap = gap_info["gap"]
            adaptive_tolerance = actual_gap * 0.5
            final_tolerance = max(1.0, adaptive_tolerance, 0.1)

            return {"tolerance": final_tolerance, "expected_gap": actual_gap}
        except Exception:
            return {"tolerance": 2.0, "expected_gap": 2.0}

    @classmethod
    def _get_adaptive_tolerance_horizontal(cls, areas):
        """Calculate adaptive tolerance based on learned horizontal gap patterns."""
        gap_pattern = cls._learn_gap_patterns_horizontal(areas)

        if not gap_pattern:
            cached = cls._get_cached_tolerance()
            return {
                "tolerance": cached["tolerance"],
                "expected_gap": cached["expected_gap"],
                "method": "fallback",
            }

        expected_gap = gap_pattern["median"]
        gap_range = gap_pattern["max"] - gap_pattern["min"]
        if gap_range > 0:
            adaptive_tolerance = gap_range * 0.5 + 1.0
        else:
            adaptive_tolerance = expected_gap * 0.5 + 1.0
        min_tolerance = 0.5
        max_tolerance = expected_gap * 2.0
        final_tolerance = max(min_tolerance, min(adaptive_tolerance, max_tolerance))

        return {
            "tolerance": final_tolerance,
            "expected_gap": expected_gap,
            "gap_pattern": gap_pattern,
            "method": "adaptive_learning",
        }

    @classmethod
    def _get_adaptive_tolerance_vertical(cls, areas):
        """Calculate adaptive tolerance based on learned vertical gap patterns."""
        gap_pattern = cls._learn_gap_patterns_vertical(areas)

        if not gap_pattern:
            cached = cls._get_cached_tolerance()
            return {
                "tolerance": cached["tolerance"],
                "expected_gap": cached["expected_gap"],
                "method": "fallback",
            }

        expected_gap = gap_pattern["median"]
        gap_range = gap_pattern["max"] - gap_pattern["min"]
        if gap_range > 0:
            adaptive_tolerance = gap_range * 0.5 + 1.0
        else:
            adaptive_tolerance = expected_gap * 0.5 + 1.0
        min_tolerance = 0.5
        max_tolerance = expected_gap * 2.0
        final_tolerance = max(min_tolerance, min(adaptive_tolerance, max_tolerance))

        return {
            "tolerance": final_tolerance,
            "expected_gap": expected_gap,
            "gap_pattern": gap_pattern,
            "method": "adaptive_learning",
        }

    def _clamp_side_width(self, context, main_area):
        """Clamp requested side width to a safe range to avoid layout corruption."""
        window = getattr(context, "window", None)
        if window and getattr(window, "width", 0):
            max_width = min(main_area.width, window.width) // 2
        else:
            max_width = main_area.width // 2

        max_width = max(32, int(max_width))
        return max(32, min(int(self.width), max_width))

    def get_horizontal_areas(self, area):
        """Detect adjacent left/right areas using adaptive horizontal gap learning."""
        all_areas = list(bpy.context.screen.areas)
        tol_info = self._get_adaptive_tolerance_horizontal(all_areas)
        expected_gap = tol_info["expected_gap"]
        tolerance = tol_info["tolerance"]
        max_search_gap = expected_gap * 3

        left_area = None
        right_area = None
        best_left = None
        best_left_gap = float("inf")
        best_right = None
        best_right_gap = float("inf")

        for candidate_area in all_areas:
            if candidate_area == area or candidate_area.ui_type in self.ia:
                continue
            height_match = abs(candidate_area.height - area.height) <= 5
            y_match = abs(candidate_area.y - area.y) <= 5

            if height_match and y_match:
                left_gap = area.x - (candidate_area.x + candidate_area.width)
                if not left_area and abs(left_gap - expected_gap) <= tolerance:
                    left_area = candidate_area
                elif (
                    not left_area
                    and 0 < left_gap <= max_search_gap
                    and left_gap < best_left_gap
                ):
                    best_left = candidate_area
                    best_left_gap = left_gap

                right_gap = candidate_area.x - (area.x + area.width)
                if not right_area and abs(right_gap - expected_gap) <= tolerance:
                    right_area = candidate_area
                elif (
                    not right_area
                    and 0 < right_gap <= max_search_gap
                    and right_gap < best_right_gap
                ):
                    best_right = candidate_area
                    best_right_gap = right_gap

            if left_area and right_area:
                break
        if not left_area and best_left:
            left_area = best_left
        if not right_area and best_right:
            right_area = best_right

        return left_area, right_area

    def get_vertical_areas(self, area):
        """Detect adjacent top/bottom areas using adaptive vertical gap learning."""
        all_areas = list(bpy.context.screen.areas)
        tol_info = self._get_adaptive_tolerance_vertical(all_areas)
        expected_gap = tol_info["expected_gap"]
        tolerance = tol_info["tolerance"]
        max_search_gap = expected_gap * 3

        top_area = None
        bottom_area = None
        best_top = None
        best_top_gap = float("inf")
        best_bottom = None
        best_bottom_gap = float("inf")

        for candidate_area in all_areas:
            if candidate_area == area or candidate_area.ui_type in self.ia:
                continue

            width_match = abs(candidate_area.width - area.width) <= 5
            x_match = abs(candidate_area.x - area.x) <= 5

            if width_match and x_match:
                bottom_gap = area.y - (candidate_area.y + candidate_area.height)
                if not bottom_area and abs(bottom_gap - expected_gap) <= tolerance:
                    bottom_area = candidate_area
                elif (
                    not bottom_area
                    and 0 < bottom_gap <= max_search_gap
                    and bottom_gap < best_bottom_gap
                ):
                    best_bottom = candidate_area
                    best_bottom_gap = bottom_gap

                top_gap = candidate_area.y - (area.y + area.height)
                if not top_area and abs(top_gap - expected_gap) <= tolerance:
                    top_area = candidate_area
                elif (
                    not top_area
                    and 0 < top_gap <= max_search_gap
                    and top_gap < best_top_gap
                ):
                    best_top = candidate_area
                    best_top_gap = top_gap

            if top_area and bottom_area:
                break

        if not bottom_area and best_bottom:
            bottom_area = best_bottom
        if not top_area and best_top:
            top_area = best_top

        return top_area, bottom_area

    def add_space(self, area, space_type):
        a_type = area.ui_type
        area.ui_type = space_type
        area.ui_type = a_type

    def move_header(self, area):
        if self.header != "DEFAULT":
            SU.move_header(
                area, top="TOP" in self.header, visible="HIDE" not in self.header
            )

    def fix_area(self, area):
        if area.ui_type in ("INFO", "PROPERTIES"):
            bpy.ops.pme.timeout("INVOKE_DEFAULT", cmd=("redraw_screen()"))

    def save_sidebars(self, area):
        if self.sidebars_state is None:
            self.__class__.sidebars_state = dict()

        r_tools, r_ui = None, None
        for r in area.regions:
            if r.type == "TOOLS":
                r_tools = r
            elif r.type == "UI":
                r_ui = r

        self.sidebars_state[area.ui_type] = (
            r_tools and r_tools.width or 0,
            r_ui and r_ui.width or 0,
        )

    def restore_sidebars(self, area):
        if self.sidebars_state is None or area.ui_type not in self.sidebars_state:
            return

        state = self.sidebars_state[area.ui_type]
        if state[0] > 1:
            SU.toggle_sidebar(area, True, True)
        if state[1] > 1:
            SU.toggle_sidebar(area, False, True)

    def close_area(self, context, main, area, direction="HORIZONTAL"):
        # area_join() can only join areas of the same type
        area.ui_type = main.ui_type

        # Redraw to ensure area state is stable before joining
        # This prevents crashes with some editor types
        SU.redraw_screen()

        use_new_api = APP_VERSION >= (4, 3, 0)

        # For Blender 4.2 and earlier, try area_close() first
        if not use_new_api:
            try:
                with context.temp_override(area=area):
                    bpy.ops.screen.area_close()
                return
            except:
                pass  # Fallback to area_join()

        if direction == "HORIZONTAL":
            if area.x < main.x:
                # Closing left area
                if use_new_api:
                    source = (area.x + area.width // 2, area.y + area.height // 2)
                    target = (main.x + main.width // 2, main.y + main.height // 2)
                    bpy.ops.screen.area_join(source_xy=source, target_xy=target)
                else:
                    bpy.ops.screen.area_join(cursor=(area.x + area.width, area.y + 2))
            else:
                # Closing right area
                if use_new_api:
                    source = (area.x + area.width // 2, area.y + area.height // 2)
                    target = (main.x + main.width // 2, main.y + main.height // 2)
                    bpy.ops.screen.area_join(source_xy=source, target_xy=target)
                else:
                    bpy.ops.screen.area_join(cursor=(area.x, area.y + 2))
        else:
            # VERTICAL direction
            if area.y < main.y:
                # Closing bottom area
                if use_new_api:
                    source = (area.x + area.width // 2, area.y + area.height // 2)
                    target = (main.x + main.width // 2, main.y + main.height // 2)
                    bpy.ops.screen.area_join(source_xy=source, target_xy=target)
                else:
                    bpy.ops.screen.area_join(cursor=(area.x + 2, area.y + area.height))
            else:
                # Closing top area
                if use_new_api:
                    source = (area.x + area.width // 2, area.y + area.height // 2)
                    target = (main.x + main.width // 2, main.y + main.height // 2)
                    bpy.ops.screen.area_join(source_xy=source, target_xy=target)
                else:
                    bpy.ops.screen.area_join(cursor=(area.x + 2, area.y))

    def _try_close_from_side_area(self, context) -> bool:
        """If the active context is in the side area, try closing it by
        joining it back into an adjacent main area.

        Returns True if the side area was closed and the operator can finish.
        """
        area = context.area
        if not (
            area
            and area.ui_type == self.area
            and self.action in ("TOGGLE", "HIDE")
        ):
            return False

        # Detect the main area that is actually adjacent to this side area.
        # This ensures we only close when the configured main/side pair are neighbors.
        l_side, r_side = self.get_horizontal_areas(area)
        t_side, b_side = self.get_vertical_areas(area)

        main = None
        direction = None

        if self.side == "LEFT":
            cand = r_side
            if cand and cand.ui_type == self.main_area:
                main = cand
                direction = "HORIZONTAL"
        elif self.side == "RIGHT":
            cand = l_side
            if cand and cand.ui_type == self.main_area:
                main = cand
                direction = "HORIZONTAL"
        elif self.side == "TOP":
            cand = b_side
            if cand and cand.ui_type == self.main_area:
                main = cand
                direction = "VERTICAL"
        elif self.side == "BOTTOM":
            cand = t_side
            if cand and cand.ui_type == self.main_area:
                main = cand
                direction = "VERTICAL"

        if not (main and direction):
            return False

        self.save_sidebars(area)
        self.close_area(context, main, area, direction=direction)
        SU.redraw_screen()
        return True

    def execute(self, context):
        self.ia = set(a.strip() for a in self.ignore_areas.split(","))
        self.ia.add(self.ignore_area)
        if self.area in self.ia:
            self.ia.remove(self.area)

        # If we are currently inside the side area, try handling the "close" case
        # directly from there (main/side must be actually adjacent).
        if self._try_close_from_side_area(context):
            return {"FINISHED"}

        a = None
        if context.area and context.area.ui_type == self.main_area:
            a = context.area
        else:
            for a in context.screen.areas:
                if a.ui_type == self.main_area:
                    break
            else:
                self.report({"WARNING"}, "Main area not found")
                return {"CANCELLED"}

        l, r = self.get_horizontal_areas(a)
        t, b = self.get_vertical_areas(a)

        if (
            l
            and self.side == "LEFT"
            and self.action in ("TOGGLE", "SHOW")
            and l.ui_type != self.area
        ):
            target_width = self._clamp_side_width(context, a)
            self.save_sidebars(l)
            CTU.swap_spaces(l, a, l.ui_type)
            self.add_space(a, self.area)
            l.ui_type = self.area
            CTU.swap_spaces(l, a, self.area)

            if l.width != target_width:
                CTU.resize_area(l, target_width, direction="RIGHT")
                SU.redraw_screen()

            self.restore_sidebars(l)
            self.move_header(l)
            self.fix_area(l)

        elif (
            r
            and self.side == "RIGHT"
            and self.action in ("TOGGLE", "SHOW")
            and r.ui_type != self.area
        ):
            target_width = self._clamp_side_width(context, a)
            self.save_sidebars(r)
            CTU.swap_spaces(r, a, r.ui_type)
            self.add_space(a, self.area)
            r.ui_type = self.area
            CTU.swap_spaces(r, a, self.area)

            if r.width != target_width:
                CTU.resize_area(r, target_width, direction="LEFT")
                SU.redraw_screen()

            self.restore_sidebars(r)
            self.move_header(r)
            self.fix_area(r)

        elif l and self.side == "LEFT" and self.action in ("TOGGLE", "HIDE"):
            self.save_sidebars(l)
            self.close_area(context, a, l, direction="HORIZONTAL")
            SU.redraw_screen()

        elif r and self.side == "RIGHT" and self.action in ("TOGGLE", "HIDE"):
            self.save_sidebars(r)
            self.close_area(context, a, r, direction="HORIZONTAL")
            SU.redraw_screen()

        elif (
            t
            and self.side == "TOP"
            and self.action in ("TOGGLE", "SHOW")
            and t.ui_type != self.area
        ):
            self.save_sidebars(t)
            CTU.swap_spaces(t, a, t.ui_type)
            self.add_space(a, self.area)
            t.ui_type = self.area
            CTU.swap_spaces(t, a, self.area)

            if t.height != self.width:
                CTU.resize_area(t, self.width, direction="BOTTOM")
                SU.redraw_screen()

            self.restore_sidebars(t)
            self.move_header(t)
            self.fix_area(t)

        elif (
            b
            and self.side == "BOTTOM"
            and self.action in ("TOGGLE", "SHOW")
            and b.ui_type != self.area
        ):
            self.save_sidebars(b)
            CTU.swap_spaces(b, a, b.ui_type)
            self.add_space(a, self.area)
            b.ui_type = self.area
            CTU.swap_spaces(b, a, self.area)

            if b.height != self.width:
                CTU.resize_area(b, self.width, direction="TOP")
                SU.redraw_screen()

            self.restore_sidebars(b)
            self.move_header(b)
            self.fix_area(b)

        elif t and self.side == "TOP" and self.action in ("TOGGLE", "HIDE"):
            self.save_sidebars(t)
            self.close_area(context, a, t, direction="VERTICAL")
            SU.redraw_screen()

        elif b and self.side == "BOTTOM" and self.action in ("TOGGLE", "HIDE"):
            self.save_sidebars(b)
            self.close_area(context, a, b, direction="VERTICAL")
            SU.redraw_screen()

        elif (
            (self.side == "LEFT" and not l) or (self.side == "RIGHT" and not r)
        ) and self.action in ("TOGGLE", "SHOW"):
            if self.width > a.width >> 1:
                self.width = a.width >> 1

            factor = (self.width - 1) / a.width
            if self.side == "RIGHT":
                factor = 1 - factor

            self.add_space(a, self.area)
            mouse = {}
            area_split_props = operator_utils.get_rna_type(
                bpy.ops.screen.area_split
            ).properties

            if "cursor" in area_split_props:
                mouse["cursor"] = [a.x + 1, a.y + 1]
            else:
                mouse["mouse_x"] = a.x + 1
                mouse["mouse_y"] = a.y + 1

            with context.temp_override(area=a):
                bpy.ops.screen.area_split(direction="VERTICAL", factor=factor, **mouse)

            new_area = context.screen.areas[-1]
            new_area.ui_type = self.area
            CTU.swap_spaces(new_area, a, self.area)

            self.restore_sidebars(new_area)
            self.move_header(new_area)
            self.fix_area(new_area)

        elif (
            (self.side == "TOP" and not t) or (self.side == "BOTTOM" and not b)
        ) and self.action in ("TOGGLE", "SHOW"):
            if self.width > a.height >> 1:
                self.width = a.height >> 1

            factor = (self.width - 1) / a.height
            if self.side == "TOP":
                factor = 1 - factor

            self.add_space(a, self.area)
            mouse = {}
            area_split_props = operator_utils.get_rna_type(
                bpy.ops.screen.area_split
            ).properties

            if "cursor" in area_split_props:
                mouse["cursor"] = [a.x + 1, a.y + 1]
            else:
                mouse["mouse_x"] = a.x + 1
                mouse["mouse_y"] = a.y + 1

            with context.temp_override(area=a):
                bpy.ops.screen.area_split(direction="HORIZONTAL", factor=factor, **mouse)

            new_area = context.screen.areas[-1]
            new_area.ui_type = self.area
            CTU.swap_spaces(new_area, a, self.area)

            self.restore_sidebars(new_area)
            self.move_header(new_area)
            self.fix_area(new_area)

        return {"FINISHED"}
