import numpy as np

from analysis.window_analysis import analyze_window
from core.models import ChannelWindow
from core.parameters import AnalysisParameters
from visualization import (
    build_scalogram_plot_data,
    build_signal_plot_data,
    build_spectrogram_plot_data,
    compute_color_range,
)


def _result():
    sfreq = 100.0
    times = np.arange(0, 10, 1 / sfreq)
    signal = np.sin(2 * np.pi * 1.2 * times)
    window = ChannelWindow("synthetic.edf", "sine", 0.0, 10.0, sfreq, times, signal)
    params = AnalysisParameters(
        window_start_s=0.0,
        window_length_s=10.0,
        scalogram_fmin_hz=0.5,
        scalogram_fmax_hz=10.0,
        scalogram_n_scales=8,
        stft_window_s=2.0,
    )
    return analyze_window(window, signal, sfreq, params)


def test_build_signal_plot_data_for_each_active_view():
    result = _result()

    raw = build_signal_plot_data(result, {"active_signal_view": "raw"})
    bbi = build_signal_plot_data(result, {"active_signal_view": "bbi"})
    amplitude = build_signal_plot_data(result, {"active_signal_view": "amplitude"})

    assert raw["view"] == "raw"
    assert len(raw["x"]) == len(result.times_s)
    assert bbi["view"] == "bbi"
    assert len(bbi["x"]) == len(result.bbi_times_s)
    assert amplitude["view"] == "amplitude"
    assert len(amplitude["x"]) == len(result.amplitude_times_s)


def test_build_scalogram_uses_active_view_and_shared_color_range():
    result = _result()
    display = {"active_signal_view": "amplitude", "color_range_mode": "auto"}

    plot_data = build_scalogram_plot_data(result, display)
    shared = compute_color_range(
        [result.raw_scalogram, result.bbi_scalogram, result.amplitude_scalogram],
        display,
    )

    assert plot_data["view"] == "amplitude"
    assert plot_data["color_range"] == shared
    assert plot_data["values"].shape == (len(plot_data["y"]), len(plot_data["x"]))


def test_frequency_range_filtering_for_scalogram_and_spectrogram():
    result = _result()
    display = {
        "active_signal_view": "raw",
        "scalogram_fmin_hz": 1.0,
        "scalogram_fmax_hz": 5.0,
        "spectrogram_fmin_hz": 1.0,
        "spectrogram_fmax_hz": 5.0,
    }

    scalogram = build_scalogram_plot_data(result, display)
    spectrogram = build_spectrogram_plot_data(result, display)

    assert np.min(scalogram["y"]) >= 1.0
    assert np.max(scalogram["y"]) <= 5.0
    assert np.min(spectrogram["y"]) >= 1.0
    assert np.max(spectrogram["y"]) <= 5.0


def test_manual_color_range():
    result = _result()
    display = {
        "active_signal_view": "raw",
        "color_range_mode": "manual",
        "color_min": -2.0,
        "color_max": 3.0,
    }

    assert build_scalogram_plot_data(result, display)["color_range"] == (-2.0, 3.0)
