import ctypes
from ctypes import wintypes, windll
import struct
import subprocess
import threading
import codecs
import os.path
import traceback

class WNDCLASS(ctypes.Structure):
    _fields = [
        ("style",  wintypes.UINT),
        ("lpfnWndProc", wintypes.LPVOID),  # wintypes.WNDPROC
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),  # wintypes.HCURSOR
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]

GetWindowText = ctypes.windll.User32.GetWindowTextW
SetWindowText = ctypes.windll.User32.SetWindowTextW
SendMessage = ctypes.windll.User32.SendMessageW
MoveWindow = ctypes.windll.User32.MoveWindow
ShowWindow = ctypes.windll.User32.ShowWindow
SetForegroundWindow = ctypes.windll.User32.SetForegroundWindow
SetFocus = ctypes.windll.User32.SetFocus
CallWindowProc = ctypes.windll.User32.CallWindowProcW
CreateWindowEx = ctypes.windll.User32.CreateWindowExW
def CreateWindow(lpClassName, lpWindowName, dwStyle, x, y, nWidth, nHeight, hWndParent, hMenu, hInstance, lpParam):
    return CreateWindowEx(0, lpClassName, lpWindowName, dwStyle, x, y, nWidth, nHeight, hWndParent, hMenu, hInstance, lpParam)
RegisterClass = ctypes.windll.User32.RegisterClassW
RegisterClass.argtypes = [ctypes.POINTER(WNDCLASS)]
GetModuleHandle = ctypes.windll.Kernel32.GetModuleHandleW
SetWindowLong = ctypes.windll.User32.SetWindowLongW
PostMessage = ctypes.windll.User32.PostMessageW
GetCursorPos = ctypes.windll.User32.GetCursorPos
GetCursorPos.argtype = [ctypes.POINTER(wintypes.POINT)]
DefWindowProc = windll.user32.DefWindowProcW
DefWindowProc.argtypes = (ctypes.wintypes.HWND, ctypes.wintypes.UINT, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)
HIWORD = lambda v: (v & 0xffff0000) >> 16
LOWORD = lambda v: v & 0xffff
VK_RETURN = 0x0d
VK_ESCAPE = 0x1b
VK_UP = 0x26
VK_DOWN = 0x28
EM_GETSEL = 0x00b0
EM_SETSEL = 0x00b1
WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_COMMAND = 0x0111
EN_CHANGE = 0x0300
WM_SETFOCUS = 0x0007
CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001
COLOR_WINDOW = 5
WS_CAPTION = 0x00c00000
WS_VISIBLE = 0x10000000
CW_USEDEFAULT = 0x80000000
WS_EX_WINDOWEDGE = 0x0100
WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00c00000
WS_SYSMENU = 0x00080000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_OVERLAPPEDWINDOW = (
    WS_OVERLAPPED     |
    WS_CAPTION        | 
    WS_SYSMENU        |
    WS_THICKFRAME     | 
    WS_MINIMIZEBOX    |
    WS_MAXIMIZEBOX)
SW_HIDE = 0
WS_CHILD = 0x40000000
ES_NOHIDESEL = 0x0100
GWL_WNDPROC = -4
WM_QUIT = 0x0012
SW_SHOW = 5


class CommandList(dict):
    def proposals(self, head):
        return sorted([p for p in self if p.startswith(head)])


class CommandWindow(object):
    def __init__(self):
        pass

    def next_candidate(self, dir):
        text = GetWindowText(self.hwnd_edit)
        selinfo  = SendMessage(self.hwnd_edit, EM_GETSEL, 0, 0)
        endpos   = HIWORD(selinfo)
        startpos = LOWORD(selinfo)
        unselected_text = text[:startpos]
        proposals = self.cmds.proposals(unselected_text)
        SetWindowText(self.hwnd_edit, proposals[(proposals.index(text) + dir) % len(proposals)])
        SendMessage(self.hwnd_edit, EM_SETSEL, len(unselected_text), -1)

    def create_window(self):
        print("create_window")
        def editwndproc(hwnd, msg, wParam, lParam):
            print("editwndproc")
            # print("EW: %08x %08x %08x"%(msg, wParam, lParam))
            if msg == WM_CHAR:
                if wParam == VK_RETURN:
                    if self.exec_command(GetWindowText(self.hwnd_edit)):
                        return 0
                if wParam == VK_ESCAPE:
                    ShowWindow(self.hwnd, SW_HIDE)
                    return 0
            if msg == WM_KEYDOWN:
                if wParam == VK_UP:
                    self.next_candidate(-1)
                    return 0
                if wParam == VK_DOWN:
                    self.next_candidate(1)
                    return 0
            return CallWindowProc(self.old_editwndproc, hwnd, msg, wParam, lParam)

        def wndproc(hwnd, msg, wParam, lParam):
            print("wndproc")
            # FIXME: not print()ing in wndproc mysteriously cause "OSError: exception: access violation"
            print("MW: %08x %08x %08x"%(msg, wParam, lParam))
            if msg == WM_COMMAND and HIWORD(wParam) == EN_CHANGE:
                text = GetWindowText(self.hwnd_edit)
                if len(text) == 0: return 0
                proposals = self.cmds.proposals(text)
                if not proposals:
                    return 0
                SetWindowText(self.hwnd_edit, proposals[0])
                SendMessage(self.hwnd_edit, EM_SETSEL, len(text), -1)

            if msg == WM_SETFOCUS:
                SetFocus(self.hwnd_edit)
            return DefWindowProc(hwnd, msg, wParam, lParam)

#        message_map = {
#            win32con.WM_DESTROY: self.OnDestroy,
#        }
        WNDPROC_FUNC = ctypes.CFUNCTYPE(
            wintypes.LPARAM,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM)
        wc = WNDCLASS()
        wc.style = CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = WNDPROC_FUNC(wndproc)
        wc.cbWndExtra = 0
        wc.hCursor = 0
        wc.hbrBackground = COLOR_WINDOW + 1
        wc.hIcon = 0
        wc.lpszClassName = "windhockey"
        wc.cbWndExtra = 0
        print("@1")
        print("wc.lpfnWndProc: {0}".format(wc.lpfnWndProc))
        RegisterClass(wc)
        print("@2")

        style = WS_OVERLAPPEDWINDOW
        print("before CreateWindowEx")
        self.hwnd = CreateWindowEx(
                             WS_EX_WINDOWEDGE,
                             "windhockey",
                             "windhockey",
                             WS_CAPTION | WS_VISIBLE,
                             CW_USEDEFAULT,
                             CW_USEDEFAULT,
                             256,
                             96,
                             0,
                             0,
                             GetModuleHandle(None),
                             None)
        print("after CreateWindowEx")
        print("before CreateWindow")
        self.hwnd_edit = CreateWindow("EDIT",
                             "",
                             WS_CHILD | WS_VISIBLE | ES_NOHIDESEL,
                             CW_USEDEFAULT,
                             CW_USEDEFAULT,
                             256,
                             96,
                             self.hwnd,
                             0,
                             GetModuleHandle(None),
                             None)
        print("after CreateWindow")
        # seems pywin32 lacks SetWindowSubclass()
        self.old_editwndproc = SetWindowLong(self.hwnd_edit, GWL_WNDPROC, WNDPROC_FUNC(editwndproc))
#        print(hex(self.old_editwndproc))
        #font = win32ui.CreateFont({'name':'Courier New', 'height':96})
        #win32gui.SendMessage(self.hwnd_edit, win32con.WM_SETFONT, font.GetSafeHandle(), True)
        ShowWindow(self.hwnd, SW_HIDE)

    def start(self):
        self.thread = threading.Thread(daemon=True, target=self._run)
        self.thread.start()

    def stop(self):
        PostMessage(self.hwnd, WM_QUIT, 0, 0)

    def show(self):
        print("show")
        point = wintypes.POINT()
        GetCursorPos(ctypes.byref(point))
        x, y = point.x, point.y
        print("x, y = {0}, {1}".format(x, y))
        MoveWindow(self.hwnd, x, y, 256, 96, True)
        ShowWindow(self.hwnd, SW_SHOW)
        SetWindowText(self.hwnd_edit, "")
        SetForegroundWindow(self.hwnd)
        print("@3")

        base_path = os.path.dirname(__file__)
        with codecs.open(os.path.join(base_path, 'winhk_config.py'), encoding='utf-8') as f:
            s = f.read()
        self.cmds = CommandList()
        exec(compile(s, 'winhk_config.py', 'exec'), globals(), self.cmds)
        print("@4")

    def exec_command(self, cmd):
        if not cmd in self.cmds:
            return False

        ShowWindow(self.hwnd, SW_HIDE)
        cmd = self.cmds[cmd]
        if callable(cmd):
            try:
                cmd()
            except:
                traceback.print_exc()
        elif type(cmd) is str:
            if cmd.startswith('http://') or cmd.startswith('https://'):
                subprocess.Popen('start %s'%(cmd), shell=True)
            elif cmd.startswith('start '):
                subprocess.Popen(cmd, shell=True)
            else:
                subprocess.Popen([cmd])
        elif type(cmd) is list:
            subprocess.Popen(cmd)
        return True

    def _run(self):
        byref = ctypes.byref
        user32 = ctypes.windll.user32
        self.create_window()
        msg = wintypes.MSG()
        while user32.GetMessageW(byref(msg), None, 0, 0) != 0:
            try:
                #print("AP: %08x %08x %08x"%(msg.message, msg.wParam, msg.lParam))
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))

            except Exception as e:
                traceback.print_exc()
