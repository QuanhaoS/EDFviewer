# EDFViewer Detailed Design Document

## 1. Purpose

This document provides the detailed design for EDFViewer based on `Proposal.md` and `Product_Development.md`.

The design expands the high-level modules into implementable components, data structures, module interfaces, workflows, validation rules, error handling rules, and independent test plans.

The current implementation target is one EDF file at a time. Future features are documented only where they affect extensibility.

## 2. Design Principles

The implementation should follow these principles:

- Keep GUI and CLI independent from signal-processing details.
- Keep preprocessing, analysis, visualization, and export modules independently testable.
- Use explicit data models between modules instead of passing GUI widget state or raw CLI arguments through the system.
- Keep current-scope and future-scope features separate.
- Use `BBI` as the only user-facing beat-to-beat interval term.
- Treat all EDF signals as generic channels.
- Analyze selected time windows instead of requiring full-record computation.

## 3. Proposed Package Structure

The current repository already contains `data`, `preprocessing`, `analysis`, GUI, and CLI scripts. The detailed design recommends organizing future implementation around these logical packages. Existing files can be refactored gradually into this structure.

```text
EDFViewer/
├── app.py
├── gui_pyqt6.py
├── cli/
│   ├── __init__.py
│   ├── commands.py
│   └── parsers.py
├── core/
│   ├── __init__.py
│   ├── workflow.py
│   ├── models.py
│   ├── parameters.py
│   ├── cache.py
│   └── errors.py
├── data/
│   ├── __init__.py
│   ├── signal_dataset.py
│   └── edf_reader.py
├── preprocessing/
│   ├── __init__.py
│   ├── downsample.py
│   └── filter.py
├── analysis/
│   ├── __init__.py
│   ├── time_domain.py
│   ├── freq_domain.py
│   ├── ppg.py
│   └── features.py
├── visualization/
│   ├── __init__.py
│   ├── plot_models.py
│   ├── pyqtgraph_views.py
│   └── matplotlib_exports.py
├── export/
│   ├── __init__.py
│   ├── png_export.py
│   ├── csv_export.py
│   └── parameter_export.py
├── packaging/
│   └── macos.md
└── tests/
    ├── test_data_layer.py
    ├── test_preprocessing.py
    ├── test_analysis.py
    ├── test_workflow.py
    ├── test_export.py
    └── test_cli.py
```

This structure is a design target. It does not require moving all existing files immediately.

## 4. Core Data Models

Core data models should live in `core/models.py` and `core/parameters.py`. They should be plain Python objects or dataclasses so they can be tested without GUI or CLI dependencies.

### 4.1 `EDFMetadata`

Purpose:

Represent metadata needed after opening an EDF file.

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `file_path` | `str` | Source EDF file path |
| `file_name` | `str` | Display-safe file name |
| `channel_names` | `list[str]` | EDF channel names |
| `sfreq_by_channel` | `dict[str, float]` or `float` | Sampling rate information |
| `duration_s` | `float` | Recording duration in seconds |
| `n_samples_by_channel` | `dict[str, int]` | Sample count by channel if available |
| `metadata` | `dict` | Additional EDF metadata for export or display |

Validation:

- `file_path` must not be empty.
- `channel_names` must not be empty.
- `duration_s` must be greater than `0`.
- Sampling rate values must be greater than `0`.

Independent tests:

- Load `samples/phantom.edf` and confirm channel names, sampling rate, and duration.
- Reject missing or unreadable EDF files.
- Reject EDF files with no readable channels.

### 4.2 `ChannelWindow`

Purpose:

Represent selected signal data for one EDF channel and one time window.

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `file_path` | `str` | Source EDF path |
| `channel_name` | `str` | Selected channel |
| `window_start_s` | `float` | Window start in seconds |
| `window_length_s` | `float` | Window length in seconds |
| `sfreq` | `float` | Sampling rate of returned signal |
| `times_s` | `np.ndarray` | Time vector relative to window start |
| `signal` | `np.ndarray` | One-dimensional selected channel signal |
| `units` | `str | None` | Optional unit label if known |

Validation:

- `signal` must be one-dimensional.
- `times_s` and `signal` must have the same length.
- `window_start_s >= 0`.
- `window_length_s > 0`.
- `sfreq > 0`.

Independent tests:

- Extract `0-60s` from `samples/phantom.edf`.
- Extract `100-160s` from `samples/phantom.edf`.
- Reject negative window start.
- Reject a window outside the recording duration.

### 4.3 `AnalysisParameters`

Purpose:

Represent all analysis settings shared by GUI and CLI.

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `target_sfreq` | `float | None` | Requested analysis sampling rate |
| `window_start_s` | `float` | Window start |
| `window_length_s` | `float` | Window length |
| `wavelet` | `str` | CWT wavelet name |
| `scalogram_fmin_hz` | `float` | Scalogram minimum frequency |
| `scalogram_fmax_hz` | `float` | Scalogram maximum frequency |
| `scalogram_n_scales` | `int` | Number of CWT scales |
| `stft_window_s` | `float` | STFT window length |
| `spectrogram_fmin_hz` | `float` | Spectrogram minimum display frequency |
| `spectrogram_fmax_hz` | `float` | Spectrogram maximum display frequency |
| `freq_axis_mode` | `Literal["linear", "log"]` | Frequency axis mode |
| `color_range_mode` | `Literal["auto", "manual"]` | Color range mode |
| `color_min` | `float | None` | Manual color minimum |
| `color_max` | `float | None` | Manual color maximum |
| `filter_enabled` | `bool` | Whether filtering is applied |
| `filter_type` | `Literal["low_pass", "high_pass", "band_pass"] | None` | Filter type |
| `low_cut_hz` | `float | None` | Low cut frequency |
| `high_cut_hz` | `float | None` | High cut frequency |
| `filter_order` | `int` | Filter order |

Validation:

- `window_start_s >= 0`.
- `window_length_s > 0`.
- `target_sfreq` is `None` or greater than `0`.
- `scalogram_fmin_hz > 0`.
- `scalogram_fmax_hz > scalogram_fmin_hz`.
- `spectrogram_fmax_hz > spectrogram_fmin_hz`.
- `stft_window_s > 0`.
- `scalogram_n_scales > 0`.
- Manual color range requires `color_max > color_min`.
- Filter frequencies must be valid for the active sampling rate.

Independent tests:

- Validate a default parameter object.
- Reject invalid frequency ranges.
- Reject invalid manual color range.
- Reject invalid filter settings.

### 4.4 `DisplayParameters`

Purpose:

Represent visualization-only settings.

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `active_signal_view` | `Literal["raw", "bbi", "amplitude"]` | Selected signal view |
| `freq_axis_mode` | `Literal["linear", "log"]` | Axis mode |
| `color_range_mode` | `Literal["auto", "manual"]` | Color range mode |
| `color_min` | `float | None` | Color minimum |
| `color_max` | `float | None` | Color maximum |
| `fit_signal_y` | `bool` | Whether the signal Y-axis is fitted |

Independent tests:

- Create display settings for each signal view.
- Validate manual color range.

### 4.5 `AnalysisResult`

Purpose:

Represent all outputs generated for one selected channel and time window.

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `source` | `ChannelWindow` | Input window data |
| `parameters` | `AnalysisParameters` | Parameters used for computation |
| `processed_signal` | `np.ndarray` | Signal after preprocessing |
| `processed_sfreq` | `float` | Sampling rate after preprocessing |
| `times_s` | `np.ndarray` | Time vector |
| `raw_signal` | `np.ndarray` | Raw or processed signal for display |
| `bbi_times_s` | `np.ndarray` | BBI time points |
| `bbi_values_s` | `np.ndarray` | BBI values |
| `amplitude_times_s` | `np.ndarray` | Amplitude time points |
| `amplitude_values` | `np.ndarray` | Amplitude values |
| `raw_scalogram` | `TimeFrequencyMap` | Raw CWT result |
| `bbi_scalogram` | `TimeFrequencyMap` | BBI CWT result |
| `amplitude_scalogram` | `TimeFrequencyMap` | Amplitude CWT result |
| `spectrogram` | `TimeFrequencyMap` | STFT result |
| `features` | `dict` | CSV-compatible feature values |

Independent tests:

- Compute result from `samples/phantom.edf`.
- Confirm output arrays have expected dimensions.
- Confirm BBI and amplitude outputs do not crash on generic channel data.

### 4.6 `TimeFrequencyMap`

Purpose:

Represent scalogram or spectrogram data in a display-independent form.

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `times_s` | `np.ndarray` | Time axis |
| `freqs_hz` | `np.ndarray` | Frequency axis |
| `values` | `np.ndarray` | 2D matrix shaped `(n_freqs, n_times)` |
| `value_label` | `str` | Display label such as `|CWT|` or `dB` |
| `method` | `str` | `cwt` or `stft` |

Validation:

- `values.shape == (len(freqs_hz), len(times_s))`.
- `times_s` must be increasing.
- `freqs_hz` must be increasing.
- Frequencies must be greater than or equal to `0`.

Independent tests:

- Validate scalogram dimensions.
- Validate spectrogram dimensions.
- Reject mismatched matrix dimensions.

### 4.7 `ExportResult`

Purpose:

Represent files produced by export actions.

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `png_paths` | `list[str]` | Exported PNG files |
| `csv_paths` | `list[str]` | Exported CSV files |
| `parameter_record_paths` | `list[str]` | Exported parameter records |
| `messages` | `list[str]` | Human-readable status messages |

Independent tests:

- Export current tab to a temporary path.
- Export CSV features to a temporary path.
- Export parameter record to a temporary path.

## 5. Module Detailed Design

## 5.1 Data Layer

### 5.1.1 Purpose

The data layer isolates EDF file reading and metadata extraction from GUI, CLI, preprocessing, and analysis modules.

### 5.1.2 Public Interface

Recommended functions:

```python
def load_edf_metadata(file_path: str) -> EDFMetadata:
    ...

def load_channel_window(
    file_path: str,
    channel_name: str,
    window_start_s: float,
    window_length_s: float,
) -> ChannelWindow:
    ...

def get_valid_time_range(metadata: EDFMetadata, channel_name: str) -> tuple[float, float]:
    ...
```

### 5.1.3 Internal Behavior

`load_edf_metadata` should:

- Check that the path exists.
- Open the EDF file through the selected EDF reader.
- Read channel names.
- Read sampling rate information.
- Read duration.
- Return `EDFMetadata`.

`load_channel_window` should:

- Validate channel name.
- Validate window start and length.
- Convert window start and length to sample indices.
- Extract only the requested channel and time range when possible.
- Return `ChannelWindow`.

`get_valid_time_range` should:

- Return `(0.0, duration_s)` for the selected channel.
- Be prepared for future channel-specific durations if needed.

### 5.1.4 Error Cases

- File does not exist.
- File cannot be read as EDF.
- Channel does not exist.
- Duration is invalid.
- Requested window is outside valid range.
- Requested window has no samples.

### 5.1.5 Independent Tests

- Load `samples/phantom.edf` metadata.
- Confirm duration is approximately `300s`.
- Confirm selected channel can be loaded.
- Confirm invalid channel raises a data-layer error.
- Confirm invalid window raises a data-layer error.

## 5.2 Parameter Management Module

### 5.2.1 Purpose

The parameter management module converts GUI widget state or CLI arguments into validated parameter objects.

### 5.2.2 Public Interface

Recommended functions:

```python
def build_analysis_parameters(raw_values: dict, metadata: EDFMetadata) -> AnalysisParameters:
    ...

def validate_analysis_parameters(
    parameters: AnalysisParameters,
    metadata: EDFMetadata,
) -> None:
    ...

def parameter_record(parameters: AnalysisParameters, metadata: EDFMetadata) -> dict:
    ...
```

### 5.2.3 Validation Rules

Window validation:

- `window_start_s >= 0`.
- `window_length_s > 0`.
- `window_start_s + window_length_s <= duration_s`.

Sampling validation:

- `target_sfreq > 0`.
- `target_sfreq <= original_sfreq` for downsampling-only behavior.

Frequency validation:

- Minimum frequency must be greater than or equal to `0` for spectrogram display.
- Minimum scalogram frequency must be greater than `0`.
- Maximum frequency must be greater than minimum frequency.
- Maximum analysis frequency should not exceed Nyquist.

Filter validation:

- Low-pass requires `high_cut_hz`.
- High-pass requires `low_cut_hz`.
- Band-pass requires both `low_cut_hz` and `high_cut_hz`.
- For band-pass, `high_cut_hz > low_cut_hz`.
- Filter frequencies must be below Nyquist.

Color range validation:

- Manual mode requires both `color_min` and `color_max`.
- `color_max > color_min`.

### 5.2.4 Independent Tests

- Valid default parameters pass.
- Window outside range fails.
- Target sampling rate above original sampling rate fails.
- Invalid filter combinations fail.
- Manual color range with equal min and max fails.

## 5.3 Preprocessing Module

### 5.3.1 Purpose

The preprocessing module prepares one selected channel window for analysis.

### 5.3.2 Public Interface

Recommended functions:

```python
def preprocess_signal(
    window: ChannelWindow,
    parameters: AnalysisParameters,
) -> tuple[np.ndarray, float, dict]:
    ...

def apply_filter_if_needed(
    signal: np.ndarray,
    sfreq: float,
    parameters: AnalysisParameters,
) -> tuple[np.ndarray, dict]:
    ...

def downsample_if_needed(
    signal: np.ndarray,
    sfreq: float,
    target_sfreq: float | None,
) -> tuple[np.ndarray, float, dict]:
    ...
```

### 5.3.3 Processing Order

The preprocessing order should be explicit and consistent between GUI and CLI.

Recommended order:

1. Validate input signal shape.
2. Apply filtering if enabled.
3. Apply downsampling if target sampling rate is lower than original sampling rate.
4. Return processed signal, processed sampling rate, and preprocessing metadata.

If implementation later requires a different order, that change must be documented because it may affect analysis results.

### 5.3.4 Inputs and Outputs

Inputs:

- `ChannelWindow`
- `AnalysisParameters`

Outputs:

- Processed one-dimensional signal array.
- Processed sampling rate.
- Metadata describing applied preprocessing.

### 5.3.5 Error Cases

- Empty signal.
- Non-1D signal.
- Invalid target sampling rate.
- Invalid filter frequencies.
- Filter computation failure.
- Downsampling computation failure.

### 5.3.6 Independent Tests

- Downsample a known sine signal and confirm output length.
- Apply low-pass filter to a synthetic signal.
- Apply high-pass filter to a synthetic signal.
- Apply band-pass filter to a synthetic signal.
- Confirm preprocessing does not import or require GUI packages.

## 5.4 Analysis Module

### 5.4.1 Purpose

The analysis module computes all numerical outputs from one preprocessed channel window.

### 5.4.2 Public Interface

Recommended functions:

```python
def analyze_window(
    window: ChannelWindow,
    processed_signal: np.ndarray,
    processed_sfreq: float,
    parameters: AnalysisParameters,
) -> AnalysisResult:
    ...

def compute_signal_views(
    signal: np.ndarray,
    times_s: np.ndarray,
    sfreq: float,
) -> dict:
    ...

def compute_time_frequency_maps(
    signal_views: dict,
    sfreq: float,
    parameters: AnalysisParameters,
) -> dict:
    ...

def compute_feature_table(result: AnalysisResult) -> dict:
    ...
```

### 5.4.3 Signal View Computation

Raw signal:

- Use the processed signal for display and analysis output.
- Preserve the corresponding time vector.

BBI:

- Compute beat-to-beat interval values from the selected signal window.
- Return BBI times and values.
- If no valid BBI can be computed, return empty arrays or a documented placeholder result without crashing.

Amplitude:

- Compute per-beat amplitude values from the selected signal window.
- Return amplitude times and values.
- If no valid amplitude can be computed, return empty arrays or a documented placeholder result without crashing.

### 5.4.4 Scalogram Computation

Scalogram inputs:

- Raw signal series.
- BBI-derived sample-aligned series.
- Amplitude-derived sample-aligned series.
- Sampling rate.
- Wavelet.
- Frequency range.
- Number of scales.

Scalogram outputs:

- `raw_scalogram`
- `bbi_scalogram`
- `amplitude_scalogram`

Each scalogram must be represented as `TimeFrequencyMap`.

Rules:

- `freqs_hz` must be increasing.
- `times_s` must be increasing.
- `values` must have shape `(n_freqs, n_times)`.
- The GUI should be able to apply one shared value range across the three scalograms for comparison.

### 5.4.5 Spectrogram Computation

Spectrogram inputs:

- Processed signal.
- Sampling rate.
- STFT window length.
- Frequency range.

Spectrogram output:

- `spectrogram` as `TimeFrequencyMap`.

Rules:

- Frequency axis must be increasing.
- Time axis must be increasing.
- Values should be display-ready for spectrogram visualization.
- STFT window changes should recompute the spectrogram.

### 5.4.6 Feature Table Computation

The feature table should be CSV-compatible.

Minimum feature table context:

- Source file.
- Channel.
- Window start.
- Window length.
- Sampling rate.
- Computed time-domain features when available.
- Computed frequency-domain features when available.
- BBI summary values when available.
- Amplitude summary values when available.

The exact feature list can follow existing analysis functions and can be expanded later.

### 5.4.7 Error Cases

- Processed signal is empty.
- Sampling rate is invalid.
- CWT computation fails.
- STFT computation fails.
- Feature computation fails.

Analysis functions should raise analysis-specific errors rather than GUI or CLI errors.

### 5.4.8 Independent Tests

- Analyze `samples/phantom.edf` first 100 seconds and confirm dominant frequency near `1.5 Hz`.
- Analyze final 100 seconds and confirm dominant frequency near `3 Hz`.
- Confirm amplitude difference between first and middle segments.
- Confirm scalogram dimensions.
- Confirm spectrogram dimensions.
- Confirm BBI and amplitude paths do not crash on generic channel input.

## 5.5 Visualization Module

### 5.5.1 Purpose

The visualization module converts `AnalysisResult` and `DisplayParameters` into GUI views or exportable figures.

### 5.5.2 Public Interface

Recommended functions:

```python
def build_signal_plot_data(
    result: AnalysisResult,
    display: DisplayParameters,
) -> dict:
    ...

def build_scalogram_plot_data(
    result: AnalysisResult,
    display: DisplayParameters,
) -> dict:
    ...

def build_spectrogram_plot_data(
    result: AnalysisResult,
    display: DisplayParameters,
) -> dict:
    ...

def compute_color_range(
    maps: list[TimeFrequencyMap],
    display: DisplayParameters,
) -> tuple[float, float]:
    ...
```

### 5.5.3 Signal View Rules

For active signal view `raw`:

- Plot raw signal time on X-axis.
- Plot raw signal value on Y-axis.
- Pair with raw scalogram.

For active signal view `bbi`:

- Plot BBI time on X-axis.
- Plot BBI value on Y-axis.
- Pair with BBI scalogram.

For active signal view `amplitude`:

- Plot amplitude time on X-axis.
- Plot amplitude value on Y-axis.
- Pair with amplitude scalogram.

### 5.5.4 Time-Frequency Display Rules

Scalogram and spectrogram plots must:

- Use time in seconds on the X-axis.
- Use frequency in Hz on the Y-axis.
- Respect selected frequency range.
- Respect linear/log axis mode.
- Respect selected color/value range.
- Keep axis labels consistent.

### 5.5.5 Color Range Rules

Automatic scalogram comparison range:

- When comparing raw, BBI, and amplitude scalograms within one window, compute a shared min/max from the relevant maps.

Manual range:

- Use user-provided `color_min` and `color_max`.
- Reject invalid manual range before plotting.

Spectrogram color range:

- Use automatic or manual range according to display parameters.

### 5.5.6 Independent Tests

- Build plot data for raw view.
- Build plot data for BBI view.
- Build plot data for amplitude view.
- Confirm scalogram color range is shared when required.
- Confirm invalid manual color range is rejected by parameter validation.
- Confirm no visualization function depends on CLI argument parsing.

## 5.6 Export Module

### 5.6.1 Purpose

The export module writes analysis outputs to files for reports and reproducibility.

### 5.6.2 Public Interface

Recommended functions:

```python
def export_current_png(
    image_or_widget,
    output_path: str,
) -> str:
    ...

def export_window_pngs(
    result: AnalysisResult,
    display: DisplayParameters,
    output_dir: str,
) -> list[str]:
    ...

def export_feature_csv(
    result: AnalysisResult,
    output_path: str,
) -> str:
    ...

def export_parameter_record(
    result: AnalysisResult,
    output_path: str,
) -> str:
    ...
```

### 5.6.3 Output Naming Rules

PNG and CSV file names should include:

- Source file stem.
- Channel name.
- Window start.
- Window length.
- View type or output type.

Example pattern:

```text
{source_stem}_{channel}_{start_s}-{end_s}_{view_type}.png
{source_stem}_{channel}_{start_s}-{end_s}_features.csv
{source_stem}_{channel}_{start_s}-{end_s}_parameters.*
```

The parameter record extension is not fixed by current requirements. The implementation should keep the writer isolated so the concrete format can be selected or changed later.

### 5.6.4 CSV Feature Rules

CSV feature output should:

- Include one header row.
- Include source file context.
- Include channel and window context.
- Include analysis parameter identifiers where useful.
- Include numeric feature values in stable column names.

### 5.6.5 Parameter Record Rules

The parameter record must include:

- Source file path or file name.
- Channel.
- Window start.
- Window length.
- Target sampling rate.
- Filtering settings.
- CWT settings.
- STFT settings.
- Frequency range.
- Frequency axis mode.
- Color range settings.

### 5.6.6 Error Cases

- Output directory does not exist and cannot be created.
- Output path is not writable.
- Required result data is missing.
- CSV serialization fails.
- PNG save fails.
- Parameter record save fails.

### 5.6.7 Independent Tests

- Export PNG to a temporary directory.
- Export feature CSV to a temporary directory.
- Export parameter record to a temporary directory.
- Confirm file names include source, channel, window, and output type.

## 5.7 Application Workflow Layer

### 5.7.1 Purpose

The workflow layer is the main shared controller used by GUI and CLI. It normalizes inputs, validates parameters, calls core modules, manages cache, and returns results.

### 5.7.2 Public Interface

Recommended class:

```python
class EDFViewerWorkflow:
    def load_file(self, file_path: str) -> EDFMetadata:
        ...

    def get_channel_range(self, channel_name: str) -> tuple[float, float]:
        ...

    def compute_window(
        self,
        channel_name: str,
        parameters: AnalysisParameters,
    ) -> AnalysisResult:
        ...

    def export_result(
        self,
        result: AnalysisResult,
        export_request: dict,
    ) -> ExportResult:
        ...
```

### 5.7.3 Compute Window Flow

`compute_window` should:

1. Confirm an EDF file is loaded.
2. Validate selected channel.
3. Validate analysis parameters.
4. Build cache key.
5. Return cached result if available and valid.
6. Load selected channel window.
7. Preprocess signal.
8. Run analysis.
9. Store result in cache.
10. Return `AnalysisResult`.

### 5.7.4 Export Flow

`export_result` should:

1. Validate export request.
2. Select export outputs.
3. Call PNG export if requested.
4. Call CSV export if requested.
5. Call parameter record export if requested.
6. Return `ExportResult`.

### 5.7.5 Independent Tests

- Load file and compute a valid window.
- Compute same window twice and confirm cache is used.
- Change a parameter and confirm cache is invalidated.
- Export analysis outputs to a temporary directory.
- Confirm workflow can run without GUI imports.

## 5.8 Cache Module

### 5.8.1 Purpose

The cache module stores recently computed analysis results to improve interactive GUI navigation.

### 5.8.2 Cache Key Fields

Cache key must include:

- EDF file path.
- Channel name.
- Window start.
- Window length.
- Target sampling rate.
- Filter settings.
- CWT wavelet.
- CWT frequency range.
- CWT scale count.
- STFT window length.
- Spectrogram frequency range.

Display-only settings that do not change analysis values may be excluded from the compute cache. If color range or axis mode only changes plotting, visualization should update without recomputing analysis.

### 5.8.3 Public Interface

Recommended class:

```python
class AnalysisCache:
    def get(self, key: tuple) -> AnalysisResult | None:
        ...

    def put(self, key: tuple, result: AnalysisResult) -> None:
        ...

    def clear(self) -> None:
        ...
```

### 5.8.4 Eviction Policy

The cache should use a small least-recently-used policy for recent windows.

The exact cache size can be configurable. Current behavior may keep the last two windows.

### 5.8.5 Independent Tests

- Store and retrieve result by key.
- Confirm least-recently-used eviction.
- Confirm cache clear removes entries.
- Confirm changed analysis parameter creates a different key.

## 5.9 GUI Interface Module

### 5.9.1 Purpose

The GUI provides interactive EDF analysis for users who inspect signals manually and export figures.

### 5.9.2 GUI State

The GUI owns:

- Widget values.
- Active selected tab.
- Active displayed signal view.
- Current status message.
- Current file label.
- Current plot widgets.

The GUI should not own:

- Core analysis algorithms.
- EDF reading logic.
- Export serialization logic.

### 5.9.3 Main GUI Events

Open EDF:

1. User selects EDF file.
2. GUI calls `workflow.load_file`.
3. GUI populates channel selector.
4. GUI displays duration and valid time range.

Select channel:

1. User selects channel.
2. GUI requests valid time range.
3. GUI updates window controls.
4. GUI clears stale analysis result if needed.

Compute current window:

1. GUI reads widget values.
2. GUI builds `AnalysisParameters`.
3. GUI calls `workflow.compute_window`.
4. GUI sends returned result to visualization rendering.
5. GUI enables export actions.

Change display-only parameter:

1. GUI updates `DisplayParameters`.
2. GUI rerenders existing result if available.
3. GUI does not recompute analysis unless the parameter affects analysis values.

Export:

1. GUI collects export target.
2. GUI calls workflow or export module.
3. GUI displays export status.

### 5.9.4 Threading Rule

Long-running file loading and analysis should not block the GUI event loop.

Worker threads may call workflow methods, but GUI widgets should only be updated on the GUI thread.

### 5.9.5 Independent Tests

GUI tests may be smoke tests:

- GUI initializes without opening a file.
- GUI opens `samples/phantom.edf`.
- GUI computes a window.
- GUI exports current tab PNG.

Core behavior should be tested outside the GUI through workflow and module tests.

## 5.10 CLI Interface Module

### 5.10.1 Purpose

The CLI provides reproducible analysis without launching the GUI.

### 5.10.2 Argument Groups

Input arguments:

- EDF file path.
- Channel name or channel index.

Window arguments:

- Window start.
- Window length.

Analysis arguments:

- Target sampling rate.
- Wavelet.
- STFT window length.
- Frequency range.
- Filter parameters.

Output arguments:

- Output directory.
- Output file prefix if supported.
- Export type selection if supported.

### 5.10.3 CLI Flow

1. Parse arguments.
2. Convert arguments to `AnalysisParameters`.
3. Load EDF metadata.
4. Validate selected channel and window.
5. Compute selected window through workflow.
6. Export requested outputs.
7. Print output paths and status.

### 5.10.4 Exit Behavior

Success:

- Exit with status `0`.
- Print output paths.

Failure:

- Exit with nonzero status.
- Print a readable error message.

### 5.10.5 Independent Tests

- Run CLI with `samples/phantom.edf`.
- Run CLI with invalid file path.
- Run CLI with invalid channel.
- Run CLI with invalid window.
- Confirm output files are generated in a temporary directory.

## 5.11 Packaging Module

### 5.11.1 Purpose

The packaging module prepares EDFViewer for Python source execution and macOS app distribution.

### 5.11.2 Current Packaging Targets

Current targets:

- Python source execution.
- macOS app.

### 5.11.3 Packaging Validation

Validation checklist:

- App starts.
- EDF file dialog works.
- `samples/phantom.edf` can be opened.
- Channel list appears.
- A window can be computed.
- Current tab PNG can be exported.

### 5.11.4 Future Packaging Targets

Future targets:

- Windows executable.
- Linux executable.

These should be documented but not required for current implementation.

## 6. Error Design

All modules should use clear error boundaries. Core modules should raise domain-specific exceptions. GUI and CLI should convert those exceptions into user-readable messages.

Recommended exception types:

```python
class EDFViewerError(Exception):
    ...

class DataLoadError(EDFViewerError):
    ...

class ParameterValidationError(EDFViewerError):
    ...

class PreprocessingError(EDFViewerError):
    ...

class AnalysisError(EDFViewerError):
    ...

class ExportError(EDFViewerError):
    ...
```

Error handling rules:

- Data layer should raise `DataLoadError`.
- Parameter management should raise `ParameterValidationError`.
- Preprocessing should raise `PreprocessingError`.
- Analysis should raise `AnalysisError`.
- Export should raise `ExportError`.
- GUI should show status messages or dialogs.
- CLI should print errors and exit nonzero.

## 7. Test Design

## 7.1 Unit Tests

Unit tests should focus on individual modules:

- Data layer tests.
- Parameter validation tests.
- Preprocessing tests.
- Analysis tests.
- Visualization data preparation tests.
- Export tests.
- Cache tests.

## 7.2 Integration Tests

Integration tests should cover:

- EDF file -> metadata -> channel window.
- Channel window -> preprocessing -> analysis.
- Analysis result -> visualization data.
- Analysis result -> export files.
- CLI command -> output files.

## 7.3 Synthetic Signal Tests

Use `samples/phantom.edf`.

Required checks:

- Duration is approximately `300s`.
- First segment dominant frequency is near `1.5 Hz`.
- Middle segment dominant frequency is near `1.5 Hz`.
- Final segment dominant frequency is near `3 Hz`.
- First segment amplitude is larger than middle segment amplitude.
- Scalogram and spectrogram show expected frequency change.

## 7.4 GUI Smoke Tests

GUI smoke tests should confirm:

- Window initializes.
- EDF file can be selected.
- Channel selector is populated.
- Compute action completes.
- Export action writes PNG.

## 7.5 CLI Tests

CLI tests should confirm:

- Valid command completes.
- Invalid input fails clearly.
- Output files are created.
- Parameter record is created when requested.

## 8. Detailed Workflow Specifications

## 8.1 Open EDF Workflow

Input:

- EDF file path.

Steps:

1. GUI or CLI sends path to workflow.
2. Workflow calls data layer.
3. Data layer validates and loads metadata.
4. Workflow stores active metadata.
5. GUI displays channel list and valid duration, or CLI proceeds to channel validation.

Output:

- `EDFMetadata`.

Failure:

- Missing file.
- Invalid EDF.
- No readable channels.

## 8.2 Compute Window Workflow

Input:

- Active EDF metadata.
- Channel.
- Window start.
- Window length.
- Analysis parameters.

Steps:

1. Validate active EDF.
2. Validate selected channel.
3. Validate parameters.
4. Check cache.
5. Load selected channel window.
6. Preprocess signal.
7. Compute analysis outputs.
8. Store result in cache.
9. Return `AnalysisResult`.

Output:

- `AnalysisResult`.

Failure:

- Invalid channel.
- Invalid window.
- Invalid parameters.
- Preprocessing failure.
- Analysis failure.

## 8.3 Render Workflow

Input:

- `AnalysisResult`.
- `DisplayParameters`.

Steps:

1. Select active signal view.
2. Select matching scalogram.
3. Apply frequency range.
4. Apply axis mode.
5. Apply color/value range.
6. Render signal plot.
7. Render scalogram plot.
8. Render spectrogram plot if requested.

Output:

- GUI view updates or exportable plot objects.

Failure:

- Missing analysis result.
- Missing selected map.
- Invalid display parameters.

## 8.4 Export Workflow

Input:

- `AnalysisResult`.
- Export request.
- Output path or directory.

Steps:

1. Validate output path.
2. Build output file names.
3. Export PNG if requested.
4. Export feature CSV if requested.
5. Export parameter record if requested.
6. Return `ExportResult`.

Output:

- Exported files.

Failure:

- Output path not writable.
- Missing result data.
- Serialization failure.

## 9. Module Independence and Testability

Each module should be independently testable:

| Module | Must Avoid Depending On | Test Input | Test Output |
| --- | --- | --- | --- |
| Data Layer | GUI widgets, CLI parser | EDF path | Metadata, channel window |
| Parameter Management | GUI widgets, CLI parser | Raw dict values | Validated parameters |
| Preprocessing | GUI, CLI, EDF reader | Arrays and parameters | Processed arrays |
| Analysis | GUI, CLI, EDF reader | Arrays and parameters | Analysis result |
| Visualization | EDF reader, CLI parser | Analysis result | Plot data |
| Export | GUI widgets, EDF reader | Result and paths | Files |
| Workflow | GUI widgets | File path and parameters | Result or export status |
| CLI | GUI widgets | Command arguments | Exit status and files |
| GUI | Analysis internals | Workflow responses | Visible views |

## 10. Traceability Matrix

| Requirement | Detailed Design Section |
| --- | --- |
| EDF file input | 5.1 Data Layer, 8.1 Open EDF Workflow |
| Channel selection | 5.1 Data Layer, 5.9 GUI, 5.10 CLI |
| Valid time range | 5.1 Data Layer, 5.7 Workflow |
| Windowed analysis | 4.2 ChannelWindow, 8.2 Compute Window Workflow |
| Target sampling rate | 4.3 AnalysisParameters, 5.3 Preprocessing |
| Filtering parameters | 4.3 AnalysisParameters, 5.3 Preprocessing |
| Raw signal view | 5.4 Analysis, 5.5 Visualization |
| BBI view | 5.4 Analysis, 5.5 Visualization |
| Amplitude view | 5.4 Analysis, 5.5 Visualization |
| CWT scalogram | 5.4 Analysis, 5.5 Visualization |
| STFT spectrogram | 5.4 Analysis, 5.5 Visualization |
| Frequency range | 4.3 AnalysisParameters, 5.5 Visualization |
| Linear/log axis | 4.4 DisplayParameters, 5.5 Visualization |
| Color/value range | 4.4 DisplayParameters, 5.5 Visualization |
| Current tab PNG export | 5.6 Export, 8.4 Export Workflow |
| All-window or selected-window PNG export | 5.6 Export |
| CSV feature table | 5.4 Analysis, 5.6 Export |
| Parameter record | 4.3 AnalysisParameters, 5.6 Export |
| GUI version | 5.9 GUI Interface Module |
| CLI version | 5.10 CLI Interface Module |
| macOS app | 5.11 Packaging Module |
| Validation plan | 7 Test Design |

## 11. Open Implementation Decisions

The following details are intentionally left open because the current requirements do not specify them:

- Concrete parameter record file format.
- Exact complete list of CSV feature columns.
- Exact GUI layout for future controls beyond current required parameters.
- Exact packaging tool for macOS app generation.
- Exact batch-processing argument format for future multi-EDF CLI support.

These decisions should be made during implementation or in a follow-up design update before coding the related feature.

## 12. Definition of Done

The detailed design is satisfied when:

- Core data models are implemented or mapped to equivalent existing structures.
- GUI and CLI call shared workflow logic for common analysis behavior.
- Each module has independent tests or clear manual validation steps.
- `samples/phantom.edf` validates expected frequency and amplitude behavior.
- Exported outputs include figures, CSV features, and parameter records.
- User-facing text uses `BBI`.
- Current-scope and future-scope features remain clearly separated.

