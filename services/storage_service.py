"""JSON attendance persistence and CSV export — compatible with Ubuntu.tkinter.py."""
from __future__ import annotations

import csv
import getpass
import json
import os
import platform
import socket
import tempfile
from datetime import datetime, timedelta
from typing import Any

from config import settings


def load_camera_pref() -> int | None:
    try:
        with open(settings.CAMERA_PREF_FILE) as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return None


def save_camera_pref(index: int | None) -> None:
    if index is None:
        return
    try:
        with open(settings.CAMERA_PREF_FILE, "w") as handle:
            handle.write(str(index))
    except OSError:
        pass


def _atomic_write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".attendance_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def today_log_path(day: datetime | None = None) -> str:
    day = day or datetime.now()
    return os.path.join(settings.ATTENDANCE_DIR, f"{day.strftime('%Y-%m-%d')}.json")


def load_day_log(day: datetime | None = None) -> dict[str, Any]:
    path = today_log_path(day)
    if not os.path.exists(path):
        return {"date": (day or datetime.now()).strftime("%Y-%m-%d"), "sessions": []}
    try:
        with open(path) as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            data.setdefault("sessions", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"date": (day or datetime.now()).strftime("%Y-%m-%d"), "sessions": []}


def load_previous_breaks() -> tuple[list[list], timedelta]:
    """Return unique break entries and total break duration from today's log."""
    entries: list[list] = []
    total = timedelta()
    seen: set[tuple] = set()
    data = load_day_log()
    for session in data.get("sessions", []):
        for item in session.get("breaks", []):
            key = tuple(item[:3])
            if key in seen:
                continue
            seen.add(key)
            entries.append(list(item))
            try:
                hours, minutes, seconds = map(float, str(item[2]).split(":"))
                total += timedelta(hours=hours, minutes=minutes, seconds=seconds)
            except (ValueError, IndexError, TypeError):
                pass
    return entries, total


def resume_login_time() -> datetime | None:
    data = load_day_log()
    sessions = data.get("sessions") or []
    if not sessions:
        return None
    try:
        first = sessions[0]
        parsed = datetime.strptime(first["login_time"], "%I:%M:%S %p").time()
        return datetime.combine(datetime.now().date(), parsed)
    except (KeyError, ValueError, TypeError):
        return None


def last_logout_time() -> datetime | None:
    """Return the most recent logout timestamp from today's sessions."""
    data = load_day_log()
    sessions = data.get("sessions") or []
    if not sessions:
        return None
    last = sessions[-1]
    raw = last.get("logout_time")
    if not raw:
        return None
    try:
        parsed = datetime.strptime(str(raw), "%I:%M:%S %p").time()
        return datetime.combine(datetime.now().date(), parsed)
    except (ValueError, TypeError):
        return None


def append_break_entry(entry: list) -> None:
    """Persist a break onto the latest session for today (creates none if empty)."""
    data = load_day_log()
    sessions = data.get("sessions") or []
    if not sessions:
        return
    sessions[-1].setdefault("breaks", []).append(list(entry))
    try:
        hours, minutes, seconds = map(float, str(entry[2]).split(":"))
        extra = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        prev = sessions[-1].get("total_break_time", "0:00:00")
        try:
            ph, pm, ps = map(float, str(prev).split(":"))
            total = timedelta(hours=ph, minutes=pm, seconds=ps) + extra
        except (ValueError, TypeError):
            total = extra
        sessions[-1]["total_break_time"] = str(total)
    except (ValueError, IndexError, TypeError):
        pass
    path = today_log_path()
    data["sessions"] = sessions
    _atomic_write_json(path, data)


def load_shift_note(day: datetime | None = None) -> str:
    data = load_day_log(day)
    note = data.get("shift_note")
    if isinstance(note, str) and note.strip():
        return note.strip()
    sessions = data.get("sessions") or []
    for session in reversed(sessions):
        raw = session.get("shift_note")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def save_shift_note(text: str, day: datetime | None = None) -> None:
    data = load_day_log(day)
    data["shift_note"] = (text or "").strip()
    path = today_log_path(day)
    _atomic_write_json(path, data)


def save_session(
    login_time: datetime,
    total_break_time: timedelta,
    breaks: list[list],
    shift_note: str = "",
) -> None:
    if not login_time:
        return
    session_date = login_time.strftime("%Y-%m-%d")
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except OSError:
        ip_address = ""
    note = (shift_note or "").strip()
    new_session = {
        "login_time": login_time.strftime("%I:%M:%S %p"),
        "logout_time": datetime.now().strftime("%I:%M:%S %p"),
        "login_duration": str(datetime.now() - login_time),
        "work_duration": str(datetime.now() - login_time - total_break_time),
        "total_break_time": str(total_break_time),
        "breaks": breaks,
        "shift_note": note,
        "employee_name": settings.EMPLOYEE_NAME,
        "employee_role": settings.EMPLOYEE_ROLE,
        "username": settings.VALID_USERNAME,
        "ip_address": ip_address,
        "hostname": hostname,
        "user": getpass.getuser(),
        "platform": platform.system(),
    }
    path = os.path.join(settings.ATTENDANCE_DIR, f"{session_date}.json")
    existing = load_day_log(login_time)
    existing["date"] = session_date
    if note:
        existing["shift_note"] = note
    existing.setdefault("sessions", []).append(new_session)
    _atomic_write_json(path, existing)


def export_breaks_csv(path: str, breaks: list[list]) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Start Time", "End Time", "Duration", "Reason"])
        for row in breaks:
            writer.writerow(list(row[:4]))


def touch_crash_flag() -> None:
    try:
        with open(settings.CRASH_FLAG_FILE, "w") as handle:
            handle.write("crash marker")
    except OSError:
        pass


def clear_crash_flag() -> None:
    try:
        if os.path.exists(settings.CRASH_FLAG_FILE):
            os.remove(settings.CRASH_FLAG_FILE)
    except OSError:
        pass


def crash_flag_exists() -> bool:
    return os.path.exists(settings.CRASH_FLAG_FILE)
