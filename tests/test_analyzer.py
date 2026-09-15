"""Tests for chord templates, key estimation, smoothing, and analysis on synthetic fixtures."""

from pathlib import Path
import numpy as np
import pytest

from chordscout.analyzer import (
    analyze_chords,
    build_chord_templates,
    estimate_key,
    merge_and_smooth_segments,
)
from chordscout.audio import load_audio
from chordscout.models import ChordSegment


def test_build_chord_templates():
    # Baseline triads: 12 Major + 12 Minor = 24
    templates = build_chord_templates(include_sevenths=False)
    assert len(templates) == 24
    assert "C" in templates
    assert "Am" in templates
    assert "F#" in templates

    # Check C major template has root (0), major 3rd (4), fifth (7)
    c_vec = templates["C"]
    assert c_vec[0] > 0
    assert c_vec[4] > 0
    assert c_vec[7] > 0
    # And non-chord notes are 0
    assert c_vec[1] == 0
    assert c_vec[2] == 0

    # With 7ths: 24 triads + 12 dom7 + 12 m7 = 48
    templates_7 = build_chord_templates(include_sevenths=True)
    assert len(templates_7) == 48
    assert "G7" in templates_7
    assert "Am7" in templates_7


def test_estimate_key():
    # Synthesize C major profile chroma (C, E, G dominant)
    c_chroma = np.zeros(12, dtype=np.float32)
    c_chroma[0] = 1.0  # C
    c_chroma[4] = 0.8  # E
    c_chroma[7] = 0.8  # G
    key = estimate_key(c_chroma)
    assert "C major" in key

    # Zero chroma returns Unknown
    assert estimate_key(np.zeros(12, dtype=np.float32)) == "Unknown"


def test_merge_and_smooth_segments():
    # Test merging identical contiguous segments
    raw = [
        ChordSegment(0.0, 1.0, "C", 0.9),
        ChordSegment(1.0, 2.0, "C", 0.8),
        ChordSegment(2.0, 3.0, "G", 0.85),
    ]
    merged = merge_and_smooth_segments(raw, total_duration=3.0, min_segment_duration=0.4)
    assert len(merged) == 2
    assert merged[0].chord == "C"
    assert merged[0].start_time == 0.0
    assert merged[0].end_time == 2.0
    assert merged[1].chord == "G"
    assert merged[1].start_time == 2.0
    assert merged[1].end_time == 3.0


def test_merge_absorbs_micro_glitches():
    # Micro segment (0.1s) of "D" between "C" and "G"
    raw = [
        ChordSegment(0.0, 2.0, "C", 0.9),
        ChordSegment(2.0, 2.1, "D", 0.3),  # glitch
        ChordSegment(2.1, 4.0, "G", 0.9),
    ]
    merged = merge_and_smooth_segments(raw, total_duration=4.0, min_segment_duration=0.4)
    assert len(merged) == 2
    assert merged[0].chord == "C"
    assert merged[1].chord == "G"


def test_analyze_chords_synthetic_progression(synthetic_progression_wav: Path):
    """Verify that a local synthetic WAV file produces an accurate visible chord progression."""
    audio, sr, duration = load_audio(synthetic_progression_wav)
    segments, meta = analyze_chords(audio, sr=sr, min_segment_duration=0.4)

    assert len(segments) >= 3
    # Check that the progression contains C, G, Am, and F
    chords_found = [s.chord for s in segments]
    assert "C" in chords_found
    assert "G" in chords_found
    assert "Am" in chords_found or "A" in chords_found
    assert "F" in chords_found

    # Check timing boundaries
    assert segments[0].start_time == 0.0
    assert segments[-1].end_time >= duration - 0.1

    # Check metadata
    assert abs(meta["duration"] - 8.0) < 0.1
    assert "key_estimate" in meta
