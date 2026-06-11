"""
PyQt6 + PyQtGraph GUI for EDFReader.

Pages (QTabWidget):
  1) Signal + matching scalogram (Raw/BBI/Amplitude selectable)
  2) Spectrogram

Multi-window strategy:
  - window_start (s) selects [window_start, window_start + window_len)
  - compute is on-demand (only current window is computed)
  - a small LRU cache keeps last 2 windows for fast back-and-forth
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtWidgets
import pyqtgraph as pg

from core.errors import EDFViewerError
from core.models import AnalysisResult, EDFMetadata
from core.parameters import AnalysisParameters
from core.workflow import EDFViewerWorkflow


pg.setConfigOptions(antialias=True)


def _resample_rows_to_uniform_axis(
    values: np.ndarray,
    source_axis: np.ndarray,
    output_axis: np.ndarray,
) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    source_axis = np.asarray(source_axis, dtype=float).ravel()
    output_axis = np.asarray(output_axis, dtype=float).ravel()
    if values.ndim != 2:
        raise ValueError(f"values must be 2-D (n_y, n_x), got shape {values.shape}")
    if source_axis.size != values.shape[0]:
        raise ValueError(
            f"source_axis length {source_axis.size} does not match values rows {values.shape[0]}"
        )
    if np.allclose(source_axis, output_axis, rtol=0.0, atol=1e-12):
        return values
    out = np.empty((output_axis.size, values.shape[1]), dtype=float)
    for j in range(values.shape[1]):
        out[:, j] = np.interp(output_axis, source_axis, values[:, j])
    return out


def _prepare_frequency_image(
    values: np.ndarray,
    freqs_hz: np.ndarray,
    *,
    log_axis: bool,
    resample_linear_hz: bool,
) -> Tuple[np.ndarray, np.ndarray, Tuple[float, float], str]:
    values = np.asarray(values, dtype=float)
    freqs_hz = np.asarray(freqs_hz, dtype=float).ravel()
    order = np.argsort(freqs_hz)
    freqs_hz = freqs_hz[order]
    values = values[order, :]
    f0 = max(float(freqs_hz[0]), 1e-6)
    f1 = max(float(freqs_hz[-1]), f0 * 1.001)

    if log_axis:
        log_freqs = np.log10(np.maximum(freqs_hz, 1e-6))
        display_y = np.linspace(np.log10(f0), np.log10(f1), freqs_hz.size)
        display_values = _resample_rows_to_uniform_axis(values, log_freqs, display_y)
        return display_values, display_y, (display_y[0], display_y[-1]), "log"

    display_y = np.linspace(f0, f1, freqs_hz.size)
    display_values = (
        _resample_rows_to_uniform_axis(values, freqs_hz, display_y)
        if resample_linear_hz
        else values
    )
    return display_values, display_y, (f0 - 5.0, f1 + 5.0), "linear"


def _default_stft_window_s(sfreq: float, n_samples: int) -> float:
    """Default STFT segment length (seconds) for a window of n_samples."""
    nperseg = min(256, max(64, int(n_samples) // 8))
    return float(nperseg) / float(sfreq)


# PyWavelets names supported by pywt.cwt (see analysis.freq_domain.cwt_scalogram).
WAVELET_CHOICES = [
    "cmor1.5-1.0",  # complex Morlet (default)
    "morl",         # real Morlet
    "mexh",         # Mexican hat
    "haar",         # Haar (custom CWT; not in pywt continuous family)
    "gaus1",
    "gaus2",
    "cgau1",
    "shan0.5-1.0",
]

SPECTROGRAM_DYNAMIC_RANGE_DB = 80.0


def _step_from_samples(
    x0: float,
    x_endpoints: np.ndarray,
    y_endpoints: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert endpoint samples into a step series for plotting.

    PyQtGraph ``stepMode=True`` requires len(step_x) == len(step_y) + 1: ``y[i]``
    is held constant on ``[step_x[i], step_x[i + 1])``. Here ``x_endpoints`` and
    ``y_endpoints`` have the same length (one time and one level per cycle).
    """
    if x_endpoints.size == 0 or y_endpoints.size == 0:
        # Degenerate: one flat segment so step lengths stay valid.
        return np.array([float(x0), float(x0) + 1e-9]), np.array([0.0])
    step_x = np.concatenate([[x0], x_endpoints])
    step_y = np.asarray(y_endpoints, dtype=float)
    return step_x, step_y


def _spectrogram_display_levels(
    values_db: np.ndarray,
    dynamic_range_db: float = SPECTROGRAM_DYNAMIC_RANGE_DB,
) -> Tuple[float, float]:
    """Choose display levels that keep numerical floor from becoming visible bands."""
    values = np.asarray(values_db, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return (0.0, 1.0)
    hi = float(np.nanmax(finite))
    lo = hi - float(dynamic_range_db)
    if lo >= hi:
        lo = hi - 1e-9
    return (lo, hi)


def _gui_results_from_analysis(result: AnalysisResult) -> Dict[str, Any]:
    t_start = float(result.source.window_start_s)
    step_x_amp, step_y_amp = _step_from_samples(
        t_start,
        t_start + result.amplitude_times_s,
        result.amplitude_values,
    )
    step_x_bbi, step_y_bbi = _step_from_samples(
        t_start,
        t_start + result.bbi_times_s,
        result.bbi_values_s,
    )
    return {
        "t_start": t_start,
        "window_len_s": result.source.window_length_s,
        "times": t_start + result.times_s,
        "sig": result.raw_signal,
        "amp_t": t_start + result.amplitude_times_s,
        "amp_y": result.amplitude_values,
        "step_x_amp": step_x_amp,
        "step_y_amp": step_y_amp,
        "bbi": result.bbi_values_s,
        "bbi_t": t_start + result.bbi_times_s,
        "step_x_bbi": step_x_bbi,
        "step_y_bbi": step_y_bbi,
        "raw": (
            t_start + result.raw_scalogram.times_s,
            result.raw_scalogram.freqs_hz,
            result.raw_scalogram.values,
        ),
        "amp_scalogram": (
            t_start + result.amplitude_scalogram.times_s,
            result.amplitude_scalogram.freqs_hz,
            result.amplitude_scalogram.values,
        ),
        "bbi_scalogram": (
            t_start + result.bbi_scalogram.times_s,
            result.bbi_scalogram.freqs_hz,
            result.bbi_scalogram.values,
        ),
        "spectrogram": (
            result.spectrogram.freqs_hz,
            t_start + result.spectrogram.times_s,
            result.spectrogram.values,
        ),
        "analysis_result": result,
    }


class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)


class WorkflowComputeWorker(QtCore.QRunnable):
    def __init__(
        self,
        signals: WorkerSignals,
        workflow: EDFViewerWorkflow,
        channel_name: str,
        parameters: AnalysisParameters,
    ):
        super().__init__()
        self._signals = signals
        self._workflow = workflow
        self._channel_name = channel_name
        self._parameters = parameters

    def run(self):
        try:
            result = self._workflow.compute_window(self._channel_name, self._parameters)
            self._signals.finished.emit(result)
        except Exception as e:
            self._signals.error.emit(str(e))


class EDFReaderPyQt6(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDFReader - PyQt6 + PyQtGraph")

        self._thread_pool = QtCore.QThreadPool.globalInstance()
        self._workflow = EDFViewerWorkflow(cache_size=2)
        self._metadata: Optional[EDFMetadata] = None
        self._active_edf_path: Optional[str] = None
        self._active_channel_name: Optional[str] = None

        self._window_cache: "OrderedDict[tuple, Dict[str, Any]]" = (
            OrderedDict()
        )
        self._pending_cache_key: Optional[tuple] = None
        self._cache_limit = 2
        self._freq_axis_log = False

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
        self.target_hz_spin.setToolTip(
            "Analysis sampling rate after optional downsampling. "
            "Maximum equals the EDF channel's original sampling rate (no downsampling at max)."
        )
        top_layout.addWidget(QtWidgets.QLabel("Target sfreq:"), stretch=0)
        top_layout.addWidget(self.target_hz_spin, stretch=1)

        self.window_len_spin = QtWidgets.QDoubleSpinBox()
        self.window_len_spin.setRange(0.1, 1e6)
        self.window_len_spin.setDecimals(2)
        self.window_len_spin.setValue(60.0)
        self.window_len_spin.setSuffix(" s")
        top_layout.addWidget(QtWidgets.QLabel("Window length:"), stretch=0)
        top_layout.addWidget(self.window_len_spin, stretch=1)

        self.window_start_spin = QtWidgets.QDoubleSpinBox()
        self.window_start_spin.setRange(0.0, 0.0)
        self.window_start_spin.setDecimals(2)
        self.window_start_spin.setSingleStep(1.0)
        self.window_start_spin.setValue(0.0)
        self.window_start_spin.setSuffix(" s")
        top_layout.addWidget(QtWidgets.QLabel("Window start:"), stretch=0)
        top_layout.addWidget(self.window_start_spin, stretch=1)

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

        nav_layout.addWidget(QtWidgets.QLabel("Wavelet:"), stretch=0)
        self.wavelet_combo = QtWidgets.QComboBox()
        self.wavelet_combo.addItems(WAVELET_CHOICES)
        self.wavelet_combo.setToolTip(
            "Continuous wavelet for scalogram (PyWavelets). "
            "Changing this clears the window cache; click Compute to refresh."
        )
        self.wavelet_combo.currentTextChanged.connect(self._on_wavelet_changed)
        nav_layout.addWidget(self.wavelet_combo, stretch=1)

        self.freq_axis_log_btn = QtWidgets.QPushButton("Freq Y: Linear")
        self.freq_axis_log_btn.setCheckable(True)
        self.freq_axis_log_btn.setChecked(False)
        self.freq_axis_log_btn.setToolTip(
            "Toggle frequency axis scale for scalogram and spectrogram "
            "(linear Hz vs logarithmic Hz)."
        )
        self.freq_axis_log_btn.clicked.connect(self._on_freq_axis_log_toggled)
        nav_layout.addWidget(self.freq_axis_log_btn, stretch=0)

        self.save_btn = QtWidgets.QPushButton("Save current Tab PNG")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_current_tab_png)
        nav_layout.addWidget(self.save_btn, stretch=0)

        self.status_label = QtWidgets.QLabel("")
        nav_layout.addWidget(self.status_label, stretch=1)

        # --- UI: tabs ---
        self.tabs = QtWidgets.QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)

        # Tab 1: signal + matching scalogram
        self.tab_signal_scal = QtWidgets.QWidget()
        v1 = QtWidgets.QVBoxLayout(self.tab_signal_scal)
        selector_layout = QtWidgets.QHBoxLayout()
        selector_layout.addWidget(QtWidgets.QLabel("Signal view:"), stretch=0)
        self.signal_view_combo = QtWidgets.QComboBox()
        self.signal_view_combo.addItems(["Raw", "BBI", "Amplitude"])
        selector_layout.addWidget(self.signal_view_combo, stretch=1)
        self.fit_xy_btn = QtWidgets.QPushButton("Fit XY")
        self.fit_xy_btn.setToolTip(
            "Fit the time-domain and time-frequency X/Y axes to the current data."
        )
        self.fit_xy_btn.clicked.connect(self._fit_xy)
        selector_layout.addWidget(self.fit_xy_btn, stretch=0)
        v1.addLayout(selector_layout)

        self.plot_signal_step = pg.PlotWidget()
        self.plot_signal_step.setBackground(None)
        self.plot_signal_step.setLabel("bottom", "Time", "s")
        self.plot_signal_step.setLabel("left", "Signal", "")
        v1.addWidget(self.plot_signal_step, stretch=1)

        self.plot_signal_scal = pg.PlotWidget()
        self.plot_signal_scal.setBackground(None)
        self.plot_signal_scal.setLabel("bottom", "Time", "s")
        self.plot_signal_scal.setLabel("left", "Frequency", "Hz")
        self.plot_signal_scal.setLogMode(y=False)
        v1.addWidget(self.plot_signal_scal, stretch=1)
        self.scalogram_lut = pg.HistogramLUTWidget()
        self.scalogram_lut.gradient.loadPreset("viridis")
        self.scalogram_lut.setMinimumHeight(120)
        v1.addWidget(self.scalogram_lut, stretch=0)
        self.tabs.addTab(self.tab_signal_scal, "Signal + Scalogram")

        # Tab 2: spectrogram
        self.tab_spec = QtWidgets.QWidget()
        v2 = QtWidgets.QVBoxLayout(self.tab_spec)
        spec_ctrl = QtWidgets.QHBoxLayout()
        spec_ctrl.addWidget(QtWidgets.QLabel("STFT window:"), stretch=0)
        self.stft_window_spin = QtWidgets.QDoubleSpinBox()
        self.stft_window_spin.setDecimals(2)
        self.stft_window_spin.setRange(0.1, 60.0)
        self.stft_window_spin.setValue(7.5)
        self.stft_window_spin.setSuffix(" s")
        self.stft_window_spin.setToolTip(
            "Short-time Fourier transform segment length (seconds). "
            "Smaller → finer time resolution, coarser frequency resolution."
        )
        self.stft_window_spin.valueChanged.connect(self._on_stft_window_changed)
        spec_ctrl.addWidget(self.stft_window_spin, stretch=1)
        v2.addLayout(spec_ctrl)
        self.plot_spec = pg.PlotWidget()
        self.plot_spec.setBackground(None)
        self.plot_spec.setLabel("bottom", "Time", "s")
        self.plot_spec.setLabel("left", "Frequency", "Hz")
        self.plot_spec.setLogMode(y=False)
        v2.addWidget(self.plot_spec)
        self.tabs.addTab(self.tab_spec, "Spectrogram")

        # Image items for scalogram/spectrogram (reuse & update)
        self._img_signal_scal: Optional[pg.ImageItem] = None
        self._img_spec: Optional[pg.ImageItem] = None

        self._line_signal_step: Optional[pg.PlotDataItem] = None
        self._latest_results: Optional[Dict[str, Any]] = None

        # React when tab changes (used for optional update)
        self.tabs.currentChanged.connect(lambda _: None)
        self.signal_view_combo.currentIndexChanged.connect(self._on_signal_view_changed)

        self.resize(1200, 900)

    def _set_status(self, text: str):
        self.status_label.setText(text)

    def _recording_duration_s(self) -> float:
        if self._metadata is not None:
            return float(self._metadata.duration_s)
        return 0.0

    def _window_cache_key(self) -> tuple:
        return (
            round(float(self.window_start_spin.value()), 4),
            round(float(self.window_len_spin.value()), 4),
            round(float(self.target_hz_spin.value()), 4),
            round(float(self.stft_window_spin.value()), 4),
            self.wavelet_combo.currentText(),
        )

    def _refresh_window_start_range(self, reset: bool = False) -> None:
        duration_s = self._recording_duration_s()
        if duration_s <= 0:
            return
        win_len = float(self.window_len_spin.value())
        min_tail = min(win_len, 0.5)
        max_start = max(0.0, duration_s - min_tail)
        cur = 0.0 if reset else float(self.window_start_spin.value())
        self.window_start_spin.setRange(0.0, max_start)
        self.window_start_spin.setSingleStep(win_len)
        self.window_start_spin.setValue(min(cur, max_start))

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

        try:
            metadata = self._workflow.load_file(str(edf_path))
        except EDFViewerError as exc:
            self._on_error(str(exc))
            return
        self._metadata = metadata
        self._active_edf_path = metadata.file_path
        self.channel_combo.clear()
        self.channel_combo.addItems(metadata.channel_names)
        self.channel_combo.setEnabled(True)

        self.file_label.setText(f"EDF: {Path(edf_path).name}")

        # Reset cached rendered windows
        self._window_cache.clear()

        self._refresh_window_start_range(reset=True)
        self._refresh_stft_window_spin(reset=True)
        self._refresh_target_hz_spin()

        self.compute_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self._set_status("Ready.")

        # When window length changes, update allowed start range
        self.window_len_spin.valueChanged.connect(self._on_window_len_changed)

        # When analysis inputs change, clear cached rendered windows.
        self.channel_combo.currentIndexChanged.connect(self._invalidate_analysis_cache)
        self.target_hz_spin.valueChanged.connect(self._invalidate_analysis_cache)

    def _on_window_len_changed(self) -> None:
        self._refresh_window_start_range()
        self._refresh_stft_window_spin()

    def _refresh_target_hz_spin(self) -> None:
        if self._metadata is None:
            return
        ch_name = self.channel_combo.currentText() or self._metadata.channel_names[0]
        orig_sfreq = float(self._metadata.sfreq_by_channel[ch_name])
        min_hz = min(1.0, orig_sfreq)
        cur = float(self.target_hz_spin.value())
        self.target_hz_spin.blockSignals(True)
        self.target_hz_spin.setRange(min_hz, orig_sfreq)
        self.target_hz_spin.setValue(min(max(cur, min_hz), orig_sfreq))
        self.target_hz_spin.blockSignals(False)

    def _stft_window_s(self) -> float:
        return float(self.stft_window_spin.value())

    def _refresh_stft_window_spin(self, reset: bool = False) -> None:
        sfreq = float(self.target_hz_spin.value())
        n_samples = int(round(float(self.window_len_spin.value()) * sfreq))
        if sfreq <= 0 or n_samples < 8:
            return
        min_s = max(8.0 / sfreq, 0.05)
        max_s = max(min_s, float(self.window_len_spin.value()))
        default_s = _default_stft_window_s(sfreq, n_samples)
        cur = default_s if reset else self._stft_window_s()
        self.stft_window_spin.blockSignals(True)
        self.stft_window_spin.setRange(min_s, max_s)
        self.stft_window_spin.setValue(min(max(cur, min_s), max_s))
        self.stft_window_spin.blockSignals(False)

    def _on_stft_window_changed(self) -> None:
        if self._latest_results is None:
            return
        if self.compute_btn.isEnabled():
            self._set_status("STFT window changed. Recomputing current window...")
            self._compute_current_window()

    def _invalidate_analysis_cache(self):
        self._window_cache.clear()
        self.save_btn.setEnabled(False)

    def _on_wavelet_changed(self, _wavelet: str):
        self._window_cache.clear()
        self._latest_results = None
        self.save_btn.setEnabled(False)
        if self._metadata is not None and self.compute_btn.isEnabled():
            self._set_status("Wavelet changed — click Compute or wait for auto recompute.")
            self._compute_current_window()

    def _on_freq_axis_log_toggled(self, checked: bool) -> None:
        self._freq_axis_log = bool(checked)
        self.freq_axis_log_btn.setText(
            "Freq Y: Log" if self._freq_axis_log else "Freq Y: Linear"
        )
        if self._latest_results is not None:
            self._apply_results(self._latest_results)
            scale = "log" if self._freq_axis_log else "linear"
            self._set_status(f"Frequency axis: {scale} Hz.")
        else:
            scale = "log" if self._freq_axis_log else "linear"
            self._set_status(f"Frequency axis set to {scale} (compute a window to view).")

    def _prev_window(self):
        win_len = float(self.window_len_spin.value())
        new_start = max(0.0, float(self.window_start_spin.value()) - win_len)
        self.window_start_spin.setValue(new_start)
        self._compute_if_cached()

    def _next_window(self):
        win_len = float(self.window_len_spin.value())
        new_start = min(
            float(self.window_start_spin.maximum()),
            float(self.window_start_spin.value()) + win_len,
        )
        self.window_start_spin.setValue(new_start)
        self._compute_if_cached()

    def _compute_if_cached(self):
        # Only update when cached; otherwise wait for user click compute.
        key = self._window_cache_key()
        if key in self._window_cache:
            self._apply_results(self._window_cache[key])

    def _compute_current_window(self):
        if self._metadata is None:
            return
        self._compute_window_on_demand()

    def _on_error(self, msg: str):
        self.compute_btn.setEnabled(True)
        self._set_status(f"Error: {msg}")

    def _compute_window_on_demand(self):
        if self._metadata is None:
            return
        cache_key = self._window_cache_key()
        t_start = cache_key[0]
        win_len = cache_key[1]

        if cache_key in self._window_cache:
            self._apply_results(self._window_cache[cache_key])
            return

        self._set_status("Computing current window (CWT/FFT)...")
        self.compute_btn.setEnabled(False)
        self._pending_cache_key = cache_key

        signals = WorkerSignals()
        signals.finished.connect(self._on_workflow_result_ready)
        signals.error.connect(self._on_error)

        params = self._build_analysis_parameters(t_start, win_len)
        worker = WorkflowComputeWorker(
            signals=signals,
            workflow=self._workflow,
            channel_name=self.channel_combo.currentText(),
            parameters=params,
        )
        worker.setAutoDelete(True)
        self._thread_pool.start(worker)

    def _build_analysis_parameters(self, window_start_s: float, window_len_s: float) -> AnalysisParameters:
        target_sfreq = float(self.target_hz_spin.value())
        safe_fmax = max(0.2, min(target_sfreq / 2.0 - 0.1, target_sfreq / 2.0 * 0.8))
        return AnalysisParameters(
            target_sfreq=target_sfreq,
            window_start_s=window_start_s,
            window_length_s=window_len_s,
            wavelet=self.wavelet_combo.currentText(),
            scalogram_fmin_hz=0.1,
            scalogram_fmax_hz=safe_fmax,
            scalogram_n_scales=64,
            stft_window_s=self._stft_window_s(),
            spectrogram_fmin_hz=0.1,
            spectrogram_fmax_hz=safe_fmax,
            freq_axis_mode="log" if self._freq_axis_log else "linear",
        )

    def _on_workflow_result_ready(self, result: AnalysisResult):
        self._on_window_ready(_gui_results_from_analysis(result))

    def _on_window_ready(self, results: Dict[str, Any]):
        key = self._pending_cache_key
        if key is None:
            key = (
                round(float(results["t_start"]), 4),
                round(float(results["window_len_s"]), 4),
                round(float(self.target_hz_spin.value()), 4),
                round(float(self.stft_window_spin.value()), 4),
                self.wavelet_combo.currentText(),
            )

        # LRU-ish cache
        self._window_cache[key] = results
        self._window_cache.move_to_end(key)
        while len(self._window_cache) > self._cache_limit:
            self._window_cache.popitem(last=False)
        self._pending_cache_key = None

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
        self._latest_results = r
        self._render_signal_and_scalogram(r)
        self._render_spectrogram(r)

    def _render_spectrogram(
        self, r: Dict[str, Any]
    ) -> None:
        spectrogram_data = r["spectrogram"]
        freqs_spec, times_spec, Sxx_db = spectrogram_data
        freqs_spec = np.asarray(freqs_spec, dtype=float)
        Sxx_db = np.asarray(Sxx_db, dtype=float)
        # Drop DC (0 Hz); Sxx is (n_freq, n_time) — use row-major like scalogram.
        spec_keep = freqs_spec >= 0.1
        if np.any(spec_keep):
            freqs_spec = freqs_spec[spec_keep]
            Sxx_db = Sxx_db[spec_keep, :]
        img_spec = self._set_image_with_axes(
            self.plot_spec,
            Sxx_db,
            np.asarray(times_spec, dtype=float),
            freqs_spec,
            resample_freqs=False,
            x_range=self._signal_x_range(r),
        )
        lo, hi = _spectrogram_display_levels(Sxx_db)
        img_spec.setLevels((lo, hi))

    def _on_signal_view_changed(self):
        if self._latest_results is not None:
            self._render_signal_and_scalogram(self._latest_results)

    @staticmethod
    def _robust_y_range(
        y: np.ndarray,
        fallback: Tuple[float, float] = (0.0, 1.0),
    ) -> Tuple[float, float]:
        y = np.asarray(y, dtype=float).ravel()
        y = y[np.isfinite(y)]
        if y.size == 0:
            return fallback
        if y.size == 1:
            v = float(y[0])
            pad = max(abs(v) * 0.1, 1e-6)
            return (v - pad, v + pad)
        lo, hi = np.nanpercentile(y, [1, 99])
        lo, hi = float(lo), float(hi)
        if lo >= hi:
            lo, hi = float(np.min(y)), float(np.max(y))
        margin = 0.1 * (hi - lo) if hi > lo else max(abs(hi) * 0.1, 1e-6)
        return (lo - margin, hi + margin)

    def _y_values_for_view(self, r: Dict[str, Any], mode: str) -> np.ndarray:
        if mode == "Raw":
            return np.asarray(r["sig"], dtype=float)
        if mode == "BBI":
            return np.asarray(r["step_y_bbi"], dtype=float)
        return np.asarray(r["step_y_amp"], dtype=float)

    @staticmethod
    def _signal_x_range(r: Dict[str, Any]) -> Tuple[float, float]:
        t_start = float(r.get("t_start", 0.0))
        window_len = float(r.get("window_len_s", 0.0))
        if window_len > 0:
            return (t_start, t_start + window_len)

        times = np.asarray(r.get("times", []), dtype=float).ravel()
        finite = times[np.isfinite(times)]
        if finite.size == 0:
            return (0.0, 1.0)
        x0 = float(np.min(finite))
        x1 = float(np.max(finite))
        if x1 <= x0:
            x1 = x0 + 1e-9
        return (x0, x1)

    def _apply_signal_view_ranges(self, r: Dict[str, Any], mode: str) -> None:
        vb = self.plot_signal_step.getViewBox()
        vb.enableAutoRange(x=False, y=False)
        x0, x1 = self._signal_x_range(r)
        y0, y1 = self._robust_y_range(self._y_values_for_view(r, mode))
        vb.setXRange(x0, x1, padding=0)
        vb.setYRange(y0, y1, padding=0)

    def _fit_xy(self) -> None:
        if self._latest_results is None:
            self._set_status("Fit XY: compute a window first.")
            return
        self._render_signal_and_scalogram(self._latest_results)
        self._render_spectrogram(self._latest_results)
        self._set_status("Fit XY.")

    def _set_image_with_axes(
        self,
        plot: pg.PlotWidget,
        coefs: np.ndarray,
        times_s: np.ndarray,
        freqs_hz: np.ndarray,
        *,
        resample_freqs: bool = True,
        x_range: Tuple[float, float] | None = None,
    ) -> pg.ImageItem:
        # ImageItem does not automatically participate in PlotItem log scaling.
        # For log frequency, draw the image in log10(Hz) coordinates and let the
        # axis item format those coordinates as Hz ticks.
        coefs, display_y, y_range, axis_mode = _prepare_frequency_image(
            coefs,
            freqs_hz,
            log_axis=self._freq_axis_log,
            resample_linear_hz=resample_freqs,
        )
        img = pg.ImageItem(axisOrder="row-major")
        plot.clear()
        plot.setLogMode(y=axis_mode == "log")
        plot.addItem(img)
        img.setAutoDownsample(False)
        img.setImage(coefs)
        if x_range is None:
            t0 = float(times_s[0])
            t1 = float(times_s[-1])
        else:
            t0 = float(x_range[0])
            t1 = float(x_range[1])
        t_width = t1 - t0
        if t_width <= 0:
            t_width = 1e-9
        y0 = float(display_y[0])
        y1 = float(display_y[-1])
        y_height = y1 - y0
        if y_height <= 0:
            y_height = 1e-9
        img.setRect(QtCore.QRectF(t0, y0, t_width, y_height))
        vb = plot.getViewBox()
        vb.enableAutoRange(x=False, y=False)
        vb.setYRange(float(y_range[0]), float(y_range[1]), padding=0)
        vb.setXRange(t0, t0 + t_width, padding=0)
        freq_label = "Frequency (Hz, log)" if axis_mode == "log" else "Frequency (Hz)"
        plot.setLabel("left", freq_label)
        plot.setLabel("bottom", "Time", "s")
        return img

    def _render_signal_and_scalogram(self, r: Dict[str, Any]):
        mode = self.signal_view_combo.currentText()
        self.plot_signal_step.clear()

        raw_times_s, raw_freqs, raw_coefs = r["raw"]
        bbi_times_s, bbi_freqs, bbi_coefs = r["bbi_scalogram"]
        amp_times_s, amp_freqs, amp_coefs = r["amp_scalogram"]
        common_min = float(min(np.min(raw_coefs), np.min(bbi_coefs), np.min(amp_coefs)))
        common_max = float(max(np.max(raw_coefs), np.max(bbi_coefs), np.max(amp_coefs)))
        if common_max <= common_min:
            common_max = common_min + 1e-9

        if mode == "Raw":
            self.plot_signal_step.plot(r["times"], r["sig"], pen=pg.mkPen("w", width=1.0))
            self.plot_signal_step.setLabel("left", self.channel_combo.currentText(), "")
            img = self._set_image_with_axes(
                self.plot_signal_scal,
                raw_coefs,
                raw_times_s,
                raw_freqs,
                x_range=self._signal_x_range(r),
            )
        elif mode == "BBI":
            self.plot_signal_step.plot(
                r["step_x_bbi"],
                r["step_y_bbi"],
                stepMode=True,
                pen=pg.mkPen("m", width=1.2),
            )
            self.plot_signal_step.setLabel("left", "BBI", "s")
            img = self._set_image_with_axes(
                self.plot_signal_scal,
                bbi_coefs,
                bbi_times_s,
                bbi_freqs,
                x_range=self._signal_x_range(r),
            )
        else:
            self.plot_signal_step.plot(
                r["step_x_amp"],
                r["step_y_amp"],
                stepMode=True,
                pen=pg.mkPen("c", width=1.2),
            )
            self.plot_signal_step.setLabel("left", "Amplitude", "")
            img = self._set_image_with_axes(
                self.plot_signal_scal,
                amp_coefs,
                amp_times_s,
                amp_freqs,
                x_range=self._signal_x_range(r),
            )

        self.plot_signal_step.setLabel("bottom", "Time", "s")
        self._apply_signal_view_ranges(r, mode)
        wavelet = self.wavelet_combo.currentText()
        self.plot_signal_scal.setTitle(f"Scalogram (CWT) — {wavelet}")
        img.setLevels((common_min, common_max))
        self.scalogram_lut.setImageItem(img)
        self.scalogram_lut.setLevels(common_min, common_max)

    def _save_current_tab_png(self):
        cur = self.tabs.currentIndex()
        w = self.tabs.currentWidget()
        if w is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save PNG",
            f"window_{self.window_start_spin.value():.2f}s_tab{cur}.png",
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
