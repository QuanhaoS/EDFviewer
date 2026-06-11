"""Window-level EDFViewer analysis."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

from analysis.freq_domain import cwt_scalogram, compute_freq_features, spectrogram
from analysis.ppg import compute_ppg_amplitude, compute_ppi
from analysis.time_domain import compute_time_features
from core.errors import AnalysisError
from core.models import AnalysisResult, ChannelWindow, TimeFrequencyMap
from core.parameters import AnalysisParameters


def analyze_window(
    window: ChannelWindow,
    processed_signal: np.ndarray,
    processed_sfreq: float,
    parameters: AnalysisParameters,
    preprocessing_metadata: dict[str, Any] | None = None,
) -> AnalysisResult:
    """Analyze one preprocessed channel window."""

    signal = _as_1d(processed_signal, "processed_signal")
    sfreq = float(processed_sfreq)
    if sfreq <= 0:
        raise AnalysisError("processed_sfreq must be > 0")
    if getattr(window, "times_s", None) is not None and len(window.times_s) == signal.shape[0]:
        times = _relative_times_for_window(window)
    else:
        times = np.arange(signal.shape[0], dtype=float) / sfreq

    signal_views = compute_signal_views(signal, times, sfreq)
    maps = compute_time_frequency_maps(signal_views, sfreq, parameters)
    result = AnalysisResult(
        source=window,
        parameters=parameters,
        processed_signal=signal,
        processed_sfreq=sfreq,
        times_s=times,
        raw_signal=signal_views["raw_values"],
        bbi_times_s=signal_views["bbi_times_s"],
        bbi_values_s=signal_views["bbi_values_s"],
        amplitude_times_s=signal_views["amplitude_times_s"],
        amplitude_values=signal_views["amplitude_values"],
        raw_scalogram=maps["raw_scalogram"],
        bbi_scalogram=maps["bbi_scalogram"],
        amplitude_scalogram=maps["amplitude_scalogram"],
        spectrogram=maps["spectrogram"],
        preprocessing=preprocessing_metadata or {},
    )
    result.features = compute_feature_table(result)
    return result


def compute_signal_views(
    signal: np.ndarray,
    times_s: np.ndarray,
    sfreq: float,
) -> dict[str, np.ndarray]:
    """Compute raw, BBI, amplitude, and sample-aligned derived series."""

    signal = _as_1d(signal, "signal")
    times = _as_1d(times_s, "times_s")
    if signal.shape[0] != times.shape[0]:
        raise AnalysisError("signal and times_s must have the same length")
    if sfreq <= 0:
        raise AnalysisError("sfreq must be > 0")

    try:
        peak_times, bbi_values = compute_ppi(signal, times=times, sfreq=sfreq)
        bbi_times = peak_times[1:] if peak_times.size > 1 else np.array([], dtype=float)
    except Exception:
        bbi_times = np.array([], dtype=float)
        bbi_values = np.array([], dtype=float)

    try:
        amplitude_times, amplitude_values = compute_ppg_amplitude(signal, times=times, sfreq=sfreq)
    except Exception:
        amplitude_times = np.array([], dtype=float)
        amplitude_values = np.array([], dtype=float)

    return {
        "times_s": times,
        "raw_values": signal,
        "bbi_times_s": np.asarray(bbi_times, dtype=float),
        "bbi_values_s": np.asarray(bbi_values, dtype=float),
        "amplitude_times_s": np.asarray(amplitude_times, dtype=float),
        "amplitude_values": np.asarray(amplitude_values, dtype=float),
        "bbi_series": _align_sparse_series(times, bbi_times, bbi_values),
        "amplitude_series": _align_sparse_series(times, amplitude_times, amplitude_values),
    }


def compute_time_frequency_maps(
    signal_views: dict[str, np.ndarray],
    sfreq: float,
    parameters: AnalysisParameters,
) -> dict[str, TimeFrequencyMap]:
    """Compute CWT maps for raw/BBI/amplitude and an STFT spectrogram."""

    maps: dict[str, TimeFrequencyMap] = {}
    for key, series in (
        ("raw_scalogram", signal_views["raw_values"]),
        ("bbi_scalogram", signal_views["bbi_series"]),
        ("amplitude_scalogram", signal_views["amplitude_series"]),
    ):
        maps[key] = _compute_cwt_map(series, sfreq, parameters)
    maps["spectrogram"] = _compute_stft_map(signal_views["raw_values"], sfreq, parameters)
    return maps


def compute_feature_table(result: AnalysisResult) -> dict[str, Any]:
    """Build a CSV-compatible one-row feature table."""

    signal_2d = result.processed_signal[np.newaxis, :]
    try:
        time_features = compute_time_features(signal_2d, axis=1)
        nperseg = min(1024, max(32, signal_2d.shape[1] // 4))
        freq_features = compute_freq_features(
            signal_2d,
            result.processed_sfreq,
            nperseg=nperseg,
            axis=1,
        )
    except Exception as exc:
        raise AnalysisError("Feature computation failed") from exc

    start = float(result.source.window_start_s)
    length = float(result.source.window_length_s)
    features: dict[str, Any] = {
        "source_file": result.source.file_path,
        "channel": result.source.channel_name,
        "window_start_s": start,
        "window_length_s": length,
        "window_end_s": start + length,
        "processed_sfreq_hz": float(result.processed_sfreq),
        "n_samples": int(result.processed_signal.shape[0]),
    }
    for name, value in time_features.items():
        features[f"time_{name}"] = _scalar(value)
    features["freq_dominant_hz"] = _scalar(freq_features["dominant_frequency"])
    features["freq_spectral_centroid_hz"] = _scalar(freq_features["spectral_centroid"])
    for band, value in freq_features["band_powers"].items():
        features[f"freq_band_power_{band}"] = _scalar(value)

    _add_summary(features, "bbi", result.bbi_values_s)
    _add_summary(features, "amplitude", result.amplitude_values)
    return features


def parameter_to_dict(parameters: Any) -> dict[str, Any]:
    if is_dataclass(parameters):
        return _json_ready(asdict(parameters))
    if isinstance(parameters, dict):
        return _json_ready(parameters)
    if hasattr(parameters, "__dict__"):
        return _json_ready({k: v for k, v in vars(parameters).items() if not k.startswith("_")})
    return {}


def source_to_dict(source: Any) -> dict[str, Any]:
    if is_dataclass(source):
        data = asdict(source)
    elif isinstance(source, dict):
        data = dict(source)
    elif hasattr(source, "__dict__"):
        data = {k: v for k, v in vars(source).items() if not k.startswith("_")}
    else:
        data = {}
    data.setdefault("file_path", getattr(source, "file_path", ""))
    data.setdefault("channel_name", getattr(source, "channel_name", ""))
    data.setdefault("window_start_s", getattr(source, "window_start_s", 0.0))
    data.setdefault("window_length_s", getattr(source, "window_length_s", 0.0))
    return _json_ready(data)


def _as_1d(values: Any, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        raise AnalysisError(f"{name} must not be empty")
    return arr


def _relative_times_for_window(window: ChannelWindow) -> np.ndarray:
    times = np.asarray(window.times_s, dtype=float)
    start_s = float(getattr(window, "window_start_s", 0.0))
    if times.size > 0 and start_s > 0 and abs(float(times[0]) - start_s) < 1e-6:
        times = times - start_s
    return times


def _align_sparse_series(
    target_times_s: np.ndarray,
    event_times_s: np.ndarray,
    event_values: np.ndarray,
) -> np.ndarray:
    target = np.asarray(target_times_s, dtype=float)
    xs = np.asarray(event_times_s, dtype=float)
    ys = np.asarray(event_values, dtype=float)
    if xs.size == 0 or ys.size == 0:
        return np.zeros_like(target, dtype=float)
    n = min(xs.size, ys.size)
    xs = xs[:n]
    ys = ys[:n]
    valid = np.isfinite(xs) & np.isfinite(ys)
    xs = xs[valid]
    ys = ys[valid]
    if xs.size == 0:
        return np.zeros_like(target, dtype=float)
    order = np.argsort(xs)
    xs = xs[order]
    ys = ys[order]
    unique_xs, unique_idx = np.unique(xs, return_index=True)
    unique_ys = ys[unique_idx]
    if unique_xs.size == 1:
        return np.full_like(target, float(unique_ys[0]), dtype=float)
    return np.interp(target, unique_xs, unique_ys, left=float(unique_ys[0]), right=float(unique_ys[-1]))


def _compute_cwt_map(
    signal: np.ndarray,
    sfreq: float,
    parameters: AnalysisParameters,
) -> TimeFrequencyMap:
    try:
        times, freqs, values = cwt_scalogram(
            signal,
            sfreq,
            wavelet=parameters.wavelet,
            fmin=parameters.scalogram_fmin_hz,
            fmax=parameters.scalogram_fmax_hz,
            n_scales=parameters.scalogram_n_scales,
        )
    except Exception as exc:
        raise AnalysisError("CWT scalogram computation failed") from exc
    values = np.asarray(values, dtype=float)
    if values.ndim == 3:
        values = values[0]
    freqs, values = _sort_freqs(freqs, values)
    return TimeFrequencyMap(
        times_s=np.asarray(times, dtype=float),
        freqs_hz=freqs,
        values=values,
        value_label="|CWT|",
        method="cwt",
    )


def _compute_stft_map(
    signal: np.ndarray,
    sfreq: float,
    parameters: AnalysisParameters,
) -> TimeFrequencyMap:
    nperseg = max(8, int(round(parameters.stft_window_s * sfreq)))
    nperseg = min(nperseg, len(signal))
    try:
        freqs, times, values = spectrogram(signal, sfreq, nperseg=nperseg)
    except Exception as exc:
        raise AnalysisError("STFT spectrogram computation failed") from exc
    values = np.asarray(values, dtype=float)
    if values.ndim == 3:
        values = values[0]
    values = 10.0 * np.log10(values + np.finfo(float).eps)
    mask = (freqs >= parameters.spectrogram_fmin_hz) & (freqs <= parameters.spectrogram_fmax_hz)
    freqs = np.asarray(freqs, dtype=float)[mask]
    values = values[mask, :]
    freqs, values = _sort_freqs(freqs, values)
    return TimeFrequencyMap(
        times_s=np.asarray(times, dtype=float),
        freqs_hz=freqs,
        values=values,
        value_label="Power (dB)",
        method="stft",
    )


def _sort_freqs(freqs: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    freqs = np.asarray(freqs, dtype=float)
    values = np.asarray(values, dtype=float)
    order = np.argsort(freqs)
    return freqs[order], values[order, :]


def _scalar(value: Any) -> Any:
    arr = np.asarray(value)
    if arr.size == 0:
        return None
    return float(arr.ravel()[0])


def _add_summary(features: dict[str, Any], prefix: str, values: np.ndarray) -> None:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    features[f"{prefix}_count"] = int(finite.size)
    if finite.size:
        features[f"{prefix}_mean"] = float(np.mean(finite))
        features[f"{prefix}_std"] = float(np.std(finite))
        features[f"{prefix}_min"] = float(np.min(finite))
        features[f"{prefix}_max"] = float(np.max(finite))
    else:
        features[f"{prefix}_mean"] = None
        features[f"{prefix}_std"] = None
        features[f"{prefix}_min"] = None
        features[f"{prefix}_max"] = None


def _json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value
