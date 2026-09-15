"""Tests for data models and formatting."""

from chordscout.models import (
    AnalysisMetadata,
    AnalysisResult,
    ChordSegment,
    format_timestamp,
)


def test_format_timestamp():
    assert format_timestamp(0.0) == "00:00"
    assert format_timestamp(65.0) == "01:05"
    assert format_timestamp(65.4, include_ms=True) == "01:05.4"


def test_chord_segment():
    seg = ChordSegment(start_time=1.5, end_time=4.5, chord="Em", confidence=0.88)
    assert seg.duration == 3.0
    assert seg.formatted_start == "00:01.5"
    assert seg.formatted_end == "00:04.5"
    assert seg.time_range_str == "00:01.5 - 00:04.5"

    d = seg.to_dict()
    assert d["chord"] == "Em"
    assert d["confidence"] == 0.88

    restored = ChordSegment.from_dict(d)
    assert restored.chord == seg.chord
    assert restored.start_time == seg.start_time


def test_analysis_result_methods():
    meta = AnalysisMetadata(
        file_path="song.mp3",
        file_name="song.mp3",
        duration=10.0,
        sample_rate=22050,
        key_estimate="C major",
    )
    segments = [
        ChordSegment(0.0, 4.0, "C"),
        ChordSegment(4.0, 8.0, "G"),
        ChordSegment(8.0, 10.0, "Am"),
    ]
    result = AnalysisResult(metadata=meta, segments=segments)

    assert result.unique_chords() == ["C", "G", "Am"]
    assert result.get_chord_at_time(2.0).chord == "C"
    assert result.get_chord_at_time(5.5).chord == "G"
    assert result.get_chord_at_time(9.0).chord == "Am"

    d = result.to_dict()
    restored = AnalysisResult.from_dict(d)
    assert len(restored.segments) == 3
    assert restored.metadata.key_estimate == "C major"
