"""Pitch transposition and Capo calculator for guitar chords."""

from __future__ import annotations

from typing import List

from chordscout.guitar import normalize_chord_name
from chordscout.models import AnalysisResult, ChordSegment


PITCHES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PITCHES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def transpose_chord_name(chord: str, semitones: int, prefer_sharps: bool = True) -> str:
    """Transpose a chord name by given semitones (+ or -)."""
    chord = chord.strip()
    if not chord:
        return ""
    if chord == "N":
        return "N"

    normalized = normalize_chord_name(chord)
    pitches = PITCHES_SHARP if prefer_sharps else PITCHES_FLAT

    # Extract root
    root = ""
    suffix = ""
    for candidate in sorted(PITCHES_SHARP + PITCHES_FLAT, key=len, reverse=True):
        if normalized.startswith(candidate):
            root = candidate
            suffix = normalized[len(candidate):]
            break

    if not root:
        return chord

    try:
        idx = PITCHES_SHARP.index(root)
    except ValueError:
        try:
            idx = PITCHES_FLAT.index(root)
        except ValueError:
            return chord

    new_idx = (idx + semitones) % 12
    return f"{pitches[new_idx]}{suffix}"


def transpose_segments(segments: List[ChordSegment], semitones: int) -> List[ChordSegment]:
    """Return a new list of segments transposed by semitones."""
    if semitones == 0:
        return [
            ChordSegment(
                s.start_time, s.end_time, s.chord, s.confidence, is_user_edited=s.is_user_edited
            )
            for s in segments
        ]

    transposed: List[ChordSegment] = []
    for s in segments:
        new_chord = transpose_chord_name(s.chord, semitones)
        transposed.append(
            ChordSegment(
                start_time=s.start_time,
                end_time=s.end_time,
                chord=new_chord,
                confidence=s.confidence,
                is_user_edited=True,
            )
        )
    return transposed
