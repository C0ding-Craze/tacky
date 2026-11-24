from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QMenu, QScrollArea, QWidget

from .theme import MENU_QSS


def styled_menu():
    m = QMenu()
    m.setStyleSheet(MENU_QSS)
    return m


class EdgeArrow(QWidget):
    step = Signal()
    hold = Signal()

    def __init__(self, direction, parent):
        super().__init__(parent)
        self.d = direction
        self._hover = False
        self.setFixedWidth(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._first = QTimer(self, singleShot=True, interval=320)
        self._rep = QTimer(self, interval=16)
        self._first.timeout.connect(self._rep.start)
        self._rep.timeout.connect(self.hold)

    def hideEvent(self, e):
        self.stop()
        super().hideEvent(e)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        self.step.emit()
        self._first.start()

    def stop(self):
        self._first.stop()
        self._rep.stop()
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        self._first.stop()
        self._rep.stop()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, w, 0) if self.d < 0 else QLinearGradient(w, 0, 0, 0)
        g.setColorAt(0, QColor(0, 0, 0, 150 if self._hover else 105))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), g)
        cx, cy, dx = (15 if self.d < 0 else w - 15), h / 2, (-5 if self.d < 0 else 5)
        pen = QPen(QColor(255, 255, 255, 245 if self._hover else 190), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(cx - dx, cy - 11)
        path.lineTo(cx + dx, cy)
        path.lineTo(cx - dx, cy + 11)
        p.drawPath(path)


class _Track(QWidget):

    def __init__(self, bar, parent, horizontal, min_handle):
        super().__init__(parent)
        self.bar, self.horiz, self.min_handle = bar, horizontal, min_handle
        self._grab = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        bar.valueChanged.connect(lambda *_: self.update())
        bar.rangeChanged.connect(self._range)
        self.setVisible(False)

    def _range(self, *_):
        try:
            self.setVisible(self.bar.maximum() > 0)
        except RuntimeError:
            return
        self.update()

    def _length(self):
        return self.width() if self.horiz else self.height()

    def _handle(self):
        mx, page, n = self.bar.maximum(), max(1, self.bar.pageStep()), self._length()
        hl = max(self.min_handle, n * page / (mx + page))
        pos = (n - hl) * (self.bar.value() / mx) if mx else 0.0
        return QRectF(pos, 0, hl, self.height()) if self.horiz else QRectF(0, pos, self.width(), hl)

    def _set_from(self, pos, offset):
        h = self._handle()
        span = max(1.0, self._length() - (h.width() if self.horiz else h.height()))
        self.bar.setValue(int(max(0.0, min(1.0, (pos - offset) / span)) * self.bar.maximum()))

    def _at(self, e):
        return e.position().x() if self.horiz else e.position().y()

    def mousePressEvent(self, e):
        h = self._handle()
        start = h.x() if self.horiz else h.y()
        self._grab = self._at(e) - start if h.contains(e.position()) else (h.width() if self.horiz else h.height()) / 2
        self._set_from(self._at(e), self._grab)

    def mouseMoveEvent(self, e):
        if self._grab is not None:
            self._set_from(self._at(e), self._grab)

    def mouseReleaseEvent(self, e):
        self._grab = None


class SlideBar(_Track):

    def __init__(self, bar, parent):
        super().__init__(bar, parent, True, 44.0)
        self.setFixedHeight(9)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(0, 0, 0, 140), 1))
        p.setBrush(QColor(25, 12, 4, 170))
        p.drawRoundedRect(r, 4, 4)
        h = self._handle().adjusted(1.5, 1.5, -1.5, -1.5)
        g = QLinearGradient(0, h.top(), 0, h.bottom())
        g.setColorAt(0, QColor("#F3E3C2"))
        g.setColorAt(1, QColor("#C7A36E"))
        p.setPen(QPen(QColor(70, 40, 15, 150), 1))
        p.setBrush(g)
        p.drawRoundedRect(h, 3, 3)


class ThinBar(_Track):

    def __init__(self, bar, parent):
        super().__init__(bar, parent, False, 28.0)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        r = self.width() / 2
        p.setBrush(QColor(110, 75, 40, 45))
        p.drawRoundedRect(QRectF(self.rect()), r, r)
        p.setBrush(QColor(138, 90, 48, 215))
        p.drawRoundedRect(self._handle(), r, r)


class HScroll(QScrollArea):
    wheeled = Signal()

    def wheelEvent(self, e):
        self.wheeled.emit()
        bar = self.horizontalScrollBar()
        d = e.angleDelta()
        bar.setValue(bar.value() - (d.y() or d.x()))
        e.accept()
