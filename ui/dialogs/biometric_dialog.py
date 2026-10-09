"""Biometric login / enrollment logic — uses the login page live camera (no second preview)."""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QColor

from config import settings, theme
from services.face_recognition_service import FaceRecognitionService
from ui.widgets.camera_widget import CameraWidget


class BiometricSession(QObject):
    """
    Runs face match / enrollment against frames from the existing CameraWidget.

    There is only one camera stream — the right-side live preview. This session
    overlays the alignment ring and status on that preview.
    """

    succeeded = Signal()
    cancelled = Signal()

    def __init__(
        self,
        mode: str,
        face_svc: FaceRecognitionService,
        camera_widget: CameraWidget,
        parent=None,
    ):
        super().__init__(parent)
        self.mode = mode  # "login" | "enroll"
        self.face_svc = face_svc
        self.camera = camera_widget
        self._closed = False
        self._faces: list = []
        self._count = 0
        self._last_capture = 0.0
        self._login_hits = 0
        self._deadline = time.time() + settings.BIOMETRIC_LOGIN_DEADLINE
        self._matched = False

        progress_max = settings.ENROLL_TARGET if mode == "enroll" else settings.LOGIN_MATCH_FRAMES
        self.camera.enter_scan_mode(mode, progress_max)
        self.camera.scan_cancel.connect(self._cancel)
        self.camera.scan_recapture.connect(self._recapture)

    def on_frame(self, frame_bgr) -> None:
        if self._closed or self._matched:
            return
        assessment, _faces = self.face_svc.process_bgr(frame_bgr)
        if self.mode == "enroll":
            self._handle_enroll(assessment)
        else:
            self._handle_login(assessment)

    def _handle_enroll(self, assessment) -> None:
        self.camera.update_scan(
            message=assessment.message,
            ok=assessment.ok,
            progress=self._count,
            count_text=f"{self._count} of {settings.ENROLL_TARGET} captures",
        )
        now = time.time()
        if assessment.ok and assessment.face_roi is not None:
            if (
                now - self._last_capture > settings.ENROLL_CAPTURE_INTERVAL
                and self._count < settings.ENROLL_TARGET
            ):
                self._faces.append(assessment.face_roi)
                self._count += 1
                self._last_capture = now
                self.camera.update_scan(
                    message=assessment.message,
                    ok=True,
                    progress=self._count,
                    count_text=f"{self._count} of {settings.ENROLL_TARGET} captures",
                )
                if self._count >= settings.ENROLL_TARGET:
                    self._finish_enroll()

    def _handle_login(self, assessment) -> None:
        matched = False
        message = assessment.message
        count_text = "Center your face in the circle"
        if assessment.ok and assessment.face_roi is not None:
            result = self.face_svc.match_face(assessment.face_roi)
            matched = result.ok
            if matched:
                message = "Hold still…"
                count_text = "Verifying identity…"
                self._login_hits = min(settings.LOGIN_MATCH_FRAMES, self._login_hits + 1)
            else:
                message = result.message
                self._login_hits = max(0, self._login_hits - 1)
        else:
            self._login_hits = max(0, self._login_hits - 1)

        self.camera.update_scan(
            message=message,
            ok=matched,
            progress=self._login_hits,
            count_text=count_text,
            ring_color=theme.SUCCESS if matched else theme.DANGER,
        )
        if self._login_hits >= settings.LOGIN_MATCH_FRAMES:
            self._matched = True
            self.camera.update_scan(
                message="Face matched",
                ok=True,
                progress=self._login_hits,
                count_text="Signing you in…",
                ring_color=theme.SUCCESS,
            )
            QTimer.singleShot(450, self._finish_login)
            return
        if time.time() >= self._deadline:
            self.camera.update_scan(
                message="Face not recognized. Try again or use password.",
                ok=False,
                progress=self._login_hits,
                count_text="Timed out",
            )
            QTimer.singleShot(900, self._cancel)

    def _finish_enroll(self) -> None:
        try:
            self.face_svc.train_and_save(self._faces)
        except Exception as exc:
            self.camera.update_scan(
                message=str(exc),
                ok=False,
                progress=self._count,
                count_text=f"{self._count} of {settings.ENROLL_TARGET} captures",
            )
            return
        self._close_ui()
        self.succeeded.emit()

    def _finish_login(self) -> None:
        if not self._matched:
            return
        self._close_ui()
        self.succeeded.emit()

    def _recapture(self) -> None:
        self._faces = []
        self._count = 0
        self._last_capture = 0.0
        self.camera.update_scan(
            message="Looking for your face…",
            ok=False,
            progress=0,
            count_text=f"0 of {settings.ENROLL_TARGET} captures",
            ring_color=theme.PRIMARY,
        )

    def _cancel(self) -> None:
        self._close_ui()
        self.cancelled.emit()

    def _close_ui(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.camera.scan_cancel.disconnect(self._cancel)
        except (TypeError, RuntimeError):
            pass
        try:
            self.camera.scan_recapture.disconnect(self._recapture)
        except (TypeError, RuntimeError):
            pass
        self.camera.exit_scan_mode()


# Backwards-compatible name used by imports
BiometricDialog = BiometricSession
