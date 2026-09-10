# EDFReader (GUI Version)

Physiological signal analysis: EDF file loading, filtering, time/frequency-domain analysis, and visualization.

---

## Features

- **Data loading**: Read EDF files into `SignalDataset`; channel selection and time cropping
- **Preprocessing**: Butterworth filters (low-pass, high-pass, band-pass)
- **Time-domain analysis**: Basic stats, RMS, peak-to-peak, zero-crossing rate, Hjorth parameters, etc.
- **Frequency-domain analysis**: Welch PSD, band powers (delta/theta/alpha/beta/gamma), dominant frequency, spectral centroid, spectrogram, CWT scalogram
- **Visualization**: Time-domain traces, PSD, spectrogram, scalogram; figures can be saved to disk

---

## Requirements

- Python ≥ 3.8
- Dependencies listed in `requirements.txt`

---

## Installation

```bash
cd EDFReader
pip install -r requirements.txt
```

---

## Project structure

```
EDFReader/
├── data/                 # Data and dataset
│   ├── edf_viewer.py     # EDF loading and simple plotting
│   └── signal_dataset.py # SignalDataset (load, filter, analyze, plot)
├── preprocessing/       # Preprocessing
│   └── filter.py       # low_pass, high_pass, band_pass
├── analysis/            # Analysis
│   ├── time_domain.py   # Time-domain features
│   └── freq_domain.py   # Frequency-domain, PSD, CWT scalogram
├── run_analysis.py      # Command-line entry
├── requirements.txt
├── samples/             # Sample EDF files
└── figures/             # Saved figures (optional)
```

---

## Usage

### Command line

```bash
# Default: load samples/A.0007.edf, plot time- and frequency-domain
python run_analysis.py

# Specify EDF file
python run_analysis.py samples/A.0007.edf

# Optional arguments
python run_analysis.py samples/A.0007.edf -n 3 -t 60 --fmax 50

# Save figures to figures/ (default)
python run_analysis.py samples/A.0007.edf --save

# Save to a custom directory, no display
python run_analysis.py samples/A.0007.edf -s -o output --no-show
```

| Argument | Description |
|----------|-------------|
| `edf_path` | Path to EDF file (optional; default: `samples/A.0007.edf`) |
| `-n, --channels` | Number of channels to plot |
| `-t, --tmax` | Analyze only first `tmax` seconds |
| `--fmax` | Maximum frequency (Hz) in PSD plot |
| `-s, --save` | Save time- and frequency-domain figures |
| `-o, --outdir` | Output directory for figures (default: `figures`) |
| `--no-show` | Do not display plots (save only when used with `--save`) |

### Python API

```python
from data import SignalDataset

# Load
dataset = SignalDataset("samples/A.0007.edf")
dataset.summary()

# Crop and filter
dataset.crop(tmin=0, tmax=30)
dataset.apply_filter("band_pass", low_cut=1, high_cut=40)

# Time-domain features
td = dataset.time_features()
# td["mean"], td["rms"], td["mobility"], ...

# Frequency-domain features
fd = dataset.freq_features()
# fd["band_powers"], fd["dominant_frequency"], ...

# Plotting (with optional save)
dataset.plot(n_channels=5, savepath="time.png", show=False)
dataset.plot_psd(n_channels=5, fmax=50, savepath="psd.png")
dataset.plot_spectrogram(channel=0, fmax=40)
dataset.plot_scalogram(channel=0, fmin=1, fmax=40)
```

```python
# Use analysis/preprocessing modules directly
from preprocessing import low_pass, high_pass, band_pass
from analysis import compute_time_features, compute_psd, cwt_scalogram, EEG_BANDS
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| mne | EDF reading |
| numpy | Numerical computation |
| scipy | Filtering, Welch PSD, spectrogram |
| matplotlib | Plotting |
| PyWavelets | CWT scalogram |

---

## Version note

This README describes the current implementation. It will be updated when significant new features are added.
