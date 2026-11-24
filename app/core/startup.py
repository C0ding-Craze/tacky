import sys
from pathlib import Path

from .config import FROZEN


LAUNCHER = Path(__file__).resolve().parents[2] / "tacky.py"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, "Tacky")
            return True
    except OSError:
        return False


def set_startup(on):
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            exe = sys.executable
            if FROZEN:
                cmd = f'"{exe}"'
            else:
                if exe.lower().endswith("python.exe"):
                    exe = exe[:-10] + "pythonw.exe"
                cmd = f'"{exe}" "{LAUNCHER}"'
            winreg.SetValueEx(k, "Tacky", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, "Tacky")
            except OSError:
                pass
