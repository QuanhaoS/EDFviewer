import numpy as np

from analysis.window_analysis import analyze_window
from core.models import ChannelWindow, TimeFrequencyMap
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


def _padded_result():
    sfreq = 100.0
    times = np.arange(-0.5, 10.5, 1 / sfreq)
    signal = np.sin(2 * np.pi * 1.2 * times)
    window = ChannelWindow(
        "synthetic.edf",
        "sine",
        10.0,
        10.0,
        sfreq,
        times,
        signal,
        context_start_s=9.5,
        context_length_s=11.0,
    )
    params = AnalysisParameters(
        window_start_s=10.0,
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


def test_plot_specific_manual_color_ranges_override_legacy_range():
    result = _result()
    display = {
        "active_signal_view": "raw",
        "color_range_mode": "manual",
        "color_min": -2.0,
        "color_max": 3.0,
        "scalogram_color_range_mode": "manual",
        "scalogram_color_min": 0.25,
        "scalogram_color_max": 1.5,
        "spectrogram_color_range_mode": "manual",
        "spectrogram_color_min": -70.0,
        "spectrogram_color_max": -5.0,
    }

    assert build_scalogram_plot_data(result, display)["color_range"] == (0.25, 1.5)
    assert build_spectrogram_plot_data(result, display)["color_range"] == (-70.0, -5.0)


def test_legacy_manual_color_range_applies_to_spectrogram_when_specific_absent():
    result = _result()
    display = {
        "active_signal_view": "raw",
        "color_range_mode": "manual",
        "color_min": -2.0,
        "color_max": 3.0,
    }

    assert build_spectrogram_plot_data(result, display)["color_range"] == (-2.0, 3.0)


def test_plot_data_crops_context_padding_to_selected_window():
    result = _padded_result()

    raw = build_signal_plot_data(result, {"active_signal_view": "raw"})
    scalogram = build_scalogram_plot_data(result, {"active_signal_view": "raw"})
    spectrogram = build_spectrogram_plot_data(result, {"active_signal_view": "raw"})

    assert np.min(raw["x"]) >= 0.0
    assert np.max(raw["x"]) <= result.source.window_length_s
    assert np.min(scalogram["x"]) >= 0.0
    assert np.max(scalogram["x"]) <= result.source.window_length_s
    assert np.min(spectrogram["x"]) >= 0.0
    assert np.max(spectrogram["x"]) <= result.source.window_length_s


def test_auto_color_range_ignores_hidden_context_padding():
    result = _padded_result()
    maps = []
    for tf_map in (result.raw_scalogram, result.bbi_scalogram, result.amplitude_scalogram):
        values = np.array(tf_map.values, copy=True)
        values[:, 0] = 1e9
        values[:, -1] = 1e9
        maps.append(
            TimeFrequencyMap(
                times_s=tf_map.times_s,
                freqs_hz=tf_map.freqs_hz,
                values=values,
                value_label=tf_map.value_label,
                method=tf_map.method,
            )
        )
    result.raw_scalogram, result.bbi_scalogram, result.amplitude_scalogram = maps

    plot_data = build_scalogram_plot_data(result, {"active_signal_view": "raw"})

    assert plot_data["color_range"][1] < 1e9
