# EDFViewer macOS Packaging

Current packaging target: macOS `.app` bundle built with PyInstaller.

## Prerequisites

Install project dependencies and PyInstaller:

```text
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
```

## Build Command

Use a writable PyInstaller config directory when the default user application-support directory is unavailable:

```text
PYINSTALLER_CONFIG_DIR=/private/tmp/edfviewer-pyinstaller-config \
python3 -m PyInstaller --clean --noconfirm --windowed \
  --name EDFViewer \
  --collect-all mne \
  --add-data samples/phantom.edf:samples \
  app.py
```

The `--collect-all mne` option is required because MNE uses lazy imports and package-data stubs that are not fully collected by the default PyInstaller analysis.

Build output:

```text
dist/EDFViewer.app
```

## Validation Performed

Packaged CLI smoke:

```text
dist/EDFViewer.app/Contents/MacOS/EDFViewer --mode cli \
  samples/phantom.edf \
  --channel sine \
  --start 0 \
  --length 5 \
  --cwt-scales 8 \
  --export csv,parameters \
  -o /private/tmp/edfviewer-packaged-cli-final
```

Result:

- CSV feature export succeeded.
- JSON parameter export succeeded.

Packaged GUI startup smoke:

- `dist/EDFViewer.app/Contents/MacOS/EDFViewer --mode gui` started under `QT_QPA_PLATFORM=offscreen`.
- The process stayed alive for five seconds and was then terminated by the smoke harness.

## Notes

- PyInstaller may print warnings for optional platform libraries such as `user32`, `libX11`, or `pyqtgraph.opengl`/`OpenGL`; these are not required for the current macOS EDFViewer workflow.
- Future Windows and Linux executable packaging remain future scope.
