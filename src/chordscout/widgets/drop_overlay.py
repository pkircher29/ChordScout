"""Hero landing drop-zone with vector artwork and instant demo song loader."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class VectorGuitarBadge(QWidget):
    """Vector-painted acoustic guitar and soundwave graphic."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(140, 120)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        # Soundwave frequency bars behind guitar
        bars = [0.3, 0.5, 0.8, 1.0, 0.7, 0.9, 0.4, 0.6, 0.9, 0.5, 0.3]
        bar_w = 4.0
        gap = 4.0
        start_x = (w - (len(bars) * (bar_w + gap))) / 2.0
        mid_y = h / 2.0

        wave_grad = QLinearGradient(0, 0, 0, h)
        wave_grad.setColorAt(0.0, QColor("#0284c7"))
        wave_grad.setColorAt(1.0, QColor("#38bdf8"))
        painter.setBrush(QBrush(wave_grad))
        painter.setPen(Qt.PenStyle.NoPen)

        for i, bh in enumerate(bars):
            bx = start_x + (i * (bar_w + gap))
            bar_height = bh * 45.0
            painter.drawRoundedRect(
                QRectF(bx, mid_y - (bar_height / 2.0), bar_w, bar_height),
                2,
                2,
            )

        # Center pick badge
        pick_rect = QRectF(w / 2.0 - 28, h / 2.0 - 28, 56, 56)
        pick_grad = QLinearGradient(pick_rect.topLeft(), pick_rect.bottomRight())
        pick_grad.setColorAt(0.0, QColor("#1e293b"))
        pick_grad.setColorAt(1.0, QColor("#0f172a"))
        painter.setPen(QPen(QColor("#38bdf8"), 2.0))
        painter.setBrush(QBrush(pick_grad))
        painter.drawEllipse(pick_rect)

        # Music note / guitar glyph
        painter.setPen(QColor("#38bdf8"))
        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        painter.drawText(pick_rect, Qt.AlignmentFlag.AlignCenter, "🎸")


class DropOverlayWidget(QFrame):
    """Full hero drop-zone view."""

    browse_requested = Signal()
    demo_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroFrame")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Vector Icon
        badge = VectorGuitarBadge(self)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignCenter)

        # Main Title
        title = QLabel("Drop an MP3 or Audio File Here")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #f8fafc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        sub = QLabel(
            "ChordScout separates harmonics, extracts Constant-Q chromagrams,\n"
            "and calculates time-aligned guitar chords with visual fretboard diagrams."
        )
        sub.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        # Format chips
        chips_layout = QHBoxLayout()
        chips_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chips_layout.setSpacing(8)
        for fmt in ["MP3", "WAV", "FLAC", "M4A", "OGG", "AAC"]:
            chip = QLabel(fmt)
            chip.setStyleSheet("""
                background-color: #1e2638;
                color: #38bdf8;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #2d3852;
            """)
            chips_layout.addWidget(chip)
        layout.addLayout(chips_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(14)

        btn_browse = QPushButton("📁 Browse Audio File...")
        btn_browse.setObjectName("primaryBtn")
        btn_browse.setMinimumHeight(40)
        btn_browse.clicked.connect(self.browse_requested)

        btn_demo = QPushButton("⚡ Try Demo Song")
        btn_demo.setMinimumHeight(40)
        btn_demo.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #f59e0b;
                border-radius: 8px;
                color: #f59e0b;
                font-weight: bold;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #293548;
                color: #fbbf24;
            }
        """)
        btn_demo.clicked.connect(self.demo_requested)

        btn_layout.addWidget(btn_browse)
        btn_layout.addWidget(btn_demo)
        layout.addLayout(btn_layout)
