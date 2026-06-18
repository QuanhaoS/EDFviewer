import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")
pytest.importorskip("pyqtgraph")

from PyQt6 import QtWidgets

import numpy as np

from gui_pyqt6 import (
    EDFReaderPyQt6,
    SPECTROGRAM_DYNAMIC_RANGE_DB,
    _gui_results_from_analysis,
    _prepare_frequency_image,
    _spectrogram_display_levels,
)


PHANTOM = Path("samples/phantom.edf")


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.mark.skipif(not PHANTOM.exists(), reason="samples/phantom.edf is missing")
def test_gui_loads_phantom_and_renders_workflow_result(qapp, tmp_path):
    win = EDFReaderPyQt6()
    try:
        win._load_dataset_full(str(PHANTOM))
        assert win._metadata is not None
        assert "sine" in win._metadata.channel_names
        assert win.channel_combo.count() >= 2
        assert win.compute_btn.isEnabled()

        win.channel_combo.setCurrentText("sine")
        win.target_hz_spin.setValue(100.0)
        win.window_start_spin.setValue(10.0)
        win.window_len_spin.setValue(5.0)
        params = win._build_analysis_parameters(10.0, 5.0)
        result = win._workflow.compute_window("sine", params)
        assert result.source.channel_name == "sine"
        assert result.times_s[0] < 0.0
        assert result.times_s[-1] > 5.0

        gui_results = _gui_results_from_analysis(result)
        assert np.min(gui_results["times"]) >= 10.0
        assert np.max(gui_results["times"]) <= 15.0
        assert np.min(gui_results["raw"][0]) >= 10.0
        assert np.max(gui_results["raw"][0]) <= 15.0
        assert np.min(gui_results["spectrogram"][1]) >= 10.0
        assert np.max(gui_results["spectrogram"][1]) <= 15.0
        win._on_window_ready(gui_results)
        qapp.processEvents()
        assert win._latest_results is gui_results
        assert win.save_btn.isEnabled()
        assert win.plot_signal_step.listDataItems()
        assert win.fit_xy_btn.text() == "Fit XY"
        cache_size = len(win._window_cache)

        win.scalogram_manual_color_check.setChecked(True)
        win.scalogram_color_min_spin.setValue(0.25)
        win.scalogram_color_max_spin.setValue(1.5)
        win.spectrogram_manual_color_check.setChecked(True)
        win.spectrogram_color_min_spin.setValue(-70.0)
        win.spectrogram_color_max_spin.setValue(-5.0)
        qapp.processEvents()
        assert win._last_scalogram_levels == (0.25, 1.5)
        assert win._last_spectrogram_levels == (-70.0, -5.0)
        assert len(win._window_cache) == cache_size

        win.scalogram_manual_color_check.setChecked(False)
        win.scalogram_lut.item.setLevels(0.4, 1.2)
        qapp.processEvents()
        assert win.scalogram_manual_color_check.isChecked()
        assert np.isclose(win.scalogram_color_min_spin.value(), 0.4)
        assert np.isclose(win.scalogram_color_max_spin.value(), 1.2)
        assert win._last_scalogram_levels == (0.4, 1.2)

        win.scalogram_color_max_spin.setValue(0.1)
        qapp.processEvents()
        assert win._last_scalogram_levels == (0.4, 1.2)
        assert "Scalogram color range invalid" in win.status_label.text()

        x0, x1 = win.plot_signal_step.getViewBox().viewRange()[0]
        assert np.isclose(x0, 10.0)
        assert np.isclose(x1, 15.0)

        raw_freqs = gui_results["raw"][1]
        x0, x1 = win.plot_signal_scal.getViewBox().viewRange()[0]
        assert np.isclose(x0, 10.0)
        assert np.isclose(x1, 15.0)
        y0, y1 = win.plot_signal_scal.getViewBox().viewRange()[1]
        assert np.isclose(y0, float(raw_freqs[0]) - 5.0)
        assert np.isclose(y1, float(raw_freqs[-1]) + 5.0)
        assert np.isclose(win.scalogram_x_min_spin.value(), x0)
        assert np.isclose(win.scalogram_x_max_spin.value(), x1)
        assert np.isclose(win.scalogram_y_min_spin.value(), y0)
        assert np.isclose(win.scalogram_y_max_spin.value(), y1)

        spec_freqs = gui_results["spectrogram"][0]
        x0, x1 = win.plot_spec.getViewBox().viewRange()[0]
        assert np.isclose(x0, 10.0)
        assert np.isclose(x1, 15.0)
        y0, y1 = win.plot_spec.getViewBox().viewRange()[1]
        assert np.isclose(y0, float(spec_freqs[0]) - 5.0)
        assert np.isclose(y1, float(spec_freqs[-1]) + 5.0)
        assert np.isclose(win.spectrogram_x_min_spin.value(), x0)
        assert np.isclose(win.spectrogram_x_max_spin.value(), x1)
        assert np.isclose(win.spectrogram_y_min_spin.value(), y0)
        assert np.isclose(win.spectrogram_y_max_spin.value(), y1)

        win.scalogram_manual_axes_check.setChecked(True)
        win.scalogram_x_min_spin.setValue(10.5)
        win.scalogram_x_max_spin.setValue(14.5)
        win.scalogram_y_min_spin.setValue(0.5)
        win.scalogram_y_max_spin.setValue(5.5)
        qapp.processEvents()
        x0, x1 = win.plot_signal_scal.getViewBox().viewRange()[0]
        y0, y1 = win.plot_signal_scal.getViewBox().viewRange()[1]
        assert np.isclose(x0, 10.5)
        assert np.isclose(x1, 14.5)
        assert np.isclose(y0, 0.5)
        assert np.isclose(y1, 5.5)

        win.spectrogram_manual_axes_check.setChecked(True)
        win.spectrogram_x_min_spin.setValue(11.0)
        win.spectrogram_x_max_spin.setValue(14.0)
        win.spectrogram_y_min_spin.setValue(1.0)
        win.spectrogram_y_max_spin.setValue(4.0)
        qapp.processEvents()
        x0, x1 = win.plot_spec.getViewBox().viewRange()[0]
        y0, y1 = win.plot_spec.getViewBox().viewRange()[1]
        assert np.isclose(x0, 11.0)
        assert np.isclose(x1, 14.0)
        assert np.isclose(y0, 1.0)
        assert np.isclose(y1, 4.0)

        win.scalogram_x_max_spin.setValue(10.0)
        qapp.processEvents()
        x0, x1 = win.plot_signal_scal.getViewBox().viewRange()[0]
        assert np.isclose(x0, 10.5)
        assert np.isclose(x1, 14.5)
        assert "Scalogram axis range invalid" in win.status_label.text()
        win.scalogram_manual_axes_check.setChecked(False)
        win.spectrogram_manual_axes_check.setChecked(False)
        qapp.processEvents()

        win.freq_axis_log_btn.setChecked(True)
        win._on_freq_axis_log_toggled(True)
        qapp.processEvents()
        y0, y1 = win.plot_signal_scal.getViewBox().viewRange()[1]
        assert np.isclose(y0, np.log10(float(raw_freqs[0])))
        assert np.isclose(y1, np.log10(float(raw_freqs[-1])))
        assert "log" in win.plot_signal_scal.getAxis("left").labelText

        win.plot_signal_step.getViewBox().setXRange(100.0, 101.0, padding=0)
        win.plot_signal_step.getViewBox().setYRange(100.0, 101.0, padding=0)
        win._fit_xy()
        qapp.processEvents()
        x0, x1 = win.plot_signal_step.getViewBox().viewRange()[0]
        assert np.isclose(x0, 10.0)
        assert np.isclose(x1, 15.0)
        y0, y1 = win.plot_signal_step.getViewBox().viewRange()[1]
        assert y0 < float(np.min(gui_results["sig"]))
        assert y1 > float(np.max(gui_results["sig"]))

        png_path = tmp_path / "current_tab.png"
        pixmap = win.tab_signal_scal.grab()
        assert pixmap.save(str(png_path), "PNG")
        assert png_path.exists()
        assert png_path.stat().st_size > 0
    finally:
        win.close()


def test_spectrogram_display_levels_use_peak_relative_floor():
    values_db = np.array(
        [
            [-150.0, -149.0],
            [-80.0, -79.0],
            [-7.0, -7.0],
        ]
    )

    lo, hi = _spectrogram_display_levels(values_db)

    assert hi == -7.0
    assert lo == hi - SPECTROGRAM_DYNAMIC_RANGE_DB


def test_prepare_frequency_image_expands_linear_hz_range():
    values = np.arange(12, dtype=float).reshape(3, 4)
    freqs = np.array([1.0, 2.0, 5.0])

    display_values, display_y, y_range, axis_mode = _prepare_frequency_image(
        values,
        freqs,
        log_axis=False,
        resample_linear_hz=True,
    )

    assert axis_mode == "linear"
    assert np.allclose(display_y, [1.0, 3.0, 5.0])
    assert y_range == (-4.0, 10.0)
    assert display_values.shape == values.shape


def test_prepare_frequency_image_uses_log_coordinates_for_log_axis():
    values = np.arange(12, dtype=float).reshape(3, 4)
    freqs = np.array([1.0, 10.0, 100.0])

    display_values, display_y, y_range, axis_mode = _prepare_frequency_image(
        values,
        freqs,
        log_axis=True,
        resample_linear_hz=True,
    )

    assert axis_mode == "log"
    assert np.allclose(display_y, [0.0, 1.0, 2.0])
    assert y_range == (0.0, 2.0)
    assert display_values.shape == values.shape
