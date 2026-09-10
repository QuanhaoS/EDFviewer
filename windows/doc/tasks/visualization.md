# Visualization Module Tasks

Goal: convert analysis results into GUI plot data and exportable figure data without owning analysis logic.

Source design: `doc/detailed-design.md` section 5.5.

## Minimal Tasks

- [ ] Create `visualization/` package.
- [ ] Implement `build_signal_plot_data(result, display)`.
- [ ] Implement `build_scalogram_plot_data(result, display)`.
- [ ] Implement `build_spectrogram_plot_data(result, display)`.
- [ ] Implement `compute_color_range(maps, display)`.
- [ ] Map active view `raw` to raw signal and raw scalogram.
- [ ] Map active view `bbi` to BBI signal and BBI scalogram.
- [ ] Map active view `amplitude` to amplitude signal and amplitude scalogram.
- [ ] Apply frequency range to scalogram display data.
- [ ] Apply frequency range to spectrogram display data.
- [ ] Apply linear frequency axis mode.
- [ ] Apply log frequency axis mode.
- [ ] Apply automatic color range.
- [ ] Apply manual color range.
- [ ] Apply shared scalogram value range for raw, BBI, and amplitude comparison.
- [ ] Keep X-axis as time in seconds.
- [ ] Keep Y-axis as frequency in Hz.
- [ ] Add tests for each active signal view.
- [ ] Add tests for shared scalogram color range.
- [ ] Add tests for frequency range filtering.

## Acceptance Criteria

- [ ] Visualization functions accept `AnalysisResult` and `DisplayParameters`.
- [ ] Visualization functions do not read EDF files.
- [ ] Visualization functions do not parse CLI arguments.
