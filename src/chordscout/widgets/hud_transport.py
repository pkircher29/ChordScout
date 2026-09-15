"""Heads-Up Display (HUD) with live active chord card, next-chord countdown, and transport bar."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from chordscout.models import format_timestamp


class HudTransportWidget(QWidget):
    """Transport HUD containing play/pause, time scrubber, speed, loop, and large active chord readout."""

    play_toggled = Signal()
    prev_chord_requested = Signal()
    next_chord_requested = Signal()
    speed_changed = Signal(float)
    loop_toggled = Signal(bool)
    volume_changed = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Top Row: HUD Info Badges
        hud_row = QHBoxLayout()
        hud_row.setSpacing(12)

        # 1. Current Chord Card (Huge & Glowing)
        self.card_current = QFrame()
        self.card_current.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #182236, stop:1 #101624);
                border: 2px solid #38bdf8;
                border-radius: 10px;
                padding: 4px 16px;
            }
        """)
        c_layout = QVBoxLayout(self.card_current)
        c_layout.setContentsMargins(8, 4, 8, 4)
        c_layout.setSpacing(0)
        lbl_cur_title = QLabel("CURRENT CHORD")
        lbl_cur_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        self.lbl_active_chord = QLabel("—")
        self.lbl_active_chord.setStyleSheet("color: #38bdf8; font-size: 28px; font-weight: 900;")
        c_layout.addWidget(lbl_cur_title)
        c_layout.addWidget(self.lbl_active_chord)
        hud_row.addWidget(self.card_current)

        # 2. Next Chord Card
        self.card_next = QFrame()
        self.card_next.setStyleSheet("""
            QFrame {
                background: #131722;
                border: 1px solid #1e2638;
                border-radius: 10px;
                padding: 4px 14px;
            }
        """)
        n_layout = QVBoxLayout(self.card_next)
        n_layout.setContentsMargins(8, 4, 8, 4)
        n_layout.setSpacing(0)
        lbl_next_title = QLabel("UPCOMING CHORD")
        lbl_next_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 800; letter-spacing: 1px;")
        self.lbl_next_chord = QLabel("—")
        self.lbl_next_chord.setStyleSheet("color: #cbd5e1; font-size: 18px; font-weight: bold;")
        self.lbl_next_countdown = QLabel("End of song")
        self.lbl_next_countdown.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 600;")
        n_layout.addWidget(lbl_next_title)
        n_layout.addWidget(self.lbl_next_chord)
        n_layout.addWidget(self.lbl_next_countdown)
        hud_row.addWidget(self.card_next)

        # 3. Key & Tempo Badges
        self.card_meta = QFrame()
        self.card_meta.setStyleSheet("""
            QFrame {
                background: #131722;
                border: 1px solid #1e2638;
                border-radius: 10px;
                padding: 4px 14px;
            }
        """)
        m_layout = QVBoxLayout(self.card_meta)
        m_layout.setContentsMargins(8, 4, 8, 4)
        m_layout.setSpacing(2)
        self.lbl_key_badge = QLabel("Key: —")
        self.lbl_key_badge.setStyleSheet("color: #a855f7; font-weight: bold; font-size: 13px;")
        self.lbl_tempo_badge = QLabel("Tempo: — BPM")
        self.lbl_tempo_badge.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px;")
        m_layout.addWidget(self.lbl_key_badge)
        m_layout.addWidget(self.lbl_tempo_badge)
        hud_row.addWidget(self.card_meta)

        hud_row.addStretch()

        # Practice Speed selector (0.75x, 0.9x, 1.0x, 1.25x)
        speed_box = QHBoxLayout()
        speed_lbl = QLabel("Speed:")
        speed_lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 11px;")
        speed_box.addWidget(speed_lbl)

        self.speed_group = QButtonGroup(self)
        self.speed_btns = {}
        for spd_val, spd_text in [(0.75, "0.75x"), (0.9, "0.9x"), (1.0, "1.0x"), (1.25, "1.25x")]:
            btn = QPushButton(spd_text)
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a202f;
                    border: 1px solid #28334a;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background-color: #0284c7;
                    border-color: #38bdf8;
                    color: #ffffff;
                }
            """)
            if spd_val == 1.0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=spd_val: self.speed_changed.emit(s))
            self.speed_group.addButton(btn)
            self.speed_btns[spd_val] = btn
            speed_box.addWidget(btn)
        hud_row.addLayout(speed_box)

        main_layout.addLayout(hud_row)

        # Bottom Row: Transport Controls (Play, Prev, Next, Loop, Time, Volume)
        trans_row = QHBoxLayout()
        trans_row.setSpacing(10)

        # Prev / Next Chord buttons
        self.btn_prev = QPushButton("⏮ Prev")
        self.btn_prev.setFixedHeight(34)
        self.btn_prev.clicked.connect(self.prev_chord_requested)

        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setObjectName("playBtn")
        self.btn_play.clicked.connect(self.play_toggled)

        self.btn_next = QPushButton("Next ⏭")
        self.btn_next.setFixedHeight(34)
        self.btn_next.clicked.connect(self.next_chord_requested)

        # Loop Toggle
        self.btn_loop = QPushButton("🔁 Loop Chord")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setFixedHeight(34)
        self.btn_loop.setToolTip("Loop the currently active chord segment for practice")
        self.btn_loop.clicked.connect(lambda c: self.loop_toggled.emit(c))

        trans_row.addWidget(self.btn_prev)
        trans_row.addWidget(self.btn_play)
        trans_row.addWidget(self.btn_next)
        trans_row.addWidget(self.btn_loop)

        # Timecode display
        self.lbl_timecode = QLabel("00:00.0 / 00:00.0")
        self.lbl_timecode.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #f8fafc;")
        trans_row.addWidget(self.lbl_timecode)

        trans_row.addStretch()

        # Volume slider
        lbl_vol = QLabel("🔊")
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(85)
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.valueChanged.connect(lambda v: self.volume_changed.emit(v / 100.0))

        trans_row.addWidget(lbl_vol)
        trans_row.addWidget(self.vol_slider)

        main_layout.addLayout(trans_row)

    def update_active_chord(
        self,
        current_chord: str,
        next_chord: Optional[str] = None,
        countdown_sec: Optional[float] = None,
    ) -> None:
        self.lbl_active_chord.setText(current_chord if current_chord else "—")
        if next_chord and next_chord != "N":
            self.lbl_next_chord.setText(next_chord)
            if countdown_sec is not None and countdown_sec > 0:
                self.lbl_next_countdown.setText(f"in {countdown_sec:0.1f}s")
            else:
                self.lbl_next_countdown.setText("Next")
        else:
            self.lbl_next_chord.setText("—")
            self.lbl_next_countdown.setText("End of track")

    def update_metadata(self, key_estimate: Optional[str], tempo_bpm: Optional[float]) -> None:
        self.lbl_key_badge.setText(f"Key: {key_estimate or 'N/A'}")
        bpm_text = f"{int(tempo_bpm)} BPM" if tempo_bpm else "— BPM"
        self.lbl_tempo_badge.setText(f"Tempo: {bpm_text}")

    def update_timecode(self, current_sec: float, total_sec: float) -> None:
        cur = format_timestamp(current_sec, include_ms=True)
        tot = format_timestamp(total_sec, include_ms=True)
        self.lbl_timecode.setText(f"{cur} / {tot}")

    def set_playing_state(self, is_playing: bool) -> None:
        if is_playing:
            self.btn_play.setText("⏸ PAUSE")
        else:
            self.btn_play.setText("▶ PLAY")
