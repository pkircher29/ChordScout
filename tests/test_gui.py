"""Tests for PySide6 GUI components in headless offscreen mode."""

import os
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from chordscout.app import ChordScoutApp, GuitarFretboardWidget, ChordTimelineWidget
from chordscout.models import AnalysisMetadata, AnalysisResult, ChordSegment


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
    assert widget.chord_name == "Am"
    assert widget.chord is not None
    assert widget.chord.frets == (-1, 0, 2, 2, 1, 0)

    widget.set_chord("N")
    assert widget.chord is None


def test_timeline_widget(qapp, sample_result: AnalysisResult):
    timeline = ChordTimelineWidget()
    timeline.set_data(sample_result.segments, sample_result.metadata.duration)
    assert len(timeline.segments) == 3
    assert timeline.total_duration == 12.0

    timeline.set_current_time(5.0)
    assert timeline.current_time == 5.0


def test_app_window_lifecycle(qapp, sample_result: AnalysisResult):
    window = ChordScoutApp()
    assert window.windowTitle() == "ChordScout - Guitar Chord Analyzer"
    assert window.acceptDrops() is True

    # Set sample result directly
    window.current_result = sample_result
    window.populate_table()
    assert window.table.rowCount() == 3

    # Select row 1 ("G")
    window.table.selectRow(1)
    window.on_table_selection_changed()
    assert window.guitar_widget.chord_name == "G"

    # Test split segment
    window.split_selected_segment()
    assert len(window.current_result.segments) == 4
    assert window.table.rowCount() == 4

    # Test merge segment
    window.table.selectRow(1)
    window.merge_with_next_segment()
    assert len(window.current_result.segments) == 3
    assert window.table.rowCount() == 3

    window.close()
