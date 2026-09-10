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

__all__ = ["low_pass", "high_pass", "band_pass", "downsample", "decimate"]
