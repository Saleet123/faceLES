# FaceLES — Face Login & Attendance

Desktop attendance monitor: password or biometric login, shift tracking, idle/absence breaks, and CSV export.

**Primary entry point:** `main.py` (PySide6)

The previous Tkinter application is preserved as `Ubuntu.tkinter.py`. See `MIGRATION.md` for the UI migration notes.

---

## Give this to employees

Do **not** send `FaceLES.exe` by itself. OpenCV and Qt live next to it. A lone `.exe` will fail on another PC.

| OS | What to give them | How they open it |
|---|---|---|
| **Ubuntu** | `faceles_1.0.0_amd64.deb` | Double-click the `.deb` (or `sudo apt install ./faceles_1.0.0_amd64.deb`), then open **FaceLES** from the applications menu. |
| **Windows** | `FaceLES-Setup.exe` (preferred) or a zip of the whole `dist\FaceLES` folder | Double-click Setup, then open FaceLES from the Start menu / Desktop. If you zipped the folder: unzip and double-click `FaceLES.exe` **inside that folder**. |
| **macOS** | `FaceLES.app` or `FaceLES-macOS.zip` | Unzip if needed, drag the app to Applications, then open FaceLES. First time: right-click → Open. |

Build each installer **on that OS** (Ubuntu `.deb` on Ubuntu, Windows `.exe` on Windows, Mac `.app` on a Mac). Do not send a lone `.exe` / binary without its folder.

Default login until you change `config/settings.py`:

- Username: `saleet`
- Password: `123`

Employee data (logs, enrolled face) is stored per user:

- Windows: `%APPDATA%\FaceLES\`
- Ubuntu: `~/.local/share/FaceLES/`
- macOS: `~/Library/Application Support/FaceLES/`

---

## Features

- Face recognition (OpenCV LBPH) + password login
- Biometric enrollment and biometric login modals
- Live shift stats (login time, breaks, work duration)
- Manual breaks (Meeting, Lunch, Prayer, Tea, Call)
- Auto breaks after **3 minutes** of inactivity (and absence when a camera + face model are available)
- Scrollable Break Log (window height stays fixed)
- Daily summary and CSV export
- Attendance JSON logs under `attendance_logs/`
- Next.js web dashboard (`web/`) that reads those day files

---

## Requirements

- Python 3.10+
- PySide6, OpenCV (`opencv-contrib-python` &lt; 5), NumPy, Pillow
- Webcam optional (without camera: password login + inactivity / manual breaks only)

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
./run.sh
# or
python main.py
```

Default demo credentials (see `config/settings.py`):

- Username: `saleet`
- Password: `123`

### Register a face

On the login screen, click **Register face**, complete the enrollment captures, then use **Biometric login**.

---

## How auto-breaks work

| Setup | Behavior |
|-------|----------|
| **No camera** | Only mouse/keyboard idle (3 min) → countdown → auto break |
| **Camera + enrolled face** | Idle and/or face absence (3 min) can trigger auto break |

With a live camera and enrolled face, only a **recognized face** cancels a pending auto-break or ends an auto-break. Mouse movement does not. If the camera is unavailable, mouse/keyboard can cancel the countdown.

---

## Project layout

```
FaceLES/
├── main.py                 # PySide6 entry point
├── run.sh
├── requirements.txt
├── config/                 # settings + theme
├── services/               # camera, face, attendance, activity, storage
├── ui/                     # pages, dialogs, widgets
├── assets/icons/
├── Ubuntu.tkinter.py       # Tkinter backup
├── haarcascade_frontalface_default.xml
├── profile_pic.jpg
├── lbph_model.yml
├── label_map.txt
├── attendance_logs/
├── web/                    # Next.js day-wise attendance dashboard
├── packaging/              # PyInstaller spec, Ubuntu .deb, Windows Inno Setup
├── scripts/                # build_ubuntu.sh, build_windows.bat, build_macos.sh
├── tests/
├── MIGRATION.md
└── README.md
```

---

## Web dashboard

Reads `attendance_logs/*.json` and shows shifts by day, employee name, times, breaks, and notes.

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000

---

## Package for employees

Build on the same kind of machine you will ship to. You cannot make a Windows `.exe` on Ubuntu, or a Mac `.app` on Windows.

---

### Ubuntu — create a `.deb`

**On an Ubuntu PC**, from the FaceLES repo:

1. Install Python 3.10+ if needed (`python3`, `python3-venv`, `python3-pip`).
2. One-time setup:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Build the app **and** the Debian package:

   ```bash
   chmod +x scripts/build_ubuntu.sh scripts/build_ubuntu_deb.sh
   ./scripts/build_ubuntu.sh
   ```

   `build_ubuntu.sh` already calls `build_ubuntu_deb.sh` at the end. To rebuild only the `.deb` after the app folder exists:

   ```bash
   ./scripts/build_ubuntu_deb.sh
   ```

4. Output file to give employees:

   ```
   dist/faceles_1.0.0_amd64.deb
   ```

5. On each Ubuntu PC, install it:

   ```bash
   sudo apt install ./faceles_1.0.0_amd64.deb
   ```

   Or double-click the `.deb` and click **Install**. Then open **FaceLES** from the applications menu.

Login: `saleet` / `123`.

---

### Windows — create an `.exe` installer

**Must be run on a Windows PC.**

1. Install [Python 3.12+](https://www.python.org/downloads/). Tick **Add python.exe to PATH**.
2. Optional, for a Setup installer employees can double-click: [Inno Setup 6](https://jrsoftware.org/isinfo.php).
3. Clone or copy this repo, open the FaceLES folder, then double-click:

   ```
   scripts\build_windows.bat
   ```

   Or in PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
   ```

4. Output:

   | File | Give to employees? |
   |---|---|
   | `dist\FaceLES\FaceLES.exe` plus the rest of `dist\FaceLES\` | Only if you zip the **whole folder** |
   | `dist\FaceLES-Setup.exe` | **Yes** — this is the installer (created when Inno Setup is installed) |

5. Employees double-click `FaceLES-Setup.exe`, install, then open FaceLES from the Start menu or Desktop.

   If you have no Setup.exe: zip `dist\FaceLES` and tell them to unzip and double-click `FaceLES.exe` **inside that folder**. A single `.exe` will not run.

You can also build on GitHub: **Actions → Build Windows → Run workflow**, then download the `FaceLES-Setup-windows` artifact.

Login: `saleet` / `123`.

---

### macOS — create a `.app`

**Must be run on a Mac.**

1. Install Python 3.12+ (python.org or Homebrew: `brew install python`).
2. From the FaceLES repo in Terminal:

   ```bash
   chmod +x scripts/build_macos.sh
   ./scripts/build_macos.sh
   ```

3. Output to give employees:

   ```
   dist/FaceLES.app
   dist/FaceLES-macOS.zip
   ```

4. Employees unzip if needed, drag **FaceLES.app** into **Applications**, then open it.

   First launch of an unsigned app: **right-click → Open** (Gatekeeper). Camera access is requested the first time.

   Shipping without Gatekeeper warnings requires an Apple Developer account (`codesign` + notarization).

Login: `saleet` / `123`.

---

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```
