from pathlib import Path

import pytest

from core.parameters import AnalysisParameters
from core.workflow import EDFViewerWorkflow


REAL_EDF = Path("samples/A.0007.edf")


@pytest.mark.skipif(not REAL_EDF.exists(), reason="real EDF sample is missing")
def test_real_edf_load_compute_and_export_smoke(tmp_path):
    workflow = EDFViewerWorkflow()
    metadata = workflow.load_file(str(REAL_EDF))
    assert metadata.channel_names

    channel = metadata.channel_names[0]
    assert workflow.get_channel_range(channel)[1] > 0
    sfreq = metadata.sfreq_by_channel[channel]
    fmax = min(8.0, sfreq / 2.0 - 0.1)
    params = AnalysisParameters(
        target_sfreq=min(50.0, sfreq),
        window_start_s=0.0,
        window_length_s=2.0,
        scalogram_fmax_hz=fmax,
        spectrogram_fmax_hz=fmax,
        scalogram_n_scales=8,
        stft_window_s=0.5,
    )

    result = workflow.compute_window(channel, params)
    assert result.source.channel_name == channel
    assert result.processed_signal.size > 0
    assert result.raw_scalogram.values.shape[0] == 8
    assert result.spectrogram.values.size > 0

    exported = workflow.export_result(result, {"output_dir": tmp_path, "types": ["csv", "parameters"]})
    assert len(exported.csv_paths) == 1
    assert len(exported.parameter_record_paths) == 1
    for path in exported.csv_paths + exported.parameter_record_paths:
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0
