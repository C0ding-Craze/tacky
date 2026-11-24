import os
import sys
from pathlib import Path


IS_WIN = sys.platform == "win32"
FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = Path(getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parents[2])
ASSETS_DIR = BASE_DIR / "assets"
ROOT = Path(os.environ.get("TACKY_HOME") or
            (Path(os.environ.get("APPDATA", Path.home() / ".config")) / "Tacky"))
ITEMS_DIR = ROOT / "items"
JSON_PATH = ROOT / "board.json"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
BOARD_STYLES = {
    "Green velvet": ("#1D4A31", "velvet"),
    "Blue velvet": ("#1D3A62", "velvet"),
    "Burgundy velvet": ("#591B2B", "velvet"),
    "Charcoal velvet": ("#25282D", "velvet"),
    "Cork": ("#C0905C", "tack"),
}
DEFAULT_STYLE = "Green velvet"
PIN_COLORS = [("#D93A3A", "#FF9A90"), ("#2F6FD6", "#9CC2FF"), ("#E8B820", "#FFEA90"), ("#2E9E5B", "#9BE8B8"),
              ("#8E44C9", "#DDB0F8"), ("#E8742A", "#FFC08A"), ("#17A8A8", "#8BEAEA"), ("#D9488E", "#FFA6D0")]
NOTE_COLORS = ["#FFF2A8", "#FFD9E2", "#D8ECFF", "#DFF5CC", "#FFE3BF"]
HK = {"pin": "Win+C"}

PAD = 18
BOARD_H = 235
INSET, INSET_B = 18, 25
CARD_H = 200
FADE_START_DAYS, EXPIRE_DAYS = 4, 7
