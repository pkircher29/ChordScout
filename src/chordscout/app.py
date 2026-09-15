"""Desktop GUI Application for ChordScout with drag-and-drop, playback, and guitar diagrams."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QThread, QTime, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QKeySequence,
    QPainter,
    QPen,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chordscout.analyzer import analyze_chords
from chordscout.audio import is_supported_audio_file, load_audio
from chordscout.export import (
    export_chordpro,
    export_csv,
    export_plain_text,
    load_project,
    save_project,
)
from chordscout.guitar import GUITAR_CHORDS, GuitarChord, get_guitar_chord
from chordscout.models import AnalysisMetadata, AnalysisResult, ChordSegment, format_timestamp


# --- Custom Widgets ---


class GuitarFretboardWidget(QWidget):
    """Visual widget displaying guitar chord diagrams (nut, frets, strings, finger dots)."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.chord: Optional[GuitarChord] = None
        self.chord_name: str = "None"
        self.setMinimumSize(170, 220)

    def set_chord(self, chord_name: str) -> None:
        self.chord_name = chord_name
        self.chord = get_guitar_chord(chord_name)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#1e1e24"))

        # Title / Chord name
        painter.setPen(QColor("#f0f0f5"))
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.drawText(QRectF(0, 8, w, 30), Qt.AlignmentFlag.AlignCenter, self.chord_name)

        if not self.chord or self.chord_name in ("N", "None", ""):
            info_font = QFont("Segoe UI", 9)
            painter.setFont(info_font)
            painter.setPen(QColor("#888899"))
            text = "No guitar voicing" if self.chord_name == "N" else "Select a chord"
            painter.drawText(QRectF(0, 50, w, 100), Qt.AlignmentFlag.AlignCenter, text)
            return

        # Fretboard geometry
        margin_x = 35
        margin_y = 55
        grid_w = w - (margin_x * 2)
        grid_h = h - margin_y - 25
        num_frets = 4
        num_strings = 6
        dx = grid_w / (num_strings - 1)
        dy = grid_h / num_frets

        # Base fret indication
        base_fret = self.chord.base_fret
        fret_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(fret_font)
        painter.setPen(QColor("#ffaa44"))
        if base_fret > 1:
            painter.drawText(margin_x - 26, int(margin_y + dy * 0.75), f"{base_fret}fr")

        # Nut or normal fret line
        nut_pen = QPen(QColor("#ffffff" if base_fret == 1 else "#777788"))
        nut_pen.setWidth(4 if base_fret == 1 else 2)
        painter.setPen(nut_pen)
        painter.drawLine(int(margin_x), int(margin_y), int(margin_x + grid_w), int(margin_y))

        # Fret wires (horizontal)
        fret_pen = QPen(QColor("#555566"), 1.5)
        painter.setPen(fret_pen)
        for i in range(1, num_frets + 1):
            y = margin_y + (i * dy)
            painter.drawLine(int(margin_x), int(y), int(margin_x + grid_w), int(y))

        # Strings (vertical) - low E to high e
        for s in range(num_strings):
            x = margin_x + (s * dx)
            # Thicker lines for bass strings
            string_width = 3.0 - (s * 0.35)
            s_pen = QPen(QColor("#a0a0b5"), max(1.0, string_width))
            painter.setPen(s_pen)
            painter.drawLine(int(x), int(margin_y), int(x), int(margin_y + grid_h))

        # Markers (open 'o', muted 'x', and finger dots)
        for s, fret in enumerate(self.chord.frets):
            x = margin_x + (s * dx)
            if fret == -1:
                # Muted 'x' above nut
                painter.setPen(QPen(QColor("#ee5555"), 2))
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                painter.drawText(
                    QRectF(x - 8, margin_y - 18, 16, 16),
                    Qt.AlignmentFlag.AlignCenter,
                    "x",
                )
            elif fret == 0:
                # Open 'o' above nut
                painter.setPen(QPen(QColor("#44cc66"), 2))
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                painter.drawText(
                    QRectF(x - 8, margin_y - 18, 16, 16),
                    Qt.AlignmentFlag.AlignCenter,
                    "o",
                )
            else:
                # Fret dot
                rel_fret = fret - base_fret + 1
                if 1 <= rel_fret <= num_frets:
                    dot_y = margin_y + ((rel_fret - 0.5) * dy)
                    dot_radius = 8.0
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(QColor("#3399ff")))
                    painter.drawEllipse(QPointF(x, dot_y), dot_radius, dot_radius)

                    # Finger number inside dot
                    finger = self.chord.fingers[s] if s < len(self.chord.fingers) else 0
                    if finger > 0:
                        painter.setPen(QColor("#ffffff"))
                        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                        painter.drawText(
                            QRectF(x - 8, dot_y - 8, 16, 16),
                            Qt.AlignmentFlag.AlignCenter,
                            str(finger),
                        )


class ChordTimelineWidget(QWidget):
    """Horizontal chord track timeline showing segments and playback cursor."""

    seek_requested = Signal(float)  # Emits target seconds when user clicks

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.segments: List[ChordSegment] = []
        self.total_duration: float = 1.0
        self.current_time: float = 0.0
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_data(self, segments: List[ChordSegment], duration: float) -> None:
        self.segments = segments
        self.total_duration = max(0.1, duration)
        self.update()

    def set_current_time(self, time_sec: float) -> None:
        self.current_time = max(0.0, min(time_sec, self.total_duration))
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.total_duration <= 0 or self.width() <= 0:
            return
        frac = event.position().x() / self.width()
        target_sec = max(0.0, min(self.total_duration, frac * self.total_duration))
        self.seek_requested.emit(target_sec)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor("#181820"))

        if not self.segments or self.total_duration <= 0:
            painter.setPen(QColor("#555566"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Timeline will appear here")
            return

        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)

        # Palette for chords
        palette = [
            QColor("#2d4059"),
            QColor("#34495e"),
            QColor("#16a085"),
            QColor("#27ae60"),
            QColor("#2980b9"),
            QColor("#8e44ad"),
            QColor("#d35400"),
            QColor("#c0392b"),
        ]

        for i, seg in enumerate(self.segments):
            x1 = (seg.start_time / self.total_duration) * w
            x2 = (seg.end_time / self.total_duration) * w
            seg_w = max(1.0, x2 - x1)

            color = QColor("#222228") if seg.chord == "N" else palette[hash(seg.chord) % len(palette)]
            # Highlight if currently active
            if seg.start_time <= self.current_time < seg.end_time:
                color = color.lighter(140)

            painter.fillRect(QRectF(x1, 2, seg_w, h - 4), color)
            painter.setPen(QColor("#101015"))
            painter.drawRect(QRectF(x1, 2, seg_w, h - 4))

            # Chord label inside block if wide enough
            if seg_w > 20:
                painter.setPen(QColor("#ffffff"))
                painter.drawText(
                    QRectF(x1, 2, seg_w, h - 4),
                    Qt.AlignmentFlag.AlignCenter,
                    seg.chord,
                )

        # Playhead cursor
        cursor_x = (self.current_time / self.total_duration) * w
        painter.setPen(QPen(QColor("#ffdd44"), 2))
        painter.drawLine(int(cursor_x), 0, int(cursor_x), h)


# --- Background Worker Thread ---


class AnalysisWorker(QThread):
    """Background worker for non-blocking chord recognition."""

    progress_updated = Signal(float, str)
    finished_success = Signal(object, object)
    finished_error = Signal(str)

    def __init__(self, file_path: Path, include_sevenths: bool = False):
        super().__init__()
        self.file_path = file_path
        self.include_sevenths = include_sevenths

    def run(self) -> None:
        try:
            self.progress_updated.emit(0.02, "Loading audio file...")
            audio, sr, duration = load_audio(self.file_path)

            def cb(p: float, msg: str) -> None:
                self.progress_updated.emit(p, msg)

            segments, meta_dict = analyze_chords(
                audio,
                sr=sr,
                include_sevenths=self.include_sevenths,
                progress_callback=cb,
            )

            metadata = AnalysisMetadata(
                file_path=str(self.file_path.resolve()),
                file_name=self.file_path.name,
                duration=duration,
                sample_rate=sr,
                tempo_bpm=meta_dict.get("tempo_bpm"),
                key_estimate=meta_dict.get("key_estimate"),
                tuning_offset_cents=meta_dict.get("tuning_offset_cents", 0.0),
            )

            result = AnalysisResult(metadata=metadata, segments=segments)
            self.finished_success.emit(result, audio)
        except Exception as err:
            self.finished_error.emit(str(err))


# --- Main Application Window ---


class ChordScoutApp(QMainWindow):
    """Main window of the ChordScout application."""

    def __init__(self, initial_file: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("ChordScout - Guitar Chord Analyzer")
        self.resize(980, 680)
        self.setAcceptDrops(True)

        self.current_result: Optional[AnalysisResult] = None
        self.audio_worker: Optional[AnalysisWorker] = None
        self.audio_data: Optional[object] = None

        # Media Player setup
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

        self._setup_ui()
        self._apply_dark_theme()

        if initial_file and os.path.exists(initial_file):
            self.start_analysis(Path(initial_file))

    def _setup_ui(self) -> None:
        # Central container
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header toolbar / actions
        top_bar = QHBoxLayout()
        self.btn_open = QPushButton("Open Song File...")
        self.btn_open.setFixedHeight(34)
        self.btn_open.clicked.connect(self.on_open_file_clicked)

        self.chk_sevenths = QCheckBox("Detect 7th Chords")
        self.chk_sevenths.setToolTip("Include dominant 7th and minor 7th templates")

        self.btn_export = QPushButton("Export Chords ▼")
        self.btn_export.setFixedHeight(34)
        export_menu = QMenu(self)
        export_menu.addAction("Export Plain Text (.txt)...", self.export_text_dialog)
        export_menu.addAction("Export ChordPro (.cho)...", self.export_chordpro_dialog)
        export_menu.addAction("Export CSV (.csv)...", self.export_csv_dialog)
        export_menu.addSeparator()
        export_menu.addAction("Save Sidecar Project (.chordscout.json)...", self.save_project_dialog)
        export_menu.addAction("Load Sidecar Project...", self.load_project_dialog)
        export_menu.addSeparator()
        export_menu.addAction("Copy Chords to Clipboard", self.copy_to_clipboard)
        self.btn_export.setMenu(export_menu)

        top_bar.addWidget(self.btn_open)
        top_bar.addWidget(self.chk_sevenths)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_export)
        main_layout.addLayout(top_bar)

        # Drop Banner / Info Card
        self.banner = QFrame()
        self.banner.setFrameShape(QFrame.Shape.StyledPanel)
        banner_layout = QHBoxLayout(self.banner)
        self.lbl_file_info = QLabel("Drop an MP3, WAV, FLAC, or M4A file anywhere into this window.")
        self.lbl_file_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #70a0ff;")
        self.lbl_meta_info = QLabel("")
        self.lbl_meta_info.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        banner_layout.addWidget(self.lbl_file_info)
        banner_layout.addStretch()
        banner_layout.addWidget(self.lbl_meta_info)
        main_layout.addWidget(self.banner)

        # Progress bar (hidden until active)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Timeline Bar
        self.timeline = ChordTimelineWidget(self)
        self.timeline.seek_requested.connect(self.seek_audio)
        main_layout.addWidget(self.timeline)

        # Middle splitter: Left = Chord Table, Right = Guitar Chord Diagram
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Table of chord segments
        table_container = QWidget()
        t_layout = QVBoxLayout(table_container)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(6)

        table_header = QHBoxLayout()
        t_lbl = QLabel("Chord Progression (Time-Aligned)")
        t_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #dddddd;")
        self.lbl_current_badge = QLabel("Current: -")
        self.lbl_current_badge.setStyleSheet(
            "background-color: #334466; color: #ffffff; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
        )
        table_header.addWidget(t_lbl)
        table_header.addStretch()
        table_header.addWidget(self.lbl_current_badge)
        t_layout.addLayout(table_header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time Range", "Duration", "Chord", "Confidence"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self.on_table_item_double_clicked)
        t_layout.addWidget(self.table)

        # Table buttons: Split, Merge, Edit
        edit_bar = QHBoxLayout()
        self.btn_edit_chord = QPushButton("Change Chord")
        self.btn_edit_chord.clicked.connect(self.edit_selected_chord)
        self.btn_split = QPushButton("Split Segment")
        self.btn_split.clicked.connect(self.split_selected_segment)
        self.btn_merge = QPushButton("Merge with Next")
        self.btn_merge.clicked.connect(self.merge_with_next_segment)
        self.btn_delete = QPushButton("Set to Silence (N)")
        self.btn_delete.clicked.connect(self.set_selected_to_silence)

        edit_bar.addWidget(self.btn_edit_chord)
        edit_bar.addWidget(self.btn_split)
        edit_bar.addWidget(self.btn_merge)
        edit_bar.addWidget(self.btn_delete)
        t_layout.addLayout(edit_bar)

        splitter.addWidget(table_container)

        # Right: Guitar Fretboard Diagram Box
        right_container = QWidget()
        r_layout = QVBoxLayout(right_container)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(6)

        r_lbl = QLabel("Guitar Voicing (Standard Tuning)")
        r_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #dddddd;")
        r_layout.addWidget(r_lbl)

        self.guitar_widget = GuitarFretboardWidget(self)
        r_layout.addWidget(self.guitar_widget)

        # Help / Hint box
        hint_box = QFrame()
        hint_box.setStyleSheet("background-color: #1a1a24; border-radius: 6px; padding: 6px;")
        h_layout = QVBoxLayout(hint_box)
        lbl_hint_title = QLabel("💡 ChordScout Tips:")
        lbl_hint_title.setStyleSheet("font-weight: bold; color: #ffa726; font-size: 11px;")
        lbl_hint_body = QLabel(
            "• Chords reflect algorithmic analysis.\n"
            "• Double-click any chord to adjust name.\n"
            "• Click the timeline to seek playback.\n"
            "• Export to ChordPro, Text, or CSV anytime."
        )
        lbl_hint_body.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        h_layout.addWidget(lbl_hint_title)
        h_layout.addWidget(lbl_hint_body)
        r_layout.addWidget(hint_box)
        r_layout.addStretch()

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)
        main_layout.addWidget(splitter)

        # Audio Playback Control Bar
        play_bar = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setFixedWidth(80)
        self.btn_play.clicked.connect(self.toggle_playback)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self.on_slider_moved)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFixedWidth(95)

        play_bar.addWidget(self.btn_play)
        play_bar.addWidget(self.slider)
        play_bar.addWidget(self.lbl_time)
        main_layout.addLayout(play_bar)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Drop an MP3 here to begin.")

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121218;
            }
            QWidget {
                color: #e0e0ea;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame {
                background-color: #1c1c26;
                border: 1px solid #2d2d3d;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #2b2b3d;
                border: 1px solid #404058;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d56;
                border-color: #555577;
            }
            QPushButton:pressed {
                background-color: #1e1e2d;
            }
            QTableWidget {
                background-color: #181822;
                gridline-color: #262636;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                selection-background-color: #2a4365;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #20202e;
                color: #b0b0c5;
                padding: 5px;
                border: none;
                border-right: 1px solid #2d2d3d;
                border-bottom: 1px solid #2d2d3d;
                font-weight: bold;
            }
            QProgressBar {
                background-color: #1c1c26;
                border: 1px solid #333348;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #252535;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QMenu {
                background-color: #20202c;
                border: 1px solid #3d3d52;
                color: #ffffff;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
            }
            QCheckBox {
                color: #c0c0d5;
            }
        """)

    # --- Drag and Drop Handling ---

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(is_supported_audio_file(u.toLocalFile()) for u in urls):
                event.acceptProposedAction()
                self.banner.setStyleSheet("background-color: #223355; border: 2px dashed #4488ff;")
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.banner.setStyleSheet("")

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self.banner.setStyleSheet("")
        urls = event.mimeData().urls()
        for u in urls:
            path = Path(u.toLocalFile())
            if is_supported_audio_file(path):
                self.start_analysis(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # --- Analysis Pipeline ---

    def on_open_file_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Song Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;All Files (*)",
        )
        if file_path:
            self.start_analysis(Path(file_path))

    def start_analysis(self, file_path: Path) -> None:
        self.player.stop()
        self.lbl_file_info.setText(f"Analyzing: {file_path.name}")
        self.lbl_meta_info.setText("Running chord recognition...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.btn_open.setEnabled(False)

        # Set media source for playback
        self.player.setSource(QUrl.fromLocalFile(str(file_path.resolve())))

        # Run in background thread
        include_7ths = self.chk_sevenths.isChecked()
        self.audio_worker = AnalysisWorker(file_path, include_sevenths=include_7ths)
        self.audio_worker.progress_updated.connect(self.on_progress_updated)
        self.audio_worker.finished_success.connect(self.on_analysis_success)
        self.audio_worker.finished_error.connect(self.on_analysis_error)
        self.audio_worker.start()

    def on_progress_updated(self, progress: float, message: str) -> None:
        self.progress_bar.setValue(int(progress * 100))
        self.progress_bar.setFormat(f"{int(progress * 100)}% - {message}")
        self.status_bar.showMessage(message)

    def on_analysis_success(self, result: AnalysisResult, audio: object) -> None:
        self.btn_open.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.current_result = result
        self.audio_data = audio

        meta = result.metadata
        dur_str = format_timestamp(meta.duration)
        key_str = f"Key: {meta.key_estimate}" if meta.key_estimate else ""
        bpm_str = f"{int(meta.tempo_bpm)} BPM" if meta.tempo_bpm else ""
        meta_summary = "  |  ".join(filter(bool, [dur_str, key_str, bpm_str]))
        self.lbl_file_info.setText(meta.file_name)
        self.lbl_meta_info.setText(meta_summary)

        # Update Timeline & Table
        self.timeline.set_data(result.segments, meta.duration)
        self.populate_table()

        self.status_bar.showMessage(
            f"Detected {len(result.segments)} chord segments. Double-click to edit."
        )

        # Select first chord if exists
        if result.segments:
            self.table.selectRow(0)

    def on_analysis_error(self, err_msg: str) -> None:
        self.btn_open.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_file_info.setText("Analysis failed.")
        self.lbl_meta_info.setText("")
        QMessageBox.critical(self, "Analysis Error", f"Could not analyze file:\n\n{err_msg}")
        self.status_bar.showMessage("Error during analysis.")

    # --- Table & Timeline Display ---

    def populate_table(self) -> None:
        if not self.current_result:
            return

        self.table.setRowCount(0)
        self.table.setRowCount(len(self.current_result.segments))

        for row, seg in enumerate(self.current_result.segments):
            # Time Range
            t_item = QTableWidgetItem(f"{seg.formatted_start} - {seg.formatted_end}")
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Duration
            d_item = QTableWidgetItem(f"{seg.duration:0.1f}s")
            d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Chord
            c_label = seg.chord + (" *" if seg.is_user_edited else "")
            c_item = QTableWidgetItem(c_label)
            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            c_item.setFont(font)
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Confidence
            conf_percent = int(seg.confidence * 100) if seg.chord != "N" else 100
            conf_item = QTableWidgetItem(f"{conf_percent}%")
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, t_item)
            self.table.setItem(row, 1, d_item)
            self.table.setItem(row, 2, c_item)
            self.table.setItem(row, 3, conf_item)

    def on_table_selection_changed(self) -> None:
        row = self.table.currentRow()
        if self.current_result and 0 <= row < len(self.current_result.segments):
            seg = self.current_result.segments[row]
            self.guitar_widget.set_chord(seg.chord)

    def on_table_item_double_clicked(self, item: QTableWidgetItem) -> None:
        self.edit_selected_chord()

    # --- Editing Chords ---

    def edit_selected_chord(self) -> None:
        row = self.table.currentRow()
        if not self.current_result or row < 0 or row >= len(self.current_result.segments):
            return

        seg = self.current_result.segments[row]
        common_chords = list(GUITAR_CHORDS.keys())
        if "N" not in common_chords:
            common_chords.insert(0, "N")

        current_idx = common_chords.index(seg.chord) if seg.chord in common_chords else 0

        new_chord, ok = QInputDialog.getItem(
            self,
            "Edit Chord",
            f"Select or type new chord for [{seg.formatted_start} - {seg.formatted_end}]:",
            common_chords,
            current_idx,
            editable=True,
        )
        if ok and new_chord:
            seg.chord = new_chord.strip()
            seg.is_user_edited = True
            self.populate_table()
            self.table.selectRow(row)
            self.timeline.update()
            self.guitar_widget.set_chord(seg.chord)

    def split_selected_segment(self) -> None:
        row = self.table.currentRow()
        if not self.current_result or row < 0 or row >= len(self.current_result.segments):
            return

        seg = self.current_result.segments[row]
        mid = (seg.start_time + seg.end_time) / 2.0
        if seg.duration < 0.6:
            QMessageBox.information(self, "Split", "Segment is too short to split further.")
            return

        seg1 = ChordSegment(seg.start_time, mid, seg.chord, seg.confidence, is_user_edited=True)
        seg2 = ChordSegment(mid, seg.end_time, seg.chord, seg.confidence, is_user_edited=True)

        self.current_result.segments[row:row + 1] = [seg1, seg2]
        self.populate_table()
        self.table.selectRow(row)
        self.timeline.set_data(self.current_result.segments, self.current_result.metadata.duration)

    def merge_with_next_segment(self) -> None:
        row = self.table.currentRow()
        if not self.current_result or row < 0 or row >= len(self.current_result.segments) - 1:
            return

        seg1 = self.current_result.segments[row]
        seg2 = self.current_result.segments[row + 1]
        seg1.end_time = seg2.end_time
        seg1.is_user_edited = True

        del self.current_result.segments[row + 1]
        self.populate_table()
        self.table.selectRow(row)
        self.timeline.set_data(self.current_result.segments, self.current_result.metadata.duration)

    def set_selected_to_silence(self) -> None:
        row = self.table.currentRow()
        if not self.current_result or row < 0 or row >= len(self.current_result.segments):
            return
        seg = self.current_result.segments[row]
        seg.chord = "N"
        seg.is_user_edited = True
        self.populate_table()
        self.table.selectRow(row)
        self.timeline.update()
        self.guitar_widget.set_chord("N")

    def show_table_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        self.table.selectRow(row)

        menu = QMenu(self)
        menu.addAction("Change Chord...", self.edit_selected_chord)
        menu.addAction("Split Segment at Midpoint", self.split_selected_segment)
        menu.addAction("Merge with Next Segment", self.merge_with_next_segment)
        menu.addAction("Set to Silence (N)", self.set_selected_to_silence)
        menu.addSeparator()
        menu.addAction("Play from this Segment", lambda: self.play_from_row(row))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def play_from_row(self, row: int) -> None:
        if self.current_result and 0 <= row < len(self.current_result.segments):
            seg = self.current_result.segments[row]
            self.seek_audio(seg.start_time)
            self.player.play()

    # --- Audio Playback & Synchronization ---

    def toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸ Pause")
        else:
            self.btn_play.setText("▶ Play")

    def on_player_position_changed(self, pos_ms: int) -> None:
        pos_sec = pos_ms / 1000.0
        dur_ms = self.player.duration()
        dur_sec = dur_ms / 1000.0 if dur_ms > 0 else (self.current_result.metadata.duration if self.current_result else 1.0)

        self.timeline.set_current_time(pos_sec)

        # Update slider without triggering move signal
        if dur_sec > 0:
            val = int((pos_sec / dur_sec) * 1000)
            self.slider.blockSignals(True)
            self.slider.setValue(val)
            self.slider.blockSignals(False)

        # Time label
        cur_str = format_timestamp(pos_sec)
        tot_str = format_timestamp(dur_sec)
        self.lbl_time.setText(f"{cur_str} / {tot_str}")

        # Active chord update
        if self.current_result:
            seg = self.current_result.get_chord_at_time(pos_sec)
            if seg:
                self.lbl_current_badge.setText(f"Current: {seg.chord}")
                self.guitar_widget.set_chord(seg.chord)

    def on_slider_moved(self, val: int) -> None:
        dur_ms = self.player.duration()
        if dur_ms > 0:
            target_ms = int((val / 1000.0) * dur_ms)
            self.player.setPosition(target_ms)

    def seek_audio(self, target_sec: float) -> None:
        target_ms = int(target_sec * 1000)
        self.player.setPosition(target_ms)

    # --- Export Dialogs ---

    def check_has_result(self) -> bool:
        if not self.current_result or not self.current_result.segments:
            QMessageBox.warning(self, "No Song", "Please drop or open an audio file first.")
            return False
        return True

    def export_text_dialog(self) -> None:
        if not self.check_has_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plain Text Chord Chart", "chords.txt", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            text = export_plain_text(self.current_result)
            Path(path).write_text(text, encoding="utf-8")
            self.status_bar.showMessage(f"Saved text chart: {Path(path).name}")

    def export_chordpro_dialog(self) -> None:
        if not self.check_has_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save ChordPro File", "song.cho", "ChordPro Files (*.cho *.chordpro);;All Files (*)"
        )
        if path:
            cho = export_chordpro(self.current_result)
            Path(path).write_text(cho, encoding="utf-8")
            self.status_bar.showMessage(f"Saved ChordPro: {Path(path).name}")

    def export_csv_dialog(self) -> None:
        if not self.check_has_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Spreadsheet", "chords.csv", "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            export_csv(self.current_result, Path(path))
            self.status_bar.showMessage(f"Saved CSV: {Path(path).name}")

    def save_project_dialog(self) -> None:
        if not self.check_has_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project Sidecar",
            f"{Path(self.current_result.metadata.file_name).stem}.chordscout.json",
            "ChordScout Project (*.chordscout.json);;JSON Files (*.json)",
        )
        if path:
            save_project(self.current_result, Path(path))
            self.status_bar.showMessage(f"Project saved: {Path(path).name}")

    def load_project_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project Sidecar",
            "",
            "ChordScout Project (*.chordscout.json *.json);;All Files (*)",
        )
        if path:
            try:
                res = load_project(Path(path))
                self.current_result = res
                self.lbl_file_info.setText(res.metadata.file_name)
                self.lbl_meta_info.setText(
                    f"{format_timestamp(res.metadata.duration)} | Key: {res.metadata.key_estimate or 'N/A'}"
                )
                self.timeline.set_data(res.segments, res.metadata.duration)
                self.populate_table()
                # If audio file exists at original path, load it
                if os.path.exists(res.metadata.file_path):
                    self.player.setSource(QUrl.fromLocalFile(res.metadata.file_path))
                self.status_bar.showMessage(f"Loaded project: {Path(path).name}")
            except Exception as err:
                QMessageBox.critical(self, "Load Error", f"Failed to load project:\n\n{err}")

    def copy_to_clipboard(self) -> None:
        if not self.check_has_result():
            return
        text = export_plain_text(self.current_result)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.status_bar.showMessage("Chord chart copied to clipboard!")


def main(initial_file: Optional[str] = None) -> None:
    """Entrypoint for the ChordScout desktop GUI."""
    app = QApplication(sys.argv)
    window = ChordScoutApp(initial_file=initial_file)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
