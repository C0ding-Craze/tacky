import ctypes
from ctypes import wintypes

from PySide6.QtCore import QThread, Signal

from ..core.config import IS_WIN
from ..core.log import log


MOD_ALT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x8, 0x4000
VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, VK_C = 0x11, 0x12, 0x5B, 0x5C, 0x43


def _win():
    return getattr(ctypes, "windll")


def key(vk, up):
    if IS_WIN:
        _win().user32.keybd_event(vk, 0, 2 if up else 0, 0)


def keys_down(*vks):
    return IS_WIN and all(_win().user32.GetAsyncKeyState(vk) & 0x8000 for vk in vks)


def snip_shortcut_down():
    win = keys_down(VK_LWIN) or keys_down(VK_RWIN)
    return (win and keys_down(0x10, 0x53)) or keys_down(0x2C)


def clip_seq():
    return _win().user32.GetClipboardSequenceNumber() if IS_WIN else 0


class KBDLL(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


LRESULT = ctypes.c_ssize_t
HOOKPROC = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class HotkeyThread(QThread):
    toggle, pin, failed, fallback = Signal(), Signal(), Signal(), Signal()

    def __init__(self):
        super().__init__()
        self._b_down = False
        self._proc = None
        self._hook = None
        self._tid = None

    def _ll(self, nCode, wParam, lParam):
        try:
            return self._hook_proc(nCode, wParam, lParam)
        except Exception:
            log.exception("Keyboard hook error")
            return _win().user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _hook_proc(self, nCode, wParam, lParam):
        u = _win().user32
        if nCode >= 0:
            k = ctypes.cast(lParam, ctypes.POINTER(KBDLL)).contents
            if k.vkCode == VK_C and not (k.flags & 0x10):
                if wParam in (0x100, 0x104):
                    win = (u.GetAsyncKeyState(VK_LWIN) | u.GetAsyncKeyState(VK_RWIN)) & 0x8000
                    other = (u.GetAsyncKeyState(0x10) | u.GetAsyncKeyState(0x11) | u.GetAsyncKeyState(0x12)) & 0x8000
                    if win and not other:
                        if not self._b_down:
                            self._b_down = True
                            self.pin.emit()
                            u.keybd_event(0xE8, 0, 0, 0)
                            u.keybd_event(0xE8, 0, 2, 0)
                        return 1
                elif wParam in (0x101, 0x105) and self._b_down:
                    self._b_down = False
                    return 1
        return u.CallNextHookEx(None, nCode, wParam, lParam)

    def run(self):
        try:
            self._run()
        except Exception:
            log.exception("Keyboard shortcut thread stopped")
            self.failed.emit()

    def _run(self):
        u, k = _win().user32, _win().kernel32
        self._tid = k.GetCurrentThreadId()
        ok1 = u.RegisterHotKey(None, 1, MOD_WIN | MOD_ALT | MOD_NOREPEAT, 0x53)

        u.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        u.CallNextHookEx.restype = LRESULT
        u.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
        u.SetWindowsHookExW.restype = wintypes.HHOOK
        k.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        k.GetModuleHandleW.restype = wintypes.HMODULE
        self._proc = HOOKPROC(self._ll)
        self._hook = u.SetWindowsHookExW(13, self._proc, k.GetModuleHandleW(None), 0)

        ok2 = bool(self._hook)
        if not ok2:
            ok2 = bool(u.RegisterHotKey(None, 2, MOD_WIN | MOD_ALT | MOD_NOREPEAT, 0x43))
            if ok2:
                self.fallback.emit()
        if not (ok1 and ok2):
            self.failed.emit()

        msg = wintypes.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:
                (self.toggle if msg.wParam == 1 else self.pin).emit()
        if self._hook:
            u.UnhookWindowsHookEx(self._hook)
        u.UnregisterHotKey(None, 1)
        u.UnregisterHotKey(None, 2)

    def stop(self):
        if self._tid:
            _win().user32.PostThreadMessageW(self._tid, 0x0012, 0, 0)
            self.wait(1000)
