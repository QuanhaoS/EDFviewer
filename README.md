# EDFViewer

EDFViewer is a Python desktop and command-line application for loading, viewing, preprocessing, analyzing, and exporting physiological signals stored in European Data Format (EDF) files.

This repository contains two platform trees:

- [`mac/`](mac/) — macOS source and `.app` packaging.
- [`windows/`](windows/) — Windows source, launchers, portable `.exe` packaging, and the latest Windows GUI refinements.

Both versions share the same main analysis workflow. They are separate source copies, however, so a few platform and UI differences exist. Those differences are listed explicitly below.

> EDFViewer is an analysis and visualization tool. It is not a certified medical device and should not be used as the sole basis for clinical decisions.

## Contents

- [Features](#features)
- [macOS and Windows comparison](#macos-and-windows-comparison)
- [Repository structure](#repository-structure)
- [Installation](#installation)
- [Quick start](#quick-start)
- [GUI guide](#gui-guide)
- [CLI guide](#cli-guide)
- [Exports](#exports)
- [Python API](#python-api)
- [Testing](#testing)
- [Packaging](#packaging)
- [GitHub Actions](#github-actions)
- [Troubleshooting](#troubleshooting)

## Features

### EDF data access

- Reads EDF metadata, channel names, units, sampling rates, duration, sample count, and measurement metadata.
- Loads only the selected channel and time window for an analysis, keeping long recordings manageable.
- Validates file paths, channels, time ranges, sampling settings, and invalid or empty data.
- Retains a legacy `SignalDataset` API for full-file scripts.

### Window-based workflow

- Select channels by name, zero-based index, comma-separated list, or `--all-channels`.
- Analyze one window or repeated batch windows.
- Adds context padding before preprocessing to reduce edge effects in the requested output window.
- Reuses recent results through a two-entry LRU cache keyed by file, channel, window, preprocessing, CWT, and STFT parameters.
- Returns structured `AnalysisResult` objects with source metadata, series, time-frequency maps, features, and parameters.

### Preprocessing

- Optional anti-aliased downsampling.
- Zero-phase IIR low-pass, high-pass, band-pass, and band-stop filters.
- Butterworth, Chebyshev I, Chebyshev II, elliptic, and Bessel families.
- Configurable cutoffs, order, passband ripple, and stopband attenuation.
- Validation against the effective sampling rate and Nyquist limit.

### Analysis

- Mean, standard deviation, variance, minimum, maximum, RMS, and peak-to-peak amplitude.
- Zero-crossing rate and Hjorth activity, mobility, and complexity.
- Welch power spectral density.
- Delta, theta, alpha, beta, and gamma band powers.
- Dominant frequency and spectral centroid.
- STFT spectrogram in dB.
- PPG/PLETH peak detection, per-cycle amplitude, and PPI/BBI.
- CWT scalograms for raw, amplitude-derived, and BBI/PPI-derived signals.
- GUI wavelets: `cmor1.5-1.0`, `morl`, `mexh`, custom `haar`, `gaus1`, `gaus2`, `cgau1`, and `shan0.5-1.0`.

### GUI and CLI

- PyQt6 and PyQtGraph interactive desktop GUI.
- Reproducible CLI for headless and batch operation.
- Raw, BBI, and Amplitude views.
- Linear/log frequency display.
- Manual plot axes and color limits.
- Interactive HistogramLUT color bars.
- PNG, feature CSV, parameter JSON, and batch-summary CSV exports.
- GUI session save/load as JSON.

## macOS and Windows comparison

### What is the same

| Capability | macOS | Windows |
|---|---:|---:|
| Unified `app.py` GUI/CLI launcher | Yes | Yes |
| PyQt6 + PyQtGraph GUI | Yes | Yes |
| Windowed EDF loading | Yes | Yes |
| Downsampling and IIR filtering | Yes | Yes |
| Time- and frequency-domain features | Yes | Yes |
| PPG/PLETH amplitude and PPI/BBI | Yes | Yes |
| CWT scalograms and STFT spectrograms | Yes | Yes |
| Linear/log frequency axes | Yes | Yes |
| Manual plot axes and color limits | Yes | Yes |
| PNG, CSV, and JSON export | Yes | Yes |
| Single-channel and batch CLI | Yes | Yes |
| Session save/load | Yes | Yes |
| Pytest suite | Yes | Yes |
| PyInstaller packaging | Yes | Yes |

The data models, preprocessing, analysis modules, CLI, exporters, visualization-data builders, and most tests are currently identical between the two trees.

### What is different

| Topic | macOS | Windows |
|---|---|---|
| Package format | `dist/EDFViewer.app` | `dist/EDFViewer/EDFViewer.exe` with `_internal/` dependencies |
| Recommended packaging file | `mac/EDFViewer.spec` | `windows/EDFViewer-windows.spec` |
| Convenience launchers | Run `python3 app.py` | `run_gui.bat` and `run_cli.bat` |
| Build helper | Manual PyInstaller command | `build_windows.ps1` |
| CI build | No macOS workflow is included | Windows GitHub Actions workflow included |
| Raw signal line | White | Blue |
| Color-bar Auto buttons | Not present | Separate Scalogram and Spectrogram **Auto** buttons |
| Scalogram automatic color range | Shared minimum/maximum across Raw, BBI, and Amplitude | P1–P98 of the currently displayed image |
| Spectrogram automatic color range | Peak-relative 80 dB range | P1–P98 of the currently displayed image |
| Matplotlib temporary directory | macOS `/tmp` path | `tempfile.gettempdir()` Windows-safe path |
| Requirements | Runtime and packaging packages | Also declares `pytest` and `edfio` |
| Phantom sine channel | Preserves a compatible existing signal, or creates a new 1 Hz sine | Deterministic piecewise sine used by Windows validation |
| Historical snapshots | `mac/versions/` contains older CLI/GUI copies | No equivalent duplicate tree |

PyInstaller output is platform-specific: build a macOS `.app` on macOS and a Windows `.exe` on Windows.

The two directories are separate copies. Changes to one are not synchronized automatically. The Windows GUI currently contains the newest color-display changes.

## Repository structure

```text
EDFViewer/
├── README.md
├── .github/workflows/windows-build.yml
├── mac/
│   ├── app.py
│   ├── gui_pyqt6.py
│   ├── EDFViewer.spec
│   ├── packaging/macos.md
│   ├── versions/                  # Archived older variants
│   └── ...
└── windows/
    ├── app.py
    ├── gui_pyqt6.py
    ├── build_windows.ps1
    ├── run_gui.bat
    ├── run_cli.bat
    ├── EDFViewer-windows.spec
    ├── packaging/windows.md
    └── ...
```

Each platform directory uses the following main layout:

```text
app.py                              # GUI/CLI dispatcher
gui_pyqt6.py                        # Interactive GUI
cli/main.py                         # CLI and batch runner
core/                               # Models, parameters, cache, workflow, errors
data/                               # EDF readers and legacy SignalDataset
preprocessing/                      # Downsampling and filtering
analysis/                           # Features, PSD, STFT, CWT, PPG helpers
visualization/plot_data.py          # Renderer-independent plot data
export/writers.py                   # PNG, CSV, and JSON output
samples/build_phantom_edf.py        # Synthetic EDF generator
tests/                              # Pytest suite
```

## Installation

Clone the repository:

```bash
git clone https://github.com/QuanhaoS/EDFviewer.git
cd EDFviewer
```

### Windows

Python 3.12 is the tested Windows build version.

```powershell
cd windows
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, either run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

or invoke `.\.venv\Scripts\python.exe` directly.

### macOS

```bash
cd mac
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

The macOS requirements file does not currently list the test/sample dependencies. Install them when running tests or generating the phantom EDF:

```bash
python3 -m pip install pytest edfio
```

## Quick start

### Generate sample data

EDF files under `samples/` are ignored by Git. Generate the synthetic file after cloning.

Windows:

```powershell
cd windows
python samples\build_phantom_edf.py
```

macOS:

```bash
cd mac
python3 samples/build_phantom_edf.py
```

The resulting `samples/phantom.edf` contains `sine` and `chirp` channels for examples and tests.

### Run the GUI from source

Windows:

```powershell
cd windows
python app.py --mode gui
```

You may also double-click `run_gui.bat`.

macOS:

```bash
cd mac
python3 app.py --mode gui
```

GUI mode is the default, so `python app.py` also works.

### Run a packaged application

Windows PowerShell:

```powershell
& ".\dist\EDFViewer\EDFViewer.exe" --mode gui
```

Keep the complete `dist/EDFViewer/` directory; the executable needs `_internal/`.

macOS:

```bash
open dist/EDFViewer.app
```

or:

```bash
dist/EDFViewer.app/Contents/MacOS/EDFViewer --mode gui
```

## GUI guide

1. Click **Browse EDF...** and select an EDF file.
2. Select a channel.
3. Set target sampling rate, window start, and window length.
4. Optionally configure filtering and click **Apply Filter**.
5. Select a wavelet.
6. Click **Compute current window**.
7. Navigate with **Prev** and **Next**.

The result tabs are:

- **Signal + Scalogram** — Raw, BBI, or Amplitude series with its CWT map.
- **Spectrogram** — STFT spectrogram and color bar.
- **Features** — computed feature values for the current window.

Other controls include STFT window length, linear/log frequency display, Fit XY, manual axes, manual color limits, plot PNG export, and session save/load.

### Windows Auto color range

The Windows Scalogram and Spectrogram panels include an **Auto** button. It uses finite values from the currently displayed image:

```text
color minimum = 1st percentile (P1)
color maximum = 98th percentile (P98)
```

This suppresses extreme outliers. Clicking **Auto** exits manual color mode, synchronizes the Min/Max fields, and updates the color bar immediately.

## CLI guide

CLI mode uses the same workflow as the GUI.

### Basic example

Windows PowerShell:

```powershell
python app.py --mode cli samples\phantom.edf `
  --channel sine --start 0 --length 5 --cwt-scales 8 `
  --export csv,parameters -o outputs\smoke
```

macOS:

```bash
python3 app.py --mode cli samples/phantom.edf \
  --channel sine --start 0 --length 5 --cwt-scales 8 \
  --export csv,parameters -o outputs/smoke
```

### Channel selection

Use exactly one:

```text
--channel PLETH             channel name
--channel-index 0           zero-based channel index
--channels PLETH,ECG        multiple channel names
--all-channels              every EDF channel
```

### Batch windows

```bash
python app.py --mode cli recording.edf \
  --channels PLETH,ECG \
  --batch-windows --start 0 --end 3600 --length 60 --step 60 \
  --export csv,parameters -o outputs/batch
```

Multiple CSV analyses also create `batch_features.csv` by default. Change its name with `--summary-csv`.

### Filtering

```bash
python app.py --mode cli recording.edf \
  --channel PLETH --start 3600 --length 60 --target-sfreq 16 \
  --filter band_pass --filter-low 0.5 --filter-high 7.5 \
  --filter-family butter --filter-order 4 \
  --export all -o outputs/filtered
```

### Main options

| Option | Meaning | Default |
|---|---|---:|
| `--start` | Window start in seconds | `0` |
| `--length` | Window length in seconds | `60` |
| `--batch-windows` | Analyze repeated windows | Off |
| `--end` | Batch stop time | Recording end |
| `--step` | Time between window starts | `--length` |
| `--target-sfreq` | Optional target sampling rate | Original rate |
| `--wavelet` | CWT wavelet | `cmor1.5-1.0` |
| `--cwt-fmin` | CWT minimum frequency | `0.1` Hz |
| `--cwt-fmax` | CWT maximum frequency | Valid maximum |
| `--cwt-scales` | CWT scale count | `64` |
| `--stft-window` | STFT window length | `5` s |
| `--spectrogram-fmin` | Spectrogram minimum | `0` Hz |
| `--spectrogram-fmax` | Spectrogram maximum | Valid maximum |
| `--freq-axis` | `linear` or `log` metadata | `linear` |
| `--filter` | Filter type | `none` |
| `--filter-family` | IIR family | `butter` |
| `--export` | `png`, `csv`, `parameters`, or `all` | All supported outputs |
| `-o`, `--outdir` | Output directory | `outputs` |

Show every option:

```bash
python app.py --mode cli --help
```

For packaged Windows CLI usage, replace `python app.py` with `.\dist\EDFViewer\EDFViewer.exe`.

## Exports

### PNG

A full analysis can export:

- raw signal and raw scalogram;
- BBI series and BBI scalogram;
- amplitude series and amplitude scalogram;
- STFT spectrogram.

### CSV

- A single analysis produces a one-row feature CSV.
- Multi-analysis CLI runs can also produce a summary CSV.

### Parameter JSON

The parameter record contains source/channel/window information, sampling settings, filter configuration, CWT/STFT settings, display settings, and serialized analysis parameters.

## Python API

Run this example from either platform directory:

```python
from core.parameters import AnalysisParameters
from core.workflow import EDFViewerWorkflow

workflow = EDFViewerWorkflow(cache_size=2)
metadata = workflow.load_file("samples/phantom.edf")

params = AnalysisParameters(
    target_sfreq=50.0,
    window_start_s=0.0,
    window_length_s=10.0,
    wavelet="cmor1.5-1.0",
    scalogram_fmin_hz=0.1,
    scalogram_fmax_hz=10.0,
    scalogram_n_scales=32,
    stft_window_s=5.0,
    spectrogram_fmin_hz=0.1,
    spectrogram_fmax_hz=10.0,
)

result = workflow.compute_window("sine", params)
exported = workflow.export_result(
    result,
    {"output_dir": "outputs/api", "types": ["png", "csv", "parameters"]},
)

print(metadata.channel_names)
print(result.features)
print(exported)
```

## Testing

Generate the phantom EDF first.

Windows:

```powershell
cd windows
python samples\build_phantom_edf.py
python -m pytest tests
```

macOS:

```bash
cd mac
python3 samples/build_phantom_edf.py
python3 -m pytest tests
```

Tests cover the CLI, entrypoints, data models, parameters, cache, EDF loading, preprocessing, analysis, exports, visualization helpers, GUI workflow, and phantom validation. The real-EDF smoke test is skipped when its external sample is unavailable.

## Packaging

### Windows

From `windows/`:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

or:

```powershell
python -m PyInstaller --clean --noconfirm EDFViewer-windows.spec
```

Output:

```text
windows/dist/EDFViewer/EDFViewer.exe
```

Packaged smoke test:

```powershell
.\dist\EDFViewer\EDFViewer.exe --mode cli samples\phantom.edf `
  --channel sine --start 0 --length 5 --cwt-scales 8 `
  --export csv,parameters -o outputs\packaged-smoke
```

Distribute the complete `dist/EDFViewer/` directory, not the `.exe` alone.

### macOS

From `mac/`:

```bash
python3 -m PyInstaller --clean --noconfirm EDFViewer.spec
```

The detailed packaging guide also provides this explicit build:

```bash
PYINSTALLER_CONFIG_DIR=/private/tmp/edfviewer-pyinstaller-config \
python3 -m PyInstaller --clean --noconfirm --windowed \
  --name EDFViewer --collect-all mne \
  --add-data samples/phantom.edf:samples app.py
```

Output:

```text
mac/dist/EDFViewer.app
```

See [`mac/packaging/macos.md`](mac/packaging/macos.md) and [`windows/packaging/windows.md`](windows/packaging/windows.md).

## GitHub Actions

`.github/workflows/windows-build.yml` runs on pushes to `main`, pull requests, and manual dispatches. It:

1. uses a Windows runner and Python 3.12;
2. installs dependencies;
3. generates `samples/phantom.edf`;
4. runs the Windows tests;
5. builds `EDFViewer-windows.spec`;
6. uploads `windows/dist/EDFViewer/` as the `EDFViewer-Windows` artifact.

Download a CI build from a successful **Windows Build** run on the repository's **Actions** page.

## Troubleshooting

### Missing `samples/phantom.edf`

Run `samples/build_phantom_edf.py`. EDF samples are intentionally ignored by Git.

### PowerShell cannot activate `.venv`

Use `Set-ExecutionPolicy -Scope Process Bypass`, or call `.venv\Scripts\python.exe` directly.

### `DLL load failed while importing QtCore` during Windows packaging

Check `PATH` for unrelated Qt, ICU, or Poppler DLL directories. PyInstaller can collect incompatible DLLs from an externally modified `PATH`. Build from a clean terminal and rebuild with `--clean`.

### GUI dependencies are missing

```bash
python -m pip install -r requirements.txt
```

The GUI requires both `PyQt6` and `pyqtgraph`.

### Channel name is rejected

Channel names must match the EDF labels exactly. Inspect the GUI selector, use `--all-channels`, or select with `--channel-index`.

### Filter settings are rejected

Cutoffs must be positive, correctly ordered for band filters, and below the Nyquist frequency after target-rate selection.

### Packaged app does not contain recent edits

Rebuild after changing source. PyInstaller does not update an existing package automatically.

## Implementation notes

- MNE provides EDF I/O and signal support.
- NumPy and SciPy provide numerical analysis, filtering, PSD, STFT, and features.
- PyWavelets provides CWT wavelets; the project includes a custom Haar path.
- Matplotlib renders headless exports.
- PyQt6 and PyQtGraph render the interactive GUI.
- PyInstaller creates platform-native packages.
- Dependencies use minimum-version constraints rather than a lock file, so exact versions can vary.
- Linux source execution may work with compatible dependencies, but no Linux package or CI workflow is currently included.
- Shared behavior must be updated and tested in both platform trees manually.
