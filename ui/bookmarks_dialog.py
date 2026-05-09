from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QClipboard


STYLE = """
QDialog {
    background: #1c234a;
}
QTableWidget {
    background: #161e40;
    color: #e8eaf8;
    border: 1.5px solid #4e5ab8;
    border-radius: 6px;
    gridline-color: #2a3566;
    font-size: 12px;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:selected {
    background: #3a4890;
}
QHeaderView::section {
    background: #222c56;
    color: #b0b8e8;
    border: none;
    border-bottom: 1.5px solid #4e5ab8;
    padding: 6px;
    font-weight: bold;
}
QScrollBar:vertical {
    width: 4px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #4e58b0;
    border-radius: 2px;
    min-height: 16px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


class BookmarksDialog(QDialog):
    def __init__(self, cache, parent=None):
        super().__init__(parent)
        self._cache = cache
        self.setWindowTitle("划词翻译 - 收藏夹")
        self.setFixedSize(560, 420)
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self._load_dates()
        self._load_bookmarks()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("按日期筛选:"))
        self._date_combo = QComboBox()
        self._date_combo.addItem("全部")
        self._date_combo.setStyleSheet(
            "QComboBox { background: #222c56; color: #e8eaf8; "
            "border: 1px solid #4e5ab8; border-radius: 4px; "
            "padding: 4px 8px; min-width: 120px; }"
            "QComboBox:hover { border-color: #6976e4; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { "
            "background: #1c234a; color: #e8eaf8; "
            "border: 1px solid #4e5ab8; }"
        )
        self._date_combo.currentIndexChanged.connect(self._on_date_filter)
        filter_row.addWidget(self._date_combo)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["原文", "译文"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().hide()
        self._table.setShowGrid(True)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget{alternate-background-color: #1a2350;}"
        )

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self._table.doubleClicked.connect(self._on_copy_source)

        layout.addWidget(self._table)

    def _load_bookmarks(self, date=None):
        rows = self._cache.get_bookmarks(date=date)
        self._table.setRowCount(len(rows))
        for i, (source, translated, _) in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(source))
            self._table.setItem(i, 1, QTableWidgetItem(translated))

    def _load_dates(self):
        dates = self._cache.get_bookmark_dates()
        for d in dates:
            self._date_combo.addItem(d)

    def _on_date_filter(self, idx):
        if idx <= 0:
            self._load_bookmarks()
        else:
            self._load_bookmarks(date=self._date_combo.currentText())

    def _on_copy_source(self, index):
        source = self._table.item(index.row(), 0)
        if source:
            QApplication.clipboard().setText(source.text())
