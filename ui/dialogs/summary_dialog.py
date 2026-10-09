from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

from config import theme
from services.attendance_service import AttendanceService
from ui.widgets.modal import CenteredModal
from ui.widgets.primary_button import PrimaryButton


class SummaryDialog(CenteredModal):
    def __init__(self, attendance: AttendanceService, parent=None):
        super().__init__(parent, width=460, title="Daily summary")
        self.add_subtitle("Shift totals and break distribution for this session.")

        snap = attendance.stats_snapshot()
        grid = QGridLayout()
        grid.setSpacing(10)
        items = [
            ("Login time", snap["login_time"], theme.PRIMARY),
            ("On shift", snap["on_shift"], theme.SUCCESS),
            ("Breaks", snap["breaks"], theme.ORANGE),
            ("Worked", snap["worked"], theme.PURPLE),
        ]
        for i, (label, value, accent) in enumerate(items):
            card = QFrame()
            card.setObjectName("summaryStatCard")
            card.setStyleSheet(
                f"""
                QFrame#summaryStatCard {{
                    background: {theme.SOFT};
                    border: 1px solid {theme.BORDER};
                    border-radius: 12px;
                }}
                QFrame#summaryStatCard QLabel {{
                    border: none;
                }}
                """
            )
            col = QVBoxLayout(card)
            col.setContentsMargins(14, 12, 14, 12)
            col.setSpacing(4)
            l = QLabel(label)
            l.setStyleSheet(f"color:{theme.MUTED}; font-size:12px; background:transparent;")
            v = QLabel(value)
            v.setStyleSheet(f"color:{accent}; font-size:18px; font-weight:700; background:transparent;")
            col.addWidget(l)
            col.addWidget(v)
            grid.addWidget(card, i // 2, i % 2)
        self.body().addLayout(grid)

        count_row = QHBoxLayout()
        count_label = QLabel(f"Break count")
        count_label.setStyleSheet(f"color:{theme.MUTED}; font-size:13px; background:transparent;")
        count_value = QLabel(str(len(attendance.break_log_entries)))
        count_value.setStyleSheet(f"color:{theme.NAVY}; font-size:15px; font-weight:700; background:transparent;")
        count_row.addWidget(count_label)
        count_row.addStretch()
        count_row.addWidget(count_value)
        self.body().addLayout(count_row)

        note = (attendance.shift_note or "").strip()
        if note:
            note_heading = QLabel("Shift note")
            note_heading.setStyleSheet(
                f"color:{theme.NAVY}; font-size:13px; font-weight:700; background:transparent;"
            )
            self.body().addWidget(note_heading)
            note_body = QLabel(note)
            note_body.setWordWrap(True)
            note_body.setStyleSheet(
                f"color:{theme.MUTED}; font-size:13px; background:transparent;"
            )
            self.body().addWidget(note_body)

        counts = attendance.break_type_counts()
        if counts:
            section = QLabel("Breaks by type")
            section.setStyleSheet(f"color:{theme.NAVY}; font-size:13px; font-weight:700; background:transparent;")
            self.body().addWidget(section)
            for name, count in counts.most_common():
                row = QFrame()
                row.setObjectName("summaryBreakRow")
                row.setStyleSheet(
                    f"""
                    QFrame#summaryBreakRow {{
                        background: {theme.SOFT};
                        border-radius: 8px;
                        border: 1px solid {theme.BORDER};
                    }}
                    QFrame#summaryBreakRow QLabel {{
                        border: none;
                    }}
                    """
                )
                hl = QHBoxLayout(row)
                hl.setContentsMargins(12, 8, 12, 8)
                n = QLabel(str(name))
                n.setStyleSheet("font-size:13px; background:transparent;")
                c = QLabel(str(count))
                c.setAlignment(Qt.AlignmentFlag.AlignRight)
                c.setStyleSheet(f"color:{theme.PRIMARY}; font-size:13px; font-weight:700; background:transparent;")
                hl.addWidget(n, 1)
                hl.addWidget(c)
                self.body().addWidget(row)

        close = PrimaryButton("Close", kind="primary")
        close.clicked.connect(self.accept)
        self.add_actions(close)
