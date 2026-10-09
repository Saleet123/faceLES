"""Automated tests for attendance/storage helpers (no camera required)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import settings
from services import storage_service
from services.attendance_service import AttendanceService


class AttendanceStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.logs = Path(self._tmpdir.name)
        self._orig = settings.ATTENDANCE_DIR
        settings.ATTENDANCE_DIR = str(self.logs)

    def tearDown(self) -> None:
        settings.ATTENDANCE_DIR = self._orig

    def test_save_and_load_session_breaks(self) -> None:
        login = datetime.now().replace(microsecond=0)
        breaks = [["01:00:00 PM", "01:05:00 PM", "0:05:00", "Tea"]]
        storage_service.save_session(login, timedelta(minutes=5), breaks)
        path = storage_service.today_log_path(login)
        self.assertTrue(os.path.exists(path))
        loaded, total = storage_service.load_previous_breaks()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0][3], "Tea")
        self.assertEqual(total, timedelta(minutes=5))

    def test_attendance_service_manual_break(self) -> None:
        svc = AttendanceService()
        svc.start_session()
        svc.begin_manual_break("Lunch")
        self.assertTrue(svc.on_break)
        svc.end_manual_break()
        self.assertFalse(svc.on_break)
        self.assertEqual(len(svc.break_log_entries), 1)
        self.assertEqual(svc.break_log_entries[0][3], "Lunch")

    def test_export_csv(self) -> None:
        path = self.logs / "out.csv"
        storage_service.export_breaks_csv(
            str(path),
            [["08:00:00 AM", "08:10:00 AM", "0:10:00", "Prayer"]],
        )
        text = path.read_text()
        self.assertIn("Start Time", text)
        self.assertIn("Prayer", text)

    def test_logout_gap_becomes_break(self) -> None:
        from unittest import mock

        login = datetime.now().replace(microsecond=0) - timedelta(hours=2)
        storage_service.save_session(login, timedelta(), [])
        logout_at = datetime.now().replace(microsecond=0) - timedelta(minutes=15)
        now = datetime.now().replace(microsecond=0)

        svc = AttendanceService()
        svc.start_session()
        svc.load_previous_breaks()
        with mock.patch.object(storage_service, "last_logout_time", return_value=logout_at):
            with mock.patch("services.attendance_service.datetime") as dt_mod:
                dt_mod.now.return_value = now
                dt_mod.side_effect = lambda *a, **kw: datetime(*a, **kw)
                svc.apply_logout_gap_break()

        self.assertTrue(any(row[3] == "Logout" for row in svc.break_log_entries))
        self.assertEqual(svc.total_break_time, timedelta(minutes=15))
        # Second apply must not duplicate
        before = len(svc.break_log_entries)
        with mock.patch.object(storage_service, "last_logout_time", return_value=logout_at):
            with mock.patch("services.attendance_service.datetime") as dt_mod:
                dt_mod.now.return_value = now
                dt_mod.side_effect = lambda *a, **kw: datetime(*a, **kw)
                svc.apply_logout_gap_break()
        self.assertEqual(len(svc.break_log_entries), before)

    def test_shift_note_saved_with_day_json(self) -> None:
        login = datetime.now().replace(microsecond=0)
        storage_service.save_session(
            login,
            timedelta(),
            [],
            shift_note="  Built reminder toast  ",
        )
        self.assertEqual(storage_service.load_shift_note(login), "Built reminder toast")
        data = storage_service.load_day_log(login)
        self.assertEqual(data["shift_note"], "Built reminder toast")
        self.assertEqual(data["sessions"][-1]["shift_note"], "Built reminder toast")

        storage_service.save_shift_note("Updated note", login)
        self.assertEqual(storage_service.load_shift_note(login), "Updated note")

        svc = AttendanceService()
        svc.start_session()
        self.assertEqual(svc.shift_note, "Updated note")


if __name__ == "__main__":
    unittest.main()
