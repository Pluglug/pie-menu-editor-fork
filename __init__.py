bl_info = {
    "name": "Pie Menu Editor Fork (PME2 Experimental)",
    "author": "pluglug (maintainer), original author: roaoao",
    "version": (2, 0, 0, 4),
    "blender": (4, 5, 0),
    "warning": "Alpha build. Use in separate portable Blender. May break PME prefs.",
    "tracker_url": "https://github.com/Pluglug/pie-menu-editor-fork/issues",
    "doc_url": "https://pluglug.github.io/pme-docs",
    "category": "User Interface",
}

# TODO: use_reload pattern disabled due to C-level crashes with complex user configs
# See: https://github.com/Pluglug/pie-menu-editor-fork/issues/67
# The pattern itself works, but exposes latent issues with:
#   - UserProperties re-registration timing
#   - CUSTOM script execution with stale Blender state
# Re-enable after Phase 3 lifecycle work is complete.
use_reload = False
# use_reload = "addon" in locals()
# if use_reload:
#     import importlib
#     importlib.reload(locals()["addon"])
#     del importlib

import bpy
import _bpy
from bpy.app.handlers import persistent
from bpy.app import version as APP_VERSION
import sys
import inspect
from .infra.debug import *

MODULES = (
    "addon",
    "pme",
    "c_utils",
    "previews_helper",
    "constants",
    "utils",
    "debug_utils",
    "bl_utils",
    "compatibility_fixes",
    "operator_utils",
    "property_utils",
    "layout_helper",
    "overlay",
    "modal_utils",
    "macro_utils",
    "ui",
    "panel_utils",
    "screen_utils",
    "selection_state",
    "keymap_helper",
    "collection_utils",
    "operators",
    "extra_operators",
    "ui_utils",
    "pme_types",
    "ed_base",
    "ed_pie_menu",
    "ed_menu",
    "ed_popup",
    "ed_stack_key",
    "ed_sticky_key",
    "ed_macro",
    "ed_modal",
    "ed_panel_group",
    "ed_hpanel_group",
    "ed_property",
    "preferences",
)

CLASSES = []


# ======================================================
# Legacy Loader (MODULES + get_classes)
# ======================================================

def legacy_get_classes():
    """Get all bpy_struct classes from MODULES for legacy registration."""
    ret = set()
    bpy_struct = bpy.types.bpy_struct
    cprop = bpy.props.CollectionProperty
    pprop = bpy.props.PointerProperty
    pdtype = getattr(bpy.props, "_PropertyDeferred", tuple)
    mems = set()
    mem_data = []
    for mod in MODULES:
        mod = sys.modules["%s.%s" % (__name__, mod)]
        # mod = sys.modules[mod]
        for name, mem in inspect.getmembers(mod):
            if inspect.isclass(mem) and issubclass(mem, bpy_struct) and mem not in mems:

                mems.add(mem)
                classes = []

                if hasattr(mem, "__annotations__"):
                    for pname, pd in mem.__annotations__.items():
                        if not isinstance(pd, pdtype):
                            continue

                        pfunc = getattr(pd, "function", None) or pd[0]
                        pkeywords = pd.keywords if hasattr(pd, "keywords") else pd[1]
                        if pfunc is cprop or pfunc is pprop:
                            classes.append(pkeywords["type"])

                if not classes:
                    ret.add(mem)
                else:
                    mem_data.append(dict(mem=mem, classes=classes))

    mems.clear()

    ret_post = []
    if mem_data:
        mem_data_len = -1
        while len(mem_data):
            if len(mem_data) == mem_data_len:
                for data in mem_data:
                    ret_post.append(data["mem"])
                break

            new_mem_data = []
            for data in mem_data:
                add = True
                for cls in data["classes"]:
                    if cls not in ret and cls not in ret_post:
                        add = False
                        break

                if add:
                    ret_post.append(data["mem"])
                else:
                    new_mem_data.append(data)

            mem_data_len = len(mem_data)
            mem_data.clear()
            mem_data = new_mem_data

    ret = list(ret)
    ret.extend(ret_post)
    return ret


def legacy_register_module():
    """Register all classes using legacy MODULES approach."""
    if hasattr(bpy.utils, "register_module"):
        bpy.utils.register_module(__name__)
    else:
        for cls in legacy_get_classes():
            bpy.utils.register_class(cls)


def legacy_unregister_module():
    """Unregister all classes using legacy MODULES approach."""
    if hasattr(bpy.utils, "unregister_module"):
        bpy.utils.unregister_module(__name__)
    else:
        for cls in legacy_get_classes():
            bpy.utils.unregister_class(cls)


# ======================================================
# New Loader (init_addon + register_modules)
# ======================================================

# Module patterns for init_addon
# These patterns define which modules are collected and loaded by the new loader.
PME2_MODULE_PATTERNS = [
    # Layer packages
    "core",
    "core.*",
    "infra",
    "infra.*",
    "ui",
    "ui.*",
    "editors",
    "editors.*",
    # Core modules (without package)
    # NOTE: "addon" is intentionally excluded - it's the bootstrap module
    # that is already loaded/reloaded in __init__.py's use_reload block.
    # Reloading it again in init_addon() would reset VERSION to None.
    "pme",
    "c_utils",
    "utils",
    "previews_helper",
    "property_utils",
    "overlay",
    "modal_utils",
    "macro_utils",
    "selection_state",
    "keymap_helper",
    "operator_utils",
    "compatibility_fixes",
    "pme_types",
    # Operators
    "operators",
    "operators.*",
    "extra_operators",
    # Preferences
    "preferences",
    # Legacy wrappers (for backward compat during transition)
    "constants",
    "debug_utils",
    "bl_utils",
    "layout_helper",
    "screen_utils",
    "collection_utils",
    "panel_utils",
    "ui_utils",
    "ed_base",
    "ed_pie_menu",
    "ed_menu",
    "ed_popup",
    "ed_stack_key",
    "ed_sticky_key",
    "ed_macro",
    "ed_modal",
    "ed_panel_group",
    "ed_hpanel_group",
    "ed_property",
]


def new_register_modules():
    """Register modules using init_addon approach."""
    from .infra.debug import dbg_log, dbg_scope

    dbg_log("deps", f"Using init_addon loader (use_reload={use_reload})", location="__init__.new_register_modules")

    # Initialize addon module system
    with dbg_scope("profile", "new_register_modules.init_addon", location="__init__"):
        addon.init_addon(
            module_patterns=PME2_MODULE_PATTERNS,
            use_reload=use_reload,
            version=bl_info["version"][:3],
            bl_version=bl_info["blender"],
        )

    # Register all classes and call module register() functions
    with dbg_scope("profile", "new_register_modules.register", location="__init__"):
        addon.register_modules()

    # Deferred initialization for editor-dependent code
    # Must run after all Editor() instances are registered
    with dbg_scope("profile", "new_register_modules.deferred_init", location="__init__"):
        from .preferences import deferred_init
        deferred_init()


def new_unregister_modules():
    """Unregister modules using init_addon approach."""
    addon.unregister_modules()


# Backward compatibility aliases
get_classes = legacy_get_classes
register_module = legacy_register_module
unregister_module = legacy_unregister_module


if not bpy.app.background:
    import importlib

    # Track reload activity for debugging unexpected reloads
    _reload_count = 0
    _import_count = 0

    for mod in MODULES:
        if mod in locals():
            try:
                importlib.reload(locals()[mod])
                _reload_count += 1
                continue
            except:
                pass

        importlib.import_module("pie_menu_editor." + mod)
        _import_count += 1

    # Log reload activity (helps detect unexpected module reloads)
    if _reload_count > 0:
        logw(f"PME: Module-level reload detected: {_reload_count} reloaded, {_import_count} imported")
    else:
        DBG_INIT and logi(f"PME: Module-level import: {_import_count} modules imported (no reloads)")

    from .addon import get_prefs, temp_prefs
    from . import property_utils
    from . import pme
    from . import compatibility_fixes
    from . import addon

    addon.VERSION = bl_info["version"][:3]
    addon.BL_VERSION = bl_info["blender"]


tmp_data = None
re_enable_data = None
tmp_filepath = None
invalid_prefs = None
timer = None


@persistent
def load_pre_handler(_):
    DBG_INIT and logh("Load Pre (%s)" % bpy.data.filepath)

    # FIXME: Use tmp_data only for legacy (<5.0.0).
    # Reason:
    # - to_dict/from_dict based restore caused data drift on 5.x
    # - In modern Blender, prefs usually persist across load; this path is likely unnecessary
    # - Keep 5.0+ path off and observe for a while
    if APP_VERSION < (5, 0, 0):
        global tmp_data
        tmp_data = property_utils.to_dict(get_prefs())

    global tmp_filepath
    tmp_filepath = bpy.data.filepath
    if not tmp_filepath:
        tmp_filepath = "__unsaved__"


@persistent
def load_post_handler(filepath):
    DBG_INIT and logh("Load Post (%s)" % filepath)

    pr = get_prefs()

    # FIXME: Legacy tmp_data restore (<5.0.0) is kept; 5.0+ path stays disabled.
    # Reason: to_dict/from_dict can introduce drift on 5.x; we'll observe for now.
    if APP_VERSION < (5, 0, 0):
        global tmp_data
        if tmp_data is None:
            DBG_INIT and logw("Skip")
            return
        if not bpy.data.filepath:
            property_utils.from_dict(pr, tmp_data)
        tmp_data = None

    if pr.missing_kms:
        logw(f"Missing Keymaps: {pr.missing_kms}")
        with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]):
            bpy.ops.pme.wait_keymaps('INVOKE_DEFAULT')
    else:
        temp_prefs().init_tags()
        pr.tree.update()


def on_context():
    DBG_INIT and logi("On Context")

    bpy.app.handlers.load_pre.append(load_pre_handler)
    bpy.app.handlers.load_post.append(load_post_handler)

    pme.context.add_global("D", bpy.data)
    pme.context.add_global("T", bpy.types)
    pme.context.add_global("O", bpy.ops)
    pme.context.add_global("P", bpy.props)
    pme.context.add_global("sys", sys)
    pme.context.add_global("BoolProperty", bpy.props.BoolProperty)
    pme.context.add_global("IntProperty", bpy.props.IntProperty)
    pme.context.add_global("FloatProperty", bpy.props.FloatProperty)
    pme.context.add_global("StringProperty", bpy.props.StringProperty)
    pme.context.add_global("EnumProperty", bpy.props.EnumProperty)
    pme.context.add_global("CollectionProperty", bpy.props.CollectionProperty)
    pme.context.add_global("PointerProperty", bpy.props.PointerProperty)
    pme.context.add_global("FloatVectorProperty", bpy.props.FloatVectorProperty)

    for k, v in globals().items():
        if k.startswith("__"):
            pme.context.add_global(k, v)

    # Branch based on loader flag
    if addon.USE_PME2_LOADER:
        # New loader: init_addon handles class registration and module.register() calls
        DBG_INIT and logi("Using PME2 Loader (init_addon)")
        new_register_modules()
    else:
        # Legacy loader: manual class registration + module.register() loop
        DBG_INIT and logi("Using Legacy Loader (MODULES)")
        legacy_register_module()

        for mod in MODULES:
            m = sys.modules["%s.%s" % (__name__, mod)]
            if hasattr(m, "register"):
                m.register()

    pr = get_prefs()

    if APP_VERSION < (5, 0, 0):
        global re_enable_data
        if re_enable_data is not None:
            if len(pr.pie_menus) == 0 and re_enable_data:
                property_utils.from_dict(pr, re_enable_data)
            re_enable_data.clear()
            re_enable_data = None

    if pr.missing_kms:
        logw(f"Missing Keymaps: {pr.missing_kms}")
        with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]):
            bpy.ops.pme.wait_keymaps('INVOKE_DEFAULT')

    else:
        compatibility_fixes.fix()


def init_keymaps():
    DBG_INIT and logi("Waiting Keymaps")

    pr = get_prefs()
    if not bpy.context.window_manager.keyconfigs.user:
        return

    keymaps = bpy.context.window_manager.keyconfigs.user.keymaps
    kms_to_remove = []
    for km in pr.missing_kms.keys():
        if km in keymaps:
            kms_to_remove.append(km)

    for km in kms_to_remove:
        pm_names = pr.missing_kms[km]
        for pm_name in pm_names:
            pr.pie_menus[pm_name].register_hotkey([km])
        pr.missing_kms.pop(km, None)


def on_timer():
    init_keymaps()

    global timer
    pr = get_prefs()
    if not pr.missing_kms or timer.elapsed_time > 10:
        timer.cancel()
        timer = None

        compatibility_fixes.fix()


@persistent
def load_post_context(scene):
    bpy.app.handlers.load_post.remove(load_post_context)
    on_context()


class PME_OT_wait_context(bpy.types.Operator):
    bl_idname = "pme.wait_context"
    bl_label = "Internal (PME)"
    bl_options = {'INTERNAL'}

    instances = []

    def remove_timer(self):
        if self.timer:
            bpy.context.window_manager.event_timer_remove(self.timer)
            self.timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            self.remove_timer()
            self.instances.remove(self)
            if self.cancelled:
                return {'CANCELLED'}

            on_context()
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def cancel(self, context):
        try:
            self.remove_timer()
            self.instances.remove(self)
        except:
            pass

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        self.cancelled = False
        self.instances.append(self)
        context.window_manager.modal_handler_add(self)
        self.timer = context.window_manager.event_timer_add(0.01, window=context.window)
        return {'RUNNING_MODAL'}


class PME_OT_wait_keymaps(bpy.types.Operator):
    bl_idname = "pme.wait_keymaps"
    bl_label = "Internal (PME)"
    bl_options = {'INTERNAL'}

    instances = []

    def remove_timer(self):
        if self.timer:
            bpy.context.window_manager.event_timer_remove(self.timer)
            self.timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            init_keymaps()

            pr = get_prefs()
            if not pr.missing_kms or self.timer.time_duration > 5:
                self.remove_timer()
                self.instances.remove(self)
                if self.cancelled:
                    return {'CANCELLED'}

                DBG_INIT and logi("%d Missing Keymaps" % len(pr.missing_kms))

                if pr.missing_kms:
                    print(
                        "PME: Some hotkeys cannot be registered. "
                        "Please restart Blender"
                    )

                temp_prefs().init_tags()
                pr.tree.update()

                compatibility_fixes.fix()
                return {'FINISHED'}

            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def cancel(self, context):
        try:
            self.remove_timer()
            self.instances.remove(self)
        except:
            pass
        DBG_INIT and logw("PME_OT_wait_keymaps Cancelled")

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        self.cancelled = False
        self.instances.append(self)
        context.window_manager.modal_handler_add(self)
        self.timer = context.window_manager.event_timer_add(0.2, window=context.window)
        return {'RUNNING_MODAL'}


_register_count = 0  # Track register calls for debugging

def register():
    global _register_count
    _register_count += 1

    if bpy.app.background:
        return

    DBG_INIT and logh("PME Register")

    # Detect multiple register calls (shouldn't happen in normal operation)
    if _register_count > 1:
        logw(f"PME: register() called {_register_count} times - possible unexpected reload")

    if addon.check_bl_version():
        if _bpy.context.window:
            bpy_context = bpy.context
            bpy.context = _bpy.context
            try:
                bpy.utils.register_class(PME_OT_wait_context)
            except:
                pass

            bpy.ops.pme.wait_context('INVOKE_DEFAULT')
            bpy.context = bpy_context
        else:
            try:
                bpy.utils.register_class(PME_OT_wait_keymaps)
            except:
                pass

            bpy.app.handlers.load_post.append(load_post_context)

    else:
        global invalid_prefs
        from .preferences import InvalidPMEPreferences

        invalid_prefs = type(
            "PMEPreferences", (InvalidPMEPreferences, bpy.types.AddonPreferences), {}
        )
        bpy.utils.register_class(invalid_prefs)


_unregister_count = 0  # Track unregister calls for debugging

def unregister():
    global _unregister_count, _register_count
    _unregister_count += 1

    if bpy.app.background:
        return

    if invalid_prefs:
        bpy.utils.unregister_class(invalid_prefs)
        return

    DBG_INIT and logh("PME Unregister")

    # Detect mismatched register/unregister calls
    if _unregister_count > _register_count:
        logw(f"PME: unregister() called more times than register() - register={_register_count}, unregister={_unregister_count}")

    for op in PME_OT_wait_context.instances:
        op.cancelled = True

    for op in PME_OT_wait_keymaps.instances:
        op.cancelled = True

    global timer
    if timer:
        timer.cancel()
        timer = None
        return

    if APP_VERSION < (5, 0, 0):
        global re_enable_data
        re_enable_data = property_utils.to_dict(get_prefs())

    # Branch based on loader flag
    if addon.USE_PME2_LOADER:
        # New loader: unregister_modules handles everything
        DBG_INIT and logi("Unregistering with PME2 Loader")
        new_unregister_modules()
    else:
        # Legacy loader: manual module.unregister() loop + class unregistration
        DBG_INIT and logi("Unregistering with Legacy Loader")
        for mod in reversed(MODULES):
            m = sys.modules["%s.%s" % (__name__, mod)]
            if hasattr(m, "unregister"):
                m.unregister()
        legacy_unregister_module()

    # Common cleanup (regardless of loader)
    if hasattr(bpy.types.WindowManager, "pme"):
        delattr(bpy.types.WindowManager, "pme")

    if load_pre_handler in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(load_pre_handler)

    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)

    if load_post_context in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_context)
