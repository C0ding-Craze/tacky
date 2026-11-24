import sys

from PySide6.QtCore import QDir, qInstallMessageHandler, QLockFile
from PySide6.QtGui import QFont, QPixmapCache
from PySide6.QtWidgets import QApplication

from .core.config import HK, IS_WIN, ROOT
from .core.log import log, setup as setup_log
from .core.store import Store
from .system.winkeys import HotkeyThread
from .board.window import Board
from .system.tray import build_tray
from .ui.icon import app_icon


def _qt_messages(mode, ctx, msg):
    if "libpng" in msg:
        return
    log.warning("Qt: %s", msg)


def main():
    setup_log()
    try:
        return _run()
    except Exception:
        log.exception("Tacky stopped because of an error")
        return 1


def _run():
    qInstallMessageHandler(_qt_messages)
    app = QApplication(sys.argv)
    QPixmapCache.setCacheLimit(1024)
    f = app.font()
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(f)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Tacky")
    app.setWindowIcon(app_icon())

    ROOT.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(QDir.temp().filePath("tacky.lock"))
    if not lock.tryLock(100):
        return 0

    store = Store()
    board = Board(store)

    hot = None
    if IS_WIN:
        hot = HotkeyThread()
        hot.toggle.connect(board.toggle)
        hot.pin.connect(board.capture.pin_selection)
        app.aboutToQuit.connect(hot.stop)

    tray, _menu = build_tray(app, board, store)
    if hot:
        hot.failed.connect(lambda: tray.showMessage("Tacky", "A keyboard shortcut is already used by another app."))

        def on_fallback():
            HK["pin"] = "Win+Alt+C"
            board.update_hint()
            tray.showMessage("Tacky", "Couldn't capture Win+C, so text pinning uses Win+Alt+C instead.")
        hot.fallback.connect(on_fallback)
        hot.start()
    code = app.exec()
    store.save()
    board.tick.stop()
    tray.hide()
    for obj in (tray, _menu, board):
        obj.deleteLater()
    app.processEvents()
    del tray, _menu, board, hot, store
    return code
