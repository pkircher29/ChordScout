"""Realistic Rosewood/Ebony guitar fretboard diagram with strum audio integration."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chordscout.guitar import GuitarChord, get_guitar_chord
from chordscout.synth import GuitarSynthesizer


STRING_NAMES = ["E", "A", "D", "G", "B", "e"]


class FretboardCanvas(QWidget):
    """Custom painted guitar fretboard canvas."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.chord: Optional[GuitarChord] = None
        self.chord_name: str = "None"
        self.capo_fret: int = 0
        self.setMinimumSize(220, 260)

    def set_chord(self, chord_name: str, capo_fret: int = 0) -> None:
        self.chord_name = chord_name
        self.chord = get_guitar_chord(chord_name)
        self.capo_fret = capo_fret
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        # Outer card background
        painter.fillRect(QRectF(0, 0, w, h), QColor("#131722"))

        # Geometry calculations
        pad_x = 42.0
        margin_top = 46.0
        margin_bottom = 24.0
        board_w = w - (pad_x * 2.0)
        board_h = h - margin_top - margin_bottom
        num_frets = 5
        num_strings = 6
        dx = board_w / (num_strings - 1)
        dy = board_h / num_frets

        # 1. Draw Rosewood Fretboard wood block
        wood_grad = QLinearGradient(pad_x, margin_top, pad_x + board_w, margin_top + board_h)
        wood_grad.setColorAt(0.0, QColor("#1f1714"))
        wood_grad.setColorAt(0.5, QColor("#281e1a"))
        wood_grad.setColorAt(1.0, QColor("#181210"))
        painter.setPen(QPen(QColor("#3d2c25"), 1.5))
        painter.setBrush(QBrush(wood_grad))
        painter.drawRoundedRect(QRectF(pad_x - 6, margin_top - 4, board_w + 12, board_h + 8), 6, 6)

        # Base fret calculation
        base_fret = self.chord.base_fret if self.chord else 1

        # 2. Draw Mother-of-Pearl Inlay Dots on fretboard
        for f in range(1, num_frets + 1):
            abs_fret = base_fret + f - 1
            if abs_fret in (3, 5, 7, 9):
                center_y = margin_top + ((f - 0.5) * dy)
                center_x = pad_x + (board_w / 2.0)
                inlay_grad = QRadialGradient(center_x, center_y, 6)
                inlay_grad.setColorAt(0.0, QColor("#f1f5f9"))
                inlay_grad.setColorAt(0.7, QColor("#94a3b8"))
                inlay_grad.setColorAt(1.0, QColor("#475569"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(inlay_grad))
                painter.drawEllipse(QPointF(center_x, center_y), 4.5, 4.5)
            elif abs_fret == 12:
                # Double dot at 12th fret
                center_y = margin_top + ((f - 0.5) * dy)
                for offset in (-dx * 0.9, dx * 0.9):
                    cx = pad_x + (board_w / 2.0) + offset
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor("#cbd5e1")))
                    painter.drawEllipse(QPointF(cx, center_y), 4.0, 4.0)

        # 3. Base Fret indicator (if > 1)
        if base_fret > 1:
            painter.setPen(QColor("#fbbf24"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                QRectF(0, margin_top + (dy * 0.15), pad_x - 10, dy),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{base_fret}fr",
            )

        # 4. Draw Nut (Bone/Ivory) or Capo or thin fret line
        nut_rect = QRectF(pad_x - 4, margin_top - 5, board_w + 8, 5)
        if base_fret == 1:
            nut_grad = QLinearGradient(pad_x, 0, pad_x + board_w, 0)
            nut_grad.setColorAt(0.0, QColor("#e2e8f0"))
            nut_grad.setColorAt(0.5, QColor("#ffffff"))
            nut_grad.setColorAt(1.0, QColor("#cbd5e1"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(nut_grad))
            painter.drawRoundedRect(nut_rect, 2, 2)
        else:
            painter.setPen(QPen(QColor("#94a3b8"), 2))
            painter.drawLine(int(pad_x), int(margin_top), int(pad_x + board_w), int(margin_top))

        # 5. Draw Fret Wires (Horizontal metallic nickel bars)
        for i in range(1, num_frets + 1):
            fret_y = margin_top + (i * dy)
            # Fret shadow
            painter.setPen(QPen(QColor("#0a0a0a"), 1.0))
            painter.drawLine(int(pad_x), int(fret_y + 1), int(pad_x + board_w), int(fret_y + 1))
            # Fret metal highlight
            painter.setPen(QPen(QColor("#cbd5e1"), 1.8))
            painter.drawLine(int(pad_x), int(fret_y), int(pad_x + board_w), int(fret_y))

        # 6. Draw Strings (Vertical with realistic gauges & wound texture)
        for s in range(num_strings):
            x = pad_x + (s * dx)
            # Low strings (wound bronze) to high strings (plain steel)
            if s < 3:
                # Wound strings (thicker, bronze/nickel hue)
                thickness = 3.5 - (s * 0.6)
                painter.setPen(QPen(QColor("#d97706"), thickness))
            else:
                # Plain steel strings
                thickness = 2.0 - ((s - 3) * 0.4)
                painter.setPen(QPen(QColor("#e2e8f0"), max(1.1, thickness)))
            painter.drawLine(int(x), int(margin_top - 4), int(x), int(margin_top + board_h + 3))

        # 7. Draw String Names at bottom
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        for s in range(num_strings):
            x = pad_x + (s * dx)
            painter.setPen(QColor("#64748b"))
            painter.drawText(
                QRectF(x - 12, margin_top + board_h + 6, 24, 16),
                Qt.AlignmentFlag.AlignCenter,
                STRING_NAMES[s],
            )

        # 8. Draw Open 'O', Muted 'X', or Finger Dots
        if not self.chord or self.chord_name in ("N", "None", ""):
            # Subtle placeholder message
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(
                QRectF(0, margin_top + (board_h * 0.35), w, 40),
                Qt.AlignmentFlag.AlignCenter,
                "No chord active" if self.chord_name == "N" else "Select a chord",
            )
            return

        for s, fret in enumerate(self.chord.frets):
            x = pad_x + (s * dx)

            if fret == -1:
                # Muted 'X' pill badge above nut
                pill_rect = QRectF(x - 9, margin_top - 28, 18, 18)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor("#4c1d24")))
                painter.drawRoundedRect(pill_rect, 9, 9)
                painter.setPen(QColor("#f43f5e"))
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, "x")

            elif fret == 0:
                # Open 'O' pill badge above nut
                pill_rect = QRectF(x - 9, margin_top - 28, 18, 18)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor("#133629")))
                painter.drawRoundedRect(pill_rect, 9, 9)
                painter.setPen(QColor("#10b981"))
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, "o")

            else:
                # Fret dot
                rel_fret = fret - base_fret + 1
                if 1 <= rel_fret <= num_frets:
                    dot_y = margin_top + ((rel_fret - 0.5) * dy)
                    dot_r = 10.0

                    # Glowing cyan outer ring
                    glow_grad = QRadialGradient(x, dot_y, dot_r + 4)
                    glow_grad.setColorAt(0.0, QColor("#38bdf8"))
                    glow_grad.setColorAt(0.7, QColor("#0284c7"))
                    glow_grad.setColorAt(1.0, QColor("#0369a1"))

                    painter.setPen(QPen(QColor("#ffffff"), 1.5))
                    painter.setBrush(QBrush(glow_grad))
                    painter.drawEllipse(QPointF(x, dot_y), dot_r, dot_r)

                    # Finger number inside dot
                    finger = self.chord.fingers[s] if s < len(self.chord.fingers) else 0
                    if finger > 0:
                        painter.setPen(QColor("#ffffff"))
                        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                        painter.drawText(
                            QRectF(x - dot_r, dot_y - dot_r, dot_r * 2, dot_r * 2),
                            Qt.AlignmentFlag.AlignCenter,
                            str(finger),
                        )


class GuitarFretboardWidget(QWidget):
    """Complete guitar voicing panel with diagram header, tab string, and strum button."""

    strum_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.synth = GuitarSynthesizer(self)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: Chord Name & Strum button
        header = QHBoxLayout()
        self.lbl_chord_title = QLabel("C")
        self.lbl_chord_title.setStyleSheet("font-size: 26px; font-weight: 900; color: #38bdf8;")

        self.btn_strum = QPushButton("🔊 Strum")
        self.btn_strum.setToolTip("Play synthesized acoustic guitar chord")
        self.btn_strum.setFixedHeight(30)
        self.btn_strum.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0284c7);
                border: 1px solid #38bdf8;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background: #0284c7;
            }
        """)
        self.btn_strum.clicked.connect(self.on_strum_clicked)

        header.addWidget(self.lbl_chord_title)
        header.addStretch()
        header.addWidget(self.btn_strum)
        layout.addLayout(header)

        # Tab string subtitle (e.g. "Tab: x 3 2 0 1 0")
        self.lbl_tab_string = QLabel("Fingering: x 3 2 0 1 0")
        self.lbl_tab_string.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: monospace;")
        layout.addWidget(self.lbl_tab_string)

        # Interactive Canvas
        self.canvas = FretboardCanvas(self)
        layout.addWidget(self.canvas, 1)

    def set_chord(self, chord_name: str, capo_fret: int = 0) -> None:
        self.canvas.set_chord(chord_name, capo_fret)
        gc = self.canvas.chord

        if chord_name in ("N", "None", ""):
            self.lbl_chord_title.setText("—")
            self.lbl_tab_string.setText("No chord / Rest")
            self.btn_strum.setEnabled(False)
        else:
            self.lbl_chord_title.setText(chord_name)
            self.btn_strum.setEnabled(gc is not None)
            if gc:
                fret_note = f" (Fret {gc.base_fret})" if gc.base_fret > 1 else ""
                self.lbl_tab_string.setText(f"Tab: {gc.string_display}{fret_note}")
            else:
                self.lbl_tab_string.setText("Custom voicing")

    def on_strum_clicked(self) -> None:
        if self.canvas.chord:
            self.synth.play_chord(self.canvas.chord)
            self.strum_requested.emit(self.canvas.chord_name)
