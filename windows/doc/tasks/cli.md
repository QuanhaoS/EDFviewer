# CLI Module Tasks

Goal: provide reproducible EDF analysis from command line using the same shared workflow as GUI.

Source design: `doc/detailed-design.md` section 5.10.

## Minimal Tasks

- [ ] Create `cli/` package.
- [ ] Create CLI parser module.
- [ ] Define EDF file path argument.
- [ ] Define channel name or channel index argument.
- [ ] Define window start argument.
- [ ] Define window length argument.
- [ ] Define target sampling rate argument.
- [ ] Define wavelet argument.
- [ ] Define STFT window argument.
- [ ] Define frequency range arguments.
- [ ] Define filter arguments.
- [ ] Define output directory argument.
- [ ] Convert parsed arguments to `AnalysisParameters`.
- [ ] Call `workflow.load_file`.
- [ ] Call `workflow.compute_window`.
- [ ] Call `workflow.export_result`.
- [ ] Print output paths on success.
- [ ] Return exit status `0` on success.
- [ ] Catch `EDFViewerError`.
- [ ] Print readable error on failure.
- [ ] Return nonzero exit status on failure.
- [ ] Add CLI test using `samples/phantom.edf`.
- [ ] Add CLI test for invalid file path.
- [ ] Add CLI test for invalid channel.
- [ ] Add CLI test for invalid window.
- [ ] Add CLI test confirming output files are created.

## Acceptance Criteria

- [ ] CLI can run without GUI imports.
- [ ] CLI uses shared workflow for analysis.
- [ ] CLI output can reproduce GUI-equivalent analysis context.
