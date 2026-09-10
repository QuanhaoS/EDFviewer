from pathlib import Path

import numpy as np
import pytest

from core.parameters import AnalysisParameters
from core.models import ChannelWindow
from data.edf_reader import get_valid_time_range, load_channel_window, load_edf_metadata
from preprocessing.pipeline import preprocess_signal


PHANTOM = Path("samples/phantom.edf")
MULTI_SFREQ_EDF = Path("samples/cfs-visit5-800537.edf")


@pytest.mark.skipif(not PHANTOM.exists(), reason="samples/phantom.edf is missing")
def test_load_phantom_metadata_and_window():
    metadata = load_edf_metadata(str(PHANTOM))
    assert "sine" in metadata.channel_names
    assert abs(metadata.duration_s - 300.0) < 0.5
    assert get_valid_time_range(metadata, "sine") == (0.0, metadata.duration_s)

    window = load_channel_window(str(PHANTOM), "sine", 0.0, 10.0)
    assert window.signal.ndim == 1
    assert len(window.signal) == len(window.times_s)
    assert abs(window.sfreq - 100.0) < 1e-6


@pytest.mark.skipif(not PHANTOM.exists(), reason="samples/phantom.edf is missing")
def test_load_phantom_invalid_window_fails():
    with pytest.raises(Exception):
        load_channel_window(str(PHANTOM), "sine", 299.0, 10.0)


@pytest.mark.skipif(not MULTI_SFREQ_EDF.exists(), reason="multi-sfreq EDF sample is missing")
def test_load_metadata_preserves_channel_original_sampling_rates():
    metadata = load_edf_metadata(str(MULTI_SFREQ_EDF))

    assert metadata.sfreq_by_channel["C3"] == 128.0
    assert metadata.sfreq_by_channel["ECG2"] == 256.0
    assert metadata.n_samples_by_channel["C3"] == 128 * 28770
    assert metadata.n_samples_by_channel["ECG2"] == 256 * 28770


def test_preprocess_downsamples_sine():
    sfreq = 100.0
    times = np.arange(0.0, 10.0, 1.0 / sfreq)
    signal = np.sin(2 * np.pi * 2.0 * times)
    window = load_channel_window(str(PHANTOM), "sine", 0.0, 10.0) if PHANTOM.exists() else None
    if window is None:
        from core.models import ChannelWindow

        window = ChannelWindow(
            file_path="synthetic.edf",
            channel_name="synthetic",
            window_start_s=0.0,
            window_length_s=10.0,
            sfreq=sfreq,
            times_s=times,
            signal=signal,
        )
    params = AnalysisParameters(target_sfreq=50.0)
    processed, processed_sfreq, meta = preprocess_signal(window, params)
    assert processed.ndim == 1
    assert abs(processed_sfreq - 50.0) < 1e-6
    assert meta["downsample_applied"] is True
    assert abs(len(processed) - 500) <= 2


def _synthetic_window():
    sfreq = 100.0
    times = np.arange(0.0, 30.0, 1.0 / sfreq)
    signal = (
        np.sin(2 * np.pi * 1.0 * times)
        + 0.8 * np.sin(2 * np.pi * 6.0 * times)
        + 0.5 * np.sin(2 * np.pi * 20.0 * times)
    )
    return ChannelWindow(
        file_path="synthetic.edf",
        channel_name="synthetic",
        window_start_s=0.0,
        window_length_s=30.0,
        sfreq=sfreq,
        times_s=times,
        signal=signal,
    )


def _tone_amplitude(signal, sfreq, freq):
    times = np.arange(signal.shape[0], dtype=float) / float(sfreq)
    sine = np.sin(2 * np.pi * float(freq) * times)
    cosine = np.cos(2 * np.pi * float(freq) * times)
    return 2.0 * np.hypot(np.dot(signal, sine), np.dot(signal, cosine)) / signal.shape[0]


def test_iir_filter_types_attenuate_expected_bands():
    window = _synthetic_window()

    low, sfreq, _ = preprocess_signal(
        window,
        AnalysisParameters(
            filter_enabled=True,
            filter_type="low_pass",
            high_cut_hz=5.0,
            filter_order=4,
        ),
    )
    high, _, _ = preprocess_signal(
        window,
        AnalysisParameters(
            filter_enabled=True,
            filter_type="high_pass",
            low_cut_hz=10.0,
            filter_order=4,
        ),
    )
    band, _, _ = preprocess_signal(
        window,
        AnalysisParameters(
            filter_enabled=True,
            filter_type="band_pass",
            low_cut_hz=4.0,
            high_cut_hz=8.0,
            filter_order=4,
        ),
    )
    stop, _, _ = preprocess_signal(
        window,
        AnalysisParameters(
            filter_enabled=True,
            filter_type="band_stop",
            low_cut_hz=4.0,
            high_cut_hz=8.0,
            filter_order=4,
        ),
    )

    assert _tone_amplitude(low, sfreq, 1.0) > 5.0 * _tone_amplitude(low, sfreq, 20.0)
    assert _tone_amplitude(high, sfreq, 20.0) > 5.0 * _tone_amplitude(high, sfreq, 1.0)
    assert _tone_amplitude(band, sfreq, 6.0) > 5.0 * _tone_amplitude(band, sfreq, 1.0)
    assert _tone_amplitude(band, sfreq, 6.0) > 5.0 * _tone_amplitude(band, sfreq, 20.0)
    assert _tone_amplitude(stop, sfreq, 1.0) > 5.0 * _tone_amplitude(stop, sfreq, 6.0)


@pytest.mark.parametrize("family", ["butter", "cheby1", "cheby2", "ellip", "bessel"])
def test_iir_filter_families_run_without_shape_or_nan_changes(family):
    window = _synthetic_window()

    processed, sfreq, meta = preprocess_signal(
        window,
        AnalysisParameters(
            filter_enabled=True,
            filter_type="low_pass",
            high_cut_hz=12.0,
            filter_order=3,
            filter_family=family,
            filter_ripple_db=1.0,
            filter_stop_atten_db=40.0,
        ),
    )

    assert processed.shape == window.signal.shape
    assert sfreq == window.sfreq
    assert np.all(np.isfinite(processed))
    assert meta["filter_applied"] is True
    assert meta["filter_family"] == family


def test_disabled_filter_returns_copy_and_metadata():
    window = _synthetic_window()

    processed, sfreq, meta = preprocess_signal(window, AnalysisParameters())

    assert processed is not window.signal
    assert np.allclose(processed, window.signal)
    assert sfreq == window.sfreq
    assert meta["filter_applied"] is False
