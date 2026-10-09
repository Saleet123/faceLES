"""Reusable live camera card with selector and 4:3 preview."""
from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
)

from config import settings, theme
from ui.widgets.icons import svg_icon
from ui.widgets.primary_button import PrimaryButton


class AspectPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"QLabel {{ background:{theme.NAVY}; border:none; border-radius:12px; color:#9ab; }}"
        )
        self.setMinimumSize(240, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pixmap: QPixmap | None = None
        self._ring: QColor | None = None
        self._frame_size: tuple[int, int] | None = None
        self._boxes: list[tuple[int, int, int, int, bool]] = []
        self._message = "Starting camera…"
        self.setText("")

    def set_ring(self, color: QColor | None) -> None:
        self._ring = color
        self.update()

    def set_boxes(self, boxes: list[tuple[int, int, int, int, bool]]) -> None:
        self._boxes = list(boxes)
        self.update()

    def clear_boxes(self) -> None:
        if self._boxes:
            self._boxes = []
            self.update()

    def set_frame(self, frame_bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self._frame_size = (w, h)
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(image)
        self._message = ""
        self.setText("")
        self.setPixmap(QPixmap())
        self.update()

    def set_message(self, text: str) -> None:
        self._pixmap = None
        self._boxes = []
        self._message = text
        self.setText("")
        self.setPixmap(QPixmap())
        self.update()

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return int(width * settings.PREVIEW_H / settings.PREVIEW_W)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def _content_rect(self) -> tuple[float, float, float, float] | None:
        if self._frame_size is None:
            return None
        fw, fh = self._frame_size
        if fw <= 0 or fh <= 0:
            return None
        scale = min(self.width() / fw, self.height() / fh)
        draw_w = fw * scale
        draw_h = fh * scale
        ox = (self.width() - draw_w) / 2
        oy = (self.height() - draw_h) / 2
        return ox, oy, draw_w, draw_h

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        clip = QPainterPath()
        clip.addRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor(theme.NAVY))
        mapping = self._content_rect()
        if self._pixmap is not None and mapping is not None:
            ox, oy, draw_w, draw_h = mapping
            painter.drawPixmap(
                int(ox),
                int(oy),
                int(draw_w),
                int(draw_h),
                self._pixmap,
            )
        elif self._message:
            painter.setPen(QColor("#9ab"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._message)
        if self._ring is not None:
            cx, cy = self.width() // 2, self.height() // 2
            r = min(self.width(), self.height()) // 2 - 14
            painter.setPen(QPen(self._ring, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
        if self._boxes and mapping is not None:
            ox, oy, draw_w, draw_h = mapping
            fw, fh = self._frame_size
            sx = draw_w / fw
            sy = draw_h / fh
            for x, y, w, h, recognized in self._boxes:
                color = QColor(theme.SUCCESS if recognized else theme.DANGER)
                painter.setPen(QPen(color, 3))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                rx, ry = int(ox + x * sx), int(oy + y * sy)
                rw, rh = int(w * sx), int(h * sy)
                painter.drawRect(rx, ry, rw, rh)
                corner = max(8, int(min(rw, rh) * 0.18))
                painter.setPen(QPen(color, 4))
                painter.drawLine(rx, ry, rx + corner, ry)
                painter.drawLine(rx, ry, rx, ry + corner)
                painter.drawLine(rx + rw, ry, rx + rw - corner, ry)
                painter.drawLine(rx + rw, ry, rx + rw, ry + corner)
                painter.drawLine(rx, ry + rh, rx + corner, ry + rh)
                painter.drawLine(rx, ry + rh, rx, ry + rh - corner)
                painter.drawLine(rx + rw, ry + rh, rx + rw - corner, ry + rh)
                painter.drawLine(rx + rw, ry + rh, rx + rw, ry + rh - corner)


class CameraWidget(QFrame):
    camera_selected = Signal(str)
    scan_cancel = Signal()
    scan_recapture = Signal()

    def __init__(self, parent=None, helper: str = "Face the camera before you sign in."):
        super().__init__(parent)
        self.setObjectName("softCard")
        self._helper = helper
        self._scan_mode = False
        self._has_frame = False
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header: [camera icon]  Live camera
        #                        Choose which camera to use
        header = QFrame()
        header.setFixedHeight(44)
        header.setStyleSheet("background:transparent; border:none;")
        head = QHBoxLayout(header)
        head.setSpacing(10)
        head.setContentsMargins(0, 0, 0, 0)

        icon = QLabel()
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(svg_icon("camera", 18).pixmap(18, 18))
        icon.setStyleSheet(
            f"background:#DDEEFF; border:none; border-radius:21px; color:{theme.PRIMARY};"
        )
        icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        head.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        self.title = QLabel("Live camera")
        self.title.setStyleSheet(f"font-size:14px; font-weight:700; color:{theme.NAVY};")
        self.sub = QLabel("Choose which camera to use")
        self.sub.setStyleSheet(f"color:{theme.MUTED}; font-size:12px;")
        titles.addWidget(self.title)
        titles.addWidget(self.sub)
        head.addLayout(titles, 1)
        layout.addWidget(header)

        self.combo = QComboBox()
        self.combo.setFixedHeight(36)
        self.combo.setCursor(Qt.CursorShape.PointingHandCursor)
        view = QListView()
        view.setObjectName("cameraComboView")
        view.setSpacing(2)
        view.setMouseTracking(True)
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.combo.setView(view)
        self.combo.setMaxVisibleItems(6)
        popup = view.window()
        popup.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup.setStyleSheet(
            f"background:{theme.CARD}; border:1px solid {theme.BORDER}; border-radius:12px;"
        )
        self.combo.currentTextChanged.connect(self.camera_selected.emit)
        layout.addWidget(self.combo)

        self.preview = AspectPreview()
        self.preview.setMinimumSize(240, 180)
        self.preview.setMaximumSize(settings.PREVIEW_W, settings.PREVIEW_H)
        self.preview.setFixedSize(settings.PREVIEW_W, settings.PREVIEW_H)
        layout.addWidget(self.preview)

        # Scan-mode chrome (biometric / enrollment) — no second camera
        self.scan_panel = QFrame()
        self.scan_panel.setObjectName("scanPanel")
        self.scan_panel.setStyleSheet(
            """
            QFrame#scanPanel { background: transparent; border: none; }
            QFrame#scanPanel QLabel { background: transparent; border: none; }
            """
        )
        scan_layout = QVBoxLayout(self.scan_panel)
        scan_layout.setContentsMargins(0, 0, 0, 0)
        scan_layout.setSpacing(6)
        self.scan_status = QLabel("Looking for your face…")
        self.scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scan_status.setWordWrap(True)
        self.scan_status.setMinimumHeight(20)
        self.scan_status.setMaximumHeight(36)
        self.scan_status.setStyleSheet(
            f"color:{theme.DANGER}; font-size:12px; font-weight:600; background:transparent;"
        )
        scan_layout.addWidget(self.scan_status)
        self.scan_progress = QProgressBar()
        self.scan_progress.setTextVisible(False)
        self.scan_progress.setFixedHeight(6)
        self.scan_progress.setStyleSheet(
            f"QProgressBar {{ background:{theme.BORDER}; border:none; border-radius:3px; }}"
            f"QProgressBar::chunk {{ background:{theme.PRIMARY}; border-radius:3px; }}"
        )
        scan_layout.addWidget(self.scan_progress)
        self.scan_count = QLabel("")
        self.scan_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scan_count.setStyleSheet(
            f"color:{theme.MUTED}; font-size:11px; background:transparent;"
        )
        scan_layout.addWidget(self.scan_count)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.recapture_btn = PrimaryButton("Recapture", kind="primary")
        self.recapture_btn.setMinimumHeight(34)
        self.recapture_btn.clicked.connect(self.scan_recapture.emit)
        self.cancel_btn = PrimaryButton("Cancel", kind="ghost")
        self.cancel_btn.setMinimumHeight(34)
        self.cancel_btn.clicked.connect(self.scan_cancel.emit)
        actions.addWidget(self.recapture_btn)
        actions.addWidget(self.cancel_btn)
        scan_layout.addLayout(actions)
        self.scan_panel.hide()
        layout.addWidget(self.scan_panel)

        # Compact two-line status block matching the login reference.
        status = QFrame()
        status.setObjectName("camStatus")
        status.setStyleSheet(
            """
            QFrame#camStatus {
                background: #E8F1FB;
                border: none;
                border-radius: 8px;
            }
            QFrame#camStatus QLabel {
                background: transparent;
                border: none;
            }
            """
        )
        status.setFixedHeight(48)
        status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        status_row = QHBoxLayout(status)
        status_row.setContentsMargins(10, 6, 10, 6)
        status_row.setSpacing(8)

        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(12)
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.status_dot.setStyleSheet(
            f"color:{theme.ORANGE}; font-size:11px; padding-top:2px; background:transparent;"
        )
        status_row.addWidget(self.status_dot, 0, Qt.AlignmentFlag.AlignTop)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        self.status_label = QLabel("Starting camera…")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet(
            f"color:{theme.NAVY}; font-size:12px; font-weight:700; background:transparent;"
        )
        self.helper_label = QLabel(helper)
        self.helper_label.setWordWrap(True)
        self.helper_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.helper_label.setStyleSheet(
            f"color:{theme.MUTED}; font-size:12px; background:transparent;"
        )
        copy.addWidget(self.status_label)
        copy.addWidget(self.helper_label)
        status_row.addLayout(copy, 1)
        layout.addWidget(status)
        self._status_frame = status
        self._presence_kind: str | None = None
        self._away_seconds = 0.0
        self._remaining_break = float(settings.INACTIVITY_THRESHOLD)
        self._watch_countdown = False
        self._watch_break = False

    def set_cameras(self, cameras: list[dict], selected_index: int | None) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        if not cameras:
            self.combo.addItem("No camera found")
            self.combo.blockSignals(False)
            self.set_status(False, "No camera found")
            return
        labels = [c["label"] for c in cameras]
        self.combo.addItems(labels)
        if selected_index is not None:
            for i, cam in enumerate(cameras):
                if cam["index"] == selected_index:
                    self.combo.setCurrentIndex(i)
                    break
        self.combo.blockSignals(False)

    def show_frame(self, frame_bgr: np.ndarray) -> None:
        self.preview.set_frame(frame_bgr)
        if not self._has_frame:
            self._has_frame = True
            if not self._scan_mode and not self.preview._boxes:
                self.set_status(True)
        elif not self._scan_mode and not self.preview._boxes:
            # Keep status stable while streaming
            pass

    def set_presence_boxes(
        self,
        boxes: list[tuple[int, int, int, int, bool]],
        *,
        recognized: bool,
    ) -> None:
        if self._scan_mode:
            return
        self.preview.set_boxes(boxes)
        if not boxes:
            self._presence_kind = "away"
        elif recognized:
            self._presence_kind = "ok"
        else:
            self._presence_kind = "unknown"
        self._apply_presence_copy()

    def clear_presence_boxes(self) -> None:
        self.preview.clear_boxes()
        self._presence_kind = None

    def set_watch(
        self,
        *,
        away_seconds: float,
        remaining_seconds: float,
        countdown: bool = False,
        on_break: bool = False,
    ) -> None:
        self._away_seconds = away_seconds
        self._remaining_break = remaining_seconds
        self._watch_countdown = countdown
        self._watch_break = on_break
        self._apply_presence_copy()

    @staticmethod
    def _fmt_mmss(seconds: float) -> str:
        total = max(0, int(seconds))
        return f"{total // 60}:{total % 60:02d}"

    def _apply_presence_copy(self) -> None:
        if self._scan_mode or self._presence_kind is None:
            return
        if self._watch_break:
            self._set_status_line(theme.ORANGE, "On break", "Presence watch paused until you return.")
            return
        if self._presence_kind == "ok":
            self._set_status_line(theme.SUCCESS, "Recognized", "You are in view.")
            return
        away = self._fmt_mmss(self._away_seconds)
        left = self._fmt_mmss(self._remaining_break)
        if self._watch_countdown:
            tip = f"Away {away}  ·  Break starts in {left}"
        else:
            tip = f"Away {away}  ·  Auto-break in {left}"
        if self._presence_kind == "unknown":
            self._set_status_line(theme.DANGER, "Not recognized", tip)
        else:
            self._set_status_line(theme.ORANGE, "Looking for you…", tip)

    def _set_status_line(self, color: str, state: str, tip: str) -> None:
        self.status_dot.setStyleSheet(f"color:{color}; font-size:11px; background:transparent;")
        self.status_label.setText(state)
        self.helper_label.setText(tip)

    def set_status(self, on: bool, detail: str | None = None) -> None:
        """Update connection state. Helper tip stays the product tip — not worker chatter."""
        # Ignore noisy worker strings like "Starting camera…" in the helper slot.
        noisy = {"starting camera…", "starting camera...", "camera is on", "looking for cameras…"}
        tip = self._helper
        if detail and detail.strip().lower() not in noisy:
            tip = detail.strip()

        if on:
            if self._has_frame:
                self._set_status_line(theme.SUCCESS, "Camera is on", tip)
            else:
                self._set_status_line(theme.ORANGE, "Starting…", tip)
                self.preview.set_message("Starting camera…")
        else:
            self._has_frame = False
            self._set_status_line(theme.DANGER, "Camera off", tip or "No signal")
            self.preview.set_message(detail or "No camera signal")

    def set_preview_visible(self, visible: bool) -> None:
        self.preview.setVisible(visible)

    def enter_scan_mode(self, mode: str, progress_max: int) -> None:
        self._scan_mode = True
        if mode == "enroll":
            self.title.setText("Register your face")
            self.sub.setText("Stay centered — samples capture automatically")
            self.recapture_btn.show()
            self.scan_count.setText(f"0 of {progress_max} captures")
        else:
            self.title.setText("Biometric login")
            self.sub.setText("Position your face inside the circle")
            self.recapture_btn.hide()
            self.scan_count.setText("Center your face in the circle")
        self.scan_progress.setRange(0, progress_max)
        self.scan_progress.setValue(0)
        self.scan_status.setText("Looking for your face…")
        self.scan_status.setStyleSheet(
            f"color:{theme.DANGER}; font-size:12px; font-weight:600; background:transparent;"
        )
        self.preview.set_ring(QColor(theme.PRIMARY))
        self.combo.hide()
        self._status_frame.hide()
        self.scan_panel.show()
        self._fit_preview()

    def update_scan(
        self,
        *,
        message: str,
        ok: bool,
        progress: int,
        count_text: str,
        ring_color: str | None = None,
    ) -> None:
        if not self._scan_mode:
            return
        color = theme.SUCCESS if ok else theme.DANGER
        if ring_color:
            color = ring_color
        self.scan_status.setText(message)
        self.scan_status.setStyleSheet(
            f"color:{color}; font-size:12px; font-weight:600; background:transparent;"
        )
        self.scan_progress.setValue(progress)
        self.scan_count.setText(count_text)
        self.preview.set_ring(QColor(color))

    def exit_scan_mode(self) -> None:
        self._scan_mode = False
        self.title.setText("Live camera")
        self.sub.setText("Choose which camera to use")
        self.preview.set_ring(None)
        self.combo.show()
        self.combo.setEnabled(True)
        self.scan_panel.hide()
        self._status_frame.show()
        self._fit_preview()
        self.set_status(True)

    @property
    def scanning(self) -> bool:
        return self._scan_mode

    def _chrome_height(self) -> int:
        chrome = 28 + 44 + 10
        if self.combo.isVisible():
            chrome += 36 + 10
        if self._scan_mode:
            chrome += 20 + 6 + 16 + 34 + 24
        else:
            chrome += 48 + 10
        return chrome

    def _fit_preview(self) -> None:
        # Size the feed from card width. Do not shrink it to leftover height —
        # that crushed the dashboard preview when the timer row was added.
        inner = max(240, self.width() - 28)
        width = min(settings.PREVIEW_W, inner)
        height = int(width * settings.PREVIEW_H / settings.PREVIEW_W)
        if self._scan_mode:
            max_h = self.maximumHeight()
            if max_h < 16777215:
                cap = max(180, max_h - self._chrome_height())
                if height > cap:
                    height = cap
                    width = max(220, int(height * settings.PREVIEW_W / settings.PREVIEW_H))
        self.preview.setFixedSize(width, height)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._fit_preview()
