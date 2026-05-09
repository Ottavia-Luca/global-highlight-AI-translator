from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QCursor

from core.win32_utils import (
    GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST,
    VK_LBUTTON, user32,
)


class OverlayIcon(QWidget):
    hovered = pyqtSignal()

    def __init__(self, icon_path, icon_size=24, hover_delay=200):
        super().__init__()
        self._icon_size = icon_size
        self._hover_delay = hover_delay
        self._lbutton_was_down = False
        self._click_outside_timer = QTimer(self)
        self._click_outside_timer.setInterval(50)
        self._click_outside_timer.timeout.connect(self._check_click_outside)
        self._setup_window()
        self._setup_ui(icon_path)
        self._setup_timer()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(self._icon_size + 8, self._icon_size + 8)
        hwnd = int(self.winId())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _setup_ui(self, icon_path):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self._label = QLabel()
        self._label.setPixmap(
            QPixmap(icon_path).scaled(
                self._icon_size, self._icon_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

    def _setup_timer(self):
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(self._hover_delay)
        self._hover_timer.timeout.connect(self.hovered.emit)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(3000)
        self._auto_hide_timer.timeout.connect(self.hide)

    def show_at(self, pos):
        self.move(pos.x() + 8, pos.y() + 8)
        self.show()
        self._auto_hide_timer.start()
        self._click_outside_timer.start()

    def hide(self):
        self._click_outside_timer.stop()
        self._lbutton_was_down = False
        self._auto_hide_timer.stop()
        self._hover_timer.stop()
        super().hide()

    def enterEvent(self, event):
        self._auto_hide_timer.stop()
        self.setStyleSheet("background: rgba(0,0,0,40); border-radius: 6px;")
        self._hover_timer.start()

    def leaveEvent(self, event):
        self.setStyleSheet("")
        self._hover_timer.stop()

    def _check_click_outside(self):
        pressed = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
        if pressed and not self._lbutton_was_down:
            if not self.geometry().contains(QCursor.pos()):
                self.hide()
                return
        self._lbutton_was_down = pressed
