<p align="center">
  <img src="assets/pin.png" alt="Tacky icon" width="128" height="128">
</p>

<h1 align="center">Tacky</h1>

<p align="center">
  <em>A tacky that slides down from the top of your screen. Pin text, screenshots, images and files, then grab them again when you need them.</em>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-yellow">
  <img alt="Built with" src="https://img.shields.io/badge/built%20with-PySide6-41cd52">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## Table of Contents

- [About](#about)
- [Features](#features)
- [Download](#download)
- [Platform and Requirements](#platform-and-requirements)
- [Installation](#installation)
  - [Option 1: Installer (recommended)](#option-1-installer-recommended)
  - [Option 2: Run from source](#option-2-run-from-source)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [Controls](#controls)
  - [Global shortcuts](#global-shortcuts)
  - [On the board](#on-the-board)
  - [Tray menu](#tray-menu)
- [Settings and Data](#settings-and-data)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## About

**Tacky** is a lightweight desktop tacky for Windows. It lives in your system tray and stays out of the way until you need it. Move your mouse to the top-centre of the screen (or press a shortcut) and a velvet or cork board slides down, covered in the notes, screenshots and files you pinned earlier.

Use it as a scratch space for the things you copy, snip and drag around all day. Anything you pin can be copied back with a click or dragged straight into another app. Unstarred items expire after a week, so the board doesn't turn into a junk drawer.

## Features

- **Pin almost anything.** Selected text, screenshots, images and files.
- **One-key text pinning.** Select text in any app and press `Win + C`.
- **Automatic screenshot pinning.** Snips taken with `Win + Shift + S` or `PrintScreen` land on the board.
- **Drag and drop in and out.** Drop files or text onto the board, or drag a card into another app.
- **Click to copy.** A single click on a card puts its content on your clipboard.
- **Editable sticky notes.** Text pins are shown as paper notes you can edit.
- **Self-cleaning.** Items fade after 4 days and expire after 7, unless you star them with **Keep**.
- **Five board styles.** Green, blue, burgundy and charcoal velvet, or cork.
- **Adjustable reveal speed.** Instant, Normal or Slow.
- **Starts with Windows**, if you want it to.
- **Single instance, tray-only.** No taskbar clutter.

## Download

> **[Download the Tacky installer](https://github.com/C0ding-Craze/tacky/releases/latest)**

Get the latest `Tacky-Setup.exe` from the [Releases page](https://github.com/C0ding-Craze/tacky/releases).

## Platform and Requirements

| | |
|---|---|
| **Operating system** | Windows 10 or Windows 11 (64-bit) |
| **Python** (source only) | 3.10 or newer |
| **Display** | Any resolution. HiDPI scaling is handled. |
| **Disk space** | Small. Pinned images are stored locally. |

Tacky is built for Windows. The global hotkeys, the screenshot hooks and the *Start with Windows* option rely on Windows APIs, so on other systems they are unavailable.

## Installation

### Option 1: Installer (recommended)

1. [Download the installer](#download).
2. Run `Tacky-Setup.exe` and follow the prompts.
3. Tacky starts in the system tray. Look for the red pin icon near the clock.

No Python installation is needed for this option.

### Option 2: Run from source

```bash
# 1. Get the code
git clone https://github.com/C0ding-Craze/tacky.git
cd tacky

# 2. (Optional) create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install the dependency
pip install PySide6

# 4. Launch
python tacky.py
```

To run without a console window, use `pythonw tacky.py`.

## Dependencies

| Package | Purpose |
|---|---|
| [**PySide6**](https://pypi.org/project/PySide6/) (Qt 6) | User interface, tray icon, drag and drop, clipboard |

Everything else is from the Python standard library (`ctypes`, `winreg`, `json`, `logging`, `pathlib` and so on). Windows APIs are called through `ctypes`, so no extra packages are needed for the hotkeys.

## Usage

**Showing the board**

- Rest your mouse at the **top-centre edge** of the screen for a moment, or
- press `Win + Alt + S`, or
- left-click the tray icon.

The board hides itself shortly after your mouse leaves it. Press `Esc` or use the shortcut again to close it right away.

**Adding things**

| To pin... | Do this |
|---|---|
| **Text** | Select it in any app, then press `Win + C`. |
| **A screenshot** | Take a snip with `Win + Shift + S` or `PrintScreen`. It is pinned automatically. |
| **Files or images** | Drag them onto the board. |
| **Text from a window** | Drag selected text onto the board. |

Your previous clipboard contents are restored after `Win + C`, so pinning doesn't disturb whatever you had copied.

**Using what you pinned**

- **Click** a card to copy it.
- **Drag** a card into any app to drop the text, image or file there.
- **Double-click** to open a file or edit a note.
- **Right-click** for more actions such as Keep, Edit and Unpin.

**Keeping things**

Pins older than 4 days start to fade, and they are removed after 7 days. Right-click a card and choose **Keep** to protect it.

## Controls

### Global shortcuts

| Shortcut | Action |
|---|---|
| `Win + Alt + S` | Show or hide the board |
| `Win + C` | Pin the currently selected text, file or image |
| `Win + Alt + C` | Fallback for pinning if `Win + C` can't be captured |
| `Win + Shift + S` | Windows snip. Tacky pins the result. |
| `PrintScreen` | Screenshot. Tacky pins the result. |

If another app already owns one of these shortcuts, Tacky shows a tray notification. Automatic screenshot pinning can be switched off from the tray menu.

### On the board

| Input | Action |
|---|---|
| Mouse at top-centre of screen | Reveal the board |
| `Esc` | Hide the board |
| `←` / `→` | Scroll the board |
| Mouse wheel | Scroll sideways |
| Edge arrows (left and right) | Step or hold to scroll |
| Single click on a card | Copy its content |
| Double-click on a card | Open the file, or edit the note |
| Drag a card out | Drop its content into another app |
| Drop files or text in | Pin them |
| Right-click a card | Keep / Unkeep, Copy, Edit or Open, Show in Explorer, Unpin |
| Right-click the board frame | Clear whole board |

**Note editor**

| Input | Action |
|---|---|
| `Ctrl + Enter` | Save |
| Cancel button | Discard changes |

### Tray menu

Right-click the tray icon:

| Item | What it does |
|---|---|
| Show / hide board | Same as `Win + Alt + S` |
| Reveal speed | Instant, Normal or Slow |
| Board style | Green, Blue, Burgundy or Charcoal velvet, or Cork |
| Pin snips | Turn automatic screenshot pinning on or off |
| Start with Windows | Launch Tacky at login |
| Clear board (keeps starred) | Remove every card except those you kept |
| Quit | Save and exit |

Left-clicking the tray icon toggles the board.

## Settings and Data

Tacky stores everything locally and sends nothing over the network.

| Item | Location |
|---|---|
| Board data and settings | `%APPDATA%\Tacky\board.json` |
| Pinned images | `%APPDATA%\Tacky\items\` |
| Log file | `%APPDATA%\Tacky\tacky.log` |

Set the `TACKY_HOME` environment variable to use a different data folder.

If `board.json` is ever corrupted, Tacky keeps a copy as `board.bad` and starts with an empty board. Files you pin by dragging them in are only referenced, not copied, so removing a card never deletes your original file.

## Project Structure

```
Tacky/
├── tacky.py             # Entry point
├── assets/
│   ├── pin.ico          # Windows icon
│   └── pin.png          # App icon
└── app/
    ├── main.py          # App start-up, tray, hotkeys, single-instance lock
    ├── board/           # The sliding board window, flip animation, textures, artwork
    ├── cards/           # Card widgets, card faces, card actions (copy, open, drag, remove)
    ├── core/            # Config, storage, logging, auto-start, memory trimming
    ├── system/          # Windows hotkeys, clipboard and screenshot capture, tray menu
    └── ui/              # Theme, icon, painting helpers, note editor, custom widgets
```

## Troubleshooting

**The board doesn't appear when I move the mouse to the top.**
Rest the pointer at the top edge, near the middle of the screen, for a moment. You can also use `Win + Alt + S` or click the tray icon.

**`Win + C` doesn't pin anything.**
Make sure text is selected first. If you see *Nothing selected*, the app didn't respond to the copy command. If Windows or another app already uses `Win + C`, Tacky switches to `Win + Alt + C` and tells you.

**Tacky says a shortcut is already in use.**
Another program has registered the same shortcut. Close it, or use the tray menu instead.

**Something isn't working.**
Check `%APPDATA%\Tacky\tacky.log`.

**Tacky doesn't start a second time.**
Only one copy can run at once. Look for the pin in the tray, and quit it from there if needed.

## Contributing

Issues and pull requests are welcome. For larger changes, please open an issue first so we can talk it through.

1. Fork the repository
2. Create a branch: `git checkout -b my-feature`
3. Commit your changes
4. Push the branch and open a pull request

## License

This project is released under the **MIT License**. See the [`LICENSE`](LICENSE) file for the full text.

---

<p align="center">Made with a red pin and too many sticky notes.</p>
