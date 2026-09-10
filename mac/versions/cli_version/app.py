#!/usr/bin/env python3
"""
Unified entrypoint for EDFReader.

- GUI mode: interactive EDF viewer and scalogram tool.
- CLI mode: same arguments and behavior as run_analysis.py.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_cli(argv):
    parser = argparse.ArgumentParser(
        prog="app.py cli",
        description="Load EDF and plot time-domain and frequency-domain signals.",
    )
    parser.add_argument(
        "edf_path",
        nargs="?",
        default="samples/A.0007.edf",
        help="Path to EDF file (default: samples/A.0007.edf)",
    )
    parser.add_argument(
        "-n",
        "--channels",
        type=int,
        default=5,
        help="Number of channels to plot (default: 5)",
    )
    parser.add_argument(
        "-t",
        "--tmax",
        type=float,
        default=None,
        help="Crop to [0, tmax] seconds (optional)",
    )
    parser.add_argument(
        "--fmax",
        type=float,
        default=None,
        help="Max frequency (Hz) in PSD plot (optional)",
    )
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="Save time-domain and frequency-domain figures to files",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=str,
        default="figures",
        help="Output directory for saved figures (default: figures)",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not display plots (only save when used with --save)",
    )
    args = parser.parse_args(argv)

    edf_path = Path(args.edf_path)
    if not edf_path.exists():
        print(f"Error: file not found: {edf_path}")
        return 1
    from data import SignalDataset

    show = not args.no_show
    if args.save:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        stem = edf_path.stem
        time_path = outdir / f"{stem}_time_domain.png"
        freq_path = outdir / f"{stem}_freq_domain.png"
    else:
        time_path = freq_path = None

    print(f"Loading {edf_path} ...")
    dataset = SignalDataset(str(edf_path))
    dataset.summary()

    if args.tmax is not None:
        dataset.crop(tmin=0, tmax=args.tmax)
        print(f"Cropped to [0, {args.tmax}] s")

    print("\n--- Time domain ---")
    dataset.plot(
        n_channels=args.channels,
        savepath=time_path,
        show=show,
    )
    if time_path:
        print(f"Saved: {time_path}")

    print("\n--- Frequency domain (PSD) ---")
    dataset.plot_psd(
        n_channels=args.channels,
        fmax=args.fmax,
        savepath=freq_path,
        show=show,
    )
    if freq_path:
        print(f"Saved: {freq_path}")
    return 0


def _run_gui():
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QWidget,
            QVBoxLayout,
            QHBoxLayout,
            QPushButton,
            QLabel,
            QFileDialog,
            QComboBox,
            QDoubleSpinBox,
            QFormLayout,
            QMessageBox,
        )
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
    except ImportError as exc:
        print("GUI dependencies are missing or incompatible.")
        print(f"Import error: {exc}")
        print("Please install GUI dependencies, for example: pip install PySide6")
        return 1

    from data import SignalDataset
    from analysis import cwt_scalogram, compute_ppg_amplitude

    class MplCanvas(FigureCanvas):
        def __init__(self, parent=None):
            fig = Figure(figsize=(8, 6), tight_layout=True)
            self.axes = fig.subplots(3, 1, height_ratios=[1, 0.7, 1.2])
            super().__init__(fig)
            self.setParent(parent)

    class MainWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("EDFReader GUI")
            self.dataset = None

            main_layout = QVBoxLayout(self)
            file_layout = QHBoxLayout()
            self.file_label = QLabel("EDF: (none)")
            browse_btn = QPushButton("Browse EDF...")
            browse_btn.clicked.connect(self.browse_edf)
            file_layout.addWidget(self.file_label)
            file_layout.addWidget(browse_btn)
            main_layout.addLayout(file_layout)

            form = QFormLayout()
            self.channel_combo = QComboBox()
            self.channel_combo.setEnabled(False)
            form.addRow("Channel:", self.channel_combo)

            self.target_hz_spin = QDoubleSpinBox()
            self.target_hz_spin.setRange(1, 500)
            self.target_hz_spin.setDecimals(2)
            self.target_hz_spin.setValue(16.0)
            self.target_hz_spin.setSuffix(" Hz")
            form.addRow("Target sfreq:", self.target_hz_spin)

            self.t_start_spin = QDoubleSpinBox()
            self.t_start_spin.setRange(0, 1e6)
            self.t_start_spin.setDecimals(2)
            self.t_start_spin.setValue(0.0)
            self.t_start_spin.setSuffix(" s")

            self.t_len_spin = QDoubleSpinBox()
            self.t_len_spin.setRange(0.1, 1e6)
            self.t_len_spin.setDecimals(2)
            self.t_len_spin.setValue(60.0)
            self.t_len_spin.setSuffix(" s")
            form.addRow("Start time:", self.t_start_spin)
            form.addRow("Window length:", self.t_len_spin)
            main_layout.addLayout(form)

            btn_layout = QHBoxLayout()
            self.analyze_btn = QPushButton("Compute amplitude + scalogram")
            self.analyze_btn.setEnabled(False)
            self.analyze_btn.clicked.connect(self.run_analysis)
            self.save_btn = QPushButton("Save PNG")
            self.save_btn.setEnabled(False)
            self.save_btn.clicked.connect(self.save_png)
            btn_layout.addStretch(1)
            btn_layout.addWidget(self.analyze_btn)
            btn_layout.addWidget(self.save_btn)
            main_layout.addLayout(btn_layout)

            self.canvas = MplCanvas(self)
            main_layout.addWidget(self.canvas)

        def browse_edf(self):
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select EDF file",
                str(PROJECT_ROOT / "samples"),
                "EDF files (*.edf);;All files (*)",
            )
            if not path:
                return
            try:
                self.dataset = SignalDataset(path)
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to load EDF:\n{exc}")
                return

            self.file_label.setText(f"EDF: {Path(path).name}")
            self.channel_combo.clear()
            self.channel_combo.addItems(self.dataset.ch_names)
            self.channel_combo.setEnabled(True)
            self.analyze_btn.setEnabled(True)
            self.save_btn.setEnabled(False)

        def run_analysis(self):
            if self.dataset is None:
                QMessageBox.warning(self, "No data", "Please load an EDF file first.")
                return

            ch_name = self.channel_combo.currentText()
            if ch_name not in self.dataset.ch_names:
                QMessageBox.warning(self, "Channel error", f"Channel {ch_name} not found.")
                return

            try:
                ds = SignalDataset(self.dataset.edf_path)
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to reload EDF:\n{exc}")
                return

            ds.select_channels([ch_name])
            target_hz = float(self.target_hz_spin.value())
            if ds.sfreq <= target_hz:
                QMessageBox.warning(
                    self,
                    "Downsample error",
                    f"Current sfreq {ds.sfreq} Hz <= target {target_hz} Hz.",
                )
                return

            ds.downsample(target_hz)
            t_start = float(self.t_start_spin.value())
            t_end = t_start + float(self.t_len_spin.value())
            ds.crop(tmin=t_start, tmax=t_end)
            if ds.data.shape[1] < 10:
                QMessageBox.warning(self, "Window too short", "Not enough samples in window.")
                return

            sig = ds.data[0]
            times = ds.times
            try:
                amp_t, amp_y = compute_ppg_amplitude(sig, times=times, sfreq=ds.sfreq)
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to compute amplitude:\n{exc}")
                return

            try:
                times_s, freqs, coefs_mag = cwt_scalogram(
                    sig[np.newaxis, :],
                    ds.sfreq,
                    fmin=0.5,
                    fmax=min(8.0, ds.sfreq / 2 - 0.1),
                    n_scales=64,
                    axis=1,
                )
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to compute scalogram:\n{exc}")
                return
            coefs_mag = coefs_mag[0]

            for ax in self.canvas.axes:
                ax.clear()
            ax0, ax1, ax2 = self.canvas.axes

            ax0.plot(times, sig, linewidth=0.5)
            ax0.set_ylabel(ch_name)
            ax0.set_title("Raw signal")
            ax0.set_xlim(times[0], times[-1])
            ax0.grid(True, alpha=0.3)

            if len(amp_t) > 0:
                step_t = np.concatenate([[times[0]], amp_t])
                step_y = np.concatenate([[amp_y[0]], amp_y])
                ax1.step(step_t, step_y, where="post", color="C1")
            ax1.set_ylabel("Amplitude")
            ax1.set_title("PPG amplitude (per cycle)")
            ax1.set_xlim(times[0], times[-1])
            ax1.grid(True, alpha=0.3)

            pcm = ax2.pcolormesh(
                times_s,
                freqs,
                coefs_mag,
                shading="auto",
                cmap="viridis",
            )
            self.canvas.figure.colorbar(pcm, ax=ax2, label="|CWT|")
            ax2.set_ylabel("Frequency (Hz)")
            ax2.set_xlabel("Time (s)")
            ax2.set_title("Scalogram")
            ax2.set_yscale("log")
            ax2.set_xlim(times_s[0], times_s[-1])
            self.canvas.draw()
            self.save_btn.setEnabled(True)

        def save_png(self):
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save current figure",
                "figure.png",
                "PNG files (*.png);;All files (*)",
            )
            if not path:
                return
            try:
                self.canvas.figure.savefig(path, dpi=150, bbox_inches="tight")
            except Exception as exc:
                QMessageBox.critical(self, "Save error", f"Failed to save figure:\n{exc}")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 800)
    window.show()
    return app.exec()


def main():
    parser = argparse.ArgumentParser(
        description="EDFReader unified launcher (GUI or CLI)."
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Run mode (default: gui).",
    )
    args, remaining = parser.parse_known_args()

    if args.mode == "gui":
        if remaining:
            print("Warning: extra arguments are ignored in GUI mode:", " ".join(remaining))
        return _run_gui()
    return _run_cli(remaining)


if __name__ == "__main__":
    sys.exit(main())
