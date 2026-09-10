# EDFViewer Project Proposal

## 1. Project Title

**EDFViewer: A GUI and CLI Tool for EDF Signal Visualization and Time-Frequency Analysis**

## 2. Project Background

EDFViewer is a physiological signal analysis application designed for laboratory researchers and clinical staff. The project focuses on analyzing signals stored in European Data Format (EDF) files. The current codebase already provides a working foundation for EDF loading, channel selection, downsampling, time-domain visualization, frequency-domain analysis, CWT scalogram visualization, STFT spectrogram visualization, BBI analysis, amplitude analysis, GUI interaction, command-line scripts, and PNG export.

The next development stage aims to turn this preliminary implementation into a clearer, more complete, and more maintainable EDF analysis tool. The software should support both an interactive GUI workflow and a command-line workflow. The GUI is intended for manual exploration and figure generation, while the CLI is intended for reproducible analysis and batch-style workflows.

This proposal defines the functional requirements, current implemented baseline, future extensions, risks, validation plan, and development milestones for EDFViewer.

## 3. Target Users

The primary users are:

- Laboratory researchers who inspect physiological signals, compare time-frequency representations, and prepare figures for research reports or publications.
- Clinical staff who need to inspect EDF recordings, select relevant channels, review time windows, and identify signal patterns or noise periods.

The software should be usable by people who are not software packaging experts and may not have deep signal-processing knowledge. The interface and documentation should support practical analysis workflows without requiring users to understand implementation details.

## 4. Project Goal

The main goal is to build an EDF signal analysis tool that can:

- Open EDF files.
- Visualize any channel as a generic signal.
- Analyze selected time windows instead of loading or rendering entire long recordings at once.
- Display raw signal, BBI, amplitude, CWT scalogram, and STFT spectrogram views.
- Allow users to adjust analysis and visualization parameters interactively.
- Export figures, features, and analysis parameters for later reporting or reproducibility.
- Provide both GUI and CLI versions whose core analysis behavior remains as consistent as possible.

## 5. Scope

### 5.1 Current Scope

The current scope focuses on single EDF file analysis. In the normal workflow, the user opens one EDF file, selects one channel, selects a time window, adjusts parameters, computes visualizations, inspects results, and exports figures or analysis outputs.

The software should treat all EDF signals as generic channels. It should not require predefined signal categories such as EEG, ECG, PPG, respiration, or blood pressure. Channel-specific analysis such as BBI and amplitude should be available when the signal content supports it, but the general viewer should remain channel-based.

### 5.2 Future Scope

Future features should be separated from the current implementation plan. These features should be documented but not required for the immediate version.

Future features include:

- Opening multiple EDF files in the GUI and switching between them.
- Batch processing multiple EDF files through the CLI.
- Reading CSV and MAT files in addition to EDF.
- Packaging Windows executables.
- Packaging Linux executables.
- Adding more adjustable analysis parameters.
- Adding optional PDF report generation.

## 6. Current Implemented Baseline

The current codebase already includes the following baseline functionality:

- EDF loading through the data layer.
- Channel selection.
- Downsampling with antialiasing.
- Basic preprocessing functions including low-pass, high-pass, and band-pass filtering.
- Time-domain analysis functions.
- Frequency-domain analysis functions including PSD, band powers, dominant frequency, spectral centroid, spectrogram, and CWT scalogram.
- PPG-related helper functions for BBI and amplitude analysis.
- PyQt6 and PyQtGraph GUI.
- CLI scripts for time-domain, PSD, PLETH, and windowed PPG/scalogram workflows.
- PNG export for visible GUI tabs and generated CLI figures.
- A synthetic EDF test file workflow through `samples/phantom.edf` and its generator script.

Some implemented components may still need integration refinement, naming cleanup, documentation updates, and packaging work before they should be considered complete user-facing product features.

## 7. Functional Requirements

### 7.1 Data Input Requirements

The system shall support opening EDF files.

The system shall support reading EDF metadata, including channel names, sampling rate, signal duration, and available data range.

The system shall allow the user to select one channel for focused analysis.

The system shall display the valid time range after an EDF file and channel are selected, so the user can choose a window start and window length within the available recording duration.

The system shall support long recordings, including overnight recordings, by analyzing selected time windows instead of requiring full-record visualization.

The system shall preserve CSV and MAT reading as future functionality.

### 7.2 GUI Requirements

The GUI shall support the following main workflow:

1. Open an EDF file.
2. Select a channel.
3. Select a time window.
4. View raw signal, scalogram, and spectrogram outputs.
5. Adjust parameters while inspecting the signal.
6. Save figures or analysis results.

The GUI shall provide controls for:

- Target sampling rate.
- Window start.
- Window length.
- CWT wavelet selection.
- STFT window length.
- Frequency range.
- Linear or logarithmic frequency axis.
- Color scale and value range.
- Filtering parameters.

The GUI shall include a `Signal + Scalogram` view.

The `Signal + Scalogram` view shall allow the user to select among:

- Raw signal.
- BBI.
- Amplitude.

The selected signal view shall be paired with the corresponding scalogram.

The GUI shall include a `Spectrogram` view.

The spectrogram shall be used as a comparison view against the scalogram.

The GUI shall support saving the current visible tab as a PNG image.

The GUI shall support future expansion for additional adjustable parameters without requiring major redesign.

### 7.3 CLI Requirements

The project shall include CLI and batch scripts as formal requirements, not only auxiliary tools.

The CLI version shall provide analysis functionality that is as consistent as possible with the GUI version.

The CLI shall support reproducible analysis by accepting file paths, channel choices, time window settings, sampling settings, and output paths as command-line arguments.

The CLI shall support generating analysis figures without opening the GUI.

The CLI shall be documented in `README.md`.

Future CLI functionality shall support batch processing across multiple EDF files.

### 7.4 Signal Visualization Requirements

The system shall display the selected raw channel signal in the time domain.

The system shall display BBI as one of the core analysis features.

The system shall display amplitude as one of the core analysis features.

The system shall use the term `BBI` consistently across the user interface, documentation, and output naming.

The system shall use `BBI` as the only user-facing term for beat-to-beat interval outputs.

The system may add additional core analysis features in future versions.

### 7.5 Scalogram Requirements

The system shall provide CWT scalogram visualization.

The scalogram shall be used to inspect frequency changes over time.

The scalogram shall help users identify the time location of motion artifacts or other noise patterns.

The scalogram shall support figure generation for papers and reports.

The scalogram shall support selectable wavelets.

The scalogram shall support adjustable frequency range.

The scalogram shall support linear and logarithmic frequency-axis display.

The scalogram shall support adjustable color scale and value range.

The scalogram shall use a consistent value range when comparing raw, BBI, and amplitude scalograms within the same analysis context.

### 7.6 Spectrogram Requirements

The system shall provide STFT spectrogram visualization.

The spectrogram shall be used as a comparison view against the scalogram.

The spectrogram shall support adjustable STFT window length.

The spectrogram shall support adjustable frequency range.

The spectrogram shall support linear and logarithmic frequency-axis display.

The spectrogram shall support adjustable color scale and value range.

### 7.7 Preprocessing Requirements

The system shall support downsampling.

The system shall support filtering controls, including filter parameter settings.

The system shall support low-pass, high-pass, and band-pass filtering.

The system shall preserve the ability to add more preprocessing methods in future versions.

### 7.8 Export Requirements

The system shall support exporting the current visible GUI tab as a PNG image.

The system shall support exporting PNG figures for all windows or selected windows.

The system shall support exporting CSV feature tables.

The system shall support saving analysis parameters so results can be reproduced.

The system may support PDF report generation in the future, but PDF report generation is not required for the current version.

### 7.9 Packaging Requirements

The current version shall support running from Python source code.

The current version shall target macOS app packaging.

Future versions shall target Windows executable packaging.

Future versions shall target Linux executable packaging.

## 8. Non-Functional Requirements

### 8.1 Performance

The software shall support large EDF recordings, including overnight files.

The software shall avoid rendering or computing the entire recording when a selected time window is sufficient.

The software shall provide clear time-window selection based on the selected file and channel duration.

The software shall use caching where appropriate to improve repeated analysis of recent windows.

### 8.2 Usability

The GUI shall make the main analysis workflow visible and direct.

The GUI shall expose important adjustable parameters without requiring users to edit source code.

The GUI shall keep raw signal, scalogram, and spectrogram inspection close together in the workflow.

The documentation shall explain how to run both GUI and CLI versions.

### 8.3 Maintainability

The project shall preserve a modular structure:

- Data layer for loading and managing signals.
- Preprocessing module for signal conditioning.
- Analysis module for numerical operations on arrays.
- Visualization layer for plotting and interaction.
- UI layer for user-facing orchestration.
- CLI layer for reproducible scripted workflows.

The GUI and CLI shall reuse shared analysis functions where possible.

## 9. Risks and Limitations

Large EDF files may require careful windowed loading, caching, and memory management.

Different EDF files may use different channel names, sampling rates, units, and metadata conventions.

BBI and amplitude analysis may not be meaningful for every channel, because the software treats channels generically.

Scalogram and spectrogram outputs depend on user-selected parameters such as wavelet, STFT window, frequency range, color scale, and filtering settings.

Spectrogram leakage and time-frequency resolution tradeoffs may affect interpretation.

Packaging PyQt6 applications for macOS, Windows, and Linux may require platform-specific testing.

CSV and MAT support is not part of the current implementation scope and may require separate metadata handling rules.

Clinical users should treat the software as an analysis and visualization tool, not as a standalone diagnostic device.

## 10. Validation Plan

The validation plan shall include synthetic data tests, real EDF tests, GUI workflow tests, CLI workflow tests, and export tests.

### 10.1 Synthetic EDF Validation

Use `samples/phantom.edf` to verify that known frequency and amplitude patterns are visible in the raw signal, scalogram, and spectrogram.

Expected validation checks include:

- The first 100 seconds should show a 1.5 Hz signal with 200 mV amplitude.
- The middle 100 seconds should show a 1.5 Hz signal with 100 mV amplitude.
- The final 100 seconds should show a 3 Hz signal with 100 mV amplitude.
- The scalogram and spectrogram should show the expected frequency change over time.
- Exported figures should preserve the visible analysis result.

### 10.2 Real EDF Validation

Use real EDF files to verify:

- File loading.
- Channel listing.
- Channel selection.
- Window range calculation.
- Windowed computation.
- GUI responsiveness for long recordings.
- Exported PNG images.
- CSV feature output.
- Analysis parameter logging.

### 10.3 CLI Validation

Verify that CLI scripts can:

- Accept EDF input paths.
- Select channels and time windows.
- Generate expected figures.
- Save outputs to user-defined directories.
- Match GUI analysis behavior where applicable.

### 10.4 Packaging Validation

For the current version, verify:

- Python source execution on macOS.
- macOS app startup.
- EDF file opening from the packaged app.
- PNG export from the packaged app.

For future versions, verify Windows and Linux executable behavior.

## 11. Development Milestones

### Milestone 1: Requirement and Documentation Consolidation

- Finalize project name as `EDFViewer`.
- Complete English and Chinese project proposals.
- Update README as the software requirements and usage document.
- Create product development documentation.
- Clean up terminology so user-facing text uses `BBI`.

### Milestone 2: Core GUI Refinement

- Ensure EDF loading and channel selection are stable.
- Show valid window range after channel selection.
- Improve time-window controls for long recordings.
- Ensure raw, BBI, amplitude, scalogram, and spectrogram views are clear.
- Add or refine controls for frequency range, color range, and filtering parameters.

### Milestone 3: Analysis Consistency

- Ensure GUI and CLI share common analysis functions.
- Verify CWT scalogram behavior across supported wavelets.
- Verify STFT spectrogram behavior across window settings.
- Ensure BBI and amplitude outputs are consistently named and exported.

### Milestone 4: Export and Reproducibility

- Implement or refine current-tab PNG export.
- Add all-window or selected-window PNG export.
- Add CSV feature table export.
- Add analysis parameter record export.
- Verify exported outputs using synthetic and real EDF files.

### Milestone 5: macOS Packaging

- Package the GUI as a macOS app.
- Verify startup, file opening, analysis, and export.
- Document installation and launch instructions.

### Milestone 6: Future Extensions

- Add multiple EDF file switching in the GUI.
- Add CLI batch processing for multiple EDF files.
- Add CSV and MAT input support.
- Add Windows executable packaging.
- Add Linux executable packaging.
- Consider optional PDF report generation.

## 12. Expected Deliverables

The expected deliverables are:

- EDFViewer Python source code.
- macOS GUI application package.
- CLI scripts for reproducible analysis.
- README usage and requirements documentation.
- English project proposal.
- Chinese project proposal.
- Product development document.
- Synthetic EDF validation file.
- Example exported figures and feature outputs.

## 13. Success Criteria

The project will be considered successful when:

- A user can open an EDF file in the GUI.
- A user can select a channel and valid time window.
- A user can view raw signal, BBI, amplitude, scalogram, and spectrogram outputs.
- A user can adjust key analysis parameters while inspecting results.
- A user can export figures, feature tables, and parameter records.
- The CLI can reproduce core analysis workflows without the GUI.
- The macOS app can run without requiring users to launch the tool manually from source code.
- Future feature boundaries are documented clearly.
