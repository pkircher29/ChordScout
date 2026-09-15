"""Generate demo MP3 audio file with C - G - Am - F progression."""

from pathlib import Path
import numpy as np
import soundfile as sf


def generate_demo():
    sr = 44100
    t = np.linspace(0, 3, sr * 3, endpoint=False)
    # C major (C4, E4, G4)
    c_chord = np.sin(2 * np.pi * 261.63 * t) + np.sin(2 * np.pi * 329.63 * t) + np.sin(2 * np.pi * 392.00 * t)
    # G major (G3, B3, D4)
    g_chord = np.sin(2 * np.pi * 196.00 * t) + np.sin(2 * np.pi * 246.94 * t) + np.sin(2 * np.pi * 293.66 * t)
    # A minor (A3, C4, E4)
    am_chord = np.sin(2 * np.pi * 220.00 * t) + np.sin(2 * np.pi * 261.63 * t) + np.sin(2 * np.pi * 329.63 * t)
    # F major (F3, A3, C4)
    f_chord = np.sin(2 * np.pi * 174.61 * t) + np.sin(2 * np.pi * 220.00 * t) + np.sin(2 * np.pi * 261.63 * t)

    audio = np.concatenate([c_chord, g_chord, am_chord, f_chord])
    audio /= np.max(np.abs(audio))

    out_dir = Path("demo")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "classic_pop_progression.mp3"
    sf.write(str(out_path), audio, sr, format="MP3")
    print(f"Created demo MP3: {out_path.resolve()}")


if __name__ == "__main__":
    generate_demo()
