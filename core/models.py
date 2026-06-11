"""Shared data models for EDFViewer modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


def _as_1d_float_array(value: Any, name: str) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got shape {arr.shape}")
    return arr


def _require_increasing(arr: np.ndarray, name: str) -> None:
    if arr.size > 1 and not np.all(np.diff(arr) > 0):
        raise ValueError(f"{name} must be strictly increasing")


@dataclass(frozen=True)
class EDFMetadata:
    """Metadata needed after opening one EDF file."""

    file_path: str
    file_name: str
    channel_names: list[str]
    sfreq_by_channel: dict[str, float]
    duration_s: float
    n_samples_by_channel: dict[str, int] = field(default_factory=dict)
    units_by_channel: dict[str, str | None] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.file_path:
            raise ValueError("file_path must not be empty")
        if not self.file_name:
            object.__setattr__(self, "file_name", Path(self.file_path).name)
        if not self.channel_names:
            raise ValueError("channel_names must not be empty")
        if self.duration_s <= 0:
            raise ValueError("duration_s must be greater than 0")
        missing = [ch for ch in self.channel_names if ch not in self.sfreq_by_channel]
        if missing:
            raise ValueError(f"sfreq missing for channels: {missing}")
        bad_sfreq = {
            ch: sfreq
            for ch, sfreq in self.sfreq_by_channel.items()
            if ch in self.channel_names and float(sfreq) <= 0
        }
        if bad_sfreq:
            raise ValueError(f"sampling rates must be positive: {bad_sfreq}")


@dataclass(frozen=True)
class ChannelWindow:
    """Selected signal data for one EDF channel and time window."""

    file_path: str
    channel_name: str
    window_start_s: float
    window_length_s: float
    sfreq: float
    times_s: np.ndarray
    signal: np.ndarray
    units: str | None = None

    def __post_init__(self) -> None:
        times = _as_1d_float_array(self.times_s, "times_s")
        signal = _as_1d_float_array(self.signal, "signal")
        if times.shape[0] != signal.shape[0]:
            raise ValueError("times_s and signal must have the same length")
        if self.window_start_s < 0:
            raise ValueError("window_start_s must be >= 0")
        if self.window_length_s <= 0:
            raise ValueError("window_length_s must be > 0")
        if self.sfreq <= 0:
            raise ValueError("sfreq must be > 0")
        if signal.size == 0:
            raise ValueError("signal must not be empty")
        _require_increasing(times, "times_s")
        object.__setattr__(self, "times_s", times)
        object.__setattr__(self, "signal", signal)


@dataclass(frozen=True)
class TimeFrequencyMap:
    """Display-independent scalogram or spectrogram matrix."""

    times_s: np.ndarray
    freqs_hz: np.ndarray
    values: np.ndarray
    value_label: str
    method: str

    def __post_init__(self) -> None:
        times = _as_1d_float_array(self.times_s, "times_s")
        freqs = _as_1d_float_array(self.freqs_hz, "freqs_hz")
        values = np.asarray(self.values, dtype=float)
        if values.ndim != 2:
            raise ValueError(f"values must be 2-D, got shape {values.shape}")
        if values.shape != (freqs.shape[0], times.shape[0]):
            raise ValueError(
                "values.shape must equal (len(freqs_hz), len(times_s)); "
                f"got {values.shape}, expected {(freqs.shape[0], times.shape[0])}"
            )
        _require_increasing(times, "times_s")
        _require_increasing(freqs, "freqs_hz")
        if np.any(freqs < 0):
            raise ValueError("freqs_hz must be >= 0")
        if self.method not in {"cwt", "stft"}:
            raise ValueError("method must be 'cwt' or 'stft'")
        object.__setattr__(self, "times_s", times)
        object.__setattr__(self, "freqs_hz", freqs)
        object.__setattr__(self, "values", values)


@dataclass
class AnalysisResult:
    """All outputs generated for one selected channel and time window."""

    source: ChannelWindow
    parameters: Any
    processed_signal: np.ndarray
    processed_sfreq: float
    times_s: np.ndarray
    raw_signal: np.ndarray
    bbi_times_s: np.ndarray
    bbi_values_s: np.ndarray
    amplitude_times_s: np.ndarray
    amplitude_values: np.ndarray
    raw_scalogram: TimeFrequencyMap
    bbi_scalogram: TimeFrequencyMap
    amplitude_scalogram: TimeFrequencyMap
    spectrogram: TimeFrequencyMap
    features: dict[str, Any] = field(default_factory=dict)
    preprocessing: dict[str, Any] = field(default_factory=dict)
    from_cache: bool = False

    def __post_init__(self) -> None:
        signal = _as_1d_float_array(self.processed_signal, "processed_signal")
        times = _as_1d_float_array(self.times_s, "times_s")
        raw = _as_1d_float_array(self.raw_signal, "raw_signal")
        if self.processed_sfreq <= 0:
            raise ValueError("processed_sfreq must be > 0")
        if signal.shape[0] != times.shape[0] or raw.shape[0] != times.shape[0]:
            raise ValueError("processed_signal, raw_signal, and times_s lengths must match")
        object.__setattr__(self, "processed_signal", signal)
        object.__setattr__(self, "times_s", times)
        object.__setattr__(self, "raw_signal", raw)


@dataclass(frozen=True)
class ExportResult:
    """Files produced by export actions."""

    png_paths: list[str] = field(default_factory=list)
    csv_paths: list[str] = field(default_factory=list)
    parameter_record_paths: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
