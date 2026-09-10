"""Display-independent plot-data builders."""

from __future__ import annotations

from typing import Any

import numpy as np

from core.errors import ParameterValidationError
from core.models import AnalysisResult, TimeFrequencyMap
from core.parameters import DisplayParameters, validate_display_parameters


class VisualizationError(ParameterValidationError):
    """Raised when visualization data cannot be built."""


def build_signal_plot_data(result: AnalysisResult, display: DisplayParameters | Any) -> dict[str, Any]:
    display = _display(display)
    validate_display_parameters(display)
    view = display.active_signal_view
    if view == "raw":
        x, y = _crop_xy_to_window(result, result.times_s, result.raw_signal)
        y_label = "Signal"
    elif view == "bbi":
        x, y = _crop_xy_to_window(result, result.bbi_times_s, result.bbi_values_s)
        y_label = "BBI (s)"
    elif view == "amplitude":
        x, y = _crop_xy_to_window(result, result.amplitude_times_s, result.amplitude_values)
        y_label = "Amplitude"
    else:
        raise VisualizationError(f"Unknown signal view: {view}")
    return {
        "view": view,
        "x": np.asarray(x, dtype=float),
        "y": np.asarray(y, dtype=float),
        "x_label": "Time (s)",
        "y_label": y_label,
        "fit_y": display.fit_signal_y,
    }


def build_scalogram_plot_data(result: AnalysisResult, display: DisplayParameters | Any) -> dict[str, Any]:
    raw_display = display
    display = _display(display)
    validate_display_parameters(display)
    tf_map = _scalogram_for_view(result, display.active_signal_view)
    filtered = _filter_frequency_range(
        tf_map,
        _range_value(raw_display, "scalogram_fmin_hz", result.parameters.scalogram_fmin_hz),
        _range_value(raw_display, "scalogram_fmax_hz", result.parameters.scalogram_fmax_hz),
    )
    filtered = _crop_time_frequency_to_window(result, filtered)
    shared_maps = [
        _crop_time_frequency_to_window(
            result,
            _filter_frequency_range(
                shared_map,
                _range_value(raw_display, "scalogram_fmin_hz", result.parameters.scalogram_fmin_hz),
                _range_value(raw_display, "scalogram_fmax_hz", result.parameters.scalogram_fmax_hz),
            ),
        )
        for shared_map in (result.raw_scalogram, result.bbi_scalogram, result.amplitude_scalogram)
    ]
    color_range = _compute_kind_color_range(
        shared_maps,
        display,
        "scalogram",
    )
    return _map_to_plot_data(filtered, display, display.active_signal_view, color_range)


def build_spectrogram_plot_data(result: AnalysisResult, display: DisplayParameters | Any) -> dict[str, Any]:
    raw_display = display
    display = _display(display)
    validate_display_parameters(display)
    filtered = _filter_frequency_range(
        result.spectrogram,
        _range_value(raw_display, "spectrogram_fmin_hz", result.parameters.spectrogram_fmin_hz),
        _range_value(raw_display, "spectrogram_fmax_hz", result.parameters.spectrogram_fmax_hz),
    )
    filtered = _crop_time_frequency_to_window(result, filtered)
    return _map_to_plot_data(
        filtered,
        display,
        "spectrogram",
        _compute_kind_color_range([filtered], display, "spectrogram"),
    )


def compute_color_range(
    maps: list[TimeFrequencyMap],
    display: DisplayParameters | Any,
) -> tuple[float, float]:
    display = _display(display)
    validate_display_parameters(display)
    manual = _manual_color_range(display, None)
    if manual is not None:
        return manual
    return _auto_color_range(maps)


def _compute_kind_color_range(
    maps: list[TimeFrequencyMap],
    display: DisplayParameters | Any,
    kind: str,
) -> tuple[float, float]:
    display = _display(display)
    validate_display_parameters(display)
    manual = _manual_color_range(display, kind)
    if manual is not None:
        return manual
    return _auto_color_range(maps)


def _manual_color_range(
    display: DisplayParameters,
    kind: str | None,
) -> tuple[float, float] | None:
    if kind is not None:
        mode = getattr(display, f"{kind}_color_range_mode")
        if mode == "manual":
            return (
                float(getattr(display, f"{kind}_color_min")),
                float(getattr(display, f"{kind}_color_max")),
            )
        if mode == "auto":
            return None
    if display.color_range_mode == "manual":
        return float(display.color_min), float(display.color_max)
    return None


def _auto_color_range(maps: list[TimeFrequencyMap]) -> tuple[float, float]:
    finite = []
    for tf_map in maps:
        values = np.asarray(tf_map.values, dtype=float)
        values = values[np.isfinite(values)]
        if values.size:
            finite.append(values)
    if not finite:
        return 0.0, 1.0
    combined = np.concatenate(finite)
    vmin = float(np.min(combined))
    vmax = float(np.max(combined))
    if vmax <= vmin:
        vmax = vmin + 1.0
    return vmin, vmax


def _display(display: DisplayParameters | Any) -> DisplayParameters:
    if isinstance(display, DisplayParameters):
        return display
    if isinstance(display, dict):
        return DisplayParameters(**{k: v for k, v in display.items() if k in DisplayParameters.__dataclass_fields__})
    return DisplayParameters(
        active_signal_view=str(getattr(display, "active_signal_view", "raw")).lower(),
        freq_axis_mode=str(getattr(display, "freq_axis_mode", "linear")),
        color_range_mode=str(getattr(display, "color_range_mode", "auto")),
        color_min=getattr(display, "color_min", None),
        color_max=getattr(display, "color_max", None),
        scalogram_color_range_mode=getattr(display, "scalogram_color_range_mode", None),
        scalogram_color_min=getattr(display, "scalogram_color_min", None),
        scalogram_color_max=getattr(display, "scalogram_color_max", None),
        spectrogram_color_range_mode=getattr(display, "spectrogram_color_range_mode", None),
        spectrogram_color_min=getattr(display, "spectrogram_color_min", None),
        spectrogram_color_max=getattr(display, "spectrogram_color_max", None),
        fit_signal_y=bool(getattr(display, "fit_signal_y", True)),
    )


def _range_value(display: DisplayParameters | Any, name: str, default: float | None) -> float | None:
    if isinstance(display, dict):
        return display.get(name, default)
    return getattr(display, name, default)


def _scalogram_for_view(result: AnalysisResult, view: str) -> TimeFrequencyMap:
    if view == "raw":
        return result.raw_scalogram
    if view == "bbi":
        return result.bbi_scalogram
    if view == "amplitude":
        return result.amplitude_scalogram
    raise VisualizationError(f"Unknown signal view: {view}")


def _filter_frequency_range(
    tf_map: TimeFrequencyMap,
    fmin: float | None,
    fmax: float | None,
) -> TimeFrequencyMap:
    freqs = np.asarray(tf_map.freqs_hz, dtype=float)
    mask = np.ones(freqs.shape, dtype=bool)
    if fmin is not None:
        mask &= freqs >= float(fmin)
    if fmax is not None:
        mask &= freqs <= float(fmax)
    if not np.any(mask):
        raise VisualizationError("Frequency range removes all bins")
    return TimeFrequencyMap(
        times_s=tf_map.times_s,
        freqs_hz=freqs[mask],
        values=tf_map.values[mask, :],
        value_label=tf_map.value_label,
        method=tf_map.method,
    )


def _window_mask(times_s: np.ndarray, window_length_s: float) -> np.ndarray:
    times = np.asarray(times_s, dtype=float)
    return (times >= -1e-9) & (times <= float(window_length_s) + 1e-9)


def _crop_xy_to_window(
    result: AnalysisResult,
    times_s: np.ndarray,
    values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    times = np.asarray(times_s, dtype=float)
    values = np.asarray(values, dtype=float)
    n = min(times.shape[0], values.shape[0])
    times = times[:n]
    values = values[:n]
    mask = _window_mask(times, result.source.window_length_s)
    return _clip_window_times(times[mask], result.source.window_length_s), values[mask]


def _crop_time_frequency_to_window(
    result: AnalysisResult,
    tf_map: TimeFrequencyMap,
) -> TimeFrequencyMap:
    mask = _window_mask(tf_map.times_s, result.source.window_length_s)
    return TimeFrequencyMap(
        times_s=_clip_window_times(tf_map.times_s[mask], result.source.window_length_s),
        freqs_hz=tf_map.freqs_hz,
        values=tf_map.values[:, mask],
        value_label=tf_map.value_label,
        method=tf_map.method,
    )


def _clip_window_times(times_s: np.ndarray, window_length_s: float) -> np.ndarray:
    return np.clip(np.asarray(times_s, dtype=float), 0.0, float(window_length_s))


def _map_to_plot_data(
    tf_map: TimeFrequencyMap,
    display: DisplayParameters,
    view: str,
    color_range: tuple[float, float],
) -> dict[str, Any]:
    return {
        "view": view,
        "x": np.asarray(tf_map.times_s, dtype=float),
        "y": np.asarray(tf_map.freqs_hz, dtype=float),
        "values": np.asarray(tf_map.values, dtype=float),
        "x_label": "Time (s)",
        "y_label": "Frequency (Hz)",
        "value_label": tf_map.value_label,
        "method": tf_map.method,
        "freq_axis_mode": display.freq_axis_mode,
        "color_range": color_range,
    }
