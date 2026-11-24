import time

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..core.config import BOARD_H, BOARD_STYLES, HK, INSET, INSET_B, PAD
from ..ui.painting import blank_pixmap
from ..ui.theme import SCROLL_QSS, TOAST_QSS
from ..core.log import guarded, log
from ..core.memory import trim
from ..core.store import assign_look, Store
from ..system.winkeys import snip_shortcut_down
from .textures import make_texture
from .boardart import draw_board, frame_paths
from ..cards.card import Card
from ..ui.widgets import EdgeArrow, HScroll, SlideBar, styled_menu
from .flipper import Flipper
from ..cards.actions import ItemActions
from ..system.capture import Capture


class Board(QWidget):

    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        self.shown = False
        self.busy = False
        self._internal_drag = False
        self._dwell: float | None = None
        self._leave: float | None = None
        self._hold_until = 0.0
        self._want_activate = False
        self._hover_card: Card | None = None
        self._need_leave_top = False

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.setWindowTitle("Tacky")

        self.resize(min(1100, int(self._geo().width() * 0.72)), BOARD_H + PAD)

        self.row = QHBoxLayout()
        self.row.setContentsMargins(8, 0, 8, 0)
        self.row.setSpacing(-6)
        self.row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        holder = QWidget()
        holder.setObjectName("holder")
        holder.setLayout(self.row)
        holder.setStyleSheet("#holder{background:transparent;}")
        self.scroller = HScroll()
        self.scroller.setWidget(holder)
        self.scroller.setWidgetResizable(True)
        self.scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroller.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroller.setStyleSheet(SCROLL_QSS)
        self.scroller.viewport().setAutoFillBackground(False)
        self.scroller.wheeled.connect(self._stop_glide)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(PAD + INSET + 2, 4, PAD + INSET + 2, PAD + INSET_B + 2)
        outer.addWidget(self.scroller)

        self.face_cache = {}
        self.thumb_cache = {}
        self._pop_lru: list[str] = []
        self._rehover_timer = QTimer(self, singleShot=True, interval=30)
        self._rehover_timer.timeout.connect(self._rehover)
        self._trim_timer = QTimer(self, singleShot=True, interval=3000)
        self._trim_timer.timeout.connect(trim)
        self._pin_queue: list[Card] = []
        self._bg: QPixmap | None = None
        self.flipper = Flipper(self)
        self.ops = ItemActions(self)
        self.capture = Capture(self)
        self._scroll_anim: QPropertyAnimation | None = None

        self.empty = QLabel("", self)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.update_hint()

        bar = self.scroller.horizontalScrollBar()
        self.edge_l = EdgeArrow(-1, self)
        self.edge_r = EdgeArrow(1, self)
        self.edge_l.step.connect(lambda: self.scroll_by(-190))
        self.edge_r.step.connect(lambda: self.scroll_by(190))
        self.edge_l.hold.connect(lambda: bar.setValue(bar.value() - 15))
        self.edge_r.hold.connect(lambda: bar.setValue(bar.value() + 15))
        self.slide = SlideBar(bar, self)
        bar.valueChanged.connect(self._update_arrows)
        bar.valueChanged.connect(self._queue_rehover)
        bar.rangeChanged.connect(self._update_arrows)

        self.toast_label = QLabel("", self)
        self.toast_label.setStyleSheet(TOAST_QSS)
        self.toast_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.toast_label.hide()
        self.toast_timer = QTimer(self, singleShot=True, interval=1200)
        self.toast_timer.timeout.connect(self.toast_label.hide)

        self.tick = QTimer(self, interval=self.IDLE_MS)
        self.tick.timeout.connect(self._tick)
        self.tick.start()

        self.expiry = QTimer(self, interval=30 * 60 * 1000)
        self.expiry.timeout.connect(lambda: self.ops.remove_expired() and self.refresh_cards())
        self.expiry.start()

        self.ops.remove_expired()
        self.refresh_cards()
        self.apply_style()
        self._background()
        QTimer.singleShot(1500, trim)

    IDLE_MS, ACTIVE_MS = 70, 40

    def set_idle(self, idle: bool):
        self.tick.setInterval(self.IDLE_MS if idle else self.ACTIVE_MS)

    def _geo(self):
        return QGuiApplication.primaryScreen().geometry()

    def _shown_pos(self):
        g = self._geo()
        return QPoint(g.x() + (g.width() - self.width()) // 2, g.y())

    @property
    def _dwell_ms(self):
        return {"Instant": 0, "Slow": 600}.get(self.store.speed, 250)

    @property
    def _anim_ms(self):
        return {"Instant": 120, "Slow": 460}.get(self.store.speed, 270)

    def _dpr(self):
        return QGuiApplication.primaryScreen().devicePixelRatio()

    def thumb(self, path):
        cache = self.thumb_cache
        img = cache.pop(path, None)
        if img is None:
            img = self._decode(path)
        if img is not None:
            cache[path] = img
            while len(cache) > 4:
                cache.pop(next(iter(cache)))
        return img

    def _decode(self, path):
        try:
            reader = QImageReader(path)
            size = reader.size()
            if size.isValid() and size.width() > 0 and size.height() > 0:
                dpr = max(1.0, self._dpr())
                f = min(1.0, 430 * dpr / size.height(), 900 * dpr / size.width())
                if f < 1.0:
                    reader.setScaledSize(QSize(max(1, round(size.width() * f)), max(1, round(size.height() * f))))
            img = reader.read()
            return None if img.isNull() else img
        except Exception:
            log.exception("Could not read picture %s", path)
            return None

    def note_pop(self, item_id):
        lru = self._pop_lru
        if item_id in lru:
            lru.remove(item_id)
        lru.append(item_id)
        while len(lru) > 3:
            fc = self.face_cache.get(lru.pop(0))
            if fc is not None:
                fc.pop = None

    def drop_pops(self):
        for i in self._pop_lru:
            fc = self.face_cache.get(i)
            if fc is not None:
                fc.pop = None
        self._pop_lru.clear()
        self.thumb_cache.clear()

    def schedule_trim(self):
        self._trim_timer.start()

    def _queue_rehover(self, *_):
        if self.isVisible() and not self._rehover_timer.isActive():
            self._rehover_timer.start()

    @guarded()
    def _rehover(self):
        pos = QCursor.pos()
        top = QApplication.widgetAt(pos) if self.isVisible() else None
        for c in self._cards():
            if c is top:
                c.update_hover(QPointF(c.mapFromGlobal(pos)))
            elif c._hover_on:
                c._set_hover(False)

    def _cards(self):
        items = (self.row.itemAt(i) for i in range(self.row.count()))
        return [w for it in items if it is not None and isinstance(w := it.widget(), Card)]

    def restack(self):
        try:
            for w in self._cards():
                w.raise_()
            if self._hover_card is not None:
                self._hover_card.raise_()
        except RuntimeError:
            self._hover_card = None

    def _reset_hover(self):
        self._hover_card = None
        for w in self._cards():
            w.reset_hover()
        self.drop_pops()
        self.restack()

    def show_board(self, activate=False):
        self._dwell = self._leave = None
        self._need_leave_top = False
        self.set_idle(False)
        if activate:
            self._hold_until = time.time() + 5
            self._want_activate = True
        if not self.shown:
            self.shown = True
            self.flipper.start(True)
        elif activate and self.isVisible():
            self.activateWindow()

    def hide_board(self):
        if self.shown:
            self.shown = False
            self._hold_until = 0
            self._need_leave_top = True
            self.flipper.start(False)

    def toggle(self):
        self.hide_board() if self.shown else self.show_board(True)

    def flash(self):
        self._hold_until = time.time() + 2.5
        self.show_board()

    def toast(self, msg):
        self.toast_label.setText(msg)
        self.toast_label.adjustSize()
        self.toast_label.move((self.width() - self.toast_label.width()) // 2,
                              BOARD_H - INSET_B - self.toast_label.height() - 6)
        self.toast_label.show()
        self.toast_label.raise_()
        self._cover_on_top()
        self.toast_timer.start()

    @guarded()
    def _tick(self):
        if snip_shortcut_down():
            self.capture.note_snip()
        pos, geo = QCursor.pos(), self._geo()
        rel = (pos.x() - geo.x()) / max(1, geo.width())
        on_top = pos.y() <= geo.y() and 0.35 <= rel <= 0.65 and geo.x() <= pos.x() < geo.right()
        now = time.time()

        if not self.shown:
            if self._need_leave_top:
                if on_top:
                    self._dwell = None
                    return
                self._need_leave_top = False
            if on_top:
                self._dwell = self._dwell or now
                if (now - self._dwell) * 1000 >= self._dwell_ms:
                    self.show_board()
            else:
                self._dwell = None
            return

        sp = self._shown_pos()
        inside = QRect(sp.x(), sp.y(), self.width(), self.height() - PAD + 6).contains(pos)
        if inside or on_top or self.busy or now < self._hold_until:
            self._leave = None
        else:
            self._leave = self._leave or now
            if now - self._leave > 0.6:
                self.hide_board()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.hide_board()
        elif e.key() == Qt.Key.Key_Left:
            self.scroll_by(-190)
        elif e.key() == Qt.Key.Key_Right:
            self.scroll_by(190)

    def scroll_by(self, dx):
        bar = self.scroller.horizontalScrollBar()
        a = self._scroll_anim
        base = bar.value()
        if a is None:
            a = self._scroll_anim = QPropertyAnimation(bar, b"value", self)
            a.setDuration(170)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
        elif a.state() == QAbstractAnimation.State.Running:
            base = int(a.endValue())
            a.stop()
        a.setStartValue(bar.value())
        a.setEndValue(max(bar.minimum(), min(bar.maximum(), base + dx)))
        a.start()

    def _stop_glide(self):
        a = self._scroll_anim
        if a is not None and a.state() == QAbstractAnimation.State.Running:
            a.stop()

    def _cover_on_top(self):
        fl = getattr(self, "flipper", None)
        if fl is not None and fl.cover.isVisible():
            fl.cover.raise_()

    def _update_arrows(self, *_):
        bar = self.scroller.horizontalScrollBar()
        can = bar.maximum() > 0
        self.edge_l.setVisible(can and bar.value() > bar.minimum())
        self.edge_r.setVisible(can and bar.value() < bar.maximum())
        self.edge_l.raise_()
        self.edge_r.raise_()
        self._cover_on_top()

    def update_hint(self):
        self.empty.setText(f"Snip something (Win + Shift + S), drop files here,\nor select text and press {HK['pin']}")

    def apply_style(self):
        dark = QColor(BOARD_STYLES[self.store.felt][0]).lightness() < 150
        self.empty.setStyleSheet("color:rgba(255,255,255,175); font-size:11pt;" if dark
                                 else "color:rgba(70,40,15,205); font-size:11pt; font-weight:600;")
        self._bg = None
        self.update()

    def resizeEvent(self, _):
        self._bg = None
        fl = getattr(self, "flipper", None)
        if fl is not None:
            fl.cover.setGeometry(self.rect())
        self.empty.setGeometry(PAD, 0, self.width() - 2 * PAD, self.height() - PAD)
        ih = BOARD_H - INSET_B
        x0 = PAD + INSET
        self.edge_l.setGeometry(x0, 0, 46, ih - 15)
        self.edge_r.setGeometry(self.width() - x0 - 46, 0, 46, ih - 15)
        sw = int(min(400, (self.width() - 2 * x0) * 0.5))
        self.slide.setGeometry((self.width() - sw) // 2, ih + (INSET_B - 9) // 2, sw, 9)
        self._update_arrows()

    def _background(self) -> QPixmap:
        if self._bg is None:  # reset by resizeEvent and apply_style
            dpr = self._dpr()
            base, kind = BOARD_STYLES[self.store.felt]
            pm = blank_pixmap(self.width(), self.height(), dpr)
            p = QPainter(pm)
            draw_board(p, self.width(), lambda w, h: make_texture(w, h, base, kind, dpr))
            p.end()
            self._bg = pm
        return self._bg

    @guarded()
    def paintEvent(self, _):
        QPainter(self).drawPixmap(0, 0, self._background())

    @guarded()
    def refresh_cards(self):
        self._pin_queue.clear()
        self._hover_card = None
        items = self.store.items
        changed = False
        for i, it in enumerate(items):
            if it.yoff == 99.0:
                assign_look(it, [items[j] for j in (i - 1, i + 1) if 0 <= j < len(items) and items[j].yoff != 99.0])
                changed = True
        if changed:
            self.store.save()
        live = {i.id for i in items}
        for k in [k for k in self.face_cache if k not in live]:
            del self.face_cache[k]
        bar = self.scroller.horizontalScrollBar()
        keep_at = bar.value()
        while self.row.count():
            it = self.row.takeAt(0)
            w = it.widget() if it is not None else None
            if w is not None:
                w.deleteLater()
        for item in items:
            try:
                self.row.addWidget(Card(self, item))
            except Exception:
                log.exception("Could not draw a card (%s)", item.kind)
        self.row.addStretch(1)
        if not self.shown:
            self.thumb_cache.clear()  # decoded originals are only needed for hover pops
        self.empty.setVisible(not items)
        if keep_at:
            QTimer.singleShot(0, lambda: bar.setValue(keep_at))

    def _card_for(self, item):
        return next((c for c in self._cards() if c.item is item), None)

    def _board_ready(self):
        return self.shown and self.isVisible() and not self.flipper.cover.isVisible()

    def _run_pin_queue(self):
        if not self._board_ready():
            return
        q, self._pin_queue = self._pin_queue, []
        for n, card in enumerate(q):
            card.later(n * 150, card.play_in)

    def _card_gone(self, card, it):
        self.row.removeWidget(card)
        card.deleteLater()
        self.ops.delete_owned(it)
        self.empty.setVisible(not self.store.items)

    @guarded()
    def contextMenuEvent(self, e):
        pt = QPointF(self.mapFromGlobal(e.globalPos()))
        outer, inner = frame_paths(self.width())
        if not outer.contains(pt) or inner.contains(pt):
            e.ignore()
            return
        menu = styled_menu()
        act = menu.addAction("Clear whole board", self.ops.clear_all)
        act.setEnabled(bool(self.store.items))
        self.busy = True
        try:
            menu.exec(e.globalPos())
        finally:
            self.busy = False

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if not self._internal_drag and (md.hasUrls() or md.hasText()):
            e.acceptProposedAction()

    @guarded()
    def dropEvent(self, e):
        md = e.mimeData()
        if not self.ops.add_urls(md.urls()) and md.hasText():
            self.ops.add_text(md.text())
        e.acceptProposedAction()