# EDFReader

生理信号分析工具：读取 EDF、降采样、滤波、时域/频域分析、PPG 派生指标（逐搏幅度、PPI），以及可视化（matplotlib 命令行脚本 + PyQt6 图形界面）。

---

## 功能概览

- **数据加载**：将 EDF 读入 `SignalDataset`；通道选择、时间裁剪、抗混叠降采样
- **预处理**：Butterworth 低/高/带通滤波；`preprocessing.downsample` 降低采样率
- **时域分析**：基本统计、RMS、峰峰值、过零率、Hjorth 参数等
- **频域分析**：Welch PSD、频段功率、spectrogram、CWT scalogram 等
- **PPG 相关**：逐搏幅度、峰峰间隔 PPI；GUI 与批处理脚本会用到
- **可视化**：时域、PSD、spectrogram、scalogram；CLI/GUI 均可导出 PNG

---

## 环境要求

- Python ≥ 3.8
- 依赖见 `requirements.txt`（含 GUI：PyQt6、pyqtgraph）

---

## 安装

```bash
cd EDFReader
pip install -r requirements.txt
```

部分脚本默认示例路径为 `samples/A.0007.edf`；若仓库中无该文件，请改为你的 EDF 路径。

---

## 项目结构

```
EDFReader/
├── app.py                    # 统一入口：--mode gui（默认）或 --mode cli
├── gui_pyqt6.py              # PyQt6 + PyQtGraph GUI（由 app.py 加载）
├── run_analysis.py           # CLI：时域 + PSD（与 app.py --mode cli 参数一致）
├── run_pleth_scalogram.py    # CLI：按时间窗切 PLETH，输出「原始+幅度+scalogram」PNG
├── run_ppg_window_scalogram.py  # CLI：单时间窗，输出 3 张 PNG（raw/amp/PPI + scalogram）
├── data/
│   ├── edf_viewer.py         # 简单读取与绘图
│   └── signal_dataset.py     # 加载、裁剪、滤波、降采样、分析、绘图
├── preprocessing/
│   ├── filter.py             # low_pass, high_pass, band_pass
│   └── downsample.py         # 抗混叠降采样
├── analysis/
│   ├── time_domain.py
│   ├── freq_domain.py
│   └── ppg.py                # compute_ppg_amplitude, compute_ppi
├── requirements.txt
├── versions/                 # cli_version / gui_version 副本，见 versions/README.md
└── figures/                  # 常用输出目录（保存时自动创建）
```

---

## 使用说明

### 1. 统一入口 `app.py`

```bash
# 图形界面（默认）：选择 EDF、通道、窗长/窗索引后，按窗计算
python app.py
python app.py --mode gui

# 命令行：与 run_analysis.py 行为一致
python app.py --mode cli
python app.py --mode cli 你的文件.edf -n 3 -t 60 --fmax 50 --save
```

GUI（`gui_pyqt6.py`）共 5 个 Tab：`Raw + Amp`、`PPI + PPI Scal`、`Raw Scalogram`、`Amp Scalogram`、`Spectrogram`。**Window length** 与 **Window index** 决定当前分析的时间段；点击 **Compute current window** 只计算当前窗（最近 2 个窗结果会缓存以便来回切换）。**Save current Tab PNG** 导出当前 Tab 为 PNG。

无显示器环境可尝试：

```bash
QT_QPA_PLATFORM=offscreen python app.py --mode gui
```

### 2. 命令行：通用 EDF（`run_analysis.py`）

```bash
python run_analysis.py
python run_analysis.py 你的文件.edf -n 3 -t 60 --fmax 50
python run_analysis.py 你的文件.edf --save -o figures --no-show
```

| 参数 | 说明 |
|------|------|
| `edf_path` | EDF 路径（可选；默认 `samples/A.0007.edf`，需文件存在） |
| `-n, --channels` | 绘制的通道数 |
| `-t, --tmax` | 只分析前 `tmax` 秒 |
| `--fmax` | PSD 图最大频率 (Hz) |
| `-s, --save` | 保存时域与频域图 |
| `-o, --outdir` | 保存目录（默认 `figures`） |
| `--no-show` | 不弹窗（常与 `--save` 联用） |

### 3. PLETH / PPG 批处理脚本

**长时程、按窗导出**（`run_pleth_scalogram.py`）：保留单通道（默认 `PLETH`），降至 16 Hz，再按时间窗（默认 1 小时，可用 `--window-min` 指定分钟）每个窗保存一张 PNG（原始波形 + 逐搏幅度 + scalogram）。

```bash
python run_pleth_scalogram.py 你的文件.edf
python run_pleth_scalogram.py 你的文件.edf -w 2 -o figures/pleth
python run_pleth_scalogram.py 你的文件.edf --window-min 1.2 --segment 60 -o figures/pleth
```

**单窗、三张图**（`run_ppg_window_scalogram.py`）：裁剪 `[tstart, tstart+tlen]`，降采样后输出三张 PNG：原始+scalogram、幅度+scalogram、PPI+scalogram。

```bash
python run_ppg_window_scalogram.py 你的文件.edf \
  -c PLETH --target-hz 16 --tstart 3600 --tlen 60 -o figures/ppg_window
```

---

## `versions/` 目录

`versions/cli_version` 与 `versions/gui_version` 为独立副本，用法见 `versions/README.md`。

---

## 打包可执行文件

以 `app.py` 为唯一入口，GUI 与 CLI 共用实现。

```bash
pip install pyinstaller PyQt6 pyqtgraph
pyinstaller --noconfirm --onefile --windowed --name EDFReader app.py
pyinstaller --noconfirm --onefile --name EDFReaderCLI app.py
```

- GUI：`dist/EDFReader`
- CLI：`dist/EDFReaderCLI --mode cli [edf_path] [选项]`

---

## Python API

```python
from data import SignalDataset

dataset = SignalDataset("你的文件.edf")
dataset.summary()

dataset.select_channels(["PLETH"])
dataset.crop(tmin=0, tmax=30)
dataset.downsample(16.0)  # 原采样率高于目标时
dataset.apply_filter("band_pass", low_cut=1, high_cut=40)

td = dataset.time_features()
fd = dataset.freq_features()

dataset.plot(n_channels=5, savepath="time.png", show=False)
dataset.plot_psd(n_channels=5, fmax=50, savepath="psd.png")
dataset.plot_spectrogram(channel=0, fmax=40)
dataset.plot_scalogram(channel=0, fmin=1, fmax=40)
```

```python
from preprocessing import low_pass, high_pass, band_pass
from preprocessing.downsample import downsample
from analysis import (
    compute_time_features,
    compute_psd,
    cwt_scalogram,
    compute_ppg_amplitude,
    compute_ppi,
    EEG_BANDS,
)
```

---

## 依赖

| 包 | 用途 |
|----|------|
| mne | 读 EDF |
| numpy | 数组运算 |
| scipy | 滤波、Welch、spectrogram |
| matplotlib | 命令行出图 |
| PyWavelets | CWT scalogram |
| PyQt6 | GUI |
| pyqtgraph | GUI 快速绘图 |

---

## 版本说明

本文档对应仓库根目录当前实现；`versions/` 下为分发的 CLI/GUI 副本，功能应与根目录类似。
