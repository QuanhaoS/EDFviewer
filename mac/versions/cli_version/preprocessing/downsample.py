"""
downsample.py
-------------
Downsampling for physiological signals.

- Anti-aliasing low-pass filter + decimation, or
- Polyphase resampling to a target sampling rate.

Dependencies:
- numpy
- scipy
"""

import numpy as np
from scipy.signal import resample_poly, butter, filtfilt
from fractions import Fraction


def _rational_ratio(target_sfreq, orig_sfreq):
    """Return (up, down) integers such that up/down = target_sfreq/orig_sfreq."""
    f = Fraction(int(round(target_sfreq)), int(round(orig_sfreq)))
    return f.numerator, f.denominator


def downsample(data, sfreq_orig, target_sfreq, axis=-1, antialias=True, filter_order=4):
    """
    Downsample signal to a lower sampling rate.

    Applies anti-aliasing low-pass filter (at ~0.8 * target_sfreq/2) then
    polyphase resampling. Modifies neither the input array nor the time axis;
    the caller must update times and sfreq.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    sfreq_orig : float
        Current sampling frequency (Hz)
    target_sfreq : float
        Target sampling frequency (Hz). Must be < sfreq_orig.
    axis : int
        Time axis (default: -1)
    antialias : bool
        If True (default), apply low-pass before resampling to avoid aliasing.
    filter_order : int
        Order of anti-aliasing Butterworth filter (default: 4)

    Returns
    -------
    resampled_data : np.ndarray
        Shape (n_channels, n_samples_new) where n_samples_new = n_samples * target_sfreq / sfreq_orig
    """
    if target_sfreq >= sfreq_orig:
        raise ValueError(
            f"target_sfreq ({target_sfreq} Hz) must be less than sfreq_orig ({sfreq_orig} Hz)"
        )

    data = np.asarray(data)
    n_samples = data.shape[axis]

    if antialias:
        nyq_new = 0.5 * target_sfreq
        cutoff = 0.8 * nyq_new
        nyq_orig = 0.5 * sfreq_orig
        normal_cutoff = cutoff / nyq_orig
        b, a = butter(filter_order, normal_cutoff, btype="low", analog=False)
        data = filtfilt(b, a, data, axis=axis)

    up, down = _rational_ratio(target_sfreq, sfreq_orig)
    # resample_poly: new_len = n_samples * up / down
    resampled = resample_poly(data, up, down, axis=axis)

    return resampled


def decimate(data, factor, sfreq, axis=-1, antialias=True, filter_order=4):
    """
    Decimate by an integer factor (keep every factor-th sample after anti-alias).

    Convenience when you want to reduce by 2x, 4x, etc. New rate = sfreq / factor.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    factor : int
        Decimation factor (e.g. 2 -> half the samples)
    sfreq : float
        Current sampling frequency (Hz)
    axis : int
        Time axis (default: -1)
    antialias : bool
        Apply low-pass before decimation (default: True)
    filter_order : int
        Anti-aliasing filter order (default: 4)

    Returns
    -------
    decimated_data : np.ndarray
        Shape (n_channels, n_samples // factor)
    """
    factor = int(factor)
    if factor < 1:
        raise ValueError("factor must be >= 1")
    if factor == 1:
        return np.asarray(data, dtype=np.float64).copy()
    target_sfreq = sfreq / factor
    return downsample(data, sfreq, target_sfreq, axis=axis, antialias=antialias, filter_order=filter_order)
