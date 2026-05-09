import sys
import os
import signal
import time
import logging
from pathlib import Path

# Qt6 会调用 SetProcessDpiAwarenessContext，但 Python 3.8+ 已预先设好
# PerMonitorAwareV2，重复调用会报"拒绝访问"。设这个环境变量告诉 Qt 跳过。
os.environ['QT_DPI_AWARENESS'] = 'per-monitor-aware-v2'

# Fix Windows DLL search: PyQt6's Qt6 bin must take priority over Anaconda's
# older Qt6 DLLs on PATH; System32 provides icuuc.dll that Qt6Core links against.
for _d in [
    os.path.join(os.path.dirname(__file__), "venv", "Lib", "site-packages", "PyQt6", "Qt6", "bin"),
    r"C:\Windows\System32",
]:
    if os.path.isdir(_d):
        os.add_dll_directory(_d)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor

from core.config import Config
from core.cache import TranslationCache
from core.translator import TranslatorService
from core.text_detector import TextDetector
from ui.overlay_icon import OverlayIcon
from ui.float_window import FloatWindow
from ui.tray import TrayManager
from ui.settings_dialog import SettingsDialog
from ui.bookmarks_dialog import BookmarksDialog

ASSETS_DIR = Path(__file__).parent / "assets"


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    return logging.getLogger("translator")


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("划词翻译")

    log = _setup_logging()

    # Core
    config = Config()
    cache = TranslationCache(
        max_entries=config.cache_max_entries,
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
            log.warning("API Key 未配置，跳过翻译")
            return
        if float_win.isVisible() and (time.time() - float_win.last_inside_click) < 2.0:
            return
        float_win._source_text = text
        overlay.show_at(QCursor.pos())

    text_detector.text_detected.connect(on_text_detected)

    def on_internal_selection(text):
        if not tray.enabled:
            return
        if not config.api_key:
            return
        float_win._source_text = text
        overlay.show_at(QCursor.pos())

    float_win.internal_text_selected.connect(on_internal_selection)

    translator.token_received.connect(float_win.append_token)

    def on_translation_done(full_text):
        log.info("[翻译完成] %s", full_text[:80])
        cache.set(float_win._source_text, full_text)

    translator.translation_done.connect(on_translation_done)

    translator.translation_error.connect(lambda msg: log.error("[API 错误] %s", msg))

    def on_hovered():
        overlay.hide()
        text = float_win._source_text or ""
        cached = cache.get(text)
        if cached:
            log.info("[缓存命中] %s", text[:80])
            float_win.show_translation(text, QCursor.pos())
            float_win.append_token(cached)
            return
        log.info("[API 请求] %s", text[:80])
        float_win.show_translation(text, QCursor.pos())
        translator.translate(text)

    overlay.hovered.connect(on_hovered)

    def on_float_hidden():
        translator._pending_text = None

    float_win.hidden.connect(on_float_hidden)

    def on_toggle():
        log.info("[开关] 划词翻译 %s", "开启" if tray.enabled else "关闭")
        text_detector.set_enabled(tray.enabled)

    tray.toggle_requested.connect(on_toggle)

    float_win.bookmark_requested.connect(
        lambda s, t: cache.save_bookmark(s, t)
    )

    def on_settings():
        dlg = SettingsDialog(config)
        dlg.exit_requested.connect(on_exit)
        dlg.exec()

    tray.settings_requested.connect(on_settings)

    def on_bookmarks():
        dlg = BookmarksDialog(cache)
        dlg.exec()

    tray.bookmarks_requested.connect(on_bookmarks)

    def on_exit():
        app.quit()

    tray.exit_requested.connect(on_exit)

    def on_config_changed():
        translator._api_key = config.api_key
        translator._model = config.api_model
        translator._system_prompt = config.system_prompt
        cache._max_entries = config.cache_max_entries

    config.changed.connect(on_config_changed)

    log.info("启动完成")

    _quit_flag = False

    def _on_sigint(signum, frame):
        nonlocal _quit_flag
        _quit_flag = True

    signal.signal(signal.SIGINT, _on_sigint)

    _poll = QTimer()
    _poll.setInterval(200)
    _poll.timeout.connect(lambda: app.quit() if _quit_flag else None)
    _poll.start()

    try:
        sys.exit(app.exec())
    finally:
        log.info("程序退出")
        text_detector.cleanup()
        translator.stop()
        cache.close()


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
