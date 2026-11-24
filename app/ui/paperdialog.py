import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QShortcut, QTextCursor,
    QTextLayout, QTextOption,
)
from PySide6.QtWidgets import QDialog, QFrame, QPlainTextEdit, QPushButton

from .theme import CANCEL_BTN_QSS, HAND_FONTS, MENU_QSS, SAVE_BTN_QSS
from .painting import blank_pixmap, draw_pin
from .widgets import ThinBar


class PaperDialog(QDialog):
    M = 28

    def __init__(self, text, paper_color, pin_colors):
        super().__init__()
        self._under: QPixmap | None = None
        self._over: QPixmap | None = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(620, 560)
        self.paper = QColor(paper_color)
        self.pin = (QColor(pin_colors[0]), QColor(pin_colors[1]))
        self._drag = None

        font = QFont()
        font.setFamilies(HAND_FONTS)
        font.setPointSize(12)
        self.edit = QPlainTextEdit(text, self)
        self.edit.setFont(font)
        self.edit.setFrameShape(QFrame.Shape.NoFrame)
        self.edit.document().setDocumentMargin(0)
        self.edit.setCursorWidth(2)
        self.edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.edit.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.edit.setStyleSheet("QPlainTextEdit{background:transparent; color:#1c3a8c;"
                                "selection-background-color:rgba(70,100,210,90); selection-color:#10246a;}" + MENU_QSS)
        self.vbar = ThinBar(self.edit.verticalScrollBar(), self)
        probe = QTextLayout("Ag", font)
        probe.beginLayout()
        ln = probe.createLine()
        ln.setLineWidth(1000)
        self.lh, self.asc = float(ln.height()), float(ln.ascent())
        probe.endLayout()
        self.edit.verticalScrollBar().valueChanged.connect(lambda *_: self.update())
        self.edit.textChanged.connect(self.update)

        self.save_btn = QPushButton("Save", self)
        self.save_btn.setStyleSheet(SAVE_BTN_QSS)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setStyleSheet(CANCEL_BTN_QSS)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        for keys in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(keys), self).activated.connect(self.accept)

        self.edit.setFocus()
        cur = self.edit.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.edit.setTextCursor(cur)

    def text(self):
        return self.edit.toPlainText()

    def resizeEvent(self, _):
        self._under = self._over = None
        m, w, h = self.M, self.width(), self.height()
        lines = max(3, int((h - 2 * m - 78 - 84) // self.lh))
        self.edit.setGeometry(m + 66, m + 78, w - 2 * m - 66 - 44, int(math.ceil(lines * self.lh)))
        self.vbar.setGeometry(self.edit.x() + self.edit.width() + 12, self.edit.y() + 2, 5, self.edit.height() - 4)
        self.save_btn.adjustSize()
        self.cancel_btn.adjustSize()
        self.save_btn.move(w - m - 52 - self.save_btn.width(), h - m - 28 - self.save_btn.height())
        self.cancel_btn.move(self.save_btn.x() - self.cancel_btn.width() - 6, self.save_btn.y())

    FOLD = 52

    def _sheet_rect(self):
        m = self.M
        return QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)

    def _bake_layers(self) -> tuple[QPixmap, QPixmap]:
        dpr = self.devicePixelRatioF()
        under, over = (blank_pixmap(self.width(), self.height(), dpr) for _ in range(2))
        for pm, fn in ((under, self._paint_base), (over, self._paint_top)):
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            fn(p)
            p.end()
        self._under, self._over = under, over
        return under, over

    def _paint_base(self, p):
        r, fold = self._sheet_rect(), self.FOLD
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(10):
            p.setBrush(QColor(0, 0, 0, 12))
            p.drawRoundedRect(r.adjusted(-i + 3, -i + 6, i + 3, i + 9), 6 + i, 6 + i)

        sheet = QPainterPath()
        sheet.moveTo(r.left(), r.top())
        sheet.lineTo(r.right(), r.top())
        sheet.lineTo(r.right(), r.bottom() - fold)
        sheet.lineTo(r.right() - fold, r.bottom())
        sheet.lineTo(r.left(), r.bottom())
        sheet.closeSubpath()
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, self.paper.lighter(110))
        g.setColorAt(1, self.paper.darker(106))
        p.setBrush(g)
        p.setPen(QPen(QColor(0, 0, 0, 55), 1))
        p.drawPath(sheet)

        p.save()
        p.setClipPath(sheet)
        rng = random.Random(4)
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(900):
            p.setBrush(QColor(90, 60, 20, rng.randint(6, 16)))
            p.drawEllipse(QRectF(rng.uniform(r.left(), r.right()), rng.uniform(r.top(), r.bottom()), 1.4, 1.4))
        p.restore()

    def _paint_top(self, p):
        r, fold = self._sheet_rect(), self.FOLD
        p.setPen(QPen(QColor(210, 75, 75, 150), 1.5))
        p.drawLine(QPointF(r.left() + 54, r.top() + 14), QPointF(r.left() + 54, r.bottom() - 14))

        tri = QPainterPath()
        tri.moveTo(r.right(), r.bottom() - fold)
        tri.lineTo(r.right() - fold, r.bottom())
        tri.lineTo(r.right() - fold, r.bottom() - fold)
        tri.closeSubpath()
        fg = QLinearGradient(r.right() - fold, r.bottom() - fold, r.right(), r.bottom())
        fg.setColorAt(0, self.paper.darker(108))
        fg.setColorAt(1, self.paper.darker(128))
        p.setBrush(fg)
        p.setPen(QPen(QColor(0, 0, 0, 60), 1))
        p.drawPath(tri)

        f = QFont()
        f.setFamilies(HAND_FONTS)
        f.setPointSize(11)
        p.setFont(f)
        p.setPen(QColor(90, 80, 70, 150))
        p.drawText(QRectF(r.left() + 66, r.top() + 34, 260, 30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Edit note")
        draw_pin(p, r.center().x(), r.top() + 26, self.pin[0], self.pin[1])

    def paintEvent(self, _):
        under, over = self._under, self._over
        if under is None or over is None:
            under, over = self._bake_layers()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self._sheet_rect()
        p.drawPixmap(0, 0, under)

        e = self.edit
        off = e.verticalScrollBar().value() * self.lh
        p.save()
        p.setClipRect(QRectF(r.left() + 14, e.y() - 6, r.width() - 28 - self.FOLD * 0.2, e.height() + 12))
        p.setPen(QPen(QColor(80, 120, 190, 105), 1.1))
        y = e.y() + self.asc + 4 - off
        while y < e.y() + e.height() + self.lh:
            if y > e.y() - self.lh:
                p.drawLine(QPointF(r.left() + 14, y), QPointF(r.right() - 14, y))
            y += self.lh
        p.restore()
        p.drawPixmap(0, 0, over)

    def mousePressEvent(self, e):
        self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None
