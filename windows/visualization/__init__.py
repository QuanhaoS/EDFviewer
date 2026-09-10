"""
Display-independent plot-data builders.
"""

from .plot_data import (
    VisualizationError,
    build_scalogram_plot_data,
    build_signal_plot_data,
    build_spectrogram_plot_data,
    compute_color_range,
)

__all__ = [
    "VisualizationError",
    "build_signal_plot_data",
    "build_scalogram_plot_data",
    "build_spectrogram_plot_data",
    "compute_color_range",
]
