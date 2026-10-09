"""Central FaceLES visual design tokens."""

import os

from config import settings as _settings

PRIMARY = "#1769D2"
BRIGHT = "#2688F0"
DEEP = "#124B9B"
SIDEBAR = "#1E5BB8"
NAVY = "#102347"
MUTED = "#6880A3"
BG = "#F7FAFF"
CARD = "#FFFFFF"
SOFT = "#EDF5FF"
BORDER = "#DCE8F8"
SUCCESS = "#20BD83"
DANGER = "#EF5260"
PURPLE = "#7868EE"
ORANGE = "#C47A38"

FONT_FAMILY = "Ubuntu"
CHEVRON_ICON = os.path.join(_settings.BUNDLE_DIR, "assets", "icons", "chevron-down.svg").replace("\\", "/")

QSS = f"""
* {{
    font-family: "{FONT_FAMILY}", "Noto Sans", "DejaVu Sans", sans-serif;
    color: {NAVY};
}}
QMainWindow, QWidget#centralRoot {{
    background: {BG};
}}
QLabel#muted {{
    color: {MUTED};
}}
QLineEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 11px 12px 11px 36px;
    font-size: 14px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:focus {{
    border: 1.5px solid {PRIMARY};
}}
QPlainTextEdit#shiftNote {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 8px 10px;
    font-size: 13px;
    color: {NAVY};
    selection-background-color: {PRIMARY};
}}
QPlainTextEdit#shiftNote:focus {{
    border: 1.5px solid {PRIMARY};
}}
QPushButton#primaryBtn {{
    background: {PRIMARY};
    color: white;
    border: none;
    border-radius: 9px;
    padding: 12px 18px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#primaryBtn:hover {{
    background: {BRIGHT};
}}
QPushButton#primaryBtn:pressed {{
    background: {DEEP};
}}
QPushButton#deepBtn {{
    background: {DEEP};
    color: white;
    border: none;
    border-radius: 9px;
    padding: 11px 14px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#deepBtn:hover {{
    background: {PRIMARY};
}}
QPushButton#ghostBtn {{
    background: {CARD};
    color: {PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 11px 14px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#ghostBtn:hover {{
    background: {SOFT};
}}
QPushButton#dangerBtn {{
    background: {DANGER};
    color: white;
    border: none;
    border-radius: 9px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#dangerBtn:hover {{
    background: #d94452;
}}
QComboBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px 32px 8px 12px;
    font-size: 13px;
    font-weight: 600;
    color: {NAVY};
    min-height: 20px;
}}
QComboBox:hover {{
    border: 1px solid {PRIMARY};
}}
QComboBox:focus, QComboBox:on {{
    border: 1.5px solid {PRIMARY};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url("{CHEVRON_ICON}");
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 6px;
    outline: 0;
    selection-background-color: {SOFT};
    selection-color: {NAVY};
    font-size: 13px;
}}
QComboBox QAbstractItemView::item {{
    min-height: 32px;
    padding: 6px 10px;
    border-radius: 8px;
    color: {NAVY};
}}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {{
    background: {SOFT};
    color: {PRIMARY};
}}
QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#softCard {{
    background: {SOFT};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QTableView {{
    background: {CARD};
    border: none;
    gridline-color: {BORDER};
    selection-background-color: {SOFT};
    selection-color: {NAVY};
    font-size: 13px;
}}
QHeaderView::section {{
    background: {SOFT};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 700;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #c5d6ec;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QDialog {{
    background: {CARD};
}}
"""
