from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from config import theme


class StatusIndicator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusPill")
        self.setFixedHeight(28)
        self.setStyleSheet(
            """
            QFrame#statusPill {
                background: rgba(255,255,255,0.16);
                border: none;
                border-radius: 14px;
            }
            QFrame#statusPill QLabel {
                background: transparent;
                border: none;
            }
            """
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(6)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color:{theme.SUCCESS}; font-size:11px; background:transparent;")
        self.text = QLabel("On shift")
        self.text.setStyleSheet(
            "color:white; font-size:12px; font-weight:600; background:transparent;"
        )
        row.addWidget(self.dot)
        row.addWidget(self.text)

    def set_status(self, kind: str, detail: str | None = None) -> None:
        if kind == "on_break":
            self.dot.setStyleSheet(
                f"color:{theme.ORANGE}; font-size:11px; background:transparent;"
            )
            self.text.setText(f"On break · {detail}" if detail else "On break")
        else:
            self.dot.setStyleSheet(
                f"color:{theme.SUCCESS}; font-size:11px; background:transparent;"
            )
            self.text.setText("On shift")
