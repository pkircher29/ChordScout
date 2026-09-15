"""Design system, color palette, and stylesheets for ChordScout."""

from __future__ import annotations

from PySide6.QtGui import QColor


class Colors:
    """Design palette for dark studio theme."""

    # Backgrounds
    BG_MAIN = "#0b0d14"
    BG_PANEL = "#131722"
    BG_CARD = "#1a202f"
    BG_CARD_HOVER = "#232b3e"
    BG_ELEVATED = "#252d42"

    # Borders
    BORDER_SUBTLE = "#1e2638"
    BORDER_MEDIUM = "#2e3952"
    BORDER_BRIGHT = "#475569"

    # Text
    TEXT_PRIMARY = "#f8fafc"
    TEXT_SECONDARY = "#94a3b8"
    TEXT_MUTED = "#64748b"

    # Accents
    ACCENT_CYAN = "#38bdf8"
    ACCENT_CYAN_GLOW = "#0284c7"
    ACCENT_AMBER = "#f59e0b"
    ACCENT_GOLD = "#fbbf24"
    ACCENT_EMERALD = "#10b981"
    ACCENT_ROSE = "#f43f5e"
    ACCENT_PURPLE = "#a855f7"
    ACCENT_INDIGO = "#6366f1"

    # Fretboard
    ROSEWOOD_DARK = "#1a1412"
    ROSEWOOD_LIGHT = "#2a1e19"
    FRET_WIRE = "#94a3b8"
    FRET_NUT = "#f1f5f9"
    INLAY_PEARL = "#cbd5e1"
    STRING_SILVER = "#cbd5e1"
    STRING_BRONZE = "#d97706"


def get_chord_color(chord: str) -> QColor:
    """Return a distinct, harmonically-coherent color for a chord."""
    if not chord or chord == "N":
        return QColor("#1e2330")

    is_minor = "m" in chord and "maj" not in chord
    is_seventh = "7" in chord

    # Extract root note (C, C#, D, etc.)
    root = chord.rstrip("m7").rstrip("maj").rstrip("sus4").rstrip("5")

    # Harmonic wheel hue offsets
    root_hues = {
        "C": 200,   # Sky Blue
        "C#": 220,  # Royal Blue
        "Db": 220,
        "D": 260,   # Violet
        "D#": 280,  # Purple
        "Eb": 280,
        "E": 320,   # Magenta / Pink
        "F": 350,   # Crimson / Red
        "F#": 25,   # Amber / Orange
        "Gb": 25,
        "G": 45,    # Warm Gold
        "G#": 85,   # Lime / Olive
        "Ab": 85,
        "A": 140,   # Emerald
        "A#": 170,  # Teal
        "Bb": 170,
        "B": 185,   # Aqua
    }

    base_hue = root_hues.get(root, 210)
    sat = 180 if is_minor else 210
    val = 140 if is_minor else 170
    if is_seventh:
        sat = min(255, sat + 30)

    color = QColor()
    color.setHsv(base_hue, sat, val)
    return color


STUDIO_DARK_STYLESHEET = """
QMainWindow {
    background-color: #0b0d14;
}

QWidget {
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #10141e;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2a3348;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3b4763;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #10141e;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #2a3348;
    min-width: 25px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #3b4763;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Card Frames */
QFrame#cardFrame {
    background-color: #131722;
    border: 1px solid #1e2638;
    border-radius: 10px;
}

QFrame#heroFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #151a28, stop:1 #0f121d);
    border: 2px dashed #2d3852;
    border-radius: 14px;
}

/* Push Buttons */
QPushButton {
    background-color: #1c2333;
    border: 1px solid #2e3952;
    border-radius: 7px;
    padding: 7px 16px;
    font-weight: 600;
    color: #f1f5f9;
}
QPushButton:hover {
    background-color: #273147;
    border-color: #38bdf8;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #151a28;
    border-color: #0284c7;
}
QPushButton:disabled {
    background-color: #111520;
    border-color: #1b2130;
    color: #475569;
}

/* Primary Action Buttons */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
    border: none;
    color: #ffffff;
    font-weight: bold;
    padding: 8px 20px;
    border-radius: 8px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0ea5e9);
}

/* Transport Play Button */
QPushButton#playBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f59e0b, stop:1 #fbbf24);
    border: none;
    color: #0b0d14;
    font-size: 15px;
    font-weight: 800;
    border-radius: 18px;
    min-width: 90px;
    height: 36px;
}
QPushButton#playBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d97706, stop:1 #f59e0b);
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #1e2638;
    background-color: #131722;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background-color: #0e111a;
    border: 1px solid #1e2638;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 4px;
    color: #94a3b8;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #131722;
    border-color: #38bdf8;
    color: #38bdf8;
}
QTabBar::tab:hover:!selected {
    background-color: #171d2b;
    color: #cbd5e1;
}

/* Table Widget */
QTableWidget {
    background-color: #10141f;
    gridline-color: #1e2638;
    border: 1px solid #1e2638;
    border-radius: 8px;
    selection-background-color: #1e3a5f;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #161c2b;
    color: #94a3b8;
    padding: 7px 10px;
    border: none;
    border-right: 1px solid #1e2638;
    border-bottom: 1px solid #1e2638;
    font-weight: 700;
    font-size: 12px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #1c2333;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #f8fafc;
    border: 2px solid #0284c7;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #38bdf8;
}

/* Context Menus */
QMenu {
    background-color: #161c2b;
    border: 1px solid #2e3952;
    border-radius: 8px;
    padding: 6px;
    color: #f8fafc;
}
QMenu::item {
    padding: 7px 22px;
    border-radius: 5px;
}
QMenu::item:selected {
    background-color: #232c40;
    color: #38bdf8;
}
QMenu::separator {
    height: 1px;
    background-color: #242e44;
    margin: 4px 6px;
}

/* Progress Bar */
QProgressBar {
    background-color: #121622;
    border: 1px solid #232c40;
    border-radius: 5px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
    border-radius: 4px;
}

/* Badges and Labels */
QLabel#badgeLabel {
    background-color: #1c2436;
    border: 1px solid #2d3852;
    border-radius: 6px;
    padding: 3px 10px;
    font-weight: 600;
    color: #38bdf8;
}

QLabel#hudChordBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a2235, stop:1 #111624);
    border: 2px solid #38bdf8;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 32px;
    font-weight: 900;
    color: #38bdf8;
}

QCheckBox {
    color: #cbd5e1;
    font-weight: 500;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #334155;
    border-radius: 4px;
    background: #111520;
}
QCheckBox::indicator:checked {
    background: #0284c7;
    border-color: #38bdf8;
}
"""
