import ctypes
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal

MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_ALT = 0x0001
VK_F8 = 0x77

user32 = ctypes.windll.user32


class TrayManager(QObject):
    toggle_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    hotkey_activated = pyqtSignal()

    def __init__(self, icon_on_path, icon_off_path):
        super().__init__()
        self._icon_on = QIcon(icon_on_path)
        self._icon_off = QIcon(icon_off_path)
        self._enabled = True
        self._hotkey_id = 1
        self._setup_tray()
        self._register_hotkey("Ctrl+Shift+F8")

    def _setup_tray(self):
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._icon_on)
        self._tray.setToolTip("划词翻译 - 开启")
        self._tray.activated.connect(self._on_tray_click)
        self._setup_menu()
        self._tray.show()

    def _setup_menu(self):
        menu = QMenu()
        self._toggle_action = QAction("开启" if self._enabled else "关闭")
        self._toggle_action.triggered.connect(self._on_toggle)
        menu.addAction(self._toggle_action)

        settings_action = QAction("设置...")
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        exit_action = QAction("退出")
        exit_action.triggered.connect(self.exit_requested.emit)
        menu.addAction(exit_action)

        self._tray.setContextMenu(menu)

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_toggle()

    def _on_toggle(self):
        self._enabled = not self._enabled
        self._toggle_action.setText("开启" if self._enabled else "关闭")
        self._tray.setIcon(self._icon_on if self._enabled else self._icon_off)
        self._tray.setToolTip(f"划词翻译 - {'开启' if self._enabled else '关闭'}")
        self.toggle_requested.emit()

    def set_enabled(self, enabled):
        if self._enabled != enabled:
            self._on_toggle()

    @property
    def enabled(self):
        return self._enabled

    def _register_hotkey(self, hotkey_str):
        hwnd = int(self._tray.winId() if hasattr(self._tray, 'winId') else 0)
        if not hwnd:
            return
        parts = hotkey_str.split("+")
        modifiers = 0
        vk = 0
        for p in parts:
            p = p.strip()
            if p == "Ctrl":
                modifiers |= MOD_CTRL
            elif p == "Shift":
                modifiers |= MOD_SHIFT
            elif p == "Alt":
                modifiers |= MOD_ALT
            else:
                vk = _key_to_vk(p)
        if vk:
            result = user32.RegisterHotKey(hwnd, self._hotkey_id, modifiers, vk)
            if not result:
                pass  # 静默失败

    def native_event_filter(self, msg, result):
        if msg.message == 0x0312 and msg.wParam == self._hotkey_id:
            self.hotkey_activated.emit()
            return True
        return False


def _key_to_vk(key):
    mapping = {
        "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
        "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
        "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    }
    return mapping.get(key.upper(), 0)
