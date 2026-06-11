"""
preprocessing
-------------
Signal preprocessing utilities for physiological signals.

Filters:
- low_pass: Low-pass Butterworth filter
- high_pass: High-pass Butterworth filter
- band_pass: Band-pass Butterworth filter

Resampling:
- downsample: Resample to a target sampling rate (with anti-aliasing)
- decimate: Decimate by integer factor
"""

from .filter import low_pass, high_pass, band_pass
from .downsample import downsample, decimate
from .pipeline import apply_filter_if_needed, downsample_if_needed, preprocess_signal

__all__ = [
    "apply_filter_if_needed",
    "band_pass",
    "decimate",
    "downsample",
    "downsample_if_needed",
    "high_pass",
    "low_pass",
    "preprocess_signal",
]
