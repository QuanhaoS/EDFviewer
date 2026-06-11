"""EDF metadata and windowed channel loading."""

from __future__ import annotations

from pathlib import Path

import mne
import numpy as np

from core.errors import DataLoadError
from core.models import ChannelWindow, EDFMetadata


def _read_raw(file_path: str, preload: bool | str = False):
    try:
        return mne.io.read_raw_edf(file_path, preload=preload, verbose=False)
    except Exception as exc:
        raise DataLoadError(f"Could not read EDF file: {file_path}") from exc


def _unit_label(raw, idx: int) -> str | None:
    try:
        unit = raw.info["chs"][idx].get("unit")
    except Exception:
        return None
    if unit == 1072:
        return "V"
    if unit == 1092:
        return "T"
    if unit in (None, 0):
        return None
    return str(unit)


def load_edf_metadata(file_path: str) -> EDFMetadata:
    path = Path(file_path)
    if not path.exists():
        raise DataLoadError(f"EDF file does not exist: {file_path}")
    if not path.is_file():
        raise DataLoadError(f"EDF path is not a file: {file_path}")

    raw = _read_raw(str(path), preload=False)
    channel_names = list(raw.info.get("ch_names", []))
    if not channel_names:
        raise DataLoadError(f"EDF file has no readable channels: {file_path}")

    sfreq_by_channel: dict[str, float] = {}
    n_samples_by_channel: dict[str, int] = {}
    units_by_channel: dict[str, str | None] = {}
    default_sfreq = float(raw.info["sfreq"])
    n_times = int(raw.n_times)
    duration_s = float(n_times) / default_sfreq
    for idx, ch in enumerate(channel_names):
        sfreq_by_channel[ch] = default_sfreq
        n_samples_by_channel[ch] = n_times
        units_by_channel[ch] = _unit_label(raw, idx)

    try:
        raw.close()
    except Exception:
        pass

    try:
        metadata = {
            "meas_date": str(raw.info.get("meas_date")),
            "n_channels": len(channel_names),
        }
    except Exception:
        metadata = {"n_channels": len(channel_names)}

    try:
        return EDFMetadata(
            file_path=str(path),
            file_name=path.name,
            channel_names=channel_names,
            sfreq_by_channel=sfreq_by_channel,
            duration_s=duration_s,
            n_samples_by_channel=n_samples_by_channel,
            units_by_channel=units_by_channel,
            metadata=metadata,
        )
    except ValueError as exc:
        raise DataLoadError(str(exc)) from exc


def get_valid_time_range(metadata: EDFMetadata, channel_name: str) -> tuple[float, float]:
    if channel_name not in metadata.channel_names:
        raise DataLoadError(f"Unknown channel: {channel_name}")
    return 0.0, float(metadata.duration_s)


def load_channel_window(
    file_path: str,
    channel_name: str,
    window_start_s: float,
    window_length_s: float,
) -> ChannelWindow:
    metadata = load_edf_metadata(file_path)
    if channel_name not in metadata.channel_names:
        raise DataLoadError(f"Unknown channel: {channel_name}")
    if window_start_s < 0:
        raise DataLoadError("window_start_s must be >= 0")
    if window_length_s <= 0:
        raise DataLoadError("window_length_s must be > 0")
    if window_start_s + window_length_s > metadata.duration_s + 1e-9:
        raise DataLoadError(
            "Requested window exceeds recording duration: "
            f"{window_start_s:g} + {window_length_s:g} > {metadata.duration_s:g}"
        )

    raw = _read_raw(str(file_path), preload=False)
    try:
        ch_index = raw.ch_names.index(channel_name)
    except ValueError as exc:
        raise DataLoadError(f"Unknown channel: {channel_name}") from exc
    sfreq = float(raw.info["sfreq"])
    start = int(np.floor(window_start_s * sfreq))
    stop = int(np.ceil((window_start_s + window_length_s) * sfreq))
    stop = min(stop, int(raw.n_times))
    if stop <= start:
        raise DataLoadError("Requested window has no samples")
    try:
        data = raw.get_data(picks=[ch_index], start=start, stop=stop)[0]
    except Exception as exc:
        raise DataLoadError(f"Could not load channel window: {channel_name}") from exc
    finally:
        try:
            raw.close()
        except Exception:
            pass

    times = np.arange(data.shape[0], dtype=float) / sfreq
    try:
        return ChannelWindow(
            file_path=str(file_path),
            channel_name=channel_name,
            window_start_s=float(window_start_s),
            window_length_s=float(window_length_s),
            sfreq=sfreq,
            times_s=times,
            signal=data,
            units=metadata.units_by_channel.get(channel_name),
        )
    except ValueError as exc:
        raise DataLoadError(str(exc)) from exc
