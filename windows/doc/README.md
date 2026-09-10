# EDFViewer

EDFViewer is a Python tool for loading, viewing, preprocessing, analyzing, and exporting physiological signal data from EDF files. The current implementation includes a PyQt6 desktop GUI, a reproducible CLI workflow, reusable analysis APIs, batch plotting scripts, and test coverage for the main data/analysis/export paths.

---

## Implemented features

### EDF data loading

- Load EDF metadata without preloading the full recording.
- Read channel names, sampling rate, duration, sample count, unit labels, and basic measurement metadata.
- Load only a selected channel/time window for analysis, which keeps long EDF files manageable.
- Validate file paths, channel names, time windows, and empty/invalid signal data.
- Provide a legacy `SignalDataset` API for full-file loading, channel selection, cropping, analysis, and plotting.

### Window-based analysis workflow

- Shared `EDFViewerWorkflow` controller used by both GUI and CLI.
- Select a single EDF channel and a time window by start time and duration.
- Add a small context pad around each requested window before preprocessing/analysis.
- Reuse recent analysis results with a two-entry LRU cache keyed by file, channel, window, preprocessing, CWT, and STFT parameters.
- Return structured `AnalysisResult` objects containing raw/derived series, time-frequency maps, features, preprocessing metadata, and cache state.

### Preprocessing

- Optional target sampling rate with anti-aliased downsampling.
- Zero-phase IIR filters:
  - low-pass
  - high-pass
  - band-pass
  - band-stop
- Filter families:
  - Butterworth
  - Chebyshev I
  - Chebyshev II
  - Elliptic
  - Bessel
- Configurable filter order, cutoff frequencies, passband ripple, and stopband attenuation.
- Central parameter validation against sampling rate/Nyquist limits before analysis.

### Time-domain features

- Mean, standard deviation, variance, minimum, and maximum.
- RMS.
- Peak-to-peak amplitude.
- Zero-crossing rate.
- Hjorth activity, mobility, and complexity.

### Frequency-domain features

- Welch power spectral density.
- EEG-style band powers:
  - delta
  - theta
  - alpha
  - beta
  - gamma
- Dominant frequency.
- Spectral centroid.
- STFT spectrogram in dB.
- Configurable STFT window length and spectrogram frequency range.

### PPG / PLETH helpers

- Peak detection for PPG-like signals.
- Per-cycle PPG amplitude.
- Peak-to-peak interval / beat-to-beat interval (PPI/BBI).
- Sample-aligned derived amplitude and BBI series for CWT analysis and GUI display.

### CWT scalogram analysis

- CWT scalograms for:
  - raw signal
  - BBI/PPI-derived series
  - amplitude-derived series
- Supported wavelets in the GUI:
  - `cmor1.5-1.0`
  - `morl`
  - `mexh`
  - custom `haar`
  - `gaus1`
  - `gaus2`
  - `cgau1`
  - `shan0.5-1.0`
- Configurable minimum/maximum frequency and number of scales.
- Custom Haar CWT implementation because PyWavelets does not provide continuous Haar directly.

### PyQt6 GUI

- EDF file picker and channel selector.
- Shows the selected channel's original sampling rate.
- Target sampling rate control with bounds capped by the original channel sampling rate.
- Window start and window length controls.
- Previous/next window navigation.
- On-demand background computation using Qt thread pool workers.
- Two main tabs:
  - **Signal + Scalogram**
  - **Spectrogram**
- Signal view selector:
  - Raw
  - BBI
  - Amplitude
- Linear/log frequency-axis toggle shared by scalogram and spectrogram.
- Wavelet selector for scalogram recomputation.
- Fit XY action for visible plots.
- Manual axis ranges for scalogram and spectrogram.
- Manual color ranges for scalogram and spectrogram.
- Interactive `HistogramLUTWidget` color bars.
- Shared scalogram color range across raw/BBI/amplitude views for easier visual comparison.
- STFT window control in the spectrogram tab.
- Preprocessing filter toolbar with filter enable/type/family/cutoff/order/ripple/attenuation controls.
- Save current GUI tab as PNG.
- Save and load GUI analysis sessions as JSON, including EDF path, channel/window, display, filter, wavelet, axis, color, and tab state.
- Features tab showing the current window's computed feature table.

### CLI workflow

The unified launcher supports GUI and CLI modes:

```bash
python app.py
python app.py --mode gui
python app.py --mode cli path/to/file.edf --channel PLETH --start 3600 --length 60 --target-sfreq 16 --export all
python app.py --mode cli path/to/file.edf --channels PLETH,ECG --batch-windows --start 0 --end 3600 --length 60 --step 60 --export csv
```

The CLI path is implemented by `cli/main.py` and the shared `EDFViewerWorkflow`. It supports:

- channel selection by name or zero-based index
- multi-channel selection with `--channels`
- all-channel selection with `--all-channels`
- window start and length
- repeated batch windows with `--batch-windows`, optional `--end`, and `--step`
- optional target sampling rate
- wavelet, CWT frequency range, and CWT scale count
- STFT window length and spectrogram frequency range
- linear/log frequency-axis mode metadata
- manual color limit parameters
- optional preprocessing filter settings
- output directory selection
- export types: `png`, `csv`, `parameters`, or `all`
- batch feature summary CSV when multiple analyses export CSV

Example:

```bash
python app.py --mode cli samples/A.0007.edf \
  --channel PLETH \
  --start 3600 \
  --length 60 \
  --target-sfreq 16 \
  --wavelet cmor1.5-1.0 \
  --cwt-fmin 0.1 \
  --cwt-fmax 7.5 \
  --stft-window 5 \
  --filter band_pass \
  --filter-low 0.5 \
  --filter-high 8 \
  --export png,csv,parameters \
  -o outputs
```

Legacy/batch scripts are still available:

- `run_analysis.py`: quick time-domain and PSD plotting for the first N channels.
- `run_pleth_scalogram.py`: split a PLETH channel into long windows and save raw/amplitude/scalogram PNGs.
- `run_ppg_window_scalogram.py`: export raw, amplitude, and PPI scalogram PNGs for one selected PPG/PLETH window.

### Export

- Export a full analysis window to PNG:
  - raw + raw scalogram
  - BBI + BBI scalogram
  - amplitude + amplitude scalogram
  - STFT spectrogram
- Export one-row feature CSV.
- Export multi-analysis summary CSV from CLI batch runs.
- Export JSON parameter record containing source, sampling, filtering, CWT, STFT, display, and full parameter values.
- Save GUI session/project JSON for restoring an analysis setup.
- Generate safe output file names based on source file, channel, time window, view/type, and extension.
- GUI can also save the currently visible tab as PNG.

### Visualization helpers

- Display-independent plot-data builders for signal, scalogram, and spectrogram views.
- Time and frequency cropping for visible windows.
- Auto/manual color range calculation.
- Linear/log frequency-axis metadata for downstream renderers.
- Matplotlib-based export rendering for CLI/headless use.
- PyQtGraph rendering for interactive GUI use.

### Validation and error handling

- Dedicated error types for data loading, preprocessing, analysis, parameter validation, and export.
- Dataclass model validation for metadata, channel windows, time-frequency maps, and analysis results.
- Analysis/display parameter validation before compute/export.
- CLI returns non-zero status and clear stderr message on `EDFViewerError`.

### Tests and sample data

- Unit/smoke tests cover:
  - CLI behavior
  - core data models
  - parameter validation and cache behavior
  - data loading/preprocessing
  - workflow computation/export
  - window analysis
  - visualization plot-data builders
  - export writers
  - GUI workflow helpers
  - entrypoints
  - phantom EDF validation
  - real EDF smoke test
- Sample EDF files are included under `samples/`.
- `samples/build_phantom_edf.py` can regenerate the synthetic phantom EDF.

---

## Requirements

- Python >= 3.8
- Dependencies from `requirements.txt`:
  - `mne`
  - `numpy`
  - `scipy`
  - `matplotlib`
  - `PyWavelets`
  - `PyQt6`
  - `pyqtgraph`
  - `pyinstaller`

Install:

```bash
pip install -r requirements.txt
```

---

## Project structure

```text
EDFViewer/
├── app.py                       # Unified launcher: GUI by default, CLI with --mode cli
├── gui_pyqt6.py                 # PyQt6 + PyQtGraph desktop GUI
├── cli/main.py                  # Reproducible CLI workflow
├── core/
│   ├── cache.py                 # Small LRU analysis cache
│   ├── errors.py                # Project-specific exceptions
│   ├── models.py                # Shared dataclass models
│   ├── parameters.py            # Analysis/display parameters and validation
│   └── workflow.py              # Shared load/compute/export controller
├── data/
│   ├── edf_reader.py            # Metadata and windowed EDF loading
│   ├── edf_viewer.py            # Older EDF helper utilities
│   └── signal_dataset.py        # Legacy full-file SignalDataset API
├── preprocessing/
│   ├── downsample.py            # Anti-aliased downsampling
│   ├── filter.py                # IIR filter implementations
│   └── pipeline.py              # Window preprocessing pipeline
├── analysis/
│   ├── time_domain.py           # Time-domain features
│   ├── freq_domain.py           # PSD, bands, spectrogram, CWT
│   ├── ppg.py                   # PPG amplitude and PPI/BBI helpers
│   └── window_analysis.py       # Window-level analysis composition
├── visualization/plot_data.py   # Renderer-independent plot-data builders
├── export/writers.py            # PNG/CSV/JSON exporters
├── run_analysis.py              # Legacy quick plotting script
├── run_pleth_scalogram.py       # PLETH batch scalogram script
├── run_ppg_window_scalogram.py  # Single-window PPG/PLETH export script
├── samples/                     # Sample and phantom EDF data
├── tests/                       # Pytest suite
├── packaging/macos.md           # macOS packaging notes
└── EDFViewer.spec               # PyInstaller spec
```

---

## Python API examples

Shared workflow API:

```python
from core.parameters import AnalysisParameters
from core.workflow import EDFViewerWorkflow

workflow = EDFViewerWorkflow(cache_size=2)
metadata = workflow.load_file("samples/A.0007.edf")

params = AnalysisParameters(
    target_sfreq=16.0,
    window_start_s=3600.0,
    window_length_s=60.0,
    wavelet="cmor1.5-1.0",
    scalogram_fmin_hz=0.1,
    scalogram_fmax_hz=7.5,
    stft_window_s=5.0,
    spectrogram_fmin_hz=0.1,
    spectrogram_fmax_hz=7.5,
    filter_enabled=True,
    filter_type="band_pass",
    low_cut_hz=0.5,
    high_cut_hz=8.0,
)

result = workflow.compute_window("PLETH", params)
export = workflow.export_result(
    result,
    {"output_dir": "outputs", "types": ["png", "csv", "parameters"]},
)
```

Batch CLI example:

```bash
python app.py --mode cli samples/phantom.edf \
  --channels sine,chirp \
  --batch-windows \
  --start 0 \
  --end 30 \
  --length 5 \
  --step 5 \
  --cwt-scales 8 \
  --export csv \
  -o outputs/batch
```

Legacy `SignalDataset` API:

```python
from data import SignalDataset

dataset = SignalDataset("samples/A.0007.edf")
dataset.summary()
dataset.select_channels(["PLETH"])
dataset.crop(tmin=0, tmax=60)
dataset.downsample(16.0)
dataset.apply_filter("band_pass", low_cut=0.5, high_cut=8.0)

time_features = dataset.time_features()
freq_features = dataset.freq_features()
peak_times, ppi = dataset.ppi("PLETH")

dataset.plot(n_channels=1, savepath="time.png", show=False)
dataset.plot_psd(n_channels=1, fmax=20, savepath="psd.png", show=False)
dataset.plot_spectrogram(channel=0, fmax=20)
dataset.plot_scalogram(channel=0, fmin=0.1, fmax=8.0)
```

---

## Packaging

The repository includes `EDFViewer.spec` and `packaging/macos.md` for PyInstaller-based packaging. The app currently uses `app.py` as the unified entrypoint.

Typical commands:

```bash
pyinstaller --noconfirm EDFViewer.spec
```

or:

```bash
pyinstaller --noconfirm --onefile --windowed --name EDFViewer app.py
pyinstaller --noconfirm --onefile --name EDFViewerCLI app.py
```

---

## Notes

- `doc/README.md` describes the current root-level implementation.
- `versions/cli_version` and `versions/gui_version` are older frozen copies kept for reference.
- The codebase still contains both the newer workflow-based path and older script/API entrypoints; prefer `app.py --mode cli` or the GUI for current workflows.
