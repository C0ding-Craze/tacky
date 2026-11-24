import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient, QTextLayout,
    QTextOption,
)

from .theme import INK_SOFT


def blank_pixmap(w, h, dpr):
    pm = QPixmap(max(1, math.ceil(w * dpr)), max(1, math.ceil(h * dpr)))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    return pm


def snap_point(p, x, y):
    t = p.deviceTransform()
    inv, ok = t.inverted()
    if not ok:
        return QPointF(x, y)
    d = t.map(QPointF(x, y))
    return inv.map(QPointF(round(d.x()), round(d.y())))


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in(x):
    return x ** 3


def draw_pin(p, cx, cy, dark, light, lift=0.0, ps=1.0):
    p.setPen(Qt.PenStyle.NoPen)
    a = max(0.35, 1 - lift / 22)
    dent = QRadialGradient(cx, cy - 1, 13)
    dent.setColorAt(0, QColor(0, 0, 0, int(95 * a)))
    dent.setColorAt(1, QColor(0, 0, 0, 0))
    p.setBrush(dent)
    p.drawEllipse(QRectF(cx - 13, cy - 8, 26, 15))
    p.setBrush(QColor(0, 0, 0, int(62 * a)))
    p.drawEllipse(QRectF(cx - 1 + lift * 0.5, cy - 1 + lift * 0.3, 19, 7))

    p.save()
    p.translate(cx, cy - lift)
    p.scale(ps, ps)
    p.translate(-cx, -cy)
    p.setBrush(dark.darker(135))
    p.drawEllipse(QRectF(cx - 7, cy - 5, 14, 6))
    neck = QLinearGradient(cx - 4.5, 0, cx + 4.5, 0)
    neck.setColorAt(0, dark.lighter(118))
    neck.setColorAt(0.45, light)
    neck.setColorAt(1, dark.darker(150))
    p.setBrush(neck)
    p.drawRoundedRect(QRectF(cx - 4.5, cy - 13, 9, 10), 2, 2)
    rim = QLinearGradient(cx - 8, 0, cx + 8, 0)
    rim.setColorAt(0, dark)
    rim.setColorAt(1, dark.darker(150))
    p.setBrush(rim)
    p.drawRoundedRect(QRectF(cx - 8.5, cy - 19, 17, 8), 3.5, 3.5)
    top = QLinearGradient(cx - 8, cy - 22, cx + 8, cy - 14)
    top.setColorAt(0, light)
    top.setColorAt(1, dark.lighter(108))
    p.setBrush(top)
    p.drawEllipse(QRectF(cx - 8.5, cy - 22, 17, 8))
    p.setBrush(QColor(255, 255, 255, 105))
    p.drawEllipse(QRectF(cx - 5.5, cy - 20.5, 6, 2.6))
    p.restore()


def note_font(px=13):
    f = QFont("Segoe UI")
    f.setPixelSize(px)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def layout_text(text, width, max_h):
    font = note_font()
    text = text.strip()
    if len(text) > 600:
        text = text[:600].rstrip() + "\u2026"
    txt = text.replace("\r\n", "\n").replace("\n", "\u2028")
    while True:
        lay = QTextLayout(txt, font)
        opt = QTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        lay.setTextOption(opt)
        lay.beginLayout()
        y = 0.0
        while True:
            line = lay.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            line.setPosition(QPointF(0, y))
            y += line.height()
        lay.endLayout()
        if y <= max_h or len(txt) <= 8:
            return lay, y
        base = txt.rstrip("\u2026")
        txt = base[: int(len(base) * 0.88)].rstrip() + "\u2026"


def draw_file_icon(p, cx, cy, is_dir):
    p.save()
    p.setBrush(QColor(0, 0, 0, 16))
    p.setPen(QPen(QColor(INK_SOFT), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if is_dir:
        p.drawRoundedRect(QRectF(cx - 21, cy - 15, 16, 9), 2.5, 2.5)
        p.drawRoundedRect(QRectF(cx - 21, cy - 10, 42, 26), 3, 3)
    else:
        x0, y0, x1, y1, f = cx - 15, cy - 20, cx + 15, cy + 20, 10
        sheet = QPainterPath()
        sheet.moveTo(x0, y0)
        sheet.lineTo(x1 - f, y0)
        sheet.lineTo(x1, y0 + f)
        sheet.lineTo(x1, y1)
        sheet.lineTo(x0, y1)
        sheet.closeSubpath()
        p.drawPath(sheet)
        fold = QPainterPath()
        fold.moveTo(x1 - f, y0)
        fold.lineTo(x1 - f, y0 + f)
        fold.lineTo(x1, y0 + f)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(fold)
        for i in range(3):
            p.drawLine(QPointF(x0 + 6, cy - 4 + i * 7), QPointF(x1 - 6, cy - 4 + i * 7))
    p.restore()


def draw_star(p, cx, cy, r):
    pts = [QPointF(cx + (r if i % 2 == 0 else r * 0.42) * math.cos(-math.pi / 2 + i * math.pi / 5),
                   cy + (r if i % 2 == 0 else r * 0.42) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(235, 170, 10))
    p.drawPolygon(QPolygonF(pts))
    p.restore()
