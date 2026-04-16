# EDFReader

Physiological signal analysis: EDF loading, downsampling, filtering, time/frequency-domain analysis, PPG-derived features (amplitude, PPI), and visualization (matplotlib CLI tools + PyQt6 GUI).

---

## Features

- **Data loading**: Read EDF into `SignalDataset`; channel selection, time cropping, antialiased downsampling
- **Preprocessing**: Butterworth filters (low-pass, high-pass, band-pass); `preprocessing.downsample` for rate reduction
- **Time-domain analysis**: Basic stats, RMS, peak-to-peak, zero-crossing rate, Hjorth parameters, etc.
- **Frequency-domain analysis**: Welch PSD, band powers (delta/theta/alpha/beta/gamma), dominant frequency, spectral centroid, spectrogram, CWT scalogram
- **PPG helpers**: Per-beat amplitude and peak-to-peak interval (PPI), used by GUI and batch scripts
- **Visualization**: Time traces, PSD, spectrogram, scalogram; PNG export from CLI and GUI

---

## Requirements

- Python ≥ 3.8
- Dependencies in `requirements.txt` (includes GUI: PyQt6, pyqtgraph)

---

## Installation

```bash
cd EDFReader
pip install -r requirements.txt
```

Provide your own EDF path if `samples/A.0007.edf` is not present (that path is only the default in some scripts).

---

## Project structure

```
EDFReader/
├── app.py                    # Unified entry: --mode gui (default) or --mode cli
├── gui_pyqt6.py              # PyQt6 + PyQtGraph GUI (loaded by app.py)
├── run_analysis.py           # CLI: time + PSD plots (same args as app.py --mode cli)
├── run_pleth_scalogram.py    # CLI: PLETH windows → raw + amplitude + scalogram PNGs
├── run_ppg_window_scalogram.py  # CLI: one time window → 3 PNGs (raw / amp / PPI + scalograms)
├── data/
│   ├── edf_viewer.py         # Simple EDF load + plot helpers
│   └── signal_dataset.py     # SignalDataset (load, crop, filter, downsample, analyze, plot)
├── preprocessing/
│   ├── filter.py             # low_pass, high_pass, band_pass
│   └── downsample.py         # antialiased downsampling
├── analysis/
│   ├── time_domain.py
│   ├── freq_domain.py        # PSD, spectrogram, CWT, band powers, ...
│   └── ppg.py                # compute_ppg_amplitude, compute_ppi
├── requirements.txt
├── versions/                 # Frozen cli_version / gui_version copies (see versions/README.md)
└── figures/                  # Typical output dir for saved PNGs (created on demand)
```

---

## Usage

### 1. Unified launcher (`app.py`)

```bash
# GUI (default): pick EDF, channel, window length/index, then compute per window
python app.py
python app.py --mode gui

# CLI: same behavior as run_analysis.py
python app.py --mode cli
python app.py --mode cli path/to/file.edf -n 3 -t 60 --fmax 50 --save
```

GUI (`gui_pyqt6.py`): five tabs — Raw + PPG amplitude (step), PPI + PPI scalogram, raw scalogram, amplitude scalogram, spectrogram (dB). **Window length** and **Window index** select a segment; **Compute current window** runs analysis for that segment only (LRU cache for the last two windows). **Save current Tab PNG** exports the visible tab.

Headless smoke test (if your environment needs it):

```bash
QT_QPA_PLATFORM=offscreen python app.py --mode gui
```

### 2. Command line: general EDF (`run_analysis.py`)

```bash
python run_analysis.py
python run_analysis.py path/to/file.edf -n 3 -t 60 --fmax 50
python run_analysis.py path/to/file.edf --save -o figures --no-show
```

| Argument | Description |
|----------|-------------|
| `edf_path` | EDF file (optional; default `samples/A.0007.edf` if that file exists) |
| `-n, --channels` | Number of channels to plot |
| `-t, --tmax` | Use only `[0, tmax]` seconds |
| `--fmax` | Max frequency (Hz) on PSD plot |
| `-s, --save` | Save time-domain and PSD figures |
| `-o, --outdir` | Output directory (default `figures`) |
| `--no-show` | Do not open plot windows (useful with `--save`) |

### 3. PLETH / PPG batch scripts

**Long recording, fixed windows** (`run_pleth_scalogram.py`): keep one channel (default `PLETH`), downsample to 16 Hz, split into windows (default 1 hour, or `--window-min` minutes), each window saved as one PNG (raw + per-beat amplitude + scalogram).

```bash
python run_pleth_scalogram.py path/to/file.edf
python run_pleth_scalogram.py path/to/file.edf -w 2 -o figures/pleth
python run_pleth_scalogram.py path/to/file.edf --window-min 1.2 --segment 60 -o figures/pleth
```

**Single window, three figures** (`run_ppg_window_scalogram.py`): crop `[tstart, tstart+tlen]`, downsample, then write three PNGs (raw+scalogram, amplitude+scalogram, PPI+scalogram).

```bash
python run_ppg_window_scalogram.py path/to/file.edf \
  -c PLETH --target-hz 16 --tstart 3600 --tlen 60 -o figures/ppg_window
```

---

## Alternate copies (`versions/`)

`versions/cli_version` and `versions/gui_version` are self-contained copies with the same layout; see `versions/README.md` for how to run each.

---

## Packaging executables

Use `app.py` as the single entrypoint so GUI and CLI share one file.

```bash
pip install pyinstaller PyQt6 pyqtgraph
pyinstaller --noconfirm --onefile --windowed --name EDFReader app.py
pyinstaller --noconfirm --onefile --name EDFReaderCLI app.py
```

- GUI: `dist/EDFReader`
- CLI: `dist/EDFReaderCLI --mode cli [edf_path] [options]`

---

## Python API

```python
from data import SignalDataset

dataset = SignalDataset("path/to/file.edf")
dataset.summary()

dataset.select_channels(["PLETH"])
dataset.crop(tmin=0, tmax=30)
dataset.downsample(16.0)  # if original rate > 16 Hz
dataset.apply_filter("band_pass", low_cut=1, high_cut=40)

td = dataset.time_features()
fd = dataset.freq_features()

dataset.plot(n_channels=5, savepath="time.png", show=False)
dataset.plot_psd(n_channels=5, fmax=50, savepath="psd.png")
dataset.plot_spectrogram(channel=0, fmax=40)
dataset.plot_scalogram(channel=0, fmin=1, fmax=40)
```

```python
from preprocessing import low_pass, high_pass, band_pass
from preprocessing.downsample import downsample
from analysis import (
    compute_time_features,
    compute_psd,
    cwt_scalogram,
    compute_ppg_amplitude,
    compute_ppi,
    EEG_BANDS,
)
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| mne | EDF reading |
| numpy | Arrays |
| scipy | Filtering, Welch PSD, spectrogram |
| matplotlib | CLI figures |
| PyWavelets | CWT scalogram |
| PyQt6 | GUI |
| pyqtgraph | Fast plots in GUI |

---

## Version note

This README matches the tree at the repository root. Feature additions may also land under `versions/`.
