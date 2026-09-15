"""Test fixtures and synthetic audio generators for ChordScout tests."""

import os
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf


def generate_chord_sine(notes_hz: list[float], duration_sec: float, sr: int = 22050) -> np.ndarray:
    """Generate a synthesized multi-tone chord with harmonics."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    signal = np.zeros_like(t)
    for f in notes_hz:
        # Fundamental
        signal += np.sin(2 * np.pi * f * t)
        # 2nd harmonic (octave)
        signal += 0.5 * np.sin(2 * np.pi * 2 * f * t)
        # 3rd harmonic (fifth)
        signal += 0.25 * np.sin(2 * np.pi * 3 * f * t)
    # Apply attack/decay envelope to avoid sharp click
    env = np.ones_like(t)
    fade_len = int(sr * 0.05)
    if len(t) > 2 * fade_len:
        env[:fade_len] = np.linspace(0, 1, fade_len)
        env[-fade_len:] = np.linspace(1, 0, fade_len)
    return (signal * env).astype(np.float32)


@pytest.fixture
def synthetic_progression_wav(tmp_path: Path) -> Path:
    """Create an 8-second WAV file with classic I-V-vi-IV progression in C major:

    C major (2s) -> G major (2s) -> A minor (2s) -> F major (2s).
    """
    sr = 22050
    # C major: C4 (261.63), E4 (329.63), G4 (392.00)
    c_chord = generate_chord_sine([261.63, 329.63, 392.00], 2.0, sr)
    # G major: G3 (196.00), B3 (246.94), D4 (293.66)
    g_chord = generate_chord_sine([196.00, 246.94, 293.66], 2.0, sr)
    # A minor: A3 (220.00), C4 (261.63), E4 (329.63)
    am_chord = generate_chord_sine([220.00, 261.63, 329.63], 2.0, sr)
    # F major: F3 (174.61), A3 (220.00), C4 (261.63)
    f_chord = generate_chord_sine([174.61, 220.00, 261.63], 2.0, sr)

    full_audio = np.concatenate([c_chord, g_chord, am_chord, f_chord])
    # Normalize
    full_audio /= np.max(np.abs(full_audio)) + 1e-6

    wav_path = tmp_path / "test_progression.wav"
    sf.write(str(wav_path), full_audio, sr, format="WAV", subtype="PCM_16")
    return wav_path


@pytest.fixture
def corrupt_audio_file(tmp_path: Path) -> Path:
    """Create a corrupted audio file for error handling verification."""
    corrupt_path = tmp_path / "corrupt_song.mp3"
    corrupt_path.write_bytes(b"NOT_A_VALID_MP3_OR_AUDIO_DATA_HEADER_1234567890")
    return corrupt_path


@pytest.fixture
def unsupported_file(tmp_path: Path) -> Path:
    """Create a file with unsupported extension."""
    doc_path = tmp_path / "song_lyrics.docx"
    doc_path.write_text("These are lyrics, not audio.")
    return doc_path
