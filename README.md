# FaceLES — Face Login & Attendance

Desktop attendance monitor for Ubuntu/Linux: password or biometric login, shift tracking, idle/absence breaks, and CSV export.

**Primary entry point:** `Ubuntu.py`

---

## Features

- Face recognition (OpenCV LBPH) + password login
- Biometric enrollment modal and biometric login
- Live shift stats (login time, breaks, work duration)
- Manual breaks (Meeting, Lunch, Prayer, Tea, Call)
- Auto breaks after **5 minutes** of inactivity (and absence when a camera + face model are available)
- Daily summary and CSV export (in-app modals)
- Attendance JSON logs under `attendance_logs/`

---

## Requirements

- Python 3.10+
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
python Ubuntu.py
```

Default demo credentials (change in `Ubuntu.py`):

- Username: `saleet`
- Password: `123`

### Register a face

On the login screen, click **Register face**, complete the enrollment captures, then use **Biometric login**.

---

## How auto-breaks work

| Setup | Behavior |
|-------|----------|
| **No camera** | Only mouse/keyboard idle (5 min) → countdown → auto break |
| **Camera + enrolled face** | Idle and/or face absence (5 min) can trigger auto break |

Moving the mouse or typing cancels a pending idle countdown.

---

## Project layout

```
FaceLES/
├── Ubuntu.py                          # Main app (use this)
├── requirements.txt
├── haarcascade_frontalface_default.xml
├── profile_pic.jpg
├── lbph_model.yml                     # Created after face registration (gitignored)
├── label_map.txt                      # Created after registration (gitignored)
├── attendance_logs/                   # Runtime logs (gitignored)
├── main.py                            # Older Tkinter variant
├── kivy_face_monitor.py               # Older Kivy variant
└── README.md
```

---

## Build (optional)

```bash
pyinstaller --noconsole --onefile Ubuntu.py \
  --add-data "haarcascade_frontalface_default.xml:." \
  --icon=face-unlock.icns
```

---

## Author

**Saleet Ul Hassan**
