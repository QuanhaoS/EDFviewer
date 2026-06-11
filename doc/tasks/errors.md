# Error Handling Tasks

Goal: define common domain-specific exceptions so each module can fail independently and GUI/CLI can display clear messages.

Source design: `doc/detailed-design.md` section 6.

## Minimal Tasks

- [ ] Create `core/errors.py`.
- [ ] Define base exception `EDFViewerError`.
- [ ] Define `DataLoadError`.
- [ ] Define `ParameterValidationError`.
- [ ] Define `PreprocessingError`.
- [ ] Define `AnalysisError`.
- [ ] Define `ExportError`.
- [ ] Replace broad user-facing exceptions in new shared modules with domain-specific exceptions.
- [ ] Ensure GUI catches `EDFViewerError` and displays readable status or dialog text.
- [ ] Ensure CLI catches `EDFViewerError`, prints readable text, and exits nonzero.
- [ ] Add tests that each exception can be raised and caught through `EDFViewerError`.

## Acceptance Criteria

- [ ] Core modules do not raise GUI-specific errors.
- [ ] CLI failures are readable and return nonzero exit status.
- [ ] GUI failures are readable and do not crash the app.

