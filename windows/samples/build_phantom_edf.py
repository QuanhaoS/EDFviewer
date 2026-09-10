#!/usr/bin/env python3
"""Build samples/phantom.edf with deterministic synthetic test channels."""

from __future__ import annotations

import argparse
from pathlib import Path

import mne
import numpy as np

DEFAULT_OUT = Path(__file__).resolve().parent / "phantom.edf"


def linear_chirp(
    t: np.ndarray,
    f0: float,
    k: float,
    amplitude: float = 0.2,
) -> np.ndarray:
    """Linear chirp: instantaneous frequency f(t) = f0 + k*t (Hz)."""
    phase = 2.0 * np.pi * (f0 * t + 0.5 * k * t**2)
    return amplitude * np.cos(phase)


def piecewise_sine(t: np.ndarray) -> np.ndarray:
    """Synthetic sine used by the test suite.

    The first 100 s segment is 1.5 Hz at 200 mV peak, the second is 1.5 Hz
    at 100 mV peak, and the last is 3 Hz at 100 mV peak.
    """
    signal = np.empty_like(t, dtype=float)
    first = t < 100.0
    second = (t >= 100.0) & (t < 200.0)
    third = t >= 200.0
    signal[first] = 0.2 * np.sin(2.0 * np.pi * 1.5 * t[first])
    signal[second] = 0.1 * np.sin(2.0 * np.pi * 1.5 * t[second])
    signal[third] = 0.1 * np.sin(2.0 * np.pi * 3.0 * t[third])
    return signal


def build_phantom_edf(
    out_path: Path,
    f0: float = 2.0,
    k: float = 0.2,
    amplitude: float = 0.2,
    sfreq: float = 100.0,
    duration_s: float = 300.0,
) -> None:
    out_path = Path(out_path)
    n_samples = int(round(sfreq * duration_s))
    t = np.arange(n_samples, dtype=float) / sfreq

    sine = piecewise_sine(t)
    chirp = linear_chirp(t, f0=f0, k=k, amplitude=amplitude)
    data = np.vstack([sine, chirp])

    info = mne.create_info(
        ch_names=["sine", "chirp"],
        sfreq=sfreq,
        ch_types=["eeg", "eeg"],
    )
    raw = mne.io.RawArray(data, info, verbose=False)
    raw.export(str(out_path), fmt="edf", overwrite=True)
    print(f"Wrote {out_path}")
    print(f"  channels : {raw.ch_names}")
    print(f"  sfreq    : {sfreq} Hz")
    print(f"  duration : {duration_s} s")
    print(f"  chirp    : f0={f0} Hz, k={k} Hz/s, A={amplitude}")


def main():
    parser = argparse.ArgumentParser(description="Build samples/phantom.edf")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output EDF path (default: {DEFAULT_OUT})",
    )
    parser.add_argument("--f0", type=float, default=2.0, help="Chirp start frequency Hz")
    parser.add_argument("--k", type=float, default=0.2, help="Chirp rate Hz/s")
    parser.add_argument("--amplitude", type=float, default=0.2, help="Peak amplitude")
    parser.add_argument("--sfreq", type=float, default=100.0, help="Sampling rate Hz")
    parser.add_argument("--duration", type=float, default=300.0, help="Duration seconds")
    args = parser.parse_args()
    build_phantom_edf(
        out_path=args.output,
        f0=args.f0,
        k=args.k,
        amplitude=args.amplitude,
        sfreq=args.sfreq,
        duration_s=args.duration,
    )


if __name__ == "__main__":
    main()
