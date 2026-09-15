"""Lead-sheet grid view displaying chord progression as measure cards."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from chordscout.models import ChordSegment, format_timestamp
from chordscout.theme import get_chord_color


class ChordCard(QFrame):
    """Visual card for a single chord segment in the lead sheet grid."""

    clicked = Signal(int)  # Emits segment index

    def __init__(self, index: int, segment: ChordSegment, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.index = index
        self.segment = segment
        self.is_active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedSize(115, 80)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Timestamp header
        time_text = format_timestamp(self.segment.start_time)
        self.lbl_time = QLabel(time_text)
        self.lbl_time.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.lbl_time)

        # Huge Chord Name
        self.lbl_chord = QLabel(self.segment.chord)
        self.lbl_chord.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_chord.setStyleSheet("font-size: 22px; font-weight: 900; color: #f8fafc;")
        layout.addWidget(self.lbl_chord)

        # Confidence footer
        conf_pct = int(self.segment.confidence * 100) if self.segment.chord != "N" else 100
        self.lbl_conf = QLabel(f"{conf_pct}%" if self.segment.chord != "N" else "Rest")
        self.lbl_conf.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_conf.setStyleSheet("color: #475569; font-size: 9px; font-weight: 600;")
        layout.addWidget(self.lbl_conf)

        self.update_style()

    def set_active(self, active: bool) -> None:
        if self.is_active != active:
            self.is_active = active
            self.update_style()

    def update_style(self) -> None:
        base_color = get_chord_color(self.segment.chord).name()
        if self.is_active:
            self.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #25334d, stop:1 #182030);
                    border: 2px solid #f59e0b;
                    border-radius: 8px;
                }}
            """)
            self.lbl_chord.setStyleSheet("font-size: 22px; font-weight: 900; color: #f59e0b;")
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #151a27;
                    border: 1px solid #232b3e;
                    border-top: 3px solid {base_color};
                    border-radius: 8px;
                }}
                QFrame:hover {{
                    background-color: #1e2538;
                    border-color: #38bdf8;
                }}
            """)
            self.lbl_chord.setStyleSheet("font-size: 22px; font-weight: 900; color: #f8fafc;")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit(self.index)


class ChordGridView(QWidget):
    """Grid container displaying chord segments grouped in bars/measures."""

    segment_clicked = Signal(int, float)  # Emits (index, start_time)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cards: List[ChordCard] = []
        self.current_active_idx = -1
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def set_segments(self, segments: List[ChordSegment]) -> None:
        # Clear existing cards
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
        self.current_active_idx = -1

        cols_per_row = 4
        for idx, seg in enumerate(segments):
            row = idx // cols_per_row
            col = idx % cols_per_row
            card = ChordCard(idx, seg, self.container)
            card.clicked.connect(self._on_card_clicked)
            self.grid.addWidget(card, row, col)
            self.cards.append(card)

    def _on_card_clicked(self, idx: int) -> None:
        if 0 <= idx < len(self.cards):
            self.set_active_index(idx)
            self.segment_clicked.emit(idx, self.cards[idx].segment.start_time)

    def set_active_index(self, active_idx: int) -> None:
        if self.current_active_idx == active_idx:
            return
        if 0 <= self.current_active_idx < len(self.cards):
            self.cards[self.current_active_idx].set_active(False)
        self.current_active_idx = active_idx
        if 0 <= self.current_active_idx < len(self.cards):
            self.cards[self.current_active_idx].set_active(True)
            # Ensure card is visible in scroll view
            self.cards[self.current_active_idx].ensurePolished()

    def update_playback_time(self, time_sec: float) -> None:
        for idx, card in enumerate(self.cards):
            if card.segment.start_time <= time_sec < card.segment.end_time:
                self.set_active_index(idx)
                return
