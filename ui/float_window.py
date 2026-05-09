import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QCursor

from core.win32_utils import (
    GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST,
    VK_LBUTTON, user32,
)

FLOAT_WIDTH = 250
FLOAT_MIN_HEIGHT = 66
FLOAT_MAX_HEIGHT = 320
STYLE = """
FloatWindow {
    background: #1c234a;
    border: 1.5px solid #6976e4;
    border-radius: 8px;
}
QLabel#trans_text {
    color: #e8eaf8;
    background: transparent;
    padding: 6px;
    font-size: 13px;
}
QScrollArea {
    border: 1.5px solid #4e5ab8;
    border-radius: 6px;
    background: #161e40;
}
QScrollBar:vertical {
    width: 4px;
    background: transparent;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #4e58b0;
    border-radius: 2px;
    min-height: 16px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QPushButton#copy_btn {
    background: #222c56;
    color: #c0c4f0;
    border: 1px solid #4e5ab8;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 11px;
}
QPushButton#copy_btn:hover {
    background: #2e3a6e;
    border-color: #6976e4;
}
QPushButton#bookmark_btn {
    background: #222c56;
    color: #d0c8f4;
    border: 1px solid #4e5ab8;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 11px;
}
QPushButton#bookmark_btn:hover {
    background: #2e3a6e;
    border-color: #6976e4;
}
"""


class FloatWindow(QWidget):
    bookmark_requested = pyqtSignal(str, str)
    hidden = pyqtSignal()
    internal_text_selected = pyqtSignal(str)

    def __init__(self, width=FLOAT_WIDTH, max_height=FLOAT_MAX_HEIGHT):
        super().__init__()
        self._width = width
        self._max_height = max_height
        self._full_text = ""
        self._source_text = ""
        self._lbutton_was_down = False
        self.last_inside_click = 0.0
        self._click_check_timer = QTimer(self)
        self._click_check_timer.setInterval(50)
        self._click_check_timer.timeout.connect(self._check_click_outside)
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(self._width)
        self.setMinimumHeight(FLOAT_MIN_HEIGHT)
        self.setMaximumHeight(self._max_height)
        self.resize(self._width, FLOAT_MIN_HEIGHT)
        hwnd = int(self.winId())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        self.setStyleSheet(STYLE)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(2)

        self._trans_label = QLabel("···")
        self._trans_label.setObjectName("trans_text")
        self._trans_label.setFont(QFont("Microsoft YaHei", 11))
        self._trans_label.setWordWrap(True)
        self._trans_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._trans_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._trans_scroll = QScrollArea()
        self._trans_scroll.setWidgetResizable(True)
        self._trans_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._trans_scroll.setWidget(self._trans_label)
        layout.addWidget(self._trans_scroll, 1)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        footer.setContentsMargins(0, 0, 0, 0)

        self._copy_btn = QPushButton("复制")
        self._copy_btn.setObjectName("copy_btn")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._on_copy)
        footer.addWidget(self._copy_btn)

        self._bookmark_btn = QPushButton("收藏")
        self._bookmark_btn.setObjectName("bookmark_btn")
        self._bookmark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bookmark_btn.clicked.connect(self._on_bookmark)
        footer.addWidget(self._bookmark_btn)

        footer.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #8890c0;"
            "border: none; border-radius: 4px; font-size: 12px; }"
            "QPushButton:hover { background: #323450; color: #f47a9e; }"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._do_hide)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def show_translation(self, source_text, cursor_pos):
        self._source_text = source_text
        self._full_text = ""
        self._trans_label.setText("···")
        self.resize(self._width, FLOAT_MIN_HEIGHT)
        x, y = _clamp_to_screen(cursor_pos.x() - self._width, cursor_pos.y(),
                                self._width, FLOAT_MIN_HEIGHT)
        self.move(x, y)
        self.show()
        self._click_check_timer.start()

    def append_token(self, token):
        self._full_text += token
        self._trans_label.setText(self._full_text)
        self._adjust_height()

    def _adjust_height(self):
        viewport_w = self._trans_scroll.viewport().width()
        if viewport_w <= 0:
            return
        text_h = self._trans_label.heightForWidth(viewport_w)
        footer_h = 28
        margins = 12
        needed = text_h + footer_h + margins
        needed = max(FLOAT_MIN_HEIGHT, min(needed, self._max_height))
        if needed != self.height():
            delta = needed - self.height()
            geo = self.geometry()
            self.resize(self._width, needed)
            new_y = max(0, geo.y() - delta)
            screen_geo = QApplication.screenAt(QPoint(geo.x(), new_y))
            if screen_geo:
                avail = screen_geo.availableGeometry()
                if new_y < avail.top():
                    new_y = avail.top()
            self.move(geo.x(), new_y)

    def _do_hide(self):
        self._click_check_timer.stop()
        self._lbutton_was_down = False
        self.hide()
        self.hidden.emit()

    def _check_click_outside(self):
        pressed = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
        if pressed and not self._lbutton_was_down:
            if not self.geometry().contains(QCursor.pos()):
                self._do_hide()
                return
            self.last_inside_click = time.time()
        elif not pressed and self._lbutton_was_down:
            if self.geometry().contains(QCursor.pos()):
                self.last_inside_click = time.time()
                selected = self._trans_label.selectedText()
                if selected:
                    self.internal_text_selected.emit(selected)
        self._lbutton_was_down = pressed

    def _on_copy(self):
        if self._full_text:
            QApplication.clipboard().setText(self._full_text)
            self._copy_btn.setText("✔ 已复制")
            QTimer.singleShot(1500, lambda: self._copy_btn.setText("复制"))

    def _on_bookmark(self):
        if self._source_text and self._full_text:
            self.bookmark_requested.emit(self._source_text, self._full_text)
            self._bookmark_btn.setText("★ 已收藏")
            QTimer.singleShot(1500, lambda: self._bookmark_btn.setText("收藏"))


def _clamp_to_screen(x, y, width, height):
    screen = QApplication.screenAt(QPoint(x, y))
    if screen is None:
        screen = QApplication.primaryScreen()
    if screen is None:
        return x, y
    geo = screen.availableGeometry()
    if x + width > geo.right():
        x = geo.right() - width
    if y + height > geo.bottom():
        y = geo.bottom() - height
    if x < geo.left():
        x = geo.left()
    if y < geo.top():
        y = geo.top()
    return x, y
