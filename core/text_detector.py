import ctypes
import re
from ctypes import wintypes
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

# Win32 DLL bindings — only work on Windows
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_MOUSE_LL = 14
WM_LBUTTONUP = 0x0202

# 全局变量保持引用防止 GC 回收回调
_hook_handle = None
_callback_ref = None


class TextDetector(QObject):
    text_detected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(100)
        self._debounce_timer.timeout.connect(self._on_debounce)

    def set_enabled(self, enabled):
        self._enabled = enabled

    def install(self):
        global _hook_handle
        if _hook_handle:
            return
        module = kernel32.GetModuleHandleW(None)
        hook_proc = _LowLevelMouseProc(self._on_mouse_event)
        _hook_handle = user32.SetWindowsHookExW(
            WH_MOUSE_LL, hook_proc, module, 0
        )
        if not _hook_handle:
            raise OSError(f"SetWindowsHookEx failed: {kernel32.GetLastError()}")

    def uninstall(self):
        global _hook_handle
        if _hook_handle:
            user32.UnhookWindowsHookEx(_hook_handle)
            _hook_handle = None

    def _on_mouse_event(self, code, wparam, lparam):
        if code >= 0 and wparam == WM_LBUTTONUP:
            self._debounce_timer.start()

    def _on_debounce(self):
        if not self._enabled:
            return
        text = _get_selected_text()
        if text and _is_valid_text(text):
            self.text_detected.emit(text)


def _get_selected_text():
    try:
        import comtypes.client
        uia = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=comtypes.gen.UIAutomationClient.IUIAutomation,
        )
        element = uia.GetFocusedElement()
        pattern = element.GetCurrentPattern(10018)  # UIA_TextPatternId
        if pattern:
            selection = pattern.GetSelection()
            if selection:
                return selection.GetElement(0).GetCurrentPropertyValue(30057)  # Text
        return None
    except Exception:
        return None


def _is_valid_text(text):
    text = text.strip()
    if not text:
        return False
    if len(text) > 2000:
        return False
    if re.match(r'^[\d\s\.,;:!?()\[\]{}<>\-+=_/\\|@#$%^&*~`\'"]+$', text):
        return False
    return True


# Win32 回调类型
LowLevelMouseProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)


class _LowLevelMouseProc:
    def __init__(self, callback):
        self._callback = callback
        global _callback_ref
        _callback_ref = LowLevelMouseProc(self._handler)

    def _handler(self, nCode, wParam, lParam):
        self._callback(nCode, wParam, lParam)
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def __call__(self):
        return _callback_ref
