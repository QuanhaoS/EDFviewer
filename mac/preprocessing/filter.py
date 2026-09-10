"""
filter.py
---------
Signal filtering utilities for physiological signals.

Filters:
- Low-pass
- High-pass
- Band-pass
- Band-stop

Dependencies:
- numpy
- scipy
"""

import numpy as np
from scipy.signal import iirfilter, sosfiltfilt


_FILTER_TYPE_TO_BTYPE = {
    "low_pass": "lowpass",
    "high_pass": "highpass",
    "band_pass": "bandpass",
    "band_stop": "bandstop",
}


def iir_filter(
    data,
    sfreq,
    cutoff,
    filter_type,
    order=4,
    family="butter",
    ripple_db=1.0,
    stop_atten_db=40.0,
):
    """
    Generic zero-phase IIR filter.

    Parameters
    ----------
    data : np.ndarray
        Shape (n_channels, n_samples)
    sfreq : float
        Sampling frequency (Hz)
    cutoff : float or tuple[float, float]
        Cutoff frequency/frequencies
    filter_type : str
        'low_pass', 'high_pass', 'band_pass', or 'band_stop'
    order : int
        Filter order
    family : str
        scipy.signal.iirfilter family: butter, cheby1, cheby2, ellip, or bessel

    Returns
    -------
    filtered_data : np.ndarray
    """
    btype = _FILTER_TYPE_TO_BTYPE[filter_type]
    kwargs = {}
    if family in {"cheby1", "ellip"}:
        kwargs["rp"] = ripple_db
    if family in {"cheby2", "ellip"}:
        kwargs["rs"] = stop_atten_db
    sos = iirfilter(
        int(order),
        cutoff,
        btype=btype,
        ftype=family,
        output="sos",
        fs=float(sfreq),
        **kwargs,
    )
    return sosfiltfilt(sos, data, axis=1)


def low_pass(data, sfreq, cutoff, order=4, family="butter", ripple_db=1.0, stop_atten_db=40.0):
    """
    Low-pass filter.

    cutoff : float (Hz)
    """
    return iir_filter(
        data,
        sfreq,
        cutoff,
        filter_type="low_pass",
        order=order,
        family=family,
        ripple_db=ripple_db,
        stop_atten_db=stop_atten_db,
    )


def high_pass(data, sfreq, cutoff, order=4, family="butter", ripple_db=1.0, stop_atten_db=40.0):
    """
    High-pass filter.

    cutoff : float (Hz)
    """
    return iir_filter(
        data,
        sfreq,
        cutoff,
        filter_type="high_pass",
        order=order,
        family=family,
        ripple_db=ripple_db,
        stop_atten_db=stop_atten_db,
    )


def band_pass(
    data,
    sfreq,
    low_cut,
    high_cut,
    order=4,
    family="butter",
    ripple_db=1.0,
    stop_atten_db=40.0,
):
    """
    Band-pass filter.

    low_cut : float (Hz)
    high_cut : float (Hz)
    """
    return iir_filter(
        data,
        sfreq,
        cutoff=(low_cut, high_cut),
        filter_type="band_pass",
        order=order,
        family=family,
        ripple_db=ripple_db,
        stop_atten_db=stop_atten_db,
    )


def band_stop(
    data,
    sfreq,
    low_cut,
    high_cut,
    order=4,
    family="butter",
    ripple_db=1.0,
    stop_atten_db=40.0,
):
    """
    Band-stop filter.

    low_cut : float (Hz)
    high_cut : float (Hz)
    """
    return iir_filter(
        data,
        sfreq,
        cutoff=(low_cut, high_cut),
        filter_type="band_stop",
        order=order,
        family=family,
        ripple_db=ripple_db,
        stop_atten_db=stop_atten_db,
    )
