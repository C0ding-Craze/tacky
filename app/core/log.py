import functools
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

from .config import ROOT

log = logging.getLogger("tacky")
_ready = False


def setup():
    global _ready
    if _ready:
        return
    _ready = True
    log.setLevel(logging.INFO)
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
        h = RotatingFileHandler(ROOT / "tacky.log", maxBytes=150_000, backupCount=1, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)
    except OSError:
        log.addHandler(logging.NullHandler())

    def on_error(kind, value, tb):
        if issubclass(kind, KeyboardInterrupt):
            sys.__excepthook__(kind, value, tb)
            return
        log.error("Unhandled error", exc_info=(kind, value, tb))

    def on_thread_error(a: threading.ExceptHookArgs):
        if a.exc_value is not None:
            log.error("Error in thread %s", a.thread, exc_info=(a.exc_type, a.exc_value, a.exc_traceback))

    sys.excepthook = on_error
    threading.excepthook = on_thread_error


def guarded(default=None):
    def deco(fn):
        @functools.wraps(fn)
        def run(*a, **k):
            try:
                return fn(*a, **k)
            except Exception:
                log.exception("%s failed", fn.__qualname__)
                return default
        return run
    return deco
