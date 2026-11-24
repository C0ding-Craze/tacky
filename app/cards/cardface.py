import math
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QImage, QPainter, QPen, QPixmap, QTextLayout, QTransform

from ..core.config import CARD_H, IMAGE_EXT
from ..ui.theme import INK, INK_SOFT
from ..core.store import Item, note_color
from ..ui.painting import draw_file_icon, layout_text, note_font

POP_SCALE, POP_LIFT = 0.075, 5.0
PIN_ROOM = 23.4
POP_TOP = PIN_ROOM + POP_LIFT
POP_BOTTOM = 14.0


class Content:

    def __init__(self, kind: str, w: float, h: float, pad: float, top: float):
        self.kind, self.w, self.h, self.pad, self.top = kind, float(w), float(h), float(pad), float(top)
        self.lay: QTextLayout | None = None
        self.img: QImage | None = None
        self.ww = self.hh = 0.0
        self.cap: str | None = None
        self.name, self.is_dir, self.exists = "", False, True


@dataclass
class Face:
    pm: QPixmap
    w: float
    h: float
    dw: float
    dh: float
    lo: float
    hi: float
    angle: float
    args: tuple
    pop: QPixmap | None = None


def measure(item: Item, thumb) -> Content:
    it = item
    if it.kind == "text":
        n = len(it.text.strip())
        widths = [84, 98, 116, 136, 152, 168]
        start = 0 if n <= 10 else 1 if n <= 24 else 2
        w = widths[start]
        for w in widths[start:]:
            lay, ht = layout_text(it.text, w, 100000)
            if ht <= 84:
                break
        lay, ht = layout_text(it.text, w, 112)
        c = Content("text", w, max(30.0, ht + 6), 12, 19)
        c.lay = lay
        return c

    p = Path(it.path)
    img = thumb(str(p)) if (it.kind == "image" or p.suffix.lower() in IMAGE_EXT) else None
    if img is not None:
        hh = 112.0 if it.kind == "image" else 92.0
        ww = hh * img.width() / img.height()
        if ww > 230:
            ww = 230.0
            hh = ww * img.height() / img.width()
        cap = p.name if it.kind == "file" else None
        c = Content("photo", ww, hh + (16 if cap else 0), 4, 4)
        c.img, c.ww, c.hh, c.cap = img, ww, hh, cap
        return c

    c = Content("file", 130, 104, 9, 9)
    try:
        c.name, c.exists, c.is_dir = p.name or str(p), p.exists(), p.is_dir()
    except OSError:
        c.name, c.exists, c.is_dir = str(p), False, False
    return c


def margins(bb: QRectF):
    return math.ceil(bb.width() * POP_SCALE / 2) + 10, math.ceil(bb.height() * POP_SCALE / 2) + 10


def build_face(item: Item, angle, dpr, thumb) -> Face:
    c = measure(item, thumb)
    lw, lh = c.w + 2 * c.pad, c.h + c.top + c.pad
    s = (0.98 + item.size * 0.06) if item.kind == "text" else (0.88 + item.size * 0.24)
    limit = (CARD_H - POP_TOP - POP_BOTTOM) / (1 + POP_SCALE)

    def box(angle, scale):
        t = QTransform()
        t.rotate(angle)
        return t.mapRect(QRectF(-lw * scale / 2, -lh * scale / 2, lw * scale, lh * scale))

    ang = angle
    bb = box(ang, s)
    while bb.height() > limit and abs(ang) > 2.0:
        ang *= 0.85
        bb = box(ang, s)
    if bb.height() > limit:
        s *= limit / bb.height()
        bb = box(ang, s)
    mx, my = margins(bb)
    baked, W, Hh = bake(item, ang, dpr, s, lw, lh, bb, c, mx=mx, my=my)

    k, h2 = 1 + POP_SCALE, bb.height() / 2
    lo, hi = h2 * k + POP_TOP - CARD_H / 2, CARD_H / 2 - (h2 * k + POP_BOTTOM)
    if lo > hi:
        lo = hi = (lo + hi) / 2
    return Face(baked, W, Hh, lw * s, lh * s, lo, hi, ang, (s, lw, lh, bb, mx, my))


def bake_pop(item: Item, face: Face, dpr, thumb) -> QPixmap:
    s, lw, lh, bb, mx, my = face.args
    pm, _, _ = bake(item, face.angle, dpr, s * (1 + POP_SCALE), lw, lh, bb, measure(item, thumb),
                    SS=3 if dpr <= 1.25 else 2, mx=mx, my=my)
    return pm


def bake(item: Item, angle, dpr, s, lw, lh, bb, c: Content, SS=3, mx=12, my=12):
    pxw = max(1, math.ceil((bb.width() + 2 * mx) * dpr))
    pxh = max(1, math.ceil((bb.height() + 2 * my) * dpr))
    W, Hh = pxw / dpr, pxh / dpr
    img = QImage(pxw * SS, pxh * SS, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.scale(dpr * SS, dpr * SS)
    p.translate(W / 2, Hh / 2)
    p.rotate(angle)
    p.scale(s, s)

    p.setPen(Qt.PenStyle.NoPen)
    for i, a in enumerate((14, 24, 36)):
        p.setBrush(QColor(0, 0, 0, a))
        p.drawRoundedRect(QRectF(-lw / 2 - i + 2, -lh / 2 - i + 4, lw + 2 * i, lh + 2 * i), 4, 4)
    note = c.kind == "text"
    p.setPen(QPen(QColor(0, 0, 0, 55), 1.0))
    p.setBrush(QColor(note_color(item.id)) if note else QColor("white"))
    p.drawRoundedRect(QRectF(-lw / 2, -lh / 2, lw, lh), 3, 3)

    ox, oy = -lw / 2 + c.pad, -lh / 2 + c.top
    if c.kind == "text":
        p.setPen(QColor(INK))
        if c.lay is not None:
            p.save()
            p.setClipRect(QRectF(-lw / 2 + 2, -lh / 2 + 2, lw - 4, lh - 4))
            c.lay.draw(p, QPointF(ox, oy))
            p.restore()
    elif c.kind == "photo":
        if c.img is not None:
            src = c.img
            k = s * dpr * SS
            tw, th = max(1, round(c.ww * k)), max(1, round(c.hh * k))
            if src.width() > tw * 1.25 or src.height() > th * 1.25:
                src = src.scaled(tw, th, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            p.drawImage(QRectF(ox, oy, c.ww, c.hh), src)
        if c.cap:
            f = note_font(11)
            p.setFont(f)
            p.setPen(QColor(INK_SOFT))
            txt = QFontMetricsF(f).elidedText(c.cap, Qt.TextElideMode.ElideMiddle, c.ww)
            p.drawText(QRectF(ox, oy + c.hh + 1, c.ww, 15), Qt.AlignmentFlag.AlignCenter, txt)
    else:
        draw_file_icon(p, ox + c.w / 2, oy + 30, c.is_dir)
        p.setPen(QColor(INK_SOFT))
        f2 = note_font(12)
        p.setFont(f2)
        name = c.name + ("" if c.exists else " (missing)")
        name = QFontMetricsF(f2).elidedText(name, Qt.TextElideMode.ElideMiddle, c.w - 6)
        p.drawText(QRectF(ox, oy + 66, c.w, 22), Qt.AlignmentFlag.AlignCenter, name)
    p.end()

    small = img.scaled(pxw, pxh, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    pm = QPixmap.fromImage(small)
    pm.setDevicePixelRatio(dpr)
    return pm, W, Hh
