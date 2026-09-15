"""Tests for PySide6 studio GUI components in headless offscreen mode."""

import os
from pathlib import Path
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from chordscout.app import ChordScoutApp
from chordscout.models import AnalysisMetadata, AnalysisResult, ChordSegment
from chordscout.widgets.chord_grid_view import ChordGridView
from chordscout.widgets.fretboard_widget import GuitarFretboardWidget
from chordscout.widgets.hud_transport import HudTransportWidget
from chordscout.widgets.waveform_timeline import WaveformTimelineWidget


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_result() -> AnalysisResult:
    meta = AnalysisMetadata(
        file_path="test_song.mp3",
        file_name="test_song.mp3",
        duration=12.0,
        sample_rate=22050,
        tempo_bpm=120.0,
        key_estimate="C major",
    )
    segments = [
        ChordSegment(0.0, 4.0, "C", 0.95),
        ChordSegment(4.0, 8.0, "G", 0.90),
        ChordSegment(8.0, 12.0, "Am", 0.88),
    ]
    return AnalysisResult(metadata=meta, segments=segments)


def test_fretboard_widget(qapp):
    widget = GuitarFretboardWidget()
    widget.set_chord("Am")
    assert widget.canvas.chord_name == "Am"
    assert widget.canvas.chord is not None
    assert widget.canvas.chord.frets == (-1, 0, 2, 2, 1, 0)

    # Test Strum execution (does not throw)
    widget.on_strum_clicked()

    widget.set_chord("N")
    assert widget.canvas.chord is None


def test_waveform_timeline_widget(qapp, sample_result: AnalysisResult):
    timeline = WaveformTimelineWidget()
    fake_audio = np.sin(np.linspace(0, 100, 1000, dtype=np.float32))
    timeline.set_data(sample_result.segments, sample_result.metadata.duration, audio_data=fake_audio)
    assert len(timeline.segments) == 3
    assert timeline.total_duration == 12.0
    assert timeline.waveform_peaks is not None

    timeline.set_current_time(5.0)
    assert timeline.current_time == 5.0

    # Test loop range
    timeline.set_loop_range(4.0, 8.0, enabled=True)
    assert timeline.is_looping is True


def test_hud_transport_widget(qapp):
    hud = HudTransportWidget()
    hud.update_active_chord("Am", "F", 2.5)
    assert hud.lbl_active_chord.text() == "Am"
    assert hud.lbl_next_chord.text() == "F"
    assert "2.5s" in hud.lbl_next_countdown.text()

    hud.update_metadata("G major", 124.0)
    assert "G major" in hud.lbl_key_badge.text()
    assert "124 BPM" in hud.lbl_tempo_badge.text()


def test_chord_grid_view(qapp, sample_result: AnalysisResult):
    grid = ChordGridView()
    grid.set_segments(sample_result.segments)
    assert len(grid.cards) == 3

    grid.update_playback_time(6.0)
    assert grid.current_active_idx == 1  # 2nd chord is G


def test_app_window_lifecycle(qapp, sample_result: AnalysisResult):
    window = ChordScoutApp()
    assert "ChordScout" in window.windowTitle()
    assert window.acceptDrops() is True

    # Check initial view is Hero Dropzone
    assert window.stack.currentIndex() == 0

    # Simulate successful analysis load
    fake_audio = np.zeros(22050 * 12, dtype=np.float32)
    window.on_analysis_success(sample_result, fake_audio)

    # Check stack switched to Workspace
    assert window.stack.currentIndex() == 1
    assert window.table.rowCount() == 3

    # Select row 1 ("G")
    window.select_segment_index(1)
    assert window.guitar_widget.canvas.chord_name == "G"

    # Test Transpose (+2 semitones: C->D, G->A, Am->Bm)
    window.adjust_transpose(2)
    assert window.lbl_trans_val.text() == "+2"
    assert window.current_result.segments[0].chord == "D"
    assert window.current_result.segments[1].chord == "A"
    assert window.current_result.segments[2].chord == "Bm"

    # Test Split Segment
    window.table.selectRow(0)
    window.split_selected_segment()
    assert len(window.current_result.segments) == 4

    # Test Merge Segment
    window.table.selectRow(0)
    window.merge_with_next_segment()
    assert len(window.current_result.segments) == 3

    window.close()
