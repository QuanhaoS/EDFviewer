# EDFViewer Vibe Coding Prompt

You are the main coding agent for the EDFViewer project. Your job is to implement the current-scope engineering plan end to end, coordinate subagents for each module, track progress, run automated validation, and compare all validation results against the theoretical expectations from `samples/phantom.edf`.

No human will participate during implementation. Do not stop to ask implementation questions unless the repository state makes the task impossible or a requirement is logically contradictory. When a detail is intentionally open in the design, choose the simplest conservative implementation that matches the existing codebase and document the decision.

## Source Documents

Read these first and treat them as the project contract:

- `doc/Proposal.md`
- `doc/detailed-design.md`
- `doc/phantom-summary.md`
- `doc/tasks/*.md`

Use `doc/tasks/progress.md` as the main progress tracker. Check a module only after all required tasks and acceptance criteria in its corresponding task file pass.

## Project Goal

Build EDFViewer into a maintainable single-EDF analysis application with:

- Shared core workflow used by both GUI and CLI.
- EDF metadata loading, channel selection, and windowed signal loading.
- Validated analysis and display parameters.
- Filtering and downsampling.
- Raw signal, BBI, amplitude, CWT scalogram, and STFT spectrogram outputs.
- PNG, CSV feature, and parameter-record export.
- GUI workflow for open/select/window/compute/inspect/export.
- CLI workflow for reproducible non-GUI analysis.
- Automated validation using `samples/phantom.edf`, especially the `sine` channel.

Keep future-scope items documented but do not implement them unless they are needed to support current-scope extensibility.

## Non-Negotiable Rules

- Use `BBI` as the only user-facing term for beat-to-beat interval output, even when reusing existing `compute_ppi` internals.
- Treat EDF signals as generic channels. Do not hard-code physiology-specific assumptions into core workflow.
- Analyze selected time windows instead of requiring full-record rendering for normal workflows.
- Keep GUI and CLI independent from signal-processing details.
- Keep data, preprocessing, analysis, visualization, export, workflow, CLI, and GUI boundaries testable.
- Prefer adapting existing files and functions over rewriting from scratch.
- Do not move the entire repository into the proposed structure in one large refactor unless required; gradual mapping to the design is acceptable.
- Do not mark task checkboxes complete until tests or explicit validation steps prove completion.

## Existing Code To Reuse

The current repository already contains useful implementation pieces:

- EDF loading: `data/signal_dataset.py`, `data/edf_viewer.py`
- Filtering: `preprocessing/filter.py`
- Downsampling: `preprocessing/downsample.py`
- Frequency analysis, spectrogram, CWT: `analysis/freq_domain.py`
- Time-domain features: `analysis/time_domain.py`
- BBI/PPI and amplitude helpers: `analysis/ppg.py`
- Existing GUI logic: `gui_pyqt6.py`
- Existing CLI-style scripts: `app.py`, `run_analysis.py`, `run_pleth_scalogram.py`, `run_ppg_window_scalogram.py`

When possible, extract shared logic from existing GUI/script code into testable modules instead of duplicating it.

## Main Agent Responsibilities

1. Inspect repository state and note existing dirty changes. Do not revert user changes.
2. Read all design and task documents.
3. Create a short execution plan ordered by module dependency.
4. Spawn focused subagents for module implementation.
5. Review every subagent result before integration.
6. Run module tests and integration tests after each meaningful stage.
7. Use `samples/phantom.edf` and channel `sine` for quantitative validation.
8. Compare measured outputs against theory and record the comparison.
9. Update `doc/tasks/progress.md` only when evidence supports it.
10. Finish with a concise implementation report, including tests run, pass/fail status, exported output paths, and any unresolved limitations.

## Recommended Implementation Order

Implement in this dependency order:

1. Core errors and models
   - `core/errors.py`
   - `core/models.py`
   - Dataclasses and validation helpers.

2. Parameter management and cache
   - `core/parameters.py`
   - `core/cache.py`
   - Analysis/display parameter dataclasses, validation, parameter records, LRU cache.

3. Data layer
   - `data/edf_reader.py`
   - Metadata loading, channel-window loading, valid time range.

4. Preprocessing
   - Reuse `preprocessing/filter.py` and `preprocessing/downsample.py`.
   - Implement `preprocess_signal`, `apply_filter_if_needed`, `downsample_if_needed`.

5. Analysis
   - Implement raw, BBI, amplitude, CWT, STFT, and feature-table outputs.
   - Wrap time-frequency results as `TimeFrequencyMap`.

6. Visualization and export
   - `visualization/*`
   - `export/*`
   - Build display-independent plot data and export PNG/CSV/parameter records.

7. Shared workflow
   - `core/workflow.py`
   - One controller for GUI and CLI.

8. CLI
   - `cli/`
   - Parse reproducible arguments, call workflow, export outputs, return correct exit codes.

9. GUI
   - Refactor `gui_pyqt6.py` to call workflow.
   - Preserve and improve existing UI behavior.

10. Validation, docs, and packaging notes
   - Automated phantom validation.
   - README/usage updates as needed.
   - macOS packaging notes and smoke checks.

## Subagent Contract

Each subagent must receive:

- The relevant task file from `doc/tasks/`.
- Relevant sections of `doc/detailed-design.md`.
- Exact files it may edit.
- Required tests and acceptance criteria.
- A requirement to avoid unrelated refactors.

Each subagent must return:

- Files changed.
- Behavior implemented.
- Tests added or updated.
- Tests run and results.
- Known limitations or decisions.
- Whether its module checkbox is ready to be marked complete.

The main agent must not blindly trust a subagent. Inspect the diff, run the tests yourself when possible, and verify boundaries such as "no GUI imports in core modules."

## Suggested Subagents

Use these focused subagents, in dependency order:

- `core-models-errors-agent`: `doc/tasks/core-models.md`, `doc/tasks/errors.md`
- `parameters-cache-agent`: `doc/tasks/parameter-management.md`, `doc/tasks/cache.md`
- `data-layer-agent`: `doc/tasks/data-layer.md`
- `preprocessing-agent`: `doc/tasks/preprocessing.md`
- `analysis-agent`: `doc/tasks/analysis.md`
- `visualization-export-agent`: `doc/tasks/visualization.md`, `doc/tasks/export.md`
- `workflow-agent`: `doc/tasks/workflow.md`
- `cli-agent`: `doc/tasks/cli.md`
- `gui-agent`: `doc/tasks/gui.md`
- `validation-packaging-agent`: `doc/tasks/validation.md`, `doc/tasks/packaging.md`

If the environment does not support spawning real subagents, simulate this structure by working module by module and writing a short module handoff note before moving to the next module.

## Phantom EDF Validation Contract

Use `samples/phantom.edf`.

Sampling and duration:

- Sampling rate: `100 Hz`
- Duration: approximately `300 s`
- Required channels: `sine`, `chirp`

Primary validation channel: `sine`.

Theoretical expectations for `sine`:

| Window | Frequency | Peak amplitude | Peak-to-peak | RMS |
| --- | --- | --- | --- | --- |
| `0-100 s` | `1.5 Hz` | `200 mV` | `400 mV` | about `141.422 mV` |
| `100-200 s` | `1.5 Hz` | `100 mV` | `200 mV` | about `70.711 mV` |
| `200-300 s` | `3.0 Hz` | `100 mV` | `200 mV` | about `70.711 mV` |

Required checks:

- Metadata duration is approximately `300 s`.
- `sine` channel exists.
- Dominant frequency in `0-100 s` is near `1.5 Hz`.
- Dominant frequency in `100-200 s` is near `1.5 Hz`.
- Dominant frequency in `200-300 s` is near `3.0 Hz`.
- First-window amplitude is about twice the middle-window amplitude.
- CWT scalogram and STFT spectrogram show the frequency transition from `1.5 Hz` to `3.0 Hz`.
- Exported PNG, CSV features, and parameter records exist and contain the selected file/channel/window context.

Use practical numeric tolerances, for example:

- Dominant frequency tolerance: `+/- 0.15 Hz` for the fixed sine windows.
- Amplitude ratio tolerance: first/middle peak or peak-to-peak ratio between `1.8` and `2.2`.
- Duration tolerance: within `0.5 s` of `300 s`.

If MNE returns signal values in volts, convert to millivolts before comparing against the table. If values are already in millivolts, detect that from measured magnitudes and document the unit handling.

Optional validation channel: `chirp`.

- The `chirp` channel should show increasing frequency over time.
- The final segment partly exceeds Nyquist (`50 Hz`), so aliasing is expected and must not be treated as a failure.

## Testing Expectations

Add or update tests under `tests/` as implementation proceeds.

Minimum test groups:

- Model validation tests.
- Parameter validation tests.
- Data-layer tests with `samples/phantom.edf`.
- Preprocessing tests with synthetic sine arrays.
- Analysis tests using the three `sine` windows from `samples/phantom.edf`.
- Visualization plot-data tests without GUI dependencies.
- Export tests using temporary directories.
- Workflow tests using `samples/phantom.edf`.
- CLI tests with valid and invalid arguments.
- GUI smoke tests that can run headlessly where possible.

Run the narrowest tests after each module and a full test suite before final delivery. If GUI or packaging tests cannot run in the environment, record the exact reason and provide the closest automated fallback.

## CLI Acceptance Shape

The CLI should support at least:

- EDF file path.
- Channel name or index.
- Window start.
- Window length.
- Target sampling rate.
- Wavelet.
- CWT frequency range.
- STFT window length.
- Spectrogram frequency range.
- Filter settings.
- Output directory.
- Requested export types.

On success:

- Exit status `0`.
- Print generated output paths.

On failure:

- Nonzero exit status.
- Readable error message from `EDFViewerError` or a specific subclass.

## GUI Acceptance Shape

The GUI must support:

- Open EDF.
- Populate channel selector.
- Show valid time range.
- Select window start and length.
- Select target sampling rate.
- Select wavelet.
- Select STFT window length.
- Select frequency range.
- Toggle linear/log frequency axis.
- Set color/value range.
- Enable low-pass, high-pass, or band-pass filtering.
- Compute current window without freezing the UI.
- View raw, BBI, and amplitude signal views paired with matching scalograms.
- View spectrogram.
- Export current visible tab as PNG.
- Show readable errors for `EDFViewerError`.

Core analysis logic must live outside GUI code.

## Export Acceptance Shape

Generated output names should include:

- Source file stem.
- Channel name.
- Window start and end or length.
- View/output type.

Parameter records must include enough information to reproduce analysis:

- Source file.
- Channel.
- Window start and length.
- Target sampling rate.
- Filter settings.
- CWT settings.
- STFT settings.
- Frequency ranges.
- Axis and color settings.

CSV features must include at least:

- Source file.
- Channel.
- Window start.
- Window length.
- Sampling rate.
- Dominant frequency or relevant frequency feature.
- Amplitude summary when available.
- BBI summary when available.

## Progress Tracking Rules

For each module task file:

1. Complete implementation.
2. Add or update tests.
3. Run relevant tests.
4. Inspect acceptance criteria.
5. Only then update `doc/tasks/progress.md`.

Do not check a progress item merely because files exist.

## Final Report Requirements

At the end, produce a report containing:

- Summary of implemented modules.
- Tests run and results.
- Phantom validation table with measured vs theoretical values.
- Exported example output paths.
- GUI/CLI usage examples.
- Progress file status.
- Known limitations and future-scope items not implemented.

The final report must clearly state whether EDFViewer satisfies the current scope from `doc/Proposal.md` and `doc/detailed-design.md`.
