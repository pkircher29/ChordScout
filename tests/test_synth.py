"""Tests for guitar chord audio synthesis."""

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication

from chordscout.guitar import GUITAR_CHORDS
from chordscout.synth import GuitarSynthesizer


@pytest.fixture(scope="session")
def qcore_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_synthesize_chord(qcore_app):
    synth = GuitarSynthesizer()
    c_chord = GUITAR_CHORDS["C"]
    samples = synth.synthesize_chord(c_chord, duration=0.5)

    assert isinstance(samples, np.ndarray)
    assert samples.dtype == np.int16
    assert len(samples) == int(44100 * 0.5)
    assert np.max(np.abs(samples)) > 0


def test_synth_play_chord(qcore_app):
    synth = GuitarSynthesizer()
    # Playing chord should execute cleanly without exception
    synth.play_chord("Am")
    synth.play_chord("N")  # Silence should be ignored safely
