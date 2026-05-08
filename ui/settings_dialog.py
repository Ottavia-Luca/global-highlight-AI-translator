import yaml
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPlainTextEdit, QSpinBox, QPushButton, QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        self.setWindowTitle("划词翻译 - 设置")
        self.setFixedSize(500, 460)
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

    def _apply(self):
        config_path = self._config._path
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            data = {}

        data.setdefault("api", {})["key"] = self._api_key.text()
        data["api"]["url"] = self._api_url.text()
        data["api"]["model"] = self._model.text()
        data["system_prompt"] = self._system_prompt.toPlainText()
        data.setdefault("cache", {})["max_entries"] = self._cache_size.value()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        self.accept()
