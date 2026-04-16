"""
PyQt6 + PyQtGraph GUI for EDFReader.

Pages (QTabWidget):
  1) Raw + PPG amplitude (step)
  2) PPI (step) + PPI scalogram
  3) Raw scalogram (|CWT|)
  4) Amplitude scalogram
  5) Spectrogram

Multi-window strategy:
  - window_index selects [window_index * window_len, (index+1) * window_len)
  - compute is on-demand (only current window is computed)
  - a small LRU cache keeps last 2 windows for fast back-and-forth
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from analysis import cwt_scalogram, compute_ppg_amplitude, compute_ppi, spectrogram
from data import SignalDataset
from preprocessing.downsample import downsample as ds_downsample


pg.setConfigOptions(antialias=True)


@dataclass
class BaseData:
    sig: np.ndarray  # shape (n_samples,)
    times: np.ndarray  # shape (n_samples,), relative time from 0
    sfreq: float
    duration_s: float


def _step_from_samples(
    x0: float,
    x_endpoints: np.ndarray,
    y_endpoints: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert endpoint samples into a step series for plotting.

    Output:
      step_x: [x0, x_endpoints...]
      step_y: [y_endpoints[0], y_endpoints...]
    """
    if x_endpoints.size == 0 or y_endpoints.size == 0:
        return np.array([x0]), np.array([0.0])
    step_x = np.concatenate([[x0], x_endpoints])
    step_y = np.concatenate([[y_endpoints[0]], y_endpoints])
    return step_x, step_y


class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)


class PrepareBaseWorker(QtCore.QRunnable):
    def __init__(
        self,
        signals: WorkerSignals,
        dataset_full: SignalDataset,
        ch_index: int,
        target_hz: float,
    ):
        super().__init__()
        self._signals = signals
        self._dataset_full = dataset_full
        self._ch_index = ch_index
        self._target_hz = target_hz

    @staticmethod
    def _make_base(
        data_1d: np.ndarray,
        sfreq_orig: float,
        target_hz: float,
    ) -> BaseData:
        if target_hz >= sfreq_orig:
            raise ValueError(
                f"target_hz ({target_hz}) must be < original sfreq ({sfreq_orig})"
            )

        sig = data_1d[np.newaxis, :]
        if target_hz == sfreq_orig:
            sig_ds = sig
        else:
            sig_ds = ds_downsample(sig, sfreq_orig, target_hz, axis=1, antialias=True)
        sig_ds = sig_ds[0].astype(float, copy=False)

        n = sig_ds.shape[0]
        times = np.arange(n, dtype=float) / float(target_hz)
        duration_s = float(n) / float(target_hz)
        return BaseData(sig=sig_ds, times=times, sfreq=float(target_hz), duration_s=duration_s)

    def run(self):
        try:
            orig_sfreq = float(self._dataset_full.sfreq)
            data = self._dataset_full.data
            sig_1d = data[self._ch_index]
            base = self._make_base(sig_1d, orig_sfreq, float(self._target_hz))
            self._signals.finished.emit(base)
        except Exception as e:
            self._signals.error.emit(str(e))


class ComputeWindowWorker(QtCore.QRunnable):
    def __init__(
        self,
        signals: WorkerSignals,
        base: BaseData,
        window_index: int,
        window_len_s: float,
        scalogram_n_scales: int,
        scalogram_fmax_hz: float,
    ):
        super().__init__()
        self._signals = signals
        self._base = base
        self._window_index = window_index
        self._window_len_s = window_len_s
        self._scalogram_n_scales = scalogram_n_scales
        self._scalogram_fmax_hz = scalogram_fmax_hz

    @staticmethod
    def _safe_fmax(sfreq: float, fmax_hz: float) -> float:
        # Mirror existing scripts: clamp to below Nyquist.
        return float(min(fmax_hz, sfreq / 2.0 - 0.1))

    def run(self):
        try:
            base = self._base
            sfreq = base.sfreq
            t_start = float(self._window_index) * float(self._window_len_s)
            if t_start < 0:
                raise ValueError("window_index must be >= 0")

            # Compute window sample indices
            start_idx = int(np.floor(t_start * sfreq))
            end_time = min(t_start + float(self._window_len_s), base.duration_s)
            end_idx = int(np.ceil(end_time * sfreq))

            if end_idx <= start_idx + 2:
                raise ValueError("Window too short for computation.")

            sig = base.sig[start_idx:end_idx]
            times_abs = base.times[start_idx:end_idx]
            # Use relative time [0, window_len]
            times = times_abs - times_abs[0]

            # ----- PPG amplitude + PPI -----
            amp_t, amp_y = compute_ppg_amplitude(sig, times=times, sfreq=sfreq)
            peak_times, ppi = compute_ppi(sig, times=times, sfreq=sfreq)

            # Sample-aligned series for scalogram
            if amp_t.size > 1:
                amp_series = np.interp(times, amp_t, amp_y, left=float(amp_y[0]), right=float(amp_y[-1]))
            else:
                amp_series = np.zeros_like(times, dtype=float)

            ppi_t = peak_times[1:] if peak_times.size > 1 else np.array([], dtype=float)
            if ppi_t.size > 1:
                ppi_series = np.interp(times, ppi_t, ppi, left=float(ppi[0]), right=float(ppi[-1]))
            else:
                ppi_series = np.zeros_like(times, dtype=float)

            # Step series (end of each cycle / interval)
            step_x_amp, step_y_amp = _step_from_samples(0.0, amp_t, amp_y)

            if ppi.size > 0:
                step_x_ppi = np.concatenate([[0.0], ppi_t])
                step_y_ppi = np.concatenate([[float(ppi[0])], ppi])
            else:
                step_x_ppi = np.array([0.0], dtype=float)
                step_y_ppi = np.array([0.0], dtype=float)

            # ----- Scalograms -----
            fmax_local = self._safe_fmax(sfreq, self._scalogram_fmax_hz)
            raw_times_s, raw_freqs, raw_coefs = cwt_scalogram(
                sig[np.newaxis, :],
                sfreq,
                fmin=0.1,
                fmax=fmax_local,
                n_scales=self._scalogram_n_scales,
                axis=1,
            )
            raw_coefs = raw_coefs[0]

            amp_times_s, amp_freqs, amp_coefs = cwt_scalogram(
                amp_series[np.newaxis, :],
                sfreq,
                fmin=0.01,
                fmax=fmax_local,
                n_scales=self._scalogram_n_scales,
                axis=1,
            )
            amp_coefs = amp_coefs[0]

            ppi_times_s, ppi_freqs, ppi_coefs = cwt_scalogram(
                ppi_series[np.newaxis, :],
                sfreq,
                fmin=0.01,
                fmax=fmax_local,
                n_scales=self._scalogram_n_scales,
                axis=1,
            )
            ppi_coefs = ppi_coefs[0]

            # ----- Spectrogram -----
            # Use a reasonable nperseg for windowed visualization.
            nperseg = min(256, max(64, int(len(sig) // 8)))
            freqs_spec, times_spec, Sxx = spectrogram(
                sig[np.newaxis, :],
                sfreq,
                nperseg=nperseg,
                axis=1,
            )
            Sxx = Sxx[0]
            Sxx_db = 10.0 * np.log10(Sxx + 1e-10)

            self._signals.finished.emit(
                {
                    "t_start": t_start,
                    "times": times,
                    "sig": sig,
                    "amp_t": amp_t,
                    "amp_y": amp_y,
                    "amp_series": amp_series,
                    "step_x_amp": step_x_amp,
                    "step_y_amp": step_y_amp,
                    "peak_times": peak_times,
                    "ppi": ppi,
                    "ppi_t": ppi_t,
                    "ppi_series": ppi_series,
                    "step_x_ppi": step_x_ppi,
                    "step_y_ppi": step_y_ppi,
                    "raw": (raw_times_s, raw_freqs, raw_coefs),
                    "amp_scalogram": (amp_times_s, amp_freqs, amp_coefs),
                    "ppi_scalogram": (ppi_times_s, ppi_freqs, ppi_coefs),
                    "spectrogram": (freqs_spec, times_spec, Sxx_db),
                }
            )
        except Exception as e:
            self._signals.error.emit(str(e))


class EDFReaderPyQt6(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDFReader - PyQt6 + PyQtGraph")

        self._thread_pool = QtCore.QThreadPool.globalInstance()
        self._dataset_full: Optional[SignalDataset] = None

        self._base_key: Optional[Tuple[str, str, float]] = None
        self._base: Optional[BaseData] = None
        self._window_cache: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
        self._cache_limit = 2

        # --- UI: controls row ---
        central = QtWidgets.QWidget(self)
        root_layout = QtWidgets.QVBoxLayout(central)
        self.setCentralWidget(central)

        top_layout = QtWidgets.QHBoxLayout()
        root_layout.addLayout(top_layout)

        self.file_label = QtWidgets.QLabel("EDF: (none)")
        top_layout.addWidget(self.file_label, stretch=3)

        browse_btn = QtWidgets.QPushButton("Browse EDF...")
        browse_btn.clicked.connect(self._browse_edf)
        top_layout.addWidget(browse_btn, stretch=0)

        self.channel_combo = QtWidgets.QComboBox()
        self.channel_combo.setEnabled(False)
        top_layout.addWidget(QtWidgets.QLabel("Channel:"), stretch=0)
        top_layout.addWidget(self.channel_combo, stretch=1)

        self.target_hz_spin = QtWidgets.QDoubleSpinBox()
        self.target_hz_spin.setRange(1.0, 500.0)
        self.target_hz_spin.setDecimals(2)
        self.target_hz_spin.setValue(16.0)
        self.target_hz_spin.setSuffix(" Hz")
        top_layout.addWidget(QtWidgets.QLabel("Target sfreq:"), stretch=0)
        top_layout.addWidget(self.target_hz_spin, stretch=1)

        self.window_len_spin = QtWidgets.QDoubleSpinBox()
        self.window_len_spin.setRange(0.1, 1e6)
        self.window_len_spin.setDecimals(2)
        self.window_len_spin.setValue(60.0)
        self.window_len_spin.setSuffix(" s")
        top_layout.addWidget(QtWidgets.QLabel("Window length:"), stretch=0)
        top_layout.addWidget(self.window_len_spin, stretch=1)

        self.window_index_spin = QtWidgets.QSpinBox()
        self.window_index_spin.setRange(0, 0)
        self.window_index_spin.setValue(0)
        top_layout.addWidget(QtWidgets.QLabel("Window index:"), stretch=0)
        top_layout.addWidget(self.window_index_spin, stretch=1)

        nav_layout = QtWidgets.QHBoxLayout()
        root_layout.addLayout(nav_layout)
        prev_btn = QtWidgets.QPushButton("Prev")
        next_btn = QtWidgets.QPushButton("Next")
        prev_btn.clicked.connect(self._prev_window)
        next_btn.clicked.connect(self._next_window)
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)

        self.compute_btn = QtWidgets.QPushButton("Compute current window")
        self.compute_btn.setEnabled(False)
        self.compute_btn.clicked.connect(self._compute_current_window)
        nav_layout.addWidget(self.compute_btn, stretch=0)

        self.save_btn = QtWidgets.QPushButton("Save current Tab PNG")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_current_tab_png)
        nav_layout.addWidget(self.save_btn, stretch=0)

        self.status_label = QtWidgets.QLabel("")
        nav_layout.addWidget(self.status_label, stretch=1)

        # --- UI: tabs ---
        self.tabs = QtWidgets.QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)

        # Tab 1: raw + amp step
        self.tab_raw_amp = QtWidgets.QWidget()
        v1 = QtWidgets.QVBoxLayout(self.tab_raw_amp)
        self.plot_raw = pg.PlotWidget()
        self.plot_raw.setBackground(None)
        self.plot_raw.setLabel("bottom", "Time", "s")
        self.plot_raw.setLabel("left", "Signal", "")
        v1.addWidget(self.plot_raw, stretch=1)

        self.plot_amp_step = pg.PlotWidget()
        self.plot_amp_step.setBackground(None)
        self.plot_amp_step.setLabel("bottom", "Time", "s")
        self.plot_amp_step.setLabel("left", "Amplitude", "")
        v1.addWidget(self.plot_amp_step, stretch=1)
        self.tabs.addTab(self.tab_raw_amp, "Raw + Amp")

        # Tab 2: ppi step + ppi scalogram
        self.tab_ppi = QtWidgets.QWidget()
        v2 = QtWidgets.QVBoxLayout(self.tab_ppi)
        self.plot_ppi_step = pg.PlotWidget()
        self.plot_ppi_step.setBackground(None)
        self.plot_ppi_step.setLabel("bottom", "Time", "s")
        self.plot_ppi_step.setLabel("left", "PPI", "s")
        v2.addWidget(self.plot_ppi_step, stretch=1)

        self.plot_ppi_scal = pg.PlotWidget()
        self.plot_ppi_scal.setBackground(None)
        self.plot_ppi_scal.setLabel("bottom", "Time", "s")
        self.plot_ppi_scal.setLabel("left", "Frequency", "Hz")
        vb = self.plot_ppi_scal.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        v2.addWidget(self.plot_ppi_scal, stretch=1)
        self.tabs.addTab(self.tab_ppi, "PPI + PPI Scal")

        # Tab 3: raw scalogram
        self.tab_raw_scal = QtWidgets.QWidget()
        v3 = QtWidgets.QVBoxLayout(self.tab_raw_scal)
        self.plot_raw_scal = pg.PlotWidget()
        self.plot_raw_scal.setBackground(None)
        self.plot_raw_scal.setLabel("bottom", "Time", "s")
        self.plot_raw_scal.setLabel("left", "Frequency", "Hz")
        vb = self.plot_raw_scal.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        v3.addWidget(self.plot_raw_scal)
        self.tabs.addTab(self.tab_raw_scal, "Raw Scalogram")

        # Tab 4: amp scalogram
        self.tab_amp_scal = QtWidgets.QWidget()
        v4 = QtWidgets.QVBoxLayout(self.tab_amp_scal)
        self.plot_amp_scal = pg.PlotWidget()
        self.plot_amp_scal.setBackground(None)
        self.plot_amp_scal.setLabel("bottom", "Time", "s")
        self.plot_amp_scal.setLabel("left", "Frequency", "Hz")
        vb = self.plot_amp_scal.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        v4.addWidget(self.plot_amp_scal)
        self.tabs.addTab(self.tab_amp_scal, "Amp Scalogram")

        # Tab 5: spectrogram
        self.tab_spec = QtWidgets.QWidget()
        v5 = QtWidgets.QVBoxLayout(self.tab_spec)
        self.plot_spec = pg.PlotWidget()
        self.plot_spec.setBackground(None)
        self.plot_spec.setLabel("bottom", "Time", "s")
        self.plot_spec.setLabel("left", "Frequency", "Hz")
        vb = self.plot_spec.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        v5.addWidget(self.plot_spec)
        self.tabs.addTab(self.tab_spec, "Spectrogram")

        # Image items for scalograms/spectrogram (reuse & update)
        self._img_raw_scal: Optional[pg.ImageItem] = None
        self._img_amp_scal: Optional[pg.ImageItem] = None
        self._img_ppi_scal: Optional[pg.ImageItem] = None
        self._img_spec: Optional[pg.ImageItem] = None

        self._line_raw: Optional[pg.PlotDataItem] = None
        self._line_amp_step: Optional[pg.PlotDataItem] = None
        self._line_ppi_step: Optional[pg.PlotDataItem] = None

        # React when tab changes (used for optional update)
        self.tabs.currentChanged.connect(lambda _: None)

        self.resize(1200, 900)

    def _set_status(self, text: str):
        self.status_label.setText(text)

    def _browse_edf(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select EDF file",
            str(Path(__file__).resolve().parent / "samples"),
            "EDF files (*.edf);;All files (*)",
        )
        if not path:
            return
        self._load_dataset_full(path)

    def _load_dataset_full(self, edf_path: str):
        self._set_status("Loading EDF (this may take time)...")
        self.compute_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.channel_combo.setEnabled(False)

        # Load in UI thread for simplicity; SignalDataset already preloads.
        # If you want fully async, we can move it to a worker later.
        ds = SignalDataset(str(edf_path))
        self._dataset_full = ds
        self.channel_combo.clear()
        self.channel_combo.addItems(ds.ch_names)
        self.channel_combo.setEnabled(True)

        self.file_label.setText(f"EDF: {Path(edf_path).name}")

        # Reset base and caches
        self._base_key = None
        self._base = None
        self._window_cache.clear()

        # Update window index range based on current window length
        duration_s = float(ds.data.shape[1]) / float(ds.sfreq)
        win_len = float(self.window_len_spin.value())
        n_windows = max(1, int(np.ceil(duration_s / win_len)))
        self.window_index_spin.setRange(0, n_windows - 1)
        self.window_index_spin.setValue(0)

        self.compute_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self._set_status("Ready.")

        # When window length changes, update max index
        self.window_len_spin.valueChanged.connect(self._update_window_range)

        # When base parameters change, clear base/cache and recompute on demand
        self.channel_combo.currentIndexChanged.connect(self._invalidate_base)
        self.target_hz_spin.valueChanged.connect(self._invalidate_base)

    def _update_window_range(self):
        if self._dataset_full is None:
            return
        duration_s = float(self._dataset_full.data.shape[1]) / float(self._dataset_full.sfreq)
        win_len = float(self.window_len_spin.value())
        n_windows = max(1, int(np.ceil(duration_s / win_len)))
        cur = int(self.window_index_spin.value())
        self.window_index_spin.setRange(0, n_windows - 1)
        self.window_index_spin.setValue(min(cur, n_windows - 1))

    def _invalidate_base(self):
        self._base_key = None
        self._base = None
        self._window_cache.clear()
        self.save_btn.setEnabled(False)
        # compute button remains enabled; it will rebuild base on-demand

    def _prev_window(self):
        self.window_index_spin.setValue(max(0, int(self.window_index_spin.value()) - 1))
        self._compute_if_cached()

    def _next_window(self):
        self.window_index_spin.setValue(min(self.window_index_spin.maximum(), int(self.window_index_spin.value()) + 1))
        self._compute_if_cached()

    def _compute_if_cached(self):
        # Only update when cached; otherwise wait for user click compute.
        idx = int(self.window_index_spin.value())
        if idx in self._window_cache:
            self._apply_results(self._window_cache[idx])

    def _compute_current_window(self):
        if self._dataset_full is None:
            return
        if self._base_key is None or self._base is None:
            self._prepare_base_then_compute()
            return
        self._compute_window_on_demand()

    def _prepare_base_then_compute(self):
        if self._dataset_full is None:
            return
        ch_name = self.channel_combo.currentText()
        if not ch_name:
            return
        ch_index = self._dataset_full.ch_names.index(ch_name)
        target_hz = float(self.target_hz_spin.value())

        key = (self._dataset_full.edf_path, ch_name, target_hz)
        if key == self._base_key and self._base is not None:
            self._compute_window_on_demand()
            return

        # Compute base in background
        self._set_status("Preparing base (downsample)...")
        self.compute_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

        signals = WorkerSignals()
        signals.finished.connect(self._on_base_ready)
        signals.error.connect(self._on_error)

        worker = PrepareBaseWorker(
            signals=signals,
            dataset_full=self._dataset_full,
            ch_index=ch_index,
            target_hz=target_hz,
        )
        worker.setAutoDelete(True)
        self._base_key = key
        self._window_cache.clear()
        self._base = None
        self._thread_pool.start(worker)

    def _on_base_ready(self, base: BaseData):
        self._base = base
        self._set_status("Base ready. Computing window...")
        self.compute_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self._compute_window_on_demand()

    def _on_error(self, msg: str):
        self.compute_btn.setEnabled(True)
        self._set_status(f"Error: {msg}")

    def _compute_window_on_demand(self):
        if self._base is None:
            return
        idx = int(self.window_index_spin.value())
        win_len = float(self.window_len_spin.value())

        if idx in self._window_cache:
            self._apply_results(self._window_cache[idx])
            return

        self._set_status("Computing current window (CWT/FFT)...")
        self.compute_btn.setEnabled(False)

        signals = WorkerSignals()
        signals.finished.connect(self._on_window_ready)
        signals.error.connect(self._on_error)

        # scalogram settings: keep consistent with existing scripts
        worker = ComputeWindowWorker(
            signals=signals,
            base=self._base,
            window_index=idx,
            window_len_s=win_len,
            scalogram_n_scales=64,
            scalogram_fmax_hz=float(self._base.sfreq),  # will be clamped inside worker
        )
        worker.setAutoDelete(True)
        self._thread_pool.start(worker)

    def _on_window_ready(self, results: Dict[str, Any]):
        idx = int(self.window_index_spin.value())

        # LRU-ish cache
        self._window_cache[idx] = results
        self._window_cache.move_to_end(idx)
        while len(self._window_cache) > self._cache_limit:
            self._window_cache.popitem(last=False)

        self._apply_results(results)
        self.compute_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self._set_status("Done.")

    def _clear_plot(self, plot: pg.PlotWidget):
        plot.clear()

    def _ensure_image(self, plot: pg.PlotWidget, existing: Optional[pg.ImageItem]) -> pg.ImageItem:
        if existing is not None:
            return existing
        img = pg.ImageItem()
        plot.addItem(img)
        return img

    def _apply_results(self, r: Dict[str, Any]):
        # ---- Tab 1: Raw + Amp ----
        self.plot_raw.clear()
        self.plot_amp_step.clear()

        times = r["times"]
        sig = r["sig"]
        step_x_amp = r["step_x_amp"]
        step_y_amp = r["step_y_amp"]

        self.plot_raw.plot(times, sig, pen=pg.mkPen("w", width=1.0))
        self.plot_raw.setLabel("left", self.channel_combo.currentText(), "")
        self.plot_raw.setLabel("bottom", "Time", "s")

        # step mode: PlotWidget.plot supports stepMode in newer pg
        # We'll use plot with connect='finite' + manual step arrays by providing x/y.
        self.plot_amp_step.plot(
            step_x_amp,
            step_y_amp,
            stepMode=True,
            pen=pg.mkPen("c", width=1.2),
        )
        self.plot_amp_step.setLabel("left", "Amplitude", "")
        self.plot_amp_step.setLabel("bottom", "Time", "s")

        # ---- Tab 2: PPI step + PPI scalogram ----
        self.plot_ppi_step.clear()
        self.plot_ppi_scal.clear()

        self.plot_ppi_step.plot(
            r["step_x_ppi"],
            r["step_y_ppi"],
            stepMode=True,
            pen=pg.mkPen("m", width=1.2),
        )
        self.plot_ppi_step.setLabel("left", "PPI", "s")
        self.plot_ppi_step.setLabel("bottom", "Time", "s")

        raw_times_s, raw_freqs, raw_coefs = r["raw"]
        _, _, ppi_coefs = r["ppi_scalogram"]
        ppi_times_s, ppi_freqs, ppi_coefs = r["ppi_scalogram"]

        img_ppi = pg.ImageItem()
        self.plot_ppi_scal.addItem(img_ppi)
        img_ppi.setImage(ppi_coefs)
        img_ppi.setAutoDownsample(False)
        img_ppi.setRect(
            QtCore.QRectF(
                float(ppi_times_s[0]),
                float(ppi_freqs[0]),
                float(ppi_times_s[-1] - ppi_times_s[0]),
                float(ppi_freqs[-1] - ppi_freqs[0]),
            )
        )
        vb = self.plot_ppi_scal.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        self.plot_ppi_scal.setLabel("left", "Frequency", "Hz")
        self.plot_ppi_scal.setLabel("bottom", "Time", "s")

        # ---- Tab 3: Raw scalogram ----
        self.plot_raw_scal.clear()
        raw_times_s, raw_freqs, raw_coefs = r["raw"]
        img_raw = pg.ImageItem()
        self.plot_raw_scal.addItem(img_raw)
        img_raw.setImage(raw_coefs)
        img_raw.setAutoDownsample(False)
        img_raw.setRect(
            QtCore.QRectF(
                float(raw_times_s[0]),
                float(raw_freqs[0]),
                float(raw_times_s[-1] - raw_times_s[0]),
                float(raw_freqs[-1] - raw_freqs[0]),
            )
        )
        vb = self.plot_raw_scal.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        self.plot_raw_scal.setLabel("left", "Frequency", "Hz")
        self.plot_raw_scal.setLabel("bottom", "Time", "s")

        # ---- Tab 4: Amp scalogram ----
        self.plot_amp_scal.clear()
        amp_times_s, amp_freqs, amp_coefs = r["amp_scalogram"]
        img_amp = pg.ImageItem()
        self.plot_amp_scal.addItem(img_amp)
        img_amp.setImage(amp_coefs)
        img_amp.setAutoDownsample(False)
        img_amp.setRect(
            QtCore.QRectF(
                float(amp_times_s[0]),
                float(amp_freqs[0]),
                float(amp_times_s[-1] - amp_times_s[0]),
                float(amp_freqs[-1] - amp_freqs[0]),
            )
        )
        vb = self.plot_amp_scal.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        self.plot_amp_scal.setLabel("left", "Frequency", "Hz")
        self.plot_amp_scal.setLabel("bottom", "Time", "s")

        # ---- Tab 5: Spectrogram ----
        self.plot_spec.clear()
        freqs_spec, times_spec, Sxx_db = r["spectrogram"]
        img_spec = pg.ImageItem()
        self.plot_spec.addItem(img_spec)
        img_spec.setImage(Sxx_db)
        img_spec.setAutoDownsample(False)
        img_spec.setRect(
            QtCore.QRectF(
                float(times_spec[0]),
                float(freqs_spec[0]),
                float(times_spec[-1] - times_spec[0]),
                float(freqs_spec[-1] - freqs_spec[0]),
            )
        )
        vb = self.plot_spec.getViewBox()
        vb.setLogMode(vb.YAxis, True)
        self.plot_spec.setLabel("left", "Frequency", "Hz")
        self.plot_spec.setLabel("bottom", "Time", "s")

    def _save_current_tab_png(self):
        cur = self.tabs.currentIndex()
        w = self.tabs.currentWidget()
        if w is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save PNG",
            f"window_{self.window_index_spin.value()}_tab{cur}.png",
            "PNG files (*.png);;All files (*)",
        )
        if not path:
            return

        # QWidget.grab() captures current pixels; it is portable for this project.
        pix = w.grab()
        ok = pix.save(path, "PNG")
        if not ok:
            QtWidgets.QMessageBox.critical(self, "Save error", "Failed to save PNG.")


def run_gui():
    app = QtWidgets.QApplication([])
    win = EDFReaderPyQt6()
    win.show()
    return app.exec()

