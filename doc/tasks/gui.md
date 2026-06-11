# GUI Module Tasks

Goal: provide interactive EDF analysis through PyQt6 while delegating core behavior to workflow and shared modules.

Source design: `doc/detailed-design.md` section 5.9.

## Minimal Tasks

- [ ] Ensure GUI can initialize without opening a file.
- [ ] Connect EDF file picker to `workflow.load_file`.
- [ ] Populate channel selector from `EDFMetadata.channel_names`.
- [ ] Display valid time range after file and channel selection.
- [ ] Keep window start and window length controls within valid range.
- [ ] Build `AnalysisParameters` from GUI controls.
- [ ] Build `DisplayParameters` from GUI controls.
- [ ] Connect compute button to `workflow.compute_window`.
- [ ] Render raw signal view.
- [ ] Render BBI view.
- [ ] Render amplitude view.
- [ ] Render matching raw scalogram.
- [ ] Render matching BBI scalogram.
- [ ] Render matching amplitude scalogram.
- [ ] Render spectrogram view.
- [ ] Connect target sampling rate control.
- [ ] Connect wavelet selector.
- [ ] Connect STFT window control.
- [ ] Add or connect frequency range controls.
- [ ] Add or connect linear/log frequency axis control.
- [ ] Add or connect color/value range controls.
- [ ] Add or connect filtering controls.
- [ ] Rerender display-only changes without recomputing analysis when possible.
- [ ] Use worker thread or existing worker pattern for long-running compute.
- [ ] Ensure GUI widgets update only on GUI thread.
- [ ] Connect current tab PNG export.
- [ ] Connect future selected-window or all-window export entry point.
- [ ] Show readable error messages for `EDFViewerError`.
- [ ] Add headless GUI smoke test for initialization.
- [ ] Add GUI smoke test for opening `samples/phantom.edf`.
- [ ] Add GUI smoke test for computing one window.
- [ ] Add GUI smoke test for current tab PNG export.

## Acceptance Criteria

- [ ] GUI follows workflow: open EDF, select channel, select window, compute, inspect, export.
- [ ] GUI does not directly duplicate core analysis logic.
- [ ] GUI remains responsive during long computations.

