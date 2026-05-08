import ctypes
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QApplication,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import QFont

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008

user32 = ctypes.windll.user32

FLOAT_WIDTH = 360
FLOAT_MAX_HEIGHT = 240


class FloatWindow(QWidget):
    copy_requested = pyqtSignal(str)
    bookmark_requested = pyqtSignal(str, str)
    hidden = pyqtSignal()

    def __init__(self, width=FLOAT_WIDTH, max_height=FLOAT_MAX_HEIGHT):
        super().__init__()
        self._width = width
        self._max_height = max_height
        self._full_text = ""
        self._source_text = ""
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(500)
        self._hide_timer.timeout.connect(self._do_hide)
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(self._width, self._max_height)
        hwnd = int(self.winId())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        self.setStyleSheet("""
            FloatWindow {
                background: #1e1e2e;
                border-radius: 12px;
                border: 1px solid #45475a;
            }
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(8)

        self._source_label = QLabel()
        self._source_label.setFont(QFont("Microsoft YaHei", 9))
        self._source_label.setStyleSheet("color: #a6adc8;")
        self._source_label.setWordWrap(True)
        self._source_label.setMaximumHeight(40)
        layout.addWidget(self._source_label)

        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #45475a;")
        layout.addWidget(line)

        self._trans_label = QLabel("...")
        self._trans_label.setFont(QFont("Microsoft YaHei", 11))
        self._trans_label.setStyleSheet("color: #cdd6f4;")
        self._trans_label.setWordWrap(True)
        self._trans_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._trans_label, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        self._copy_btn = QPushButton("复制")
        self._copy_btn.setFixedSize(60, 28)
        self._copy_btn.setStyleSheet("""
            QPushButton {
                background: #313244; color: #cdd6f4; border: none;
                border-radius: 6px; font-size: 11px;
            }
            QPushButton:hover { background: #45475a; }
        """)
        self._copy_btn.clicked.connect(self._on_copy)
        footer.addWidget(self._copy_btn)

        self._bookmark_btn = QPushButton("收藏")
        self._bookmark_btn.setFixedSize(60, 28)
        self._bookmark_btn.setStyleSheet("""
            QPushButton {
                background: #313244; color: #cdd6f4; border: none;
                border-radius: 6px; font-size: 11px;
            }
            QPushButton:hover { background: #45475a; }
        """)
        self._bookmark_btn.clicked.connect(self._on_bookmark)
        footer.addWidget(self._bookmark_btn)

        footer.addStretch()
        layout.addLayout(footer)

    def show_translation(self, source_text, cursor_pos):
        self._source_text = source_text
        self._full_text = ""
        self._source_label.setText(source_text)
        self._trans_label.setText("...")
        x = cursor_pos.x() + 16
        y = cursor_pos.y() + 48
        self.move(x, y)
        self.show()

    def append_token(self, token):
        self._full_text += token
        self._trans_label.setText(self._full_text)

    def enterEvent(self, event):
        self._hide_timer.stop()

    def leaveEvent(self, event):
        self._hide_timer.start()

    def _do_hide(self):
        self.hide()
        self.hidden.emit()

    def _on_copy(self):
        if self._full_text:
            QApplication.clipboard().setText(self._full_text)

    def _on_bookmark(self):
        if self._source_text and self._full_text:
            self.bookmark_requested.emit(self._source_text, self._full_text)
