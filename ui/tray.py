from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal


class TrayManager(QObject):
    toggle_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, icon_on_path, icon_off_path):
        super().__init__()
        self._icon_on = QIcon(icon_on_path)
        self._icon_off = QIcon(icon_off_path)
        self._enabled = True
        self._setup_tray()

    def _setup_tray(self):
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(self._icon_on)
        self._tray.setToolTip("划词翻译 - 开启")
        self._tray.activated.connect(self._on_tray_click)
        self._setup_menu()
        self._tray.show()

    def _setup_menu(self):
        menu = QMenu()
        self._toggle_action = QAction("关闭" if self._enabled else "开启")
        self._toggle_action.triggered.connect(self._on_toggle)
        menu.addAction(self._toggle_action)

        self._settings_action = QAction("设置...")
        self._settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(self._settings_action)

        menu.addSeparator()

        self._exit_action = QAction("退出")
        self._exit_action.triggered.connect(self.exit_requested.emit)
        menu.addAction(self._exit_action)

        self._tray.setContextMenu(menu)

    def _on_tray_click(self, reason):
        try:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                self._on_toggle()
        except TypeError:
            pass

    def _on_toggle(self):
        self._enabled = not self._enabled
        self._toggle_action.setText("关闭" if self._enabled else "开启")
        self._tray.setIcon(self._icon_on if self._enabled else self._icon_off)
        self._tray.setToolTip(f"划词翻译 - {'开启' if self._enabled else '关闭'}")
        self.toggle_requested.emit()

    def set_enabled(self, enabled):
        if self._enabled != enabled:
            self._on_toggle()

    @property
    def enabled(self):
        return self._enabled
