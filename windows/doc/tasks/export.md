# Export Module Tasks

Goal: write PNG, CSV feature tables, and analysis parameter records.

Source design: `doc/detailed-design.md` sections 5.6 and 8.4.

## Minimal Tasks

- [ ] Create `export/` package.
- [ ] Implement `export_current_png(image_or_widget, output_path)`.
- [ ] Implement `export_window_pngs(result, display, output_dir)`.
- [ ] Implement `export_feature_csv(result, output_path)`.
- [ ] Implement `export_parameter_record(result, output_path)`.
- [ ] Implement output file name builder.
- [ ] Include source file stem in output names.
- [ ] Include channel name in output names.
- [ ] Include window start and end or length in output names.
- [ ] Include view type or output type in output names.
- [ ] Ensure CSV output includes one header row.
- [ ] Ensure CSV output includes source file, channel, and window context.
- [ ] Ensure parameter record includes sampling settings.
- [ ] Ensure parameter record includes filtering settings.
- [ ] Ensure parameter record includes CWT settings.
- [ ] Ensure parameter record includes STFT settings.
- [ ] Ensure parameter record includes frequency range and color range.
- [ ] Raise `ExportError` for unwritable output paths.
- [ ] Add tests for PNG export to temporary directory.
- [ ] Add tests for CSV export to temporary directory.
- [ ] Add tests for parameter record export to temporary directory.
- [ ] Add tests for output file naming.

## Acceptance Criteria

- [ ] Exports are reproducible from an `AnalysisResult`.
- [ ] Export module does not run analysis itself.
- [ ] Export failures are reported clearly.
