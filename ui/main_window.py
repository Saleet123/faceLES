"""Main FaceLES window — stacks login and dashboard at a fixed size."""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import cv2
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from config import settings
from config.theme import QSS
from services.activity_monitor import ActivityMonitor
from services.attendance_service import AttendanceService
from services.camera_service import CameraService
from services.face_recognition_service import FaceRecognitionService
from services import storage_service
from ui.dashboard_page import DashboardPage
from ui.dialogs.biometric_dialog import BiometricSession
from ui.dialogs.break_dialog import BreakSelectDialog
from ui.dialogs.export_dialog import ExportDialog
from ui.dialogs.inactivity_dialog import InactivityDialog
from ui.dialogs.summary_dialog import SummaryDialog
from ui.login_page import LoginPage
from ui.widgets.icons import app_icon
from ui.widgets.modal import AlertModal


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FaceLES")
        self.setWindowIcon(app_icon())
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setFixedSize(settings.LOGIN_WINDOW_W, settings.LOGIN_WINDOW_H)
        self.setStyleSheet(QSS)

        self.camera = CameraService(self)
        self.face = FaceRecognitionService()
        self.attendance = AttendanceService(self)
        self.activity = ActivityMonitor(self)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage()
        self.dashboard = DashboardPage()
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard)

        self._bio_session: BiometricSession | None = None
        self._idle: InactivityDialog | None = None
        self._break_is_auto = False
        self._presence_busy = False
        self._last_presence_check = 0.0
        self._logged_in = False

        self._wire()
        storage_service.touch_crash_flag()
        QTimer.singleShot(50, self._boot_camera)

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(1000)
        self._stats_timer.timeout.connect(self._tick_stats)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.setMouseTracking(True)

    def _set_locked_window_size(self, width: int, height: int) -> None:
        """Switch page size, keep it locked, and center it on the active screen."""
        self.setFixedSize(width, height)
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _wire(self) -> None:
        self.login_page.sign_in.connect(self._password_login)
        self.login_page.biometric.connect(self._open_biometric)
        self.login_page.register_face.connect(self._open_enroll)
        self.login_page.camera_selected.connect(self.camera.select_by_label)

        self.dashboard.start_break.connect(self._start_manual_break)
        self.dashboard.end_break.connect(self._end_manual_break)
        self.dashboard.export_csv.connect(self._export_csv)
        self.dashboard.summary.connect(self._summary)
        self.dashboard.logout.connect(self._logout)
        self.dashboard.camera_selected.connect(self.camera.select_by_label)
        self.dashboard.stay_present.connect(self._on_stay_present)
        self.dashboard.note_changed.connect(self._on_note_changed)

        self.camera.cameras_updated.connect(self._on_cameras)
        self.camera.frame_ready.connect(self._on_frame)
        self.camera.status_changed.connect(self._on_cam_status)
        self.camera.camera_failed.connect(self._on_cam_fail)

        self.attendance.stats_changed.connect(self._refresh_stats)
        self.attendance.breaks_changed.connect(self._refresh_breaks)

        self.activity.countdown_requested.connect(self._idle_countdown)
        self.activity.watch_updated.connect(self._on_watch)
        self.camera.add_frame_hook(self._presence_hook)

    def _boot_camera(self) -> None:
        self.camera.refresh_cameras()

    def _on_cameras(self, cameras: list) -> None:
        self.login_page.camera.set_cameras(cameras, self.camera.camera_index)
        self.dashboard.camera.set_cameras(cameras, self.camera.camera_index)

    def _on_frame(self, frame) -> None:
        page = self.stack.currentWidget()
        if page is self.login_page:
            self.login_page.camera.show_frame(frame)
        elif page is self.dashboard:
            self.dashboard.camera.show_frame(frame)
        if self._bio_session is not None:
            self._bio_session.on_frame(frame)

    def _on_cam_status(self, text: str) -> None:
        self.login_page.camera.set_status(True, text)
        self.dashboard.camera.set_status(True, text)

    def _on_cam_fail(self, text: str) -> None:
        self.login_page.camera.set_status(False, text)
        self.dashboard.camera.set_status(False, text)

    def _password_login(self, username: str, password: str) -> None:
        if storage_service.crash_flag_exists():
            self.attendance.log_crash_break()
        if username.lower() != settings.VALID_USERNAME.lower() or password != settings.VALID_PASSWORD:
            AlertModal.error(
                self,
                "Login failed",
                f"Invalid username or password.\nExpected username: {settings.VALID_USERNAME}",
            )
            return
        self._finish_login()

    def _finish_login(self) -> None:
        self.attendance.start_session()
        self.attendance.load_previous_breaks()
        # Time spent logged out since the last session counts as a break.
        self.attendance.apply_logout_gap_break()
        self._logged_in = True
        self.activity.face_monitor_alive = self.face.model_exists()
        self.activity.start()
        self.stack.setCurrentWidget(self.dashboard)
        self.setWindowTitle("FaceLES · Dashboard")
        self.dashboard.set_break_active(False)
        self.dashboard.set_shift_note(self.attendance.shift_note)
        self._refresh_stats()
        self._refresh_breaks()
        self._stats_timer.start()
        self._set_locked_window_size(
            settings.DASHBOARD_WINDOW_W,
            settings.DASHBOARD_WINDOW_H,
        )

    def _open_biometric(self) -> None:
        if not self.face.model_exists():
            AlertModal.info(
                self,
                "No face enrolled",
                "Register your face first, then use Biometric login.",
            )
            return
        self._open_face_dialog("login")

    def _open_enroll(self) -> None:
        self._open_face_dialog("enroll")

    def _open_face_dialog(self, mode: str) -> None:
        if self._bio_session is not None:
            return
        # Use the existing right-side live camera — no second preview/modal feed.
        session = BiometricSession(mode, self.face, self.login_page.camera, self)
        self._bio_session = session
        self.login_page.set_busy(True)
        self.login_page.bio_btn.setEnabled(False)
        self.login_page.register_btn.setEnabled(False)

        def done_ok():
            self._bio_session = None
            self.login_page.set_busy(False)
            self.login_page.bio_btn.setEnabled(True)
            self.login_page.register_btn.setEnabled(True)
            if mode == "login":
                self._finish_login()
            else:
                AlertModal.info(
                    self, "Success", "Face enrollment complete. You can use Biometric login."
                )

        def done_cancel():
            self._bio_session = None
            self.login_page.set_busy(False)
            self.login_page.bio_btn.setEnabled(True)
            self.login_page.register_btn.setEnabled(True)

        session.succeeded.connect(done_ok)
        session.cancelled.connect(done_cancel)

    def _start_manual_break(self) -> None:
        if self.attendance.on_break:
            AlertModal.info(self, "Break active", "A break is already in progress.")
            return
        picker = BreakSelectDialog(self)
        chosen = {"value": None}

        def on_selected(value: str):
            chosen["value"] = value

        picker.selected.connect(on_selected)
        if picker.exec() != BreakSelectDialog.DialogCode.Accepted or not chosen["value"]:
            return
        try:
            self.attendance.begin_manual_break(chosen["value"])
        except RuntimeError as exc:
            AlertModal.error(self, "Break", str(exc))
            return
        self._break_is_auto = False
        self.activity.mark_break_started()
        self.dashboard.set_break_active(
            True, chosen["value"], self.attendance.break_start_time
        )

    def _end_manual_break(self) -> None:
        if not self.attendance.on_break:
            return
        if self._break_is_auto:
            self.attendance.end_auto_break()
        else:
            self.attendance.end_manual_break()
        self.activity.mark_break_ended()
        self._break_is_auto = False
        self.dashboard.set_break_active(False)

    def _idle_countdown(self, reason: str) -> None:
        if self._idle is not None or self.attendance.on_break:
            return
        # Approximate existing auto-break start offset by inactivity elapsed
        inactivity_elapsed = time.time() - self.activity.last_user_input_time
        start_guess = datetime.now() - timedelta(seconds=inactivity_elapsed)
        dlg = InactivityDialog(
            reason,
            parent=self,
            allow_input=not self._can_verify_face(),
        )
        self._idle = dlg

        def cancelled():
            self.activity.cancel_countdown()
            self._idle = None

        def timed_out():
            self._idle = None
            self.attendance.begin_auto_break(reason, start_guess)
            self._break_is_auto = True
            self.activity.mark_break_started()
            self.dashboard.set_break_active(
                True,
                reason,
                self.attendance.break_start_time,
                face_resume=self._can_verify_face(),
            )

        dlg.cancelled.connect(cancelled)
        dlg.timed_out.connect(timed_out)
        dlg.exec()
        self._idle = None

    def _on_watch(self, snap: dict) -> None:
        if not self._logged_in:
            return
        self.dashboard.camera.set_watch(
            away_seconds=snap["away_seconds"],
            remaining_seconds=snap["remaining_break"],
            countdown=snap["countdown"],
            on_break=snap["on_break"],
        )
        remaining = snap["remaining_break"]
        if snap["on_break"] or snap["countdown"] or remaining > settings.REMINDER_SECONDS:
            self.dashboard.reminder.hide_warning()
        elif remaining > 0:
            self.dashboard.reminder.show_warning(
                remaining,
                away=not snap["visible"],
                camera_available=self._can_verify_face(),
            )

    def _can_verify_face(self) -> bool:
        return self.activity.face_monitor_alive and self.camera.is_live()

    def _on_stay_present(self) -> None:
        # I'm here is only a fallback when there is no camera / face model.
        if self._can_verify_face() and not self.activity.is_user_visible:
            return
        self.activity.note_user_activity()
        if not self._can_verify_face():
            self.activity.note_person_seen()
        self.dashboard.reminder.hide_warning()
        if self._idle is not None and not self._can_verify_face():
            self._idle.note_activity()

    def _resume_from_face(self) -> None:
        """Only a recognized face can cancel a pending auto-break or end one."""
        if self._idle is not None:
            self._idle.cancel_for_face()
        if self.attendance.on_break and self._break_is_auto:
            self._end_manual_break()
        self.dashboard.reminder.hide_warning()

    def _on_note_changed(self, text: str) -> None:
        if self._logged_in:
            self.attendance.set_shift_note(text, persist=True)

    def _presence_hook(self, frame) -> None:
        if not self._logged_in:
            return
        now = time.time()
        if self._presence_busy or now - self._last_presence_check < settings.PRESENCE_CHECK_INTERVAL:
            return
        self._presence_busy = True
        self._last_presence_check = now
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self.activity.face_monitor_alive:
                waiting = self._idle is not None or (
                    self.attendance.on_break and self._break_is_auto
                )
                recognized, boxes = self.face.presence_evaluate(gray, lenient=waiting)
                self.dashboard.camera.set_presence_boxes(boxes, recognized=recognized)
                if self._idle is not None:
                    self._idle.set_face_status(has_face=bool(boxes), recognized=recognized)
                if recognized:
                    self.activity.note_person_seen()
                    if waiting:
                        self._resume_from_face()
                    elif self.dashboard.reminder.isVisible():
                        self.activity.note_user_activity()
                        self.dashboard.reminder.hide_warning()
                else:
                    self.activity.note_person_absent()
            else:
                # No enrolled model — still show detection boxes in red (not verified).
                faces = self.face.detect_faces(gray)
                boxes = [(int(x), int(y), int(w), int(h), False) for (x, y, w, h) in faces]
                self.dashboard.camera.set_presence_boxes(boxes, recognized=False)
        finally:
            self._presence_busy = False

    def _tick_stats(self) -> None:
        if self._logged_in:
            self._refresh_stats()

    def _refresh_stats(self) -> None:
        self.dashboard.update_stats(self.attendance.stats_snapshot())

    def _refresh_breaks(self) -> None:
        self.dashboard.update_breaks(self.attendance.break_log_entries)

    def _export_csv(self) -> None:
        ExportDialog(self.attendance.break_log_entries, self).exec()

    def _summary(self) -> None:
        SummaryDialog(self.attendance, self).exec()

    def _logout(self) -> None:
        if not AlertModal.confirm(
            self,
            "Logout",
            "Are you sure you want to log out? Your shift data will be saved.",
        ):
            return
        self._end_shift(return_to_login=True)

    def _end_shift(self, *, return_to_login: bool) -> None:
        self._stats_timer.stop()
        self.activity.stop()
        # Finalize any open break before saving so logout time is clean.
        if self.attendance.on_break:
            self._end_manual_break()
        self.attendance.set_shift_note(self.dashboard.shift_note())
        self.attendance.save_session()
        self.dashboard.set_shift_note("")
        self._logged_in = False
        self.dashboard.set_break_active(False)
        self.dashboard.camera.clear_presence_boxes()
        if return_to_login:
            self.stack.setCurrentWidget(self.login_page)
            self.setWindowTitle("FaceLES")
            self._set_locked_window_size(
                settings.LOGIN_WINDOW_W,
                settings.LOGIN_WINDOW_H,
            )
            if self.camera._worker is None or not self.camera._worker.isRunning():
                self.camera.start_preview()
        else:
            self.camera.shutdown()

    def _shutdown_session(self) -> None:
        self._end_shift(return_to_login=False)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        et = event.type()
        if not self._logged_in:
            return super().eventFilter(obj, event)
        # Clicks / keys count as desk activity. Hover must not reset the idle
        # clocks — otherwise Auto-break stays near full while you are off camera.
        input_event = et in (
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Wheel,
            QEvent.Type.MouseMove,
        )
        if not input_event:
            return super().eventFilter(obj, event)
        # Mouse/keys cancel a pending auto-break only when the camera (and
        # enrolled face) cannot prove the employee is back.
        if self._idle is not None:
            if not self._can_verify_face():
                self._idle.note_activity()
            return super().eventFilter(obj, event)
        if et != QEvent.Type.MouseMove:
            self.activity.note_user_activity()
        return super().eventFilter(obj, event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._logged_in:
            self._shutdown_session()
        else:
            self.camera.shutdown()
            storage_service.clear_crash_flag()
        event.accept()
