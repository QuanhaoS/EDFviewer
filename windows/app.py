#!/usr/bin/env python3
"""
Unified entrypoint for EDFReader.

- GUI mode: interactive EDF viewer and scalogram tool.
- CLI mode: reproducible analysis/export workflow from cli.main.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _run_cli(argv):
    from cli.main import main as cli_main

    return cli_main(argv)


def _run_gui():
    try:
        from gui_pyqt6 import run_gui
    except ImportError as exc:
        print("GUI dependencies are missing or incompatible.")
        print(f"Import error: {exc}")
        print("Please install: pip install PyQt6 pyqtgraph")
        return 1

    return run_gui()


def _build_launcher_parser(add_help: bool = True):
    parser = argparse.ArgumentParser(
        description="EDFReader unified launcher (GUI or CLI).",
        add_help=add_help,
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Run mode (default: gui).",
    )
    return parser


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)

    mode_parser = _build_launcher_parser(add_help=False)
    args, remaining = mode_parser.parse_known_args(argv)

    if args.mode == "cli":
        return _run_cli(remaining)

    parser = _build_launcher_parser()
    args, remaining = parser.parse_known_args(argv)
    if remaining:
        print("Warning: extra arguments are ignored in GUI mode:", " ".join(remaining))
    return _run_gui()


if __name__ == "__main__":
    sys.exit(main())
