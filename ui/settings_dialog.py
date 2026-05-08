from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPlainTextEdit, QSpinBox, QPushButton, QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal


class SettingsDialog(QDialog):
    exit_requested = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._env_path = Path(__file__).parent.parent / ".env"
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        self.setWindowTitle("划词翻译 - 设置")
        self.setFixedSize(500, 500)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()

        self._api_url = QLineEdit()
        form.addRow("API URL:", self._api_url)

        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key:", self._api_key)

        self._model = QLineEdit()
        form.addRow("Model:", self._model)

        form.addRow(QLabel(""))

        self._system_prompt = QPlainTextEdit()
        self._system_prompt.setFixedHeight(160)
        self._system_prompt.setPlaceholderText("输入系统提示词...")
        form.addRow("系统提示词:", self._system_prompt)

        form.addRow(QLabel(""))

        self._cache_size = QSpinBox()
        self._cache_size.setRange(100, 100000)
        self._cache_size.setSingleStep(1000)
        form.addRow("缓存条目上限:", self._cache_size)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        exit_btn = QPushButton("退出程序")
        exit_btn.setStyleSheet(
            "QPushButton { background: #e64553; color: #ffffff; "
            "border: none; border-radius: 6px; padding: 6px 16px; }"
            "QPushButton:hover { background: #d63443; }"
        )
        exit_btn.clicked.connect(self._on_exit)
        btn_layout.addWidget(exit_btn)
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        apply_btn = QPushButton("应用")
        apply_btn.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; "
            "border: none; border-radius: 6px; padding: 6px 20px; }"
        )
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _load_config(self):
        self._api_url.setText(self._config.api_url)
        self._api_key.setText(self._config.api_key)
        self._model.setText(self._config.api_model)
        self._system_prompt.setPlainText(self._config.system_prompt)
        self._cache_size.setValue(self._config.cache_max_entries)

    def _on_exit(self):
        confirm = QMessageBox.question(
            self, "确认退出", "确定要退出划词翻译程序吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.exit_requested.emit()
            self.accept()

    def _apply(self):
        updates = {
            "DEEPSEEK_API_KEY": self._api_key.text(),
            "DEEPSEEK_API_URL": self._api_url.text(),
            "DEEPSEEK_API_MODEL": self._model.text(),
            "DEEPSEEK_SYSTEM_PROMPT": self._system_prompt.toPlainText(),
            "DEEPSEEK_CACHE_MAX_ENTRIES": str(self._cache_size.value()),
        }
        lines = []
        seen = set()
        try:
            with open(self._env_path, "r", encoding="utf-8") as f:
                for line in f:
                    key = line.split("=", 1)[0].strip() if "=" in line else ""
                    if key in updates:
                        lines.append(f"{key}={updates[key]}\n")
                        seen.add(key)
                    else:
                        lines.append(line.rstrip("\n") + "\n" if line.strip() else line)
        except FileNotFoundError:
            pass
        for key, val in updates.items():
            if key not in seen:
                lines.append(f"{key}={val}\n")
        with open(self._env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        self._config._load_env()
        self.accept()
