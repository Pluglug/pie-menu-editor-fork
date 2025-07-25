# Do NOT edit this file. All changes will be lost


def ups():
    return bpy.context.tool_settings.unified_paint_settings


def brush(use_ups=False):
    """
    Return brush settings.
    Property Tab Usage:
    brush(ups().use_unified_size).size
    """
    return ups() if use_ups else getattr(paint_settings(), "brush", None)


def setattr_(object, name, value):
    setattr(object, name, value)
    return True


def try_setattr(object, name, value):
    try:
        setattr(object, name, value)
    except:
        pass

    return True


def event_mods(event):
    """
    Return key modifiers (e.g. Ctrl+Shift, Alt+OSKey, None).
    Command Tab Usage:
    Call Stack Key's slot depending on key modifiers:
    open_menu("Stack Key", event_mods(E))
    """
    mods = "+".join(
        m for m in ["Ctrl", "Shift", "Alt", "OSKey"]
        if getattr(event, m.lower(), False))

    return mods or "None"


def raise_error(message):
    bpy.ops.pme.message_box(message=message, icon='ERROR')
    raise Exception(message)


pme.context.add_global("ups", ups)
pme.context.add_global("brush", brush)
pme.context.add_global("setattr", setattr_)
pme.context.add_global("try_setattr", try_setattr)
pme.context.add_global("event_mods", event_mods)
pme.context.add_global("raise_error", raise_error)
