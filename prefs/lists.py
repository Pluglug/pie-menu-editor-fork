# pyright: reportInvalidTypeForm=false
# prefs/lists.py - UIList クラス
# LAYER = "prefs"
"""
WM_UL_panel_list, WM_UL_pm_list

PME_UL_pm_tree は prefs/tree.py に配置（P6）
"""

from bpy.types import UIList, UI_UL_list

from ..addon import get_prefs, ic, ic_cb
from ..core import constants as CC
from ..keymap_helper import to_ui_hotkey
from ..ui.layout import lh
from ..ui.panels import hidden_panel


class WM_UL_panel_list(UIList):
    """パネルリストの描画"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        tp = hidden_panel(item.text)
        pr = get_prefs()
        v = pr.panel_info_visibility
        ic_items = pr.rna_type.properties["panel_info_visibility"].enum_items

        if 'NAME' in v:
            layout.label(text=item.name or item.text, icon=ic(ic_items['NAME'].icon))
        if 'CLASS' in v:
            layout.label(text=item.text, icon=ic(ic_items['CLASS'].icon))
        if 'CTX' in v:
            layout.label(
                text=tp.bl_context if tp and hasattr(tp, "bl_context") else "-",
                icon=ic(ic_items['CTX'].icon),
            )
        if 'CAT' in v:
            layout.label(
                text=tp.bl_category if tp and hasattr(tp, "bl_category") else "-",
                icon=ic(ic_items['CAT'].icon),
            )


class WM_UL_pm_list(UIList):
    """Pie Menu リストの描画、フィルタリング、ソート"""

    def draw_filter(self, context, layout):
        pr = get_prefs()

        col = layout.column(align=True)
        col.prop(self, "filter_name", text="", icon=ic('VIEWZOOM'))
        col.prop(pr, "list_size")
        col.prop(pr, "num_list_rows")

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        pr = get_prefs()
        pm = item

        layout = layout.row(align=True)
        lh.lt(layout)

        num_cols = pr.show_names + pr.show_hotkeys + pr.show_keymap_names + pr.show_tags

        use_split = num_cols > 2
        if use_split:
            layout = lh.split(factor=0.5 if pr.show_names else 0.4)
            lh.row()

        lh.prop(item, "enabled", "", emboss=False, icon=ic_cb(item.enabled))

        lh.label("", item.ed.icon)

        col = 0

        hk = to_ui_hotkey(pm)
        show_hotkeys = pr.show_hotkeys
        if pr.show_names:
            lh.prop(pm, "label", "", emboss=False)
            col += 1
        elif show_hotkeys:
            if hk:
                lh.label(hk)
            else:
                lh.prop(pm, "label", "", emboss=False)
            show_hotkeys = False
            col += 1

        if use_split:
            lh.lt(layout)

        if pr.show_tags:
            if col == num_cols - 1:
                lh.row(layout, alignment='RIGHT')
            elif use_split:
                lh.row(layout)
            tag = pm.tag
            if tag:
                tag, _, rest = pm.tag.partition(",")
                if rest:
                    tag += ",.."
            lh.label(tag)
            col += 1

        if pr.show_keymap_names:
            if col == num_cols - 1:
                lh.row(layout, alignment='RIGHT')
            elif use_split:
                lh.row(layout)
            names = [s.strip() for s in pm.km_name.split(CC.KEYMAP_SPLITTER) if s.strip()]
            km_name = names[0] if names else ""
            if len(names) > 1:
                km_name += f" +{len(names) - 1}"
            lh.label(km_name)
            col += 1

        if show_hotkeys:
            if num_cols > 1:
                lh.row(layout, alignment='RIGHT')

            lh.label(hk)

    def filter_items(self, context, data, propname):
        pr = get_prefs()
        pie_menus = getattr(data, propname)
        helper_funcs = UI_UL_list

        filtered = []
        ordered = []

        if self.filter_name and self.use_filter_show:
            filtered = helper_funcs.filter_items_by_name(
                self.filter_name, self.bitflag_filter_item, pie_menus, "name"
            )

        if not filtered:
            filtered = [self.bitflag_filter_item] * len(pie_menus)

        if pr.use_filter:
            for idx, pm in enumerate(pie_menus):
                if not pm.filter_list(pr):
                    filtered[idx] = 0

        if self.use_filter_sort_alpha:
            ordered = helper_funcs.sort_items_by_name(pie_menus, "name")

        return filtered, ordered
