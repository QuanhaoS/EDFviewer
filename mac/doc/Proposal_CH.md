# EDFViewer 项目 Proposal

## 1. 项目名称

**EDFViewer：用于 EDF 信号可视化与时频分析的 GUI 和 CLI 工具**

## 2. 项目背景

EDFViewer 是一个面向生理信号分析的软件项目，主要用于读取、查看和分析 EDF 文件中的多通道信号。目标用户是实验室研究人员和临床人员。当前项目已经完成了初步功能，包括 EDF 文件读取、通道选择、降采样、时域可视化、频域分析、CWT scalogram 可视化、STFT spectrogram 可视化、BBI 分析、Amplitude 分析、PyQt6 图形界面、命令行脚本以及 PNG 导出。

下一阶段的目标是将已有原型整理为更清晰、更完整、更易维护的 EDF 分析工具。软件需要同时支持交互式 GUI 工作流和命令行工作流。GUI 主要用于人工浏览、参数调整和论文/报告出图；CLI 主要用于可复现分析和批处理式工作流。

本文档定义 EDFViewer 的功能需求、当前已实现基础、未来功能、风险与限制、验证计划和开发里程碑。

## 3. 目标用户

主要用户包括：

- 实验室研究人员：用于检查生理信号、比较时频分析结果、生成研究报告或论文图片。
- 临床人员：用于查看 EDF 记录、选择相关通道、检查时间窗口，并定位信号模式或噪声区域。

软件应考虑到用户可能不了解软件封装和信号处理实现细节，因此界面和文档需要支持实际分析流程，而不是要求用户理解底层算法实现。

## 4. 项目目标

项目主要目标是开发一个 EDF 信号分析工具，使用户能够：

- 打开 EDF 文件。
- 将任意 EDF channel 作为通用信号进行可视化和分析。
- 针对选定时间窗进行分析，而不是一次性渲染或计算完整长记录。
- 显示原始信号、BBI、Amplitude、CWT scalogram 和 STFT spectrogram。
- 在查看结果时交互式调整分析和可视化参数。
- 导出图片、特征和分析参数，便于报告和结果复现。
- 提供 GUI 和 CLI 两个版本，并尽可能保持二者核心分析功能一致。

## 5. 项目范围

### 5.1 当前范围

当前版本重点支持单个 EDF 文件分析。典型工作流是：用户打开一个 EDF 文件，选择一个 channel，选择一个时间窗口，调整参数，计算可视化结果，检查结果，并导出图片或分析结果。

软件当前不区分 EEG、ECG、PPG、呼吸、血压等信号类型，而是将所有 EDF 信号统一作为 channel 处理。BBI 和 Amplitude 等分析功能在信号内容适用时提供，但整个软件的基础逻辑仍然是通道级分析。

### 5.2 未来范围

未来功能需要与当前实现范围分开记录。以下功能作为未来功能保留，当前阶段不要求实现：

- GUI 中打开多个 EDF 文件，并在多个文件之间切换。
- CLI 批量处理多个 EDF 文件。
- 支持读取 CSV 和 MAT 文件。
- 打包 Windows exe。
- 打包 Linux 可执行文件。
- 增加更多可调分析参数。
- 增加可选 PDF 报告导出。

## 6. 当前已实现基础

当前代码库已经具备以下基础功能：

- 通过 data layer 读取 EDF 文件。
- 通道选择。
- 带抗混叠的降采样。
- 基础预处理函数，包括低通、高通和带通滤波。
- 时域分析函数。
- 频域分析函数，包括 PSD、频带能量、主频、谱质心、spectrogram 和 CWT scalogram。
- 与 PPG 相关的 BBI 和 Amplitude 分析辅助函数。
- PyQt6 和 PyQtGraph 图形界面。
- 用于时域、PSD、PLETH 和窗口化 PPG/scalogram 工作流的 CLI 脚本。
- GUI 当前 tab 和 CLI 生成图片的 PNG 导出。
- 使用 `samples/phantom.edf` 和生成脚本进行合成 EDF 测试。

部分已实现组件仍需要进一步集成、命名清理、文档同步和封装测试，才能作为完整的用户级功能交付。

## 7. 功能需求

### 7.1 数据输入需求

系统应支持打开 EDF 文件。

系统应读取 EDF 元数据，包括通道名称、采样率、信号时长和可用数据范围。

系统应允许用户选择一个 channel 进行重点分析。

系统应在 EDF 文件和 channel 选择完成后显示有效时间范围，使用户能够在可用记录范围内选择窗口起点和窗口长度。

系统应支持长时间记录，包括整夜记录。软件应通过选择时间窗进行分析，而不是强制显示或计算完整记录。

系统应将 CSV 和 MAT 文件读取作为未来功能保留。

### 7.2 GUI 需求

GUI 应支持以下主要流程：

1. 打开 EDF 文件。
2. 选择 channel。
3. 选择时间窗口。
4. 查看 raw signal、scalogram 和 spectrogram。
5. 边查看信号边调整参数。
6. 保存图片或分析结果。

GUI 应提供以下参数控制：

- 目标采样率。
- 窗口起点。
- 窗口长度。
- CWT wavelet 选择。
- STFT window 长度。
- 频率范围。
- 线性或对数频率轴。
- 颜色范围和值范围。
- 滤波参数。

GUI 应包含 `Signal + Scalogram` 视图。

`Signal + Scalogram` 视图应允许用户选择：

- Raw signal。
- BBI。
- Amplitude。

当前选择的信号视图应与对应的 scalogram 同时显示。

GUI 应包含 `Spectrogram` 视图。

Spectrogram 应作为与 scalogram 对照的视图。

GUI 应支持将当前可见 tab 保存为 PNG 图片。

GUI 应支持未来增加更多可调参数，而不需要大幅重构界面。

### 7.3 CLI 需求

CLI 和 batch scripts 应作为正式需求，而不是辅助工具。

CLI 版本应尽可能与 GUI 版本保持一致的分析功能。

CLI 应通过命令行参数支持可复现分析，包括文件路径、channel、时间窗、采样设置和输出路径。

CLI 应支持在不打开 GUI 的情况下生成分析图片。

CLI 的使用方式应写入 `README.md`。

未来 CLI 功能应支持批量处理多个 EDF 文件。

### 7.4 信号可视化需求

系统应显示所选 channel 的原始时域信号。

系统应将 BBI 作为核心分析功能之一。

系统应将 Amplitude 作为核心分析功能之一。

系统应在用户界面、文档和输出命名中统一使用 `BBI`。

系统应将 `BBI` 作为 beat-to-beat interval 输出的唯一面向用户术语。

系统未来可以增加其他核心分析功能。

### 7.5 Scalogram 需求

系统应提供 CWT scalogram 可视化。

Scalogram 应用于观察频率随时间变化。

Scalogram 应帮助用户定位 motion artifact 或其他噪声出现的时间位置。

Scalogram 应支持用于论文和报告出图。

Scalogram 应支持选择 wavelet。

Scalogram 应支持调整频率范围。

Scalogram 应支持线性和对数频率轴显示。

Scalogram 应支持调整颜色范围和值范围。

在同一分析上下文中比较 raw、BBI 和 amplitude scalogram 时，系统应支持统一的 value range。

### 7.6 Spectrogram 需求

系统应提供 STFT spectrogram 可视化。

Spectrogram 应作为 scalogram 的对照视图。

Spectrogram 应支持调整 STFT window 长度。

Spectrogram 应支持调整频率范围。

Spectrogram 应支持线性和对数频率轴显示。

Spectrogram 应支持调整颜色范围和值范围。

### 7.7 预处理需求

系统应支持降采样。

系统应支持滤波控制，包括滤波参数设置。

系统应支持低通、高通和带通滤波。

系统应保留未来增加更多预处理方法的能力。

### 7.8 导出需求

系统应支持将当前可见 GUI tab 导出为 PNG 图片。

系统应支持导出所有窗口或选定窗口的 PNG 图片。

系统应支持导出 CSV 特征表。

系统应支持保存分析参数，以便结果复现。

系统未来可以支持 PDF 报告导出，但 PDF 报告不是当前版本必须功能。

### 7.9 封装需求

当前版本应支持从 Python 源码运行。

当前版本应支持 macOS app 封装。

未来版本应支持 Windows exe 封装。

未来版本应支持 Linux 可执行文件封装。

## 8. 非功能需求

### 8.1 性能

软件应支持大型 EDF 记录，包括整夜记录。

当用户只需要分析一个时间窗时，软件不应强制渲染或计算完整记录。

软件应根据所选文件和 channel 的时长，向用户展示清晰的可选时间范围。

软件应在合适位置使用缓存，以提升最近窗口重复分析时的响应速度。

### 8.2 易用性

GUI 应让主要分析流程清晰可见。

GUI 应暴露重要可调参数，避免用户为了修改参数而编辑源代码。

GUI 应将 raw signal、scalogram 和 spectrogram 检查流程放在较近的位置。

文档应说明 GUI 和 CLI 两种运行方式。

### 8.3 可维护性

项目应保持模块化结构：

- Data layer：加载和管理信号。
- Preprocessing module：进行信号预处理。
- Analysis module：对数组执行数值分析。
- Visualization layer：负责绘图和交互。
- UI layer：负责用户界面流程组织。
- CLI layer：负责可复现脚本化工作流。

GUI 和 CLI 应尽可能复用共享分析函数。

## 9. 风险与限制

大型 EDF 文件可能需要仔细处理窗口化读取、缓存和内存管理。

不同 EDF 文件可能使用不同的 channel 名称、采样率、单位和元数据规范。

由于软件将 channel 作为通用信号处理，BBI 和 Amplitude 分析并不一定对每个 channel 都有意义。

Scalogram 和 spectrogram 结果会受到用户所选 wavelet、STFT window、频率范围、颜色范围和滤波设置影响。

Spectrogram 存在频谱泄漏和时频分辨率权衡，这可能影响结果解释。

PyQt6 应用在 macOS、Windows 和 Linux 上封装时，可能需要平台相关测试。

CSV 和 MAT 支持不属于当前实现范围，未来可能需要单独设计元数据处理规则。

临床用户应将本软件作为分析和可视化工具，而不是独立诊断设备。

## 10. 验证计划

验证计划应包括合成数据测试、真实 EDF 测试、GUI 工作流测试、CLI 工作流测试和导出测试。

### 10.1 合成 EDF 验证

使用 `samples/phantom.edf` 验证已知频率和幅值模式是否能在 raw signal、scalogram 和 spectrogram 中正确显示。

预期验证内容包括：

- 前 100 秒应显示 1.5 Hz、200 mV 幅值信号。
- 中间 100 秒应显示 1.5 Hz、100 mV 幅值信号。
- 最后 100 秒应显示 3 Hz、100 mV 幅值信号。
- Scalogram 和 spectrogram 应显示预期频率随时间变化。
- 导出图片应保留可见分析结果。

### 10.2 真实 EDF 验证

使用真实 EDF 文件验证：

- 文件读取。
- Channel 列表。
- Channel 选择。
- 窗口范围计算。
- 窗口化计算。
- 长记录下 GUI 响应速度。
- PNG 图片导出。
- CSV 特征输出。
- 分析参数记录。

### 10.3 CLI 验证

验证 CLI scripts 能够：

- 接收 EDF 输入路径。
- 选择 channel 和时间窗口。
- 生成预期图片。
- 保存输出到用户指定目录。
- 在适用情况下与 GUI 分析行为保持一致。

### 10.4 封装验证

当前版本需要验证：

- macOS 上 Python 源码运行。
- macOS app 启动。
- 从封装 app 打开 EDF 文件。
- 从封装 app 导出 PNG 图片。

未来版本需要验证 Windows 和 Linux 可执行文件行为。

## 11. 开发里程碑

### 里程碑 1：需求与文档整理

- 将项目名称统一为 `EDFViewer`。
- 完成英文和中文 Proposal。
- 将 README 更新为软件需求和使用说明文档。
- 创建产品开发文档。
- 清理术语，使面向用户的内容统一使用 `BBI`。

### 里程碑 2：核心 GUI 完善

- 确保 EDF 读取和 channel 选择稳定。
- 在 channel 选择后显示有效窗口范围。
- 改进长记录的时间窗口控制。
- 确保 raw、BBI、amplitude、scalogram 和 spectrogram 视图清晰。
- 增加或完善频率范围、颜色范围和滤波参数控制。

### 里程碑 3：分析一致性

- 确保 GUI 和 CLI 共享通用分析函数。
- 验证 CWT scalogram 在不同 wavelet 下的行为。
- 验证 STFT spectrogram 在不同 window 设置下的行为。
- 确保 BBI 和 Amplitude 输出命名一致并可导出。

### 里程碑 4：导出与复现

- 实现或完善当前 tab PNG 导出。
- 增加所有窗口或选定窗口 PNG 导出。
- 增加 CSV 特征表导出。
- 增加分析参数记录导出。
- 使用合成 EDF 和真实 EDF 验证导出结果。

### 里程碑 5：macOS 封装

- 将 GUI 封装为 macOS app。
- 验证启动、打开文件、分析和导出。
- 编写安装与启动说明。

### 里程碑 6：未来扩展

- 增加 GUI 多 EDF 文件切换。
- 增加 CLI 多 EDF 批处理。
- 增加 CSV 和 MAT 输入支持。
- 增加 Windows exe 封装。
- 增加 Linux 可执行文件封装。
- 考虑可选 PDF 报告导出。

## 12. 预期交付物

预期交付物包括：

- EDFViewer Python 源代码。
- macOS GUI app。
- 用于可复现分析的 CLI scripts。
- README 使用说明和需求文档。
- 英文项目 Proposal。
- 中文项目 Proposal。
- 产品开发文档。
- 合成 EDF 验证文件。
- 示例导出图片和特征输出。

## 13. 成功标准

当满足以下条件时，项目可认为达到目标：

- 用户可以在 GUI 中打开 EDF 文件。
- 用户可以选择 channel 和有效时间窗口。
- 用户可以查看 raw signal、BBI、Amplitude、scalogram 和 spectrogram。
- 用户可以在查看结果时调整关键分析参数。
- 用户可以导出图片、特征表和参数记录。
- CLI 可以在不打开 GUI 的情况下复现核心分析流程。
- macOS app 可以运行，用户不必手动从源码启动工具。
- 未来功能边界被清楚记录。
