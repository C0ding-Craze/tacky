import math
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QElapsedTimer, QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QTransform
from PySide6.QtWidgets import QApplication, QWidget

from ..core.config import CARD_H, FADE_START_DAYS, PIN_COLORS
from ..core.log import guarded
from ..core.store import Item
from ..ui.painting import draw_pin, draw_star, ease_in, ease_out, snap_point
from ..ui.widgets import styled_menu
from .cardface import POP_LIFT, POP_SCALE, bake_pop, build_face

if TYPE_CHECKING:
    from ..board.window import Board

HOVER_OMEGA = 27.0
PIN_LIFT, PIN_GROW = 11.0, 0.15


class Card(QWidget):

    def __init__(self, board: "Board", item: Item):
        super().__init__()
        self.board, self.item = board, item
        self._press = None
        self._suppress = False
        self.mode = None
        self.t = 1.0
        self._anims = []
        self.hover_t = 0.0
        self._hover_v = 0.0
        self._hover_on = False
        self._hover_clock = QElapsedTimer()
        self._hover_timer = QTimer(self, interval=8)
        self._hover_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._hover_timer.timeout.connect(self._step_hover)
        self.setMouseTracking(True)

        fc = board.face_cache.get(item.id)
        if fc is None:
            fc = board.face_cache[item.id] = build_face(item, item.angle, board._dpr(), board.thumb)
        self.fc = fc
        self.face = fc.pm
        self.angle = fc.angle
        self.spin = 1 if item.angle >= 0 else -1
        self.pin_col = PIN_COLORS[item.pin % len(PIN_COLORS)]
        self.dw, self.dh = fc.dw, fc.dh
        self.yoff = max(fc.lo, min(fc.hi, item.yoff))
        self.bw = math.ceil(fc.w)
        self.setFixedSize(self.bw, CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to copy \u2022 double-click to edit \u2022 drag out to share" if item.kind == "text"
                        else "Click to copy \u2022 double-click to open \u2022 drag out to share")

        age = (time.time() - item.created) / 86400
        self._fade = 1.0
        if not item.kept and age > FADE_START_DAYS:
            self._fade = max(0.35, 1 - (age - FADE_START_DAYS) / 3 * 0.65)

    def later(self, ms, fn):
        t = QTimer(self)
        t.setSingleShot(True)
        t.timeout.connect(fn)
        t.timeout.connect(t.deleteLater)
        t.start(max(0, int(ms)))

    def _run(self, start, end, ms, curve, on_step, on_done=None):
        a = QVariantAnimation(self)
        a.setStartValue(start)
        a.setEndValue(end)
        a.setDuration(ms)
        a.setEasingCurve(curve)
        a.valueChanged.connect(on_step)

        def finished():
            if a in self._anims:
                self._anims.remove(a)
            a.deleteLater()
            if on_done:
                on_done()
        a.finished.connect(finished)
        self._anims.append(a)
        a.start()

    def _step_t(self, v):
        self.t = float(v)
        self.update()

    def _step_w(self, v):
        self.setFixedWidth(max(0, int(v)))

    def begin_hidden(self):
        self.mode = "hidden"
        self.setFixedWidth(0)

    def play_in(self):
        def land():
            self.mode, self.t = "in", 0.0
            self._run(0.0, 1.0, 470, QEasingCurve.Type.Linear, self._step_t, done)

        def done():
            self.mode, self.t = None, 1.0
            self.update()
        self.begin_hidden()
        self._run(0, self.bw, 170, QEasingCurve.Type.OutCubic, self._step_w, land)

    def play_out(self, on_gone, delay=0):
        def go():
            self.mode, self.t = "out", 0.0
            self._run(0.0, 1.0, 420, QEasingCurve.Type.Linear, self._step_t, shrink)

        def shrink():
            self.mode = "hidden"
            self._run(self.width(), 0, 170, QEasingCurve.Type.InCubic, self._step_w, on_gone)
        if delay:
            self.later(delay, go)
        else:
            go()

    def _xf(self):
        t = QTransform()
        t.translate(self.width() / 2, self.height() / 2 + self.yoff)
        t.rotate(self.angle)
        return t

    def _hit(self, pos, grow=0.0) -> bool:
        inv, ok = self._xf().inverted()
        return ok and QRectF(-self.dw / 2 - grow, -self.dh / 2 - grow, self.dw + 2 * grow,
                             self.dh + 2 * grow).contains(inv.map(QPointF(pos)))

    def _set_hover(self, on: bool):
        if on == self._hover_on:
            return
        self._hover_on = on
        if on:
            try:
                self._ensure_pop()
            except Exception:
                self._hover_on = False
                raise
            self.board._hover_card = self
            self.raise_()
        elif self.board._hover_card is self:
            self.board._hover_card = None
        if not self._hover_timer.isActive():
            self._hover_clock.start()
            self._hover_timer.start()

    def _ensure_pop(self):
        if self.fc.pop is None:
            self.fc.pop = bake_pop(self.item, self.fc, self.board._dpr(), self.board.thumb)
        self.board.note_pop(self.item.id)

    @guarded()
    def _step_hover(self):
        dt = min(0.05, self._hover_clock.restart() / 1000.0)
        target = 1.0 if self._hover_on else 0.0
        x, v, w = self.hover_t - target, self._hover_v, HOVER_OMEGA
        e = math.exp(-w * dt)
        j = v + w * x
        x, v = (x + j * dt) * e, (v - j * w * dt) * e
        t = target + x
        if t < 0.0 or t > 1.0:
            t, v = max(0.0, min(1.0, t)), 0.0
        if abs(t - target) < 0.0015 and abs(v) < 0.03:
            t, v = target, 0.0
            self._hover_timer.stop()
        self.hover_t, self._hover_v = t, v
        self.update()
        if not self._hover_timer.isActive() and not self._hover_on:
            self.board.restack()

    def reset_hover(self):
        self._hover_on, self.hover_t, self._hover_v = False, 0.0, 0.0
        self._hover_timer.stop()
        self.update()

    @guarded()
    def update_hover(self, pos):
        ok = self.mode is None and not self.board.busy
        inside = ok and self._hit(pos, 7.0 if self._hover_on else 0.0)
        if ok and self._hit(pos):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()
        self._set_hover(bool(inside))

    @guarded()
    def leaveEvent(self, e):
        self._set_hover(False)
        self.unsetCursor()

    def _draw_pop_shadow(self, p, tr, h):
        p.save()
        p.setTransform(tr)
        p.setPen(Qt.PenStyle.NoPen)
        dw, dh = self.dw, self.dh
        for g, a in ((4.0, 10), (2.5, 14), (1.2, 20)):
            p.setBrush(QColor(0, 0, 0, int(a * h)))
            p.drawRoundedRect(QRectF(-dw / 2 - g, -dh / 2 - g + 2 + 3 * h, dw + 2 * g, dh + 2 * g), 4 + g, 4 + g)
        p.restore()

    def _draw_pop_face(self, p, x, y, sc, h):
        fc = self.fc
        pop = fc.pop
        if pop is None:
            p.drawPixmap(QRectF(x - fc.w * sc / 2, y - fc.h * sc / 2, fc.w * sc, fc.h * sc), fc.pm, QRectF(fc.pm.rect()))
            return
        if h >= 0.9995:
            p.drawPixmap(QPointF(x - fc.w / 2, y - fc.h / 2), pop)
            return
        r = sc / (1 + POP_SCALE)
        w, hh = fc.w * r, fc.h * r
        p.drawPixmap(QRectF(x - w / 2, y - hh / 2, w, hh), pop, QRectF(pop.rect()))

    def _pop_centre(self, p, cx, cy, h):
        fc = self.fc
        a = snap_point(p, cx - fc.w / 2, cy - fc.h / 2)
        b = snap_point(p, cx - fc.w / 2, cy - POP_LIFT - fc.h / 2)
        return QPointF(a.x() + fc.w / 2 + (b.x() - a.x()) * h, a.y() + fc.h / 2 + (b.y() - a.y()) * h)

    @guarded()
    def paintEvent(self, _):
        if self.mode == "hidden":
            return
        fc = self.fc
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        cx, cy = self.width() / 2, self.height() / 2 + self.yoff

        t = self.t
        mul, dy, extra, alpha, lift, ps = 1.0, 0.0, 0.0, 1.0, 0.0, 1.0
        if self.mode == "in":
            c = ease_out(min(1.0, t / 0.55))
            mul, dy, extra = 1 + 0.12 * (1 - c), -10 * (1 - c), 6 * self.spin * (1 - c)
            alpha = min(1.0, t / 0.3)
            pp = max(0.0, min(1.0, (t - 0.5) / 0.5))
            lift, ps = PIN_LIFT * (1 - ease_in(pp)), 1 + PIN_GROW * (1 - ease_in(pp))
            mul *= 1 - 0.018 * math.sin(math.pi * pp)
        elif self.mode == "out":
            pl = min(1.0, t / 0.3)
            lift, ps = PIN_LIFT * ease_out(pl), 1 + PIN_GROW * ease_out(pl)
            f = max(0.0, (t - 0.3) / 0.7)
            dy, extra, alpha, mul = 80 * f * f, -20 * self.spin * f, 1 - f ** 1.4, 1 + 0.06 * f
        h = self.hover_t
        popped = self.mode is None and h > 0.002
        p.setOpacity(max(0.0, min(1.0, alpha)) * self._fade)

        if self.mode is None and not popped:
            p.drawPixmap(snap_point(p, cx - fc.w / 2, cy - fc.h / 2), fc.pm)
            tr = QTransform()
            tr.translate(cx, cy)
            tr.rotate(self.angle)
        elif popped:
            sc = 1 + POP_SCALE * h
            mid = self._pop_centre(p, cx, cy, h)
            tr = QTransform()
            tr.translate(mid.x(), mid.y())
            tr.rotate(self.angle)
            tr.scale(sc, sc)
            self._draw_pop_shadow(p, tr, h)
            self._draw_pop_face(p, mid.x(), mid.y(), sc, h)
        else:
            tr = QTransform()
            tr.translate(cx, cy + dy)
            tr.rotate(self.angle + extra)
            tr.scale(mul, mul)
            m = QTransform()
            m.translate(cx, cy + dy)
            m.rotate(extra)
            m.scale(mul, mul)
            p.setTransform(m)
            p.drawPixmap(QPointF(-fc.w / 2, -fc.h / 2), fc.pm)
        p.setTransform(tr)
        dw, dh = self.dw, self.dh
        draw_pin(p, 0, -dh / 2 + 13, QColor(self.pin_col[0]), QColor(self.pin_col[1]), lift, ps)

        if self.item.kept:
            draw_star(p, dw / 2 - 11, dh / 2 - 11, 6.5)

    @guarded()
    def mousePressEvent(self, e):
        if self.mode in ("hidden", "out"):
            e.ignore()
            return
        if e.button() == Qt.MouseButton.LeftButton and self._hit(e.position()):
            self._press = e.position().toPoint()
            self._suppress = False
        else:
            e.ignore()

    @guarded()
    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            self.update_hover(e.position())
        if self._press is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        if (e.position().toPoint() - self._press).manhattanLength() < QApplication.startDragDistance():
            return
        self._press = None
        self._set_hover(False)
        self.board.ops.start_drag(self.item, self)

    @guarded()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._press is not None and not self._suppress:
            self.board.ops.copy_item(self.item)
        self._press = None

    @guarded()
    def mouseDoubleClickEvent(self, e):
        if self.mode is not None or not self._hit(e.position()):
            e.ignore()
            return
        self._suppress = True
        self.board.ops.open_item(self.item)

    @guarded()
    def contextMenuEvent(self, e):
        if self.mode in ("hidden", "out") or not self._hit(e.pos()):
            e.ignore()
            return
        self._press = None
        self._set_hover(False)
        m = styled_menu()
        it = self.item
        m.addAction("Unkeep" if it.kept else "Keep", lambda: self.board.ops.toggle_keep(it))
        m.addAction("Copy", lambda: self.board.ops.copy_item(it))
        if it.kind == "text":
            m.addAction("Edit\u2026", lambda: self.board.ops.edit_text(it))
        else:
            m.addAction("Open", lambda: self.board.ops.open_item(it))
            m.addAction("Show in Explorer", lambda: self.board.ops.show_in_explorer(it))
        m.addSeparator()
        m.addAction("Unpin", lambda: self.board.ops.remove(it))
        self.board.busy = True
        try:
            m.exec(e.globalPos())
        finally:
            self.board.busy = False
