import os
import shutil
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QMimeData, QStandardPaths, QTimer
from PySide6.QtGui import QGuiApplication, QImageReader

from ..core.config import IMAGE_EXT, ITEMS_DIR
from ..core.log import guarded
from ..core.store import Item
from .winkeys import clip_seq, key, VK_C, VK_CONTROL, VK_LWIN, VK_MENU, VK_RWIN

if TYPE_CHECKING:
    from ..board.window import Board


class Capture:

    def __init__(self, board: "Board"):
        self.board = board
        self._ignore_clip_until = 0.0
        self._snip_until = 0.0
        self._last_snip = 0.0
        self._prev_clip: QMimeData | None = None
        self._shots: dict[str, list[int]] = {}
        self._dir_mtime = None
        self.seen: set[str] = set()
        self._shot_timer = QTimer(board, interval=250)
        self._shot_timer.timeout.connect(self._shots_tick)
        self.shots_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)) / "Screenshots"
        try:
            if self.shots_dir.is_dir():
                self.seen = {p.name for p in self.shots_dir.iterdir()}
        except OSError:
            pass
        self.watch = QTimer(board, interval=1000)
        self.watch.timeout.connect(self._poll_screenshots)
        self.watch.start()
        QGuiApplication.clipboard().dataChanged.connect(self._on_clip_changed)

    def note_snip(self):
        self._snip_until = time.time() + 90

    def guard_clip(self):
        self._ignore_clip_until = time.time() + 0.8

    def _poll_screenshots(self):
        try:
            m = self.shots_dir.stat().st_mtime_ns
            if m == self._dir_mtime:
                return
            self._dir_mtime = m
            names = {p.name for p in self.shots_dir.iterdir()}
        except OSError:
            return
        for n in sorted(names - self.seen):
            self.seen.add(n)
            p = self.shots_dir / n
            if p.suffix.lower() in IMAGE_EXT:
                self._shots[str(p)] = [-1, 0]
                if not self._shot_timer.isActive():
                    self._shot_timer.start()

    @guarded()
    def _shots_tick(self):
        for path, st in list(self._shots.items()):
            try:
                size = os.path.getsize(path)
            except OSError:
                del self._shots[path]
                continue
            if size > 0 and size == st[0]:
                st[1] += 1
            else:
                st[0], st[1] = size, 0
            if st[1] >= 2:
                del self._shots[path]
                self._import_shot(Path(path))
        if not self._shots:
            self._shot_timer.stop()

    @guarded()
    def _import_shot(self, p: Path):
        if time.time() - self._last_snip < 5:
            return
        dest = ITEMS_DIR / f"{uuid.uuid4().hex}{p.suffix.lower()}"
        try:
            shutil.copyfile(p, dest)
        except OSError:
            dest.unlink(missing_ok=True)
            return
        if not QImageReader(str(dest)).canRead():
            dest.unlink(missing_ok=True)
            return
        self._last_snip = time.time()
        self._snip_until = 0
        self.board.ops.add_item(Item(kind="image", path=str(dest), owned=True))

    @guarded()
    def _on_clip_changed(self):
        now = time.time()
        if not self.board.store.pin_snips or now < self._ignore_clip_until or now > self._snip_until:
            return
        md = QGuiApplication.clipboard().mimeData()
        if md and md.hasImage() and not md.hasUrls():
            img = QGuiApplication.clipboard().image()
            if not img.isNull():
                self._snip_until = 0
                self._last_snip = now
                self.board.ops.add_qimage(img)

    @guarded()
    def pin_selection(self):
        cb = QGuiApplication.clipboard()
        old = cb.mimeData()
        prev = QMimeData()
        for f in old.formats():
            prev.setData(f, old.data(f))
        if old.hasImage():
            prev.setImageData(old.imageData())
        self._prev_clip = prev
        seq = clip_seq()
        for vk in (VK_LWIN, VK_RWIN, VK_MENU):
            key(vk, True)
        QTimer.singleShot(40, lambda: self._send_copy(seq))

    @guarded()
    def _send_copy(self, seq):
        key(VK_CONTROL, False); key(VK_C, False); key(VK_C, True); key(VK_CONTROL, True)
        self._poll_clip(seq, 0)

    @guarded()
    def _poll_clip(self, seq, n):
        if clip_seq() != seq:
            QTimer.singleShot(60, self._read_selection)
        elif n >= 15:
            self._restore_clip()
            self.board.flash()
            self.board.toast("Nothing selected")
        else:
            QTimer.singleShot(30, lambda: self._poll_clip(seq, n + 1))

    @guarded()
    def _read_selection(self):
        try:
            md = QGuiApplication.clipboard().mimeData()
            if not self.board.ops.add_urls(md.urls()):
                if md.hasImage():
                    img = QGuiApplication.clipboard().image()
                    if not img.isNull():
                        self.board.ops.add_qimage(img)
                elif md.hasText():
                    self.board.ops.add_text(md.text())
        finally:
            self._restore_clip()

    def _restore_clip(self):
        self.guard_clip()
        cb = QGuiApplication.clipboard()
        if self._prev_clip is not None and (self._prev_clip.formats() or self._prev_clip.hasImage()):
            cb.setMimeData(self._prev_clip)
        else:
            cb.clear()
        self._prev_clip = None
