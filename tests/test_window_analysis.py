import os

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/edfviewer-mpl")

import mne
import numpy as np

from analysis.window_analysis import analyze_window, compute_signal_views
from core.models import ChannelWindow, TimeFrequencyMap
from core.parameters import AnalysisParameters


def _phantom_sine_window(start_s, length_s=100.0):
    raw = mne.io.read_raw_edf("samples/phantom.edf", preload=True, verbose=False)
    sfreq = float(raw.info["sfreq"])
    idx = raw.info["ch_names"].index("sine")
    start = int(round(start_s * sfreq))
    stop = int(round((start_s + length_s) * sfreq))
    signal = raw.get_data(picks=[idx], start=start, stop=stop)[0]
    times = raw.times[start:stop]
    window = ChannelWindow(
        file_path="samples/phantom.edf",
        channel_name="sine",
        window_start_s=start_s,
        window_length_s=length_s,
        sfreq=sfreq,
        times_s=times,
        signal=signal,
        units="V",
    )
    parameters = AnalysisParameters(
        window_start_s=start_s,
        window_length_s=length_s,
        scalogram_fmin_hz=0.5,
        scalogram_fmax_hz=8.0,
        scalogram_n_scales=16,
        stft_window_s=4.0,
    )
    return window, signal, sfreq, parameters


def test_phantom_sine_first_window_dominant_frequency_near_1p5_hz():
    window, signal, sfreq, parameters = _phantom_sine_window(0.0)

    result = analyze_window(window, signal, sfreq, parameters)

    assert abs(result.features["freq_dominant_hz"] - 1.5) <= 0.15
    assert result.raw_scalogram.values.shape == (
        len(result.raw_scalogram.freqs_hz),
        len(result.raw_scalogram.times_s),
    )
    assert result.spectrogram.values.shape == (
        len(result.spectrogram.freqs_hz),
        len(result.spectrogram.times_s),
    )
    assert np.all(np.diff(result.raw_scalogram.freqs_hz) > 0)
    assert np.all(np.diff(result.spectrogram.freqs_hz) > 0)


def test_phantom_sine_final_window_dominant_frequency_near_3_hz():
    window, signal, sfreq, parameters = _phantom_sine_window(200.0)

    result = analyze_window(window, signal, sfreq, parameters)

    assert abs(result.features["freq_dominant_hz"] - 3.0) <= 0.15


def test_processed_times_remain_relative_after_resampling():
    window, signal, sfreq, parameters = _phantom_sine_window(20.0, length_s=60.0)
    processed = signal[::2]

    result = analyze_window(window, processed, sfreq / 2.0, parameters)

    assert np.isclose(result.times_s[0], 0.0)
    assert 59.0 < result.times_s[-1] < 60.0


def test_phantom_sine_first_segment_amplitude_is_twice_middle_segment():
    first = analyze_window(*_phantom_sine_window(0.0))
    middle = analyze_window(*_phantom_sine_window(100.0))

    ratio = first.features["time_peak_to_peak"] / middle.features["time_peak_to_peak"]

    assert 1.8 <= ratio <= 2.2


def test_bbi_and_amplitude_paths_do_not_crash_on_generic_signal():
    sfreq = 50.0
    times = np.arange(200) / sfreq
    signal = np.linspace(-1.0, 1.0, len(times))

    views = compute_signal_views(signal, times, sfreq)

    assert views["bbi_times_s"].size == 0
    assert views["bbi_values_s"].size == 0
    assert views["amplitude_times_s"].size == 0
    assert views["amplitude_values"].size == 0
    assert views["bbi_series"].shape == signal.shape
    assert views["amplitude_series"].shape == signal.shape


def test_time_frequency_map_rejects_mismatched_dimensions():
    with np.testing.assert_raises(Exception):
        TimeFrequencyMap(
            times_s=np.array([0.0, 1.0]),
            freqs_hz=np.array([1.0, 2.0]),
            values=np.ones((1, 2)),
            value_label="x",
            method="cwt",
        )
