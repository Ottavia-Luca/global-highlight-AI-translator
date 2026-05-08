import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core.config import Config
from core.cache import TranslationCache
from core.translator import TranslatorService
from core.text_detector import TextDetector
from ui.overlay_icon import OverlayIcon
from ui.float_window import FloatWindow
from ui.tray import TrayManager
from ui.settings_dialog import SettingsDialog


ASSETS_DIR = Path(__file__).parent / "assets"


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("划词翻译")

    # Core
    config = Config()
    cache = TranslationCache(
        max_entries=config.cache_max_entries,
        ttl_days=config.cache_ttl_days,
    )
    translator = TranslatorService(
        api_url=config.api_url,
        api_key=config.api_key,
        model=config.api_model,
        system_prompt=config.system_prompt,
        timeout=config.api_timeout,
        max_tokens=config.api_max_tokens,
    )

    # UI
    icon_on = str(ASSETS_DIR / "icon_on.ico")
    icon_off = str(ASSETS_DIR / "icon_off.ico")
    overlay_icon_path = str(ASSETS_DIR / "overlay_icon.png")

    if not os.path.exists(overlay_icon_path):
        _create_placeholder_icons()

    tray = TrayManager(icon_on, icon_off)
    overlay = OverlayIcon(
        overlay_icon_path,
        icon_size=config.icon_size,
        hover_delay=config.hover_delay,
    )
    float_win = FloatWindow(
        width=config.float_window_width,
        max_height=config.float_window_max_height,
    )
    text_detector = TextDetector()

    # --- 信号连接 ---

    def on_text_detected(text):
        if not tray.enabled:
            return
        if not config.api_key:
            return
        cached = cache.get(text)
        if cached:
            float_win.show_translation(text, app.cursor().pos())
            float_win.append_token(cached)
            return
        overlay.show_at(app.cursor().pos())
        translator.translate(text)

    text_detector.text_detected.connect(on_text_detected)

    translator.token_received.connect(float_win.append_token)

    def on_translation_done(full_text):
        cache.set(float_win._source_text, full_text)

    translator.translation_done.connect(on_translation_done)

    def on_hovered():
        overlay.hide()
        float_win.show_translation(float_win._source_text or "", app.cursor().pos())

    overlay.hovered.connect(on_hovered)

    def on_float_hidden():
        translator._pending_text = None

    float_win.hidden.connect(on_float_hidden)

    def on_toggle():
        text_detector.set_enabled(tray.enabled)

    tray.toggle_requested.connect(on_toggle)

    def on_hotkey():
        tray.set_enabled(not tray.enabled)

    tray.hotkey_activated.connect(on_hotkey)

    def on_settings():
        dlg = SettingsDialog(config)
        dlg.exec()
        translator._api_key = config.api_key
        translator._model = config.api_model
        translator._system_prompt = config.system_prompt
        cache._max_entries = config.cache_max_entries
        cache._ttl_days = config.cache_ttl_days

    tray.settings_requested.connect(on_settings)

    def on_exit():
        text_detector.uninstall()
        cache.close()
        translator.quit()
        app.quit()

    tray.exit_requested.connect(on_exit)

    text_detector.install()
    app.installNativeEventFilter(tray)

    sys.exit(app.exec())


def _create_placeholder_icons():
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon

    def create_simple_ico(path, color):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        pixmap.save(path, "PNG")

    os.makedirs(ASSETS_DIR, exist_ok=True)
    create_simple_ico(str(ASSETS_DIR / "icon_on.ico"), "#a6e3a1")
    create_simple_ico(str(ASSETS_DIR / "icon_off.ico"), "#6c7086")
    create_simple_ico(str(ASSETS_DIR / "overlay_icon.png"), "#89b4fa")


if __name__ == "__main__":
    main()
