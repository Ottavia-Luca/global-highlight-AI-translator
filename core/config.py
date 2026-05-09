import os
from pathlib import Path
from PyQt6.QtCore import QFileSystemWatcher, QObject, pyqtSignal


class Config(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._env = {}
        self._load_env()
        self._setup_watcher()

    def _load_env(self):
        self._env.clear()
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    self._env[k.strip()] = v.strip().strip("\"'")

    def _get(self, key, default=""):
        return self._env.get(key, default)

    def _setup_watcher(self):
        env_path = str(Path(__file__).parent.parent / ".env")
        self._watcher = QFileSystemWatcher()
        if os.path.exists(env_path):
            self._watcher.addPath(env_path)
        self._watcher.fileChanged.connect(self._on_file_changed)

    def _on_file_changed(self, path):
        self._load_env()
        self.changed.emit()
        if os.path.exists(path):
            self._watcher.addPath(path)

    @property
    def api_url(self):
        return self._get(
            "DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"
        )

    @property
    def api_key(self):
        return self._get("DEEPSEEK_API_KEY")

    @property
    def api_model(self):
        return self._get("DEEPSEEK_API_MODEL", "deepseek-v4-flash")

    @property
    def api_timeout(self):
        return int(self._get("DEEPSEEK_API_TIMEOUT", "10"))

    @property
    def api_max_tokens(self):
        return int(self._get("DEEPSEEK_API_MAX_TOKENS", "512"))

    @property
    def system_prompt(self):
        return self._get(
            "DEEPSEEK_SYSTEM_PROMPT",
            '你是翻译助手。英文翻译成中文，中文翻译成英文。专有名词缩写按"全称是 XXX（YYY）"输出。简洁输出。',
        )

    @property
    def cache_max_entries(self):
        return int(self._get("DEEPSEEK_CACHE_MAX_ENTRIES", "10000"))

    @property
    def icon_size(self):
        return int(self._get("DEEPSEEK_UI_ICON_SIZE", "24"))

    @property
    def float_window_width(self):
        return int(self._get("DEEPSEEK_UI_FLOAT_WINDOW_WIDTH", "300"))

    @property
    def float_window_max_height(self):
        return int(self._get("DEEPSEEK_UI_FLOAT_WINDOW_MAX_HEIGHT", "320"))

    @property
    def hover_delay(self):
        return int(self._get("DEEPSEEK_UI_HOVER_DELAY", "200"))
