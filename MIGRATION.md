# FaceLES Tkinter → PySide6 Migration Summary

## What changed

- UI toolkit moved from **Tkinter** to **PySide6**.
- Application entry point is now `main.py` (launch via `python main.py` or `./run.sh`).
- Tkinter source preserved as `Ubuntu.tkinter.py` (and the previous `Ubuntu.py` copy).
- Vendored Tk/Xft font preload logic is no longer used by the Qt launch path.

## Project structure

```text
FaceLES/
├── main.py
├── requirements.txt
├── run.sh
├── config/           # settings + theme/QSS tokens
├── services/         # camera, face, attendance, activity, storage
├── ui/               # login, dashboard, dialogs, widgets
├── assets/icons/     # SVG icons
├── assets/styles/    # QSS reference
├── tests/
├── Ubuntu.tkinter.py # full Tkinter backup
└── (existing model / attendance / cascade files unchanged)
```

## Preserved functionality

| Area | Status |
|---|---|
| Username/password login (`saleet` / `123`) | Preserved |
| Biometric login (LBPH, 6-frame match, threshold ~60, 15s deadline) | Preserved |
| Face enrollment (9 samples, ~0.55s interval, 200×200) | Preserved |
| Haar cascade + LBPH model files | Compatible / reused |
| Shift / break / work timers | Preserved |
| Manual breaks (Meeting, Lunch, Prayer, Tea, Call) | Preserved |
| Auto inactivity (5 min) + 10s countdown + 60s cooldown | Preserved |
| Presence checks (~1/s) | Preserved |
| JSON attendance logs under `attendance_logs/` | Compatible |
| CSV export columns | Preserved |
| Camera preference file | Preserved |
| Crash flag handling | Preserved |
| Window size 1100×720 (min 960×640) | Enforced across pages |

## Visual redesign

- Login: blue gradient sidebar, credential form, live camera card.
- Dashboard: gradient header, profile, four stat cards, scrollable Break Log, camera panel, fixed bottom action bar.
- Modals for biometric/enrollment, breaks, idle countdown, summary, and CSV export.

## Intentional non-changes

- LBPH algorithm and thresholds were not rewritten.
- Attendance JSON schema was not migrated or rewritten.
- Auto-break reason labels match the Tkinter app (`Inactivity Only` displays as `Idle Sitting` when logged).

## Known limitations

- Prototype-style local credentials and LBPH are not production-grade biometric security.
- Full biometric/camera hardware validation depends on a working webcam and display session.
- Global idle detection uses Qt event filtering within the app (same practical scope as the prior Tk bindings for in-app mouse/keyboard).

## Launch

```bash
cd /home/hytgenx/FaceLES
source .venv/bin/activate   # optional if using project venv
pip install -r requirements.txt
python main.py
# or
./run.sh
```
