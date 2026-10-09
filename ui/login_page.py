"""Modern FaceLES login page matching the supplied design."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QLinearGradient, QColor, QPainter, QPainterPath, QBrush
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import theme
from ui.widgets.camera_widget import CameraWidget
from ui.widgets.icons import svg_icon, svg_pixmap
from ui.widgets.primary_button import PrimaryButton


class BrandSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(246)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 90, 28, 28)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(svg_pixmap("face-brand", 64))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("FaceLES")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color:white; font-size:34px; font-weight:800;")
        layout.addWidget(title)

        sub = QLabel("Face login & attendance")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#d7e6f6; font-size:13px;")
        layout.addWidget(sub)

        line = QFrame()
        line.setFixedSize(56, 2)
        line.setStyleSheet("background:white; border:none;")
        line_wrap = QHBoxLayout()
        line_wrap.addStretch()
        line_wrap.addWidget(line)
        line_wrap.addStretch()
        layout.addLayout(line_wrap)

        tag = QLabel("A smarter way to mark\nyour attendance.")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setStyleSheet("color:#d7e6f6; font-size:13px;")
        layout.addWidget(tag)
        layout.addStretch(1)

        tip = QFrame()
        tip.setObjectName("sidebarTip")
        tip.setStyleSheet(
            """
            QFrame#sidebarTip {
                background: rgba(5,35,88,0.22);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 12px;
            }
            QFrame#sidebarTip QLabel {
                background: transparent;
                border: none;
            }
            """
        )
        tip_row = QHBoxLayout(tip)
        tip_row.setContentsMargins(14, 14, 14, 14)
        tip_row.setSpacing(10)
        shield = QLabel()
        shield.setPixmap(svg_pixmap("shield", 18))
        tip_row.addWidget(shield, 0, Qt.AlignmentFlag.AlignTop)
        tip_text = QLabel("Stay in frame while you sign in.\nYour camera is on the right.")
        tip_text.setWordWrap(True)
        tip_text.setStyleSheet("color:#e8f1fb; font-size:12px;")
        tip_row.addWidget(tip_text, 1)
        layout.addWidget(tip)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(theme.BRIGHT))
        grad.setColorAt(0.45, QColor(theme.PRIMARY))
        grad.setColorAt(1.0, QColor(theme.DEEP))
        painter.fillRect(self.rect(), QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(18, 75, 155, 70))
        path = QPainterPath()
        path.moveTo(0, self.height() * 0.55)
        path.cubicTo(
            self.width() * 0.4,
            self.height() * 0.45,
            self.width() * 0.7,
            self.height() * 0.85,
            self.width(),
            self.height() * 0.65,
        )
        path.lineTo(self.width(), self.height())
        path.lineTo(0, self.height())
        path.closeSubpath()
        painter.drawPath(path)
        super().paintEvent(event)


class IconLineEdit(QWidget):
    def __init__(self, icon_name: str, placeholder: str, parent=None, password: bool = False):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        if password:
            self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.edit)

        self._icon = QLabel(self.edit)
        self._icon.setPixmap(svg_icon(icon_name, 16).pixmap(16, 16))
        self._icon.setFixedSize(18, 18)
        self._icon.move(12, 12)
        self._icon.raise_()

        self._eye = None
        if password:
            self.edit.setTextMargins(0, 0, 36, 0)
            self._eye = QToolButton(self.edit)
            self._eye.setIcon(svg_icon("eye", 16))
            self._eye.setAutoRaise(True)
            self._eye.setCursor(Qt.CursorShape.PointingHandCursor)
            self._eye.clicked.connect(self._toggle)
            self._eye.setFixedSize(28, 28)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._icon.move(12, (self.edit.height() - 18) // 2)
        if self._eye is not None:
            self._eye.move(self.edit.width() - 34, (self.edit.height() - 28) // 2)

    def _toggle(self) -> None:
        if self.edit.echoMode() == QLineEdit.EchoMode.Password:
            self.edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._eye.setIcon(svg_icon("eye-off", 16))
        else:
            self.edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._eye.setIcon(svg_icon("eye", 16))

    def text(self) -> str:
        return self.edit.text().strip()


class LoginPage(QWidget):
    sign_in = Signal(str, str)
    biometric = Signal()
    register_face = Signal()
    camera_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = BrandSidebar()
        root.addWidget(self.sidebar)

        body = QHBoxLayout()
        body.setContentsMargins(32, 23, 16, 28)
        body.setSpacing(26)

        form_wrap = QVBoxLayout()
        form_wrap.setContentsMargins(0, 0, 0, 0)
        form_wrap.setSpacing(0)
        form_wrap.addSpacing(14)
        form = QVBoxLayout()
        form.setSpacing(8)

        heading = QLabel("Sign in")
        heading.setStyleSheet(f"font-size:34px; font-weight:800; color:{theme.NAVY};")
        form.addWidget(heading)
        sub = QLabel("Use your work credentials, or sign in with your face.")
        sub.setStyleSheet(f"color:{theme.MUTED}; font-size:13px; margin-bottom:8px;")
        form.addWidget(sub)
        form.addSpacing(12)

        user_label = QLabel("Username")
        user_label.setStyleSheet(f"color:{theme.MUTED}; font-size:12px;")
        form.addWidget(user_label)
        self.username = IconLineEdit("user", "Enter your username")
        form.addWidget(self.username)
        form.addSpacing(4)

        pass_label = QLabel("Password")
        pass_label.setStyleSheet(f"color:{theme.MUTED}; font-size:12px;")
        form.addWidget(pass_label)
        self.password = IconLineEdit("lock", "Enter your password", password=True)
        form.addWidget(self.password)

        self.sign_in_btn = PrimaryButton("Sign in  ›", kind="primary")
        self.sign_in_btn.setMinimumHeight(44)
        self.sign_in_btn.clicked.connect(self._emit_sign_in)
        self.password.edit.returnPressed.connect(self._emit_sign_in)
        self.username.edit.returnPressed.connect(self._emit_sign_in)
        form.addSpacing(12)
        form.addWidget(self.sign_in_btn)

        divider = QHBoxLayout()
        left = QFrame()
        left.setFixedHeight(1)
        left.setStyleSheet(f"background:{theme.BORDER};")
        right = QFrame()
        right.setFixedHeight(1)
        right.setStyleSheet(f"background:{theme.BORDER};")
        or_label = QLabel("  OR  ")
        or_label.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        divider.addWidget(left, 1)
        divider.addWidget(or_label)
        divider.addWidget(right, 1)
        form.addSpacing(12)
        form.addLayout(divider)

        alts = QHBoxLayout()
        alts.setSpacing(10)
        self.bio_btn = PrimaryButton("Biometric login", kind="deep")
        self.bio_btn.setIcon(svg_icon("face", 16))
        self.bio_btn.setMinimumHeight(44)
        self.bio_btn.clicked.connect(self.biometric.emit)
        self.register_btn = PrimaryButton("Register face", kind="ghost")
        self.register_btn.setIcon(svg_icon("user-plus", 16))
        self.register_btn.setMinimumHeight(44)
        self.register_btn.clicked.connect(self.register_face.emit)
        alts.addWidget(self.bio_btn, 1)
        alts.addWidget(self.register_btn, 1)
        form.addSpacing(4)
        form.addLayout(alts)

        form_wrap.addLayout(form)
        form_wrap.addStretch(1)
        form_host = QWidget()
        form_host.setLayout(form_wrap)
        form_host.setFixedHeight(418)
        body.addWidget(form_host, 1, Qt.AlignmentFlag.AlignVCenter)

        self.camera = CameraWidget(helper="Face the camera before you sign in.")
        self.camera.camera_selected.connect(self.camera_selected.emit)
        self.camera.setFixedWidth(322)
        self.camera.setMaximumHeight(418)
        body.addWidget(self.camera, 0, Qt.AlignmentFlag.AlignTop)

        body_host = QWidget()
        body_host.setLayout(body)
        root.addWidget(body_host, 1)

    def _emit_sign_in(self) -> None:
        self.sign_in.emit(self.username.text(), self.password.text())

    def set_busy(self, busy: bool) -> None:
        self.sign_in_btn.setEnabled(not busy)


def settings_preview_width() -> int:
    from config import settings

    return settings.PREVIEW_W + 48
