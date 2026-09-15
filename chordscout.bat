@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
    start "" ".venv\Scripts\pythonw.exe" -m chordscout.cli
) else (
    echo [ChordScout] Analyzing audio: "%~1"
    echo.
    call ".venv\Scripts\python.exe" -m chordscout.cli "%~1" --export-all
    echo.
    echo Launching ChordScout Visual Interface...
    start "" ".venv\Scripts\pythonw.exe" -m chordscout.cli "%~1" --gui
)
