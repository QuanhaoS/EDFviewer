"""Shared EDFViewer workflow used by GUI and CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
if not hasattr(np, "trapz") and hasattr(np, "trapezoid"):
    np.trapz = np.trapezoid

from analysis.window_analysis import analyze_window
from core.cache import AnalysisCache, build_cache_key
from core.errors import EDFViewerError, ExportError, ParameterValidationError
from core.models import AnalysisResult, ChannelWindow, EDFMetadata, ExportResult
from core.parameters import (
    AnalysisParameters,
    DisplayParameters,
    validate_analysis_parameters,
    validate_display_parameters,
)
from data.edf_reader import get_valid_time_range, load_channel_window, load_edf_metadata
from export.writers import (
    build_output_path,
    export_feature_csv,
    export_parameter_record,
    export_window_pngs,
)
from preprocessing.pipeline import preprocess_signal


class EDFViewerWorkflow:
    """Controller for file loading, window computation, caching, and export."""

    def __init__(self, cache_size: int = 2):
        self.metadata: EDFMetadata | None = None
        self.cache = AnalysisCache(max_size=cache_size)

    def load_file(self, file_path: str) -> EDFMetadata:
        metadata = load_edf_metadata(file_path)
        self.metadata = metadata
        self.cache.clear()
        return metadata

    def get_channel_range(self, channel_name: str) -> tuple[float, float]:
        metadata = self._require_metadata()
        return get_valid_time_range(metadata, channel_name)

    def compute_window(
        self,
        channel_name: str,
        parameters: AnalysisParameters,
    ) -> AnalysisResult:
        metadata = self._require_metadata()
        if channel_name not in metadata.channel_names:
            raise ParameterValidationError(f"Channel not found: {channel_name}")
        validate_analysis_parameters(parameters, metadata, channel_name=channel_name)
        key = build_cache_key(metadata.file_path, channel_name, parameters)
        cached = self.cache.get(key)
        if cached is not None:
            cached.from_cache = True
            return cached

        window = _load_window_with_context(metadata, channel_name, parameters)
        processed_signal, processed_sfreq, preprocessing_metadata = preprocess_signal(window, parameters)
        result = analyze_window(
            window,
            processed_signal,
            processed_sfreq,
            parameters,
            preprocessing_metadata=preprocessing_metadata,
        )
        result.from_cache = False
        self.cache.put(key, result)
        return result

    def export_result(
        self,
        result: AnalysisResult,
        export_request: dict[str, Any],
    ) -> ExportResult:
        output_dir = Path(export_request.get("output_dir", "."))
        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            raise ExportError(f"Output path is not a directory: {output_dir}")

        display = export_request.get("display") or DisplayParameters(
            active_signal_view=str(export_request.get("active_signal_view", "raw")),
            freq_axis_mode=getattr(result.parameters, "freq_axis_mode", "linear"),
            color_range_mode=getattr(result.parameters, "color_range_mode", "auto"),
            color_min=getattr(result.parameters, "color_min", None),
            color_max=getattr(result.parameters, "color_max", None),
            scalogram_color_range_mode=getattr(result.parameters, "scalogram_color_range_mode", None),
            scalogram_color_min=getattr(result.parameters, "scalogram_color_min", None),
            scalogram_color_max=getattr(result.parameters, "scalogram_color_max", None),
            spectrogram_color_range_mode=getattr(result.parameters, "spectrogram_color_range_mode", None),
            spectrogram_color_min=getattr(result.parameters, "spectrogram_color_min", None),
            spectrogram_color_max=getattr(result.parameters, "spectrogram_color_max", None),
        )
        validate_display_parameters(display)

        requested = _normalize_export_types(export_request.get("types"))
        png_paths: list[str] = []
        csv_paths: list[str] = []
        parameter_paths: list[str] = []
        if "png" in requested:
            png_paths = export_window_pngs(result, display, output_dir)
        if "csv" in requested:
            path = build_output_path(result, output_dir, "features", "csv")
            csv_paths = [export_feature_csv(result, path)]
        if "parameters" in requested:
            path = build_output_path(result, output_dir, "parameters", "json")
            parameter_paths = [export_parameter_record(result, path)]
        return ExportResult(
            png_paths=png_paths,
            csv_paths=csv_paths,
            parameter_record_paths=parameter_paths,
            messages=[f"Exported {len(png_paths) + len(csv_paths) + len(parameter_paths)} files"],
        )

    def _require_metadata(self) -> EDFMetadata:
        if self.metadata is None:
            raise EDFViewerError("No EDF file is loaded")
        return self.metadata


def _normalize_export_types(value: Any) -> set[str]:
    if value is None:
        return {"png", "csv", "parameters"}
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = value
    normalized: set[str] = set()
    for item in items:
        kind = str(item).strip().lower()
        if not kind:
            continue
        if kind == "all":
            normalized.update({"png", "csv", "parameters"})
        elif kind in {"png", "csv", "parameters"}:
            normalized.add(kind)
        elif kind in {"json", "params", "parameter"}:
            normalized.add("parameters")
        else:
            raise ExportError(f"Unsupported export type: {item}")
    return normalized or {"png", "csv", "parameters"}


def _load_window_with_context(
    metadata: EDFMetadata,
    channel_name: str,
    parameters: AnalysisParameters,
) -> ChannelWindow:
    window_start = float(parameters.window_start_s)
    window_length = float(parameters.window_length_s)
    context_pad = 0.05 * window_length
    context_start = max(0.0, window_start - context_pad)
    context_end = min(float(metadata.duration_s), window_start + window_length + context_pad)
    context_length = context_end - context_start

    context_window = load_channel_window(
        metadata.file_path,
        channel_name,
        context_start,
        context_length,
    )
    context_times = np.asarray(context_window.times_s, dtype=float)
    if context_times.size and abs(float(context_times[0]) - context_start) < 1e-6:
        absolute_times = context_times
    else:
        absolute_times = context_start + context_times

    return ChannelWindow(
        file_path=context_window.file_path,
        channel_name=context_window.channel_name,
        window_start_s=window_start,
        window_length_s=window_length,
        sfreq=context_window.sfreq,
        times_s=absolute_times - window_start,
        signal=context_window.signal,
        units=context_window.units,
        context_start_s=context_start,
        context_length_s=context_length,
    )
