from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from config import theme
from ui.widgets.icons import svg_pixmap


class StatCard(QFrame):
    def __init__(
        self,
        label: str,
        value: str = "--",
        accent: str = theme.PRIMARY,
        icon_name: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(96)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        badge = QLabel()
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"background:{accent}22; border-radius:8px;")
        if icon_name:
            badge.setPixmap(svg_pixmap(icon_name, 16))
        top.addWidget(badge)
        title = QLabel(label)
        title.setStyleSheet(f"color:{theme.MUTED}; font-size:12px;")
        top.addWidget(title)
        top.addStretch()
        layout.addLayout(top)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color:{theme.NAVY}; font-size:22px; font-weight:700;")
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
