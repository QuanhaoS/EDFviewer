# EDFViewer for Windows

This directory is a Windows-ready copy of the EDFViewer application from `mac/`.
It keeps the same Python GUI and CLI behavior while adding Windows launchers,
Windows packaging instructions, and CI packaging through GitHub Actions.

## Run from source

```powershell
cd windows
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python samples\build_phantom_edf.py
python app.py --mode gui
```

CLI smoke run:

```powershell
python app.py --mode cli samples\phantom.edf --channel sine --start 0 --length 5 --cwt-scales 8 --export csv,parameters -o outputs\smoke
```

## Build executable

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The portable executable is created at:

```text
dist\EDFViewer\EDFViewer.exe
```

GitHub Actions also builds the same package on `windows-latest` and uploads it
as the `EDFViewer-Windows` artifact.
