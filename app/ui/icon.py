import functools

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from ..core.config import ASSETS_DIR, PIN_COLORS
from .painting import draw_pin


def _drawn_pin() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    dark, light = PIN_COLORS[0]
    draw_pin(p, 30, 54, QColor(dark), QColor(light), 0.0, 2.0)
    p.end()
    return QIcon(pm)


@functools.cache
def app_icon() -> QIcon:
    for name in ("pin.ico", "pin.png"):
        path = ASSETS_DIR / name
        if path.is_file() and not (icon := QIcon(str(path))).isNull():
            return icon
    return _drawn_pin()
