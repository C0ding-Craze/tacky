import hashlib
import json
import math
import os
import random
import time
import uuid
from dataclasses import asdict, dataclass

from .config import BOARD_STYLES, DEFAULT_STYLE, ITEMS_DIR, JSON_PATH, NOTE_COLORS, PIN_COLORS
from .log import log


@dataclass
class Item:
    kind: str
    id: str = ""
    path: str = ""
    text: str = ""
    created: float = 0.0
    kept: bool = False
    owned: bool = False
    angle: float = 0.0
    yoff: float = 99.0
    pin: int = -1
    size: float = 0.5

    def __post_init__(self):
        self.id = self.id or uuid.uuid4().hex
        self.created = self.created or time.time()


def assign_look(it: Item, neighbours):
    ang = 6.0
    for _ in range(25):
        ang = random.uniform(2.5, 15) * random.choice((-1, 1))
        if all(abs(ang - n.angle) >= 7 for n in neighbours):
            break
    it.angle = ang
    it.yoff = random.uniform(-17, 17)
    free = [i for i in range(len(PIN_COLORS)) if i not in {n.pin for n in neighbours}]
    it.pin = random.choice(free or list(range(len(PIN_COLORS))))
    it.size = random.random()


def _float(v, default, lo=None, hi=None):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    if lo is not None:
        f = max(lo, f)
    if hi is not None:
        f = min(hi, f)
    return f


def _load_item(d: dict) -> Item:
    kind = d.get("kind")
    if kind not in ("text", "image", "file"):
        raise ValueError(f"unknown card kind {kind!r}")
    it = Item(kind=kind)
    it.id = str(d.get("id") or it.id)
    it.path = str(d.get("path") or "")
    it.text = str(d.get("text") or "")
    it.created = _float(d.get("created"), it.created, 0.0)
    it.kept, it.owned = bool(d.get("kept")), bool(d.get("owned"))
    it.angle = _float(d.get("angle"), 0.0, -45.0, 45.0)
    it.yoff = _float(d.get("yoff"), 99.0)
    it.size = _float(d.get("size"), 0.5, 0.0, 1.0)
    try:
        it.pin = int(d.get("pin", -1))
    except (TypeError, ValueError):
        it.pin = -1
    return it


class Store:
    def __init__(self):
        self.items: list[Item] = []
        self.speed, self.felt, self.pin_snips = "Normal", DEFAULT_STYLE, True
        try:
            ITEMS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            log.exception("Could not create %s", ITEMS_DIR)
        try:
            d = json.loads(JSON_PATH.read_text(encoding="utf-8"))
            if not isinstance(d, dict):
                raise ValueError("board.json is not an object")
            seen = set()
            for raw in d.get("items") or []:
                try:
                    it = _load_item(raw)
                except Exception as exc:
                    log.warning("Skipped a card in board.json: %s", exc)
                    continue
                if it.id not in seen:
                    seen.add(it.id)
                    self.items.append(it)
            if d.get("speed") in ("Instant", "Normal", "Slow"):
                self.speed = d["speed"]
            if d.get("felt") in BOARD_STYLES:
                self.felt = d["felt"]
            self.pin_snips = bool(d.get("pin_snips", True))
            if _float(d.get("ver"), 1.0) < 5:
                self.felt = DEFAULT_STYLE
        except FileNotFoundError:
            pass
        except Exception:
            log.exception("board.json could not be read; keeping a copy as board.bad")
            self.items = []
            try:
                JSON_PATH.replace(JSON_PATH.with_suffix(".bad"))
            except OSError:
                pass

    def save(self) -> bool:
        tmp = JSON_PATH.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps({"items": [asdict(i) for i in self.items], "speed": self.speed,
                                       "felt": self.felt, "pin_snips": self.pin_snips, "ver": 5}, indent=2),
                           encoding="utf-8")
            os.replace(tmp, JSON_PATH)
            return True
        except Exception:
            log.exception("Could not save board.json")
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False


def note_color(item_id: str) -> str:
    h = int(hashlib.md5(f"{item_id}:5".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return NOTE_COLORS[int(h * len(NOTE_COLORS)) % len(NOTE_COLORS)]  # md5 keeps each note's colour stable across versions
