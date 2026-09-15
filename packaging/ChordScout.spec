# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = Path(SPECPATH).parent

# Collect all binaries, data, and hidden imports for scientific/Qt libraries
librosa_datas, librosa_binaries, librosa_hidden = collect_all("librosa")
scipy_datas, scipy_binaries, scipy_hidden = collect_all("scipy")

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "demo" / "classic_pop_progression.mp3"), "demo"),
] + librosa_datas + scipy_datas

binaries = librosa_binaries + scipy_binaries

hidden_imports = (
    [
        "PySide6.QtMultimedia",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "audioread",
        "soundfile",
        "librosa",
        "numpy",
        "scipy",
        "scipy.ndimage",
        "scipy.signal",
        "scipy.special",
        "lazy_loader",
        "chordscout",
        "chordscout.analyzer",
        "chordscout.audio",
        "chordscout.guitar",
        "chordscout.models",
        "chordscout.export",
        "chordscout.synth",
        "chordscout.transposer",
        "chordscout.theme",
        "chordscout.widgets",
        "chordscout.widgets.chord_grid_view",
        "chordscout.widgets.drop_overlay",
        "chordscout.widgets.fretboard_widget",
        "chordscout.widgets.hud_transport",
        "chordscout.widgets.waveform_timeline",
    ]
    + librosa_hidden
    + scipy_hidden
)

a = Analysis(
    [str(ROOT / "src" / "chordscout" / "app.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "notebook", "test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ChordScout",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "chordscout.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ChordScout",
)
