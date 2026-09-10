# EDFReader

Physiological Signal Analysis Software

┌──────────────────────────────────────────────┐
│                 User Interface (UI)          │
│                                              │
│  • File loading / Channel selection / Crop   │
│  • Parameter settings (filter, window, etc.) │
│  • Signal view / Spectrum / Time-Frequency   │
│  • Result export                             │
└─────────────────────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│            Visualization Module               │
│                                              │
│  • Multi-channel time-series plots            │
│  • FFT / PSD visualization                   │
│  • Time-frequency maps (STFT / Wavelet)      │
│  • Event annotation (R-peaks / bursts)       │
└─────────────────────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│               Analysis Module                 │
│                                              │
│  • Time-domain analysis (mean, RMS, peaks)   │
│  • Frequency-domain analysis (FFT, PSD)      │
│  • Time-frequency analysis                   │
│  • Feature extraction (HRV, entropy, etc.)   │
└─────────────────────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│           Preprocessing Module                │
│                                              │
│  • Band-pass / High-pass / Low-pass / Notch  │
│  • Baseline removal                           │
│  • Denoising / Normalization                 │
│  • Resampling                                │
└─────────────────────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│                 Data Layer                    │
│                                              │
│  • EDF / CSV / MAT readers                   │
│  • Multi-channel signal management           │
│  • Metadata (sampling rate, channels, events)│
└──────────────────────────────────────────────┘

Module
* Data Layer: data loading and management
* Preprocessing: signal conditioning
* Analysis Module: operates purely on numpy arrays
* Visualization: plotting and interaction
* UI Layer: orchestration and user interaction

Recommended Project Structure
project/
│── data/
│   ├── edf_reader.py
│   └── dataset.py
│── preprocessing/
│   ├── filter.py
│   └── normalize.py
│── analysis/
│   ├── time_domain.py
│   ├── frequency_domain.py
│   └── features.py
│── visualization/
│   ├── plot_time.py
│   ├── plot_psd.py
│   └── plot_tfr.py
│── ui/
│   └── main_window.py
│── main.py