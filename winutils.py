import os
import ctypes
# import re
# import unicodedata

from ctypes import (
    wintypes,
    byref,
    # c_int,
    c_long,
    c_char_p,
    Structure
)


########################################################
# Basic Win32 constants, structs, etc.

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


# Common flags
NULL            = 0x0
SWP_NOSIZE      = 0x0001
SWP_NOMOVE      = 0x0002
SWP_NOZORDER    = 0x0004
SWP_SHOWWINDOW  = 0x0040

GWL_EXSTYLE     = -20
WS_EX_LAYERED   = 0x00080000
LWA_ALPHA       = 0x00000002
LWA_COLORKEY    = 0x00000001

SW_FORCEMINIMIZE= 11
SW_MINIMIZE     = 6
SW_RESTORE      = 9
SW_SHOWMAXIMIZED= 3
SW_SHOWNORMAL   = 1

HWND_TOPMOST    = -1
HWND_NOTOPMOST  = -2


# Transparency
def RGB(r, g, b):
    """Convert (r,g,b) in 0..255 to COLORREF(DWORD)."""
    return (b << 16) | (g << 8) | r


# POINT struct for cursor coords
class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


# Callback signature for EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,  # return type
    wintypes.HWND,  # hWnd
    wintypes.LPARAM # lParam
)


########################################################
# Helpers

active_process_id = os.getpid()  # Current Python process ID


def _check_bool(result, func, args):
    """Helper to check if a WinAPI function returned a failing boolean."""
    if not result:
        err = ctypes.get_last_error()
        if err != 0:
            raise ctypes.WinError(err)
    return result


# Optionally attach custom error checker to some functions
user32.SetWindowPos.errcheck = _check_bool


########################################################
# Mouse

def get_mouse_position():
    """Get current mouse (cursor) position (x, y) in screen coordinates."""
    pos = POINT()
    user32.GetCursorPos(byref(pos))
    return (pos.x, pos.y)


########################################################
# Window Visibility / Minimize / Restore

def show_window(hWnd, show=True):
    """
    Restore or minimize the given window handle.
    :param hWnd: Window handle
    :param show: True -> restore, False -> minimize
    """
    cmd = SW_RESTORE if show else SW_MINIMIZE
    user32.ShowWindow(hWnd, cmd)

def is_window_minimized(hWnd):
    """
    Check if the window is minimized (iconic).
    """
    return bool(user32.IsIconic(hWnd))

def is_window_visible(hWnd):
    """
    Check if the window is visible.
    """
    return bool(user32.IsWindowVisible(hWnd))


########################################################
# Enumerate Windows

def get_active_window():
    """
    Get the handle of the currently active (foreground) window.
    """
    return user32.GetForegroundWindow()

def get_all_windows(filter_pid=None):
    """
    Enumerate all top-level windows on the desktop.
    :param filter_pid: If set, only return windows belonging to that process ID.
    """
    handles = []

    def callback(hWnd, lParam):
        if filter_pid is None:
            handles.append(hWnd)
        else:
            pid = get_window_process_id(hWnd)
            if pid == filter_pid:
                handles.append(hWnd)
        return True

    cb = WNDENUMPROC(callback)
    user32.EnumWindows(cb, 0)
    return handles

def get_window_process_id(hWnd):
    """
    Get the process ID owning this window.
    """
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hWnd, byref(pid))
    return pid.value

def get_window_text(hWnd):
    """
    Get the window title (Unicode).
    """
    length = user32.GetWindowTextLengthW(hWnd)
    if length == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hWnd, buffer, length + 1)
    return buffer.value

def set_window_text(hWnd, text):
    """
    Set the window title (ANSI version).
    """
    user32.SetWindowTextA(hWnd, c_char_p(text.encode('utf-8')))


########################################################
# Blender-specific convenience

def get_blender_windows():
    """
    Attempt to return all visible top-level windows owned by *this* Blender process.
    In many cases, GHOST creates multiple windows (main, prefs, popups, etc.).
    """
    all_wins = get_all_windows(filter_pid=active_process_id)
    blender_wins = []
    for w in all_wins:
        title = get_window_text(w)
        # Heuristic: skip the console window titled "blender.exe" or empty
        # You can refine this condition as needed
        if not title.lower().startswith("blender.exe") and title.strip() != "":
            if is_window_visible(w):
                blender_wins.append(w)
    return blender_wins

def get_blender_console():
    """
    Return the console window for the current Blender process (if any).
    """
    all_wins = get_all_windows(filter_pid=active_process_id)
    for w in all_wins:
        title = get_window_text(w)
        if title.lower().startswith("blender.exe"):
            return w
    return None


########################################################
# Position / Size

def set_window_geometry(hWnd, x=None, y=None, width=None, height=None):
    """
    Set the location and/or size of the given window. If x,y or width,height is None, we skip it.
    """
    flags = SWP_SHOWWINDOW | SWP_NOZORDER

    # If we skip location
    if x is None or y is None:
        flags |= SWP_NOMOVE
        X, Y = 0, 0
    else:
        X, Y = int(x), int(y)

    # If we skip size
    if width is None or height is None:
        flags |= SWP_NOSIZE
        W, H = 0, 0
    else:
        W, H = int(width), int(height)

    # This will raise an exception if it fails
    user32.SetWindowPos(hWnd, NULL, X, Y, W, H, flags)

def get_window_geometry(hWnd):
    """
    Get window position and size in screen coordinates.
    Returns (x, y, width, height).
    """
    rect = wintypes.RECT()
    user32.GetWindowRect(hWnd, byref(rect))
    x, y = rect.left, rect.top
    width, height = rect.right - rect.left, rect.bottom - rect.top
    return (x, y, width, height)


########################################################
# Transparency

def set_window_transparency(hWnd, percent=50):
    """
    Set the window transparency (alpha), 0..100% (0=fully transparent, 100=fully opaque).
    Minimal practical value is around 10 to avoid glitching.
    """
    if percent < 0:
        percent = 0
    elif percent > 100:
        percent = 100

    # Convert to 0..255
    alpha_byte = int(255 * (percent / 100.0))

    # Set WS_EX_LAYERED style
    style = user32.GetWindowLongA(hWnd, GWL_EXSTYLE)
    user32.SetWindowLongA(hWnd, GWL_EXSTYLE, style | WS_EX_LAYERED)

    # Apply alpha
    user32.SetLayeredWindowAttributes(hWnd, 0, alpha_byte, LWA_ALPHA)

def get_window_transparency(hWnd):
    """
    Return approximate transparency level (0..100).
    """
    key_color = wintypes.DWORD(0)
    current_alpha = wintypes.BYTE(0)
    flags = wintypes.DWORD(0)

    # int GetLayeredWindowAttributes(HWND hwnd, COLORREF *pcrKey, BYTE *pbAlpha, DWORD *pdwFlags)
    # We pass pointers. On success -> returns nonzero
    ret = user32.GetLayeredWindowAttributes(hWnd,
                                           byref(key_color),
                                           byref(current_alpha),
                                           byref(flags))
    if not ret:
        # If window not layered or call failed, assume 100
        return 100

    return int((current_alpha.value / 255.0) * 100)


def set_window_chromakey(hWnd, color=(0.0, 1.0, 0.0)):
    """
    Make a certain RGB color fully transparent (chroma key).
    Color must be in 0..1 range for each component (R, G, B).
    """
    # Convert float to 0..255 integer
    r = int(color[0] * 255)
    g = int(color[1] * 255)
    b = int(color[2] * 255)
    colorref = RGB(r, g, b)

    style = user32.GetWindowLongA(hWnd, GWL_EXSTYLE)
    user32.SetWindowLongA(hWnd, GWL_EXSTYLE, style | WS_EX_LAYERED)

    # Use LWA_COLORKEY
    user32.SetLayeredWindowAttributes(hWnd, colorref, 0, LWA_COLORKEY)

def is_window_chromakeyed(hWnd):
    """
    Check if the window has LWA_COLORKEY enabled.
    There's no direct API to retrieve the color key easily, so we check the flags.
    """
    key_color = wintypes.DWORD(0)
    current_alpha = wintypes.BYTE(0)
    flags = wintypes.DWORD(0)

    ret = user32.GetLayeredWindowAttributes(hWnd, byref(key_color), byref(current_alpha), byref(flags))
    if not ret:
        return False
    # if the LWA_COLORKEY bit is set in flags
    return bool(flags.value & LWA_COLORKEY)


########################################################
# Always-on-top

def set_window_always_on_top(hWnd, enable=True):
    """
    Make this window always on top (or revert).
    """
    # If enable: pass HWND_TOPMOST, else HWND_NOTOPMOST
    insert_after = HWND_TOPMOST if enable else HWND_NOTOPMOST

    # Keep size and position
    flags = SWP_NOMOVE | SWP_NOSIZE
    user32.SetWindowPos(hWnd, insert_after, 0, 0, 0, 0, flags)

def is_window_always_on_top(hWnd):
    """
    Check if the WS_EX_TOPMOST style is applied.
    """
    style = user32.GetWindowLongA(hWnd, GWL_EXSTYLE)
    # There's no single bit for "always on top"; it’s controlled by window z-order.
    # Typically checking z-order requires comparing with other windows or checking the window's HMON.
    # A more direct approach is to call GetWindowLong on GWL_HWNDPARENT, but that might not be reliable.
    # Easiest is to compare with the OS-level z-order:
    # 
    # We'll do a naive approach: if window is above *any other window* -> we guess it's topmost.
    # But let's try the official approach with "window style topmost".
    # 
    # Actually, the topmost style is not purely a bit in GWL_EXSTYLE. 
    # It's set by SetWindowPos(hWnd, HWND_TOPMOST, ...).
    # 
    # So we attempt the following:
    import sys

    # We can do a real check using the Windows API:
    # If hWnd is topmost, GetWindow(hWnd, GW_HWNDPREV) will skip all normal windows, etc.
    # But that might get complicated.

    # For demonstration, let's do a simplified approach:
    #  - We'll compare the next window in the Z-order. If there's no window above it except topmost ones,
    #    it might be topmost. This is not 100% robust, but a decent guess.

    GW_HWNDPREV = 3
    hPrev = user32.GetWindow(hWnd, GW_HWNDPREV)
    if hPrev == 0:
        # No window above => likely topmost
        return True
    # If there's a window above, we can try checking if that is also topmost or not:
    # This approach is incomplete, but it's a starting point. 
    # 
    # For demonstration, let's say we just return False if there's any window above us.
    return False


########################################################
# Example usage (if run as a standalone script)

if __name__ == "__main__":
    # Let's just try listing all windows from the current process (like Blender):
    my_wins = get_all_windows(filter_pid=active_process_id)
    print(f"Process {active_process_id} windows:")
    for w in my_wins:
        txt = get_window_text(w)
        print(f"  hWnd={w}, title='{txt}', minimized={is_window_minimized(w)}")

    # For Blender usage:
    blender_wins = get_blender_windows()
    for wnd in blender_wins:
        print(f"Blender window found: {wnd}, title={get_window_text(wnd)}")
    
    #     # Example: set always-on-top
    #     set_window_always_on_top(wnd, True)
    #     # Move it somewhere
    #     set_window_geometry(wnd, 100, 100, 1024, 768)
    #     # Make it half transparent
    #     set_window_transparency(wnd, 50)
    #
    #     # or revert changes...
    #     # set_window_always_on_top(wnd, False)
    #     # set_window_transparency(wnd, 100)
