from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..core.config import BOARD_STYLES
from ..core.log import log
from ..ui.icon import app_icon
from ..ui.theme import MENU_QSS
from ..core.startup import set_startup, startup_enabled


def build_tray(app, board, store):
    tray = QSystemTrayIcon(app_icon(), app)
    tray.setToolTip("Tacky")
    menu = QMenu()
    menu.setStyleSheet(MENU_QSS)
    menu.addAction("Show / hide board   (Win+Alt+S)", board.toggle)

    sp = menu.addMenu("Reveal speed")
    grp = QActionGroup(sp)
    for s in ("Instant", "Normal", "Slow"):
        a = QAction(s, sp, checkable=True, checked=store.speed == s)
        a.triggered.connect(lambda _=False, s=s: (setattr(store, "speed", s), store.save()))
        grp.addAction(a)
        sp.addAction(a)

    fm = menu.addMenu("Board style")
    fgrp = QActionGroup(fm)
    for name in BOARD_STYLES:
        act = QAction(name, fm, checkable=True, checked=store.felt == name)
        act.triggered.connect(lambda _=False, n=name: (setattr(store, "felt", n), store.save(), board.apply_style()))
        fgrp.addAction(act)
        fm.addAction(act)

    snip = QAction("Pin snips (Win+Shift+S / PrintScreen)", menu, checkable=True, checked=store.pin_snips)
    snip.triggered.connect(lambda v: (setattr(store, "pin_snips", bool(v)), store.save()))
    menu.addAction(snip)

    st = QAction("Start with Windows", menu, checkable=True, checked=startup_enabled())

    def toggle_startup(v):
        try:
            set_startup(bool(v))
        except Exception:
            log.exception("Could not change start-with-Windows")
            tray.showMessage("Tacky", "Couldn't change the start-with-Windows setting.")
        st.setChecked(startup_enabled())
    st.triggered.connect(toggle_startup)
    menu.addAction(st)

    menu.addSeparator()
    menu.addAction("Clear board (keeps starred)", board.ops.clear_unkept)

    menu.addAction("Quit", app.quit)  # main() saves, stops the hotkeys and hides the tray after exec()

    tray.setContextMenu(menu)
    tray.activated.connect(lambda r: board.toggle() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()
    return tray, menu
