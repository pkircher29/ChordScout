"""ChordScout - Modern Studio Desktop GUI Application for Guitar Chord Recognition."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QThread, QTime, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QIcon,
    QKeySequence,
    QShortcut,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
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
from chordscout.guitar import GUITAR_CHORDS, get_guitar_chord
from chordscout.models import AnalysisMetadata, AnalysisResult, ChordSegment, format_timestamp
from chordscout.theme import STUDIO_DARK_STYLESHEET
from chordscout.transposer import transpose_chord_name, transpose_segments
from chordscout.widgets.chord_grid_view import ChordGridView
from chordscout.widgets.drop_overlay import DropOverlayWidget
from chordscout.widgets.fretboard_widget import GuitarFretboardWidget
from chordscout.widgets.hud_transport import HudTransportWidget
from chordscout.widgets.waveform_timeline import WaveformTimelineWidget


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
            self.progress_updated.emit(0.04, "Reading & normalizing audio...")
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
    """Studio-grade desktop interface for ChordScout."""

    def __init__(self, initial_file: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("ChordScout 🎸 — Guitar Chord Analyzer")
        self.resize(1120, 780)
        self.setMinimumSize(880, 600)
        self.setAcceptDrops(True)

        self.current_result: Optional[AnalysisResult] = None
        self.base_segments: List[ChordSegment] = []  # Original untransposed segments
        self.audio_worker: Optional[AnalysisWorker] = None
        self.audio_data: Optional[np.ndarray] = None
        self.transposition_semitones: int = 0
        self.is_looping_chord: bool = False

        # Media Player setup
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

        self._setup_ui()
        self.setStyleSheet(STUDIO_DARK_STYLESHEET)
        self._setup_shortcuts()

        # Window Icon
        for candidate in [
            Path(__file__).resolve().parent.parent.parent / "assets" / "chordscout.ico",
            Path(sys.prefix) / "assets" / "chordscout.ico",
            Path(sys.executable).parent / "assets" / "chordscout.ico",
        ]:
            if candidate.exists():
                self.setWindowIcon(QIcon(str(candidate)))
                break

        if initial_file and os.path.exists(initial_file):
            self.start_analysis(Path(initial_file))

    def _setup_shortcuts(self) -> None:
        # Spacebar for Play/Pause
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.toggle_playback)
        # S for Strum current chord
        QShortcut(QKeySequence(Qt.Key.Key_S), self, self.strum_current_chord)
        # Ctrl+O for Open file
        QShortcut(QKeySequence(Qt.Key.Key_O | Qt.KeyboardModifier.ControlModifier), self, self.on_open_file_clicked)
        # Ctrl+C for Copy
        QShortcut(QKeySequence(Qt.Key.Key_C | Qt.KeyboardModifier.ControlModifier), self, self.copy_to_clipboard)

    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # 1. Top Command Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.btn_open = QPushButton("📁 Open Song...")
        self.btn_open.setFixedHeight(34)
        self.btn_open.clicked.connect(self.on_open_file_clicked)

        self.btn_demo = QPushButton("⚡ Demo Song")
        self.btn_demo.setFixedHeight(34)
        self.btn_demo.setToolTip("Analyze the built-in C-G-Am-F demo track")
        self.btn_demo.clicked.connect(self.load_demo_song)

        # Capo Selector
        capo_lbl = QLabel("Capo:")
        capo_lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.combo_capo = QComboBox()
        self.combo_capo.setFixedHeight(32)
        self.combo_capo.addItems(["No Capo"] + [f"Capo {i}" for i in range(1, 8)])
        self.combo_capo.currentIndexChanged.connect(self.on_capo_changed)

        # Transpose Buttons
        trans_lbl = QLabel("Transpose:")
        trans_lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.btn_trans_down = QPushButton("♭ -1")
        self.btn_trans_down.setFixedWidth(44)
        self.btn_trans_down.clicked.connect(lambda: self.adjust_transpose(-1))

        self.lbl_trans_val = QLabel("0")
        self.lbl_trans_val.setStyleSheet("font-weight: bold; color: #38bdf8; min-width: 18px;")
        self.lbl_trans_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_trans_up = QPushButton("♯ +1")
        self.btn_trans_up.setFixedWidth(44)
        self.btn_trans_up.clicked.connect(lambda: self.adjust_transpose(1))

        self.chk_sevenths = QCheckBox("Detect 7ths")
        self.chk_sevenths.setToolTip("Include dominant 7th and minor 7th templates")

        # Export Menu Button
        self.btn_export = QPushButton("Export Chords ▼")
        self.btn_export.setFixedHeight(34)
        export_menu = QMenu(self)
        export_menu.addAction("Export Plain Text (.txt)...", self.export_text_dialog)
        export_menu.addAction("Export ChordPro (.cho)...", self.export_chordpro_dialog)
        export_menu.addAction("Export CSV Spreadsheet (.csv)...", self.export_csv_dialog)
        export_menu.addSeparator()
        export_menu.addAction("Save Project Sidecar (.chordscout.json)...", self.save_project_dialog)
        export_menu.addAction("Load Project Sidecar...", self.load_project_dialog)
        export_menu.addSeparator()
        export_menu.addAction("Copy Chords to Clipboard (Ctrl+C)", self.copy_to_clipboard)
        self.btn_export.setMenu(export_menu)

        top_bar.addWidget(self.btn_open)
        top_bar.addWidget(self.btn_demo)
        top_bar.addSpacing(8)
        top_bar.addWidget(capo_lbl)
        top_bar.addWidget(self.combo_capo)
        top_bar.addSpacing(6)
        top_bar.addWidget(trans_lbl)
        top_bar.addWidget(self.btn_trans_down)
        top_bar.addWidget(self.lbl_trans_val)
        top_bar.addWidget(self.btn_trans_up)
        top_bar.addSpacing(10)
        top_bar.addWidget(self.chk_sevenths)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_export)
        main_layout.addLayout(top_bar)

        # Progress bar (for analysis)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Stacked central view: Index 0 = Hero Dropzone, Index 1 = Workspace Deck
        self.stack = QStackedWidget()

        # View 0: Hero Dropzone
        self.drop_hero = DropOverlayWidget(self)
        self.drop_hero.browse_requested.connect(self.on_open_file_clicked)
        self.drop_hero.demo_requested.connect(self.load_demo_song)
        self.stack.addWidget(self.drop_hero)

        # View 1: Main Workspace Deck
        self.workspace = QWidget()
        w_layout = QVBoxLayout(self.workspace)
        w_layout.setContentsMargins(0, 0, 0, 0)
        w_layout.setSpacing(10)

        # Waveform Timeline
        self.timeline = WaveformTimelineWidget(self)
        self.timeline.seek_requested.connect(self.seek_audio)
        w_layout.addWidget(self.timeline)

        # Middle Splitter: Tabs (Grid / Table / ChordPro) on Left, Fretboard on Right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Container: Tabs
        left_tabs = QTabWidget()

        # Tab 1: Lead Sheet Grid View
        self.grid_view = ChordGridView(self)
        self.grid_view.segment_clicked.connect(self.on_grid_card_clicked)
        left_tabs.addTab(self.grid_view, "🎼 Lead Sheet Grid")

        # Tab 2: Table & Editor View
        table_container = QWidget()
        t_layout = QVBoxLayout(table_container)
        t_layout.setContentsMargins(8, 8, 8, 8)
        t_layout.setSpacing(8)

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

        # Edit Action Buttons
        edit_row = QHBoxLayout()
        btn_edit = QPushButton("✏️ Change Chord")
        btn_edit.clicked.connect(self.edit_selected_chord)
        btn_split = QPushButton("✂️ Split Midpoint")
        btn_split.clicked.connect(self.split_selected_segment)
        btn_merge = QPushButton("🔗 Merge Next")
        btn_merge.clicked.connect(self.merge_with_next_segment)
        btn_del = QPushButton("🗑️ Set Silence")
        btn_del.clicked.connect(self.set_selected_to_silence)

        edit_row.addWidget(btn_edit)
        edit_row.addWidget(btn_split)
        edit_row.addWidget(btn_merge)
        edit_row.addWidget(btn_del)
        t_layout.addLayout(edit_row)

        left_tabs.addTab(table_container, "📋 Detailed Table & Editor")

        # Tab 3: ChordPro Text View
        self.text_chordpro = QTextEdit()
        self.text_chordpro.setReadOnly(True)
        self.text_chordpro.setStyleSheet("font-family: monospace; font-size: 12px; background-color: #10141f;")
        left_tabs.addTab(self.text_chordpro, "📄 ChordPro / Text View")

        splitter.addWidget(left_tabs)

        # Right Container: Rosewood Fretboard Panel
        right_panel = QFrame()
        right_panel.setObjectName("cardFrame")
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(6, 6, 6, 6)
        self.guitar_widget = GuitarFretboardWidget(self)
        r_layout.addWidget(self.guitar_widget)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 68)
        splitter.setStretchFactor(1, 32)
        w_layout.addWidget(splitter, 1)

        # Bottom HUD & Transport Bar
        self.hud = HudTransportWidget(self)
        self.hud.play_toggled.connect(self.toggle_playback)
        self.hud.prev_chord_requested.connect(self.jump_prev_chord)
        self.hud.next_chord_requested.connect(self.jump_next_chord)
        self.hud.speed_changed.connect(self.on_speed_changed)
        self.hud.loop_toggled.connect(self.on_loop_toggled)
        self.hud.volume_changed.connect(self.on_volume_changed)
        w_layout.addWidget(self.hud)

        self.stack.addWidget(self.workspace)
        main_layout.addWidget(self.stack, 1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Drop an audio file into the window to analyze.")

    # --- Drag & Drop ---

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(is_supported_audio_file(u.toLocalFile()) for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        for u in urls:
            path = Path(u.toLocalFile())
            if is_supported_audio_file(path):
                self.start_analysis(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # --- Analysis Intake ---

    def on_open_file_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;All Files (*)",
        )
        if path:
            self.start_analysis(Path(path))

    def load_demo_song(self) -> None:
        demo_path = Path(__file__).resolve().parent.parent.parent / "demo" / "classic_pop_progression.mp3"
        if demo_path.exists():
            self.start_analysis(demo_path)
        else:
            QMessageBox.information(
                self, "Demo Song", "Demo audio file not found. Please drop an MP3 into the window."
            )

    def start_analysis(self, file_path: Path) -> None:
        self.player.stop()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.btn_open.setEnabled(False)
        self.btn_demo.setEnabled(False)

        # Set media source for playback
        self.player.setSource(QUrl.fromLocalFile(str(file_path.resolve())))

        # Run background worker thread
        include_7ths = self.chk_sevenths.isChecked()
        self.audio_worker = AnalysisWorker(file_path, include_sevenths=include_7ths)
        self.audio_worker.progress_updated.connect(self.on_progress_updated)
        self.audio_worker.finished_success.connect(self.on_analysis_success)
        self.audio_worker.finished_error.connect(self.on_analysis_error)
        self.audio_worker.start()

    def on_progress_updated(self, progress: float, message: str) -> None:
        self.progress_bar.setValue(int(progress * 100))
        self.progress_bar.setFormat(f"{int(progress * 100)}% — {message}")
        self.status_bar.showMessage(message)

    def on_analysis_success(self, result: AnalysisResult, audio: np.ndarray) -> None:
        self.btn_open.setEnabled(True)
        self.btn_demo.setEnabled(True)
        self.progress_bar.setVisible(False)

        self.current_result = result
        self.base_segments = [
            ChordSegment(s.start_time, s.end_time, s.chord, s.confidence, s.is_user_edited)
            for s in result.segments
        ]
        self.audio_data = audio
        self.transposition_semitones = 0
        self.lbl_trans_val.setText("0")
        self.combo_capo.setCurrentIndex(0)

        # Switch stack to Workspace view
        self.stack.setCurrentIndex(1)

        # Update HUD
        meta = result.metadata
        self.hud.update_metadata(meta.key_estimate, meta.tempo_bpm)
        self.hud.update_timecode(0.0, meta.duration)

        # Update Timeline & Views
        self.timeline.set_data(result.segments, meta.duration, audio_data=audio)
        self.grid_view.set_segments(result.segments)
        self.populate_table()
        self.update_chordpro_preview()

        self.status_bar.showMessage(
            f"Analysis complete: {len(result.segments)} chords detected. Key: {meta.key_estimate or 'N/A'}"
        )

        if result.segments:
            self.select_segment_index(0)

    def on_analysis_error(self, err_msg: str) -> None:
        self.btn_open.setEnabled(True)
        self.btn_demo.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Analysis Failed", f"Could not analyze audio file:\n\n{err_msg}")
        self.status_bar.showMessage("Analysis failed.")

    # --- UI Updates ---

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
            c_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Confidence
            conf_val = int(seg.confidence * 100) if seg.chord != "N" else 100
            conf_item = QTableWidgetItem(f"{conf_val}%")
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, t_item)
            self.table.setItem(row, 1, d_item)
            self.table.setItem(row, 2, c_item)
            self.table.setItem(row, 3, conf_item)

    def update_chordpro_preview(self) -> None:
        if not self.current_result:
            return
        cho_text = export_chordpro(self.current_result)
        self.text_chordpro.setPlainText(cho_text)

    def select_segment_index(self, idx: int) -> None:
        if not self.current_result or idx < 0 or idx >= len(self.current_result.segments):
            return
        seg = self.current_result.segments[idx]
        capo = self.combo_capo.currentIndex()
        self.guitar_widget.set_chord(seg.chord, capo_fret=capo)
        self.grid_view.set_active_index(idx)

        # Highlight in table without triggering circular signals
        self.table.blockSignals(True)
        self.table.selectRow(idx)
        self.table.blockSignals(False)

    def on_table_selection_changed(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.current_result.segments):
            self.select_segment_index(row)

    def on_table_item_double_clicked(self, item: QTableWidgetItem) -> None:
        self.edit_selected_chord()

    def on_grid_card_clicked(self, idx: int, start_time: float) -> None:
        self.seek_audio(start_time)
        self.select_segment_index(idx)

    # --- Editing Chords ---

    def edit_selected_chord(self) -> None:
        row = self.table.currentRow()
        if not self.current_result or row < 0 or row >= len(self.current_result.segments):
            return

        seg = self.current_result.segments[row]
        common = list(GUITAR_CHORDS.keys())
        if "N" not in common:
            common.insert(0, "N")

        cur_idx = common.index(seg.chord) if seg.chord in common else 0

        new_chord, ok = QInputDialog.getItem(
            self,
            "Edit Chord Name",
            f"Select or enter chord for [{seg.formatted_start} - {seg.formatted_end}]:",
            common,
            cur_idx,
            editable=True,
        )
        if ok and new_chord:
            seg.chord = new_chord.strip()
            seg.is_user_edited = True
            self.populate_table()
            self.grid_view.set_segments(self.current_result.segments)
            self.timeline.update()
            self.update_chordpro_preview()
            self.select_segment_index(row)

    def split_selected_segment(self) -> None:
        row = self.table.currentRow()
        if not self.current_result or row < 0 or row >= len(self.current_result.segments):
            return

        seg = self.current_result.segments[row]
        if seg.duration < 0.6:
            QMessageBox.information(self, "Split", "Segment is too short to split further.")
            return

        mid = (seg.start_time + seg.end_time) / 2.0
        seg1 = ChordSegment(seg.start_time, mid, seg.chord, seg.confidence, is_user_edited=True)
        seg2 = ChordSegment(mid, seg.end_time, seg.chord, seg.confidence, is_user_edited=True)

        self.current_result.segments[row:row + 1] = [seg1, seg2]
        self.populate_table()
        self.grid_view.set_segments(self.current_result.segments)
        self.timeline.set_data(self.current_result.segments, self.current_result.metadata.duration, self.audio_data)
        self.update_chordpro_preview()
        self.select_segment_index(row)

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
        self.grid_view.set_segments(self.current_result.segments)
        self.timeline.set_data(self.current_result.segments, self.current_result.metadata.duration, self.audio_data)
        self.update_chordpro_preview()
        self.select_segment_index(row)

    def set_selected_to_silence(self) -> None:
        row = self.table.currentRow()
        if not self.current_result or row < 0 or row >= len(self.current_result.segments):
            return
        seg = self.current_result.segments[row]
        seg.chord = "N"
        seg.is_user_edited = True
        self.populate_table()
        self.grid_view.set_segments(self.current_result.segments)
        self.timeline.update()
        self.update_chordpro_preview()
        self.select_segment_index(row)

    def show_table_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        self.table.selectRow(row)

        menu = QMenu(self)
        menu.addAction("✏️ Change Chord...", self.edit_selected_chord)
        menu.addAction("✂️ Split Segment at Midpoint", self.split_selected_segment)
        menu.addAction("🔗 Merge with Next Segment", self.merge_with_next_segment)
        menu.addAction("🗑️ Set to Silence (N)", self.set_selected_to_silence)
        menu.addSeparator()
        menu.addAction("▶ Play from this Segment", lambda: self.play_from_row(row))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def play_from_row(self, row: int) -> None:
        if self.current_result and 0 <= row < len(self.current_result.segments):
            seg = self.current_result.segments[row]
            self.seek_audio(seg.start_time)
            self.player.play()

    # --- Transpose & Capo ---

    def adjust_transpose(self, delta: int) -> None:
        if not self.current_result:
            return
        self.transposition_semitones += delta
        self.lbl_trans_val.setText(f"{self.transposition_semitones:+d}" if self.transposition_semitones != 0 else "0")

        # Apply to segments
        self.current_result.segments = transpose_segments(self.base_segments, self.transposition_semitones)
        self.populate_table()
        self.grid_view.set_segments(self.current_result.segments)
        self.timeline.set_data(self.current_result.segments, self.current_result.metadata.duration, self.audio_data)
        self.update_chordpro_preview()

        # Update current chord
        pos_sec = self.player.position() / 1000.0
        seg = self.current_result.get_chord_at_time(pos_sec)
        if seg:
            self.guitar_widget.set_chord(seg.chord, self.combo_capo.currentIndex())

    def on_capo_changed(self, idx: int) -> None:
        # Capo 0 to 7
        if self.current_result:
            pos_sec = self.player.position() / 1000.0
            seg = self.current_result.get_chord_at_time(pos_sec)
            if seg:
                self.guitar_widget.set_chord(seg.chord, capo_fret=idx)

    # --- Playback & Synchronization ---

    def toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.hud.set_playing_state(is_playing)

    def on_player_position_changed(self, pos_ms: int) -> None:
        pos_sec = pos_ms / 1000.0
        dur_sec = self.current_result.metadata.duration if self.current_result else 1.0

        # Update Timeline playhead & HUD timecode
        self.timeline.set_current_time(pos_sec)
        self.hud.update_timecode(pos_sec, dur_sec)

        if not self.current_result or not self.current_result.segments:
            return

        # Find current segment and upcoming segment
        current_seg: Optional[ChordSegment] = None
        current_idx: int = -1
        for idx, s in enumerate(self.current_result.segments):
            if s.start_time <= pos_sec < s.end_time:
                current_seg = s
                current_idx = idx
                break

        if current_seg:
            next_seg = (
                self.current_result.segments[current_idx + 1]
                if current_idx + 1 < len(self.current_result.segments)
                else None
            )
            countdown = max(0.0, current_seg.end_time - pos_sec)
            next_name = next_seg.chord if next_seg else None
            self.hud.update_active_chord(current_seg.chord, next_name, countdown)

            # Update fretboard and grid
            capo = self.combo_capo.currentIndex()
            self.guitar_widget.set_chord(current_seg.chord, capo_fret=capo)
            self.grid_view.update_playback_time(pos_sec)

            # Loop check
            if self.is_looping_chord and pos_sec >= current_seg.end_time - 0.05:
                self.seek_audio(current_seg.start_time)

    def seek_audio(self, target_sec: float) -> None:
        target_ms = int(target_sec * 1000)
        self.player.setPosition(target_ms)
        self.timeline.set_current_time(target_sec)

    def jump_prev_chord(self) -> None:
        if not self.current_result or not self.current_result.segments:
            return
        pos_sec = self.player.position() / 1000.0
        for idx in range(len(self.current_result.segments) - 1, -1, -1):
            s = self.current_result.segments[idx]
            if s.start_time < pos_sec - 0.3:
                self.seek_audio(s.start_time)
                self.select_segment_index(idx)
                return
        self.seek_audio(0.0)

    def jump_next_chord(self) -> None:
        if not self.current_result or not self.current_result.segments:
            return
        pos_sec = self.player.position() / 1000.0
        for idx, s in enumerate(self.current_result.segments):
            if s.start_time > pos_sec + 0.1:
                self.seek_audio(s.start_time)
                self.select_segment_index(idx)
                return

    def on_speed_changed(self, speed: float) -> None:
        self.player.setPlaybackRate(speed)
        self.status_bar.showMessage(f"Playback speed set to {speed}x")

    def on_loop_toggled(self, loop_on: bool) -> None:
        self.is_looping_chord = loop_on
        if loop_on and self.current_result:
            pos_sec = self.player.position() / 1000.0
            seg = self.current_result.get_chord_at_time(pos_sec)
            if seg:
                self.timeline.set_loop_range(seg.start_time, seg.end_time, enabled=True)
                self.status_bar.showMessage(f"Looping chord: {seg.chord}")
                return
        self.timeline.set_loop_range(None, None, enabled=False)
        self.status_bar.showMessage("Loop disabled.")

    def on_volume_changed(self, vol: float) -> None:
        self.audio_output.setVolume(vol)

    def strum_current_chord(self) -> None:
        self.guitar_widget.on_strum_clicked()

    # --- Export Dialogs ---

    def check_has_result(self) -> bool:
        if not self.current_result or not self.current_result.segments:
            QMessageBox.warning(self, "No Song", "Please load an audio file first.")
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
            self.status_bar.showMessage(f"Exported text chart: {Path(path).name}")

    def export_chordpro_dialog(self) -> None:
        if not self.check_has_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save ChordPro File", "song.cho", "ChordPro Files (*.cho *.chordpro);;All Files (*)"
        )
        if path:
            cho = export_chordpro(self.current_result)
            Path(path).write_text(cho, encoding="utf-8")
            self.status_bar.showMessage(f"Exported ChordPro: {Path(path).name}")

    def export_csv_dialog(self) -> None:
        if not self.check_has_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Spreadsheet", "chords.csv", "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            export_csv(self.current_result, Path(path))
            self.status_bar.showMessage(f"Exported CSV: {Path(path).name}")

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
                self.on_analysis_success(res, audio=np.array([]))
                if os.path.exists(res.metadata.file_path):
                    self.player.setSource(QUrl.fromLocalFile(res.metadata.file_path))
                self.status_bar.showMessage(f"Project loaded: {Path(path).name}")
            except Exception as err:
                QMessageBox.critical(self, "Load Error", f"Failed to load project:\n\n{err}")

    def copy_to_clipboard(self) -> None:
        if not self.check_has_result():
            return
        text = export_plain_text(self.current_result)
        QApplication.clipboard().setText(text)
        self.status_bar.showMessage("Chord chart copied to clipboard! (Ctrl+C)")


def main(initial_file: Optional[str] = None) -> None:
    """Launch the ChordScout application."""
    app = QApplication(sys.argv)
    window = ChordScoutApp(initial_file=initial_file)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
