import os
import yaml
from pathlib import Path
from PyQt6.QtCore import QFileSystemWatcher, QObject, pyqtSignal

DEFAULT_CONFIG = {
    "api": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "key": "",
        "model": "deepseek-v4-flash",
        "timeout": 10,
        "max_tokens": 512,
    },
    "translation": {
        "auto_detect": True,
        "fallback_source": "en",
        "fallback_target": "zh",
    },
    "system_prompt": "你是一个翻译助手。翻译用户输入的文本。\n",
    "hotkeys": {"toggle": "Ctrl+Shift+F8"},
    "cache": {"max_entries": 10000, "ttl_days": 30},
    "ui": {
        "icon_size": 24,
        "float_window_width": 360,
        "float_window_max_height": 240,
        "hover_delay": 200,
    },
}


def _deep_get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, {})
        else:
            return default
    return d if d != {} else default


class Config(QObject):
    changed = pyqtSignal()

    def __init__(self, config_path=None):
        super().__init__()
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        self._path = str(config_path)
        self._data = {}
        self._load()
        self._setup_watcher()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self._data = {}

    def _get(self, *keys, default=None):
        val = _deep_get(self._data, *keys)
        if val is not None:
            return val
        return _deep_get(DEFAULT_CONFIG, *keys, default=default)

    def reload(self):
        """手动重新加载配置（用于无事件循环环境）"""
        self._load()

    def _setup_watcher(self):
        self._watcher = QFileSystemWatcher()
        if os.path.exists(self._path):
            self._watcher.addPath(self._path)
        self._watcher.fileChanged.connect(self._on_file_changed)

    def _on_file_changed(self, path):
        self._load()
        self.changed.emit()
        if os.path.exists(self._path):
            self._watcher.addPath(self._path)

    @property
    def api_url(self):
        return self._get("api", "url")

    @property
    def api_key(self):
        return self._get("api", "key")

    @property
    def api_model(self):
        return self._get("api", "model")

    @property
    def api_timeout(self):
        return self._get("api", "timeout")

    @property
    def api_max_tokens(self):
        return self._get("api", "max_tokens")

    @property
    def auto_detect(self):
        return self._get("translation", "auto_detect")

    @property
    def fallback_source(self):
        return self._get("translation", "fallback_source")

    @property
    def fallback_target(self):
        return self._get("translation", "fallback_target")

    @property
    def system_prompt(self):
        return self._get("system_prompt")

    @property
    def toggle_hotkey(self):
        return self._get("hotkeys", "toggle")

    @property
    def cache_max_entries(self):
        return self._get("cache", "max_entries")

    @property
    def cache_ttl_days(self):
        return self._get("cache", "ttl_days")

    @property
    def icon_size(self):
        return self._get("ui", "icon_size")

    @property
    def float_window_width(self):
        return self._get("ui", "float_window_width")

    @property
    def float_window_max_height(self):
        return self._get("ui", "float_window_max_height")

    @property
    def hover_delay(self):
        return self._get("ui", "hover_delay")
