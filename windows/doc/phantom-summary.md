# phantom.edf Signal Summary

File: `samples/phantom.edf`

Sampling rate: `100 Hz`

Duration: `300 s`

Channels:

- `sine`
- `chirp`

Amplitude units in this summary are millivolts (`mV`). `Peak amplitude` means the maximum absolute value in the segment. `Peak-to-peak` means `max - min`.

## Segment Summary

| Channel | Time segment | Frequency summary | Peak amplitude | Peak-to-peak | RMS amplitude |
| --- | --- | --- | --- | --- | --- |
| `sine` | `0-100 s` | `1.5 Hz` | `200.000 mV` | `400.000 mV` | `141.422 mV` |
| `sine` | `100-200 s` | `1.5 Hz` | `100.003 mV` | `200.006 mV` | `70.711 mV` |
| `sine` | `200-300 s` | `3.0 Hz` | `100.003 mV` | `200.006 mV` | `70.711 mV` |
| `chirp` | `0-100 s` | Instantaneous frequency `2-22 Hz`; FFT dominant frequency `2.380 Hz` | `200.001 mV` | `400.000 mV` | `141.422 mV` |
| `chirp` | `100-200 s` | Instantaneous frequency `22-42 Hz`; FFT dominant frequency `41.620 Hz` | `200.000 mV` | `400.000 mV` | `141.421 mV` |
| `chirp` | `200-300 s` | Instantaneous frequency `42-62 Hz`; FFT dominant frequency `42.420 Hz` | `200.000 mV` | `400.000 mV` | `142.210 mV` |

## Channel Details

### `sine`

The `sine` channel is a three-segment sinusoidal test signal:

| Time segment | Designed frequency | Designed peak amplitude |
| --- | --- | --- |
| `0-100 s` | `1.5 Hz` | `200 mV` |
| `100-200 s` | `1.5 Hz` | `100 mV` |
| `200-300 s` | `3.0 Hz` | `100 mV` |

This channel is useful for validating:

- Whether the viewer detects a frequency change from `1.5 Hz` to `3.0 Hz`.
- Whether the viewer shows the amplitude drop from `200 mV` to `100 mV`.
- Whether scalogram and spectrogram displays show a stable horizontal frequency component inside each segment.

### `chirp`

The `chirp` channel is a linear frequency-modulated test signal:

```text
instantaneous frequency f(t) = 2 + 0.2 * t Hz
peak amplitude = 200 mV
sampling rate = 100 Hz
```

Because the sampling rate is `100 Hz`, the Nyquist frequency is `50 Hz`. In the final segment, the theoretical instantaneous frequency reaches `62 Hz`, which is above Nyquist. Frequencies above Nyquist can appear aliased in sampled data, so the final segment should be interpreted carefully when using FFT, STFT, or CWT displays.

| Time segment | Theoretical instantaneous frequency range | Notes |
| --- | --- | --- |
| `0-100 s` | `2-22 Hz` | Within Nyquist |
| `100-200 s` | `22-42 Hz` | Within Nyquist |
| `200-300 s` | `42-62 Hz` | Partly above Nyquist; aliasing may be visible |

This channel is useful for validating:

- Whether scalogram and spectrogram show frequency increasing over time.
- Whether high-frequency behavior near the Nyquist limit is displayed clearly.
- Whether the application communicates frequency-axis and sampling-rate limitations during analysis.

## Verification Method

The summary above was computed by reading `samples/phantom.edf` with MNE, splitting each channel into three fixed windows:

- `0-100 s`
- `100-200 s`
- `200-300 s`

For each channel and segment, the measured values were computed as:

- FFT dominant frequency after subtracting the segment mean.
- Peak amplitude: `max(abs(signal)) * 1000`.
- Peak-to-peak amplitude: `(max(signal) - min(signal)) * 1000`.
- RMS amplitude: `sqrt(mean(signal^2)) * 1000`.
