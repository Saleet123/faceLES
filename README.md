# FaceLES — Face Login & Attendance

Desktop attendance monitor: password or biometric login, shift tracking, idle/absence breaks, and CSV export.

**Primary entry point:** `main.py` (PySide6)

The previous Tkinter application is preserved as `Ubuntu.tkinter.py`. See `MIGRATION.md` for the UI migration notes.

---

## Give this to employees

Do **not** send `FaceLES.exe` by itself. OpenCV and Qt live next to it. A lone `.exe` will fail on another PC.

| OS | What to give them | How they open it |
|---|---|---|
| **Windows** | `FaceLES-Setup.exe` (preferred) or a zip of the whole `dist\FaceLES` folder | Double-click Setup, then open FaceLES from the Start menu / Desktop. If you zipped the folder: unzip and double-click `FaceLES.exe` **inside that folder**. |
| **Ubuntu** | `faceles_1.0.0_amd64.deb` | Double-click the `.deb` (or `sudo apt install ./faceles_1.0.0_amd64.deb`), then open **FaceLES** from the applications menu. |

Build those installers on the matching OS (Windows `.exe` on a Windows PC, Ubuntu `.deb` on Ubuntu).

Default login until you change `config/settings.py`:

- Username: `saleet`
- Password: `123`

Employee data (logs, enrolled face) is stored per user:

- Windows: `%APPDATA%\FaceLES\`
- Ubuntu: `~/.local/share/FaceLES/`

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
├── scripts/                # build_ubuntu.sh, build_windows.bat
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

### Ubuntu (`.deb`)

On Ubuntu, from this repo:

```bash
./scripts/build_ubuntu.sh
```

That builds the app and then:

```bash
./scripts/build_ubuntu_deb.sh
```

Output:

- `dist/faceles_1.0.0_amd64.deb` — copy this to other Ubuntu PCs

Install:

```bash
sudo apt install ./faceles_1.0.0_amd64.deb
```

Then search **FaceLES** in the applications menu.

### Windows (`.exe` installer)

Must be run **on a Windows PC** (this cannot be built from Ubuntu).

1. Install [Python 3.12+](https://www.python.org/downloads/) (tick **Add python.exe to PATH**).
2. Optional, for a Setup installer: [Inno Setup 6](https://jrsoftware.org/isinfo.php).
3. Open the FaceLES folder in File Explorer, then double-click:

   `scripts\build_windows.bat`

That creates:

- `dist\FaceLES\FaceLES.exe` — portable app; zip the **whole** `FaceLES` folder
- `dist\FaceLES-Setup.exe` — only if Inno Setup is installed; **this is what you send to employees**

Employees double-click `FaceLES-Setup.exe`, click through the installer, then open FaceLES from the Start menu or Desktop shortcut.

You can also build on GitHub: **Actions → Build Windows → Run workflow**, then download the `FaceLES-Setup-windows` artifact.

---

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```
