# Parameter Management Tasks

Goal: convert GUI widget values and CLI arguments into one validated `AnalysisParameters` object.

Source design: `doc/detailed-design.md` sections 4.3, 4.4, and 5.2.

## Minimal Tasks

- [ ] Create `core/parameters.py`.
- [ ] Define `AnalysisParameters` dataclass.
- [ ] Define `DisplayParameters` dataclass.
- [ ] Implement `validate_analysis_parameters(parameters, metadata)`.
- [ ] Implement validation for window start and window length.
- [ ] Implement validation for target sampling rate.
- [ ] Implement validation for scalogram frequency range.
- [ ] Implement validation for spectrogram frequency range.
- [ ] Implement validation for STFT window length.
- [ ] Implement validation for manual color range.
- [ ] Implement validation for low-pass filter parameters.
- [ ] Implement validation for high-pass filter parameters.
- [ ] Implement validation for band-pass filter parameters.
- [ ] Implement `parameter_record(parameters, metadata)`.
- [ ] Add tests for valid default parameters.
- [ ] Add tests for invalid window ranges.
- [ ] Add tests for invalid frequency ranges.
- [ ] Add tests for invalid color ranges.
- [ ] Add tests for invalid filter settings.

## Acceptance Criteria

- [ ] GUI and CLI can both create the same parameter object shape.
- [ ] Invalid settings fail before analysis starts.
- [ ] Parameter records contain enough settings to reproduce analysis.

