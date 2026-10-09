from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit

from config import settings, theme
from services import storage_service
from ui.widgets.modal import AlertModal, CenteredModal
from ui.widgets.primary_button import PrimaryButton


class ExportDialog(CenteredModal):
    def __init__(self, breaks: list[list], parent=None):
        super().__init__(parent, width=460, title="Export CSV")
        self.breaks = breaks
        self.add_subtitle("Export today's break log to a CSV file.")

        name_label = QLabel("File name")
        name_label.setStyleSheet(f"color:{theme.MUTED}; font-size:12px; background:transparent;")
        self.body().addWidget(name_label)
        default = f"breaks_{datetime.now().strftime('%Y%m%d')}.csv"
        self.name_edit = QLineEdit(default)
        self.name_edit.setStyleSheet(
            f"QLineEdit {{ padding: 10px 12px; border:1px solid {theme.BORDER}; border-radius:9px; }}"
        )
        self.body().addWidget(self.name_edit)

        path_label = QLabel("Save to")
        path_label.setStyleSheet(f"color:{theme.MUTED}; font-size:12px; background:transparent;")
        self.body().addWidget(path_label)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit(settings.EXPORT_DIR)
        self.path_edit.setStyleSheet(
            f"QLineEdit {{ padding: 10px 12px; border:1px solid {theme.BORDER}; border-radius:9px; }}"
        )
        browse = PrimaryButton("Browse", kind="ghost")
        browse.setMinimumHeight(40)
        browse.setMinimumWidth(96)
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        self.body().addLayout(path_row)

        cancel = PrimaryButton("Cancel", kind="ghost")
        cancel.clicked.connect(self.reject)
        export = PrimaryButton("Export", kind="primary")
        export.clicked.connect(self._export)
        self.add_actions(cancel, export)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select folder", self.path_edit.text())
        if path:
            self.path_edit.setText(path)

    def _export(self) -> None:
        name = self.name_edit.text().strip() or "breaks.csv"
        if not name.endswith(".csv"):
            name += ".csv"
        folder = self.path_edit.text().strip() or settings.EXPORT_DIR
        path = os.path.join(folder, name)
        try:
            storage_service.export_breaks_csv(path, self.breaks)
        except OSError as exc:
            AlertModal.error(self.parentWidget() or self, "Export failed", str(exc))
            return
        AlertModal.info(self.parentWidget() or self, "Export complete", f"Saved to:\n{path}")
        self.accept()
