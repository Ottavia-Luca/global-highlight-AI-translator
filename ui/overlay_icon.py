import ctypes
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QMouseEvent


GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020

user32 = ctypes.windll.user32


class OverlayIcon(QWidget):
    hovered = pyqtSignal()
    leave = pyqtSignal()

    def __init__(self, icon_path, icon_size=24, hover_delay=200):
        super().__init__()
        self._icon_size = icon_size
        self._hover_delay = hover_delay
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
        style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_TRANSPARENT
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
        self.move(pos.x() + 16, pos.y() + 16)
        self.show()
        self._auto_hide_timer.start()

    def enterEvent(self, event):
        self._auto_hide_timer.stop()
        self.setStyleSheet("background: rgba(0,0,0,40); border-radius: 6px;")
        self._hover_timer.start()

    def leaveEvent(self, event):
        self.setStyleSheet("")
        self._hover_timer.stop()
        self.leave.emit()
