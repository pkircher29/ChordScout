"""Audio decoding, validation, and metadata extraction."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Tuple

import librosa
import numpy as np
import soundfile as sf


SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
    ".aiff",
    ".aif",
    ".wma",
}


class AudioError(Exception):
    """Base exception for audio processing errors."""


class UnsupportedAudioFormatError(AudioError):
    """Raised when an unsupported file extension or format is provided."""


class AudioDecodeError(AudioError):
    """Raised when audio decoding fails."""


def is_supported_audio_file(file_path: str | Path) -> bool:
    """Check whether a file has a supported audio extension."""
    suffix = Path(file_path).suffix.lower()
    return suffix in SUPPORTED_EXTENSIONS


def get_audio_info(file_path: str | Path) -> dict[str, Any]:
    """Retrieve audio metadata (duration, sample rate, channels) safely."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    if not is_supported_audio_file(path):
        raise UnsupportedAudioFormatError(
            f"Unsupported audio file extension '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    try:
        info = sf.info(str(path))
        return {
            "duration": float(info.duration),
            "sample_rate": int(info.samplerate),
            "channels": int(info.channels),
            "format": str(info.format),
            "subtype": str(info.subtype),
        }
    except Exception:
        # Fallback to librosa if sf.info fails (e.g. some m4a/aac)
        try:
            duration = librosa.get_duration(path=str(path))
            return {
                "duration": float(duration),
                "sample_rate": 22050,
                "channels": 1,
                "format": path.suffix.upper().lstrip("."),
                "subtype": "unknown",
            }
        except Exception as err:
            raise AudioDecodeError(f"Could not read audio information for '{path.name}': {err}") from err


def decode_with_ffmpeg(input_path: str | Path, target_sr: int = 22050) -> Tuple[np.ndarray, int]:
    """Fallback decoder using ffmpeg if direct library decode fails."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise AudioDecodeError("FFmpeg is not installed or not in PATH for fallback decoding.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name

    try:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            str(target_sr),
            "-vn",
            tmp_wav,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if res.returncode != 0:
            raise AudioDecodeError(
                f"FFmpeg decoding failed: {res.stderr.decode('utf-8', errors='replace')[:400]}"
            )

        data, sr = sf.read(tmp_wav, dtype="float32")
        return data, sr
    finally:
        if os.path.exists(tmp_wav):
            try:
                os.remove(tmp_wav)
            except OSError:
                pass


def load_audio(
    file_path: str | Path,
    target_sr: int = 22050,
    mono: bool = True,
) -> Tuple[np.ndarray, int, float]:
    """Load and normalize audio from supported audio formats.

    Returns:
        (audio_data, sample_rate, duration_seconds)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    if not is_supported_audio_file(path):
        raise UnsupportedAudioFormatError(
            f"Unsupported audio file extension '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # First attempt: librosa.load (which uses soundfile then audioread)
    try:
        y, sr = librosa.load(str(path), sr=target_sr, mono=mono)
    except Exception:
        # Second attempt: soundfile directly
        try:
            data, original_sr = sf.read(str(path), dtype="float32")
            if mono and data.ndim > 1:
                data = np.mean(data, axis=1)
            if original_sr != target_sr:
                y = librosa.resample(data, orig_sr=original_sr, target_sr=target_sr)
                sr = target_sr
            else:
                y = data
                sr = original_sr
        except Exception:
            # Third attempt: FFmpeg fallback
            try:
                y, sr = decode_with_ffmpeg(path, target_sr=target_sr)
            except Exception as err:
                raise AudioDecodeError(f"Failed to decode audio file '{path.name}': {err}") from err

    if len(y) == 0:
        raise AudioDecodeError(f"Audio file '{path.name}' contains no samples.")

    # Normalize audio amplitude safely
    max_val = np.max(np.abs(y))
    if max_val > 1e-5:
        y = y / max_val

    duration = float(len(y) / sr)
    return y, sr, duration


def compute_waveform_envelope(audio: np.ndarray, num_points: int = 1000) -> np.ndarray:
    """Compute a downsampled peak envelope for fast UI waveform rendering."""
    if len(audio) == 0:
        return np.zeros(num_points, dtype=np.float32)
    if len(audio) <= num_points:
        return np.abs(audio)

    chunk_size = len(audio) // num_points
    trimmed = audio[: chunk_size * num_points]
    reshaped = np.abs(trimmed.reshape(num_points, chunk_size))
    return np.max(reshaped, axis=1)
