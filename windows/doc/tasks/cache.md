# Cache Module Tasks

Goal: cache recently computed analysis windows for faster interactive inspection.

Source design: `doc/detailed-design.md` section 5.8.

## Minimal Tasks

- [ ] Create `core/cache.py`.
- [ ] Implement `AnalysisCache`.
- [ ] Implement `get(key)`.
- [ ] Implement `put(key, result)`.
- [ ] Implement `clear()`.
- [ ] Implement a small least-recently-used eviction policy.
- [ ] Include EDF file path in cache key.
- [ ] Include channel name in cache key.
- [ ] Include window start and window length in cache key.
- [ ] Include target sampling rate in cache key.
- [ ] Include filter settings in cache key.
- [ ] Include CWT wavelet and CWT range in cache key.
- [ ] Include STFT window and spectrogram range in cache key.
- [ ] Exclude display-only settings from compute cache when they do not affect analysis values.
- [ ] Add test for storing and retrieving cached result.
- [ ] Add test for LRU eviction.
- [ ] Add test for clear.
- [ ] Add test confirming changed analysis parameter creates a different key.

## Acceptance Criteria

- [ ] Cache never returns stale analysis after analysis-affecting parameters change.
- [ ] Cache can be tested without GUI.
- [ ] Cache size is configurable or clearly documented.
