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

__all__ = ["SignalDataset", "load_edf", "plot_channels"]
