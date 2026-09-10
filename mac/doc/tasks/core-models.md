# Core Models Tasks

Goal: define shared data objects used by GUI, CLI, workflow, analysis, visualization, export, and tests.

Source design: `doc/detailed-design.md` sections 4.1-4.7.

## Minimal Tasks

- [ ] Create `core/` package with `__init__.py`.
- [ ] Create `core/models.py`.
- [ ] Define `EDFMetadata` dataclass.
- [ ] Define `ChannelWindow` dataclass.
- [ ] Define `TimeFrequencyMap` dataclass.
- [ ] Define `AnalysisResult` dataclass.
- [ ] Define `ExportResult` dataclass.
- [ ] Add validation helper methods or standalone validators for shape, duration, and axis consistency.
- [ ] Ensure `TimeFrequencyMap.values.shape == (len(freqs_hz), len(times_s))`.
- [ ] Ensure `ChannelWindow.times_s` and `ChannelWindow.signal` lengths match.
- [ ] Ensure models do not import PyQt6, pyqtgraph, argparse, or CLI-specific code.
- [ ] Add unit tests for valid model construction.
- [ ] Add unit tests for invalid `ChannelWindow` shapes.
- [ ] Add unit tests for invalid `TimeFrequencyMap` dimensions.

## Acceptance Criteria

- [ ] Models can be imported in a plain Python session.
- [ ] Models can be used by tests without launching GUI.
- [ ] Invalid model data is rejected clearly.
