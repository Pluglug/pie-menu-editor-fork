import bpy
import addon_utils
from bpy.app.handlers import persistent
from .addon import ADDON_ID, get_prefs, get_uprefs
from .bl_utils import PopupOperator, popup_area, ctx_dict, area_header_text_set
from .panel_utils import panel, panel_label, bl_panel_enum_items
from .constants import (
    PME_TEMP_SCREEN,
    PME_SCREEN,
    MAX_STR_LEN,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)
from . import constants as CC
from . import c_utils as CTU
from . import screen_utils as SU
from .layout_helper import lh, split
from . import pme
from . import operator_utils


class PME_OT_dummy(bpy.types.Operator):
    bl_idname = "pme.dummy"
    bl_label = ""
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return {'FINISHED'}


class PME_OT_modal_dummy(bpy.types.Operator):
    bl_idname = "pme.modal_dummy"
    bl_label = "Dummy Modal"

    message: bpy.props.StringProperty(
        name="Message",
        options={'SKIP_SAVE'},
        default="OK: Enter/LClick, Cancel: Esc/RClick)",
    )

    def modal(self, context, event):
        if event.value == 'PRESS':
            if event.type in {'ESC', 'RIGHTMOUSE'}:
                area_header_text_set()
                return {'CANCELLED'}
            elif event.type in {'RET', 'LEFTMOUSE'}:
                area_header_text_set()
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        area_header_text_set(self.message)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class PME_OT_none(bpy.types.Operator):
    bl_idname = "pme.none"
    bl_label = ""
    bl_options = {'INTERNAL'}

    pass_through: bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        return {'PASS_THROUGH' if self.pass_through else 'CANCELLED'}

    def invoke(self, context, event):
        return {'PASS_THROUGH' if self.pass_through else 'CANCELLED'}


class WM_OT_pme_sidebar_toggle(bpy.types.Operator):
    bl_idname = "wm.pme_sidebar_toggle"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    tools: bpy.props.BoolProperty()

    def execute(self, context):
        SU.toggle_sidebar(tools=self.tools)
        return {'FINISHED'}


class PME_OT_sidebar_toggle(bpy.types.Operator):
    bl_idname = "pme.sidebar_toggle"
    bl_label = "Toggle Sidebar"
    bl_description = "Toggle sidebar"

    sidebar: bpy.props.EnumProperty(
        name="Sidebar",
        description="Sidebar",
        items=(
            ('TOOLS', "Tools", "", 'PREFERENCES', 0),
            ('PROPERTIES', "Properties", "", 'BUTS', 1),
        ),
        options={'SKIP_SAVE'},
    )

    action: bpy.props.EnumProperty(
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


class PME_OT_screen_set(bpy.types.Operator):
    bl_idname = "pme.screen_set"
    bl_label = "Set Screen/Workspace By Name"

    name: bpy.props.StringProperty(
        name="Screen Layout/Workspace Name", description="Screen layout/workspace name"
    )

    def execute(self, context):
        if self.name not in bpy.data.workspaces:
            return {'CANCELLED'}

        if context.screen.show_fullscreen:
            bpy.ops.screen.back_to_previous()

        if context.screen.show_fullscreen:
            bpy.ops.screen.back_to_previous()

        context.window.workspace = bpy.data.workspaces[self.name]

        return {'FINISHED'}


class PME_OT_popup_property(PopupOperator, bpy.types.Operator):
    bl_idname = "pme.popup_property"
    bl_label = "Property"
    bl_description = "Edit property"
    bl_options = {'INTERNAL'}

    path: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def draw(self, context):
        super().draw(context)
        lh.lt(self.layout)
        obj, sep, prop = self.path.rpartition(".")
        if sep:
            obj = pme.context.eval(obj)
            if obj:
                lh.prop_compact(obj, prop)


class PME_OT_popup_user_preferences(PopupOperator, bpy.types.Operator):
    bl_idname = "pme.popup_user_preferences"
    bl_label = "User Preferences"
    bl_description = "Open the user preferences in a popup"
    bl_options = {'INTERNAL'}

    tab: bpy.props.EnumProperty(
        name="Tab",
        description="Tab",
        options={'SKIP_SAVE'},
        items=(
            ('CURRENT', "Current", ""),
            ('INTERFACE', "Interface", ""),
            ('EDITING', "Editing", ""),
            ('INPUT', "Input", ""),
            ('ADDONS', "Add-ons", ""),
            ('THEMES', "Themes", ""),
            ('FILES', "File", ""),
            ('SYSTEM', "System", ""),
        ),
    )
    width: bpy.props.IntProperty(
        name="Width",
        description="Width of the popup",
        default=800,
        options={'SKIP_SAVE'},
    )
    center: bpy.props.BoolProperty(
        name="Center", description="Center", default=True, options={'SKIP_SAVE'}
    )

    def draw(self, context):
        PopupOperator.draw(self, context)

        upr = get_uprefs()
        col = self.layout.column(align=True)
        col.row(align=True).prop(upr, "active_section", expand=True)

        if upr.active_section == 'INTERFACE':
            tp = bpy.types.USERPREF_PT_interface
        elif upr.active_section == 'EDITING':
            tp = bpy.types.USERPREF_PT_edit
        elif upr.active_section == 'INPUT':
            tp = bpy.types.USERPREF_PT_input
        elif upr.active_section == 'ADDONS':
            tp = bpy.types.USERPREF_PT_addons
        elif upr.active_section == 'THEMES':
            tp = bpy.types.USERPREF_PT_theme
        elif upr.active_section == 'FILES':
            tp = bpy.types.USERPREF_PT_file
        elif upr.active_section == 'SYSTEM':
            tp = getattr(bpy.types, "USERPREF_PT_system", None) or getattr(
                bpy.types, "USERPREF_PT_system_general", None
            )

        pme.context.layout = col
        panel(tp, frame=True, header=False, poll=False)

    def invoke(self, context, event):
        if self.tab != 'CURRENT':
            try:
                get_uprefs().active_section = self.tab
            except:
                pass

        return PopupOperator.invoke(self, context, event)


class PME_OT_popup_addon_preferences(PopupOperator, bpy.types.Operator):
    bl_idname = "pme.popup_addon_preferences"
    bl_label = "Addon Preferences"
    bl_description = "Open the addon preferences in a popup"
    bl_options = {'INTERNAL'}

    addon: bpy.props.StringProperty(
        name="Add-on", description="Add-on", options={'SKIP_SAVE'}
    )
    width: bpy.props.IntProperty(
        name="Width",
        description="Width of the popup",
        default=800,
        options={'SKIP_SAVE'},
    )
    center: bpy.props.BoolProperty(
        default=True, name="Center", description="Center", options={'SKIP_SAVE'}
    )
    auto_close: bpy.props.BoolProperty(
        default=False,
        name="Auto Close",
        description="Auto close the popup",
        options={'SKIP_SAVE'},
    )

    def draw(self, context):
        title = None
        if self.auto_close:
            mod = addon_utils.addons_fake_modules.get(self.addon)
            if not mod:
                return
            info = addon_utils.module_bl_info(mod)
            title = info["name"]

        PopupOperator.draw(self, context, title)

        addon_prefs = None
        for addon in get_uprefs().addons:
            if addon.module == self.addon:
                addon_prefs = addon.preferences
                break

        if addon_prefs and hasattr(addon_prefs, "draw"):
            col = self.layout.column(align=True)
            addon_prefs.layout = col.box()
            addon_prefs.draw(context)
            addon_prefs.layout = None

            row = col.row(align=True)
            row.operator_context = 'INVOKE_DEFAULT'
            row.operator("wm.save_userpref")

    def invoke(self, context, event):
        if not self.addon:
            self.addon = ADDON_ID
        return PopupOperator.invoke(self, context, event)


class PME_OT_popup_panel(PopupOperator, bpy.types.Operator):
    bl_idname = "pme.popup_panel"
    bl_label = "Pie Menu Editor"
    bl_description = "Open the panel in a popup"
    bl_options = {'INTERNAL'}

    panel: bpy.props.StringProperty(
        name="Panel(s)",
        description=(
            "Comma/semicolon separated panel ID(s).\n"
            "  Use a semicolon to add columns.\n"
        ),
        options={'SKIP_SAVE'},
    )
    frame: bpy.props.BoolProperty(
        name="Frame", description="Frame", default=True, options={'SKIP_SAVE'}
    )
    header: bpy.props.BoolProperty(
        name="Header", description="Header", default=True, options={'SKIP_SAVE'}
    )
    area: bpy.props.EnumProperty(
        name="Area Type",
        description="Area type",
        items=CC.area_type_enum_items(),
        options={'SKIP_SAVE'},
    )
    width: bpy.props.IntProperty(
        name="Width",
        description="Width of the popup",
        default=-1,
        options={'SKIP_SAVE'},
    )

    def draw(self, context):
        title = None
        panel_groups = self.panel.split(";")
        if len(panel_groups) == 1:
            panels = panel_groups[0].split(",")
            if len(panels) == 1:
                p = panels[0]
                if p[0] == "!":
                    p = p[1:]
                title = panel_label(p)
        PopupOperator.draw(self, context, title)

        layout = self.layout

        if len(panel_groups) > 1:
            layout = split(layout)

        for group in panel_groups:
            panels = group.split(",")
            col = layout.column()
            pme.context.layout = col
            for p in panels:
                expand = None
                if p[0] == "!":
                    expand = False
                    p = p[1:]
                panel(
                    p.strip(),
                    frame=self.frame,
                    header=self.header,
                    area=self.area,
                    expand=expand,
                )

    def cancel(self, context):
        PopupOperator.cancel(self, context)
        # bpy.types.Context.__getattribute__ = self.oga

    def execute(self, context):
        PopupOperator.execute(self, context)
        # bpy.types.Context.__getattribute__ = self.oga
        return {'FINISHED'}

    def invoke(self, context, event):
        pme.context.reset()

        if self.width == -1:
            panel_groups = self.panel.split(";")
            self.width = 300 * len(panel_groups)

        return PopupOperator.invoke(self, context, event)


class PME_OT_select_popup_panel(bpy.types.Operator):
    bl_idname = "pme.select_popup_panel"
    bl_label = "Select and Open Panel"
    bl_description = "Select and open the panel in a popup"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        if not PME_OT_select_popup_panel.enum_items:
            PME_OT_select_popup_panel.enum_items = bl_panel_enum_items()

        return PME_OT_select_popup_panel.enum_items

    item: bpy.props.EnumProperty(items=get_items, options={'SKIP_SAVE', 'HIDDEN'})

    def execute(self, context):
        PME_OT_select_popup_panel.enum_items = None
        bpy.ops.pme.popup_panel('INVOKE_DEFAULT', panel=self.item)
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_select_popup_panel.enum_items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_window_auto_close(bpy.types.Operator):
    bl_idname = "pme.window_auto_close"
    bl_label = "Close Temp Windows (PME)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        # Refactor_TODO: Revisit roaoao's original code and consider refactoring it.
        #                If you do ctx_override, use temp_override

        # if context.window.screen.name.startswith(PME_SCREEN) or \
        #         context.window.screen.name.startswith(PME_TEMP_SCREEN):
        #     bpy.ops.wm.window_close(dict(window=context.window))

        # return {'PASS_THROUGH'}

        if not context.window.screen.name.startswith(PME_TEMP_SCREEN):
            # delete_flag = False
            # window = context.window

            wm = context.window_manager
            # used_pme_screens = set()
            for w in wm.windows:
                if w.screen.name.startswith(PME_TEMP_SCREEN):
                    with context.temp_override(window=w):
                        bpy.ops.screen.new()

                    bpy.ops.pme.timeout(
                        cmd=f"p = {w.as_pointer()}; "
                            "w = [w for w in C.window_manager.windows "
                            "if w.as_pointer() == p][0]; "
                            "oc = C.temp_override(window=w); oc.__enter__(); "
                            "bpy.ops.wm.window_close(); oc.__exit__()")

                # elif w.screen.name.startswith(PME_SCREEN):
                #     used_pme_screens.add(w.screen.name)

            # screens = [w.screen for w in wm.windows]

            # for s in bpy.data.screens:
            #     if s.name.startswith(PME_TEMP_SCREEN):
            #         delete_flag = True
            #         bpy.ops.screen.delete(dict(window=window, screen=s))

            #     elif s.name.startswith(PME_SCREEN) and \
            #             s.name not in used_pme_screens:
            #         delete_flag = True
            #         bpy.ops.screen.delete(dict(window=window, screen=s))

            # if delete_flag:
            #     for s, w in zip(screens, wm.windows):
            #         bpy.ops.pme.screen_set(
            #             dict(window=w, screen=s),
            #             'INVOKE_DEFAULT', name=s.name)

            get_prefs().enable_window_kmis(False)

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        return self.execute(context)


class PME_OT_area_move(bpy.types.Operator):
    bl_idname = "pme.area_move"
    bl_label = "Move Area"
    bl_description = "Move area"
    bl_options = {'INTERNAL'}

    area: bpy.props.EnumProperty(
        name="Area Type",
        description="Area type",
        items=CC.area_type_enum_items(),
        options={'SKIP_SAVE'},
    )
    edge: bpy.props.EnumProperty(
        name="Area Edge",
        description="Edge of the area to move",
        items=(
            ('TOP', "Top", "", 'TRIA_TOP_BAR', 0),
            ('BOTTOM', "Bottom", "", 'TRIA_BOTTOM_BAR', 1),
            ('LEFT', "Left", "", 'TRIA_LEFT_BAR', 2),
            ('RIGHT', "Right", "", 'TRIA_RIGHT_BAR', 3),
        ),
        options={'SKIP_SAVE'},
    )
    delta: bpy.props.IntProperty(
        name="Delta", description="Delta", default=300, options={'SKIP_SAVE'}
    )
    move_cursor: bpy.props.BoolProperty(
        name="Move Cursor", description="Move cursor", options={'SKIP_SAVE'}
    )

    def get_target_area(self, context):
        if self.area == 'CURRENT':
            return context.area

        for area in reversed(context.screen.areas):
            if area.ui_type == self.area:
                return area

        return None

    def calculate_cursor_positions(self, area, event):
        mx, my = event.mouse_x, event.mouse_y
        x, y = mx, my

        if self.edge == 'TOP':
            y = area.y + area.height
            my += self.delta * self.move_cursor
        elif self.edge == 'BOTTOM':
            y = area.y
            my += self.delta * self.move_cursor
        elif self.edge == 'RIGHT':
            x = area.x + area.width
            mx += self.delta * self.move_cursor
        elif self.edge == 'LEFT':
            x = area.x
            mx += self.delta * self.move_cursor

        return x, y, mx, my

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        area = self.get_target_area(context)
        if not area:
            self.report({'WARNING'}, "Target area not found")
            return {'CANCELLED'}

        x, y, mx, my = self.calculate_cursor_positions(area, event)
        bpy.context.window.cursor_warp(x, y)

        bpy.ops.pme.timeout(
            delay=0.0001,
            cmd=(
                "bpy.ops.screen.area_move(x=%d, y=%d, delta=%d);"
                "bpy.context.window.cursor_warp(%d, %d);"
            ) % (x, y, self.delta, mx, my)
        )
        return {'FINISHED'}


class PME_OT_sidearea_toggle(bpy.types.Operator):
    bl_idname = "pme.sidearea_toggle"
    bl_label = "Toggle Side Area"
    bl_description = "Toggle side area"
    bl_options = {"INTERNAL"}

    _tolerance_cache = None
    _cache_ui_scale = None
    _cache_ui_line_width = None

    sidebars_state = None

    action: bpy.props.EnumProperty(
        name="Action",
        description="Action",
        items=(
            ("TOGGLE", "Toggle", ""),
            ("SHOW", "Show", ""),
            ("HIDE", "Hide", ""),
        ),
        options={"SKIP_SAVE"},
    )
    main_area: bpy.props.EnumProperty(
        name="Main Area Type",
        description="Main area type",
        items=CC.area_type_enum_items(current=False),
        default="VIEW_3D",
        options={"SKIP_SAVE"},
    )
    area: bpy.props.EnumProperty(
        name="Side Area Type",
        description="Side area type",
        items=CC.area_type_enum_items(current=False),
        default="OUTLINER",
        options={"SKIP_SAVE"},
    )
    ignore_area: bpy.props.EnumProperty(
        name="Ignore Area Type",
        description="Area type to ignore",
        items=CC.area_type_enum_items(current=False, none=True),
        default="NONE",
        options={"SKIP_SAVE"},
    )
    side: bpy.props.EnumProperty(
        name="Side",
        description="Side",
        items=(
            ("LEFT", "Left", "", "TRIA_LEFT_BAR", 0),
            ("RIGHT", "Right", "", "TRIA_RIGHT_BAR", 1),
        ),
        options={"SKIP_SAVE"},
    )
    width: bpy.props.IntProperty(
        name="Width", default=300, subtype="PIXEL", options={"SKIP_SAVE"}
    )
    header: bpy.props.EnumProperty(
        name="Header",
        description="Header options",
        items=CC.header_action_enum_items(),
        options={"SKIP_SAVE"},
    )
    ignore_areas: bpy.props.StringProperty(
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
    def _learn_gap_patterns(cls, areas):
        """Learn gap patterns from current area layout."""
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
    def _get_adaptive_tolerance(cls, areas):
        """Calculate adaptive tolerance based on learned gap patterns."""
        gap_pattern = cls._learn_gap_patterns(areas)

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

    def get_side_areas(self, area):
        """Detect adjacent side areas using adaptive gap learning."""
        all_areas = list(bpy.context.screen.areas)
        tol_info = self._get_adaptive_tolerance(all_areas)
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

    def close_area(self, context, main, area):
        CTU.swap_spaces(area, main, self.area)
        try:
            with context.temp_override(area=area):
                bpy.ops.screen.area_close()
            return
        except:
            pass

        if area.x < main.x:
            try:
                bpy.ops.screen.area_join(
                    min_x=area.x + 2,
                    min_y=area.y + 2,
                    max_x=area.x - 2,
                    max_y=area.y + 2,
                )
            except:
                bpy.ops.screen.area_join(cursor=(area.x, area.y + 2))
        else:
            try:
                bpy.ops.screen.area_join(
                    min_x=area.x + area.width - 2,
                    min_y=area.y + area.height - 2,
                    max_x=area.x + area.width + 2,
                    max_y=area.y + area.height - 2,
                )
            except:
                bpy.ops.screen.area_swap(cursor=(area.x + area.width - 2, area.y + 2))
                bpy.ops.screen.area_join(cursor=(area.x + area.width - 2, area.y + 2))

    def execute(self, context):
        self.ia = set(a.strip() for a in self.ignore_areas.split(","))
        self.ia.add(self.ignore_area)
        if self.area in self.ia:
            self.ia.remove(self.area)

        for a in context.screen.areas:
            if a.ui_type == self.main_area:
                break
        else:
            self.report({"WARNING"}, "Main area not found")
            return {"CANCELLED"}

        l, r = self.get_side_areas(a)

        if (
            l
            and self.side == "LEFT"
            and self.action in ("TOGGLE", "SHOW")
            and l.ui_type != self.area
        ):
            self.save_sidebars(l)
            CTU.swap_spaces(l, a, l.ui_type)
            self.add_space(a, self.area)
            l.ui_type = self.area
            CTU.swap_spaces(l, a, self.area)

            if l.width != self.width:
                CTU.resize_area(l, self.width, direction="RIGHT")
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
            self.save_sidebars(r)
            CTU.swap_spaces(r, a, r.ui_type)
            self.add_space(a, self.area)
            r.ui_type = self.area
            CTU.swap_spaces(r, a, self.area)

            if r.width != self.width:
                CTU.resize_area(r, self.width, direction="LEFT")
                SU.redraw_screen()

            self.restore_sidebars(r)
            self.move_header(r)
            self.fix_area(r)

        elif l and self.side == "LEFT" and self.action in ("TOGGLE", "HIDE"):
            self.save_sidebars(l)
            self.close_area(context, a, l)
            SU.redraw_screen()

        elif r and self.side == "RIGHT" and self.action in ("TOGGLE", "HIDE"):
            self.save_sidebars(r)
            self.close_area(context, a, r)
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

        return {"FINISHED"}


class PME_OT_popup_area(bpy.types.Operator):
    bl_idname = "pme.popup_area"
    bl_label = "Popup Area"
    bl_description = "Open the area in a new window"
    bl_options = {'INTERNAL'}

    width: bpy.props.IntProperty(
        name="Width",
        description="Width of the window (-1 - auto)",
        subtype='PIXEL',
        default=-1,
        min=WINDOW_MIN_WIDTH,
        soft_min=-1,
        options={'SKIP_SAVE'},
    )
    height: bpy.props.IntProperty(
        name="Height",
        description="Height of the window (-1 - auto)",
        subtype='PIXEL',
        default=-1,
        min=WINDOW_MIN_HEIGHT,
        soft_min=-1,
        options={'SKIP_SAVE'},
    )
    center: bpy.props.BoolProperty(
        name="Center", description="Center", options={'SKIP_SAVE'}
    )
    area: bpy.props.EnumProperty(
        name="Area",
        description="Area",
        items=CC.area_type_enum_items(),
        options={'SKIP_SAVE'},
    )
    auto_close: bpy.props.BoolProperty(
        default=True,
        name="Auto Close",
        description="Click outside to close the window",
        options={'SKIP_SAVE'},
    )
    header: bpy.props.EnumProperty(
        name="Header",
        description="Header options",
        items=CC.header_action_enum_items(),
        options={'SKIP_SAVE'},
    )
    cmd: bpy.props.StringProperty(
        name="Exec on Open",
        description="Execute python code on window open",
        maxlen=MAX_STR_LEN,
        options={'SKIP_SAVE'},
    )

    def update_header(self, context, on_top, visible, d):
        if self.header == 'DEFAULT':
            return

        if 'TOP' in self.header:
            if not on_top:
                with context.temp_override(**d):
                    bpy.ops.screen.region_flip()
        else:
            if on_top:
                with context.temp_override(**d):
                    bpy.ops.screen.region_flip()

        if 'HIDE' in self.header:
            if visible:
                with context.temp_override(**d):
                    bpy.ops.screen.header()
        else:
            if not visible:
                with context.temp_override(**d):
                    bpy.ops.screen.header()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        # Setup area
        if self.area == 'CURRENT':
            if not context.area:
                return {'CANCELLED'}

            self.area = context.area.ui_type

        # Setup Screen Name
        area_name = next((item[1] for item in CC.area_type_enum_items() if item[0] == self.area), "")
        screen_name = PME_TEMP_SCREEN if self.auto_close else PME_SCREEN
        screen_name += area_name

        area = context.area or context.screen.areas[0]

        rh, rw = None, None
        for r in area.regions:
            if r.type == 'HEADER':
                rh = r
            elif r.type == 'WINDOW':
                rw = r

        header_dict = ctx_dict(area=area, region=rh)
        header_visible = rh.height > 1
        if header_visible:
            header_on_top = rw.y == area.y
        else:
            header_on_top = rh.y > area.y

        self.update_header(context, header_on_top, header_visible, header_dict)

        window = context.window
        windows = [w for w in context.window_manager.windows]

        if self.width == -1:
            if self.area == 'PROPERTIES':
                self.width = round(350 * get_uprefs().view.ui_scale)
            elif self.area == 'OUTLINER':
                self.width = round(400 * get_uprefs().view.ui_scale)
            else:
                self.width = round(window.width * 0.8)

        if self.width < WINDOW_MIN_WIDTH:
            self.width = WINDOW_MIN_WIDTH
        elif self.width > window.width:
            self.width = window.width

        if self.height == -1:
            self.height = round(window.height * 0.8)
        elif self.height < WINDOW_MIN_HEIGHT:
            self.height = WINDOW_MIN_HEIGHT

        x, y = event.mouse_x, event.mouse_y
        if self.center:
            x = window.width >> 1
            y = window.height - (window.height - self.height >> 1)
            context.window.cursor_warp(x, y)

        popup_area(area, self.width, self.height, x, y)

        new_window = None
        if context.window_manager.windows[-1] not in windows:
            new_window = context.window_manager.windows[-1]

        if new_window:
            target_area = new_window.screen.areas[0] if new_window.screen.areas else None
            target_area.ui_type = self.area

            if screen_name in bpy.data.screens:
                new_window.screen = bpy.data.screens[screen_name]
            else:
                new_window.screen.name = screen_name
                new_window.screen.user_clear()

                # FIXME: Screen reuse not implemented - commands only execute on first creation
                if self.cmd:
                    SU.exec_with_override(
                        cmd=self.cmd,
                        window=new_window,
                        screen=new_window.screen,
                        area=target_area,
                    )

        self.update_header(context, header_on_top, header_visible, header_dict)

        get_prefs().enable_window_kmis()

        return {'FINISHED'}


class PME_OT_clipboard_copy(bpy.types.Operator):
    bl_idname = "pme.clipboard_copy"
    bl_label = "Copy"
    bl_options = {'INTERNAL'}

    text: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        context.window_manager.clipboard = self.text
        return {'FINISHED'}


@persistent
def save_pre_handler(_):
    for s in bpy.data.screens:
        if s.name.startswith(PME_TEMP_SCREEN) and s.users > 0:
            s.user_clear()


def register():
    bpy.app.handlers.save_pre.append(save_pre_handler)


def unregister():
    if save_pre_handler in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(save_pre_handler)
