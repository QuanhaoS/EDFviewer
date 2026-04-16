"""
ppg.py
------
PPG (photoplethysmography) / PLETH: amplitude and peak-to-peak interval (PPI).

- compute_ppg_amplitude: peak-to-trough amplitude per cycle
- compute_ppi: peak-to-peak interval (time between consecutive peaks) in seconds

Dependencies:
- numpy
- scipy
"""

import numpy as np
from scipy.signal import find_peaks


def compute_ppg_amplitude(signal, times=None, sfreq=None, min_peak_distance=None, peak_prominence=None):
    """
    Find each PPG cycle and compute amplitude (peak-to-trough) per cycle.

    Cycles are defined by consecutive peaks. For each cycle, amplitude = max - min
    of the signal in that segment. Returns arrays suitable for a stepped plot:
    one amplitude value per cycle, with time at the end of each cycle (so the
    step is constant over the cycle duration).

    Parameters
    ----------
    signal : np.ndarray
        1D PPG/PLETH signal
    times : np.ndarray, optional
        Time for each sample (s). If None, uses sfreq to build times.
    sfreq : float, optional
        Sampling frequency (Hz). Required if times is None.
    min_peak_distance : int, optional
        Minimum samples between peaks. Default: 0.3 * sfreq (≈180 ms at 16 Hz).
    peak_prominence : float, optional
        Minimum prominence for peak detection. Default: 0.1 * (max(signal)-min(signal)).

    Returns
    -------
    amp_times : np.ndarray
        Time point for each amplitude (end of each cycle), length n_cycles.
    amplitudes : np.ndarray
        Amplitude (max - min) for each cycle, length n_cycles.
    """
    signal = np.asarray(signal, dtype=float).ravel()
    n = len(signal)

    if times is None:
        if sfreq is None:
            raise ValueError("Either times or sfreq must be provided")
        times = np.arange(n) / sfreq
    else:
        times = np.asarray(times).ravel()
        if len(times) != n:
            raise ValueError("times length must match signal length")

    if n < 10:
        return np.array([]), np.array([])

    if min_peak_distance is None:
        if sfreq is not None:
            min_peak_distance = max(3, int(0.3 * sfreq))
        else:
            sfreq_est = (n - 1) / (times[-1] - times[0]) if times[-1] > times[0] else 1
            min_peak_distance = max(3, int(0.3 * sfreq_est))

    if peak_prominence is None:
        peak_prominence = 0.1 * (np.nanmax(signal) - np.nanmin(signal) + 1e-10)

    peak_idx, _ = find_peaks(
        signal,
        distance=min_peak_distance,
        prominence=peak_prominence,
    )

    if len(peak_idx) < 2:
        return np.array([]), np.array([])

    amp_times = []
    amplitudes = []

    for i in range(len(peak_idx) - 1):
        start, end = peak_idx[i], peak_idx[i + 1]
        segment = signal[start:end + 1]
        amp = np.max(segment) - np.min(segment)
        amp_times.append(times[end])
        amplitudes.append(amp)

    return np.array(amp_times), np.array(amplitudes)


def compute_ppi(signal, times=None, sfreq=None, min_peak_distance=None, peak_prominence=None):
    """
    Compute peak-to-peak interval (PPI) of PPG: time between consecutive peaks (s).

    Uses the same peak detection as compute_ppg_amplitude. PPI[i] = time of (i+1)-th peak
    minus time of i-th peak (inter-beat interval).

    Parameters
    ----------
    signal : np.ndarray
        1D PPG/PLETH signal
    times : np.ndarray, optional
        Time for each sample (s). If None, uses sfreq to build times.
    sfreq : float, optional
        Sampling frequency (Hz). Required if times is None.
    min_peak_distance : int, optional
        Minimum samples between peaks. Default: 0.3 * sfreq.
    peak_prominence : float, optional
        Minimum prominence for peak detection.

    Returns
    -------
    peak_times : np.ndarray
        Time of each detected peak (s), length n_peaks.
    ppi : np.ndarray
        Peak-to-peak interval (s), length n_peaks - 1. ppi[i] = peak_times[i+1] - peak_times[i].
    """
    signal = np.asarray(signal, dtype=float).ravel()
    n = len(signal)

    if times is None:
        if sfreq is None:
            raise ValueError("Either times or sfreq must be provided")
        times = np.arange(n) / sfreq
    else:
        times = np.asarray(times).ravel()
        if len(times) != n:
            raise ValueError("times length must match signal length")

    if n < 10:
        return np.array([]), np.array([])

    if min_peak_distance is None:
        if sfreq is not None:
            min_peak_distance = max(3, int(0.3 * sfreq))
        else:
            sfreq_est = (n - 1) / (times[-1] - times[0]) if times[-1] > times[0] else 1
            min_peak_distance = max(3, int(0.3 * sfreq_est))

    if peak_prominence is None:
        peak_prominence = 0.1 * (np.nanmax(signal) - np.nanmin(signal) + 1e-10)

    peak_idx, _ = find_peaks(
        signal,
        distance=min_peak_distance,
        prominence=peak_prominence,
    )

    if len(peak_idx) < 2:
        return np.array([]), np.array([])

    peak_times = times[peak_idx]
    ppi = np.diff(peak_times)

    return peak_times, ppi
