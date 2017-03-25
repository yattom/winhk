import ctypes
from ctypes import wintypes
import win32con

user32 = ctypes.windll.user32
byref = ctypes.byref

hotkeys = []

MODS = {
    'alt': win32con.MOD_ALT,
    'win': win32con.MOD_WIN,
    'ctrl': win32con.MOD_CONTROL,
    'shift': win32con.MOD_SHIFT,
}

def convert_key(key):
    keys = [s.lower() for s in key.split('-')]
    mods = 0
    vk = 0
    for k in keys:
        if k in MODS:
            mods = mods | MODS[k]
        else:
            vk = eval('win32con.VK_%s'%(k.upper()))
    return (vk, mods)

def register_hotkey(keystroke, action):
    vk, mods = convert_key(keystroke)
    idx = len(hotkeys)
    if not user32.RegisterHotKey(None, idx, mods, vk):
        raise ValueError('cannot register hotkey')
    hotkeys.append(((vk, mods), action))

def run():
    try:
        msg = wintypes.MSG()
        while user32.GetMessageW(byref(msg), None, 0, 0) != 0:
            if msg.message == win32con.WM_HOTKEY:
                _, action = hotkeys[msg.wParam]
                if action:
                    action()

            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))

    finally:
        for idx in range(len(hotkeys)):
            user32.UnregisterHotKey(None, idx)
