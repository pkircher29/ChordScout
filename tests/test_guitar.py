"""Tests for guitar chord database and diagram rendering."""

from chordscout.guitar import GUITAR_CHORDS, get_guitar_chord, normalize_chord_name


def test_guitar_chords_library():
    # Common open chords
    assert "C" in GUITAR_CHORDS
    assert "G" in GUITAR_CHORDS
    assert "D" in GUITAR_CHORDS
    assert "Am" in GUITAR_CHORDS
    assert "Em" in GUITAR_CHORDS
    assert "F" in GUITAR_CHORDS

    c = GUITAR_CHORDS["C"]
    assert c.frets == (-1, 3, 2, 0, 1, 0)
    assert c.string_display == "x 3 2 0 1 0"
    assert c.base_fret == 1


def test_normalize_chord_name_enharmonics():
    assert normalize_chord_name("C") == "C"
    assert normalize_chord_name("Db") == "C#"
    assert normalize_chord_name("Eb") == "D#"
    assert normalize_chord_name("Gb") == "F#"
    assert normalize_chord_name("Ab") == "G#"
    assert normalize_chord_name("Bb") == "A#"
    assert normalize_chord_name("  Am  ") == "Am"
    assert normalize_chord_name("N") == "N"


def test_get_guitar_chord():
    assert get_guitar_chord("G") is not None
    assert get_guitar_chord("Am7") is not None
    assert get_guitar_chord("Db") is not None  # Resolves to C#
    assert get_guitar_chord("N") is None
    assert get_guitar_chord("NonExistentChordXYZ") is None


def test_guitar_chord_ascii_diagram():
    chord = GUITAR_CHORDS["Am"]
    ascii_art = chord.render_ascii()
    assert "Am" in ascii_art
    assert "|" in ascii_art
    assert "O" in ascii_art
