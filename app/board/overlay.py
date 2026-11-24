from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QWidget


class FlipCover(QWidget):
    def __init__(self, board):
        super().__init__(board)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.snap = None
        self.shade = None
        self.angle = -90.0
        self.hide()

    def set_snapshot(self, pm):
        self.snap = pm
        sh = QPixmap(pm.size())
        sh.setDevicePixelRatio(pm.devicePixelRatio())
        sh.fill(Qt.GlobalColor.transparent)
        q = QPainter(sh)
        q.drawPixmap(0, 0, pm)
        q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        q.fillRect(sh.rect(), QColor(0, 0, 0))
        q.end()
        self.shade = sh

    def clear(self):
        self.snap = self.shade = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if self.snap is None or self.shade is None:
            return
        a = min(90.0, abs(self.angle))
        if a < 0.01:
            p.drawPixmap(0, 0, self.snap)
            return
        if a >= 89.5:
            return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        cx = self.width() / 2
        t = QTransform()
        t.translate(cx, 0)
        t.rotate(self.angle, Qt.Axis.XAxis, 800.0)
        t.translate(-cx, 0)
        p.setTransform(t)
        p.drawPixmap(0, 0, self.snap)
        p.setOpacity(0.55 * a / 90.0)
        p.drawPixmap(0, 0, self.shade)
