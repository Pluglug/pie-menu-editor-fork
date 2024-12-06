import sys
import inspect
import importlib

import bpy
import _bpy
from bpy.app.handlers import persistent

from . import property_utils
from . import pme
from . import compatibility_fixes
from . import addon
from .debug_utils import *
from .addon import prefs, temp_prefs


module_names = (
    "addon",
    "bl_utils",
    "c_utils",
    "collection_utils",
    "compatibility_fixes",
    "constants",
    "debug_utils",
    "extra_operators",
    "keymap_helper",
    "layout_helper",
    "macro_utils",
    "modal_utils",
    "operator_utils",
    "operators",
    "overlay",
    "panel_utils",
    "pme",
    "previews_helper",
    "property_utils",
    "screen_utils",
    "selection_state",
    "types",
    "ui_utils",
    "ui",
    "utils",

    "editor.ed_base",
    "editor.ed_hpanel_group",
    "editor.ed_macro",
    "editor.ed_menu",
    "editor.ed_modal",
    "editor.ed_panel_group",
    "editor.ed_pie_menu",
    "editor.ed_popup",
    "editor.ed_property",
    "editor.ed_stack_key",
    "editor.ed_sticky_key",

    # NOTE: Must be last
    "preferences"
)
if not bpy.app.background:
    modules = []
    for module_name in module_names:
        if module_name in locals():
            modules.append(
                importlib.reload(locals()[module_name])
            )
        else:
            modules.append(
                importlib.import_module(f".{module_name}", __package__)
            )


tmp_data       = None
re_enable_data = None
tmp_filepath   = None
invalid_prefs  = None
timer          = None


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
    pme.context.add_global(
        "FloatVectorProperty", bpy.props.FloatVectorProperty)

    for k, v in globals().items():
        if k.startswith("__"):
            pme.context.add_global(k, v)

    register_module()

    pr = prefs()
    global re_enable_data
    if re_enable_data is not None:
        if len(pr.pie_menus) == 0 and re_enable_data:
            property_utils.from_dict(pr, re_enable_data)
        re_enable_data.clear()
        re_enable_data = None

    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()

    if pr.missing_kms:
        DBG_INIT and logi(f"{len(pr.missing_kms)} missing keymaps")
        bpy.ops.pme.wait_keymaps(
            {'window': bpy.context.window_manager.windows[0]}, 'INVOKE_DEFAULT'
        )
    else:
        compatibility_fixes.fix()


def get_classes():
    ret = set()
    bpy_struct = bpy.types.bpy_struct
    cprop = bpy.props.CollectionProperty
    pprop = bpy.props.PointerProperty
    pdtype = getattr(bpy.props, "_PropertyDeferred", tuple)
    mems = set()
    mem_data = []
    for mod in modules:
        for _name, mem in inspect.getmembers(mod):
            if inspect.isclass(mem) \
            and issubclass(mem, bpy_struct) \
            and mem not in mems:
                mems.add(mem)
                classes = []

                if hasattr(mem, "__annotations__"):
                    for _pname, pd in mem.__annotations__.items():
                        if not isinstance(pd, pdtype):
                            continue

                        pfunc = getattr(pd, "function", None) or pd[0]
                        pkeywords = pd.keywords if hasattr(pd, "keywords") \
                            else pd[1]
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
        while mem_data:
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


def init_keymaps():
    DBG_INIT and logi("Waiting Keymaps")

    pr = prefs()
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
    pr = prefs()
    if not pr.missing_kms or timer.elapsed_time > 10:
        timer.cancel()
        timer = None

        compatibility_fixes.fix()


@persistent
def load_post_context(_):
    bpy.app.handlers.load_post.remove(load_post_context)
    on_context()


@persistent
def load_pre_handler(_):
    DBG_INIT and logh(f"Load Pre ({bpy.data.filepath})")

    global tmp_data
    tmp_data = property_utils.to_dict(prefs())

    global tmp_filepath
    tmp_filepath = bpy.data.filepath
    if not tmp_filepath:
        tmp_filepath = "__unsaved__"


@persistent
def load_post_handler(_):
    DBG_INIT and logh(f"Load Post ({bpy.data.filepath})")

    global tmp_data
    if tmp_data is None:
        DBG_INIT and logw("Skip")
        return

    pr = prefs()
    if not bpy.data.filepath:
        property_utils.from_dict(pr, tmp_data)

    tmp_data = None

    if pr.missing_kms:
        bpy.ops.pme.wait_keymaps(
            {'window': bpy.context.window_manager.windows[0]}, 'INVOKE_DEFAULT'
        )
    else:
        temp_prefs().init_tags()
        pr.tree.update()


class PME_OT_wait_context(bpy.types.Operator):
    bl_idname = "pme.wait_context"
    bl_label = "Internal (PME)"
    bl_options = {'INTERNAL'}

    instances = []
    timer     = None
    cancelled = False

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
        self.timer = context.window_manager.event_timer_add(
            0.01, window=context.window)
        return {'RUNNING_MODAL'}


class PME_OT_wait_keymaps(bpy.types.Operator):
    bl_idname = "pme.wait_keymaps"
    bl_label = "Internal (PME)"
    bl_options = {'INTERNAL'}

    instances = []
    timer     = None
    cancelled = False

    def remove_timer(self):
        if self.timer:
            bpy.context.window_manager.event_timer_remove(self.timer)
            self.timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            init_keymaps()

            pr = prefs()
            if not pr.missing_kms or self.timer.time_duration > 5:
                self.remove_timer()
                self.instances.remove(self)
                if self.cancelled:
                    return {'CANCELLED'}

                DBG_INIT and logi(f"{len(pr.missing_kms)} Missing Keymaps")

                if pr.missing_kms:
                    print(
                        "PME: Some hotkeys cannot be registered. "
                        "Please restart Blender")

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
        self.timer = context.window_manager.event_timer_add(
            0.2, window=context.window
        )
        return {'RUNNING_MODAL'}


def register_module():
    if hasattr(bpy.utils, "register_module"):
        bpy.utils.register_module(__name__)
    else:
        for cls in get_classes():
            bpy.utils.register_class(cls)


def unregister_module():
    if hasattr(bpy.utils, "unregister_module"):
        bpy.utils.unregister_module(__name__)
    else:
        for cls in get_classes():
            bpy.utils.unregister_class(cls)


def register():
    if bpy.app.background:
        return

    DBG_INIT and logh("PME Register")

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
            "PMEPreferences",
            (InvalidPMEPreferences, bpy.types.AddonPreferences), {}
        )
        bpy.utils.register_class(invalid_prefs)


def unregister():
    if bpy.app.background:
        return

    if invalid_prefs:
        bpy.utils.unregister_class(invalid_prefs)
        return

    DBG_INIT and logh("PME Unregister")

    for op in PME_OT_wait_context.instances:
        op.cancelled = True

    for op in PME_OT_wait_keymaps.instances:
        op.cancelled = True

    global timer
    if timer:
        timer.cancel()
        timer = None
        return

    global re_enable_data
    re_enable_data = property_utils.to_dict(prefs())

    for mod in modules:
        if hasattr(mod, "unregister"):
            mod.unregister()

    if hasattr(bpy.types.WindowManager, "pme"):
        delattr(bpy.types.WindowManager, "pme")

    if load_pre_handler in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(load_pre_handler)

    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)

    if load_post_context in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_context)

    unregister_module()
