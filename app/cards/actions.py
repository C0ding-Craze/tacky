import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QFile, QMimeData, QPoint, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QDrag, QGuiApplication, QImage
from PySide6.QtWidgets import QWidget

from ..core.config import EXPIRE_DAYS, IMAGE_EXT, IS_WIN, ITEMS_DIR, PIN_COLORS
from ..core.log import guarded, log
from ..core.store import assign_look, Item, note_color
from .card import Card
from ..ui.paperdialog import PaperDialog

if TYPE_CHECKING:
    from ..board.window import Board


class ItemActions:

    def __init__(self, board: "Board"):
        self.board = board

    def _has_file(self, it: Item) -> bool:
        found = Path(it.path).exists()
        if not found:
            self.board.toast("File not found")
        return found

    @guarded()
    def copy_item(self, it: Item):
        mime = QMimeData()
        if it.kind == "text":
            mime.setText(it.text)
        else:
            if not self._has_file(it):
                return
            if it.kind == "image" or Path(it.path).suffix.lower() in IMAGE_EXT:
                img = QImage(it.path)
                if not img.isNull():
                    mime.setImageData(img)
            mime.setUrls([QUrl.fromLocalFile(it.path)])
        self.board.capture.guard_clip()
        QGuiApplication.clipboard().setMimeData(mime)
        self.board.toast("Copied")

    @guarded()
    def open_item(self, it: Item):
        if it.kind == "text":
            self.edit_text(it)
        elif self._has_file(it) and not QDesktopServices.openUrl(QUrl.fromLocalFile(it.path)):
            self.board.toast("Couldn't open it")

    @guarded()
    def show_in_explorer(self, it: Item):
        if not self._has_file(it):
            return
        try:
            if IS_WIN:
                subprocess.Popen(["explorer", f"/select,{os.path.normpath(it.path)}"])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(it.path).parent)))
        except OSError:
            log.exception("Could not open Explorer")
            self.board.toast("Couldn't open Explorer")

    @guarded()
    def toggle_keep(self, it: Item):
        it.kept = not it.kept
        self.board.store.save()
        self.board.refresh_cards()

    @guarded()
    def remove(self, it: Item):
        self._remove_all([it])

    @staticmethod
    def delete_owned(it: Item):
        try:
            if it.owned and it.path and Path(it.path).exists():
                res = QFile.moveToTrash(it.path)
                if not (res[0] if isinstance(res, tuple) else res):
                    os.remove(it.path)
        except OSError:
            log.warning("Could not delete %s", it.path)

    def remove_expired(self):
        old = [i for i in self.board.store.items if not i.kept and time.time() - i.created > EXPIRE_DAYS * 86400]
        for i in old:
            self.board.store.items.remove(i)
            self.delete_owned(i)
        if old:
            self.board.store.save()
        return bool(old)

    @guarded()
    def clear_unkept(self):
        self._remove_all([i for i in self.board.store.items if not i.kept])

    @guarded()
    def clear_all(self):
        self._remove_all(list(self.board.store.items))

    def _remove_all(self, gone):
        b = self.board
        cards = [b._card_for(i) for i in gone]
        for it, card in zip(gone, cards):
            if it in b.store.items:
                b.store.items.remove(it)
            b.face_cache.pop(it.id, None)
            if card in b._pin_queue:
                b._pin_queue.remove(card)
        b.store.save()
        if not b._board_ready():
            for it in gone:
                self.delete_owned(it)
            b.refresh_cards()
            return
        for n, (it, card) in enumerate(zip(gone, cards)):
            if card is None:
                self.delete_owned(it)
            else:
                card.play_out(lambda c=card, i=it: b._card_gone(c, i), delay=n * 70)

    def edit_text(self, it: Item):
        self.board.busy = True
        dlg = None
        try:
            dlg = PaperDialog(it.text, note_color(it.id), PIN_COLORS[it.pin % len(PIN_COLORS)])
            g = QGuiApplication.primaryScreen().geometry()
            dlg.move(g.center() - QPoint(dlg.width() // 2, dlg.height() // 2))
            if dlg.exec() and dlg.text().strip():
                it.text = dlg.text().strip()
                self.board.face_cache.pop(it.id, None)
                self.board.store.save()
                self.board.refresh_cards()
        except Exception:
            log.exception("Editing a note failed")
        finally:
            if dlg is not None:
                dlg.deleteLater()
            self.board.busy = False

    def start_drag(self, it: Item, src: QWidget):
        mime = QMimeData()
        if it.kind == "text":
            mime.setText(it.text)
        elif self._has_file(it):
            mime.setUrls([QUrl.fromLocalFile(it.path)])
        else:
            return
        self.board.busy = self.board._internal_drag = True
        try:
            drag = QDrag(src)
            drag.setMimeData(mime)
            if isinstance(src, Card):
                dpr = src.face.devicePixelRatio()
                pm = src.face.scaledToWidth(int(150 * dpr), Qt.TransformationMode.SmoothTransformation)
                pm.setDevicePixelRatio(dpr)
            else:
                pm = src.grab()
            drag.setPixmap(pm)
            drag.setHotSpot(QPoint(int(pm.width() / pm.devicePixelRatio() / 2), int(pm.height() / pm.devicePixelRatio() / 2)))
            drag.exec(Qt.DropAction.CopyAction)
        except Exception:
            log.exception("Drag failed")
        finally:
            self.board.busy = self.board._internal_drag = False

    def add_item(self, it: Item):
        b = self.board
        assign_look(it, b.store.items[:2])
        b.store.items.insert(0, it)
        b.store.save()
        try:
            card = Card(b, it)
        except Exception:
            log.exception("Could not draw the new card")
            b.refresh_cards()
            return
        card.begin_hidden()
        b.row.insertWidget(0, card)
        b.empty.hide()
        b.scroller.horizontalScrollBar().setValue(0)
        b._pin_queue.append(card)
        b.flash()
        if b._board_ready():
            QTimer.singleShot(30, b._run_pin_queue)

    @guarded()
    def add_text(self, text):
        text = (text or "").strip()
        if text:
            self.add_item(Item(kind="text", text=text))

    def add_urls(self, urls) -> bool:
        files = [u.toLocalFile() for u in urls if u.isLocalFile()]
        for f in files:
            self.add_file(f)
        return bool(files)

    @guarded()
    def add_file(self, path):
        if not os.path.exists(path):
            return
        if any(i.kind == "file" and os.path.normcase(i.path) == os.path.normcase(path) for i in self.board.store.items):
            return
        self.add_item(Item(kind="file", path=path))

    @guarded()
    def add_qimage(self, img: QImage):
        dest = ITEMS_DIR / f"{uuid.uuid4().hex}.png"
        try:
            ok = img.save(str(dest))
        except OSError:
            ok = False
        if not ok:
            log.warning("Could not save a picture to %s", dest)
            self.board.toast("Couldn't save the picture")
            return
        self.add_item(Item(kind="image", path=str(dest), owned=True))
