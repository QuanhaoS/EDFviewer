#!/usr/bin/env python3
"""
run_ppg_window_scalogram.py
---------------------------

Select a single time window of a PPG/PLETH channel and compute:
- raw signal + PPG amplitude (per beat) + PPI (peak-to-peak interval)
Then save 3 PNGs:
1) raw signal + raw scalogram
2) amplitude + amplitude scalogram
3) PPI + PPI scalogram

Usage (example):
    python run_ppg_window_scalogram.py samples/A.0007.edf \\
        -c PLETH --target-hz 16 --tstart 3600 --tlen 60 -o figures/ppg_window
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib

# Force non-interactive backend for headless execution.
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data import SignalDataset
from analysis import cwt_scalogram, compute_ppg_amplitude, compute_ppi


def _ensure_outdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Select a time window of a PPG/PLETH channel, compute amplitude + PPI "
            "and scalograms, then save 3 PNGs: raw+scalogram, amplitude+scalogram, PPI+scalogram."
        )
    )
    parser.add_argument("edf_path", help="Path to EDF file")
    parser.add_argument(
        "-c",
        "--channel",
        default="PLETH",
        help="Channel name (default: PLETH)",
    )
    parser.add_argument(
        "--target-hz",
        type=float,
        default=16.0,
        help="Target sampling rate in Hz for downsampling (default: 16)",
    )
    parser.add_argument(
        "--tstart",
        type=float,
        default=3600.0,
        help="Window start time in seconds (default: 3600). Example: --tstart 7200",
    )
    parser.add_argument(
        "--tlen",
        type=float,
        default=60.0,
        help="Window length in seconds (default: 60). Example: --tlen 30",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=str,
        default="figures/ppg_window",
        help="Output directory for PNGs (default: figures/ppg_window)",
    )
    args = parser.parse_args()

    edf_path = Path(args.edf_path)
    if not edf_path.exists():
        print(f"Error: EDF file not found: {edf_path}")
        sys.exit(1)

    outdir = _ensure_outdir(Path(args.outdir))

    print(f"Loading {edf_path} ...")
    ds = SignalDataset(str(edf_path))

    if args.channel not in ds.ch_names:
        print(f"Error: channel '{args.channel}' not found.")
        print("Available channels:", ds.ch_names)
        sys.exit(1)

    ds.select_channels([args.channel])
    print(f"Selected channel: {args.channel}, sfreq: {ds.sfreq} Hz")

    if ds.sfreq <= args.target_hz:
        print(
            f"Warning: current sfreq {ds.sfreq} Hz <= target {args.target_hz} Hz. "
            "Skip downsampling."
        )
    else:
        ds.downsample(args.target_hz)
        print(f"Downsampled to {ds.sfreq} Hz")

    t_start = float(args.tstart)
    t_end = t_start + float(args.tlen)

    ds.crop(tmin=t_start, tmax=t_end)
    sig = ds.data[0]
    times = ds.times

    if sig.size < 10:
        print("Error: window too short after cropping.")
        sys.exit(1)

    print(
        f"Window: {t_start:.2f}–{t_end:.2f} s, "
        f"samples: {sig.size}, sfreq: {ds.sfreq} Hz"
    )

    # ---- Amplitude and PPI ----
    amp_t, amp_y = compute_ppg_amplitude(sig, times=times, sfreq=ds.sfreq)
    peak_times, ppi = compute_ppi(sig, times=times, sfreq=ds.sfreq)

    # PPI is defined between consecutive peaks; we align it to peak_times[1:] (end of interval)
    ppi_t = peak_times[1:] if peak_times.size > 1 else np.array([])

    # Build amplitude and PPI time series on the original sample grid (so CWT uses ds.sfreq)
    # Amplitude series (sample-aligned): interpolate beat-level amplitude to each sample time.
    if amp_t.size > 1:
        amp_series = np.interp(times, amp_t, amp_y, left=amp_y[0], right=amp_y[-1])
    else:
        amp_series = np.zeros_like(times, dtype=float)

    # PPI series: interpolate interval values to each sample time.
    if ppi_t.size > 1:
        ppi_series = np.interp(times, ppi_t, ppi, left=ppi[0], right=ppi[-1])
    else:
        ppi_series = np.zeros_like(times, dtype=float)

    # ---- Helper: compute scalogram (no saving here) ----
    def compute_scalogram(series_1d, sfreq, fmin, fmax=None, n_scales=64):
        if series_1d.size < 10:
            return None, None, None
        fmax_local = min(fmax, sfreq / 2 - 0.1) if fmax is not None else min(8.0, sfreq / 2 - 0.1)
        times_s, freqs, coefs_mag = cwt_scalogram(
            series_1d[np.newaxis, :],
            sfreq,
            fmin=fmin,
            fmax=fmax_local,
            n_scales=n_scales,
            axis=1,
        )
        return times_s, freqs, coefs_mag[0]

    # ---- Compute scalograms ----
    raw_times_s, raw_freqs, raw_coefs = compute_scalogram(sig, ds.sfreq, fmin=0.1, fmax=args.target_hz)
    amp_times_s, amp_freqs, amp_coefs = compute_scalogram(amp_series, ds.sfreq, fmin=0.01, fmax=args.target_hz)
    ppi_times_s, ppi_freqs, ppi_coefs = compute_scalogram(ppi_series, ds.sfreq, fmin=0.01, fmax=args.target_hz)

    # ---- Save 3 PNGs (each with raw/amplitude/PPI + its scalogram) ----
    stem = edf_path.stem
    time_tag = f"{t_start:.2f}-{t_end:.2f}s"

    # 1) Raw + raw scalogram
    fig1, axes1 = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[1, 1.2])
    axes1[0].plot(times, sig, linewidth=0.6)
    axes1[0].set_ylabel(args.channel)
    axes1[0].set_title("Raw signal")
    axes1[0].set_xlim(times[0], times[-1])
    axes1[0].grid(True, alpha=0.3)

    pcm1 = axes1[1].pcolormesh(
        raw_times_s,
        raw_freqs,
        raw_coefs,
        shading="auto",
        cmap="viridis",
    )
    fig1.colorbar(pcm1, ax=axes1[1], label="|CWT|")
    axes1[1].set_ylabel("Frequency (Hz)")
    axes1[1].set_xlabel("Time (s)")
    axes1[1].set_title("Raw scalogram")
    axes1[1].set_yscale("log")
    axes1[1].set_xlim(times[0] - times[0], times[-1] - times[0])  # keep consistent with cwt_scalogram time axis
    fig1.suptitle(f"{stem} {args.channel} {time_tag}")
    fig1.tight_layout()
    out1 = outdir / f"{stem}_{args.channel}_{time_tag}_raw_plus_scalogram.png"
    fig1.savefig(out1, dpi=150, bbox_inches="tight")
    plt.close(fig1)
    print(f"Saved: {out1}")

    # 2) Amplitude + amplitude scalogram (top shows per-cycle step if available)
    fig2, axes2 = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[1, 1.2])
    if amp_t.size > 0:
        step_t = np.concatenate([[times[0]], amp_t])
        step_y = np.concatenate([[amp_y[0]], amp_y])
        axes2[0].step(step_t, step_y, where="post", color="C1", linewidth=1.2)
    else:
        axes2[0].plot(times, amp_series, linewidth=0.6, color="C1")
    axes2[0].set_ylabel("Amplitude")
    axes2[0].set_title("PPG amplitude (per cycle)")
    axes2[0].set_xlim(times[0], times[-1])
    axes2[0].grid(True, alpha=0.3)

    pcm2 = axes2[1].pcolormesh(
        amp_times_s,
        amp_freqs,
        amp_coefs,
        shading="auto",
        cmap="viridis",
    )
    fig2.colorbar(pcm2, ax=axes2[1], label="|CWT|")
    axes2[1].set_ylabel("Frequency (Hz)")
    axes2[1].set_xlabel("Time (s)")
    axes2[1].set_title("Amplitude scalogram")
    axes2[1].set_yscale("log")
    axes2[1].set_xlim(times[0] - times[0], times[-1] - times[0])
    fig2.suptitle(f"{stem} {args.channel} {time_tag}")
    fig2.tight_layout()
    out2 = outdir / f"{stem}_{args.channel}_{time_tag}_amplitude_plus_scalogram.png"
    fig2.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"Saved: {out2}")

    # 3) PPI + PPI scalogram (top shows per-interval step if available)
    fig3, axes3 = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[1, 1.2])
    if ppi_t.size > 0:
        step_t_ppi = np.concatenate([[times[0]], ppi_t])
        step_y_ppi = np.concatenate([[ppi[0]], ppi]) if ppi.size > 0 else ppi
        axes3[0].step(step_t_ppi, step_y_ppi, where="post", color="C2", linewidth=1.2)
    else:
        axes3[0].plot(times, ppi_series, linewidth=0.6, color="C2")
    axes3[0].set_ylabel("PPI (s)")
    axes3[0].set_title("Peak-to-peak interval")
    axes3[0].set_xlim(times[0], times[-1])
    axes3[0].grid(True, alpha=0.3)

    pcm3 = axes3[1].pcolormesh(
        ppi_times_s,
        ppi_freqs,
        ppi_coefs,
        shading="auto",
        cmap="viridis",
    )
    fig3.colorbar(pcm3, ax=axes3[1], label="|CWT|")
    axes3[1].set_ylabel("Frequency (Hz)")
    axes3[1].set_xlabel("Time (s)")
    axes3[1].set_title("PPI scalogram")
    axes3[1].set_yscale("log")
    axes3[1].set_xlim(times[0] - times[0], times[-1] - times[0])
    fig3.suptitle(f"{stem} {args.channel} {time_tag}")
    fig3.tight_layout()
    out3 = outdir / f"{stem}_{args.channel}_{time_tag}_ppi_plus_scalogram.png"
    fig3.savefig(out3, dpi=150, bbox_inches="tight")
    plt.close(fig3)
    print(f"Saved: {out3}")

    print("Done.")


if __name__ == "__main__":
    main()
