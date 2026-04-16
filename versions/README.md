# Versions

This folder contains two project variants:

- `cli_version`: Command-line focused version.
- `gui_version`: GUI-focused version.

## How To Run

### CLI version
```bash
cd versions/cli_version
python app.py --mode cli
python run_analysis.py
python run_pleth_scalogram.py
python run_ppg_window_scalogram.py
```

### GUI version
```bash
cd versions/gui_version
python app.py
```

## Packaging recommendation

To keep GUI and CLI behavior consistent, package `app.py` in each version as the single entrypoint.

```bash
# Example in versions/gui_version or versions/cli_version
pip install pyinstaller PyQt6 pyqtgraph
pyinstaller --noconfirm --onefile --windowed --name EDFReader app.py
pyinstaller --noconfirm --onefile --name EDFReaderCLI app.py
```
