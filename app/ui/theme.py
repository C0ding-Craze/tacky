INK = "#2A2A2A"
INK_SOFT = "#5A4636"
HAND_FONTS = ["Segoe Print", "Ink Free", "Bradley Hand ITC", "Segoe Script", "Comic Sans MS", "Segoe UI"]

MENU_QSS = """
QMenu { background:#17382A; color:#F3EAD3; border:1px solid #C9A24B; padding:6px; }
QMenu::item { padding:7px 30px 7px 28px; margin:1px 0px; border-radius:5px; background:transparent; }
QMenu::item:selected { background:#D9A441; color:#1A2A1E; }
QMenu::item:disabled { color:#7E9788; background:transparent; }
QMenu::separator { height:1px; background:#2E5A45; margin:5px 8px; }
QMenu::indicator { width:8px; height:8px; margin-left:10px; border-radius:4px; background:transparent; }
QMenu::indicator:checked { background:#F2D27A; }
QMenu::indicator:checked:selected { background:#1A2A1E; }
QMenu::right-arrow { width:6px; height:6px; margin-right:10px; }
"""
SCROLL_QSS = """
QScrollArea { background:transparent; border:none; }
QScrollBar:horizontal { height:10px; background:rgba(0,0,0,70); border-radius:5px; margin:0px 46px 1px 46px; }
QScrollBar::handle:horizontal { background:rgba(255,248,235,200); border-radius:5px; min-width:44px; }
QScrollBar::handle:horizontal:hover { background:white; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background:transparent; }
"""

TOAST_QSS = ("background:#000000; color:#FFFFFF; border-radius:11px;"
             "padding:3px 12px; font-size:9pt; font-weight:600;")
SAVE_BTN_QSS = ("QPushButton{background:#7a4e2b; color:#fff4e0; border:1px solid #4a2c14; border-radius:7px;"
                "padding:7px 22px; font-size:11pt; font-weight:600;}"
                "QPushButton:hover{background:#8d5c33;} QPushButton:pressed{background:#633d20;}")
CANCEL_BTN_QSS = ("QPushButton{background:transparent; color:#5b4a3a; border:none; padding:7px 14px; font-size:11pt;}"
                  "QPushButton:hover{color:#2b1f14; text-decoration:underline;}")