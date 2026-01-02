# operators/io.py - Import/Export operators for PME
# LAYER = "operators"
#
# Moved from: preferences.py (Phase 2-C operators reorganization)
#
# Contains:
#   - WM_OT_pm_import: Import menus from JSON/ZIP files
#   - WM_OT_pm_export: Export menus to JSON files
#   - PME_OT_backup: Backup menus
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

LAYER = "operators"

import os
import json

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, CollectionProperty, StringProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper

from ..addon import get_prefs, temp_prefs, ic_fb, ic_eye, print_exc, ADDON_PATH
from ..ui.layout import lh
from ..compatibility_fixes import fix_json, fix
from ..bl_utils import message_box
from .. import keymap_helper
from ..pme_types import Tag
from .. import constants as CC
from ..infra.io import (
    read_import_file,
    write_export_file,
    get_user_exports_dir,
)


# Global state for file dialogs
# Import starts from bundled examples (read-only)
import_filepath = os.path.join(ADDON_PATH, "examples", "examples.json")
# Export starts from user directory (initialized lazily to avoid bpy dependency at module load)
export_filepath = None  # Will be set to get_user_exports_dir() on first use


class WM_OT_pm_import(Operator, ImportHelper):
    bl_idname = "wm.pm_import"
    bl_label = "Import Menus"
    bl_description = "Import menus"
    bl_options = {'INTERNAL'}

    filename_ext = ".json"
    filepath: StringProperty(subtype='FILE_PATH', default="*.json")
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)
    filter_glob: StringProperty(default="*.json;*.zip", options={'HIDDEN'})
    directory: StringProperty(subtype='DIR_PATH')
    mode: StringProperty()
    tags: StringProperty(
        name="Tags",
        description="Assign tags (separate by comma)",
        options={'SKIP_SAVE'},
    )
    password: StringProperty(
        name="Password",
        description="Password for zip files",
        subtype='PASSWORD',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    password_visible: StringProperty(
        name="Password",
        description="Password for zip files",
        get=lambda s: s.password,
        set=lambda s, v: setattr(s, "password", v),
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    show_password: BoolProperty(options={'HIDDEN'})

    def _draw(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.operator(
            WM_OT_pm_import.bl_idname,
            "Rename if exists",
            filepath=import_filepath,
            mode='RENAME',
        )

        lh.operator(
            WM_OT_pm_import.bl_idname,
            "Skip if exists",
            filepath=import_filepath,
            mode='SKIP',
        )

        lh.operator(
            WM_OT_pm_import.bl_idname,
            "Replace if exists",
            filepath=import_filepath,
            mode='REPLACE',
        )

    def draw(self, context):
        col = self.layout.column(align=True)
        col.label(text="Assign Tags:")
        col.prop(self, "tags", text="", icon=ic_fb(False))

        col = self.layout.column(align=True)
        col.active = self.password != ""
        col.label(text="Password:")
        row = col.row(align=True)
        row.prop(
            self, "password_visible" if self.show_password else "password", text=""
        )
        row.prop(
            self, "show_password", text="", toggle=True, icon=ic_eye(self.show_password)
        )

    def import_json(self, json_data):
        if isinstance(json_data, bytes):
            json_data = json_data.decode("utf-8")
        try:
            data = json.loads(json_data)
        except:
            self.report({'WARNING'}, CC.W_JSON)
            return

        pr = get_prefs()

        menus = None
        if isinstance(data, list):
            version = "1.13.6"
            menus = data
        elif isinstance(data, dict):
            try:
                version = data["version"]
                menus = data["menus"]
            except:
                self.report({'WARNING'}, CC.W_JSON)
                return
        else:
            self.report({'WARNING'}, CC.W_JSON)
            return

        if not menus:
            return

        version = tuple(int(i) for i in version.split("."))

        new_names = {}
        if self.mode == 'RENAME':
            pm_names = [menu[0] for menu in menus]

            for name in pm_names:
                if name in pr.pie_menus:
                    new_names[name] = pr.unique_pm_name(name)

        for menu in menus:
            if self.mode == 'REPLACE':
                if menu[0] in pr.pie_menus:
                    pr.remove_pm(pr.pie_menus[menu[0]])
            elif self.mode == 'RENAME':
                if menu[0] in new_names:
                    menu[0] = new_names[menu[0]]
            elif self.mode == 'SKIP':
                if menu[0] in pr.pie_menus:
                    continue

            mode = menu[4] if len(menu) > 4 else 'PMENU'
            # pm = pr.add_pm(mode, menu[0], True)
            pm = pr.pie_menus.add()
            pm.mode = mode
            fix_json(pm, menu, version)
            pm.name = pr.unique_pm_name(menu[0] or pm.ed.default_name)
            pm.km_name = menu[1]

            n = len(menu)
            if n > 5:
                pm.data = menu[5]
            if n > 6:
                pm.open_mode = menu[6]
            if n > 7:
                pm.poll_cmd = menu[7] or CC.DEFAULT_POLL
            if n > 8:
                pm.tag = menu[8]
            if n > 9:
                pm.enabled = bool(menu[9])
            if n > 10 and pm.open_mode == 'CLICK_DRAG':
                try:
                    pm.drag_dir = menu[10] or 'ANY'
                except:
                    pm.drag_dir = 'ANY'

            if self.tags:
                tags = self.tags.split(",")
                for t in tags:
                    pm.add_tag(t)

            if menu[2]:
                try:
                    (
                        pm.key,
                        pm.ctrl,
                        pm.shift,
                        pm.alt,
                        pm.oskey,
                        pm.any,
                        pm.key_mod,
                        pm.chord,
                    ) = keymap_helper.parse_hotkey(menu[2])
                except:
                    self.report({'WARNING'}, CC.W_KEY % menu[2])

            items = menu[3]
            for i in range(0, len(items)):
                item = items[i]
                # pmi = pm.pmis[i] if mode == 'PMENU' else pm.pmis.add()
                pmi = pm.pmis.add()
                n = len(item)
                if n >= 4:
                    if (
                        self.mode == 'RENAME'
                        and item[1] == 'MENU'
                        and item[3] in new_names
                    ):
                        item[3] = new_names[item[3]]

                    try:
                        pmi.mode = item[1]
                    except:
                        pmi.mode = 'EMPTY'

                    pmi.name = item[0]
                    pmi.icon = item[2]
                    pmi.text = item[3]

                    if n >= 5:
                        pmi.flags(item[4])

                elif n == 3:
                    pmi.mode = 'EMPTY'
                    pmi.name = item[0]
                    pmi.icon = item[1]
                    pmi.text = item[2]

                elif n == 1:
                    pmi.mode = 'EMPTY'
                    pmi.text = item[0]

            if pm.mode == 'SCRIPT' and not pm.data.startswith("s?"):
                pmi = pm.pmis.add()
                pmi.text = pm.data
                pmi.mode = 'COMMAND'
                pmi.name = "Command 1"
                pm.data = pm.ed.default_pmi_data

        pms = [pr.pie_menus[menu[0]] for menu in menus]

        fix(pms, version)

        for pm in pms:
            pm.ed.init_pm(pm)

    def import_file(self, filepath):
        # Use infra.io for file reading
        result = read_import_file(
            filepath=filepath,
            addon_path=ADDON_PATH,
            password=self.password if self.password else None,
            conflict_mode=self.mode,
        )

        # Report errors
        for error in result.errors:
            if "password" in error.lower() or "runtime" in error.lower():
                message_box(error)
                return
            else:
                self.report({'WARNING'}, error)

        # Set icon refresh flag
        if result.has_icons:
            self.refresh_icons_flag = True

        # Import each JSON file
        for json_data in result.json_data_list:
            self.import_json(json_data)

    def execute(self, context):
        global import_filepath
        pr = get_prefs()
        pr.tree.lock()

        select_pm_flag = len(pr.pie_menus) == 0

        self.refresh_icons_flag = False
        try:
            # From direct file path
            if not self.files and self.filepath and os.path.isfile(self.filepath):
                self.import_file(self.filepath)
            else:
                # From file selection dialog
                for f in self.files:
                    filepath = os.path.join(self.directory, f.name)
                    if os.path.isfile(filepath):
                        self.import_file(filepath)
        except:
            raise
        finally:
            pr.tree.unlock()

        import_filepath = self.filepath

        temp_prefs().init_tags()
        # Lazy import to avoid circular dependency
        from ..preferences import PME_UL_pm_tree
        PME_UL_pm_tree.update_tree()

        if select_pm_flag:
            idx = pr.active_pie_menu_idx
            pr.active_pie_menu_idx = -1
            pr.active_pie_menu_idx = idx

        if self.refresh_icons_flag:
            bpy.ops.pme.icons_refresh()

        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.mode:
            context.window_manager.popup_menu(self._draw, title=self.bl_description)
            return {'FINISHED'}

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_pm_export(Operator, ExportHelper):
    bl_idname = "wm.pm_export"
    bl_label = "Export Menus"
    bl_description = "Export menus"
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    filename_ext = ".json"
    filepath: StringProperty(subtype='FILE_PATH', default="*.json")
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    mode: StringProperty(options={'SKIP_SAVE'})
    tag: StringProperty(options={'SKIP_SAVE'})
    export_tags: BoolProperty(
        name="Export Tags",
        description="Export tags",
        default=True,
        options={'SKIP_SAVE'},
    )
    compat_json: BoolProperty(
        name="Export Compatible JSON",
        description="Export without PME-F extensions (no enabled/drag_dir; CLICK->PRESS, CLICK_DRAG->TWEAK)",
        default=False,
        options={'SKIP_SAVE'},
    )  # Compat
    mark_schema: BoolProperty(
        name="Mark Schema (PME-F)",
        description="Add 'schema': 'PME-F' to top-level JSON when not compatible",
        default=True,
        options={'SKIP_SAVE'},
    )  # Compat

    def _draw(self, menu, context):
        global export_filepath
        # Initialize export_filepath lazily (first time only)
        if export_filepath is None:
            export_filepath = os.path.join(
                get_user_exports_dir(create=True), "my_pie_menus.json"
            )

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.operator(
            WM_OT_pm_export.bl_idname,
            "All Menus",
            'ALIGN_JUSTIFY',
            filepath=export_filepath,
            mode='ALL',
        )

        lh.operator(
            WM_OT_pm_export.bl_idname,
            "All Enabled Menus",
            'SYNTAX_ON',
            filepath=export_filepath,
            mode='ENABLED',
        )

        lh.operator(
            WM_OT_pm_export.bl_idname,
            "Selected Menu",
            'REMOVE',
            filepath=export_filepath,
            mode='ACTIVE',
        )

        if temp_prefs().tags:
            lh.operator(
                WM_OT_pm_export.bl_idname,
                "By Tag",
                filepath=export_filepath,
                mode='TAG',
            )

        lh.sep()

        lh.layout.prop(get_prefs(), "auto_backup")

        lh.operator(PME_OT_backup.bl_idname, "Backup Now", 'FILE_HIDDEN')

    def check(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_tags")
        layout.prop(self, "compat_json")
        row = layout.row(align=True)
        row.active = not self.compat_json
        row.prop(self, "mark_schema")

    def execute(self, context):
        global export_filepath

        if not self.filepath:
            return {'CANCELLED'}

        data = get_prefs().get_export_data(
            export_tags=self.export_tags, mode=self.mode, tag=self.tag,
            compat=self.compat_json, mark_schema=self.mark_schema
        )

        try:
            # Use infra.io for file writing
            write_export_file(self.filepath, data)
        except Exception:
            print_exc()
            return {'CANCELLED'}

        # Update filepath (write_export_file may have added .json extension)
        if not self.filepath.endswith(".json"):
            self.filepath += ".json"
        export_filepath = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.mode:
            context.window_manager.popup_menu(self._draw, title=self.bl_description)
            return {'FINISHED'}

        elif self.mode == 'TAG' and not self.tag:
            Tag.popup_menu(self.bl_idname, "Export by Tag", invoke=True, mode=self.mode)
            return {'FINISHED'}

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PME_OT_backup(Operator):
    bl_idname = "pme.backup"
    bl_label = "Backup Menus"
    bl_description = "Backup PME menus"

    def invoke(self, context, event):
        get_prefs().backup_menus(operator=self)
        return {'FINISHED'}
