"""Fixed-height scrollable break log using QTableView."""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QFrame, QHeaderView, QLabel, QTableView, QVBoxLayout

from config import theme


class BreakTableModel(QAbstractTableModel):
    HEADERS = ["Time", "Duration", "Reason"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[list[str]] = []

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else 3

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return None
        row = self._rows[index.row()]
        return row[index.column()]

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def set_breaks(self, entries: list[list]) -> None:
        rows: list[list[str]] = []
        for entry in reversed(entries):
            start = entry[0] if len(entry) > 0 else ""
            end = entry[1] if len(entry) > 1 else ""
            duration = entry[2] if len(entry) > 2 else ""
            reason = entry[3] if len(entry) > 3 else ""
            try:
                parts = str(duration).split(":")
                if len(parts) == 3:
                    h, m, s = map(float, parts)
                    duration = f"{int(h):02}:{int(m):02}:{s:.2f}"
            except ValueError:
                pass
            rows.append([f"{start} – {end}", duration, str(reason)])
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class BreakLogTable(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background:transparent;")
        head_layout = QVBoxLayout(header)
        head_layout.setContentsMargins(14, 12, 14, 8)
        self.title = QLabel("Break log")
        self.title.setStyleSheet("font-size:14px; font-weight:700;")
        head_layout.addWidget(self.title)
        layout.addWidget(header)

        self.model = BreakTableModel(self)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setShowGrid(False)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.view.verticalHeader().setDefaultSectionSize(34)
        self.view.setMinimumHeight(150)
        self.view.setMaximumHeight(180)
        layout.addWidget(self.view)

        self.empty = QLabel("No breaks recorded yet.")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet(f"color:{theme.MUTED}; padding:24px; font-size:13px;")
        layout.addWidget(self.empty)
        self.empty.hide()

    def set_breaks(self, entries: list[list]) -> None:
        self.model.set_breaks(entries)
        count = len(entries)
        self.title.setText(f"Break log — {count} break{'s' if count != 1 else ''} today")
        empty = count == 0
        self.empty.setVisible(empty)
        self.view.setVisible(not empty)
