"""Shift timing, breaks, and session state."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import QObject, Signal

from config import settings
from services import storage_service


class AttendanceService(QObject):
    stats_changed = Signal()
    breaks_changed = Signal()
    status_changed = Signal(str)  # "on_shift" | "on_break"

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.login_time: Optional[datetime] = None
        self.total_break_time = timedelta()
        self.break_log_entries: list[list] = []
        self.break_start_time: Optional[datetime] = None
        self.break_reason: Optional[str] = None
        self.manual_break_type: Optional[str] = None
        self.break_triggered = False
        self.last_break_end_time: Optional[float] = None
        self.shift_note = ""
        self._saved = False

    @property
    def on_break(self) -> bool:
        return self.break_start_time is not None

    def start_session(self) -> None:
        resumed = storage_service.resume_login_time()
        self.login_time = resumed or datetime.now()
        self.break_log_entries = []
        self.total_break_time = timedelta()
        self.break_start_time = None
        self.break_reason = None
        self.manual_break_type = None
        self.break_triggered = False
        self.shift_note = storage_service.load_shift_note()
        self._saved = False
        self.status_changed.emit("on_shift")
        self.stats_changed.emit()

    def load_previous_breaks(self) -> None:
        entries, total = storage_service.load_previous_breaks()
        self.break_log_entries = entries
        self.total_break_time = total
        self.breaks_changed.emit()
        self.stats_changed.emit()

    def apply_logout_gap_break(self) -> None:
        """
        If the employee logged out earlier today, count the time until this
        re-login as a Logout break so shift totals stay accurate.
        """
        logout_at = storage_service.last_logout_time()
        if logout_at is None:
            return
        now = datetime.now().replace(microsecond=0)
        logout_at = logout_at.replace(microsecond=0)
        if now <= logout_at:
            return
        duration = now - logout_at
        entry = [
            logout_at.strftime("%I:%M:%S %p"),
            now.strftime("%I:%M:%S %p"),
            str(duration),
            "Logout",
        ]
        key = tuple(entry[:3])
        if any(tuple(existing[:3]) == key for existing in self.break_log_entries):
            return
        self.break_log_entries.append(entry)
        self.total_break_time += duration
        storage_service.append_break_entry(entry)
        self.breaks_changed.emit()
        self.stats_changed.emit()

    def shift_duration(self) -> timedelta:
        if not self.login_time:
            return timedelta()
        return datetime.now() - self.login_time

    def work_duration(self) -> timedelta:
        active_break = timedelta()
        if self.break_start_time:
            active_break = datetime.now() - self.break_start_time
        return self.shift_duration() - self.total_break_time - active_break

    def breaks_duration(self) -> timedelta:
        active = timedelta()
        if self.break_start_time:
            active = datetime.now() - self.break_start_time
        return self.total_break_time + active

    def stats_snapshot(self) -> dict:
        login_str = self.login_time.strftime("%I:%M %p") if self.login_time else "--"
        return {
            "login_time": login_str,
            "on_shift": str(self.shift_duration()).split(".")[0],
            "breaks": str(self.breaks_duration()).split(".")[0],
            "worked": str(max(self.work_duration(), timedelta())).split(".")[0],
        }

    def begin_manual_break(self, reason: str) -> None:
        if self.break_start_time:
            raise RuntimeError("A break is already in progress.")
        self.break_reason = reason
        self.manual_break_type = reason
        self.break_start_time = datetime.now()
        self.break_triggered = True
        self.status_changed.emit("on_break")
        self.stats_changed.emit()

    def end_manual_break(self) -> None:
        if not self.break_start_time:
            return
        end = datetime.now()
        duration = end - self.break_start_time
        self.total_break_time += duration
        entry = [
            self.break_start_time.strftime("%I:%M:%S %p"),
            end.strftime("%I:%M:%S %p"),
            str(duration),
            self.manual_break_type or self.break_reason or "Break",
        ]
        self.break_log_entries.append(entry)
        self.break_start_time = None
        self.manual_break_type = None
        self.break_reason = None
        self.break_triggered = False
        import time

        self.last_break_end_time = time.time()
        self.status_changed.emit("on_shift")
        self.breaks_changed.emit()
        self.stats_changed.emit()

    def begin_auto_break(self, reason: str, start_time: datetime) -> None:
        self.break_reason = reason
        self.break_start_time = start_time
        self.break_triggered = True
        self.status_changed.emit("on_break")
        self.stats_changed.emit()

    def end_auto_break(self) -> None:
        if not self.break_start_time:
            return
        end = datetime.now()
        duration = end - self.break_start_time
        self.total_break_time += duration
        display_reason = "Idle Sitting" if self.break_reason == "Inactivity Only" else self.break_reason
        entry = [
            self.break_start_time.strftime("%I:%M:%S %p"),
            end.strftime("%I:%M:%S %p"),
            str(duration),
            display_reason or "Auto",
        ]
        self.break_log_entries.append(entry)
        self.break_start_time = None
        self.break_reason = None
        self.break_triggered = False
        import time

        self.last_break_end_time = time.time()
        self.status_changed.emit("on_shift")
        self.breaks_changed.emit()
        self.stats_changed.emit()

    def log_crash_break(self) -> None:
        if not self.login_time:
            return
        now = datetime.now()
        duration = timedelta(seconds=1)
        self.total_break_time += duration
        entry = [
            now.strftime("%I:%M:%S %p"),
            now.strftime("%I:%M:%S %p"),
            str(duration),
            "Crash",
        ]
        if not self.break_log_entries or self.break_log_entries[-1][3] != "Crash":
            self.break_log_entries.append(entry)
            self.breaks_changed.emit()
            self.stats_changed.emit()

    def break_type_counts(self) -> Counter:
        counts: Counter = Counter()
        for entry in self.break_log_entries:
            reason = entry[3] if len(entry) > 3 else "Other"
            counts[reason] += 1
        return counts

    def set_shift_note(self, text: str, *, persist: bool = False) -> None:
        self.shift_note = (text or "").strip()
        if persist:
            storage_service.save_shift_note(self.shift_note, self.login_time)

    def save_session(self) -> None:
        if self._saved or not self.login_time:
            return
        storage_service.save_session(
            self.login_time,
            self.total_break_time,
            self.break_log_entries,
            shift_note=self.shift_note,
        )
        self._saved = True
        storage_service.clear_crash_flag()
