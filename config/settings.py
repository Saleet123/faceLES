"""Application settings and paths — preserved from the Tkinter FaceLES app."""
from __future__ import annotations

import os
import sys


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _bundle_dir() -> str:
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_dir() -> str:
    """Writable files. Frozen builds keep logs outside the install folder."""
    if not _is_frozen():
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(root, "FaceLES")
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "FaceLES")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
        path = os.path.join(root, "FaceLES")
    os.makedirs(os.path.join(path, "attendance_logs"), exist_ok=True)
    return path


BUNDLE_DIR = _bundle_dir()
DATA_DIR = _data_dir()
APP_DIR = DATA_DIR

# Login matches the supplied compact reference. The dashboard uses a larger
# locked canvas so its cards, break log, and camera are not compressed.
LOGIN_WINDOW_W = 964
LOGIN_WINDOW_H = 474
DASHBOARD_WINDOW_W = 1100
DASHBOARD_WINDOW_H = 720

# Backward-compatible aliases used by the entry point.
WINDOW_W = LOGIN_WINDOW_W
WINDOW_H = LOGIN_WINDOW_H
WINDOW_MIN_W = LOGIN_WINDOW_W
WINDOW_MIN_H = LOGIN_WINDOW_H

PREVIEW_W = 400
PREVIEW_H = 300

CRASH_FLAG_FILE = os.path.join(DATA_DIR, "crash_flag.tmp")
MODEL_FILE = os.path.join(DATA_DIR, "lbph_model.yml")
LABEL_MAP_FILE = os.path.join(DATA_DIR, "label_map.txt")
CASCADE_FILE = os.path.join(BUNDLE_DIR, "haarcascade_frontalface_default.xml")
CAMERA_PREF_FILE = os.path.join(DATA_DIR, "camera_pref.txt")
_PROFILE_DATA = os.path.join(DATA_DIR, "profile_pic.jpg")
_PROFILE_BUNDLE = os.path.join(BUNDLE_DIR, "profile_pic.jpg")
PROFILE_PIC = _PROFILE_DATA if os.path.isfile(_PROFILE_DATA) else _PROFILE_BUNDLE
ATTENDANCE_DIR = os.path.join(DATA_DIR, "attendance_logs")
EXPORT_DIR = os.path.expanduser("~")

# Development credentials (isolated from UI; same defaults as Ubuntu.tkinter.py)
VALID_USERNAME = "saleet"
VALID_PASSWORD = "123"
EMPLOYEE_NAME = "Saleet Ul Hassan"
EMPLOYEE_ROLE = "Employee · Face-verified attendance"

# Scheduled desk shift. Login beyond shift + grace is not counted on the dashboard.
SHIFT_HOURS = 8
SHIFT_GRACE_MINUTES = 30

INACTIVITY_THRESHOLD = 3 * 60
BREAK_COOLDOWN_SECONDS = 60
COUNTDOWN_SECONDS = 10
REMINDER_SECONDS = 60

ENROLL_TARGET = 9
ENROLL_CAPTURE_INTERVAL = 0.55
LOGIN_MATCH_FRAMES = 6
BIOMETRIC_LOGIN_DEADLINE = 15
LBPH_LOGIN_THRESHOLD = 60
# Presence uses the same 200×200 prep as enrollment. Slightly looser than
# login so normal desk lighting still counts as "you are in view".
LBPH_PRESENCE_THRESHOLD = 70

MANUAL_BREAK_OPTIONS = ["Meeting", "Lunch", "Prayer", "Tea", "Call"]

PRESENCE_CHECK_INTERVAL = 1.0


def resource_path(relative_path: str) -> str:
    return os.path.join(BUNDLE_DIR, relative_path)
