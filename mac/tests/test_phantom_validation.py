from pathlib import Path

import numpy as np
import pytest

from core.parameters import AnalysisParameters
from core.workflow import EDFViewerWorkflow


PHANTOM = Path("samples/phantom.edf")


@pytest.mark.skipif(not PHANTOM.exists(), reason="samples/phantom.edf is missing")
def test_phantom_sine_matches_theoretical_frequency_and_amplitude():
    workflow = EDFViewerWorkflow()
    metadata = workflow.load_file(str(PHANTOM))
    assert "sine" in metadata.channel_names
    assert abs(metadata.duration_s - 300.0) < 0.5

    windows = [
        (0.0, 1.5, 200.0),
        (100.0, 1.5, 100.0),
        (200.0, 3.0, 100.0),
    ]
    measured = []
    for start_s, expected_freq_hz, expected_peak_mv in windows:
        params = AnalysisParameters(
            window_start_s=start_s,
            window_length_s=100.0,
            scalogram_fmax_hz=10.0,
            spectrogram_fmax_hz=10.0,
            scalogram_n_scales=16,
            stft_window_s=5.0,
        )
        result = workflow.compute_window("sine", params)
        dominant = result.features["freq_dominant_hz"]
        visible = (result.times_s >= -1e-9) & (result.times_s <= result.source.window_length_s + 1e-9)
        signal = result.processed_signal[visible]
        peak = float(np.max(np.abs(signal - np.mean(signal))))
        peak_mv = peak * 1000.0 if peak < 10.0 else peak
        measured.append((dominant, peak_mv))
        assert dominant == pytest.approx(expected_freq_hz, abs=0.15)
        assert peak_mv == pytest.approx(expected_peak_mv, rel=0.05)
        assert result.raw_scalogram.values.shape[0] == 16
        assert result.spectrogram.values.size > 0

    first_peak = measured[0][1]
    middle_peak = measured[1][1]
    assert first_peak / middle_peak == pytest.approx(2.0, rel=0.1)
