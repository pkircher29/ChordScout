"""Guitar chord fingerings, fretboard definitions, and visual diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class GuitarChord:
    """Guitar chord fingering definition for standard tuning (E A D G B e).

    frets: List of 6 integers representing strings from low E (string 6) to high e (string 1).
           -1 represents muted ('x'), 0 represents open ('o'), >0 represents fret number.
    fingers: Optional list of 6 integers (1=index, 2=middle, 3=ring, 4=pinky, 0=none).
    base_fret: Starting fret offset (1 if in first position).
    """

    name: str
    frets: Tuple[int, int, int, int, int, int]
    fingers: Tuple[int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0)
    base_fret: int = 1

    @property
    def string_display(self) -> str:
        """Display string like 'x 3 2 0 1 0'."""
        return " ".join("x" if f == -1 else str(f) for f in self.frets)

    def render_ascii(self) -> str:
        """Render a readable ASCII fretboard diagram."""
        lines = [f"Chord: {self.name} (Base fret: {self.base_fret})"]
        header = "  " + " ".join("x" if f == -1 else ("o" if f == 0 else " ") for f in self.frets)
        lines.append(header)
        nut_or_bar = "  " + ("=" * 11 if self.base_fret == 1 else "-" * 11)
        lines.append(nut_or_bar)

        max_fret = max([f for f in self.frets if f > 0] + [self.base_fret + 3])
        min_fret = self.base_fret
        display_frets = range(min_fret, min_fret + 4)

        for fret in display_frets:
            fret_str = f"{fret:1d}|"
            row = []
            for f in self.frets:
                if f == fret:
                    row.append("O")
                else:
                    row.append("|")
            fret_str += " ".join(row)
            lines.append(fret_str)

        return "\n".join(lines)


# Standard guitar chord library (Standard Tuning E-A-D-G-B-e)
GUITAR_CHORDS: Dict[str, GuitarChord] = {
    # Major chords
    "C": GuitarChord("C", (-1, 3, 2, 0, 1, 0), (0, 3, 2, 0, 1, 0), 1),
    "C#": GuitarChord("C#", (-1, 4, 6, 6, 6, 4), (0, 1, 2, 3, 4, 1), 4),
    "Db": GuitarChord("Db", (-1, 4, 6, 6, 6, 4), (0, 1, 2, 3, 4, 1), 4),
    "D": GuitarChord("D", (-1, -1, 0, 2, 3, 2), (0, 0, 0, 1, 3, 2), 1),
    "D#": GuitarChord("D#", (-1, 6, 8, 8, 8, 6), (0, 1, 2, 3, 4, 1), 6),
    "Eb": GuitarChord("Eb", (-1, 6, 8, 8, 8, 6), (0, 1, 2, 3, 4, 1), 6),
    "E": GuitarChord("E", (0, 2, 2, 1, 0, 0), (0, 2, 3, 1, 0, 0), 1),
    "F": GuitarChord("F", (1, 3, 3, 2, 1, 1), (1, 3, 4, 2, 1, 1), 1),
    "F#": GuitarChord("F#", (2, 4, 4, 3, 2, 2), (1, 3, 4, 2, 1, 1), 2),
    "Gb": GuitarChord("Gb", (2, 4, 4, 3, 2, 2), (1, 3, 4, 2, 1, 1), 2),
    "G": GuitarChord("G", (3, 2, 0, 0, 0, 3), (2, 1, 0, 0, 0, 3), 1),
    "G#": GuitarChord("G#", (4, 6, 6, 5, 4, 4), (1, 3, 4, 2, 1, 1), 4),
    "Ab": GuitarChord("Ab", (4, 6, 6, 5, 4, 4), (1, 3, 4, 2, 1, 1), 4),
    "A": GuitarChord("A", (-1, 0, 2, 2, 2, 0), (0, 0, 1, 2, 3, 0), 1),
    "A#": GuitarChord("A#", (-1, 1, 3, 3, 3, 1), (0, 1, 2, 3, 4, 1), 1),
    "Bb": GuitarChord("Bb", (-1, 1, 3, 3, 3, 1), (0, 1, 2, 3, 4, 1), 1),
    "B": GuitarChord("B", (-1, 2, 4, 4, 4, 2), (0, 1, 2, 3, 4, 1), 2),

    # Minor chords
    "Cm": GuitarChord("Cm", (-1, 3, 5, 5, 4, 3), (0, 1, 3, 4, 2, 1), 3),
    "C#m": GuitarChord("C#m", (-1, 4, 6, 6, 5, 4), (0, 1, 3, 4, 2, 1), 4),
    "Dbm": GuitarChord("Dbm", (-1, 4, 6, 6, 5, 4), (0, 1, 3, 4, 2, 1), 4),
    "Dm": GuitarChord("Dm", (-1, -1, 0, 2, 3, 1), (0, 0, 0, 2, 3, 1), 1),
    "D#m": GuitarChord("D#m", (-1, 6, 8, 8, 7, 6), (0, 1, 3, 4, 2, 1), 6),
    "Ebm": GuitarChord("Ebm", (-1, 6, 8, 8, 7, 6), (0, 1, 3, 4, 2, 1), 6),
    "Em": GuitarChord("Em", (0, 2, 2, 0, 0, 0), (0, 2, 3, 0, 0, 0), 1),
    "Fm": GuitarChord("Fm", (1, 3, 3, 1, 1, 1), (1, 3, 4, 1, 1, 1), 1),
    "F#m": GuitarChord("F#m", (2, 4, 4, 2, 2, 2), (1, 3, 4, 1, 1, 1), 2),
    "Gbm": GuitarChord("Gbm", (2, 4, 4, 2, 2, 2), (1, 3, 4, 1, 1, 1), 2),
    "Gm": GuitarChord("Gm", (3, 5, 5, 3, 3, 3), (1, 3, 4, 1, 1, 1), 3),
    "G#m": GuitarChord("G#m", (4, 6, 6, 4, 4, 4), (1, 3, 4, 1, 1, 1), 4),
    "Abm": GuitarChord("Abm", (4, 6, 6, 4, 4, 4), (1, 3, 4, 1, 1, 1), 4),
    "Am": GuitarChord("Am", (-1, 0, 2, 2, 1, 0), (0, 0, 2, 3, 1, 0), 1),
    "A#m": GuitarChord("A#m", (-1, 1, 3, 3, 2, 1), (0, 1, 3, 4, 2, 1), 1),
    "Bbm": GuitarChord("Bbm", (-1, 1, 3, 3, 2, 1), (0, 1, 3, 4, 2, 1), 1),
    "Bm": GuitarChord("Bm", (-1, 2, 4, 4, 3, 2), (0, 1, 3, 4, 2, 1), 2),

    # 7th chords
    "C7": GuitarChord("C7", (-1, 3, 2, 3, 1, 0), (0, 3, 2, 4, 1, 0), 1),
    "D7": GuitarChord("D7", (-1, -1, 0, 2, 1, 2), (0, 0, 0, 2, 1, 3), 1),
    "E7": GuitarChord("E7", (0, 2, 0, 1, 0, 0), (0, 2, 0, 1, 0, 0), 1),
    "F7": GuitarChord("F7", (1, 3, 1, 2, 1, 1), (1, 3, 1, 2, 1, 1), 1),
    "G7": GuitarChord("G7", (3, 2, 0, 0, 0, 1), (3, 2, 0, 0, 0, 1), 1),
    "A7": GuitarChord("A7", (-1, 0, 2, 0, 2, 0), (0, 0, 2, 0, 3, 0), 1),
    "B7": GuitarChord("B7", (-1, 2, 1, 2, 0, 2), (0, 2, 1, 3, 0, 4), 1),

    # Minor 7th chords
    "Am7": GuitarChord("Am7", (-1, 0, 2, 0, 1, 0), (0, 0, 2, 0, 1, 0), 1),
    "Em7": GuitarChord("Em7", (0, 2, 0, 0, 0, 0), (0, 1, 0, 0, 0, 0), 1),
    "Dm7": GuitarChord("Dm7", (-1, -1, 0, 2, 1, 1), (0, 0, 0, 2, 1, 1), 1),
    "Bm7": GuitarChord("Bm7", (-1, 2, 0, 2, 0, 2), (0, 1, 0, 2, 0, 3), 2),

    # Suspended chords
    "Dsus4": GuitarChord("Dsus4", (-1, -1, 0, 2, 3, 3), (0, 0, 0, 1, 2, 3), 1),
    "Asus4": GuitarChord("Asus4", (-1, 0, 2, 2, 3, 0), (0, 0, 1, 2, 3, 0), 1),
    "Esus4": GuitarChord("Esus4", (0, 2, 2, 2, 0, 0), (0, 2, 3, 4, 0, 0), 1),

    # Power chords (5)
    "E5": GuitarChord("E5", (0, 2, 2, -1, -1, -1), (0, 1, 2, 0, 0, 0), 1),
    "A5": GuitarChord("A5", (-1, 0, 2, 2, -1, -1), (0, 0, 1, 2, 0, 0), 1),
    "D5": GuitarChord("D5", (-1, -1, 0, 2, 3, -1), (0, 0, 0, 1, 2, 0), 1),
    "G5": GuitarChord("G5", (3, 5, 5, -1, -1, -1), (1, 3, 4, 0, 0, 0), 3),
    "C5": GuitarChord("C5", (-1, 3, 5, 5, -1, -1), (0, 1, 3, 4, 0, 0), 3),
}


ENHARMONIC_FLAT_TO_SHARP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}


def normalize_chord_name(name: str) -> str:
    """Normalize chord name to canonical representation (e.g. Db -> C#, clean whitespace)."""
    name = name.strip()
    if not name or name == "N":
        return "N"

    for flat, sharp in ENHARMONIC_FLAT_TO_SHARP.items():
        if name.startswith(flat):
            return sharp + name[len(flat):]

    return name


def get_guitar_chord(chord_name: str) -> Optional[GuitarChord]:
    """Retrieve guitar chord fingering by name, or None if unknown."""
    norm = normalize_chord_name(chord_name)
    return GUITAR_CHORDS.get(norm)
