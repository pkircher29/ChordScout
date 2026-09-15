"""Tests for plain text, ChordPro, CSV, and JSON project export."""

from pathlib import Path
import pytest

from chordscout.export import (
    export_chordpro,
    export_csv,
    export_plain_text,
    load_project,
    save_project,
)
from chordscout.models import AnalysisMetadata, AnalysisResult, ChordSegment


@pytest.fixture
def sample_result() -> AnalysisResult:
    meta = AnalysisMetadata(
        file_path="test_song.mp3",
        file_name="test_song.mp3",
        duration=16.0,
        sample_rate=22050,
        tempo_bpm=120.0,
        key_estimate="G major",
    )
    segments = [
        ChordSegment(0.0, 4.0, "G", 0.95),
        ChordSegment(4.0, 8.0, "D", 0.90),
        ChordSegment(8.0, 12.0, "Em", 0.88),
        ChordSegment(12.0, 16.0, "C", 0.92, is_user_edited=True),
    ]
    return AnalysisResult(metadata=meta, segments=segments)


def test_export_plain_text(sample_result: AnalysisResult):
    text = export_plain_text(sample_result)
    assert "test_song.mp3" in text
    assert "G major" in text
    assert "120" in text
    assert "00:00.0 - 00:04.0   G" in text
    assert "00:12.0 - 00:16.0   C" in text
    assert "GUITAR CHORDS REFERENCE" in text
    assert "3 2 0 0 0 3" in text  # G chord


def test_export_chordpro(sample_result: AnalysisResult):
    cho = export_chordpro(sample_result)
    assert "{title: test_song.mp3}" in cho
    assert "{key: G major}" in cho
    assert "{tempo: 120}" in cho
    assert "[G]" in cho
    assert "[D]" in cho
    assert "[Em]" in cho
    assert "[C]" in cho
    assert "{define: G frets" in cho


def test_export_csv(sample_result: AnalysisResult, tmp_path: Path):
    csv_path = tmp_path / "output.csv"
    export_csv(sample_result, csv_path)

    content = csv_path.read_text(encoding="utf-8")
    assert "start_time,end_time,duration,chord,confidence,is_user_edited" in content
    assert "0.0,4.0,4.0,G,0.95,False" in content
    assert "12.0,16.0,4.0,C,0.92,True" in content


def test_save_and_load_project(sample_result: AnalysisResult, tmp_path: Path):
    project_path = tmp_path / "test.chordscout.json"
    save_project(sample_result, project_path)

    loaded = load_project(project_path)
    assert loaded.metadata.file_name == sample_result.metadata.file_name
    assert loaded.metadata.key_estimate == "G major"
    assert len(loaded.segments) == 4
    assert loaded.segments[3].chord == "C"
    assert loaded.segments[3].is_user_edited is True
