"""Idle / absence monitoring — same thresholds as Ubuntu.tkinter.py."""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from config import settings


class ActivityMonitor(QObject):
    countdown_requested = Signal(str)  # break reason
    presence_updated = Signal(bool)
    watch_updated = Signal(dict)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.last_user_input_time = time.time()
        self.last_person_seen_time = time.time()
        self.face_monitor_alive = False
        self.is_user_visible = True
        self.countdown_active = False
        self.countdown_deadline: float | None = None
        self.break_active = False
        self.last_break_end_time: float | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)

    def note_user_activity(self) -> None:
        self.last_user_input_time = time.time()

    def note_person_seen(self) -> None:
        self.last_person_seen_time = time.time()
        self.is_user_visible = True
        self.presence_updated.emit(True)

    def note_person_absent(self) -> None:
        self.is_user_visible = False
        self.presence_updated.emit(False)

    def start(self) -> None:
        now = time.time()
        self.last_user_input_time = now
        self.last_person_seen_time = now
        self.countdown_active = False
        self.countdown_deadline = None
        self.break_active = False
        self._timer.start()
        self.watch_updated.emit(self.watch_snapshot())

    def stop(self) -> None:
        self._timer.stop()

    def cancel_countdown(self) -> None:
        self.countdown_active = False
        self.countdown_deadline = None
        now = time.time()
        self.last_user_input_time = now
        self.last_person_seen_time = now

    def mark_break_ended(self) -> None:
        self.break_active = False
        self.countdown_active = False
        self.countdown_deadline = None
        now = time.time()
        self.last_break_end_time = now
        self.last_user_input_time = now
        self.last_person_seen_time = now

    def mark_break_started(self) -> None:
        self.break_active = True
        self.countdown_active = False
        self.countdown_deadline = None

    def watch_snapshot(self) -> dict:
        now = time.time()
        visible = self.is_user_visible
        away = 0.0 if visible else max(0.0, now - self.last_person_seen_time)
        remaining_idle = max(0.0, settings.INACTIVITY_THRESHOLD - (now - self.last_user_input_time))
        remaining_away = max(0.0, settings.INACTIVITY_THRESHOLD - (now - self.last_person_seen_time))
        if self.break_active:
            remaining = 0.0
            phase = "break"
        elif self.countdown_active and self.countdown_deadline is not None:
            remaining = max(0.0, self.countdown_deadline - now)
            phase = "countdown"
        else:
            # Camera card is about being on seat: count down from last recognized face.
            remaining = remaining_away if not visible else remaining_idle
            phase = "watch"
        return {
            "visible": visible,
            "away_seconds": away,
            "remaining_break": remaining,
            "remaining_away": remaining_away,
            "countdown": phase == "countdown",
            "on_break": phase == "break",
        }

    def _tick(self) -> None:
        self.watch_updated.emit(self.watch_snapshot())
        if self.break_active or self.countdown_active:
            return
        now = time.time()
        no_user_input = now - self.last_user_input_time > settings.INACTIVITY_THRESHOLD
        user_absent = self.face_monitor_alive and (
            now - self.last_person_seen_time > settings.INACTIVITY_THRESHOLD
        )
        cooldown_elapsed = True
        if self.last_break_end_time:
            cooldown_elapsed = now - self.last_break_end_time > settings.BREAK_COOLDOWN_SECONDS
        if not cooldown_elapsed:
            return
        # Off-camera for 3 minutes starts a break even if the mouse is hovering.
        if user_absent:
            reason = "Inactivity + Absence" if no_user_input else "Absence Only"
            self.countdown_active = True
            self.countdown_deadline = now + settings.COUNTDOWN_SECONDS
            self.countdown_requested.emit(reason)
            return
        if no_user_input:
            self.countdown_active = True
            self.countdown_deadline = now + settings.COUNTDOWN_SECONDS
            self.countdown_requested.emit("Inactivity Only")
