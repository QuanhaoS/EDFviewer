"""Small least-recently-used cache for analysis windows."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, is_dataclass
from typing import Any


class AnalysisCache:
    """LRU cache keyed by source, channel, window, and analysis parameters."""

    def __init__(self, max_size: int = 2):
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self.max_size = int(max_size)
        self._items: OrderedDict[tuple, Any] = OrderedDict()

    def get(self, key: tuple) -> Any | None:
        if key not in self._items:
            return None
        value = self._items.pop(key)
        self._items[key] = value
        return value

    def put(self, key: tuple, result: Any) -> None:
        if key in self._items:
            self._items.pop(key)
        self._items[key] = result
        while len(self._items) > self.max_size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


def _freeze(value: Any) -> Any:
    if is_dataclass(value):
        return _freeze(asdict(value))
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def build_cache_key(
    file_path: str,
    channel_name: str,
    parameters: Any,
) -> tuple:
    """Build a cache key excluding display-only settings."""

    data = asdict(parameters) if is_dataclass(parameters) else dict(parameters)
    included = {
        "window_start_s",
        "window_length_s",
        "target_sfreq",
        "filter_enabled",
        "filter_type",
        "low_cut_hz",
        "high_cut_hz",
        "filter_order",
        "filter_family",
        "filter_ripple_db",
        "filter_stop_atten_db",
        "wavelet",
        "scalogram_fmin_hz",
        "scalogram_fmax_hz",
        "scalogram_n_scales",
        "stft_window_s",
        "spectrogram_fmin_hz",
        "spectrogram_fmax_hz",
    }
    return (file_path, channel_name, _freeze({k: data.get(k) for k in sorted(included)}))
