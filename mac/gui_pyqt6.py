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

import json
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtWidgets
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter

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


def _result_window_mask(times_s: np.ndarray, result: AnalysisResult) -> np.ndarray:
    times = np.asarray(times_s, dtype=float)
    window_len = float(result.source.window_length_s)
    return (times >= -1e-9) & (times <= window_len + 1e-9)


def _crop_result_series(
    result: AnalysisResult,
    times_s: np.ndarray,
    values: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    times = np.asarray(times_s, dtype=float)
    values = np.asarray(values, dtype=float)
    n = min(times.shape[0], values.shape[0])
    times = times[:n]
    values = values[:n]
    mask = _result_window_mask(times, result)
    return _clip_result_window_times(times[mask], result), values[mask]


def _crop_result_map(
    result: AnalysisResult,
    times_s: np.ndarray,
    values: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    times = np.asarray(times_s, dtype=float)
    values = np.asarray(values, dtype=float)
    mask = _result_window_mask(times, result)
    return _clip_result_window_times(times[mask], result), values[:, mask]


def _clip_result_window_times(times_s: np.ndarray, result: AnalysisResult) -> np.ndarray:
    return np.clip(
        np.asarray(times_s, dtype=float),
        0.0,
        float(result.source.window_length_s),
    )


def _gui_results_from_analysis(result: AnalysisResult) -> Dict[str, Any]:
    t_start = float(result.source.window_start_s)
    times_s, raw_signal = _crop_result_series(result, result.times_s, result.raw_signal)
    amplitude_times_s, amplitude_values = _crop_result_series(
        result,
        result.amplitude_times_s,
        result.amplitude_values,
    )
    bbi_times_s, bbi_values = _crop_result_series(
        result,
        result.bbi_times_s,
        result.bbi_values_s,
    )
    raw_scalogram_times_s, raw_scalogram_values = _crop_result_map(
        result,
        result.raw_scalogram.times_s,
        result.raw_scalogram.values,
    )
    amp_scalogram_times_s, amp_scalogram_values = _crop_result_map(
        result,
        result.amplitude_scalogram.times_s,
        result.amplitude_scalogram.values,
    )
    bbi_scalogram_times_s, bbi_scalogram_values = _crop_result_map(
        result,
        result.bbi_scalogram.times_s,
        result.bbi_scalogram.values,
    )
    spectrogram_times_s, spectrogram_values = _crop_result_map(
        result,
        result.spectrogram.times_s,
        result.spectrogram.values,
    )
    step_x_amp, step_y_amp = _step_from_samples(
        t_start,
        t_start + amplitude_times_s,
        amplitude_values,
    )
    step_x_bbi, step_y_bbi = _step_from_samples(
        t_start,
        t_start + bbi_times_s,
        bbi_values,
    )
    return {
        "t_start": t_start,
        "window_len_s": result.source.window_length_s,
        "times": t_start + times_s,
        "sig": raw_signal,
        "amp_t": t_start + amplitude_times_s,
        "amp_y": amplitude_values,
        "step_x_amp": step_x_amp,
        "step_y_amp": step_y_amp,
        "bbi": bbi_values,
        "bbi_t": t_start + bbi_times_s,
        "step_x_bbi": step_x_bbi,
        "step_y_bbi": step_y_bbi,
        "raw": (
            t_start + raw_scalogram_times_s,
            result.raw_scalogram.freqs_hz,
            raw_scalogram_values,
        ),
        "amp_scalogram": (
            t_start + amp_scalogram_times_s,
            result.amplitude_scalogram.freqs_hz,
            amp_scalogram_values,
        ),
        "bbi_scalogram": (
            t_start + bbi_scalogram_times_s,
            result.bbi_scalogram.freqs_hz,
            bbi_scalogram_values,
        ),
        "spectrogram": (
            result.spectrogram.freqs_hz,
            t_start + spectrogram_times_s,
            spectrogram_values,
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
        self._last_scalogram_levels: Tuple[float, float] | None = None
        self._last_spectrogram_levels: Tuple[float, float] | None = None
        self._syncing_color_controls = False
        self._setting_scalogram_lut_levels = False
        self._setting_spectrogram_lut_levels = False
        self._syncing_axis_controls = False
        self._loading_session = False
        self._dataset_control_signals_connected = False
        self._state_version = 0

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

        self.close_signal_btn = QtWidgets.QPushButton("Close Signal")
        self.close_signal_btn.setEnabled(False)
        self.close_signal_btn.setToolTip("Close the loaded EDF signal and reset the interface.")
        self.close_signal_btn.clicked.connect(self._close_current_signal)
        top_layout.addWidget(self.close_signal_btn, stretch=0)

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
        self.original_hz_label = QtWidgets.QLabel("Original frequency: -- Hz")
        self.original_hz_label.setToolTip("Original sampling rate for the selected EDF channel.")
        top_layout.addWidget(self.original_hz_label, stretch=0)

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

        self.save_scalogram_btn = QtWidgets.QPushButton("Save Scalogram")
        self.save_scalogram_btn.setEnabled(False)
        self.save_scalogram_btn.clicked.connect(self._save_scalogram_png)
        nav_layout.addWidget(self.save_scalogram_btn, stretch=0)

        self.save_signal_btn = QtWidgets.QPushButton("Save Signal")
        self.save_signal_btn.setEnabled(False)
        self.save_signal_btn.clicked.connect(self._save_signal_png)
        nav_layout.addWidget(self.save_signal_btn, stretch=0)

        self.save_spectrogram_btn = QtWidgets.QPushButton("Save Spectrogram")
        self.save_spectrogram_btn.setEnabled(False)
        self.save_spectrogram_btn.clicked.connect(self._save_spectrogram_png)
        nav_layout.addWidget(self.save_spectrogram_btn, stretch=0)

        self.save_session_btn = QtWidgets.QPushButton("Save Session")
        self.save_session_btn.clicked.connect(self._save_session_dialog)
        nav_layout.addWidget(self.save_session_btn, stretch=0)

        self.load_session_btn = QtWidgets.QPushButton("Load Session")
        self.load_session_btn.clicked.connect(self._load_session_dialog)
        nav_layout.addWidget(self.load_session_btn, stretch=0)

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
        selector_layout.addWidget(QtWidgets.QLabel("Color:"), stretch=0)
        self.scalogram_manual_color_check = QtWidgets.QCheckBox("Manual")
        self.scalogram_manual_color_check.setToolTip("Set scalogram color bar limits manually.")
        selector_layout.addWidget(self.scalogram_manual_color_check, stretch=0)
        selector_layout.addWidget(QtWidgets.QLabel("Min:"), stretch=0)
        self.scalogram_color_min_spin = self._make_color_limit_spin(0.0)
        selector_layout.addWidget(self.scalogram_color_min_spin, stretch=0)
        selector_layout.addWidget(QtWidgets.QLabel("Max:"), stretch=0)
        self.scalogram_color_max_spin = self._make_color_limit_spin(1.0)
        selector_layout.addWidget(self.scalogram_color_max_spin, stretch=0)
        self.scalogram_manual_color_check.toggled.connect(self._on_color_controls_changed)
        self.scalogram_color_min_spin.valueChanged.connect(self._on_color_controls_changed)
        self.scalogram_color_max_spin.valueChanged.connect(self._on_color_controls_changed)
        v1.addLayout(selector_layout)

        self.plot_signal_step = pg.PlotWidget()
        self.plot_signal_step.setBackground(None)
        self.plot_signal_step.setLabel("bottom", "Time", "s")
        self.plot_signal_step.setLabel("left", "Signal", "")
        v1.addWidget(self.plot_signal_step, stretch=1)

        scal_axis_layout = QtWidgets.QHBoxLayout()
        scal_axis_layout.addWidget(QtWidgets.QLabel("Scalogram axes:"), stretch=0)
        self.scalogram_manual_axes_check = QtWidgets.QCheckBox("Manual")
        self.scalogram_manual_axes_check.setToolTip("Set scalogram X/Y coordinate limits manually.")
        scal_axis_layout.addWidget(self.scalogram_manual_axes_check, stretch=0)
        for label, attr in (
            ("X min:", "scalogram_x_min_spin"),
            ("X max:", "scalogram_x_max_spin"),
            ("Y min:", "scalogram_y_min_spin"),
            ("Y max:", "scalogram_y_max_spin"),
        ):
            scal_axis_layout.addWidget(QtWidgets.QLabel(label), stretch=0)
            spin = self._make_axis_limit_spin()
            setattr(self, attr, spin)
            scal_axis_layout.addWidget(spin, stretch=0)
        self.scalogram_manual_axes_check.toggled.connect(
            lambda *_args: self._on_axis_controls_changed("scalogram")
        )
        for spin in (
            self.scalogram_x_min_spin,
            self.scalogram_x_max_spin,
            self.scalogram_y_min_spin,
            self.scalogram_y_max_spin,
        ):
            spin.valueChanged.connect(lambda *_args: self._on_axis_controls_changed("scalogram"))
        v1.addLayout(scal_axis_layout)

        self.plot_signal_scal = pg.PlotWidget()
        self.plot_signal_scal.setBackground(None)
        self.plot_signal_scal.setLabel("bottom", "Time", "s")
        self.plot_signal_scal.setLabel("left", "Frequency", "Hz")
        self.plot_signal_scal.setLogMode(y=False)
        v1.addWidget(self.plot_signal_scal, stretch=1)
        self.scalogram_lut = pg.HistogramLUTWidget()
        self.scalogram_lut.gradient.loadPreset("viridis")
        self.scalogram_lut.setMinimumHeight(120)
        self.scalogram_lut.item.sigLevelsChanged.connect(self._on_scalogram_lut_levels_changed)
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
        spec_ctrl.addWidget(QtWidgets.QLabel("Color:"), stretch=0)
        self.spectrogram_manual_color_check = QtWidgets.QCheckBox("Manual")
        self.spectrogram_manual_color_check.setToolTip("Set spectrogram color bar limits manually.")
        spec_ctrl.addWidget(self.spectrogram_manual_color_check, stretch=0)
        spec_ctrl.addWidget(QtWidgets.QLabel("Min:"), stretch=0)
        self.spectrogram_color_min_spin = self._make_color_limit_spin(-80.0)
        spec_ctrl.addWidget(self.spectrogram_color_min_spin, stretch=0)
        spec_ctrl.addWidget(QtWidgets.QLabel("Max:"), stretch=0)
        self.spectrogram_color_max_spin = self._make_color_limit_spin(0.0)
        spec_ctrl.addWidget(self.spectrogram_color_max_spin, stretch=0)
        self.spectrogram_manual_color_check.toggled.connect(self._on_color_controls_changed)
        self.spectrogram_color_min_spin.valueChanged.connect(self._on_color_controls_changed)
        self.spectrogram_color_max_spin.valueChanged.connect(self._on_color_controls_changed)
        v2.addLayout(spec_ctrl)
        spec_axis_layout = QtWidgets.QHBoxLayout()
        spec_axis_layout.addWidget(QtWidgets.QLabel("Spectrogram axes:"), stretch=0)
        self.spectrogram_manual_axes_check = QtWidgets.QCheckBox("Manual")
        self.spectrogram_manual_axes_check.setToolTip("Set spectrogram X/Y coordinate limits manually.")
        spec_axis_layout.addWidget(self.spectrogram_manual_axes_check, stretch=0)
        for label, attr in (
            ("X min:", "spectrogram_x_min_spin"),
            ("X max:", "spectrogram_x_max_spin"),
            ("Y min:", "spectrogram_y_min_spin"),
            ("Y max:", "spectrogram_y_max_spin"),
        ):
            spec_axis_layout.addWidget(QtWidgets.QLabel(label), stretch=0)
            spin = self._make_axis_limit_spin()
            setattr(self, attr, spin)
            spec_axis_layout.addWidget(spin, stretch=0)
        self.spectrogram_manual_axes_check.toggled.connect(
            lambda *_args: self._on_axis_controls_changed("spectrogram")
        )
        for spin in (
            self.spectrogram_x_min_spin,
            self.spectrogram_x_max_spin,
            self.spectrogram_y_min_spin,
            self.spectrogram_y_max_spin,
        ):
            spin.valueChanged.connect(lambda *_args: self._on_axis_controls_changed("spectrogram"))
        v2.addLayout(spec_axis_layout)
        self.plot_spec = pg.PlotWidget()
        self.plot_spec.setBackground(None)
        self.plot_spec.setLabel("bottom", "Time", "s")
        self.plot_spec.setLabel("left", "Frequency", "Hz")
        self.plot_spec.setLogMode(y=False)
        v2.addWidget(self.plot_spec)
        self.spectrogram_lut = pg.HistogramLUTWidget()
        self.spectrogram_lut.gradient.loadPreset("viridis")
        self.spectrogram_lut.setMinimumHeight(120)
        self.spectrogram_lut.item.sigLevelsChanged.connect(self._on_spectrogram_lut_levels_changed)
        v2.addWidget(self.spectrogram_lut, stretch=0)
        self.tabs.addTab(self.tab_spec, "Spectrogram")

        # Tab 3: computed feature values for the active analysis window.
        self.tab_features = QtWidgets.QWidget()
        v3 = QtWidgets.QVBoxLayout(self.tab_features)
        self.features_table = QtWidgets.QTableWidget(0, 2)
        self.features_table.setHorizontalHeaderLabels(["Feature", "Value"])
        self.features_table.horizontalHeader().setStretchLastSection(True)
        self.features_table.verticalHeader().setVisible(False)
        self.features_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.features_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        v3.addWidget(self.features_table, stretch=1)
        self.tabs.addTab(self.tab_features, "Features")

        root_layout.addLayout(self._build_filter_toolbar())

        # Image items for scalogram/spectrogram (reuse & update)
        self._img_signal_scal: Optional[pg.ImageItem] = None
        self._img_spec: Optional[pg.ImageItem] = None

        self._line_signal_step: Optional[pg.PlotDataItem] = None
        self._latest_results: Optional[Dict[str, Any]] = None

        # React when tab changes (used for optional update)
        self.tabs.currentChanged.connect(lambda _: None)
        self.signal_view_combo.currentIndexChanged.connect(self._on_signal_view_changed)

        self.resize(1200, 900)
        self._refresh_color_limit_controls()
        self._refresh_axis_limit_controls()
        self._reset_to_initial_state(status="")

    def _set_status(self, text: str):
        self.status_label.setText(text)

    def _set_save_buttons_enabled(self, enabled: bool) -> None:
        self.save_btn.setEnabled(enabled)
        self.save_scalogram_btn.setEnabled(enabled)
        self.save_signal_btn.setEnabled(enabled)
        self.save_spectrogram_btn.setEnabled(enabled)

    def _close_current_signal(self) -> None:
        self._reset_to_initial_state(status="Signal closed.")

    def _reset_to_initial_state(self, *, status: str = "Ready.") -> None:
        self._state_version += 1
        self._metadata = None
        self._active_edf_path = None
        self._active_channel_name = None
        self._pending_cache_key = None
        self._latest_results = None
        self._window_cache.clear()
        self._workflow.metadata = None
        self._workflow.cache.clear()

        self._loading_session = True
        try:
            self.file_label.setText("EDF: (none)")
            self.channel_combo.blockSignals(True)
            self.channel_combo.clear()
            self.channel_combo.setEnabled(False)
            self.channel_combo.blockSignals(False)

            self.target_hz_spin.blockSignals(True)
            self.target_hz_spin.setRange(1.0, 500.0)
            self.target_hz_spin.setValue(16.0)
            self.target_hz_spin.blockSignals(False)
            self.original_hz_label.setText("Original frequency: -- Hz")

            self.window_len_spin.blockSignals(True)
            self.window_len_spin.setRange(0.1, 1e6)
            self.window_len_spin.setValue(60.0)
            self.window_len_spin.blockSignals(False)

            self.window_start_spin.blockSignals(True)
            self.window_start_spin.setRange(0.0, 0.0)
            self.window_start_spin.setSingleStep(1.0)
            self.window_start_spin.setValue(0.0)
            self.window_start_spin.blockSignals(False)

            self.stft_window_spin.blockSignals(True)
            self.stft_window_spin.setRange(0.1, 60.0)
            self.stft_window_spin.setValue(7.5)
            self.stft_window_spin.blockSignals(False)

            self.wavelet_combo.setCurrentIndex(0)
            self.signal_view_combo.setCurrentIndex(0)
            self.freq_axis_log_btn.setChecked(False)
            self._freq_axis_log = False
            self.freq_axis_log_btn.setText("Freq Y: Linear")

            self.filter_enabled_check.setChecked(False)
            self.filter_type_combo.setCurrentIndex(0)
            self.filter_family_combo.setCurrentIndex(0)
            self.filter_low_spin.setRange(0.001, 1e6)
            self.filter_high_spin.setRange(0.001, 1e6)
            self.filter_low_spin.setValue(0.5)
            self.filter_high_spin.setValue(8.0)
            self.filter_order_spin.setValue(4)
            self.filter_ripple_spin.setValue(1.0)
            self.filter_stop_atten_spin.setValue(40.0)

            self.scalogram_manual_color_check.setChecked(False)
            self.scalogram_color_min_spin.setValue(0.0)
            self.scalogram_color_max_spin.setValue(1.0)
            self.spectrogram_manual_color_check.setChecked(False)
            self.spectrogram_color_min_spin.setValue(-80.0)
            self.spectrogram_color_max_spin.setValue(0.0)
            self._last_scalogram_levels = None
            self._last_spectrogram_levels = None

            for kind in ("scalogram", "spectrogram"):
                manual, x_min, x_max, y_min, y_max, _plot, _label = self._axis_controls(kind)
                manual.setChecked(False)
                for spin in (x_min, x_max, y_min, y_max):
                    spin.setValue(0.0)

            self.tabs.setCurrentIndex(0)
            self.features_table.setRowCount(0)
            self._clear_all_plots()
        finally:
            self._loading_session = False

        self._refresh_filter_controls()
        self._refresh_color_limit_controls()
        self._refresh_axis_limit_controls()
        self.compute_btn.setEnabled(False)
        self.close_signal_btn.setEnabled(False)
        self._set_save_buttons_enabled(False)
        self._set_status(status)

    def _clear_all_plots(self) -> None:
        self.plot_signal_step.clear()
        self.plot_signal_step.setLabel("bottom", "Time", "s")
        self.plot_signal_step.setLabel("left", "Signal", "")
        self.plot_signal_scal.clear()
        self.plot_signal_scal.setTitle("")
        self.plot_signal_scal.setLogMode(y=False)
        self.plot_signal_scal.setLabel("bottom", "Time", "s")
        self.plot_signal_scal.setLabel("left", "Frequency", "Hz")
        self._clear_histogram_lut(self.scalogram_lut)
        self.plot_spec.clear()
        self.plot_spec.setLogMode(y=False)
        self.plot_spec.setLabel("bottom", "Time", "s")
        self.plot_spec.setLabel("left", "Frequency", "Hz")
        self._clear_histogram_lut(self.spectrogram_lut)
        self._img_signal_scal = None
        self._img_spec = None
        self._line_signal_step = None

    def _clear_histogram_lut(self, lut: pg.HistogramLUTWidget) -> None:
        item = lut.item
        image_ref = getattr(item, "imageItem", None)
        image = image_ref() if callable(image_ref) else None
        if image is not None and hasattr(image, "sigImageChanged"):
            try:
                image.sigImageChanged.disconnect(item.imageChanged)
            except (TypeError, RuntimeError):
                pass
        item.imageItem = lambda: None
        for plot in getattr(item, "plots", []):
            plot.setData([], [])
        item.setLevels(0.0, 1.0)

    def _make_color_limit_spin(self, value: float) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e12, 1e12)
        spin.setDecimals(4)
        spin.setSingleStep(1.0)
        spin.setValue(float(value))
        spin.setMaximumWidth(110)
        spin.setEnabled(False)
        return spin

    def _make_axis_limit_spin(self) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e12, 1e12)
        spin.setDecimals(4)
        spin.setSingleStep(1.0)
        spin.setMaximumWidth(110)
        spin.setEnabled(False)
        return spin

    def _build_filter_toolbar(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Filter:"), stretch=0)
        self.filter_enabled_check = QtWidgets.QCheckBox("Enable")
        self.filter_enabled_check.setToolTip("Apply preprocessing filter to the full analysis pipeline.")
        layout.addWidget(self.filter_enabled_check, stretch=0)

        layout.addWidget(QtWidgets.QLabel("Type:"), stretch=0)
        self.filter_type_combo = QtWidgets.QComboBox()
        self.filter_type_combo.addItems(["LPF", "HPF", "BPF", "BSF"])
        self.filter_type_combo.setToolTip("Low-pass, high-pass, band-pass, or band-stop filter.")
        layout.addWidget(self.filter_type_combo, stretch=0)

        layout.addWidget(QtWidgets.QLabel("Family:"), stretch=0)
        self.filter_family_combo = QtWidgets.QComboBox()
        self.filter_family_combo.addItems(["Butterworth", "Chebyshev I", "Chebyshev II", "Elliptic", "Bessel"])
        layout.addWidget(self.filter_family_combo, stretch=0)

        layout.addWidget(QtWidgets.QLabel("Low:"), stretch=0)
        self.filter_low_spin = self._make_frequency_spin(0.5)
        layout.addWidget(self.filter_low_spin, stretch=0)
        layout.addWidget(QtWidgets.QLabel("High:"), stretch=0)
        self.filter_high_spin = self._make_frequency_spin(8.0)
        layout.addWidget(self.filter_high_spin, stretch=0)

        layout.addWidget(QtWidgets.QLabel("Order:"), stretch=0)
        self.filter_order_spin = QtWidgets.QSpinBox()
        self.filter_order_spin.setRange(1, 20)
        self.filter_order_spin.setValue(4)
        self.filter_order_spin.setMaximumWidth(80)
        layout.addWidget(self.filter_order_spin, stretch=0)

        layout.addWidget(QtWidgets.QLabel("Ripple:"), stretch=0)
        self.filter_ripple_spin = self._make_db_spin(1.0)
        layout.addWidget(self.filter_ripple_spin, stretch=0)
        layout.addWidget(QtWidgets.QLabel("Stop atten:"), stretch=0)
        self.filter_stop_atten_spin = self._make_db_spin(40.0)
        layout.addWidget(self.filter_stop_atten_spin, stretch=0)

        self.apply_filter_btn = QtWidgets.QPushButton("Apply Filter")
        self.apply_filter_btn.setEnabled(False)
        self.apply_filter_btn.clicked.connect(self._apply_filter_settings)
        layout.addWidget(self.apply_filter_btn, stretch=0)
        layout.addStretch(1)

        self.filter_enabled_check.toggled.connect(self._on_filter_controls_changed)
        self.filter_type_combo.currentTextChanged.connect(self._on_filter_controls_changed)
        self.filter_family_combo.currentTextChanged.connect(self._on_filter_controls_changed)
        self.filter_low_spin.valueChanged.connect(self._on_filter_controls_changed)
        self.filter_high_spin.valueChanged.connect(self._on_filter_controls_changed)
        self.filter_order_spin.valueChanged.connect(self._on_filter_controls_changed)
        self.filter_ripple_spin.valueChanged.connect(self._on_filter_controls_changed)
        self.filter_stop_atten_spin.valueChanged.connect(self._on_filter_controls_changed)
        self._refresh_filter_controls()
        return layout

    def _make_frequency_spin(self, value: float) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0.001, 1e6)
        spin.setDecimals(3)
        spin.setSingleStep(0.1)
        spin.setSuffix(" Hz")
        spin.setValue(float(value))
        spin.setMaximumWidth(110)
        return spin

    def _make_db_spin(self, value: float) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0.001, 300.0)
        spin.setDecimals(2)
        spin.setSingleStep(1.0)
        spin.setSuffix(" dB")
        spin.setValue(float(value))
        spin.setMaximumWidth(110)
        return spin

    def _refresh_color_limit_controls(self) -> None:
        self.scalogram_color_min_spin.setEnabled(self.scalogram_manual_color_check.isChecked())
        self.scalogram_color_max_spin.setEnabled(self.scalogram_manual_color_check.isChecked())
        self.spectrogram_color_min_spin.setEnabled(self.spectrogram_manual_color_check.isChecked())
        self.spectrogram_color_max_spin.setEnabled(self.spectrogram_manual_color_check.isChecked())

    def _on_color_controls_changed(self, *_args) -> None:
        if self._syncing_color_controls:
            return
        self._refresh_color_limit_controls()
        if self._loading_session:
            return
        if self._latest_results is None:
            return
        self._apply_results(self._latest_results)

    def _on_scalogram_lut_levels_changed(self, *_args) -> None:
        if self._setting_scalogram_lut_levels:
            return
        levels = self.scalogram_lut.item.getLevels()
        if levels is None:
            return
        lo, hi = float(levels[0]), float(levels[1])
        if hi <= lo:
            return
        self._last_scalogram_levels = (lo, hi)
        self._syncing_color_controls = True
        try:
            self.scalogram_manual_color_check.setChecked(True)
            self.scalogram_color_min_spin.setValue(lo)
            self.scalogram_color_max_spin.setValue(hi)
            self._refresh_color_limit_controls()
        finally:
            self._syncing_color_controls = False
        self._set_status("Scalogram color range updated from color bar.")

    def _on_spectrogram_lut_levels_changed(self, *_args) -> None:
        if self._setting_spectrogram_lut_levels:
            return
        levels = self.spectrogram_lut.item.getLevels()
        if levels is None:
            return
        lo, hi = float(levels[0]), float(levels[1])
        if hi <= lo:
            return
        self._last_spectrogram_levels = (lo, hi)
        self._syncing_color_controls = True
        try:
            self.spectrogram_manual_color_check.setChecked(True)
            self.spectrogram_color_min_spin.setValue(lo)
            self.spectrogram_color_max_spin.setValue(hi)
            self._refresh_color_limit_controls()
        finally:
            self._syncing_color_controls = False
        self._set_status("Spectrogram color range updated from color bar.")

    def _axis_controls(self, kind: str):
        if kind == "scalogram":
            return (
                self.scalogram_manual_axes_check,
                self.scalogram_x_min_spin,
                self.scalogram_x_max_spin,
                self.scalogram_y_min_spin,
                self.scalogram_y_max_spin,
                self.plot_signal_scal,
                "Scalogram",
            )
        return (
            self.spectrogram_manual_axes_check,
            self.spectrogram_x_min_spin,
            self.spectrogram_x_max_spin,
            self.spectrogram_y_min_spin,
            self.spectrogram_y_max_spin,
            self.plot_spec,
            "Spectrogram",
        )

    def _refresh_axis_limit_controls(self) -> None:
        for kind in ("scalogram", "spectrogram"):
            manual, x_min, x_max, y_min, y_max, _plot, _label = self._axis_controls(kind)
            enabled = manual.isChecked()
            for spin in (x_min, x_max, y_min, y_max):
                spin.setEnabled(enabled)

    def _on_axis_controls_changed(self, kind: str) -> None:
        if self._syncing_axis_controls:
            return
        self._refresh_axis_limit_controls()
        if self._loading_session:
            return
        manual, _x_min, _x_max, _y_min, _y_max, _plot, _label = self._axis_controls(kind)
        if manual.isChecked():
            if self._apply_axis_limits(kind):
                if kind == "scalogram":
                    self._maybe_recompute_scalogram_frequency_range()
                elif kind == "spectrogram":
                    self._maybe_recompute_spectrogram_frequency_range()
        elif self._latest_results is not None:
            self._apply_results(self._latest_results)

    def _sync_axis_controls_from_plot(self, kind: str) -> None:
        manual, x_min, x_max, y_min, y_max, plot, _label = self._axis_controls(kind)
        if manual.isChecked():
            return
        x_range, y_range = plot.getViewBox().viewRange()
        self._syncing_axis_controls = True
        try:
            x_min.setValue(float(x_range[0]))
            x_max.setValue(float(x_range[1]))
            y_min.setValue(float(y_range[0]))
            y_max.setValue(float(y_range[1]))
            self._refresh_axis_limit_controls()
        finally:
            self._syncing_axis_controls = False

    def _apply_axis_limits(self, kind: str) -> bool:
        manual, x_min, x_max, y_min, y_max, plot, label = self._axis_controls(kind)
        if not manual.isChecked():
            return False
        x0 = float(x_min.value())
        x1 = float(x_max.value())
        y0 = float(y_min.value())
        y1 = float(y_max.value())
        if x1 <= x0 or y1 <= y0:
            self._set_status(f"{label} axis range invalid: max must be greater than min.")
            return False
        vb = plot.getViewBox()
        vb.enableAutoRange(x=False, y=False)
        vb.setXRange(x0, x1, padding=0)
        vb.setYRange(y0, y1, padding=0)
        return True

    def _default_scalogram_frequency_range(self) -> tuple[float, float]:
        target_sfreq = float(self.target_hz_spin.value())
        safe_fmax = max(0.2, min(target_sfreq / 2.0 - 0.1, target_sfreq / 2.0 * 0.8))
        return 0.1, safe_fmax

    def _scalogram_frequency_range(self) -> tuple[float, float]:
        default_fmin, default_fmax = self._default_scalogram_frequency_range()
        if not self.scalogram_manual_axes_check.isChecked():
            return default_fmin, default_fmax

        y0 = float(self.scalogram_y_min_spin.value())
        y1 = float(self.scalogram_y_max_spin.value())
        if y1 <= y0:
            return default_fmin, default_fmax

        if self._freq_axis_log:
            y0 = 10.0 ** y0
            y1 = 10.0 ** y1

        nyquist_limit = max(default_fmin, float(self.target_hz_spin.value()) / 2.0 - 0.1)
        fmin = max(default_fmin, y0)
        fmax = min(y1, nyquist_limit)
        if fmax <= fmin:
            return default_fmin, default_fmax
        return fmin, fmax

    def _scalogram_frequency_key(self) -> tuple[float, float]:
        fmin, fmax = self._scalogram_frequency_range()
        return round(float(fmin), 4), round(float(fmax), 4)

    def _latest_scalogram_frequency_key(self) -> tuple[float, float] | None:
        if self._latest_results is None:
            return None
        result = self._latest_results.get("analysis_result")
        parameters = getattr(result, "parameters", None)
        if parameters is None:
            return None
        return (
            round(float(parameters.scalogram_fmin_hz), 4),
            round(float(parameters.scalogram_fmax_hz), 4),
        )

    def _default_spectrogram_frequency_range(self) -> tuple[float, float]:
        target_sfreq = float(self.target_hz_spin.value())
        safe_fmax = max(0.2, min(target_sfreq / 2.0 - 0.1, target_sfreq / 2.0 * 0.8))
        return 0.1, safe_fmax

    def _spectrogram_frequency_range(self) -> tuple[float, float]:
        default_fmin, default_fmax = self._default_spectrogram_frequency_range()
        if not self.spectrogram_manual_axes_check.isChecked():
            return default_fmin, default_fmax

        y0 = float(self.spectrogram_y_min_spin.value())
        y1 = float(self.spectrogram_y_max_spin.value())
        if y1 <= y0:
            return default_fmin, default_fmax

        if self._freq_axis_log:
            y0 = 10.0 ** y0
            y1 = 10.0 ** y1

        nyquist_limit = max(default_fmin, float(self.target_hz_spin.value()) / 2.0 - 0.1)
        fmin = max(default_fmin, y0)
        fmax = min(y1, nyquist_limit)
        if fmax <= fmin:
            return default_fmin, default_fmax
        return fmin, fmax

    def _spectrogram_frequency_key(self) -> tuple[float, float]:
        fmin, fmax = self._spectrogram_frequency_range()
        return round(float(fmin), 4), round(float(fmax), 4)

    def _latest_spectrogram_frequency_key(self) -> tuple[float, float] | None:
        if self._latest_results is None:
            return None
        result = self._latest_results.get("analysis_result")
        parameters = getattr(result, "parameters", None)
        if parameters is None:
            return None
        return (
            round(float(parameters.spectrogram_fmin_hz), 4),
            round(float(parameters.spectrogram_fmax_hz), 4),
        )

    def _maybe_recompute_scalogram_frequency_range(self) -> None:
        if self._metadata is None or self._latest_results is None:
            return
        requested_key = self._scalogram_frequency_key()
        if requested_key == self._latest_scalogram_frequency_key():
            return
        self._window_cache.clear()
        self._set_status("Scalogram frequency range changed. Recomputing 64 bins...")
        self._compute_current_window()

    def _maybe_recompute_spectrogram_frequency_range(self) -> None:
        if self._metadata is None or self._latest_results is None:
            return
        requested_key = self._spectrogram_frequency_key()
        if requested_key == self._latest_spectrogram_frequency_key():
            return
        self._window_cache.clear()
        self._set_status("Spectrogram frequency range changed. Recomputing 64 bins...")
        self._compute_current_window()

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
            *self._scalogram_frequency_key(),
            *self._spectrogram_frequency_key(),
            self.filter_enabled_check.isChecked(),
            self._filter_type_value(),
            self._filter_family_value(),
            round(float(self.filter_low_spin.value()), 4),
            round(float(self.filter_high_spin.value()), 4),
            int(self.filter_order_spin.value()),
            round(float(self.filter_ripple_spin.value()), 4),
            round(float(self.filter_stop_atten_spin.value()), 4),
        )

    def _filter_type_value(self) -> str:
        return {
            "LPF": "low_pass",
            "HPF": "high_pass",
            "BPF": "band_pass",
            "BSF": "band_stop",
        }[self.filter_type_combo.currentText()]

    def _filter_family_value(self) -> str:
        return {
            "Butterworth": "butter",
            "Chebyshev I": "cheby1",
            "Chebyshev II": "cheby2",
            "Elliptic": "ellip",
            "Bessel": "bessel",
        }[self.filter_family_combo.currentText()]

    def _refresh_filter_controls(self) -> None:
        enabled = self.filter_enabled_check.isChecked()
        filter_type = self._filter_type_value()
        family = self._filter_family_value()
        needs_low = filter_type in {"high_pass", "band_pass", "band_stop"}
        needs_high = filter_type in {"low_pass", "band_pass", "band_stop"}
        self.filter_type_combo.setEnabled(enabled)
        self.filter_family_combo.setEnabled(enabled)
        self.filter_low_spin.setEnabled(enabled and needs_low)
        self.filter_high_spin.setEnabled(enabled and needs_high)
        self.filter_order_spin.setEnabled(enabled)
        self.filter_ripple_spin.setEnabled(enabled and family in {"cheby1", "ellip"})
        self.filter_stop_atten_spin.setEnabled(enabled and family in {"cheby2", "ellip"})
        self.apply_filter_btn.setEnabled(self._metadata is not None)

    def _on_filter_controls_changed(self, *_args) -> None:
        self._refresh_filter_controls()
        if self._metadata is not None:
            self._set_status("Filter settings changed. Click Apply Filter to recompute.")

    def _refresh_filter_cutoff_defaults(self) -> None:
        sfreq = float(self.target_hz_spin.value())
        nyquist = max(sfreq / 2.0, 0.001)
        high = min(8.0, max(0.001, nyquist - 0.1))
        low = min(0.5, max(0.001, high * 0.5))
        self.filter_low_spin.blockSignals(True)
        self.filter_high_spin.blockSignals(True)
        self.filter_low_spin.setRange(0.001, max(0.001, nyquist - 1e-6))
        self.filter_high_spin.setRange(0.001, max(0.001, nyquist - 1e-6))
        self.filter_low_spin.setValue(low)
        self.filter_high_spin.setValue(high)
        self.filter_low_spin.blockSignals(False)
        self.filter_high_spin.blockSignals(False)
        self._refresh_filter_controls()

    def _apply_filter_settings(self) -> None:
        if self._metadata is None:
            return
        self._window_cache.clear()
        self._set_status("Applying filter and recomputing current window...")
        self._compute_current_window()

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
        self._state_version += 1
        self._set_status("Loading EDF (this may take time)...")
        self.compute_btn.setEnabled(False)
        self._set_save_buttons_enabled(False)
        self.close_signal_btn.setEnabled(False)
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
        self._refresh_filter_cutoff_defaults()

        self.compute_btn.setEnabled(True)
        self.close_signal_btn.setEnabled(True)
        self._set_save_buttons_enabled(False)
        self._set_status("Ready.")

        if not self._dataset_control_signals_connected:
            # When window length changes, update allowed start range.
            self.window_len_spin.valueChanged.connect(self._on_window_len_changed)

            # When analysis inputs change, clear cached rendered windows.
            self.channel_combo.currentIndexChanged.connect(self._on_channel_changed)
            self.target_hz_spin.valueChanged.connect(self._on_target_hz_changed)
            self._dataset_control_signals_connected = True

    def _on_window_len_changed(self) -> None:
        self._refresh_window_start_range()
        self._refresh_stft_window_spin()

    def _on_channel_changed(self) -> None:
        self._refresh_target_hz_spin()
        self._refresh_stft_window_spin(reset=True)
        self._refresh_filter_cutoff_defaults()
        self._invalidate_analysis_cache()

    def _refresh_target_hz_spin(self) -> None:
        if self._metadata is None:
            self.original_hz_label.setText("Original frequency: -- Hz")
            return
        ch_name = self.channel_combo.currentText() or self._metadata.channel_names[0]
        orig_sfreq = float(self._metadata.sfreq_by_channel[ch_name])
        self.original_hz_label.setText(f"Original frequency: {orig_sfreq:g} Hz")
        min_hz = min(1.0, orig_sfreq)
        cur = float(self.target_hz_spin.value())
        self.target_hz_spin.blockSignals(True)
        self.target_hz_spin.setRange(min_hz, orig_sfreq)
        self.target_hz_spin.setValue(min(max(cur, min_hz), orig_sfreq))
        self.target_hz_spin.blockSignals(False)

    def _on_target_hz_changed(self) -> None:
        self._invalidate_analysis_cache()
        self._refresh_stft_window_spin()
        self._refresh_filter_cutoff_defaults()

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
        self._set_save_buttons_enabled(False)

    def _on_wavelet_changed(self, _wavelet: str):
        self._window_cache.clear()
        self._latest_results = None
        self._set_save_buttons_enabled(False)
        self._update_features_table(None)
        if self._loading_session:
            return
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
        has_signal = self._metadata is not None
        self.compute_btn.setEnabled(has_signal)
        self.close_signal_btn.setEnabled(has_signal)
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
        state_version = self._state_version

        signals = WorkerSignals()
        signals.finished.connect(
            lambda result, version=state_version: self._on_workflow_result_ready(result, version)
        )
        signals.error.connect(
            lambda msg, version=state_version: self._on_compute_error(msg, version)
        )

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
        scalogram_fmin, scalogram_fmax = self._scalogram_frequency_range()
        spectrogram_fmin, spectrogram_fmax = self._spectrogram_frequency_range()
        return AnalysisParameters(
            target_sfreq=target_sfreq,
            window_start_s=window_start_s,
            window_length_s=window_len_s,
            wavelet=self.wavelet_combo.currentText(),
            scalogram_fmin_hz=scalogram_fmin,
            scalogram_fmax_hz=scalogram_fmax,
            scalogram_n_scales=64,
            stft_window_s=self._stft_window_s(),
            spectrogram_fmin_hz=spectrogram_fmin,
            spectrogram_fmax_hz=spectrogram_fmax,
            spectrogram_n_freq_bins=64,
            freq_axis_mode="log" if self._freq_axis_log else "linear",
            filter_enabled=self.filter_enabled_check.isChecked(),
            filter_type=self._filter_type_value() if self.filter_enabled_check.isChecked() else None,
            low_cut_hz=float(self.filter_low_spin.value()),
            high_cut_hz=float(self.filter_high_spin.value()),
            filter_order=int(self.filter_order_spin.value()),
            filter_family=self._filter_family_value(),
            filter_ripple_db=float(self.filter_ripple_spin.value()),
            filter_stop_atten_db=float(self.filter_stop_atten_spin.value()),
        )

    def _on_compute_error(self, msg: str, state_version: int) -> None:
        if state_version != self._state_version:
            return
        self._on_error(msg)

    def _on_workflow_result_ready(self, result: AnalysisResult, state_version: int | None = None):
        if state_version is not None and state_version != self._state_version:
            return
        self._on_window_ready(_gui_results_from_analysis(result))

    def _on_window_ready(self, results: Dict[str, Any]):
        key = self._pending_cache_key
        if key is None:
            key = self._window_cache_key()

        # LRU-ish cache
        self._window_cache[key] = results
        self._window_cache.move_to_end(key)
        while len(self._window_cache) > self._cache_limit:
            self._window_cache.popitem(last=False)
        self._pending_cache_key = None

        self._apply_results(results)
        self.compute_btn.setEnabled(True)
        self._set_save_buttons_enabled(True)
        self._set_status("Done.")

    def _clear_plot(self, plot: pg.PlotWidget):
        plot.clear()

    def _ensure_image(self, plot: pg.PlotWidget, existing: Optional[pg.ImageItem]) -> pg.ImageItem:
        if existing is not None:
            return existing
        img = pg.ImageItem()
        plot.addItem(img)
        return img

    def _bind_lut_to_image(
        self,
        lut: pg.HistogramLUTWidget,
        img: pg.ImageItem,
        levels: Tuple[float, float],
    ) -> None:
        img.setLookupTable(lut.item.getLookupTable)
        img.setLevels(levels)
        lut.item.setImageItem(img)
        lut.item.setLevels(*levels)

    def _apply_results(self, r: Dict[str, Any]):
        self._latest_results = r
        self._render_signal_and_scalogram(r)
        self._render_spectrogram(r)
        self._update_features_table(r.get("analysis_result"))

    def _update_features_table(self, result: AnalysisResult | None) -> None:
        self.features_table.setRowCount(0)
        if result is None or not result.features:
            return
        rows = sorted(result.features.items(), key=lambda item: item[0])
        self.features_table.setRowCount(len(rows))
        for row, (key, value) in enumerate(rows):
            key_item = QtWidgets.QTableWidgetItem(str(key))
            value_item = QtWidgets.QTableWidgetItem(_feature_value_text(value))
            self.features_table.setItem(row, 0, key_item)
            self.features_table.setItem(row, 1, value_item)
        self.features_table.resizeColumnsToContents()

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
        auto_levels = _spectrogram_display_levels(Sxx_db)
        levels = self._color_levels(
            self.spectrogram_manual_color_check,
            self.spectrogram_color_min_spin,
            self.spectrogram_color_max_spin,
            auto_levels,
            "_last_spectrogram_levels",
            "Spectrogram",
        )
        self._setting_spectrogram_lut_levels = True
        try:
            self._bind_lut_to_image(self.spectrogram_lut, img_spec, levels)
        finally:
            self._setting_spectrogram_lut_levels = False
        self._img_spec = img_spec
        self._sync_axis_controls_from_plot("spectrogram")
        self._apply_axis_limits("spectrogram")

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

    def _color_levels(
        self,
        manual_check: QtWidgets.QCheckBox,
        min_spin: QtWidgets.QDoubleSpinBox,
        max_spin: QtWidgets.QDoubleSpinBox,
        auto_levels: Tuple[float, float],
        last_attr: str,
        label: str,
    ) -> Tuple[float, float]:
        if not manual_check.isChecked():
            setattr(self, last_attr, auto_levels)
            return auto_levels
        lo = float(min_spin.value())
        hi = float(max_spin.value())
        if hi <= lo:
            previous = getattr(self, last_attr)
            self._set_status(f"{label} color range invalid: max must be greater than min.")
            return previous if previous is not None else auto_levels
        levels = (lo, hi)
        setattr(self, last_attr, levels)
        return levels

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
        levels = self._color_levels(
            self.scalogram_manual_color_check,
            self.scalogram_color_min_spin,
            self.scalogram_color_max_spin,
            (common_min, common_max),
            "_last_scalogram_levels",
            "Scalogram",
        )
        self._setting_scalogram_lut_levels = True
        try:
            self._bind_lut_to_image(self.scalogram_lut, img, levels)
        finally:
            self._setting_scalogram_lut_levels = False
        self._img_signal_scal = img
        self._sync_axis_controls_from_plot("scalogram")
        self._apply_axis_limits("scalogram")

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

    def _save_signal_png(self) -> None:
        self._save_plot_png(self.plot_signal_step, "signal", "Save Signal PNG")

    def _save_scalogram_png(self) -> None:
        self._save_plot_png(self.plot_signal_scal, "scalogram", "Save Scalogram PNG")

    def _save_spectrogram_png(self) -> None:
        self._save_plot_png(self.plot_spec, "spectrogram", "Save Spectrogram PNG")

    def _save_plot_png(self, plot: pg.PlotWidget, stem: str, title: str) -> None:
        if self._latest_results is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            title,
            f"{stem}_{self.window_start_spin.value():.2f}s.png",
            "PNG files (*.png);;All files (*)",
        )
        if not path:
            return
        try:
            ImageExporter(plot.plotItem).export(path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save error", f"Failed to save PNG: {exc}")
            return
        self._set_status(f"Saved {stem}: {path}")

    def _save_session_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save EDFViewer session",
            "edfviewer_session.json",
            "JSON files (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            self._save_session_to_path(path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save session error", str(exc))

    def _load_session_dialog(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load EDFViewer session",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            self._load_session_from_path(path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Load session error", str(exc))

    def _save_session_to_path(self, path: str | Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._session_state(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._set_status(f"Session saved: {path}")
        return str(path)

    def _load_session_from_path(self, path: str | Path) -> dict[str, Any]:
        path = Path(path)
        state = json.loads(path.read_text(encoding="utf-8"))
        self._apply_session_state(state)
        self._set_status(f"Session loaded: {path}")
        return state

    def _session_state(self) -> dict[str, Any]:
        active_result = None
        if self._latest_results is not None:
            result = self._latest_results.get("analysis_result")
            if result is not None:
                active_result = {
                    "channel": result.source.channel_name,
                    "window_start_s": result.source.window_start_s,
                    "window_length_s": result.source.window_length_s,
                    "parameters": asdict(result.parameters),
                }
        return {
            "version": 1,
            "edf_path": self._active_edf_path,
            "channel": self.channel_combo.currentText(),
            "target_sfreq": float(self.target_hz_spin.value()),
            "window_start_s": float(self.window_start_spin.value()),
            "window_length_s": float(self.window_len_spin.value()),
            "wavelet": self.wavelet_combo.currentText(),
            "freq_axis": "log" if self._freq_axis_log else "linear",
            "signal_view": self.signal_view_combo.currentText(),
            "active_tab": int(self.tabs.currentIndex()),
            "stft_window_s": float(self.stft_window_spin.value()),
            "filter": {
                "enabled": self.filter_enabled_check.isChecked(),
                "type": self.filter_type_combo.currentText(),
                "family": self.filter_family_combo.currentText(),
                "low_hz": float(self.filter_low_spin.value()),
                "high_hz": float(self.filter_high_spin.value()),
                "order": int(self.filter_order_spin.value()),
                "ripple_db": float(self.filter_ripple_spin.value()),
                "stop_atten_db": float(self.filter_stop_atten_spin.value()),
            },
            "color_ranges": {
                "scalogram": {
                    "manual": self.scalogram_manual_color_check.isChecked(),
                    "min": float(self.scalogram_color_min_spin.value()),
                    "max": float(self.scalogram_color_max_spin.value()),
                },
                "spectrogram": {
                    "manual": self.spectrogram_manual_color_check.isChecked(),
                    "min": float(self.spectrogram_color_min_spin.value()),
                    "max": float(self.spectrogram_color_max_spin.value()),
                },
            },
            "axes": {
                "scalogram": self._axis_state("scalogram"),
                "spectrogram": self._axis_state("spectrogram"),
            },
            "active_result": active_result,
        }

    def _axis_state(self, kind: str) -> dict[str, float | bool]:
        manual, x_min, x_max, y_min, y_max, _plot, _label = self._axis_controls(kind)
        return {
            "manual": manual.isChecked(),
            "x_min": float(x_min.value()),
            "x_max": float(x_max.value()),
            "y_min": float(y_min.value()),
            "y_max": float(y_max.value()),
        }

    def _apply_session_state(self, state: dict[str, Any]) -> None:
        self._loading_session = True
        try:
            edf_path = state.get("edf_path")
            if edf_path:
                if not Path(edf_path).exists():
                    raise FileNotFoundError(f"Session EDF file not found: {edf_path}")
                if edf_path != self._active_edf_path:
                    self._load_dataset_full(str(edf_path))

            _set_combo_text(self.channel_combo, state.get("channel"))
            self._refresh_target_hz_spin()
            self.target_hz_spin.setValue(float(state.get("target_sfreq", self.target_hz_spin.value())))
            self.window_len_spin.setValue(float(state.get("window_length_s", self.window_len_spin.value())))
            self._refresh_window_start_range()
            self.window_start_spin.setValue(float(state.get("window_start_s", self.window_start_spin.value())))
            _set_combo_text(self.wavelet_combo, state.get("wavelet"))
            _set_combo_text(self.signal_view_combo, state.get("signal_view"))
            self.stft_window_spin.setValue(float(state.get("stft_window_s", self.stft_window_spin.value())))

            freq_axis = str(state.get("freq_axis", "linear")).lower()
            self.freq_axis_log_btn.setChecked(freq_axis == "log")
            self._on_freq_axis_log_toggled(freq_axis == "log")

            filter_state = state.get("filter") or {}
            self.filter_enabled_check.setChecked(bool(filter_state.get("enabled", False)))
            _set_combo_text(self.filter_type_combo, filter_state.get("type"))
            _set_combo_text(self.filter_family_combo, filter_state.get("family"))
            self.filter_low_spin.setValue(float(filter_state.get("low_hz", self.filter_low_spin.value())))
            self.filter_high_spin.setValue(float(filter_state.get("high_hz", self.filter_high_spin.value())))
            self.filter_order_spin.setValue(int(filter_state.get("order", self.filter_order_spin.value())))
            self.filter_ripple_spin.setValue(float(filter_state.get("ripple_db", self.filter_ripple_spin.value())))
            self.filter_stop_atten_spin.setValue(
                float(filter_state.get("stop_atten_db", self.filter_stop_atten_spin.value()))
            )
            self._refresh_filter_controls()

            color_ranges = state.get("color_ranges") or {}
            self._apply_color_state("scalogram", color_ranges.get("scalogram") or {})
            self._apply_color_state("spectrogram", color_ranges.get("spectrogram") or {})

            axes = state.get("axes") or {}
            self._apply_axis_state("scalogram", axes.get("scalogram") or {})
            self._apply_axis_state("spectrogram", axes.get("spectrogram") or {})

            tab = int(state.get("active_tab", self.tabs.currentIndex()))
            self.tabs.setCurrentIndex(max(0, min(tab, self.tabs.count() - 1)))
            self._window_cache.clear()
            self._latest_results = None
            self._set_save_buttons_enabled(False)
            self._update_features_table(None)
        finally:
            self._loading_session = False
        self._refresh_color_limit_controls()
        self._refresh_axis_limit_controls()

    def _apply_color_state(self, kind: str, state: dict[str, Any]) -> None:
        if kind == "scalogram":
            manual = self.scalogram_manual_color_check
            min_spin = self.scalogram_color_min_spin
            max_spin = self.scalogram_color_max_spin
        else:
            manual = self.spectrogram_manual_color_check
            min_spin = self.spectrogram_color_min_spin
            max_spin = self.spectrogram_color_max_spin
        manual.setChecked(bool(state.get("manual", False)))
        if "min" in state:
            min_spin.setValue(float(state["min"]))
        if "max" in state:
            max_spin.setValue(float(state["max"]))

    def _apply_axis_state(self, kind: str, state: dict[str, Any]) -> None:
        manual, x_min, x_max, y_min, y_max, _plot, _label = self._axis_controls(kind)
        manual.setChecked(bool(state.get("manual", False)))
        for key, spin in (
            ("x_min", x_min),
            ("x_max", x_max),
            ("y_min", y_min),
            ("y_max", y_max),
        ):
            if key in state:
                spin.setValue(float(state[key]))


def _feature_value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.8g}"
    if isinstance(value, (int, str, bool)):
        return str(value)
    if hasattr(value, "item"):
        try:
            return _feature_value_text(value.item())
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _set_combo_text(combo: QtWidgets.QComboBox, value: Any) -> None:
    if value is None:
        return
    text = str(value)
    idx = combo.findText(text)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def run_gui():
    app = QtWidgets.QApplication([])
    win = EDFReaderPyQt6()
    win.show()
    return app.exec()
