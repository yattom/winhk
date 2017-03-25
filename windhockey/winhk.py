import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
byref = ctypes.byref

hotkeys = []

WM_HOTKEY = 0x0312  # win32con.WM_HOTKEY

MODS = {
    'alt': 0x0001,  # win32con.MOD_ALT,
    'win': 0x0008,  # win32con.MOD_WIN,
    'ctrl': 0x0002,  # win32con.MOD_CONTROL,
    'shift': 0x0004,  # win32con.MOD_SHIFT,
}

VK_RETURN = 0x0d
VK_ESCAPE = 0x1b
VK_UP = 0x26
VK_DOWN = 0x28
VK_SPACE = 0x20

def convert_key(key):
    keys = [s.lower() for s in key.split('-')]
    mods = 0
    vk = 0
    for k in keys:
        if k in MODS:
            mods = mods | MODS[k]
        else:
            vk = eval('VK_%s'%(k.upper()))
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
            if msg.message == WM_HOTKEY:
                _, action = hotkeys[msg.wParam]
                if action:
                    action()

            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))

    finally:
        for idx in range(len(hotkeys)):
            user32.UnregisterHotKey(None, idx)
