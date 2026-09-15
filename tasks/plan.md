# ChordScout implementation plan

## Goal

Build a standalone, local-first Windows desktop application that accepts a song file and produces an editable, time-aligned guitar chord progression.

## Approved scope

- Input: local MP3, WAV, M4A, and FLAC files.
- Output: approximate chord names aligned to time, plus plain text, CSV, and ChordPro export.
- Interface: a standalone desktop window, not an Auto-KJ feature.
- Privacy: audio stays on the local machine.

## Product decisions

- The app must label the initial result as an analysis, not ground truth.
- Users must be able to correct chord names and timing before export.
- The first version targets common major/minor pop and rock harmony. It must disclose that dense arrangements, borrowed chords, jazz voicings, and key changes can require correction.
- The app should keep the original audio untouched and persist edits in a sidecar project file.

## Architecture

- Python 3.11 virtual environment for dependency compatibility.
- PySide6 desktop UI.
- FFmpeg for decode/normalization.
- Librosa chroma features plus a transparent chord-template baseline; chord detection remains replaceable by a stronger model later.
- JSON project file stores source-file fingerprint, segments, edits, and export metadata.

## Vertical delivery slices

1. Audio intake and waveform metadata
   - User selects a supported local song.
   - App reports filename, duration, and decoding errors.

2. Chord-analysis baseline
   - App computes chroma features and an estimated major/minor/no-chord sequence.
   - App displays chord segments with timestamps and a confidence hint.

3. Correction and export
   - User can rename, split, merge, or remove chord segments.
   - App exports plain text, CSV, and ChordPro from the corrected result.

## Acceptance criteria

- A local WAV fixture produces a visible progression without network access.
- Unsupported or corrupt files return a readable error, never a crash.
- Users can change a detected chord and export the corrected progression.
- Tests cover chord-template scoring, segment merging, and export formatting.
- The packaged app opens on Windows and can analyze a local WAV fixture.

## Risk

The baseline analyzer will be approximate. It should earn trust by showing timing and confidence, preserving user corrections, and avoiding claims that it can identify an exact guitar voicing from every mixed recording.
