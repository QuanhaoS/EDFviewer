"""CLI parser and runner for reproducible EDFViewer analysis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

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
    parser.add_argument("--start", type=float, default=0.0, help="Window start in seconds.")
    parser.add_argument("--length", type=float, default=60.0, help="Window length in seconds.")
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
    parser.add_argument("--filter", choices=["none", "low_pass", "high_pass", "band_pass"], default="none")
    parser.add_argument("--filter-low", type=float, default=None)
    parser.add_argument("--filter-high", type=float, default=None)
    parser.add_argument("--filter-order", type=int, default=4)
    parser.add_argument("-o", "--outdir", default="outputs", help="Output directory.")
    parser.add_argument(
        "--export",
        action="append",
        default=None,
        help="Export type: png, csv, parameters, all. May be repeated or comma-separated.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workflow = EDFViewerWorkflow()
    try:
        metadata = workflow.load_file(args.edf_path)
        channel_name = _resolve_channel(args, metadata.channel_names)
        default_fmax = _default_fmax(metadata, channel_name, args.target_sfreq)
        color_range_mode = "manual" if args.color_min is not None or args.color_max is not None else "auto"
        params = AnalysisParameters(
            target_sfreq=args.target_sfreq,
            window_start_s=args.start,
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
            filter_enabled=args.filter != "none",
            filter_type=None if args.filter == "none" else args.filter,
            low_cut_hz=args.filter_low,
            high_cut_hz=args.filter_high,
            filter_order=args.filter_order,
        )
        result = workflow.compute_window(channel_name, params)
        export = workflow.export_result(
            result,
            {
                "output_dir": args.outdir,
                "types": _flatten_export_args(args.export),
            },
        )
    except EDFViewerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Analysis completed.")
    print(f"EDF: {Path(metadata.file_path)}")
    print(f"Channel: {channel_name}")
    print(f"Window: {params.window_start_s:g}-{params.window_start_s + params.window_length_s:g} s")
    for path in export.png_paths:
        print(f"png: {path}")
    for path in export.csv_paths:
        print(f"csv: {path}")
    for path in export.parameter_record_paths:
        print(f"parameters: {path}")
    return 0


def _resolve_channel(args: argparse.Namespace, channel_names: list[str]) -> str:
    if args.channel is not None:
        if args.channel not in channel_names:
            raise EDFViewerError(f"Channel not found: {args.channel}")
        return args.channel
    if args.channel_index is None:
        raise EDFViewerError("A channel name or channel index is required")
    if args.channel_index < 0 or args.channel_index >= len(channel_names):
        raise EDFViewerError(f"Channel index out of range: {args.channel_index}")
    return channel_names[args.channel_index]


def _flatten_export_args(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    flattened: list[str] = []
    for value in values:
        flattened.extend(part.strip() for part in value.split(",") if part.strip())
    return flattened


def _default_fmax(metadata, channel_name: str, target_sfreq: float | None) -> float:
    source_sfreq = float(metadata.sfreq_by_channel[channel_name])
    analysis_sfreq = float(target_sfreq) if target_sfreq is not None else source_sfreq
    return min(10.0, max(0.2, analysis_sfreq / 2.0 - 0.1))


if __name__ == "__main__":
    sys.exit(main())
