# ChordScout 🎸

**Local-first chord progression analysis for song files.**

ChordScout is a standalone Windows desktop application and CLI tool where you can drop in any audio file (`.mp3`, `.wav`, `.flac`, `.m4a`, `.ogg`) and immediately extract time-aligned guitar chords, visual fretboard fingerings, and exportable chord sheets.

---

## Features

- **Drag-and-Drop Intake**: Drag an MP3 file directly into the desktop window (or drop it onto `chordscout.bat` in Windows Explorer).
- **Audio Processing**:
  - Harmonic-Percussive Separation (HPSS) to strip out drum noise and isolate harmonic chord tones.
  - Constant-Q Transform (CQT) chromagram tuned to standard concert pitch ($C_2 = 65.4\text{ Hz}$).
  - Automatic tuning offset estimation ($\pm \text{cents}$) for songs tuned slightly sharp or flat.
  - Beat-tracking rhythm synchronization to snap chord changes to musical beats.
  - Key estimation (e.g. C major, G major, A minor).
- **Guitar Chord Diagrams**:
  - Interactive visual fretboard widget displaying finger positions (1=Index, 2=Middle, 3=Ring, 4=Pinky), fret wires, open (`o`) and muted (`x`) strings in standard tuning ($E-A-D-G-B-e$).
- **Synchronized Playback**:
  - Built-in audio player with playhead scrubber.
  - Timeline track showing color-coded chord blocks.
  - Chords and guitar diagrams update in real-time as the song plays.
  - Click anywhere on the timeline to seek playback to that exact measure.
- **Chord Progression Table & Correction**:
  - Chronological segment list with timestamps, durations, and confidence ratings.
  - Double-click to rename any chord (from dropdown or custom input).
  - Right-click context menu: *Change Chord*, *Split Segment in Half*, *Merge with Next*, *Set to Silence*.
- **Multi-Format Export**:
  - **Plain Text (`.txt`)**: Clean chord chart with timestamp ranges and guitar chord reference table.
  - **ChordPro (`.cho`)**: Standard ChordPro format ready for SongBook, OnSong, and chord viewers.
  - **CSV (`.csv`)**: Time-aligned spreadsheet (`start_time, end_time, duration, chord, confidence`).
  - **Project Sidecar (`.chordscout.json`)**: Preserves all audio metadata, segment edits, and custom chords.
  - **Clipboard**: 1-click copy formatted chord chart.
- **Privacy**: 100% local-first and offline. No audio leaves your machine.

---

## Quick Start

### 1. Launch the Desktop App
Double-click `chordscout.bat` or run:
```bash
.venv/Scripts/chordscout
```
Then drag and drop any MP3 or WAV into the window.

### 2. Windows Droplet (Drag-and-Drop)
Drag any audio file directly onto `chordscout.bat` in Windows Explorer. It will:
1. Run chord analysis and print the chord chart in the console.
2. Automatically export `.txt`, `.cho`, `.csv`, and `.chordscout.json` alongside the song.
3. Open the ChordScout visual GUI.

### 3. Command Line Interface (CLI)
```bash
# Analyze a song and view the chord progression in your terminal
chordscout path/to/song.mp3

# Analyze and automatically export all sheet formats (.txt, .cho, .csv, .json)
chordscout path/to/song.mp3 --export-all

# Include 7th chord detection (e.g. G7, Am7, Cmaj7)
chordscout path/to/song.mp3 --7ths
```

---

## Running Tests

ChordScout includes a comprehensive pytest suite covering audio decoding, chord template matching, segment smoothing, guitar diagram rendering, export formatting, and GUI components:

```bash
export QT_QPA_PLATFORM=offscreen
.venv/Scripts/pytest -v
```
