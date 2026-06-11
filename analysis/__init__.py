"""
analysis
--------
Time-domain, frequency-domain, BBI/amplitude, and window-level analysis.
"""

from .freq_domain import (
    EEG_BANDS,
    band_power,
    band_powers,
    compute_freq_features,
    compute_psd,
    cwt_scalogram,
    dominant_frequency,
    spectral_centroid,
    spectrogram,
)
from .ppg import compute_ppg_amplitude, compute_ppi
from .time_domain import (
    basic_stats,
    compute_time_features,
    hjorth_parameters,
    peak_to_peak,
    rms,
    zero_crossing_rate,
)
from .window_analysis import (
    analyze_window,
    compute_feature_table,
    compute_signal_views,
    compute_time_frequency_maps,
)

__all__ = [
    "EEG_BANDS",
    "analyze_window",
    "band_power",
    "band_powers",
    "basic_stats",
    "compute_feature_table",
    "compute_freq_features",
    "compute_psd",
    "compute_ppg_amplitude",
    "compute_signal_views",
    "compute_time_features",
    "compute_time_frequency_maps",
    "compute_ppi",
    "cwt_scalogram",
    "dominant_frequency",
    "hjorth_parameters",
    "peak_to_peak",
    "rms",
    "spectral_centroid",
    "spectrogram",
    "zero_crossing_rate",
]
