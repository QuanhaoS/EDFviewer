"""
freq_domain.py
--------------
Frequency-domain analysis for physiological signals.

Features:
- Power spectral density (Welch method)
- Band power (delta, theta, alpha, beta, gamma)
- Dominant frequency
- Spectral centroid
- Spectrogram
- CWT scalogram (continuous wavelet transform)

Dependencies:
- numpy
- scipy
- pywt (PyWavelets, for CWT scalogram)
"""

import numpy as np
from scipy.signal import welch


# Default EEG frequency bands (Hz)
EEG_BANDS = {
    "delta": (0.5, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "beta": (13, 30),
    "gamma": (30, 50),
}


def compute_psd(data, sfreq, nperseg=None, axis=-1):
    """
    Compute power spectral density using Welch method.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    sfreq : float
        Sampling frequency (Hz)
    nperseg : int, optional
        Length of each segment for Welch. Default: min(256, n_samples // 4)
    axis : int
        Time axis (default: -1)

    Returns
    -------
    freqs : np.ndarray
        Frequency bins (Hz)
    psd : np.ndarray
        Power spectral density, shape (n_channels, n_freqs)
    """
    data = np.atleast_2d(data)
    n_samples = data.shape[axis]

    if nperseg is None:
        nperseg = min(256, max(32, n_samples // 4))

    # Welch along time axis
    freqs, psd = welch(data, fs=sfreq, nperseg=nperseg, axis=axis)
    return freqs, psd


def band_power(psd, freqs, low, high):
    """
    Compute power in a frequency band by integrating PSD.

    Parameters
    ----------
    psd : np.ndarray
        Shape (n_channels, n_freqs)
    freqs : np.ndarray
        Frequency bins
    low : float
        Low frequency (Hz)
    high : float
        High frequency (Hz)

    Returns
    -------
    np.ndarray : shape (n_channels,) - power in band
    """
    mask = (freqs >= low) & (freqs <= high)
    if hasattr(np, "trapezoid"):
        integrate = np.trapezoid
    else:
        integrate = np.trapz
    return integrate(psd[:, mask], freqs[mask], axis=-1)


def band_powers(data, sfreq, bands=None, nperseg=None, axis=-1):
    """
    Compute power in multiple frequency bands.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    sfreq : float
        Sampling frequency (Hz)
    bands : dict, optional
        {name: (low_hz, high_hz)}. Default: EEG_BANDS
    nperseg : int, optional
    axis : int

    Returns
    -------
    dict : band name -> array of shape (n_channels,)
    """
    if bands is None:
        bands = EEG_BANDS

    freqs, psd = compute_psd(data, sfreq, nperseg=nperseg, axis=axis)

    result = {}
    for name, (low, high) in bands.items():
        result[name] = band_power(psd, freqs, low, high)

    return result


def dominant_frequency(psd, freqs, low=None, high=None):
    """
    Find frequency with maximum power in optional band.

    Parameters
    ----------
    psd : np.ndarray
        Shape (n_channels, n_freqs)
    freqs : np.ndarray
        Frequency bins
    low, high : float, optional
        Restrict search to [low, high] Hz

    Returns
    -------
    np.ndarray : shape (n_channels,) - dominant frequency (Hz)
    """
    if low is not None:
        mask = freqs >= low
    else:
        mask = np.ones_like(freqs, dtype=bool)
    if high is not None:
        mask &= freqs <= high

    # Index of max power per channel
    psd_masked = np.where(mask, psd, -np.inf)
    idx = np.argmax(psd_masked, axis=-1)
    return freqs[idx]


def spectral_centroid(psd, freqs, axis=-1):
    """
    Spectral centroid: weighted mean frequency.

    Parameters
    ----------
    psd : np.ndarray
        Shape (n_channels, n_freqs)
    freqs : np.ndarray
        Frequency bins
    axis : int

    Returns
    -------
    np.ndarray : shape (n_channels,) - centroid (Hz)
    """
    power_sum = np.sum(psd, axis=axis, keepdims=True)
    power_sum = np.where(power_sum > 0, power_sum, 1)
    centroid = np.sum(freqs * psd, axis=axis) / np.squeeze(power_sum)
    return centroid


def compute_freq_features(data, sfreq, bands=None, nperseg=None, axis=-1):
    """
    Compute all frequency-domain features.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    sfreq : float
        Sampling frequency (Hz)
    bands : dict, optional
    nperseg : int, optional
    axis : int

    Returns
    -------
    dict : freqs, psd, band_powers, dominant_freq, spectral_centroid
    """
    freqs, psd = compute_psd(data, sfreq, nperseg=nperseg, axis=axis)

    bp = band_powers(data, sfreq, bands=bands, nperseg=nperseg, axis=axis)

    return {
        "freqs": freqs,
        "psd": psd,
        "band_powers": bp,
        "dominant_frequency": dominant_frequency(psd, freqs),
        "spectral_centroid": spectral_centroid(psd, freqs, axis=axis),
    }


def spectrogram(data, sfreq, nperseg=256, noverlap=None, axis=-1):
    """
    Compute spectrogram (time-frequency representation).

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    sfreq : float
        Sampling frequency (Hz)
    nperseg : int
    noverlap : int, optional
        Default: nperseg // 2
    axis : int

    Returns
    -------
    freqs : np.ndarray
    times : np.ndarray
    Sxx : np.ndarray
        Shape (n_channels, n_freqs, n_times)
    """
    from scipy.signal import spectrogram

    data = np.atleast_2d(data)
    if noverlap is None:
        noverlap = nperseg // 2

    freqs, times, Sxx = spectrogram(
        data, fs=sfreq, nperseg=nperseg, noverlap=noverlap, axis=axis
    )

    return freqs, times, Sxx


def _haar_scales_from_freqs(freqs_hz: np.ndarray, sfreq: float) -> np.ndarray:
    """Map Hz to Haar CWT scales (width in samples): f ≈ sfreq / (2 * scale)."""
    freqs_hz = np.asarray(freqs_hz, dtype=float)
    freqs_hz = np.maximum(freqs_hz, 1e-6)
    scales = sfreq / (2.0 * freqs_hz)
    return np.sort(scales)[::-1]


def _cwt_haar_1d(signal: np.ndarray, scales: np.ndarray) -> np.ndarray:
    """
    Haar CWT via convolution (PyWavelets has no continuous Haar).

    Returns |CWT| with shape (n_scales, n_samples).
    """
    from scipy.signal import convolve

    sig = np.asarray(signal, dtype=float).ravel()
    n = sig.shape[0]
    scales = np.asarray(scales, dtype=float)
    coefs = np.empty((scales.shape[0], n), dtype=float)
    for i, scale in enumerate(scales):
        width = max(2, int(np.ceil(float(scale))))
        if width % 2:
            width += 1
        half = width // 2
        psi = np.concatenate([np.ones(half, dtype=float), -np.ones(half, dtype=float)])
        psi /= np.linalg.norm(psi) + 1e-12
        coefs[i] = np.abs(convolve(sig, psi[::-1], mode="same"))
    return coefs


def cwt_scalogram(
    data,
    sfreq,
    wavelet="cmor1.5-1.0",
    fmin=0.5,
    fmax=None,
    n_scales=64,
    axis=-1,
):
    """
    Continuous wavelet transform (CWT) and scalogram.

    Uses PyWavelets. Returns times, frequencies, and magnitude of CWT
    coefficients for plotting (e.g. scalogram = |CWT| or |CWT|²).

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples) or (n_samples,) for single channel
    sfreq : float
        Sampling frequency (Hz)
    wavelet : str
        Wavelet name for pywt.cwt (default: 'cmor1.5-1.0' complex Morlet).
        Use 'haar' for a custom Haar CWT (not provided by PyWavelets).
        Examples: 'morl', 'mexh', 'cmor1.5-1.0', 'haar'
    fmin : float
        Minimum frequency (Hz)
    fmax : float, optional
        Maximum frequency (Hz). Default: sfreq / 4 (below Nyquist)
    n_scales : int
        Number of scale bins (log-spaced between fmin and fmax)
    axis : int
        Time axis (default: -1)

    Returns
    -------
    times : np.ndarray
        Time points (s), length n_samples
    freqs : np.ndarray
        Frequency bins (Hz), length n_scales
    coefs_mag : np.ndarray
        Magnitude of CWT coefficients.
        Shape (n_channels, n_scales, n_samples) or (n_scales, n_samples) for 1D
    """
    try:
        import pywt
    except ImportError:
        raise ImportError("CWT scalogram requires PyWavelets: pip install PyWavelets")

    data = np.asarray(data)
    if data.ndim == 0:
        raise ValueError("data must have at least 1 dimension")

    axis = int(axis)
    if axis < 0:
        axis += data.ndim
    if axis < 0 or axis >= data.ndim:
        raise ValueError(f"axis out of range: {axis} for data.ndim={data.ndim}")

    # Move the requested time axis to the end so the CWT loop can be axis-agnostic.
    data_t_last = np.moveaxis(data, axis, -1)
    input_was_1d = data_t_last.ndim == 1
    if input_was_1d:
        data_t_last = data_t_last[np.newaxis, :]

    if fmax is None:
        fmax = sfreq / 4.0

    sampling_period = 1.0 / sfreq

    # Convert frequency range to scales (pywt: scale2frequency(wavelet, scale) / dt = f)
    freqs_desired = np.logspace(
        np.log10(max(fmin, 0.1)), np.log10(min(fmax, sfreq / 2 - 0.1)), n_scales
    )
    use_haar = str(wavelet).lower() == "haar"
    if use_haar:
        scales = _haar_scales_from_freqs(freqs_desired, sfreq)
        freqs = freqs_desired
    else:
        # frequency2scale expects normalized frequency (f / fs)
        freqs_norm = freqs_desired * sampling_period
        scales = pywt.frequency2scale(wavelet, freqs_norm)
        scales = np.sort(scales)[::-1]

    # Reshape to (n_channels, n_samples), where channel can represent any
    # combination of non-time axes.
    n_samples = data_t_last.shape[-1]
    non_time_shape = data_t_last.shape[:-1]
    data_2d = data_t_last.reshape(-1, n_samples)
    n_channels = data_2d.shape[0]

    coefs_list = []
    for ch in range(n_channels):
        sig = data_2d[ch, :]
        if use_haar:
            coefs = _cwt_haar_1d(sig, scales)
        else:
            coefs, freqs = pywt.cwt(
                sig, scales, wavelet, sampling_period=sampling_period
            )
            coefs = np.abs(coefs)
        coefs_list.append(coefs)
    coefs_mag = np.stack(coefs_list, axis=0)  # (n_channels, n_scales, n_samples)

    # Restore non-time dimensions: (...non_time, n_scales, n_samples)
    coefs_mag = coefs_mag.reshape(*non_time_shape, coefs_mag.shape[-2], coefs_mag.shape[-1])

    # pywt.cwt already returns frequencies aligned to the supplied scales.
    # With the current scale construction this is low->high, which is what we
    # want for plotting (low frequency at the bottom, high at the top).

    times = np.arange(n_samples) * sampling_period

    if input_was_1d:
        coefs_mag = coefs_mag.squeeze(axis=0)

    return times, freqs, coefs_mag
