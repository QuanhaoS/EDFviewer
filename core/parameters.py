"""Analysis and display parameter management."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .errors import ParameterValidationError
from .models import EDFMetadata


FilterType = Literal["low_pass", "high_pass", "band_pass"]


@dataclass(frozen=True)
class AnalysisParameters:
    target_sfreq: float | None = None
    window_start_s: float = 0.0
    window_length_s: float = 60.0
    wavelet: str = "cmor1.5-1.0"
    scalogram_fmin_hz: float = 0.1
    scalogram_fmax_hz: float = 10.0
    scalogram_n_scales: int = 64
    stft_window_s: float = 5.0
    spectrogram_fmin_hz: float = 0.0
    spectrogram_fmax_hz: float = 10.0
    freq_axis_mode: Literal["linear", "log"] = "linear"
    color_range_mode: Literal["auto", "manual"] = "auto"
    color_min: float | None = None
    color_max: float | None = None
    scalogram_color_range_mode: Literal["auto", "manual"] | None = None
    scalogram_color_min: float | None = None
    scalogram_color_max: float | None = None
    spectrogram_color_range_mode: Literal["auto", "manual"] | None = None
    spectrogram_color_min: float | None = None
    spectrogram_color_max: float | None = None
    filter_enabled: bool = False
    filter_type: FilterType | None = None
    low_cut_hz: float | None = None
    high_cut_hz: float | None = None
    filter_order: int = 4


@dataclass(frozen=True)
class DisplayParameters:
    active_signal_view: Literal["raw", "bbi", "amplitude"] = "raw"
    freq_axis_mode: Literal["linear", "log"] = "linear"
    color_range_mode: Literal["auto", "manual"] = "auto"
    color_min: float | None = None
    color_max: float | None = None
    scalogram_color_range_mode: Literal["auto", "manual"] | None = None
    scalogram_color_min: float | None = None
    scalogram_color_max: float | None = None
    spectrogram_color_range_mode: Literal["auto", "manual"] | None = None
    spectrogram_color_min: float | None = None
    spectrogram_color_max: float | None = None
    fit_signal_y: bool = True


def _channel_sfreq(metadata: EDFMetadata, channel_name: str | None) -> float:
    if channel_name is not None:
        try:
            return float(metadata.sfreq_by_channel[channel_name])
        except KeyError as exc:
            raise ParameterValidationError(f"Unknown channel: {channel_name}") from exc
    return min(float(v) for v in metadata.sfreq_by_channel.values())


def validate_display_parameters(display: DisplayParameters) -> None:
    if display.active_signal_view not in {"raw", "bbi", "amplitude"}:
        raise ParameterValidationError("active_signal_view must be raw, bbi, or amplitude")
    if display.freq_axis_mode not in {"linear", "log"}:
        raise ParameterValidationError("freq_axis_mode must be linear or log")
    _validate_color_range("color", display.color_range_mode, display.color_min, display.color_max)
    _validate_color_range(
        "scalogram_color",
        display.scalogram_color_range_mode,
        display.scalogram_color_min,
        display.scalogram_color_max,
        allow_none_mode=True,
    )
    _validate_color_range(
        "spectrogram_color",
        display.spectrogram_color_range_mode,
        display.spectrogram_color_min,
        display.spectrogram_color_max,
        allow_none_mode=True,
    )


def validate_analysis_parameters(
    parameters: AnalysisParameters,
    metadata: EDFMetadata,
    channel_name: str | None = None,
) -> None:
    if parameters.window_start_s < 0:
        raise ParameterValidationError("window_start_s must be >= 0")
    if parameters.window_length_s <= 0:
        raise ParameterValidationError("window_length_s must be > 0")
    if parameters.window_start_s + parameters.window_length_s > metadata.duration_s + 1e-9:
        raise ParameterValidationError(
            "Requested window exceeds recording duration: "
            f"{parameters.window_start_s:g} + {parameters.window_length_s:g} > "
            f"{metadata.duration_s:g}"
        )

    original_sfreq = _channel_sfreq(metadata, channel_name)
    analysis_sfreq = original_sfreq
    if parameters.target_sfreq is not None:
        if parameters.target_sfreq <= 0:
            raise ParameterValidationError("target_sfreq must be > 0")
        if parameters.target_sfreq > original_sfreq + 1e-9:
            raise ParameterValidationError("target_sfreq cannot exceed original sampling rate")
        analysis_sfreq = float(parameters.target_sfreq)

    nyquist = analysis_sfreq / 2.0
    if parameters.scalogram_fmin_hz <= 0:
        raise ParameterValidationError("scalogram_fmin_hz must be > 0")
    if parameters.scalogram_fmax_hz <= parameters.scalogram_fmin_hz:
        raise ParameterValidationError("scalogram_fmax_hz must be greater than scalogram_fmin_hz")
    if parameters.scalogram_fmax_hz >= nyquist:
        raise ParameterValidationError("scalogram_fmax_hz must be below Nyquist")
    if parameters.scalogram_n_scales <= 0:
        raise ParameterValidationError("scalogram_n_scales must be > 0")
    if parameters.spectrogram_fmin_hz < 0:
        raise ParameterValidationError("spectrogram_fmin_hz must be >= 0")
    if parameters.spectrogram_fmax_hz <= parameters.spectrogram_fmin_hz:
        raise ParameterValidationError("spectrogram_fmax_hz must be greater than spectrogram_fmin_hz")
    if parameters.spectrogram_fmax_hz >= nyquist:
        raise ParameterValidationError("spectrogram_fmax_hz must be below Nyquist")
    if parameters.stft_window_s <= 0:
        raise ParameterValidationError("stft_window_s must be > 0")
    if parameters.filter_order <= 0:
        raise ParameterValidationError("filter_order must be > 0")
    if parameters.freq_axis_mode not in {"linear", "log"}:
        raise ParameterValidationError("freq_axis_mode must be linear or log")
    _validate_color_range("color", parameters.color_range_mode, parameters.color_min, parameters.color_max)
    _validate_color_range(
        "scalogram_color",
        parameters.scalogram_color_range_mode,
        parameters.scalogram_color_min,
        parameters.scalogram_color_max,
        allow_none_mode=True,
    )
    _validate_color_range(
        "spectrogram_color",
        parameters.spectrogram_color_range_mode,
        parameters.spectrogram_color_min,
        parameters.spectrogram_color_max,
        allow_none_mode=True,
    )

    if not parameters.filter_enabled:
        return
    if parameters.filter_type not in {"low_pass", "high_pass", "band_pass"}:
        raise ParameterValidationError("filter_type must be low_pass, high_pass, or band_pass")
    low = parameters.low_cut_hz
    high = parameters.high_cut_hz
    if parameters.filter_type == "low_pass":
        if high is None or high <= 0 or high >= nyquist:
            raise ParameterValidationError("low-pass filtering requires 0 < high_cut_hz < Nyquist")
    elif parameters.filter_type == "high_pass":
        if low is None or low <= 0 or low >= nyquist:
            raise ParameterValidationError("high-pass filtering requires 0 < low_cut_hz < Nyquist")
    elif parameters.filter_type == "band_pass":
        if low is None or high is None:
            raise ParameterValidationError("band-pass filtering requires low_cut_hz and high_cut_hz")
        if low <= 0 or high <= 0 or high <= low or high >= nyquist:
            raise ParameterValidationError(
                "band-pass filtering requires 0 < low_cut_hz < high_cut_hz < Nyquist"
            )


def build_analysis_parameters(raw_values: dict, metadata: EDFMetadata) -> AnalysisParameters:
    params = AnalysisParameters(**raw_values)
    validate_analysis_parameters(params, metadata)
    return params


def _validate_color_range(
    name: str,
    mode: Literal["auto", "manual"] | None,
    color_min: float | None,
    color_max: float | None,
    *,
    allow_none_mode: bool = False,
) -> None:
    if mode is None:
        if allow_none_mode:
            return
        raise ParameterValidationError(f"{name}_range_mode must be auto or manual")
    if mode not in {"auto", "manual"}:
        raise ParameterValidationError(f"{name}_range_mode must be auto or manual")
    if mode == "manual":
        if color_min is None or color_max is None:
            raise ParameterValidationError(f"Manual {name} range requires min and max")
        if color_max <= color_min:
            raise ParameterValidationError(f"{name}_max must be greater than {name}_min")


def parameter_record(
    parameters: AnalysisParameters,
    metadata: EDFMetadata,
    channel_name: str | None = None,
) -> dict:
    record = {
        "source_file": metadata.file_path,
        "file_name": metadata.file_name,
        "channel": channel_name,
        "duration_s": metadata.duration_s,
    }
    record.update(asdict(parameters))
    if channel_name is not None:
        record["original_sfreq"] = metadata.sfreq_by_channel.get(channel_name)
        record["n_samples"] = metadata.n_samples_by_channel.get(channel_name)
        record["units"] = metadata.units_by_channel.get(channel_name)
    return record
