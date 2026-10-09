from PySide6.QtWidgets import QPushButton


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None, kind: str = "primary"):
        super().__init__(text, parent)
        mapping = {
            "primary": "primaryBtn",
            "deep": "deepBtn",
            "ghost": "ghostBtn",
            "danger": "dangerBtn",
        }
        self.setObjectName(mapping.get(kind, "primaryBtn"))
        self.setCursor(self.cursor().shape() if False else self.cursor())
        from PySide6.QtCore import Qt

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)
