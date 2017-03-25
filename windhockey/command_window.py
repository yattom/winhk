import pythoncom, ctypes
from ctypes import wintypes, windll
import struct
import subprocess
import threading
import win32con
import win32gui
import win32ui
import win32api
import codecs
import os.path
import traceback


class CommandList(dict):
    def proposals(self, head):
        return sorted([p for p in self if p.startswith(head)])


class CommandWindow(object):
    def __init__(self):
        pass

    def next_candidate(self, dir):
        text = win32gui.GetWindowText(self.hwnd_edit)
        selinfo  = win32gui.SendMessage(self.hwnd_edit, win32con.EM_GETSEL, 0, 0)
        endpos   = win32api.HIWORD(selinfo)
        startpos = win32api.LOWORD(selinfo)
        unselected_text = text[:startpos]
        proposals = self.cmds.proposals(unselected_text)
        win32gui.SetWindowText(self.hwnd_edit, proposals[(proposals.index(text) + dir) % len(proposals)])
        win32api.SendMessage(self.hwnd_edit, win32con.EM_SETSEL, len(unselected_text), -1)

    def create_window(self):
        def editwndproc(hwnd, msg, wParam, lParam):
            # print("EW: %08x %08x %08x"%(msg, wParam, lParam))
            if msg == win32con.WM_CHAR:
                if wParam == win32con.VK_RETURN:
                    if self.exec_command(win32gui.GetWindowText(self.hwnd_edit)):
                        return 0
                if wParam == win32con.VK_ESCAPE:
                    win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
                    return 0
            if msg == win32con.WM_KEYDOWN:
                if wParam == win32con.VK_UP:
                    self.next_candidate(-1)
                    return 0
                if wParam == win32con.VK_DOWN:
                    self.next_candidate(1)
                    return 0
            return win32gui.CallWindowProc(self.old_editwndproc, hwnd, msg, wParam, lParam)

        def wndproc(hwnd, msg, wParam, lParam):
            # FIXME: not print()ing in wndproc mysteriously cause "OSError: exception: access violation"
            print("MW: %08x %08x %08x"%(msg, wParam, lParam))
            if msg == win32con.WM_COMMAND and win32api.HIWORD(wParam) == win32con.EN_CHANGE:
                text = win32gui.GetWindowText(self.hwnd_edit)
                if len(text) == 0: return 0
                proposals = self.cmds.proposals(text)
                if not proposals:
                    return 0
                win32gui.SetWindowText(self.hwnd_edit, proposals[0])
                win32api.SendMessage(self.hwnd_edit, win32con.EM_SETSEL, len(text), -1)

            if msg == win32con.WM_SETFOCUS:
                win32gui.SetFocus(self.hwnd_edit)
            windll.user32.DefWindowProcW.argtypes = (ctypes.wintypes.HWND, ctypes.wintypes.UINT, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)
            return windll.user32.DefWindowProcW(hwnd, msg, wParam, lParam)

#        message_map = {
#            win32con.WM_DESTROY: self.OnDestroy,
#        }
        wc = win32gui.WNDCLASS()
        wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        wc.lpfnWndProc = wndproc
        wc.cbWndExtra = 0
        wc.hCursor = 0
        wc.hbrBackground = win32con.COLOR_WINDOW + 1
        wc.hIcon = 0
        wc.lpszClassName = "windhockey"
        wc.cbWndExtra = 0
        win32gui.RegisterClass(wc)

        style = win32con.WS_OVERLAPPEDWINDOW
        self.hwnd = win32gui.CreateWindowEx(
                             win32con.WS_EX_WINDOWEDGE,
                             "windhockey",
                             "windhockey",
                             win32con.WS_CAPTION | win32con.WS_VISIBLE,
                             win32con.CW_USEDEFAULT,
                             win32con.CW_USEDEFAULT,
                             256,
                             96,
                             0,
                             0,
                             win32api.GetModuleHandle(None),
                             None)
        self.hwnd_edit = win32gui.CreateWindow("EDIT",
                             "",
                             win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.ES_NOHIDESEL,
                             win32con.CW_USEDEFAULT,
                             win32con.CW_USEDEFAULT,
                             256,
                             96,
                             self.hwnd,
                             0,
                             win32api.GetModuleHandle(None),
                             None)
        # seems pywin32 lacks SetWindowSubclass()
        self.old_editwndproc = win32gui.SetWindowLong(self.hwnd_edit, win32con.GWL_WNDPROC, editwndproc)
#        print(hex(self.old_editwndproc))
        #font = win32ui.CreateFont({'name':'Courier New', 'height':96})
        #win32gui.SendMessage(self.hwnd_edit, win32con.WM_SETFONT, font.GetSafeHandle(), True)
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def start(self):
        self.thread = threading.Thread(daemon=True, target=self._run)
        self.thread.start()

    def stop(self):
        win32api.PostMessage(self.hwnd, win32con.WM_QUIT, 0, 0)

    def show(self):
        x, y = win32gui.GetCursorPos()
        win32gui.MoveWindow(self.hwnd, x, y, 256, 96, True)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetWindowText(self.hwnd_edit, "")
        win32gui.SetForegroundWindow(self.hwnd)

        base_path = os.path.dirname(__file__)
        with codecs.open(os.path.join(base_path, 'winhk_config.py'), encoding='utf-8') as f:
            s = f.read()
        self.cmds = CommandList()
        exec(compile(s, 'winhk_config.py', 'exec'), globals(), self.cmds)

    def exec_command(self, cmd):
        if not cmd in self.cmds:
            return False

        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
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
