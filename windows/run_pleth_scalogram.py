#!/usr/bin/env python3
"""
Command-line: load EDF, keep PLETH channel, downsample to 16 Hz,
then plot and save one image per time window (raw signal + scalogram).

Time window length is controlled by -w/--window (default: 1 hour).
Each window is stored as one PNG.

Usage:
    python run_pleth_scalogram.py <edf_path>
    python run_pleth_scalogram.py samples/A.0007.edf --window-min 1.2 --segment 60   # 1.2 min per unit, show 60th
    python run_pleth_scalogram.py samples/A.0007.edf -w 2          # 2-hour windows
    python run_pleth_scalogram.py samples/A.0007.edf -o figures/pleth
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from data import SignalDataset
from analysis import cwt_scalogram, compute_ppg_amplitude


def main():
    parser = argparse.ArgumentParser(
        description="PLETH channel: downsample to 16 Hz, plot scalogram per hour."
    )
    parser.add_argument(
        "edf_path",
        help="Path to EDF file",
    )
    parser.add_argument(
        "-c",
        "--channel",
        default="PLETH",
        help="Channel name to use (default: PLETH)",
    )
    parser.add_argument(
        "--target-hz",
        type=float,
        default=16.0,
        help="Target sampling rate in Hz (default: 16)",
    )
    parser.add_argument(
        "-w",
        "--window",
        type=float,
        default=None,
        dest="segment_hours",
        metavar="HOURS",
        help="Time window length in hours (default: 1). Ignored if --window-min is set.",
    )
    parser.add_argument(
        "--window-min",
        type=float,
        default=None,
        metavar="MINUTES",
        help="Time window length in minutes (e.g. 1.2 for 1.2 min). Overrides -w if set.",
    )
    parser.add_argument(
        "--segment",
        type=int,
        default=None,
        metavar="N",
        help="Only plot/save the N-th time window (1-based). E.g. 60 for the 60th unit.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save images (by default, each time window is saved as one PNG)",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        default="figures/pleth_scalogram",
        help="Output directory for PNG files (default: figures/pleth_scalogram)",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not display plots (only save files, no window)",
    )
    parser.add_argument(
        "--fmin",
        type=float,
        default=0.5,
        help="Scalogram minimum frequency Hz (default: 0.5)",
    )
    parser.add_argument(
        "--fmax",
        type=float,
        default=8.0,
        help="Scalogram maximum frequency Hz (default: 8, Nyquist for 16 Hz is 8)",
    )
    args = parser.parse_args()

    if args.window_min is not None:
        args.segment_hours = args.window_min / 60.0
    elif args.segment_hours is None:
        args.segment_hours = 1.0

    edf_path = Path(args.edf_path)
    if not edf_path.exists():
        print(f"Error: file not found: {edf_path}")
        sys.exit(1)

    print(f"Loading {edf_path} ...")
    dataset = SignalDataset(str(edf_path))

    if args.channel not in dataset.ch_names:
        print(f"Error: channel '{args.channel}' not found. Available: {dataset.ch_names}")
        sys.exit(1)

    dataset.select_channels([args.channel])
    print(f"Selected channel: {args.channel}, sfreq before: {dataset.sfreq} Hz")

    if dataset.sfreq <= args.target_hz:
        print(f"Error: current sfreq {dataset.sfreq} Hz <= target {args.target_hz} Hz. No downsampling.")
        sys.exit(1)

    dataset.downsample(args.target_hz)
    print(f"Downsampled to {dataset.sfreq} Hz, samples: {dataset.data.shape[1]}")

    segment_sec = args.segment_hours * 3600.0
    segment_samples = int(segment_sec * dataset.sfreq)
    n_samples = dataset.data.shape[1]
    n_segments = max(1, (n_samples + segment_samples - 1) // segment_samples)

    if args.segment is not None:
        if args.segment < 1 or args.segment > n_segments:
            print(f"Error: --segment {args.segment} is out of range (1 to {n_segments}).")
            sys.exit(1)
        segment_indices = [args.segment - 1]
        print(f"Only processing unit {args.segment} of {n_segments}.")
    else:
        segment_indices = list(range(n_segments))

    save = not args.no_save
    if save:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        stem = edf_path.stem
        print(f"Saving one PNG per {args.segment_hours}h window to: {outdir}/")

    show = not args.no_show

    for i in segment_indices:
        start = i * segment_samples
        end = min(start + segment_samples, n_samples)
        seg = dataset.data[:, start:end]
        n_seg = seg.shape[1]
        t_start_h = dataset.times[start] / 3600.0
        t_end_h = dataset.times[min(end - 1, len(dataset.times) - 1)] / 3600.0

        if n_seg < 100:
            print(f"Segment {i + 1}: too short ({n_seg} samples), skip.")
            continue

        print(f"Segment {i + 1}/{n_segments}: hour {t_start_h:.2f}–{t_end_h:.2f} ({n_seg} samples) ...")

        times_s, freqs, coefs_mag = cwt_scalogram(
            seg,
            dataset.sfreq,
            fmin=args.fmin,
            fmax=min(args.fmax, dataset.sfreq / 2 - 0.1),
            n_scales=64,
            axis=1,
        )
        coefs_mag = coefs_mag[0] if coefs_mag.ndim == 3 else coefs_mag

        seg_signal = seg[0]
        times_seg = np.arange(n_seg) / dataset.sfreq

        amp_times, amplitudes = compute_ppg_amplitude(
            seg_signal, times=times_seg, sfreq=dataset.sfreq
        )

        fig, axes = plt.subplots(3, 1, figsize=(12, 9), height_ratios=[1, 0.7, 1.2])
        fig.suptitle(
            f"{args.channel} @ {dataset.sfreq} Hz | "
            f"Segment {i + 1} (hour {t_start_h:.2f}–{t_end_h:.2f})"
        )

        axes[0].plot(times_seg, seg_signal, linewidth=0.5)
        axes[0].set_ylabel(f"{args.channel}")
        axes[0].set_title("Raw signal")
        axes[0].set_xlim(0, times_seg[-1])
        axes[0].grid(True, alpha=0.3)

        if len(amp_times) > 0:
            step_t = np.concatenate([[0], amp_times])
            step_y = np.concatenate([[amplitudes[0]], amplitudes])
            axes[1].step(step_t, step_y, where="post", color="C0", linewidth=1)
        axes[1].set_ylabel(f"{args.channel} amplitude")
        axes[1].set_title("PPG amplitude (per cycle)")
        axes[1].set_xlim(0, times_seg[-1])
        axes[1].grid(True, alpha=0.3)

        pcm = axes[2].pcolormesh(
            times_s,
            freqs,
            coefs_mag,
            shading="auto",
            cmap="viridis",
        )
        fig.colorbar(pcm, ax=axes[2], label="|CWT|")
        axes[2].set_ylabel("Frequency (Hz)")
        axes[2].set_xlabel("Time (s)")
        axes[2].set_title("Scalogram")
        axes[2].set_yscale("log")
        axes[2].set_xlim(0, times_seg[-1])

        plt.tight_layout()

        if save:
            win_str = f"{args.segment_hours:g}hour"
            outpath = outdir / f"{stem}_{args.channel}_{win_str}_{i + 1:03d}.png"
            fig.savefig(outpath, dpi=150, bbox_inches="tight")
            print(f"  Saved: {outpath}")

        if show:
            plt.show()
        else:
            plt.close(fig)

    print("Done.")


if __name__ == "__main__":
    main()
