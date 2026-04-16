#!/usr/bin/env python3
"""
Unified entrypoint for EDFReader.

- GUI mode: interactive EDF viewer and scalogram tool.
- CLI mode: same arguments and behavior as run_analysis.py.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Allow importing gui_pyqt6.py from the repository root.
# Keep versions/gui_version at highest priority for `analysis`/`data` imports.
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))


def _run_cli(argv):
    parser = argparse.ArgumentParser(
        prog="app.py cli",
        description="Load EDF and plot time-domain and frequency-domain signals.",
    )
    parser.add_argument(
        "edf_path",
        nargs="?",
        default="samples/A.0007.edf",
        help="Path to EDF file (default: samples/A.0007.edf)",
    )
    parser.add_argument(
        "-n",
        "--channels",
        type=int,
        default=5,
        help="Number of channels to plot (default: 5)",
    )
    parser.add_argument(
        "-t",
        "--tmax",
        type=float,
        default=None,
        help="Crop to [0, tmax] seconds (optional)",
    )
    parser.add_argument(
        "--fmax",
        type=float,
        default=None,
        help="Max frequency (Hz) in PSD plot (optional)",
    )
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="Save time-domain and frequency-domain figures to files",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=str,
        default="figures",
        help="Output directory for saved figures (default: figures)",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not display plots (only save when used with --save)",
    )
    args = parser.parse_args(argv)

    edf_path = Path(args.edf_path)
    if not edf_path.exists():
        print(f"Error: file not found: {edf_path}")
        return 1
    from data import SignalDataset

    show = not args.no_show
    if args.save:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        stem = edf_path.stem
        time_path = outdir / f"{stem}_time_domain.png"
        freq_path = outdir / f"{stem}_freq_domain.png"
    else:
        time_path = freq_path = None

    print(f"Loading {edf_path} ...")
    dataset = SignalDataset(str(edf_path))
    dataset.summary()

    if args.tmax is not None:
        dataset.crop(tmin=0, tmax=args.tmax)
        print(f"Cropped to [0, {args.tmax}] s")

    print("\n--- Time domain ---")
    dataset.plot(
        n_channels=args.channels,
        savepath=time_path,
        show=show,
    )
    if time_path:
        print(f"Saved: {time_path}")

    print("\n--- Frequency domain (PSD) ---")
    dataset.plot_psd(
        n_channels=args.channels,
        fmax=args.fmax,
        savepath=freq_path,
        show=show,
    )
    if freq_path:
        print(f"Saved: {freq_path}")
    return 0


def _run_gui():
    try:
        from gui_pyqt6 import run_gui
    except ImportError as exc:
        print("GUI dependencies are missing or incompatible.")
        print(f"Import error: {exc}")
        print("Please install: pip install PyQt6 pyqtgraph")
        return 1

    return run_gui()


def main():
    parser = argparse.ArgumentParser(
        description="EDFReader unified launcher (GUI or CLI)."
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Run mode (default: gui).",
    )
    args, remaining = parser.parse_known_args()

    if args.mode == "gui":
        if remaining:
            print("Warning: extra arguments are ignored in GUI mode:", " ".join(remaining))
        return _run_gui()
    return _run_cli(remaining)


if __name__ == "__main__":
    sys.exit(main())

