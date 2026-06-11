# Preprocessing Module Tasks

Goal: prepare selected channel windows for analysis through filtering and downsampling.

Source design: `doc/detailed-design.md` section 5.3.

## Minimal Tasks

- [ ] Implement `preprocess_signal(window, parameters)`.
- [ ] Implement `apply_filter_if_needed(signal, sfreq, parameters)`.
- [ ] Implement `downsample_if_needed(signal, sfreq, target_sfreq)`.
- [ ] Use existing `preprocessing/filter.py` low-pass function.
- [ ] Use existing `preprocessing/filter.py` high-pass function.
- [ ] Use existing `preprocessing/filter.py` band-pass function.
- [ ] Use existing `preprocessing/downsample.py` downsampling function.
- [ ] Return processed signal, processed sampling rate, and preprocessing metadata.
- [ ] Keep processing order explicit: validate signal, filter if enabled, downsample if needed.
- [ ] Raise `PreprocessingError` for invalid signal shape.
- [ ] Raise `PreprocessingError` for filter computation failure.
- [ ] Raise `PreprocessingError` for downsampling failure.
- [ ] Add tests for downsampling a synthetic sine.
- [ ] Add tests for low-pass filtering.
- [ ] Add tests for high-pass filtering.
- [ ] Add tests for band-pass filtering.
- [ ] Add tests confirming no GUI dependency.

## Acceptance Criteria

- [ ] Preprocessing accepts `ChannelWindow` and `AnalysisParameters`.
- [ ] Output signal remains one-dimensional.
- [ ] Output sampling rate is correct after downsampling.

