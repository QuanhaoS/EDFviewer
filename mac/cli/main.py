"""CLI parser and runner for reproducible EDFViewer analysis."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.errors import EDFViewerError
from core.parameters import AnalysisParameters
from core.workflow import EDFViewerWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edfviewer",
        description="Run EDFViewer analysis without launching the GUI.",
    )
    parser.add_argument("edf_path", help="Path to an EDF file.")
    channel = parser.add_mutually_exclusive_group(required=True)
    channel.add_argument("--channel", help="Channel name to analyze.")
    channel.add_argument("--channel-index", type=int, help="Zero-based channel index.")
    channel.add_argument(
        "--channels",
        help="Comma-separated channel names to analyze in one run.",
    )
    channel.add_argument(
        "--all-channels",
        action="store_true",
        help="Analyze every channel in the EDF file.",
    )
    parser.add_argument("--start", type=float, default=0.0, help="Window start in seconds.")
    parser.add_argument("--length", type=float, default=60.0, help="Window length in seconds.")
    parser.add_argument(
        "--batch-windows",
        action="store_true",
        help="Analyze repeated windows from --start to the end of the recording.",
    )
    parser.add_argument(
        "--end",
        type=float,
        default=None,
        help="Optional batch stop time in seconds (default: recording end).",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=None,
        help="Step between batch window starts in seconds (default: --length).",
    )
    parser.add_argument("--target-sfreq", type=float, default=None, help="Optional target sampling rate.")
    parser.add_argument("--wavelet", default="cmor1.5-1.0", help="PyWavelets CWT wavelet.")
    parser.add_argument("--cwt-fmin", type=float, default=0.1, help="CWT minimum frequency.")
    parser.add_argument("--cwt-fmax", type=float, default=None, help="CWT maximum frequency.")
    parser.add_argument("--cwt-scales", type=int, default=64, help="Number of CWT scales.")
    parser.add_argument(
        "--stft-window",
        "--stft-window-length",
        dest="stft_window",
        type=float,
        default=5.0,
        help="STFT window length in seconds.",
    )
    parser.add_argument("--spectrogram-fmin", type=float, default=0.0, help="Spectrogram minimum frequency.")
    parser.add_argument("--spectrogram-fmax", type=float, default=None, help="Spectrogram maximum frequency.")
    parser.add_argument("--freq-axis", choices=["linear", "log"], default="linear")
    parser.add_argument("--color-min", type=float, default=None)
    parser.add_argument("--color-max", type=float, default=None)
    parser.add_argument("--scalogram-color-min", type=float, default=None)
    parser.add_argument("--scalogram-color-max", type=float, default=None)
    parser.add_argument("--spectrogram-color-min", type=float, default=None)
    parser.add_argument("--spectrogram-color-max", type=float, default=None)
    parser.add_argument(
        "--filter",
        choices=["none", "low_pass", "high_pass", "band_pass", "band_stop"],
        default="none",
    )
    parser.add_argument("--filter-low", type=float, default=None)
    parser.add_argument("--filter-high", type=float, default=None)
    parser.add_argument("--filter-order", type=int, default=4)
    parser.add_argument(
        "--filter-family",
        choices=["butter", "cheby1", "cheby2", "ellip", "bessel"],
        default="butter",
    )
    parser.add_argument("--filter-ripple-db", type=float, default=1.0)
    parser.add_argument("--filter-stop-atten-db", type=float, default=40.0)
    parser.add_argument("-o", "--outdir", default="outputs", help="Output directory.")
    parser.add_argument(
        "--export",
        action="append",
        default=None,
        help="Export type: png, csv, parameters, all. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--summary-csv",
        default="batch_features.csv",
        help="Batch feature summary filename when multiple analyses export CSV.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workflow = EDFViewerWorkflow()
    try:
        metadata = workflow.load_file(args.edf_path)
        channel_names = _resolve_channels(args, metadata.channel_names)
        starts = _window_starts(args, metadata.duration_s)
        export_types = _flatten_export_args(args.export)
        all_png_paths: list[str] = []
        all_csv_paths: list[str] = []
        all_parameter_paths: list[str] = []
        feature_rows: list[dict[str, Any]] = []
        analyses: list[tuple[str, AnalysisParameters]] = []

        for channel_name in channel_names:
            for start_s in starts:
                params = _build_parameters(args, metadata, channel_name, start_s)
                result = workflow.compute_window(channel_name, params)
                export = workflow.export_result(
                    result,
                    {
                        "output_dir": args.outdir,
                        "types": export_types,
                    },
                )
                analyses.append((channel_name, params))
                feature_rows.append(dict(result.features))
                all_png_paths.extend(export.png_paths)
                all_csv_paths.extend(export.csv_paths)
                all_parameter_paths.extend(export.parameter_record_paths)

        summary_path = None
        if len(feature_rows) > 1 and "csv" in _requested_export_types(export_types):
            summary_path = _write_batch_feature_csv(
                feature_rows,
                Path(args.outdir) / args.summary_csv,
            )
            all_csv_paths.append(summary_path)
    except EDFViewerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Analysis completed.")
    print(f"EDF: {Path(metadata.file_path)}")
    print(f"Analyses: {len(analyses)}")
    for channel_name, params in analyses:
        print(
            "analysis: "
            f"channel={channel_name} "
            f"window={params.window_start_s:g}-{params.window_start_s + params.window_length_s:g} s"
        )
    for path in all_png_paths:
        print(f"png: {path}")
    for path in all_csv_paths:
        print(f"csv: {path}")
    for path in all_parameter_paths:
        print(f"parameters: {path}")
    return 0


def _resolve_channels(args: argparse.Namespace, channel_names: list[str]) -> list[str]:
    if args.all_channels:
        return list(channel_names)
    if args.channels is not None:
        requested = [part.strip() for part in args.channels.split(",") if part.strip()]
        if not requested:
            raise EDFViewerError("--channels requires at least one channel name")
        missing = [channel for channel in requested if channel not in channel_names]
        if missing:
            raise EDFViewerError(f"Channel not found: {', '.join(missing)}")
        return requested
    if args.channel is not None:
        if args.channel not in channel_names:
            raise EDFViewerError(f"Channel not found: {args.channel}")
        return [args.channel]
    if args.channel_index is None:
        raise EDFViewerError("A channel name or channel index is required")
    if args.channel_index < 0 or args.channel_index >= len(channel_names):
        raise EDFViewerError(f"Channel index out of range: {args.channel_index}")
    return [channel_names[args.channel_index]]


def _window_starts(args: argparse.Namespace, duration_s: float) -> list[float]:
    if args.length <= 0:
        raise EDFViewerError("--length must be > 0")
    if args.start < 0:
        raise EDFViewerError("--start must be >= 0")
    if not args.batch_windows:
        return [float(args.start)]

    step = float(args.step) if args.step is not None else float(args.length)
    if step <= 0:
        raise EDFViewerError("--step must be > 0")
    end_s = float(args.end) if args.end is not None else float(duration_s)
    if end_s > float(duration_s) + 1e-9:
        raise EDFViewerError("--end cannot exceed recording duration")
    if end_s <= args.start:
        raise EDFViewerError("--end must be greater than --start")
    last_start = end_s - float(args.length)
    if args.start > last_start + 1e-9:
        raise EDFViewerError("No full batch windows fit in the requested range")
    starts: list[float] = []
    current = float(args.start)
    while current <= last_start + 1e-9:
        starts.append(round(current, 9))
        current += step
    return starts


def _build_parameters(
    args: argparse.Namespace,
    metadata,
    channel_name: str,
    start_s: float,
) -> AnalysisParameters:
    default_fmax = _default_fmax(metadata, channel_name, args.target_sfreq)
    color_range_mode = "manual" if args.color_min is not None or args.color_max is not None else "auto"
    scalogram_color_range_mode = (
        "manual"
        if args.scalogram_color_min is not None or args.scalogram_color_max is not None
        else None
    )
    spectrogram_color_range_mode = (
        "manual"
        if args.spectrogram_color_min is not None or args.spectrogram_color_max is not None
        else None
    )
    return AnalysisParameters(
        target_sfreq=args.target_sfreq,
        window_start_s=float(start_s),
        window_length_s=args.length,
        wavelet=args.wavelet,
        scalogram_fmin_hz=args.cwt_fmin,
        scalogram_fmax_hz=args.cwt_fmax if args.cwt_fmax is not None else default_fmax,
        scalogram_n_scales=args.cwt_scales,
        stft_window_s=args.stft_window,
        spectrogram_fmin_hz=args.spectrogram_fmin,
        spectrogram_fmax_hz=(
            args.spectrogram_fmax if args.spectrogram_fmax is not None else default_fmax
        ),
        freq_axis_mode=args.freq_axis,
        color_range_mode=color_range_mode,
        color_min=args.color_min,
        color_max=args.color_max,
        scalogram_color_range_mode=scalogram_color_range_mode,
        scalogram_color_min=args.scalogram_color_min,
        scalogram_color_max=args.scalogram_color_max,
        spectrogram_color_range_mode=spectrogram_color_range_mode,
        spectrogram_color_min=args.spectrogram_color_min,
        spectrogram_color_max=args.spectrogram_color_max,
        filter_enabled=args.filter != "none",
        filter_type=None if args.filter == "none" else args.filter,
        low_cut_hz=args.filter_low,
        high_cut_hz=args.filter_high,
        filter_order=args.filter_order,
        filter_family=args.filter_family,
        filter_ripple_db=args.filter_ripple_db,
        filter_stop_atten_db=args.filter_stop_atten_db,
    )


def _flatten_export_args(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    flattened: list[str] = []
    for value in values:
        flattened.extend(part.strip() for part in value.split(",") if part.strip())
    return flattened


def _requested_export_types(values: list[str] | None) -> set[str]:
    if values is None:
        return {"png", "csv", "parameters"}
    requested: set[str] = set()
    for item in values:
        kind = str(item).strip().lower()
        if kind == "all":
            requested.update({"png", "csv", "parameters"})
        elif kind in {"png", "csv", "parameters"}:
            requested.add(kind)
        elif kind in {"json", "params", "parameter"}:
            requested.add("parameters")
    return requested


def _write_batch_feature_csv(rows: list[dict[str, Any]], output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})
    return str(output_path)


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, sort_keys=True)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _default_fmax(metadata, channel_name: str, target_sfreq: float | None) -> float:
    source_sfreq = float(metadata.sfreq_by_channel[channel_name])
    analysis_sfreq = float(target_sfreq) if target_sfreq is not None else source_sfreq
    return min(10.0, max(0.2, analysis_sfreq / 2.0 - 0.1))


if __name__ == "__main__":
    sys.exit(main())
