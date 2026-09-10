"""
data
----
Data loading and signal dataset for physiological signals.

Classes:
- SignalDataset: Multi-channel physiological signal dataset (EDF)

Functions:
- load_edf: Load EDF file and return raw, data, times
- plot_channels: Plot selected channels from raw EDF data
"""

from .signal_dataset import SignalDataset
from .edf_viewer import load_edf, plot_channels
from .edf_reader import get_valid_time_range, load_channel_window, load_edf_metadata

__all__ = [
    "SignalDataset",
    "get_valid_time_range",
    "load_channel_window",
    "load_edf",
    "load_edf_metadata",
    "plot_channels",
]
