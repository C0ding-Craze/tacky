import math
import random

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen

from ..core.config import BOARD_H, INSET, INSET_B, PAD

RO, RI = 30.0, 19.0


def _shape(x, y, ww, hh, r):
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y - 40, ww, hh + 40), r, r)
    return path


def frame_paths(w):
    ih = BOARD_H - INSET_B
    return (_shape(PAD, 0, w - 2 * PAD, BOARD_H, RO),
            _shape(PAD + INSET, 0, w - 2 * PAD - 2 * INSET, ih, RI))


def _masked(p, w, path, paint):
    dpr = p.device().devicePixelRatioF()
    layer = QImage(max(1, math.ceil(w * dpr)), max(1, math.ceil((BOARD_H + 2) * dpr)),
                   QImage.Format.Format_ARGB32_Premultiplied)
    layer.setDevicePixelRatio(dpr)
    layer.fill(0)
    q = QPainter(layer)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint(q)
    q.end()

    mask = QImage(layer.size(), QImage.Format.Format_ARGB32_Premultiplied)
    mask.setDevicePixelRatio(dpr)
    mask.fill(0)
    m = QPainter(mask)
    m.setRenderHint(QPainter.RenderHint.Antialiasing)
    m.setPen(Qt.PenStyle.NoPen)
    m.setBrush(QColor(0, 0, 0))
    m.drawPath(path)
    m.end()

    q = QPainter(layer)
    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    q.drawImage(0, 0, mask)
    q.end()
    p.drawImage(0, 0, layer)


def draw_board(p, w, texture):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    ih = BOARD_H - INSET_B
    iw = w - 2 * PAD - 2 * INSET
    def line(x0, x1, y0, r):
        r = max(2.0, r)
        k = 0.4477
        path = QPainterPath()
        path.moveTo(x0, -40)
        path.lineTo(x0, y0 - r)
        path.cubicTo(x0, y0 - r * k, x0 + r * k, y0, x0 + r, y0)
        path.lineTo(x1 - r, y0)
        path.cubicTo(x1 - r * k, y0, x1, y0 - r * k, x1, y0 - r)
        path.lineTo(x1, -40)
        return path

    def ring(t):
        e = 0.9
        return line(PAD + e + t * (INSET - 2 * e), w - PAD - e - t * (INSET - 2 * e),
                    BOARD_H - e - t * (INSET_B - 2 * e), (RO - e) + ((RI + e) - (RO - e)) * t)

    def from_outer(d):
        return line(PAD + d, w - PAD - d, BOARD_H - d, RO - d)

    def from_inner(d):
        return line(PAD + INSET - d, w - PAD - INSET + d, ih + d, RI + d)

    outer, inner = frame_paths(w)

    p.setPen(Qt.PenStyle.NoPen)
    for grow, alpha in ((3.0, 20), (2.0, 20), (1.0, 24)):
        p.setBrush(QColor(0, 0, 0, alpha))
        p.drawPath(_shape(PAD - grow + 0.5, 0, w - 2 * PAD + 2 * grow - 1, BOARD_H + grow + 1.5, RO + grow))

    p.setBrush(Qt.BrushStyle.NoBrush)
    profile = [(0.0, (92, 56, 29)), (0.2, (138, 90, 50)), (0.4, (162, 112, 68)),
               (0.72, (132, 85, 47)), (1.0, (100, 63, 34))]

    def tone(t):
        for (t0, c0), (t1, c1) in zip(profile, profile[1:]):
            if t <= t1:
                f = (t - t0) / (t1 - t0)
                return QColor(*(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3)))
        return QColor(*profile[-1][1])

    light_above = QLinearGradient(0, 0, 0, BOARD_H)
    light_above.setColorAt(0, QColor(255, 235, 200, 38))
    light_above.setColorAt(1, QColor(0, 0, 0, 80))
    for i in range(61):
        t = i / 60
        p.setPen(QPen(tone(t), 1.9))
        p.drawPath(ring(t))
    rng = random.Random(21)
    for _ in range(9):
        col = QColor(50, 24, 6, rng.randint(10, 26)) if rng.random() < 0.5 else QColor(255, 210, 160, rng.randint(8, 20))
        pen = QPen(col, rng.uniform(8, 18))
        pen.setDashPattern([rng.uniform(12, 30), rng.uniform(3, 12)])
        pen.setDashOffset(rng.uniform(0, 500))
        p.setPen(pen)
        p.drawPath(ring(rng.random()))
    for _ in range(55):
        col = QColor(45, 20, 5, rng.randint(20, 56)) if rng.random() < 0.7 else QColor(255, 215, 165, rng.randint(10, 30))
        pen = QPen(col, rng.uniform(0.5, 1.3))
        pen.setDashPattern([rng.uniform(150, 420), rng.uniform(6, 40)])
        pen.setDashOffset(rng.uniform(0, 800))
        p.setPen(pen)
        p.drawPath(ring(rng.random()))

    _masked(p, w, outer.subtracted(inner),
            lambda q: q.fillRect(QRectF(0, -40, w, BOARD_H + 40), light_above))

    def bevel(rgb, alpha, path_fn, widths=7):
        for k in range(widths):
            wd = float(widths - k)
            p.setPen(QPen(QColor(rgb[0], rgb[1], rgb[2], alpha), wd))
            p.drawPath(path_fn(wd / 2))

    bevel((0, 0, 0), 18, from_outer)
    bevel((0, 0, 0), 22, from_inner)
    crest = from_outer(5.0)
    p.setPen(QPen(QColor(255, 226, 180, 70), 2.4))
    p.drawPath(crest)
    p.setPen(QPen(QColor(255, 226, 180, 60), 1.0))
    p.drawPath(from_inner(1.6))

    groove = from_outer(6.5)
    p.setPen(QPen(QColor(35, 15, 3, 120), 1.3))
    p.drawPath(groove)
    p.translate(0.8, 1.0)
    p.setPen(QPen(QColor(255, 225, 175, 28), 1.0))
    p.drawPath(groove)
    p.translate(-0.8, -1.0)

    x0 = PAD + INSET

    def surface(q):
        q.drawPixmap(x0, 0, texture(iw, ih))
        for rect, g in (
            (QRectF(x0, 0, iw, 32), QLinearGradient(0, 0, 0, 32)),
            (QRectF(x0, 0, 26, ih), QLinearGradient(x0, 0, x0 + 26, 0)),
            (QRectF(x0 + iw - 26, 0, 26, ih), QLinearGradient(x0 + iw, 0, x0 + iw - 26, 0)),
            (QRectF(x0, ih - 24, iw, 24), QLinearGradient(0, ih, 0, ih - 24)),
        ):
            g.setColorAt(0, QColor(0, 0, 0, 115))
            g.setColorAt(1, QColor(0, 0, 0, 0))
            q.fillRect(rect, g)
    _masked(p, w, inner, surface)

    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(15, 6, 1, 215), 2.2))
    p.drawPath(inner)
    p.setPen(QPen(QColor(255, 225, 175, 130), 1.3))
    p.drawPath(outer)
