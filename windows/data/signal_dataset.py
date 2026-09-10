"""
signal_dataset.py
-----------------
SignalDataset class for physiological signal analysis.

Current functionality:
- Load EDF file
- Store signal data and metadata
- Select channels
- Crop time segment
- Plot signals

Dependencies:
- mne
- numpy
- matplotlib
- scipy (via preprocessing.filter)
"""

import sys
from pathlib import Path

import mne
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path for preprocessing import
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from preprocessing.filter import low_pass, high_pass, band_pass
from preprocessing.downsample import downsample
from analysis import (
    compute_time_features,
    compute_freq_features,
    compute_psd,
    band_powers,
    spectrogram,
    cwt_scalogram,
    compute_ppg_amplitude,
    compute_ppi,
    EEG_BANDS,
)


class SignalDataset:
    """
    A dataset class for multi-channel physiological signals.
    """

    def __init__(self, edf_path: str):
        """
        Initialize dataset from EDF file.

        Parameters
        ----------
        edf_path : str
            Path to EDF file
        """
        self.edf_path = edf_path
        self.raw = None
        self.data = None
        self.times = None
        self.sfreq = None
        self.ch_names = None

        self._load_edf()

    def _load_edf(self):
        """Load EDF file into memory."""
        self.raw = mne.io.read_raw_edf(
            self.edf_path, preload=True, verbose=False
        )
        self.data, self.times = self.raw.get_data(return_times=True)
        self.sfreq = self.raw.info["sfreq"]
        self.ch_names = self.raw.info["ch_names"]
        self.print_header()

    def print_header(self):
        """
        Print EDF header: overall recording info and per-channel info.
        Called automatically after loading.
        """
        info = self.raw.info
        n_chans = len(self.ch_names)
        n_samples = self.data.shape[1]
        duration_s = n_samples / self.sfreq

        # ----- Overall -----
        print("\n" + "=" * 60)
        print("EDF HEADER")
        print("=" * 60)
        print("[Overall]")
        print(f"  File path      : {self.edf_path}")
        print(f"  Channels       : {n_chans}")
        print(f"  Samples        : {n_samples}")
        print(f"  Duration       : {duration_s:.3f} s")
        print(f"  Sampling rate   : {self.sfreq} Hz")
        if info.get("meas_date") is not None:
            print(f"  Measurement date : {info['meas_date']}")
        if info.get("subject_info"):
            print(f"  Subject info   : {info['subject_info']}")

        # ----- Per channel -----
        print("\n[Per channel]")
        print("-" * 60)
        try:
            ctype_fn = mne.channel_type
        except AttributeError:
            try:
                ctype_fn = mne.io.pick.channel_type
            except AttributeError:
                ctype_fn = lambda inf, idx: str(inf["chs"][idx].get("kind", "?"))

        for i in range(n_chans):
            ch = info["chs"][i]
            ctype = ctype_fn(info, i)
            unit = ch.get("unit", 0)
            cal = ch.get("cal", 1.0)
            range_val = ch.get("range", 1.0)
            phys_range = range_val * cal if cal else range_val
            # Common MNE unit codes: 1072=V, 1092=T, 0=none
            unit_s = "V" if unit == 1072 else ("T" if unit == 1092 else str(unit))
            print(
                f"  [{i:3d}] {self.ch_names[i]:20s}  type={ctype:8s}  "
                f"unit={unit_s:4s}  range={phys_range}"
            )
        print("=" * 60 + "\n")

    # =========================
    # Basic information
    # =========================
    def summary(self):
        """Print dataset summary."""
        print("SignalDataset Summary")
        print("---------------------")
        print(f"EDF file        : {self.edf_path}")
        print(f"Channels        : {len(self.ch_names)}")
        print(f"Samples         : {self.data.shape[1]}")
        print(f"Sampling rate   : {self.sfreq} Hz")
        print(f"Channel names   : {self.ch_names}")

    # =========================
    # Channel & time operations
    # =========================
    def get_channel(self, ch):
        """
        Get signal of a single channel.

        Parameters
        ----------
        ch : int or str
            Channel index or channel name
        """
        if isinstance(ch, int):
            idx = ch
        elif isinstance(ch, str):
            idx = self.ch_names.index(ch)
        else:
            raise ValueError("ch must be int or str")

        return self.data[idx], self.times

    def select_channels(self, channels):
        """
        Select a subset of channels.

        Parameters
        ----------
        channels : list of int or str
        """
        if isinstance(channels[0], str):
            indices = [self.ch_names.index(ch) for ch in channels]
        else:
            indices = channels

        self.data = self.data[indices]
        self.ch_names = [self.ch_names[i] for i in indices]

    def crop(self, tmin: float, tmax: float):
        """
        Crop signal in time.

        Parameters
        ----------
        tmin : float
            Start time (seconds)
        tmax : float
            End time (seconds)
        """
        mask = (self.times >= tmin) & (self.times <= tmax)
        self.times = self.times[mask]
        self.data = self.data[:, mask]

    # =========================
    # Filtering
    # =========================
    def apply_filter(self, filter_type, cutoff=None, low_cut=None, high_cut=None, order=4):
        """
        Apply filter to all channels. Modifies self.data in place.

        Parameters
        ----------
        filter_type : str
            'low_pass', 'high_pass', or 'band_pass'
        cutoff : float, optional
            Cutoff frequency (Hz). Required for low_pass and high_pass.
        low_cut : float, optional
            Low cutoff (Hz). Required for band_pass.
        high_cut : float, optional
            High cutoff (Hz). Required for band_pass.
        order : int
            Filter order (default: 4)

        Examples
        --------
        >>> ds.apply_filter('low_pass', cutoff=40)
        >>> ds.apply_filter('high_pass', cutoff=1)
        >>> ds.apply_filter('band_pass', low_cut=1, high_cut=40)
        """
        if filter_type == "low_pass":
            if cutoff is None:
                raise ValueError("cutoff required for low_pass filter")
            self.data = low_pass(self.data, self.sfreq, cutoff, order=order)
        elif filter_type == "high_pass":
            if cutoff is None:
                raise ValueError("cutoff required for high_pass filter")
            self.data = high_pass(self.data, self.sfreq, cutoff, order=order)
        elif filter_type == "band_pass":
            if low_cut is None or high_cut is None:
                raise ValueError("low_cut and high_cut required for band_pass filter")
            self.data = band_pass(self.data, self.sfreq, low_cut, high_cut, order=order)
        else:
            raise ValueError(
                f"filter_type must be 'low_pass', 'high_pass', or 'band_pass', got '{filter_type}'"
            )

    def downsample(self, target_sfreq, antialias=True):
        """
        Downsample all channels to a lower sampling rate.

        Applies anti-aliasing low-pass then resampling. Updates self.data,
        self.times, and self.sfreq in place.

        Parameters
        ----------
        target_sfreq : float
            Target sampling frequency (Hz). Must be < current self.sfreq.
        antialias : bool
            Apply low-pass before resampling (default: True)

        Examples
        --------
        >>> dataset.downsample(100)   # resample to 100 Hz
        """
        if target_sfreq >= self.sfreq:
            raise ValueError(
                f"target_sfreq ({target_sfreq} Hz) must be less than current sfreq ({self.sfreq} Hz)"
            )
        self.data = downsample(
            self.data, self.sfreq, target_sfreq, axis=1, antialias=antialias
        )
        n_new = self.data.shape[1]
        self.times = np.arange(n_new) / target_sfreq
        self.sfreq = target_sfreq

    # =========================
    # Time-domain analysis
    # =========================
    def time_features(self):
        """
        Compute time-domain features for all channels.

        Returns
        -------
        dict : mean, std, var, min, max, rms, peak_to_peak,
               zero_crossing_rate, activity, mobility, complexity
        """
        return compute_time_features(self.data, axis=1)

    def ppi(self, channel=0):
        """
        Compute peak-to-peak interval (PPI) for one channel (e.g. PPG/PLETH).

        Parameters
        ----------
        channel : int or str
            Channel index or name

        Returns
        -------
        peak_times : np.ndarray
            Time of each detected peak (s)
        ppi : np.ndarray
            Peak-to-peak interval (s), ppi[i] = peak_times[i+1] - peak_times[i]
        """
        sig, times = self.get_channel(channel)
        return compute_ppi(sig, times=times, sfreq=self.sfreq)

    # =========================
    # Frequency-domain analysis
    # =========================
    def freq_features(self, bands=None, nperseg=None):
        """
        Compute frequency-domain features for all channels.

        Parameters
        ----------
        bands : dict, optional
            {name: (low_hz, high_hz)}. Default: EEG_BANDS
        nperseg : int, optional
            Welch segment length

        Returns
        -------
        dict : freqs, psd, band_powers, dominant_frequency, spectral_centroid
        """
        return compute_freq_features(
            self.data, self.sfreq, bands=bands, nperseg=nperseg, axis=1
        )

    def psd(self, nperseg=None):
        """
        Compute power spectral density (Welch method).

        Returns
        -------
        freqs : np.ndarray
        psd : np.ndarray (n_channels, n_freqs)
        """
        return compute_psd(self.data, self.sfreq, nperseg=nperseg, axis=1)

    def band_powers(self, bands=None, nperseg=None):
        """
        Compute power in frequency bands.

        Parameters
        ----------
        bands : dict, optional
            Default: EEG_BANDS (delta, theta, alpha, beta, gamma)

        Returns
        -------
        dict : band name -> array (n_channels,)
        """
        return band_powers(
            self.data, self.sfreq, bands=bands, nperseg=nperseg, axis=1
        )

    # =========================
    # Visualization
    # =========================
    def plot(self, n_channels=5, savepath=None, show=True, dpi=150):
        """
        Plot first N channels.

        Parameters
        ----------
        n_channels : int
        savepath : str or Path, optional
            If set, save figure to this path (e.g. .png, .pdf)
        show : bool
            Whether to display the figure (default: True)
        dpi : int
            DPI for saved image (default: 150)
        """
        n_channels = min(n_channels, self.data.shape[0])

        plt.figure(figsize=(12, 2 * n_channels))
        for i in range(n_channels):
            plt.subplot(n_channels, 1, i + 1)
            plt.plot(self.times, self.data[i])
            plt.ylabel(self.ch_names[i])
            if i == 0:
                plt.title("Signal Preview")

        plt.xlabel("Time (s)")
        plt.tight_layout()
        if savepath is not None:
            plt.savefig(savepath, dpi=dpi, bbox_inches="tight")
        if show:
            plt.show()
        else:
            plt.close()

    def plot_psd(self, n_channels=5, nperseg=None, fmax=None, savepath=None, show=True, dpi=150):
        """
        Plot power spectral density for first N channels.

        Parameters
        ----------
        n_channels : int
        nperseg : int, optional
        fmax : float, optional
            Maximum frequency to display (Hz)
        savepath : str or Path, optional
            If set, save figure to this path
        show : bool
            Whether to display the figure (default: True)
        dpi : int
            DPI for saved image (default: 150)
        """
        freqs, psd = self.psd(nperseg=nperseg)
        n_channels = min(n_channels, psd.shape[0])

        if fmax is not None:
            mask = freqs <= fmax
            freqs, psd = freqs[mask], psd[:, mask]

        plt.figure(figsize=(10, 2 * n_channels))
        for i in range(n_channels):
            plt.subplot(n_channels, 1, i + 1)
            plt.semilogy(freqs, psd[i])
            plt.ylabel(f"{self.ch_names[i]}\n(μV²/Hz)")
            if i == 0:
                plt.title("Power Spectral Density")

        plt.xlabel("Frequency (Hz)")
        plt.tight_layout()
        if savepath is not None:
            plt.savefig(savepath, dpi=dpi, bbox_inches="tight")
        if show:
            plt.show()
        else:
            plt.close()

    def plot_spectrogram(self, channel=0, nperseg=256, fmax=None):
        """
        Plot spectrogram for one channel.

        Parameters
        ----------
        channel : int or str
            Channel index or name
        nperseg : int
        fmax : float, optional
        """
        if isinstance(channel, str):
            ch_idx = self.ch_names.index(channel)
        else:
            ch_idx = channel

        freqs, times, Sxx = spectrogram(
            self.data[ch_idx : ch_idx + 1],
            self.sfreq,
            nperseg=nperseg,
            axis=1,
        )
        Sxx = Sxx[0]

        if fmax is not None:
            mask = freqs <= fmax
            freqs, Sxx = freqs[mask], Sxx[mask, :]

        plt.figure(figsize=(10, 4))
        plt.pcolormesh(
            times, freqs, 10 * np.log10(Sxx + 1e-10), shading="auto", cmap="viridis"
        )
        plt.colorbar(label="Power (dB)")
        plt.ylabel("Frequency (Hz)")
        plt.xlabel("Time (s)")
        plt.title(f"Spectrogram - {self.ch_names[ch_idx]}")
        plt.tight_layout()
        plt.show()

    def plot_scalogram(
        self,
        channel=0,
        wavelet="cmor1.5-1.0",
        fmin=0.5,
        fmax=None,
        n_scales=64,
        y_log=True,
    ):
        """
        Plot scalogram (CWT magnitude) for one channel.

        Uses continuous wavelet transform. Requires PyWavelets (pip install PyWavelets).

        Parameters
        ----------
        channel : int or str
            Channel index or name
        wavelet : str
            Wavelet name for pywt (default: 'cmor1.5-1.0' complex Morlet)
        fmin : float
            Minimum frequency (Hz)
        fmax : float, optional
            Maximum frequency (Hz)
        n_scales : int
            Number of scale bins
        y_log : bool
            Use log scale for frequency axis (default: True)
        """
        if isinstance(channel, str):
            ch_idx = self.ch_names.index(channel)
        else:
            ch_idx = channel

        times, freqs, coefs_mag = cwt_scalogram(
            self.data[ch_idx : ch_idx + 1],
            self.sfreq,
            wavelet=wavelet,
            fmin=fmin,
            fmax=fmax,
            n_scales=n_scales,
            axis=1,
        )
        coefs_mag = coefs_mag[0]

        plt.figure(figsize=(10, 4))
        pcm = plt.pcolormesh(
            times,
            freqs,
            coefs_mag,
            shading="auto",
            cmap="viridis",
        )
        plt.colorbar(pcm, label="|CWT|")
        plt.ylabel("Frequency (Hz)")
        plt.xlabel("Time (s)")
        plt.title(f"Scalogram (CWT) - {self.ch_names[ch_idx]} [{wavelet}]")
        if y_log:
            plt.yscale("log")
        plt.tight_layout()
        plt.show()


# =========================
# Example usage
# =========================
if __name__ == "__main__":
    import os

    # Use sample EDF if available
    edf_path = "samples/A.0007.edf" if os.path.exists("samples/A.0007.edf") else "example.edf"

    dataset = SignalDataset(edf_path)
    dataset.summary()

    # Plot original signals
    dataset.plot(n_channels=5)

    # Example: crop first 10 seconds
    dataset.crop(tmin=0, tmax=10)

    # Example: apply band-pass filter (e.g. 1–40 Hz for EEG)
    dataset.apply_filter("band_pass", low_cut=1, high_cut=40)
    dataset.plot(n_channels=5)
