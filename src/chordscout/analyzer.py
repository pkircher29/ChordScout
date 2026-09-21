"""Audio chord recognition engine using Chroma features and template matching."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import librosa
import numpy as np
from scipy.ndimage import median_filter

from chordscout.models import ChordSegment


PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

ENHARMONIC_MAP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}

# Krumhansl-Schmuckler key profiles for key estimation
MAJOR_KEY_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=np.float32,
)
MINOR_KEY_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=np.float32,
)


def normalize_vector(v: np.ndarray) -> np.ndarray:
    """Normalize vector to unit L2 norm."""
    norm = np.linalg.norm(v)
    if norm > 1e-7:
        return v / norm
    return v


def build_chord_templates(include_sevenths: bool = False) -> Dict[str, np.ndarray]:
    """Generate normalized 12-semitone chord templates.

    Default dictionary covers the 24 fundamental triads (12 Major, 12 Minor).
    If include_sevenths is True, adds Dominant 7th and Minor 7th templates.
    """
    templates: Dict[str, np.ndarray] = {}

    for i, root in enumerate(PITCH_NAMES):
        # Major triad: Root (0), Major 3rd (4), Perfect 5th (7)
        maj = np.zeros(12, dtype=np.float32)
        maj[i] = 1.0
        maj[(i + 4) % 12] = 0.8
        maj[(i + 7) % 12] = 0.8
        templates[root] = normalize_vector(maj)

        # Minor triad: Root (0), Minor 3rd (3), Perfect 5th (7)
        min_triad = np.zeros(12, dtype=np.float32)
        min_triad[i] = 1.0
        min_triad[(i + 3) % 12] = 0.8
        min_triad[(i + 7) % 12] = 0.8
        templates[f"{root}m"] = normalize_vector(min_triad)

        if include_sevenths:
            # Dominant 7th: Root (0), Major 3rd (4), 5th (7), Minor 7th (10)
            dom7 = np.zeros(12, dtype=np.float32)
            dom7[i] = 1.0
            dom7[(i + 4) % 12] = 0.75
            dom7[(i + 7) % 12] = 0.75
            dom7[(i + 10) % 12] = 0.65
            templates[f"{root}7"] = normalize_vector(dom7)

            # Minor 7th: Root (0), Minor 3rd (3), 5th (7), Minor 7th (10)
            m7 = np.zeros(12, dtype=np.float32)
            m7[i] = 1.0
            m7[(i + 3) % 12] = 0.75
            m7[(i + 7) % 12] = 0.75
            m7[(i + 10) % 12] = 0.65
            templates[f"{root}m7"] = normalize_vector(m7)

    return templates


def estimate_key(chroma_mean: np.ndarray) -> str:
    """Estimate song key by correlating mean chroma with Krumhansl-Schmuckler profiles."""
    if np.sum(chroma_mean) < 1e-6:
        return "Unknown"

    v = normalize_vector(chroma_mean)
    maj_prof = normalize_vector(MAJOR_KEY_PROFILE)
    min_prof = normalize_vector(MINOR_KEY_PROFILE)

    best_corr = -1.0
    best_key = "C major"

    for shift in range(12):
        # Major correlation
        rot_maj = np.roll(maj_prof, shift)
        corr_maj = float(np.dot(v, rot_maj))
        if corr_maj > best_corr:
            best_corr = corr_maj
            best_key = f"{PITCH_NAMES[shift]} major"

        # Minor correlation
        rot_min = np.roll(min_prof, shift)
        corr_min = float(np.dot(v, rot_min))
        if corr_min > best_corr:
            best_corr = corr_min
            best_key = f"{PITCH_NAMES[shift]} minor"

    return best_key


def _confidence_from_score(score: float) -> float:
    """Map a cosine match in roughly [0.2, 1.0] onto a 0.1-1.0 confidence."""
    return max(0.1, min(1.0, (score - 0.2) / 0.8))


def hold_chord_labels(
    scores: np.ndarray,
    chord_names: List[str],
    rms: np.ndarray,
    silence_threshold: float = 0.015,
    confidence_threshold: float = 0.35,
    change_margin: float = 0.05,
) -> List[Tuple[str, float]]:
    """Choose one label per frame, and do not change chords on a near-tie.

    ``scores`` is cosine similarity with shape ``(n_chords, n_frames)``.

    Desktop chroma (CQT) separates pitch classes sharply, so two templates that
    share most notes (G vs Gm on a power chord, or any other ambiguous frame)
    trade the top score by only about 0.00-0.02 and each spell lasts long enough
    to survive a short segment hold. A real triad change still leads the chord
    it replaces by well over 0.10. Require that lead (``change_margin``) before
    replacing the held chord.

    The held chord only blocks a challenger while it is itself still above
    ``confidence_threshold``. Once it drops out, the next frame that clears the
    floor can start a new chord immediately. Silence also clears the hold.
    """
    if scores.ndim != 2:
        raise ValueError("scores must have shape (n_chords, n_frames)")
    n_frames = int(scores.shape[1])
    if len(rms) < n_frames:
        raise ValueError("rms must cover every score frame")
    if len(chord_names) != scores.shape[0]:
        raise ValueError("chord_names must match the score rows")

    labels: List[Tuple[str, float]] = []
    held: Optional[int] = None

    for i in range(n_frames):
        if float(rms[i]) < silence_threshold:
            labels.append(("N", 1.0))
            held = None
            continue

        best = int(np.argmax(scores[:, i]))
        best_score = float(scores[best, i])
        if best_score < confidence_threshold:
            labels.append(("N", 0.5))
            held = None
            continue

        held_score = float(scores[held, i]) if held is not None else -1.0
        if (
            held is None
            or best == held
            or held_score < confidence_threshold
            or best_score >= held_score + change_margin
        ):
            held = best

        labels.append((chord_names[held], _confidence_from_score(float(scores[held, i]))))

    return labels


def merge_and_smooth_segments(
    raw_segments: List[ChordSegment],
    total_duration: float,
    min_segment_duration: float = 0.4,
) -> List[ChordSegment]:
    """Merge contiguous identical chords, remove ultra-short glitch transitions,

    and ensure continuous coverage from 0.0 to total_duration.
    """
    if not raw_segments:
        return [ChordSegment(0.0, total_duration, "N", confidence=1.0)]

    # 1. Merge contiguous identical chord names
    merged: List[ChordSegment] = []
    current = raw_segments[0]

    for nxt in raw_segments[1:]:
        if nxt.chord == current.chord:
            # Expand current segment and average confidence weighted by duration
            dur_cur = max(0.01, current.end_time - current.start_time)
            dur_nxt = max(0.01, nxt.end_time - nxt.start_time)
            avg_conf = (current.confidence * dur_cur + nxt.confidence * dur_nxt) / (dur_cur + dur_nxt)
            current.end_time = nxt.end_time
            current.confidence = avg_conf
        else:
            merged.append(current)
            current = nxt
    merged.append(current)

    # 2. Prune micro-segments shorter than min_segment_duration (absorb into neighbor)
    if len(merged) > 1:
        cleaned: List[ChordSegment] = []
        i = 0
        while i < len(merged):
            seg = merged[i]
            if seg.duration < min_segment_duration and len(merged) > 1:
                if cleaned:
                    # Absorb into previous segment
                    cleaned[-1].end_time = seg.end_time
                elif i + 1 < len(merged):
                    # Absorb into next segment
                    merged[i + 1].start_time = seg.start_time
                else:
                    cleaned.append(seg)
            else:
                cleaned.append(seg)
            i += 1
        merged = cleaned if cleaned else merged

    # 3. Final consolidation pass to re-merge any adjacent identical chords formed after absorption
    final_segments: List[ChordSegment] = []
    if merged:
        cur = merged[0]
        for nxt in merged[1:]:
            if nxt.chord == cur.chord:
                cur.end_time = nxt.end_time
                cur.confidence = (cur.confidence + nxt.confidence) / 2.0
            else:
                final_segments.append(cur)
                cur = nxt
        final_segments.append(cur)

    # 4. Enforce exact bounds [0.0, total_duration]
    if final_segments:
        final_segments[0].start_time = 0.0
        final_segments[-1].end_time = max(final_segments[-1].end_time, total_duration)

    return final_segments


def analyze_chords(
    audio: np.ndarray,
    sr: int = 22050,
    hop_length: int = 1024,
    include_sevenths: bool = False,
    min_segment_duration: float = 0.1,
    silence_threshold: float = 0.015,
    confidence_threshold: float = 0.35,
    change_margin: float = 0.05,
    chroma_smooth_frames: int = 3,
    progress_callback: Optional[Any] = None,
) -> Tuple[List[ChordSegment], Dict[str, Any]]:
    """Analyze audio to extract time-aligned chord segments and metadata.

    Args:
        audio: 1D normalized float32 audio waveform.
        sr: Sample rate (default 22050).
        hop_length: Hop length for STFT/CQT (default 1024).
        include_sevenths: Whether to include 7th chord templates.
        min_segment_duration: Minimum duration (seconds) before micro-segments are merged.
            Kept near a tenth of a second so real offbeat changes survive. Raising
            this toward half a second is what makes detection miss fast changes;
            false flips are handled by ``change_margin`` instead.
        silence_threshold: RMS threshold below which frames are labeled 'N'.
        confidence_threshold: Minimum correlation required to start or keep a chord, else 'N'.
        change_margin: How far a new template must outscore the held chord before
            the label changes. 0 restores raw frame-by-frame argmax.
        chroma_smooth_frames: Width of the chroma median filter, in frames. 3 is
            about 140 ms at the default hop and only removes single-frame spikes.
        progress_callback: Callable taking float progress (0.0 to 1.0) and status string.

    Returns:
        (segments, metadata_dict)
    """
    total_samples = len(audio)
    total_duration = float(total_samples / sr)

    if progress_callback:
        progress_callback(0.05, "Separating harmonic audio...")

    # Harmonic-Percussive Separation to isolate pitch/chords from drum noise
    try:
        y_harm, y_perc = librosa.effects.hpss(audio, margin=(1.0, 1.0))
    except Exception:
        y_harm = audio
        y_perc = audio

    if progress_callback:
        progress_callback(0.20, "Estimating tuning offset...")

    # Estimate tuning offset
    try:
        tuning = float(librosa.estimate_tuning(y=y_harm, sr=sr))
    except Exception:
        tuning = 0.0
    tuning_cents = float(tuning * 100)

    if progress_callback:
        progress_callback(0.35, "Extracting constant-Q chromagram...")

    # Constant-Q Chromagram (tuned to C2=65.4Hz)
    try:
        chroma = librosa.feature.chroma_cqt(
            y=y_harm,
            sr=sr,
            hop_length=hop_length,
            tuning=tuning,
            n_chroma=12,
            fmin=librosa.note_to_hz("C2"),
        )
    except Exception:
        chroma = librosa.feature.chroma_stft(
            y=y_harm, sr=sr, hop_length=hop_length, n_chroma=12, tuning=tuning
        )

    # Frame energy (RMS)
    rms = librosa.feature.rms(y=audio, hop_length=hop_length)[0]
    # Match length
    min_len = min(chroma.shape[1], len(rms))
    chroma = chroma[:, :min_len]
    rms = rms[:min_len]

    # Non-linear logarithmic compression on chroma
    chroma = np.log1p(10.0 * chroma)

    if progress_callback:
        progress_callback(0.50, "Tracking beat rhythm...")

    # Tempo only. Chord labels are not snapped to these beats; see below.
    try:
        tempo, beats = librosa.beat.beat_track(
            y=y_perc, sr=sr, hop_length=hop_length, trim=False
        )
        if hasattr(tempo, "__len__"):
            tempo_bpm = float(tempo[0]) if len(tempo) > 0 else 120.0
        else:
            tempo_bpm = float(tempo)
    except Exception:
        tempo_bpm = 120.0
        beats = np.array([], dtype=int)

    # Key estimation from global chroma average
    global_chroma = np.mean(chroma, axis=1)
    estimated_key = estimate_key(global_chroma)

    if progress_callback:
        progress_callback(0.65, "Matching chord templates...")

    templates = build_chord_templates(include_sevenths=include_sevenths)
    chord_names = list(templates.keys())
    template_matrix = np.array([templates[k] for k in chord_names], dtype=np.float32)  # (N_chords, 12)

    raw_segments: List[ChordSegment] = []

    # Beat tracking stays in the metadata only. One label per beat interval drops
    # genuine offbeat changes, so chords are labeled per frame. A wide median
    # would blur those changes too; near-tie flicker is rejected by change_margin.
    smooth_frames = max(1, int(chroma_smooth_frames))
    smoothed_chroma = median_filter(chroma, size=(1, smooth_frames))
    frame_times = librosa.frames_to_time(np.arange(min_len), sr=sr, hop_length=hop_length)

    norms = np.linalg.norm(smoothed_chroma, axis=0, keepdims=True)
    norms[norms < 1e-6] = 1.0
    norm_chroma = smoothed_chroma / norms

    # (N_chords, 12) x (12, N_frames) -> (N_chords, N_frames)
    all_scores = np.dot(template_matrix, norm_chroma)

    frame_labels = hold_chord_labels(
        all_scores,
        chord_names,
        rms,
        silence_threshold=silence_threshold,
        confidence_threshold=confidence_threshold,
        change_margin=change_margin,
    )

    dt = float(hop_length / sr)
    for i, (chord_label, conf) in enumerate(frame_labels):
        t_start = float(frame_times[i])
        t_end = float(min(total_duration, t_start + dt))
        raw_segments.append(ChordSegment(t_start, t_end, chord_label, confidence=conf))

    if progress_callback:
        progress_callback(0.85, "Smoothing and merging chord segments...")

    # Consolidate and smooth segments
    smoothed_segments = merge_and_smooth_segments(
        raw_segments,
        total_duration=total_duration,
        min_segment_duration=min_segment_duration,
    )

    metadata: Dict[str, Any] = {
        "duration": total_duration,
        "sample_rate": sr,
        "tempo_bpm": round(tempo_bpm, 1),
        "key_estimate": estimated_key,
        "tuning_offset_cents": round(tuning_cents, 1),
    }

    if progress_callback:
        progress_callback(1.0, "Analysis complete.")

    return smoothed_segments, metadata
