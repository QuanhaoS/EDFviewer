import csv
import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/edfviewer-mpl")

from analysis.window_analysis import analyze_window
from core.models import ChannelWindow
from core.parameters import AnalysisParameters
from export import (
    build_output_filename,
    export_feature_csv,
    export_parameter_record,
    export_window_pngs,
)


def _result():
    sfreq = 100.0
    times = np.arange(0, 5, 1 / sfreq)
    signal = np.sin(2 * np.pi * 1.5 * times)
    window = ChannelWindow("samples/phantom.edf", "sine", 0.0, 5.0, sfreq, times, signal)
    params = AnalysisParameters(
        target_sfreq=sfreq,
        window_start_s=0.0,
        window_length_s=5.0,
        scalogram_fmin_hz=0.5,
        scalogram_fmax_hz=8.0,
        scalogram_n_scales=8,
        stft_window_s=1.0,
        filter_enabled=True,
        filter_type="band_pass",
        low_cut_hz=0.5,
        high_cut_hz=8.0,
    )
    return analyze_window(window, signal, sfreq, params)


def test_output_filename_contains_source_channel_window_and_type():
    result = _result()

    name = build_output_filename(result, "features", "csv")

    assert name == "phantom_sine_0s-5s_features.csv"


def test_export_feature_csv_writes_header_and_context(tmp_path):
    result = _result()
    path = tmp_path / "features.csv"

    exported = export_feature_csv(result, path)

    with Path(exported).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["source_file"] == "samples/phantom.edf"
    assert rows[0]["channel"] == "sine"
    assert rows[0]["window_start_s"] == "0.0"


def test_export_parameter_record_writes_required_sections(tmp_path):
    result = _result()
    object.__setattr__(result.parameters, "scalogram_color_range_mode", "manual")
    object.__setattr__(result.parameters, "scalogram_color_min", 0.25)
    object.__setattr__(result.parameters, "scalogram_color_max", 1.5)
    object.__setattr__(result.parameters, "spectrogram_color_range_mode", "manual")
    object.__setattr__(result.parameters, "spectrogram_color_min", -70.0)
    object.__setattr__(result.parameters, "spectrogram_color_max", -5.0)
    path = tmp_path / "parameters.json"

    exported = export_parameter_record(result, path)

    record = json.loads(Path(exported).read_text(encoding="utf-8"))
    assert record["source"]["channel_name"] == "sine"
    assert record["sampling"]["processed_sfreq_hz"] == 100.0
    assert record["filtering"]["filter_enabled"] is True
    assert record["cwt"]["wavelet"] == "cmor1.5-1.0"
    assert record["stft"]["stft_window_s"] == 1.0
    assert record["display"]["freq_axis_mode"] == "linear"
    assert record["display"]["scalogram_color_min"] == 0.25
    assert record["display"]["spectrogram_color_max"] == -5.0


def test_export_window_pngs_to_temporary_directory(tmp_path):
    result = _result()
    display = {
        "active_signal_view": "raw",
        "freq_axis_mode": "linear",
        "color_range_mode": "auto",
    }

    paths = export_window_pngs(result, display, tmp_path)

    assert len(paths) == 4
    for path in paths:
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0
