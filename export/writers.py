"""PNG, CSV, and parameter-record exporters."""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from analysis.window_analysis import parameter_to_dict, source_to_dict
from core.errors import ExportError
from core.models import AnalysisResult
from core.parameters import DisplayParameters
from visualization.plot_data import (
    build_scalogram_plot_data,
    build_signal_plot_data,
    build_spectrogram_plot_data,
)


def export_current_png(image_or_widget: Any, output_path: str | Path) -> str:
    """Save an existing image, matplotlib figure, Qt-like widget, path, or result."""

    path = _prepare_output_path(output_path)
    try:
        if hasattr(image_or_widget, "savefig"):
            image_or_widget.savefig(path, dpi=150, bbox_inches="tight")
        elif isinstance(image_or_widget, AnalysisResult):
            display = DisplayParameters(active_signal_view="raw")
            fig = _make_signal_scalogram_figure(image_or_widget, display)
            fig.savefig(path, dpi=150, bbox_inches="tight")
            _close_fig(fig)
        elif hasattr(image_or_widget, "grab"):
            pixmap = image_or_widget.grab()
            ok = pixmap.save(str(path), "PNG")
            if ok is False:
                raise ExportError(f"PNG save returned false for {path}")
        elif hasattr(image_or_widget, "save"):
            ok = image_or_widget.save(str(path))
            if ok is False:
                raise ExportError(f"PNG save returned false for {path}")
        elif isinstance(image_or_widget, (str, Path)):
            shutil.copyfile(image_or_widget, path)
        else:
            raise ExportError("Unsupported PNG export source")
    except ExportError:
        raise
    except Exception as exc:
        raise ExportError(f"Failed to export PNG to {path}: {exc}") from exc
    return str(path)


def export_window_pngs(
    result: AnalysisResult,
    display: DisplayParameters | Any,
    output_dir: str | Path,
) -> list[str]:
    display = _display(display)
    outdir = _prepare_output_dir(output_dir)
    exported: list[str] = []
    for view in ("raw", "bbi", "amplitude"):
        view_display = DisplayParameters(
            active_signal_view=view,
            freq_axis_mode=display.freq_axis_mode,
            color_range_mode=display.color_range_mode,
            color_min=display.color_min,
            color_max=display.color_max,
            fit_signal_y=display.fit_signal_y,
        )
        path = outdir / build_output_filename(result, f"{view}_scalogram", "png")
        fig = _make_signal_scalogram_figure(result, view_display)
        try:
            fig.savefig(path, dpi=150, bbox_inches="tight")
        finally:
            _close_fig(fig)
        exported.append(str(path))

    path = outdir / build_output_filename(result, "spectrogram", "png")
    fig = _make_spectrogram_figure(result, display)
    try:
        fig.savefig(path, dpi=150, bbox_inches="tight")
    finally:
        _close_fig(fig)
    exported.append(str(path))
    return exported


def export_feature_csv(result: AnalysisResult, output_path: str | Path) -> str:
    path = _prepare_output_path(output_path)
    if not result.features:
        raise ExportError("Analysis result has no features to export")
    try:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result.features.keys()))
            writer.writeheader()
            writer.writerow({key: _csv_value(value) for key, value in result.features.items()})
    except Exception as exc:
        raise ExportError(f"Failed to export feature CSV to {path}: {exc}") from exc
    return str(path)


def export_parameter_record(result: AnalysisResult, output_path: str | Path) -> str:
    path = _prepare_output_path(output_path)
    record = {
        "source": source_to_dict(result.source),
        "sampling": {
            "processed_sfreq_hz": result.processed_sfreq,
            "n_samples": int(result.processed_signal.shape[0]),
        },
        "filtering": {
            "filter_enabled": getattr(result.parameters, "filter_enabled", None),
            "filter_type": getattr(result.parameters, "filter_type", None),
            "low_cut_hz": getattr(result.parameters, "low_cut_hz", None),
            "high_cut_hz": getattr(result.parameters, "high_cut_hz", None),
            "filter_order": getattr(result.parameters, "filter_order", None),
        },
        "cwt": {
            "wavelet": getattr(result.parameters, "wavelet", None),
            "scalogram_fmin_hz": getattr(result.parameters, "scalogram_fmin_hz", None),
            "scalogram_fmax_hz": getattr(result.parameters, "scalogram_fmax_hz", None),
            "scalogram_n_scales": getattr(result.parameters, "scalogram_n_scales", None),
        },
        "stft": {
            "stft_window_s": getattr(result.parameters, "stft_window_s", None),
            "spectrogram_fmin_hz": getattr(result.parameters, "spectrogram_fmin_hz", None),
            "spectrogram_fmax_hz": getattr(result.parameters, "spectrogram_fmax_hz", None),
        },
        "display": {
            "freq_axis_mode": getattr(result.parameters, "freq_axis_mode", None),
            "color_range_mode": getattr(result.parameters, "color_range_mode", None),
            "color_min": getattr(result.parameters, "color_min", None),
            "color_max": getattr(result.parameters, "color_max", None),
        },
        "parameters": parameter_to_dict(result.parameters),
    }
    try:
        path.write_text(json.dumps(_json_ready(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        raise ExportError(f"Failed to export parameter record to {path}: {exc}") from exc
    return str(path)


def build_output_filename(
    result: AnalysisResult,
    output_type: str,
    extension: str,
    view_type: str | None = None,
) -> str:
    source = source_to_dict(result.source)
    source_path = str(source.get("file_path") or source.get("source_file") or "edf")
    source_stem = _safe_token(Path(source_path).stem or "edf")
    channel = _safe_token(str(source.get("channel_name") or "channel"))
    start_s = float(source.get("window_start_s") or 0.0)
    length_s = float(source.get("window_length_s") or 0.0)
    if length_s <= 0:
        length_s = len(result.processed_signal) / float(result.processed_sfreq)
    end_s = start_s + length_s
    kind = _safe_token(view_type or output_type)
    ext = extension.lstrip(".")
    return f"{source_stem}_{channel}_{_fmt_time(start_s)}-{_fmt_time(end_s)}_{kind}.{ext}"


def build_output_path(
    result: AnalysisResult,
    output_dir: str | Path,
    output_type: str,
    extension: str,
) -> Path:
    return Path(output_dir) / build_output_filename(result, output_type, extension)


def _make_signal_scalogram_figure(result: AnalysisResult, display: DisplayParameters):
    plt = _plt()
    signal = build_signal_plot_data(result, display)
    scalogram = build_scalogram_plot_data(result, display)
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
    axes[0].plot(signal["x"], signal["y"], linewidth=1.0)
    axes[0].set_xlabel(signal["x_label"])
    axes[0].set_ylabel(signal["y_label"])
    mesh = axes[1].pcolormesh(
        scalogram["x"],
        scalogram["y"],
        scalogram["values"],
        shading="auto",
        vmin=scalogram["color_range"][0],
        vmax=scalogram["color_range"][1],
        cmap="viridis",
    )
    if scalogram["freq_axis_mode"] == "log":
        axes[1].set_yscale("log")
    axes[1].set_xlabel(scalogram["x_label"])
    axes[1].set_ylabel(scalogram["y_label"])
    fig.colorbar(mesh, ax=axes[1], label=scalogram["value_label"])
    return fig


def _make_spectrogram_figure(result: AnalysisResult, display: DisplayParameters):
    plt = _plt()
    spectro = build_spectrogram_plot_data(result, display)
    fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
    mesh = ax.pcolormesh(
        spectro["x"],
        spectro["y"],
        spectro["values"],
        shading="auto",
        vmin=spectro["color_range"][0],
        vmax=spectro["color_range"][1],
        cmap="viridis",
    )
    if spectro["freq_axis_mode"] == "log":
        ax.set_yscale("log")
    ax.set_xlabel(spectro["x_label"])
    ax.set_ylabel(spectro["y_label"])
    fig.colorbar(mesh, ax=ax, label=spectro["value_label"])
    return fig


def _prepare_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise ExportError(f"Failed to create output directory {path}: {exc}") from exc
    if not path.is_dir():
        raise ExportError(f"Output directory is not a directory: {path}")
    return path


def _prepare_output_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    _prepare_output_dir(path.parent if str(path.parent) else Path("."))
    if path.exists() and path.is_dir():
        raise ExportError(f"Output path is a directory: {path}")
    return path


def _plt():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    return plt


def _display(display: DisplayParameters | Any) -> DisplayParameters:
    if isinstance(display, DisplayParameters):
        return display
    if isinstance(display, dict):
        return DisplayParameters(
            **{
                key: value
                for key, value in display.items()
                if key in DisplayParameters.__dataclass_fields__
            }
        )
    return DisplayParameters(
        active_signal_view=str(getattr(display, "active_signal_view", "raw")).lower(),
        freq_axis_mode=str(getattr(display, "freq_axis_mode", "linear")),
        color_range_mode=str(getattr(display, "color_range_mode", "auto")),
        color_min=getattr(display, "color_min", None),
        color_max=getattr(display, "color_max", None),
        fit_signal_y=bool(getattr(display, "fit_signal_y", True)),
    )


def _close_fig(fig) -> None:
    _plt().close(fig)


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    token = token.strip("-._")
    return token or "value"


def _fmt_time(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "p") + "s"


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return json.dumps(value.tolist())
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(_json_ready(value), sort_keys=True)
    return value


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
