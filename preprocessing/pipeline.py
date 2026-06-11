"""Preprocessing pipeline for one channel window."""

from __future__ import annotations

import numpy as np

from core.errors import PreprocessingError
from core.models import ChannelWindow
from core.parameters import AnalysisParameters
from preprocessing.downsample import downsample
from preprocessing.filter import band_pass, high_pass, low_pass


def _as_1d_signal(signal) -> np.ndarray:
    arr = np.asarray(signal, dtype=float)
    if arr.ndim != 1:
        raise PreprocessingError(f"signal must be one-dimensional, got shape {arr.shape}")
    if arr.size == 0:
        raise PreprocessingError("signal must not be empty")
    return arr


def apply_filter_if_needed(
    signal: np.ndarray,
    sfreq: float,
    parameters: AnalysisParameters,
) -> tuple[np.ndarray, dict]:
    signal = _as_1d_signal(signal)
    if sfreq <= 0:
        raise PreprocessingError("sfreq must be > 0")
    if not parameters.filter_enabled:
        return signal.copy(), {"filter_applied": False}

    try:
        data_2d = signal[np.newaxis, :]
        if parameters.filter_type == "low_pass":
            if parameters.high_cut_hz is None:
                raise PreprocessingError("low-pass requires high_cut_hz")
            filtered = low_pass(data_2d, sfreq, parameters.high_cut_hz, order=parameters.filter_order)[0]
        elif parameters.filter_type == "high_pass":
            if parameters.low_cut_hz is None:
                raise PreprocessingError("high-pass requires low_cut_hz")
            filtered = high_pass(data_2d, sfreq, parameters.low_cut_hz, order=parameters.filter_order)[0]
        elif parameters.filter_type == "band_pass":
            if parameters.low_cut_hz is None or parameters.high_cut_hz is None:
                raise PreprocessingError("band-pass requires low_cut_hz and high_cut_hz")
            filtered = band_pass(
                data_2d,
                sfreq,
                parameters.low_cut_hz,
                parameters.high_cut_hz,
                order=parameters.filter_order,
            )[0]
        else:
            raise PreprocessingError(f"Unknown filter_type: {parameters.filter_type}")
    except PreprocessingError:
        raise
    except Exception as exc:
        raise PreprocessingError("Filter computation failed") from exc

    return filtered, {
        "filter_applied": True,
        "filter_type": parameters.filter_type,
        "low_cut_hz": parameters.low_cut_hz,
        "high_cut_hz": parameters.high_cut_hz,
        "filter_order": parameters.filter_order,
    }


def downsample_if_needed(
    signal: np.ndarray,
    sfreq: float,
    target_sfreq: float | None,
) -> tuple[np.ndarray, float, dict]:
    signal = _as_1d_signal(signal)
    if sfreq <= 0:
        raise PreprocessingError("sfreq must be > 0")
    if target_sfreq is None or abs(float(target_sfreq) - float(sfreq)) < 1e-12:
        return signal.copy(), float(sfreq), {"downsample_applied": False}
    if target_sfreq <= 0:
        raise PreprocessingError("target_sfreq must be > 0")
    if target_sfreq > sfreq:
        raise PreprocessingError("target_sfreq cannot exceed original sampling rate")
    try:
        resampled = downsample(
            signal[np.newaxis, :],
            sfreq,
            target_sfreq,
            axis=1,
            antialias=True,
        )[0]
    except Exception as exc:
        raise PreprocessingError("Downsampling failed") from exc
    return resampled, float(target_sfreq), {
        "downsample_applied": True,
        "original_sfreq": float(sfreq),
        "target_sfreq": float(target_sfreq),
    }


def preprocess_signal(
    window: ChannelWindow,
    parameters: AnalysisParameters,
) -> tuple[np.ndarray, float, dict]:
    signal = _as_1d_signal(window.signal)
    metadata: dict = {
        "input_sfreq": float(window.sfreq),
        "input_samples": int(signal.shape[0]),
    }
    filtered, filter_meta = apply_filter_if_needed(signal, window.sfreq, parameters)
    processed, processed_sfreq, downsample_meta = downsample_if_needed(
        filtered,
        window.sfreq,
        parameters.target_sfreq,
    )
    metadata.update(filter_meta)
    metadata.update(downsample_meta)
    metadata["output_sfreq"] = processed_sfreq
    metadata["output_samples"] = int(processed.shape[0])
    return processed, processed_sfreq, metadata
