from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPoint, QTimer, QVariantAnimation
from PySide6.QtGui import QPainter, QRegion
from PySide6.QtWidgets import QWidget

from ..core.log import log
from ..ui.painting import blank_pixmap
from .overlay import FlipCover

if TYPE_CHECKING:
    from .window import Board

RECONCILE_MS = 320


class Flipper:
    def __init__(self, board: "Board"):
        self.board = board
        self.cover = FlipCover(board)
        self._anim: QVariantAnimation | None = None
        self._token = 0
        self._guard = QTimer(board, singleShot=True, interval=RECONCILE_MS)
        self._guard.timeout.connect(self._reconcile)

    def _snapshot(self):
        pm = blank_pixmap(self.board.width(), self.board.height(), self.board._dpr())
        lay = self.board.layout()
        if lay is not None:
            lay.activate()
        p = QPainter(pm)
        self.board.render(p, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
        p.end()
        return pm

    def _settle(self):
        a = self.board._scroll_anim
        if a is not None and a.state() == QAbstractAnimation.State.Running:
            end = a.endValue()
            a.stop()
            if end is not None:
                self.board.scroller.horizontalScrollBar().setValue(int(end))
        self.board.edge_l.stop()
        self.board.edge_r.stop()
        self.board.slide._grab = None

    def _stop_anim(self):
        old, self._anim = self._anim, None
        if old is not None:
            try:
                old.stop()
                old.deleteLater()
            except RuntimeError:
                pass

    def _drop_cover(self):
        self.cover.hide()
        self.cover.clear()

    def start(self, opening: bool):
        try:
            self._start(opening)
        except Exception:
            log.exception("Flip animation failed")
            self._token += 1
            self._stop_anim()
            self._drop_cover()
            self.board.show() if opening else self.board.hide()
        self._guard.start()

    def _prepare(self, angle: float):
        board, cover = self.board, self.cover
        board.move(board._shown_pos())
        cover.setGeometry(board.rect())
        cover.set_snapshot(self._snapshot())
        cover.angle = angle
        cover.show()
        cover.raise_()

    def _start(self, opening: bool):
        self._token += 1
        token = self._token
        self._stop_anim()
        board, cover = self.board, self.cover
        if opening:
            if not cover.isVisible():
                if board.isVisible():
                    self._finish_open(token)
                    return
                self._prepare(-90.0)
                board.show()
                board.raise_()
            self._animate(True, token)
        else:
            if not board.isVisible():
                self._finish_close(token)
                return
            if not cover.isVisible():
                self._settle()
                self._prepare(0.0)
                cover.repaint()
            self._animate(False, token)

    def _animate(self, opening: bool, token):
        start = self.cover.angle
        target = 0.0 if opening else -90.0
        if abs(target - start) < 0.01:
            self._flip_done(opening, token)
            return
        anim = QVariantAnimation(self.board)
        anim.setStartValue(start)
        anim.setEndValue(target)
        anim.setDuration(int(self.board._anim_ms * abs(target - start) / 90) + 30)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic if opening else QEasingCurve.Type.InCubic)
        anim.valueChanged.connect(lambda v: self._flip_step(v, token))

        def finished():
            if self._anim is anim:
                self._anim = None
            anim.deleteLater()
            self._flip_done(opening, token)
        anim.finished.connect(finished)
        self._anim = anim
        anim.start()

    def _flip_step(self, v, token):
        if token != self._token:
            return
        self.cover.angle = float(v)
        self.cover.update()

    def _flip_done(self, opening, token):
        if token != self._token:
            return
        if opening and self.board.shown:
            self.cover.angle = 0.0
            self.cover.repaint()
            self._finish_open(token)
        elif not opening and not self.board.shown:
            self._finish_close(token)
        else:
            self._drop_cover()
        self._guard.start()

    def _finish_open(self, token):
        if token != self._token:
            return
        board = self.board
        self._drop_cover()
        if not board.isVisible():
            board.show()
        board.raise_()
        if board._want_activate:
            board.activateWindow()
        board._want_activate = False
        board._update_arrows()
        board._run_pin_queue()
        self._guard.start()

    def _finish_close(self, token):
        if token != self._token:
            return
        board = self.board
        board.hide()
        self._drop_cover()
        board._reset_hover()
        board._want_activate = False
        board.set_idle(True)
        board.schedule_trim()
        self._guard.start()

    def _reconcile(self):
        if self._anim is not None:
            self._guard.start()
            return
        board, cover = self.board, self.cover
        try:
            if cover.isVisible():
                self._drop_cover()
            if board.shown:
                if not board.isVisible():
                    board.show()
                    board.raise_()
                    board._run_pin_queue()
            elif board.isVisible():
                board.hide()
        except RuntimeError:
            pass
