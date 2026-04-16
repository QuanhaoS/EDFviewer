#!/usr/bin/env python3
"""
Unified entrypoint for EDFReader.

- GUI mode: interactive EDF viewer and scalogram tool.
- CLI mode: same arguments and behavior as run_analysis.py.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

# region agent log
_AGENT_DEBUG_LOG = Path(
    "/scratch/faculty/hkim/quanhao/EDFReader/.cursor/debug-8f17cc.log"
)


def _agent_debug_ndjson(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict | None = None,
) -> None:
    payload = {
        "sessionId": "8f17cc",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        _AGENT_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_AGENT_DEBUG_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _agent_debug_probe_libstdcxx() -> None:
    """Runtime probe for GLIBCXX vs PyQt6 QtCore needs (debug session 8f17cc)."""
    _agent_debug_ndjson(
        "H2",
        "app.py:_agent_debug_probe_libstdcxx",
        "dynamic linker env",
        {
            "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH"),
            "LD_PRELOAD": os.environ.get("LD_PRELOAD"),
        },
    )
    _agent_debug_ndjson(
        "H4",
        "app.py:_agent_debug_probe_libstdcxx",
        "python/conda prefix",
        {
            "sys_prefix": sys.prefix,
            "CONDA_PREFIX": os.environ.get("CONDA_PREFIX"),
        },
    )
    candidates = []
    for rel in ("lib/libstdc++.so.6", "lib64/libstdc++.so.6"):
        p = Path(sys.prefix) / rel
        if p.is_file():
            candidates.append(str(p.resolve()))
    max_suffix = None
    last_samples: list[str] = []
    for libpath in candidates:
        try:
            proc = subprocess.run(
                ["strings", libpath],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode != 0:
                _agent_debug_ndjson(
                    "H1",
                    "app.py:_agent_debug_probe_libstdcxx",
                    "strings non-zero",
                    {"lib": libpath, "returncode": proc.returncode},
                )
                continue
            lines = [
                ln
                for ln in proc.stdout.splitlines()
                if ln.startswith("GLIBCXX_3.4.")
            ]
            last_samples = sorted(set(lines))[-12:]
            suffixes = []
            for ln in lines:
                try:
                    suffixes.append(int(ln.replace("GLIBCXX_3.4.", "", 1)))
                except ValueError:
                    continue
            if suffixes:
                m = max(suffixes)
                if max_suffix is None or m > max_suffix:
                    max_suffix = m
        except (OSError, subprocess.SubprocessError, ValueError) as ex:
            _agent_debug_ndjson(
                "H1",
                "app.py:_agent_debug_probe_libstdcxx",
                "probe exception",
                {"lib": libpath, "error": repr(ex)},
            )
    _agent_debug_ndjson(
        "H1",
        "app.py:_agent_debug_probe_libstdcxx",
        "GLIBCXX summary",
        {
            "libstdcxx_candidates": candidates,
            "max_glibcxx_3_4_suffix": max_suffix,
            "has_glibcxx_3_4_29": max_suffix is not None and max_suffix >= 29,
            "sample_glibcxx_lines": last_samples,
        },
    )


# endregion

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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
    # region agent log
    _agent_debug_probe_libstdcxx()
    # endregion
    try:
        from gui_pyqt6 import run_gui
    except ImportError as exc:
        # region agent log
        _agent_debug_ndjson(
            "H5",
            "app.py:_run_gui",
            "PyQt6 import failed",
            {"error": str(exc)},
        )
        # endregion
        print("GUI dependencies are missing or incompatible.")
        print(f"Import error: {exc}")
        print("Please install: pip install PyQt6 pyqtgraph")
        return 1

    # region agent log
    _agent_debug_ndjson(
        "H5",
        "app.py:_run_gui",
        "PyQt6 import ok",
        {},
    )
    # endregion
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

