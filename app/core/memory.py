import gc

from .config import IS_WIN


def trim():
    gc.collect()
    if not IS_WIN:
        return
    try:
        import ctypes
        from ctypes import wintypes
        k = getattr(ctypes, "windll").kernel32
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.K32EmptyWorkingSet.argtypes = [wintypes.HANDLE]
        k.K32EmptyWorkingSet(k.GetCurrentProcess())
    except Exception:
        pass
