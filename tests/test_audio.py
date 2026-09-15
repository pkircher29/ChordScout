"""Tests for audio loading, format verification, and waveform envelope calculation."""

from pathlib import Path
import numpy as np
import pytest

from chordscout.audio import (
    AudioDecodeError,
    UnsupportedAudioFormatError,
    compute_waveform_envelope,
    get_audio_info,
    is_supported_audio_file,
    load_audio,
)


def test_supported_audio_formats():
    assert is_supported_audio_file("track.mp3")
    assert is_supported_audio_file("track.WAV")
    assert is_supported_audio_file("track.flac")
    assert is_supported_audio_file("track.m4a")
    assert is_supported_audio_file("track.ogg")
    assert not is_supported_audio_file("track.txt")
    assert not is_supported_audio_file("track.exe")
    assert not is_supported_audio_file("track.mid")


def test_get_audio_info_valid(synthetic_progression_wav: Path):
    info = get_audio_info(synthetic_progression_wav)
    assert info["duration"] > 7.5
    assert info["sample_rate"] == 22050
    assert info["channels"] == 1


def test_get_audio_info_file_not_found():
    with pytest.raises(FileNotFoundError):
        get_audio_info("non_existent_file_12345.mp3")


def test_get_audio_info_unsupported(unsupported_file: Path):
    with pytest.raises(UnsupportedAudioFormatError):
        get_audio_info(unsupported_file)


def test_load_audio_success(synthetic_progression_wav: Path):
    y, sr, duration = load_audio(synthetic_progression_wav, target_sr=22050)
    assert sr == 22050
    assert abs(duration - 8.0) < 0.1
    assert isinstance(y, np.ndarray)
    assert y.ndim == 1
    assert len(y) == int(sr * duration)
    assert np.max(np.abs(y)) <= 1.0


def test_load_audio_corrupt_file(corrupt_audio_file: Path):
    with pytest.raises(AudioDecodeError):
        load_audio(corrupt_audio_file)


def test_compute_waveform_envelope():
    audio = np.array([0.1, -0.5, 0.8, -0.2, 0.4, -0.9, 0.3, -0.1], dtype=np.float32)
    env = compute_waveform_envelope(audio, num_points=4)
    assert len(env) == 4
    assert np.all(env >= 0.0)

    # Empty audio handling
    empty_env = compute_waveform_envelope(np.array([], dtype=np.float32), num_points=10)
    assert len(empty_env) == 10
    assert np.all(empty_env == 0.0)
