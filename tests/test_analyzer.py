"""Tests for chord templates, key estimation, smoothing, and analysis on synthetic fixtures."""

from pathlib import Path
import numpy as np
import pytest

import chordscout.analyzer as analyzer
from chordscout.analyzer import (
    analyze_chords,
    build_chord_templates,
    estimate_key,
    hold_chord_labels,
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


def test_hold_chord_labels_ignores_near_tie_flicker():
    """A rival that leads by less than change_margin must not split the chord."""
    # Row 0 is G, row 1 is Gm. Gm pokes ahead by 0.02 in the middle.
    scores = np.array(
        [
            [0.80, 0.80, 0.80, 0.79, 0.79, 0.80],
            [0.70, 0.70, 0.70, 0.81, 0.81, 0.70],
        ],
        dtype=np.float32,
    )
    rms = np.ones(scores.shape[1], dtype=np.float32)
    labels = [name for name, _ in hold_chord_labels(scores, ["G", "Gm"], rms, change_margin=0.05)]
    assert labels == ["G", "G", "G", "G", "G", "G"]


def test_hold_chord_labels_accepts_a_real_change_and_resets_on_silence():
    scores = np.array(
        [
            [0.85, 0.40, 0.20, 0.20],
            [0.40, 0.85, 0.10, 0.82],
        ],
        dtype=np.float32,
    )
    rms = np.array([0.2, 0.2, 0.001, 0.2], dtype=np.float32)
    labels = [name for name, _ in hold_chord_labels(scores, ["C", "G"], rms, change_margin=0.05)]
    assert labels == ["C", "G", "N", "G"]


def test_analyze_chords_stable_power_chord_does_not_flicker():
    """A chord with no third used to flip G/Gm. It should stay on one label."""
    sr = 22050
    duration = 3.0
    freqs = [98.00, 146.83, 196.00, 293.66]  # G power chord
    n = int(sr * duration)
    t = np.arange(n) / sr
    rng = np.random.default_rng(2)
    signal = np.zeros(n, dtype=np.float64)
    for index, freq in enumerate(freqs):
        start = int(sr * 0.02 * index / (len(freqs) - 1))
        tt = t[start:]
        for harmonic in range(1, 7):
            signal[start:] += (
                (1.0 / harmonic)
                * np.sin(2 * np.pi * freq * harmonic * (1 + 0.001 * harmonic) * tt)
                * np.exp(-tt * 0.9 * (0.5 + 0.4 * harmonic))
            )
    signal[: int(sr * 0.015)] += rng.standard_normal(int(sr * 0.015)) * 0.08
    signal = (signal / (np.max(np.abs(signal)) + 1e-6)).astype(np.float32)

    segments, _ = analyze_chords(signal, sr=sr)
    chord_names = [segment.chord for segment in segments if segment.chord != "N"]

    assert chord_names
    assert len(set(chord_names)) == 1
    assert chord_names[0] in {"G", "Gm"}


def test_analyze_chords_preserves_offbeat_changes(monkeypatch: pytest.MonkeyPatch):
    """Chord changes between detected beats must remain visible."""
    sr = 22050
    duration = 0.5
    notes_by_chord = [
        ("C", [261.63, 329.63, 392.00]),
        ("G", [196.00, 246.94, 293.66]),
        ("Am", [220.00, 261.63, 329.63]),
        ("F", [174.61, 220.00, 261.63]),
    ] * 2
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = np.concatenate(
        [sum(np.sin(2 * np.pi * frequency * t) for frequency in notes) for _, notes in notes_by_chord]
    ).astype(np.float32)
    audio /= np.max(np.abs(audio)) + 1e-6
    monkeypatch.setattr(
        analyzer.librosa.beat,
        "beat_track",
        lambda **_: (120.0, np.array([0, 22, 44, 66, 80])),
    )

    segments, _ = analyze_chords(audio, sr=sr)

    assert [name for name, _ in notes_by_chord] == [segment.chord for segment in segments]


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
