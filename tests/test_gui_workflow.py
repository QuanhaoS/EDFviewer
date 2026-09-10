import json
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
        assert win.apply_filter_btn.isEnabled()
        assert not win.save_btn.isEnabled()
        assert not win.save_signal_btn.isEnabled()
        assert not win.save_scalogram_btn.isEnabled()
        assert not win.save_spectrogram_btn.isEnabled()
        original_sfreq = win._metadata.sfreq_by_channel[win.channel_combo.currentText()]
        assert win.original_hz_label.text() == f"Original frequency: {original_sfreq:g} Hz"
        assert np.isclose(win.filter_low_spin.value(), 0.5)
        assert win.filter_high_spin.value() > win.filter_low_spin.value()
        assert not win.filter_type_combo.isEnabled()

        win.channel_combo.setCurrentText("sine")
        original_sfreq = win._metadata.sfreq_by_channel["sine"]
        assert win.original_hz_label.text() == f"Original frequency: {original_sfreq:g} Hz"
        win.target_hz_spin.setValue(100.0)
        win.window_start_spin.setValue(10.0)
        win.window_len_spin.setValue(5.0)
        win.filter_enabled_check.setChecked(True)
        win.filter_type_combo.setCurrentText("BPF")
        win.filter_family_combo.setCurrentText("Elliptic")
        win.filter_low_spin.setValue(1.0)
        win.filter_high_spin.setValue(8.0)
        win.filter_order_spin.setValue(3)
        win.filter_ripple_spin.setValue(1.5)
        win.filter_stop_atten_spin.setValue(45.0)
        assert win.filter_low_spin.isEnabled()
        assert win.filter_high_spin.isEnabled()
        assert win.filter_ripple_spin.isEnabled()
        assert win.filter_stop_atten_spin.isEnabled()
        params = win._build_analysis_parameters(10.0, 5.0)
        assert params.filter_enabled is True
        assert params.filter_type == "band_pass"
        assert params.filter_family == "ellip"
        assert params.low_cut_hz == 1.0
        assert params.high_cut_hz == 8.0
        assert params.filter_order == 3
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
        assert win.save_signal_btn.isEnabled()
        assert win.save_scalogram_btn.isEnabled()
        assert win.save_spectrogram_btn.isEnabled()
        assert win._img_signal_scal is win.scalogram_lut.item.imageItem()
        assert win._img_spec is win.spectrogram_lut.item.imageItem()
        assert callable(win._img_signal_scal.lut)
        assert callable(win._img_spec.lut)
        assert win.plot_signal_step.listDataItems()
        assert win.fit_xy_btn.text() == "Fit XY"
        assert win.tabs.tabText(2) == "Features"
        assert win.features_table.rowCount() == len(result.features)
        feature_names = {
            win.features_table.item(row, 0).text()
            for row in range(win.features_table.rowCount())
        }
        assert "time_rms" in feature_names
        assert "freq_dominant_hz" in feature_names
        cache_size = len(win._window_cache)

        win.filter_type_combo.setCurrentText("BSF")
        qapp.processEvents()
        assert len(win._window_cache) == cache_size
        assert "Click Apply Filter" in win.status_label.text()
        recomputed = []
        win._compute_current_window = lambda: recomputed.append(True)
        win._apply_filter_settings()
        assert recomputed == [True]
        assert len(win._window_cache) == 0
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

        win.spectrogram_manual_color_check.setChecked(False)
        win.spectrogram_lut.item.setLevels(-60.0, -10.0)
        qapp.processEvents()
        assert win.spectrogram_manual_color_check.isChecked()
        assert np.isclose(win.spectrogram_color_min_spin.value(), -60.0)
        assert np.isclose(win.spectrogram_color_max_spin.value(), -10.0)
        assert win._last_spectrogram_levels == (-60.0, -10.0)

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

        session_path = tmp_path / "session.json"
        win.scalogram_color_max_spin.setValue(1.2)
        win.tabs.setCurrentWidget(win.tab_features)
        saved_path = win._save_session_to_path(session_path)
        assert saved_path == str(session_path)
        session = json.loads(session_path.read_text(encoding="utf-8"))
        assert session["version"] == 1
        assert session["channel"] == "sine"
        assert session["active_tab"] == 2
        assert session["filter"]["enabled"] is True
        assert session["active_result"]["parameters"]["filter_family"] == "ellip"

        win.channel_combo.setCurrentIndex(0)
        win.window_start_spin.setValue(0.0)
        win.window_len_spin.setValue(10.0)
        win.wavelet_combo.setCurrentText("mexh")
        win.filter_enabled_check.setChecked(False)
        win.scalogram_manual_color_check.setChecked(False)
        win.features_table.setRowCount(1)

        loaded = win._load_session_from_path(session_path)
        qapp.processEvents()
        assert loaded["channel"] == "sine"
        assert win.channel_combo.currentText() == "sine"
        assert np.isclose(win.window_start_spin.value(), 10.0)
        assert np.isclose(win.window_len_spin.value(), 5.0)
        assert win.wavelet_combo.currentText() == "cmor1.5-1.0"
        assert win.filter_enabled_check.isChecked()
        assert win.filter_family_combo.currentText() == "Elliptic"
        assert win.scalogram_manual_color_check.isChecked()
        assert np.isclose(win.scalogram_color_min_spin.value(), 0.4)
        assert win.tabs.currentWidget() is win.tab_features
        assert win.features_table.rowCount() == 0
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


def test_manual_scalogram_axes_drive_cwt_frequency_range(qapp):
    win = EDFReaderPyQt6()
    try:
        win.target_hz_spin.setValue(100.0)
        win.scalogram_manual_axes_check.setChecked(True)
        win.scalogram_y_min_spin.setValue(2.0)
        win.scalogram_y_max_spin.setValue(8.0)

        params = win._build_analysis_parameters(0.0, 10.0)

        assert params.scalogram_fmin_hz == 2.0
        assert params.scalogram_fmax_hz == 8.0
        assert params.scalogram_n_scales == 64
    finally:
        win.close()


def test_manual_spectrogram_axes_drive_stft_frequency_range(qapp):
    win = EDFReaderPyQt6()
    try:
        win.target_hz_spin.setValue(100.0)
        win.spectrogram_manual_axes_check.setChecked(True)
        win.spectrogram_y_min_spin.setValue(2.0)
        win.spectrogram_y_max_spin.setValue(8.0)

        params = win._build_analysis_parameters(0.0, 10.0)

        assert params.spectrogram_fmin_hz == 2.0
        assert params.spectrogram_fmax_hz == 8.0
        assert params.spectrogram_n_freq_bins == 64
    finally:
        win.close()


@pytest.mark.skipif(not PHANTOM.exists(), reason="samples/phantom.edf is missing")
def test_close_signal_button_resets_gui_to_initial_state(qapp):
    win = EDFReaderPyQt6()
    try:
        assert not win.close_signal_btn.isEnabled()

        win._load_dataset_full(str(PHANTOM))
        qapp.processEvents()
        assert win._metadata is not None
        assert win._workflow.metadata is not None
        assert win.channel_combo.isEnabled()
        assert win.compute_btn.isEnabled()
        assert win.close_signal_btn.isEnabled()

        win._latest_results = {"analysis_result": None}
        win._set_save_buttons_enabled(True)
        win.features_table.setRowCount(1)
        win.plot_signal_step.plot([0.0, 1.0], [0.0, 1.0])
        scal_img = win._ensure_image(win.plot_signal_scal, None)
        spec_img = win._ensure_image(win.plot_spec, None)
        win.scalogram_lut.item.setImageItem(scal_img)
        win.spectrogram_lut.item.setImageItem(spec_img)

        win.close_signal_btn.click()
        qapp.processEvents()

        assert win._metadata is None
        assert win._active_edf_path is None
        assert win._workflow.metadata is None
        assert win.channel_combo.count() == 0
        assert not win.channel_combo.isEnabled()
        assert not win.compute_btn.isEnabled()
        assert not win.close_signal_btn.isEnabled()
        assert not win.save_btn.isEnabled()
        assert win.file_label.text() == "EDF: (none)"
        assert win.original_hz_label.text() == "Original frequency: -- Hz"
        assert np.isclose(win.target_hz_spin.value(), 16.0)
        assert np.isclose(win.window_start_spin.value(), 0.0)
        assert np.isclose(win.window_len_spin.value(), 60.0)
        assert win.features_table.rowCount() == 0
        assert win.plot_signal_step.listDataItems() == []
        assert win.plot_signal_scal.plotItem.items == []
        assert win.plot_spec.plotItem.items == []
        assert win.scalogram_lut.item.imageItem() is None
        assert win.spectrogram_lut.item.imageItem() is None
        for plot in [*win.scalogram_lut.item.plots, *win.spectrogram_lut.item.plots]:
            x_data, y_data = plot.getData()
            assert len(x_data) == 0
            assert len(y_data) == 0
        assert "Signal closed." in win.status_label.text()
    finally:
        win.close()


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
