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


# Chords are decoded over the whole track (Viterbi), not frame by frame.
# A chord change costs SWITCH_PENALTY in frame-score units; a new chord is
# kept only when its lead, summed over every frame it lasts, pays that off.
# Real changes win frame after frame; near-ties and passing tones never add up.
SWITCH_PENALTY = 1.5

# Head start for chords in the song's key on the second decode. The key comes
# from the first decode's chords, not raw chroma. Clearly played chords win by
# far more than this; in thin passages it keeps near-ties in key.
KEY_BONUS = 0.05

# A frame's evidence counts (best score / CLEAR_SCORE) ** CLARITY_POWER, capped
# at 1: thin near-tie passages need longer to change and stop flickering, while
# clearly played quick changes switch at the normal cost.
CLARITY_POWER = 2.0
CLEAR_SCORE = 0.5

# Below this centered-correlation score a frame is "N" (no chord).
CONFIDENCE_THRESHOLD = 0.25


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


def _centered(m: np.ndarray, axis: int) -> np.ndarray:
    """Mean-removed, unit-length along ``axis`` (Pearson correlation form).

    Log-compressed chroma has a floor in every bin, so plain cosine scores a
    clean C triad nearly the same as Cm. Centering scores the shape instead.
    """
    c = m - np.mean(m, axis=axis, keepdims=True)
    norms = np.linalg.norm(c, axis=axis, keepdims=True)
    norms[norms < 1e-6] = 1.0
    return c / norms


def _parse_chord(name: str) -> Optional[Tuple[int, bool]]:
    """Root pitch class and minor flag of a chord name ("F#m7" -> (6, True))."""
    root_name = name[:2] if len(name) > 1 and name[1] == "#" else name[:1]
    if root_name not in PITCH_NAMES:
        return None
    return PITCH_NAMES.index(root_name), name[len(root_name):].startswith("m")


def is_diatonic(chord: str, tonic: int) -> bool:
    """True if ``chord`` is I, IV, V (major) or ii, iii, vi (minor) of ``tonic`` major."""
    parsed = _parse_chord(chord)
    if parsed is None:
        return False
    root, minor = parsed
    degree = (root - tonic) % 12
    return degree in (2, 4, 9) if minor else degree in (0, 5, 7)


def key_from_chords(path: np.ndarray, chord_names: List[str]) -> Optional[Tuple[int, bool]]:
    """Major-key tonic whose diatonic chords cover the most decoded frames,

    and whether the song sits on its relative minor (vi clearly outlasts I).
    ``path`` holds chord indices; values past the chord list mean "N".
    Returns None when fewer than ~2 seconds of chords were found.
    """
    path = np.asarray(path)
    counts = np.bincount(path[path < len(chord_names)], minlength=len(chord_names))
    if counts.sum() < 43:
        return None

    def frames_of(name: str) -> int:
        return int(counts[chord_names.index(name)]) if name in chord_names else 0

    best_tonic, best_cover = 0, -1
    for tonic in range(12):
        cover = sum(int(counts[c]) for c, name in enumerate(chord_names) if is_diatonic(name, tonic))
        # Keys a fifth apart share four chords; a tie goes to the key whose
        # I or vi chord is actually heard more.
        cover = cover * 4 + frames_of(PITCH_NAMES[tonic]) + frames_of(f"{PITCH_NAMES[(tonic + 9) % 12]}m")
        if cover > best_cover:
            best_tonic, best_cover = tonic, cover
    major = frames_of(PITCH_NAMES[best_tonic])
    rel_minor = frames_of(f"{PITCH_NAMES[(best_tonic + 9) % 12]}m")
    # Only the name depends on this; a near-even split is usually a major
    # song visiting vi.
    return best_tonic, rel_minor * 4 > major * 5


def _key_name(tonic: int, minor: bool) -> str:
    return f"{PITCH_NAMES[(tonic + 9) % 12]} minor" if minor else f"{PITCH_NAMES[tonic]} major"


def viterbi(scores: np.ndarray, weights: np.ndarray, penalty: float) -> np.ndarray:
    """Highest-scoring state path when every change costs ``penalty``.

    ``scores`` is (states, frames). Staying is free and all changes cost the
    same, so each step only needs the best previous state: O(frames x states).
    """
    n_states, n_frames = scores.shape
    back = np.zeros((n_frames, n_states), dtype=np.int32)
    total = scores[:, 0] * weights[0]
    states = np.arange(n_states)
    for t in range(1, n_frames):
        best_prev = int(np.argmax(total))
        switch_total = total[best_prev] - penalty
        stay = total >= switch_total
        back[t] = np.where(stay, states, best_prev)
        total = np.where(stay, total, switch_total) + weights[t] * scores[:, t]
    path = np.empty(n_frames, dtype=np.int32)
    state = int(np.argmax(total))
    for t in range(n_frames - 1, -1, -1):
        path[t] = state
        state = back[t, state]
    return path


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
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    switch_penalty: float = SWITCH_PENALTY,
    key_bonus: float = KEY_BONUS,
    clarity_power: float = CLARITY_POWER,
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
        silence_threshold: RMS threshold below which frames are labeled 'N'.
        confidence_threshold: Minimum centered correlation required, else 'N'.
        switch_penalty: Cost of a chord change in the Viterbi decode.
        key_bonus: Head start for in-key chords on the second decode (0 skips it).
        clarity_power: How much less thin, near-tie frames count (0 disables).
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

    # Beat tracking to synchronize chords with musical beats
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

    # Beat tracking is useful for tempo metadata, but one label per beat interval
    # loses genuine changes that happen on an offbeat. Label at frame resolution,
    # then let the segment smoother remove only very brief noise.
    smoothed_chroma = median_filter(chroma, size=(1, max(1, int(chroma_smooth_frames))))
    frame_times = librosa.frames_to_time(np.arange(min_len), sr=sr, hop_length=hop_length)

    # (N_chords, 12) x (12, N_frames) -> (N_chords, N_frames)
    chord_scores = np.dot(_centered(template_matrix, axis=1), _centered(smoothed_chroma, axis=0))
    n_chords = len(chord_names)
    silent = rms < silence_threshold

    # Chords plus "N" (last row). N scores the confidence threshold, so it
    # wins where no chord clears it, and owns silent frames outright.
    scores = np.vstack([chord_scores, np.full((1, min_len), confidence_threshold)])
    scores[:, silent] = -1.0
    scores[n_chords, silent] = 1.0
    best = np.max(chord_scores, axis=0)
    weights = np.minimum(1.0, np.maximum(best, 0.0) / CLEAR_SCORE) ** clarity_power
    weights[silent] = 1.0

    path = viterbi(scores, weights, switch_penalty)

    # Second pass: find the key the first pass's chords live in, give those
    # chords a head start, and decode again.
    song_key = key_from_chords(path, chord_names)
    if song_key is not None and key_bonus > 0:
        in_key = np.array([is_diatonic(name, song_key[0]) for name in chord_names])
        boosted = scores.copy()
        boosted[np.ix_(np.flatnonzero(in_key), np.flatnonzero(~silent))] += key_bonus
        path = viterbi(boosted, weights, switch_penalty)
    if song_key is not None:
        estimated_key = _key_name(*song_key)

    dt = float(hop_length / sr)
    for i in range(min_len):
        t_start = float(frame_times[i])
        t_end = float(min(total_duration, t_start + dt))
        state = int(path[i])
        if state == n_chords:
            raw_segments.append(ChordSegment(t_start, t_end, "N", confidence=1.0))
        else:
            # Centered scores run lower than cosine: a clean triad is ~0.55.
            conf = max(0.1, min(1.0, (float(chord_scores[state, i]) - 0.2) / 0.5))
            raw_segments.append(ChordSegment(t_start, t_end, chord_names[state], confidence=conf))

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
