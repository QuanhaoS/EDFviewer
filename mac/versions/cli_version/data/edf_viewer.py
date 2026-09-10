"""
edf_viewer.py
--------------
Basic EDF file reader and signal plotter.

Functionality:
- Load EDF file
- Print basic metadata
- Plot selected channels

Dependencies:
- mne
- numpy
- matplotlib
"""

import mne
import numpy as np
import matplotlib.pyplot as plt


def load_edf(edf_path: str):
    """
    Load EDF file using MNE.

    Parameters
    ----------
    edf_path : str
        Path to EDF file

    Returns
    -------
    raw : mne.io.Raw
        Raw EDF object
    data : np.ndarray
        Signal data, shape (n_channels, n_samples)
    times : np.ndarray
        Time axis in seconds
    """
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    data, times = raw.get_data(return_times=True)
    return raw, data, times


def plot_channels(raw, data, times, n_channels=5):
    """
    Plot first N channels.

    Parameters
    ----------
    raw : mne.io.Raw
    data : np.ndarray
    times : np.ndarray
    n_channels : int
        Number of channels to plot
    """
    n_channels = min(n_channels, data.shape[0])

    plt.figure(figsize=(12, 2 * n_channels))

    for i in range(n_channels):
        plt.subplot(n_channels, 1, i + 1)
        plt.plot(times, data[i])
        plt.ylabel(raw.info["ch_names"][i])
        if i == 0:
            plt.title("EDF Signal Preview")

    plt.xlabel("Time (s)")
    plt.tight_layout()
    plt.show()


def main():
    # ====== MODIFY THIS PATH ======
    edf_path = "example.edf"
    # ==============================

    raw, data, times = load_edf(edf_path)

    # Print basic info
    print("EDF loaded successfully")
    print("-----------------------")
    print(f"Number of channels : {data.shape[0]}")
    print(f"Number of samples  : {data.shape[1]}")
    print(f"Sampling rate (Hz) : {raw.info['sfreq']}")
    print("Channel names      :", raw.info["ch_names"])

    # Plot signals
    plot_channels(raw, data, times, n_channels=5)


if __name__ == "__main__":
    main()
