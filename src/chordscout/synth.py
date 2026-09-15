"""Synthesizer for realistic plucked acoustic guitar chord audio previews."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject
from PySide6.QtMultimedia import QAudioFormat, QAudioSink

from chordscout.guitar import GuitarChord, get_guitar_chord


# Standard guitar string open frequencies (E2, A2, D3, G3, B3, E4) in Hz
STANDARD_TUNING_HZ = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63]


class GuitarSynthesizer(QObject):
    """Synthesizes and plays plucked guitar chord voicings."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.sr = 44100
        self._sink: Optional[QAudioSink] = None
        self._buffer: Optional[QBuffer] = None
        self._setup_sink()

    def _setup_sink(self) -> None:
        fmt = QAudioFormat()
        fmt.setSampleRate(self.sr)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._sink = QAudioSink(fmt, self)

    def synthesize_chord(
        self,
        chord: GuitarChord,
        duration: float = 1.6,
        strum_speed_sec: float = 0.035,
    ) -> np.ndarray:
        """Synthesize a plucked acoustic guitar chord waveform.

        Each string is plucked with a slight delay (strum) and decays exponentially
        with physical acoustic harmonics.
        """
        num_samples = int(self.sr * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        waveform = np.zeros(num_samples, dtype=np.float32)

        # Iterate strings from low E (string 6, idx 0) to high e (string 1, idx 5)
        for s_idx, fret in enumerate(chord.frets):
            if fret < 0:
                continue  # Muted string

            # Compute frequency: f = open_freq * 2^(fret / 12)
            base_hz = STANDARD_TUNING_HZ[s_idx]
            freq = base_hz * (2.0 ** (fret / 12.0))

            # Strum delay for natural arpeggiation feel
            delay_samples = int(s_idx * strum_speed_sec * self.sr)
            remaining_samples = num_samples - delay_samples
            if remaining_samples <= 0:
                continue

            st = t[:remaining_samples]
            # Exponential decay envelope: higher strings decay slightly faster
            decay_rate = 3.2 + (s_idx * 0.4)
            decay = np.exp(-decay_rate * st)

            # Pluck body: fundamental + rich harmonics
            fundamental = np.sin(2.0 * np.pi * freq * st)
            h2 = 0.55 * np.sin(2.0 * np.pi * 2.0 * freq * st) * np.exp(-1.5 * decay_rate * st)
            h3 = 0.28 * np.sin(2.0 * np.pi * 3.0 * freq * st) * np.exp(-2.5 * decay_rate * st)
            h4 = 0.14 * np.sin(2.0 * np.pi * 4.0 * freq * st) * np.exp(-3.5 * decay_rate * st)

            # Pluck attack transient (slight initial pick scratch)
            attack_samples = min(200, remaining_samples)
            attack = np.ones_like(st)
            attack[:attack_samples] = np.linspace(0.0, 1.0, attack_samples)

            string_tone = (fundamental + h2 + h3 + h4) * decay * attack
            waveform[delay_samples:] += string_tone

        # Normalize and prevent clipping
        max_peak = np.max(np.abs(waveform))
        if max_peak > 1e-5:
            waveform = (waveform / max_peak) * 0.88

        # Convert to 16-bit PCM integer
        return (waveform * 32767.0).astype(np.int16)

    def play_chord(self, chord_or_name: GuitarChord | str) -> None:
        """Play synthesized guitar chord immediately."""
        if isinstance(chord_or_name, str):
            gc = get_guitar_chord(chord_or_name)
            if not gc:
                return
            chord = gc
        else:
            chord = chord_or_name

        pcm_data = self.synthesize_chord(chord)
        raw_bytes = pcm_data.tobytes()

        # Stop previous playback if any
        if self._sink:
            self._sink.stop()
        if self._buffer:
            self._buffer.close()

        byte_array = QByteArray(raw_bytes)
        self._buffer = QBuffer(byte_array, self)
        self._buffer.open(QIODevice.OpenModeFlag.ReadOnly)

        if self._sink:
            self._sink.start(self._buffer)
