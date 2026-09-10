# Data Layer Tasks

Goal: load EDF metadata and selected channel windows without depending on GUI or CLI code.

Source design: `doc/detailed-design.md` sections 5.1 and 8.1.

## Minimal Tasks

- [ ] Add or update `data/edf_reader.py`.
- [ ] Implement `load_edf_metadata(file_path)`.
- [ ] Implement `load_channel_window(file_path, channel_name, window_start_s, window_length_s)`.
- [ ] Implement `get_valid_time_range(metadata, channel_name)`.
- [ ] Return `EDFMetadata` from metadata loading.
- [ ] Return `ChannelWindow` from window loading.
- [ ] Validate missing file path.
- [ ] Validate unreadable EDF file.
- [ ] Validate empty channel list.
- [ ] Validate invalid channel name.
- [ ] Validate negative window start.
- [ ] Validate non-positive window length.
- [ ] Validate window outside duration.
- [ ] Add tests using `samples/phantom.edf`.
- [ ] Add tests for invalid file path.
- [ ] Add tests for invalid channel.
- [ ] Add tests for invalid window range.

## Acceptance Criteria

- [ ] Metadata loading returns file path, channels, sampling rate, and duration.
- [ ] Window loading returns a one-dimensional signal and matching time vector.
- [ ] The module has no PyQt6 or CLI parser dependency.
