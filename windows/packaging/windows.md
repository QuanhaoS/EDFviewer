# EDFViewer Windows Packaging

Current packaging target: Windows portable PyInstaller onedir build.

## Prerequisites

- Windows 10 or later
- Python 3.12
- PowerShell

## Build

From this directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The script installs dependencies, builds `samples\phantom.edf`, runs the test
suite, and creates:

```text
dist\EDFViewer\EDFViewer.exe
```

## Manual PyInstaller Command

```powershell
python -m PyInstaller --clean --noconfirm EDFViewer-windows.spec
```

The spec collects MNE package data because MNE uses lazy imports and package
data that PyInstaller does not fully discover by default.

## Validation

Source validation:

```powershell
python samples\build_phantom_edf.py
python -m pytest tests
python app.py --mode cli samples\phantom.edf --channel sine --start 0 --length 5 --cwt-scales 8 --export csv,parameters -o outputs\smoke
```

Packaged CLI validation:

```powershell
dist\EDFViewer\EDFViewer.exe --mode cli samples\phantom.edf --channel sine --start 0 --length 5 --cwt-scales 8 --export csv,parameters -o outputs\packaged-smoke
```

Packaged GUI validation:

```powershell
dist\EDFViewer\EDFViewer.exe --mode gui
```
