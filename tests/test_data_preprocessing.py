from pathlib import Path

import numpy as np
import pytest

from core.parameters import AnalysisParameters
from data.edf_reader import get_valid_time_range, load_channel_window, load_edf_metadata
from preprocessing.pipeline import preprocess_signal


PHANTOM = Path("samples/phantom.edf")


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
