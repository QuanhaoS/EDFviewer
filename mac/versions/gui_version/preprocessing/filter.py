"""
filter.py
---------
Signal filtering utilities for physiological signals.

Filters:
- Low-pass
- High-pass
- Band-pass

Dependencies:
- numpy
- scipy
"""

import numpy as np
from scipy.signal import butter, filtfilt


def _butter_filter(data, sfreq, cutoff, btype, order=4):
    """
    Internal Butterworth filter.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    sfreq : float
        Sampling frequency (Hz)
    cutoff : float or tuple
        Cutoff frequency/frequencies
    btype : str
        'low', 'high', or 'band'
    order : int
        Filter order

    Returns
    -------
    filtered_data : np.ndarray
    """
    nyq = 0.5 * sfreq

    if btype == "band":
        normal_cutoff = [c / nyq for c in cutoff]
    else:
        normal_cutoff = cutoff / nyq

    b, a = butter(order, normal_cutoff, btype=btype, analog=False)
    filtered_data = filtfilt(b, a, data, axis=1)

    return filtered_data


def low_pass(data, sfreq, cutoff, order=4):
    """
    Low-pass filter.

    cutoff : float (Hz)
    """
    return _butter_filter(data, sfreq, cutoff, btype="low", order=order)


def high_pass(data, sfreq, cutoff, order=4):
    """
    High-pass filter.

    cutoff : float (Hz)
    """
    return _butter_filter(data, sfreq, cutoff, btype="high", order=order)


def band_pass(data, sfreq, low_cut, high_cut, order=4):
    """
    Band-pass filter.

    low_cut : float (Hz)
    high_cut : float (Hz)
    """
    return _butter_filter(
        data,
        sfreq,
        cutoff=(low_cut, high_cut),
        btype="band",
        order=order,
    )
