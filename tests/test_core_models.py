import numpy as np
import pytest

from core.models import ChannelWindow, EDFMetadata, TimeFrequencyMap


def test_channel_window_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        ChannelWindow(
            file_path="x.edf",
            channel_name="sine",
            window_start_s=0.0,
            window_length_s=1.0,
            sfreq=100.0,
            times_s=np.array([0.0, 0.01]),
            signal=np.array([1.0]),
        )


def test_time_frequency_map_validates_dimensions():
    tf = TimeFrequencyMap(
        times_s=np.array([0.0, 1.0]),
        freqs_hz=np.array([1.0, 2.0, 3.0]),
        values=np.ones((3, 2)),
        value_label="power",
        method="cwt",
    )
    assert tf.values.shape == (3, 2)

    with pytest.raises(ValueError):
        TimeFrequencyMap(
            times_s=np.array([0.0, 1.0]),
            freqs_hz=np.array([1.0, 2.0]),
            values=np.ones((3, 2)),
            value_label="power",
            method="stft",
        )


def test_metadata_requires_positive_sampling_rates():
    with pytest.raises(ValueError):
        EDFMetadata(
            file_path="x.edf",
            file_name="x.edf",
            channel_names=["sine"],
            sfreq_by_channel={"sine": 0.0},
            duration_s=1.0,
        )
