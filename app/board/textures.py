import math
import random

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient


def _noise(w, h, seed):
    data = random.Random(seed).randbytes(w * h)
    return QImage(data, w, h, w, QImage.Format.Format_Grayscale8).copy()


def _velvet(p, c, w, h, rng):
    light, dark = c.lighter(165), c.darker(240)
    sheen = QRadialGradient(w * 0.5, h * 0.3, max(w, h) * 0.65)
    lc, dc = QColor(light), QColor(dark)
    lc.setAlpha(70)
    dc.setAlpha(70)
    sheen.setColorAt(0, lc)
    sheen.setColorAt(1, dc)
    p.fillRect(QRect(0, 0, w, h), sheen)
    for _ in range(110):
        p.save()
        p.translate(rng.uniform(0, w), rng.uniform(0, h))
        p.rotate(rng.uniform(-22, 22))
        gr = QRadialGradient(0, 0, 90)
        col = QColor(light if rng.random() < 0.5 else dark)
        col.setAlpha(rng.randint(22, 44))
        gr.setColorAt(0, col)
        col.setAlpha(0)
        gr.setColorAt(1, col)
        p.setBrush(gr)
        p.drawEllipse(QRectF(-150, -34, 300, 68))
        p.restore()
    for scale, opacity, seed in ((1, 0.34, 3), (2, 0.30, 5)):
        n = _noise(max(2, w // scale), max(2, h // scale), seed)
        if scale > 1:
            n = n.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        inv = n.copy()
        inv.invertPixels()
        for tone, mask in ((light, n), (dark, inv)):
            layer = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            layer.fill(tone)
            layer.setAlphaChannel(mask)
            p.setOpacity(opacity)
            p.drawImage(0, 0, layer)
    p.setOpacity(1.0)
    for _ in range(w * h // 36):
        x, y, ln = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(1.2, 3.2)
        a = rng.uniform(-0.6, 0.6)
        col = QColor(light if rng.random() < 0.55 else dark)
        col.setAlpha(rng.randint(10, 26))
        p.setPen(QPen(col, 0.8))
        p.drawLine(QPointF(x, y), QPointF(x + ln * math.cos(a), y + ln * math.sin(a)))
    p.setPen(Qt.PenStyle.NoPen)


def _tack(p, c, w, h, rng):
    for _ in range(40):
        col = QColor(255, 255, 255) if rng.random() < 0.5 else QColor(0, 0, 0)
        col.setAlpha(rng.randint(5, 10))
        rr = rng.uniform(40, 130)
        p.setBrush(col)
        p.drawEllipse(QRectF(rng.uniform(-40, w), rng.uniform(-40, h), rr * rng.uniform(1.2, 2.2), rr))
    for _ in range(w * h // 13):
        col = c.lighter(rng.randint(74, 134))
        col.setAlpha(rng.randint(150, 235))
        sz = rng.uniform(2.0, 5.2)
        p.setBrush(col)
        p.drawEllipse(QRectF(rng.uniform(-2, w), rng.uniform(-2, h), sz, sz * rng.uniform(0.6, 1.1)))
    for _ in range(w * h // 55):
        p.setBrush(QColor(0, 0, 0, rng.randint(45, 115)))
        sz = rng.uniform(0.9, 2.0)
        p.drawEllipse(QRectF(rng.uniform(0, w), rng.uniform(0, h), sz, sz * rng.uniform(0.7, 1.2)))
    for _ in range(w * h // 90):
        col = c.lighter(rng.randint(150, 190))
        col.setAlpha(rng.randint(50, 110))
        sz = rng.uniform(0.8, 1.8)
        p.setBrush(col)
        p.drawEllipse(QRectF(rng.uniform(0, w), rng.uniform(0, h), sz, sz))
    for _ in range(max(10, w * h // 1800)):
        x, y = rng.uniform(8, w - 8), rng.uniform(8, h - 8)
        p.setBrush(QColor(0, 0, 0, 38))
        p.drawEllipse(QRectF(x - 2.8, y - 2.8, 5.6, 5.6))
        p.setBrush(QColor(0, 0, 0, 140))
        p.drawEllipse(QRectF(x - 1.1, y - 1.1, 2.2, 2.2))
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawEllipse(QRectF(x - 1.9, y - 2.4, 1.4, 1.1))


def make_texture(w, h, base, kind, dpr=1.0):
    w, h = max(1, int(w)), max(1, int(h))
    rng = random.Random(11)
    pm = QPixmap(max(1, math.ceil(w * dpr)), max(1, math.ceil(h * dpr)))
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(base)
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, c.darker(112))
    g.setColorAt(0.5, c.lighter(105))
    g.setColorAt(1, c.darker(108))
    p.fillRect(QRect(0, 0, w, h), g)
    p.setPen(Qt.PenStyle.NoPen)

    {"velvet": _velvet, "tack": _tack}[kind](p, c, w, h, rng)
    p.end()
    return pm
