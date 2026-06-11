# Analysis Module Tasks

Goal: compute raw, BBI, amplitude, scalogram, spectrogram, and feature outputs for one selected channel window.

Source design: `doc/detailed-design.md` section 5.4.

## Minimal Tasks

- [ ] Implement `analyze_window(window, processed_signal, processed_sfreq, parameters)`.
- [ ] Implement `compute_signal_views(signal, times_s, sfreq)`.
- [ ] Implement raw signal view output.
- [ ] Implement BBI output using existing BBI computation logic.
- [ ] Implement amplitude output using existing amplitude computation logic.
- [ ] Ensure BBI returns empty arrays or documented placeholder result when no valid intervals are found.
- [ ] Ensure amplitude returns empty arrays or documented placeholder result when no valid amplitude is found.
- [ ] Implement sample-aligned BBI series for scalogram computation.
- [ ] Implement sample-aligned amplitude series for scalogram computation.
- [ ] Implement `compute_time_frequency_maps(signal_views, sfreq, parameters)`.
- [ ] Compute raw CWT scalogram.
- [ ] Compute BBI CWT scalogram.
- [ ] Compute amplitude CWT scalogram.
- [ ] Compute STFT spectrogram.
- [ ] Wrap each time-frequency result as `TimeFrequencyMap`.
- [ ] Implement `compute_feature_table(result)`.
- [ ] Include source file, channel, window, and sampling context in feature output.
- [ ] Raise `AnalysisError` for failed CWT or STFT computation.
- [ ] Add phantom EDF test for first 100 seconds near `1.5 Hz`.
- [ ] Add phantom EDF test for final 100 seconds near `3 Hz`.
- [ ] Add test confirming first segment amplitude is larger than middle segment amplitude.
- [ ] Add dimension tests for scalogram and spectrogram.
- [ ] Add test confirming BBI and amplitude paths do not crash on generic channel input.

## Acceptance Criteria

- [ ] `AnalysisResult` contains raw, BBI, amplitude, scalogram, spectrogram, and feature fields.
- [ ] Frequency axes are increasing.
- [ ] Time-frequency matrices have shape `(n_freqs, n_times)`.
- [ ] No GUI or CLI parser dependency exists in analysis code.

