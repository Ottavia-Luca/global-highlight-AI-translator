import re
import ctypes
import logging
from ctypes import wintypes, CFUNCTYPE, POINTER, Structure, c_int
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202

class MSLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]

HOOKPROC = CFUNCTYPE(ctypes.c_longlong, c_int, wintypes.WPARAM, wintypes.LPARAM)

user32 = ctypes.windll.user32
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.restype = ctypes.c_longlong
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_ulonglong]

_detector_instance = None
_log = logging.getLogger("translator")


@HOOKPROC
def _mouse_hook_callback(nCode, wParam, lParam):
    if nCode >= 0 and _detector_instance is not None:
        inst = _detector_instance
        if wParam == WM_LBUTTONDOWN:
            p = ctypes.cast(lParam, POINTER(MSLLHOOKSTRUCT)).contents
            inst._mouse_down_pos = (p.pt.x, p.pt.y)
            inst._mouse_down_valid = True
        elif wParam == WM_LBUTTONUP and inst._mouse_down_valid:
            p = ctypes.cast(lParam, POINTER(MSLLHOOKSTRUCT)).contents
            dx = p.pt.x - inst._mouse_down_pos[0]
            dy = p.pt.y - inst._mouse_down_pos[1]
            if abs(dx) > 5 or abs(dy) > 5:
                inst._selection_detected = True
            inst._mouse_down_valid = False
    return user32.CallNextHookEx(None, nCode, wParam, lParam)


class TextDetector(QObject):
    text_detected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True
        self._mouse_down_pos = (0, 0)
        self._mouse_down_valid = False
        self._selection_detected = False
        self._hook_handle = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._check_selection)
        self._install_hook()

    def set_enabled(self, enabled):
        self._enabled = enabled
        if enabled:
            self._install_hook()
        else:
            self._uninstall_hook()

    def cleanup(self):
        self._uninstall_hook()

    def _install_hook(self):
        global _detector_instance
        if self._hook_handle:
            return
        _detector_instance = self
        self._hook_handle = user32.SetWindowsHookExW(
            WH_MOUSE_LL, _mouse_hook_callback, None, 0
        )
        if self._hook_handle:
            self._poll_timer.start()

    def _uninstall_hook(self):
        self._poll_timer.stop()
        if self._hook_handle:
            user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None
        self._mouse_down_valid = False
        self._selection_detected = False

    def _check_selection(self):
        if self._selection_detected and self._enabled:
            self._selection_detected = False
            x, y = self._mouse_down_pos
            _log.info("[钩子] 检测到划选 pos=(%d,%d)", x, y)
            clipboard = QApplication.clipboard()
            old_text = clipboard.text()
            user32.keybd_event(0x11, 0, 0, 0)
            user32.keybd_event(0x43, 0, 0, 0)
            user32.keybd_event(0x43, 0, 2, 0)
            user32.keybd_event(0x11, 0, 2, 0)
            self._poll_clipboard(old_text, 0)

    def _poll_clipboard(self, old_text, attempts):
        if attempts > 10:
            return
        text = QApplication.clipboard().text()
        if text and text != old_text:
            if old_text:
                QApplication.clipboard().setText(old_text)
            _log.info("[剪贴板] text=%r", text[:120])
            if _is_valid_text(text):
                self.text_detected.emit(text)
            return
        QTimer.singleShot(50, lambda: self._poll_clipboard(old_text, attempts + 1))


def _is_valid_text(text):
    text = text.strip()
    if not text:
        return False
    if len(text) > 2000:
        return False
    if re.match(r'^[\d\s\.,;:!?()\[\]{}<>\-+=_/\\|@#$%^&*~`\'"]+$', text):
        return False
    return True
