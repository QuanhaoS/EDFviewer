"""
time_domain.py
--------------
Time-domain analysis for physiological signals.

Features:
- Basic statistics (mean, std, var, min, max)
- RMS (root mean square)
- Peak-to-peak amplitude
- Zero-crossing rate
- Hjorth parameters (activity, mobility, complexity)

Dependencies:
- numpy
"""

import numpy as np


def basic_stats(data, axis=-1):
    """
    Compute basic statistics per channel.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    axis : int
        Axis along which to compute (default: -1, time axis)

    Returns
    -------
    dict : mean, std, var, min, max
        Each is array of shape (n_channels,)
    """
    return {
        "mean": np.mean(data, axis=axis),
        "std": np.std(data, axis=axis),
        "var": np.var(data, axis=axis),
        "min": np.min(data, axis=axis),
        "max": np.max(data, axis=axis),
    }


def rms(data, axis=-1):
    """
    Root mean square amplitude.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    axis : int

    Returns
    -------
    np.ndarray : shape (n_channels,)
    """
    return np.sqrt(np.mean(data ** 2, axis=axis))


def peak_to_peak(data, axis=-1):
    """
    Peak-to-peak amplitude (max - min).

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    axis : int

    Returns
    -------
    np.ndarray : shape (n_channels,)
    """
    return np.ptp(data, axis=axis)


def zero_crossing_rate(data, axis=-1):
    """
    Zero-crossing rate: number of sign changes per sample.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    axis : int

    Returns
    -------
    np.ndarray : shape (n_channels,)
    """
    data = np.atleast_2d(data)
    signs = np.sign(data)
    signs[signs == 0] = 1  # treat 0 as positive
    diff = np.diff(signs, axis=axis)
    crossings = np.sum(np.abs(diff) == 2, axis=axis) / 2
    n_samples = data.shape[axis]
    return crossings / (n_samples - 1) if n_samples > 1 else np.zeros(data.shape[0])


def hjorth_parameters(data, axis=-1):
    """
    Hjorth parameters: activity, mobility, complexity.
    Common in EEG analysis.

    - Activity: variance of signal
    - Mobility: std of 1st derivative / std of signal
    - Complexity: mobility of 1st derivative / mobility of signal

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    axis : int

    Returns
    -------
    dict : activity, mobility, complexity
        Each is array of shape (n_channels,)
    """
    data = np.atleast_2d(data)
    d0 = data
    d1 = np.diff(data, axis=axis)
    d2 = np.diff(d1, axis=axis)

    var0 = np.var(d0, axis=axis)
    var1 = np.var(d1, axis=axis)
    var2 = np.var(d2, axis=axis)

    activity = var0
    mobility = np.sqrt(var1 / (var0 + 1e-10))
    complexity = np.sqrt(var2 / (var1 + 1e-10)) / (mobility + 1e-10)

    return {
        "activity": activity,
        "mobility": mobility,
        "complexity": complexity,
    }


def compute_time_features(data, axis=-1):
    """
    Compute all time-domain features as a dictionary.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    axis : int

    Returns
    -------
    dict : all time-domain features per channel
    """
    stats = basic_stats(data, axis=axis)
    hjorth = hjorth_parameters(data, axis=axis)

    return {
        **stats,
        "rms": rms(data, axis=axis),
        "peak_to_peak": peak_to_peak(data, axis=axis),
        "zero_crossing_rate": zero_crossing_rate(data, axis=axis),
        **hjorth,
    }
