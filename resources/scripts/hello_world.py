# Open a pop-up message

# Usage 1 (Command tab):
# execute_script("scripts/menu.py", msg="My Message")

# Usage 2 (Command tab):
# from .scripts.menu import say_hello; say_hello("My Message")

import bpy


def say_hello(msg):
    def draw(menu, _context):
        menu.layout.label(text=msg, icon='BLENDER')

    bpy.context.window_manager.popup_menu(draw, title="My Popup")


msg = locals().get("kwargs", {}).get("msg", "Hello World!")
say_hello(msg)
