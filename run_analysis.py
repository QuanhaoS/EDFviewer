#!/usr/bin/env python3
"""
Command-line script: load EDF, plot time-domain and frequency-domain signals.

Usage:
    python run_analysis.py [edf_path]
    python run_analysis.py samples/A.0007.edf

Default edf_path: samples/A.0007.edf
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from data import SignalDataset


def main():
    parser = argparse.ArgumentParser(
        description="Load EDF and plot time-domain and frequency-domain signals."
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
    args = parser.parse_args()

    edf_path = Path(args.edf_path)
    if not edf_path.exists():
        print(f"Error: file not found: {edf_path}")
        sys.exit(1)

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


if __name__ == "__main__":
    main()
