# Validation Module Tasks

Goal: validate EDFViewer with synthetic EDF, real EDF, GUI workflow, CLI workflow, export outputs, and packaging.

Source design: `doc/detailed-design.md` sections 7 and 13.

## Minimal Tasks

- [ ] Confirm `samples/phantom.edf` exists or can be regenerated.
- [ ] Validate phantom duration is approximately `300s`.
- [ ] Validate first 100 seconds dominant frequency is near `1.5 Hz`.
- [ ] Validate middle 100 seconds dominant frequency is near `1.5 Hz`.
- [ ] Validate final 100 seconds dominant frequency is near `3 Hz`.
- [ ] Validate first segment amplitude is larger than middle segment amplitude.
- [ ] Validate scalogram shows expected frequency change.
- [ ] Validate spectrogram shows expected frequency change.
- [ ] Validate real EDF file loading.
- [ ] Validate real EDF channel listing.
- [ ] Validate real EDF channel selection.
- [ ] Validate real EDF window range calculation.
- [ ] Validate GUI can complete open, select, compute, inspect, export workflow.
- [ ] Validate CLI can complete equivalent workflow.
- [ ] Validate current tab PNG export.
- [ ] Validate selected-window or all-window PNG export.
- [ ] Validate CSV feature table export.
- [ ] Validate parameter record export.
- [ ] Validate macOS app startup.
- [ ] Validate macOS app EDF opening.
- [ ] Validate macOS app PNG export.

## Acceptance Criteria

- [ ] Synthetic EDF tests confirm known frequency and amplitude behavior.
- [ ] Real EDF smoke tests pass.
- [ ] GUI and CLI produce equivalent analysis context for same inputs.
- [ ] Exported files are readable and contain expected context.
