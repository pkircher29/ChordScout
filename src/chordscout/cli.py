"""Command-line interface and droplet handler for ChordScout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chordscout.analyzer import analyze_chords
from chordscout.audio import get_audio_info, is_supported_audio_file, load_audio
from chordscout.export import export_chordpro, export_csv, export_plain_text, save_project
from chordscout.models import AnalysisMetadata, AnalysisResult


def analyze_file_cli(
    audio_path: Path,
    include_sevenths: bool = False,
    output_dir: Path | None = None,
    export_all: bool = False,
) -> AnalysisResult:
    """Analyze an audio file from the CLI and display/export results."""
    print(f"\n[ChordScout] Loading: {audio_path.name}")
    info = get_audio_info(audio_path)
    print(f"[ChordScout] Duration: {info['duration']:.1f}s | Sample Rate: {info['sample_rate']}Hz")

    def cli_progress(p: float, msg: str) -> None:
        bar_len = 25
        filled = int(p * bar_len)
        bar = "=" * filled + "-" * (bar_len - filled)
        sys.stdout.write(f"\r[{bar}] {int(p*100):3d}% : {msg:<35}")
        sys.stdout.flush()

    y, sr, duration = load_audio(audio_path)
    segments, metadata_dict = analyze_chords(
        y, sr, include_sevenths=include_sevenths, progress_callback=cli_progress
    )
    print("\n")

    metadata = AnalysisMetadata(
        file_path=str(audio_path.resolve()),
        file_name=audio_path.name,
        duration=duration,
        sample_rate=sr,
        tempo_bpm=metadata_dict.get("tempo_bpm"),
        key_estimate=metadata_dict.get("key_estimate"),
        tuning_offset_cents=metadata_dict.get("tuning_offset_cents", 0.0),
    )

    result = AnalysisResult(metadata=metadata, segments=segments)

    # Print plain text chart to console
    text_chart = export_plain_text(result)
    print(text_chart)

    # Export if requested
    out_dir = output_dir or audio_path.parent
    base_name = audio_path.stem

    if export_all:
        txt_file = out_dir / f"{base_name}_chords.txt"
        txt_file.write_text(text_chart, encoding="utf-8")
        print(f"\n[Exported] Text: {txt_file.name}")

        cho_file = out_dir / f"{base_name}.cho"
        cho_file.write_text(export_chordpro(result), encoding="utf-8")
        print(f"[Exported] ChordPro: {cho_file.name}")

        csv_file = out_dir / f"{base_name}_chords.csv"
        export_csv(result, csv_file)
        print(f"[Exported] CSV: {csv_file.name}")

        json_file = out_dir / f"{base_name}.chordscout.json"
        save_project(result, json_file)
        print(f"[Exported] Sidecar Project: {json_file.name}")

    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="chordscout",
        description="Drop an MP3 into ChordScout to detect and display guitar chords.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Audio file (MP3, WAV, FLAC, M4A) to analyze.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the desktop graphical interface (default if no file provided).",
    )
    parser.add_argument(
        "--7ths",
        dest="sevenths",
        action="store_true",
        help="Include 7th chord templates (e.g. G7, Am7).",
    )
    parser.add_argument(
        "--export-all",
        action="store_true",
        help="Automatically export .txt, .cho, .csv, and .chordscout.json sidecar files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Directory to save exported files.",
    )
    return parser.parse_args(argv)


def run_cli() -> None:
    args = parse_args()
    if args.file and not args.gui:
        if not args.file.exists():
            print(f"Error: File '{args.file}' does not exist.", file=sys.stderr)
            sys.exit(1)
        if not is_supported_audio_file(args.file):
            print(f"Error: Unsupported file format '{args.file.suffix}'.", file=sys.stderr)
            sys.exit(1)

        analyze_file_cli(
            args.file,
            include_sevenths=args.sevenths,
            output_dir=args.output_dir,
            export_all=args.export_all,
        )
    else:
        # Launch GUI
        from chordscout.app import main as launch_gui
        initial_file = str(args.file.resolve()) if args.file and args.file.exists() else None
        launch_gui(initial_file=initial_file)


if __name__ == "__main__":
    run_cli()
