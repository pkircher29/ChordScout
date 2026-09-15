"""Tests for transposer and capo calculation."""

from chordscout.models import ChordSegment
from chordscout.transposer import transpose_chord_name, transpose_segments


def test_transpose_chord_name():
    # C major + 2 semitones = D
    assert transpose_chord_name("C", 2) == "D"
    # C major - 2 semitones = Bb or A#
    assert transpose_chord_name("C", -2) in ("A#", "Bb")
    # Am + 2 semitones = Bm
    assert transpose_chord_name("Am", 2) == "Bm"
    # G7 + 1 semitone = G#7
    assert transpose_chord_name("G7", 1) == "G#7"
    # Silence stays silence
    assert transpose_chord_name("N", 3) == "N"
    assert transpose_chord_name("", 2) == ""


def test_transpose_segments():
    segments = [
        ChordSegment(0.0, 2.0, "C"),
        ChordSegment(2.0, 4.0, "G"),
        ChordSegment(4.0, 6.0, "Am"),
    ]
    # Transpose +2
    t = transpose_segments(segments, 2)
    assert t[0].chord == "D"
    assert t[1].chord == "A"
    assert t[2].chord == "Bm"
    # Zero transposition returns exact copy
    t0 = transpose_segments(segments, 0)
    assert [s.chord for s in t0] == ["C", "G", "Am"]
