"""
analysis
--------
Time-domain and frequency-domain analysis for physiological signals.

Time-domain:
- basic_stats, rms, peak_to_peak, zero_crossing_rate, hjorth_parameters
- compute_time_features

Frequency-domain:
- compute_psd, band_power, band_powers, EEG_BANDS
- dominant_frequency, spectral_centroid
- compute_freq_features, spectrogram, cwt_scalogram

PPG:
- compute_ppg_amplitude, compute_ppi
"""

from .time_domain import (
    basic_stats,
    rms,
    peak_to_peak,
    zero_crossing_rate,
    hjorth_parameters,
    compute_time_features,
)
from .freq_domain import (
    compute_psd,
    band_power,
    band_powers,
    EEG_BANDS,
    dominant_frequency,
    spectral_centroid,
    compute_freq_features,
    spectrogram,
    cwt_scalogram,
)
from .ppg import compute_ppg_amplitude, compute_ppi

__all__ = [
    "basic_stats",
    "rms",
    "peak_to_peak",
    "zero_crossing_rate",
    "hjorth_parameters",
    "compute_time_features",
    "compute_psd",
    "band_power",
    "band_powers",
    "EEG_BANDS",
    "dominant_frequency",
    "spectral_centroid",
    "compute_freq_features",
    "spectrogram",
    "cwt_scalogram",
    "compute_ppg_amplitude",
    "compute_ppi",
]
