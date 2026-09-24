; NSIS Installer Script for ChordScout
!include "MUI2.nsh"
!include "FileFunc.nsh"

; General Definitions
Name "ChordScout"
OutFile "..\dist\ChordScout_Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\ChordScout"
InstallDirRegKey HKCU "Software\ChordScout" "InstallDir"
RequestExecutionLevel user

; Interface Configuration
!define MUI_ICON "..\assets\chordscout.ico"
!define MUI_UNICON "..\assets\chordscout.ico"
!define MUI_HEADERIMAGE
!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Finish Page with Run Checkbox
!define MUI_FINISHPAGE_RUN "$INSTDIR\ChordScout.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ChordScout"
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

Section "ChordScout Core" SecCore
    SectionIn RO

    ; Output folder
    SetOutPath "$INSTDIR"

    ; Copy compiled bundle
    File /r "..\dist\ChordScout\*.*"

    ; Store installation folder
    WriteRegStr HKCU "Software\ChordScout" "InstallDir" "$INSTDIR"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Windows Add/Remove Programs Registration
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ChordScout" "DisplayName" "ChordScout - Guitar Chord Analyzer"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ChordScout" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ChordScout" "DisplayIcon" '"$INSTDIR\ChordScout.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ChordScout" "Publisher" "pkircher29"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ChordScout" "DisplayVersion" "0.2.0"

    ; Shortcuts
    CreateDirectory "$SMPROGRAMS\ChordScout"
    CreateShortcut "$SMPROGRAMS\ChordScout\ChordScout.lnk" "$INSTDIR\ChordScout.exe" "" "$INSTDIR\ChordScout.exe" 0
    CreateShortcut "$SMPROGRAMS\ChordScout\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0
    CreateShortcut "$DESKTOP\ChordScout.lnk" "$INSTDIR\ChordScout.exe" "" "$INSTDIR\ChordScout.exe" 0

    ; Explorer Context Menu ("Open with ChordScout" on audio files)
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.mp3\shell\ChordScout" "" "Analyze with ChordScout"
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.mp3\shell\ChordScout" "Icon" '"$INSTDIR\ChordScout.exe"'
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.mp3\shell\ChordScout\command" "" '"$INSTDIR\ChordScout.exe" "%1"'

    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.wav\shell\ChordScout" "" "Analyze with ChordScout"
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.wav\shell\ChordScout" "Icon" '"$INSTDIR\ChordScout.exe"'
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.wav\shell\ChordScout\command" "" '"$INSTDIR\ChordScout.exe" "%1"'

    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.flac\shell\ChordScout" "" "Analyze with ChordScout"
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.flac\shell\ChordScout" "Icon" '"$INSTDIR\ChordScout.exe"'
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.flac\shell\ChordScout\command" "" '"$INSTDIR\ChordScout.exe" "%1"'

    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.m4a\shell\ChordScout" "" "Analyze with ChordScout"
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.m4a\shell\ChordScout" "Icon" '"$INSTDIR\ChordScout.exe"'
    WriteRegStr HKCU "Software\Classes\SystemFileAssociations\.m4a\shell\ChordScout\command" "" '"$INSTDIR\ChordScout.exe" "%1"'
SectionEnd

Section "Uninstall"
    ; Remove Context Menu
    DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.mp3\shell\ChordScout"
    DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.wav\shell\ChordScout"
    DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.flac\shell\ChordScout"
    DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\.m4a\shell\ChordScout"

    ; Remove Add/Remove Programs
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\ChordScout"
    DeleteRegKey HKCU "Software\ChordScout"

    ; Remove Shortcuts
    Delete "$DESKTOP\ChordScout.lnk"
    Delete "$SMPROGRAMS\ChordScout\*.*"
    RMDir "$SMPROGRAMS\ChordScout"

    ; Remove Files
    RMDir /r "$INSTDIR"
SectionEnd
