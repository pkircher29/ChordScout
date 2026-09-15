"""High-DPI interactive audio waveform timeline with chord segments, scrub laser, and tooltips."""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QToolTip, QWidget

from chordscout.audio import compute_waveform_envelope
from chordscout.models import ChordSegment, format_timestamp
from chordscout.theme import get_chord_color


class WaveformTimelineWidget(QWidget):
    """Visual DAW-style timeline displaying mirrored audio waveform, chord zones, and playhead."""

    seek_requested = Signal(float)  # Emits target seconds
    segment_selected = Signal(int)  # Emits row/segment index

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.segments: List[ChordSegment] = []
        self.total_duration: float = 1.0
        self.current_time: float = 0.0
        self.waveform_peaks: Optional[np.ndarray] = None

        # Loop A-B points
        self.loop_start: Optional[float] = None
        self.loop_end: Optional[float] = None
        self.is_looping: bool = False

        self.is_scrubbing = False
        self.setFixedHeight(75)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_data(
        self,
        segments: List[ChordSegment],
        duration: float,
        audio_data: Optional[np.ndarray] = None,
    ) -> None:
        self.segments = segments
        self.total_duration = max(0.1, duration)

        if audio_data is not None and len(audio_data) > 0:
            # Generate 1200 downsampled peak points for smooth waveform display
            self.waveform_peaks = compute_waveform_envelope(audio_data, num_points=1200)
        else:
            self.waveform_peaks = None

        self.update()

    def set_current_time(self, time_sec: float) -> None:
        self.current_time = max(0.0, min(time_sec, self.total_duration))
        self.update()

    def set_loop_range(self, start: Optional[float], end: Optional[float], enabled: bool = True) -> None:
        self.loop_start = start
        self.loop_end = end
        self.is_looping = enabled
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.total_duration <= 0 or self.width() <= 0:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_scrubbing = True
            sec = (event.position().x() / self.width()) * self.total_duration
            self.seek_requested.emit(max(0.0, min(self.total_duration, sec)))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.total_duration <= 0 or self.width() <= 0:
            return

        sec = max(0.0, min(self.total_duration, (event.position().x() / self.width()) * self.total_duration))

        if self.is_scrubbing:
            self.seek_requested.emit(sec)
        else:
            # Show hover inspection tooltip
            hovered_seg = None
            hovered_idx = -1
            for idx, s in enumerate(self.segments):
                if s.start_time <= sec < s.end_time:
                    hovered_seg = s
                    hovered_idx = idx
                    break

            if hovered_seg:
                tip = (
                    f"⏱ {format_timestamp(hovered_seg.start_time, True)} - {format_timestamp(hovered_seg.end_time, True)}\n"
                    f"🎸 Chord: {hovered_seg.chord}\n"
                    f"🎯 Confidence: {int(hovered_seg.confidence * 100)}%"
                )
                QToolTip.showText(event.globalPosition().toPoint(), tip, self)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_scrubbing = False

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        mid_y = h / 2.0

        # Background
        painter.fillRect(QRectF(0, 0, w, h), QColor("#0d1017"))

        if not self.segments or self.total_duration <= 0:
            painter.setPen(QColor("#334155"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Audio Waveform & Chord Progression")
            return

        # 1. Draw Chord Segment Blocks (Color-coded zones)
        label_font = QFont("Segoe UI", 11, QFont.Weight.Black)
        time_font = QFont("Segoe UI", 8, QFont.Weight.Bold)

        for seg in self.segments:
            x1 = (seg.start_time / self.total_duration) * w
            x2 = (seg.end_time / self.total_duration) * w
            seg_w = max(1.0, x2 - x1)

            # Get harmonic color
            base_col = get_chord_color(seg.chord)
            is_active = seg.start_time <= self.current_time < seg.end_time

            # Semi-transparent chord background block
            fill_col = QColor(base_col)
            fill_col.setAlpha(110 if is_active else 55)
            painter.fillRect(QRectF(x1, 0, seg_w, h), fill_col)

            # Segment border divider
            painter.setPen(QPen(QColor("#1e293b"), 1.0))
            painter.drawLine(int(x1), 0, int(x1), int(h))

            # Chord Pill Badge in Center
            if seg_w > 26 and seg.chord != "N":
                badge_w = min(seg_w - 6, 60.0)
                badge_h = 24.0
                bx = x1 + (seg_w - badge_w) / 2.0
                by = mid_y - (badge_h / 2.0)

                # Pill background
                pill_col = QColor(base_col)
                pill_col.setAlpha(220 if is_active else 170)
                painter.setPen(QPen(QColor("#ffffff") if is_active else QColor("#94a3b8"), 1.2))
                painter.setBrush(QBrush(pill_col))
                painter.drawRoundedRect(QRectF(bx, by, badge_w, badge_h), 5, 5)

                # Chord text
                painter.setPen(QColor("#ffffff"))
                painter.setFont(label_font)
                painter.drawText(QRectF(bx, by, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, seg.chord)

        # 2. Draw Mirrored Audio Waveform
        if self.waveform_peaks is not None and len(self.waveform_peaks) > 0:
            num_peaks = len(self.waveform_peaks)
            dx = w / num_peaks
            max_amp = mid_y - 4.0

            # Mirrored waveform path
            top_points = []
            bot_points = []

            for i, val in enumerate(self.waveform_peaks):
                px = i * dx
                amp = float(val) * max_amp
                top_points.append(QPointF(px, mid_y - amp))
                bot_points.append(QPointF(px, mid_y + amp))

            # Combine into closed polygon
            poly = QPolygonF(top_points + list(reversed(bot_points)))
            wave_grad = QLinearGradient(0, 0, 0, h)
            wave_grad.setColorAt(0.0, QColor(56, 189, 248, 180))   # Cyan top
            wave_grad.setColorAt(0.5, QColor(14, 165, 233, 240))   # Bright middle
            wave_grad.setColorAt(1.0, QColor(2, 132, 199, 180))   # Deep cyan bot

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(wave_grad))
            painter.drawPolygon(poly)

        # 3. Center line
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
        painter.drawLine(0, int(mid_y), int(w), int(mid_y))

        # 4. Draw Loop Region (if active)
        if self.is_looping and self.loop_start is not None and self.loop_end is not None:
            lx1 = (self.loop_start / self.total_duration) * w
            lx2 = (self.loop_end / self.total_duration) * w
            painter.fillRect(QRectF(lx1, 0, lx2 - lx1, h), QColor(245, 158, 11, 40))
            painter.setPen(QPen(QColor("#f59e0b"), 2, Qt.PenStyle.DashLine))
            painter.drawLine(int(lx1), 0, int(lx1), int(h))
            painter.drawLine(int(lx2), 0, int(lx2), int(h))

        # 5. Playhead Laser (Golden beam with glowing diamond head)
        play_x = (self.current_time / self.total_duration) * w

        # Laser beam
        painter.setPen(QPen(QColor("#f59e0b"), 2.0))
        painter.drawLine(int(play_x), 0, int(play_x), int(h))

        # Top diamond marker
        diamond = QPolygonF([
            QPointF(play_x - 6, 0),
            QPointF(play_x + 6, 0),
            QPointF(play_x, 9),
        ])
        painter.setPen(QPen(QColor("#ffffff"), 1.0))
        painter.setBrush(QBrush(QColor("#f59e0b")))
        painter.drawPolygon(diamond)
