# EDFReader

生理信号分析工具：支持 EDF 文件读取、滤波、时域/频域分析与可视化。

---

## 功能概览

- **数据加载**：读取 EDF，封装为 `SignalDataset`，支持通道选择、时间裁剪
- **预处理**：Butterworth 滤波（低通、高通、带通）
- **时域分析**：基本统计、RMS、峰峰值、过零率、Hjorth 参数等
- **频域分析**：Welch PSD、频段功率（delta/theta/alpha/beta/gamma）、主频、谱质心、spectrogram、CWT scalogram
- **可视化**：时域波形、PSD、spectrogram、scalogram，支持保存为图片

---

## 环境要求

- Python ≥ 3.8
- 依赖见 `requirements.txt`

---

## 安装

```bash
cd EDFReader
pip install -r requirements.txt
```

---

## 项目结构

```
EDFReader/
├── data/                 # 数据与数据集
│   ├── edf_viewer.py     # EDF 读取与简单绘图
│   └── signal_dataset.py # SignalDataset（加载、滤波、分析、绘图）
├── preprocessing/       # 预处理
│   └── filter.py        # low_pass, high_pass, band_pass
├── analysis/             # 分析
│   ├── time_domain.py    # 时域特征
│   └── freq_domain.py    # 频域、PSD、CWT scalogram
├── run_analysis.py       # 命令行入口
├── requirements.txt
├── samples/              # 示例 EDF
└── figures/              # 保存的图片（可选）
```

---

## 使用

### 命令行

```bash
# 默认读取 samples/A.0007.edf，绘制时域 + 频域
python run_analysis.py

# 指定 EDF
python run_analysis.py samples/A.0007.edf

# 可选参数
python run_analysis.py samples/A.0007.edf -n 3 -t 60 --fmax 50

# 保存图片到 figures/（默认）
python run_analysis.py samples/A.0007.edf --save

# 保存到指定目录，且不弹窗
python run_analysis.py samples/A.0007.edf -s -o output --no-show
```

| 参数 | 说明 |
|------|------|
| `edf_path` | EDF 文件路径（可选，默认 `samples/A.0007.edf`） |
| `-n, --channels` | 绘制的通道数 |
| `-t, --tmax` | 只分析前 tmax 秒 |
| `--fmax` | PSD 显示的最大频率 (Hz) |
| `-s, --save` | 保存时域/频域图到文件 |
| `-o, --outdir` | 保存目录（默认 `figures`） |
| `--no-show` | 不弹窗，仅保存 |

### Python API

```python
from data import SignalDataset

# 加载
dataset = SignalDataset("samples/A.0007.edf")
dataset.summary()

# 裁剪与滤波
dataset.crop(tmin=0, tmax=30)
dataset.apply_filter("band_pass", low_cut=1, high_cut=40)

# 时域特征
td = dataset.time_features()
# td["mean"], td["rms"], td["mobility"], ...

# 频域特征
fd = dataset.freq_features()
# fd["band_powers"], fd["dominant_frequency"], ...

# 绘图（可保存）
dataset.plot(n_channels=5, savepath="time.png", show=False)
dataset.plot_psd(n_channels=5, fmax=50, savepath="psd.png")
dataset.plot_spectrogram(channel=0, fmax=40)
dataset.plot_scalogram(channel=0, fmin=1, fmax=40)
```

```python
# 直接使用分析/预处理模块
from preprocessing import low_pass, high_pass, band_pass
from analysis import compute_time_features, compute_psd, cwt_scalogram, EEG_BANDS
```

---

## 依赖

| 包 | 用途 |
|----|------|
| mne | EDF 读取 |
| numpy | 数值计算 |
| scipy | 滤波、Welch PSD、spectrogram |
| matplotlib | 绘图 |
| PyWavelets | CWT scalogram |

---

## 版本说明

当前 README 对应项目当前实现；后续功能积累后会再更新 README。
