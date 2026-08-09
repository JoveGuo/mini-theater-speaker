# Audio Pipeline 定义

> 状态：草稿（V1 评审稿）  
> 本文是 mini-theater-speaker 音频信号链的权威定义，所有配置与代码实现以本文为准。

## 1. 目标

定义一条与声道数量无关、可配置、可测试的音频处理管线，当前以 2.1 落地，未来可直接扩展 5.1 / 7.1。

## 2. 内部音频约定

| 项目 | 约定 |
| --- | --- |
| 处理采样率 | 48000 Hz（源侧统一采样率转换后进入 DSP） |
| DSP 内部精度 | 浮点处理，边界按设备能力选择 S16_LE / S24_LE / S32_LE |
| 声道语义 | 使用逻辑声道名（FL/FR/LFE...），不使用裸数字通道号 |
| 声道数量 | 管线按 8 声道建模，2.1 是 3 声道 profile |
| 块大小 | 默认 1024 帧；低延迟 profile 可降为 256/512 帧 |

## 3. 管线总览

```mermaid
flowchart LR
  A["Input Adapter"] --> B["Input Selector"]
  B --> C["Rate/Format Normalize"]
  C --> D["Input -> Logical Remap"]
  D --> E["Pre-processing"]
  E --> F["Upmix / Downmix"]
  F --> G["Bass Management"]
  G --> H["Per-channel Processing"]
  H --> I["Logical -> Output Remap"]
  I --> J["Output Sink"]
```

## 4. 各阶段定义

### 4.1 Input Adapter（输入适配）

负责采集一路原始 PCM 并给出：

- 声道数、声道布局（如 stereo = FL/FR）；
- 采样率、位深、格式；
- 设备/节点标识（ALSA 设备名、PipeWire node id）。

V1 输入：

| 输入 | 布局 | 说明 |
| --- | --- | --- |
| USB PCM | stereo / 多声道 | 直连 ALSA 或经 PipeWire |
| A2DP | stereo | BlueZ -> PipeWire -> ALSA loopback |
| Line-in | stereo | ALC5651 ADC -> I2S1 -> ALSA |

### 4.2 Input Selector（输入选择）

- 同一时刻只允许一个活动输入（V1）；
- 支持输入切换时软静音/淡入淡出，避免爆音；
- 后续可扩展多输入混音、自动切换、优先级。

### 4.3 Rate/Format Normalize（归一化）

- 44.1kHz 等源统一转换到 48kHz；
- 位深/格式转换到 DSP 输入约定；
- 转换可在 PipeWire、ALSA `plug` 或 DSP 引擎完成，但对上层透明。

### 4.4 Input -> Logical Remap（输入布局重映射）

将源声道布局映射到逻辑声道集合，例如：

| 源布局 | 逻辑声道 |
| --- | --- |
| stereo | FL, FR |
| 5.1 (ALSA) | FL, FR, FC, LFE, BL, BR |
| 7.1 (ALSA) | FL, FR, FC, LFE, BL, BR, SL, SR |

规则：**输入声道顺序必须显式声明**，默认采用 ALSA 标准顺序；若源设备顺序不同，用映射表纠正。

### 4.5 Pre-processing（前级处理）

- 主音量、声道平衡、静音；
- 输入增益/衰减；
- 可选：响度补偿、压缩器/AGC、低音/高音音调；
- 位置：在 Bass Management 之前，保证所有声道音量一致。

### 4.6 Upmix / Downmix（上混 / 下混）

V1 仅实现 stereo 到 2.1 的“直通 + 低频管理”，即：

- FL、FR 原样进入卫星通道；
- 低频内容由 Bass Management 从 FL+FR 提取到 LFE。

后续可扩展：

| 场景 | 算法 |
| --- | --- |
| stereo -> 5.1 | 简单环绕提取或虚拟环绕（如 Dolby Pro Logic II 类） |
| 5.1 -> 2.1 | 下混到 FL/FR，LFE 合并进 SUB |
| 5.1 原生直通 | 不改变声道布局，只做 Bass Management |

### 4.7 Bass Management（低频管理）

这是 2.1 的核心，也是 5.1/7.1 的统一机制。

默认参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| 分频点 | 100 Hz | 按实际单元与听音位测量后调整 |
| 滤波器 | Linkwitz-Riley | 4 阶（LR4） |
| 卫星高通 | 从每个非 LFE 声道提取高频 | FL/FR 各一个高通 |
| 低音低通 | 所有非 LFE 声道和 LFE 混合后低通 | 求和 -> 低通 -> 输出到 SUB |
| LFE 增益 | 0 dB | 可调 |
| 相位 | 0° | 用于分频区对齐 |

处理公式（V1 stereo -> 2.1）：

```text
sat_L = HP(FL)
sat_R = HP(FR)
SUB   = LP(FL + FR + LFE_in)
```

5.1 时：

```text
sat_FL = HP(FL)
sat_FR = HP(FR)
sat_FC = HP(FC)
sat_BL = HP(BL)
sat_BR = HP(BR)
SUB    = LP(FL + FR + FC + BL + BR + LFE_in)
```

设计要点：

- 分频点、阶数、滤波器类型均可配置；
- 多低音炮（2 个 SUB）在 V2 之后支持，SUB 路由本身仍是配置；
- 所有声道数变化只影响 Bass Management 的输入求和集合，不改管线框架。

### 4.8 Per-channel Processing（每声道处理）

每个输出声道按固定顺序：

```text
PEQ / Room EQ -> Delay -> Gain -> Limiter
```

| 处理 | 说明 |
| --- | --- |
| PEQ | 房间/单元频响校正，默认关闭，由测量结果生成 |
| Delay | 声道间物理延迟对齐，默认 0 ms，支持小数 |
| Gain | 声道电平微调 |
| Limiter | 软限幅，默认 -0.5 dBFS，保护功放与单元 |

### 4.9 Logical -> Output Remap（输出重映射）

把逻辑声道映射到物理 DAC 通道。V1 USB DAC 3 通道：

| 物理通道 | 逻辑声道 |
| --- | --- |
| 0 | FL |
| 1 | FR |
| 2 | LFE（SUB） |

映射必须显式配置，避免将来更换 DAC 时改动管线代码。

### 4.10 Output Sink（输出）

- ALSA 播放设备，格式按 DAC 能力选择；
- V1 默认 `S32_LE`，3 声道；
- `chunksize` / `target_level` 是延迟与稳定性的主要旋钮；
- 输出前做最后的爆音防护（淡入淡出、静音）。

## 5. 延迟预算

| 阶段 | 典型延迟 |
| --- | --- |
| 采集 / 路由 | 5 ~ 15 ms |
| DSP 处理（含块缓冲） | 10 ~ 25 ms（chunksize 1024 时更高） |
| 输出缓冲 | 5 ~ 15 ms |
| V1 总延迟目标 | ≤ 40 ms |
| 后续低延迟 profile | ≤ 20 ms（chunksize 256/512） |

延迟测量方法见 `docs/measurement_method.md`。

## 6. 配置模板

### 6.1 当前 2.1 引擎配置

`configs/2.1*.yml` 直接对应 CamillaDSP 配置，管线为：

```text
Mixer(to_2_1) -> Filter(HP+Delay+Limiter per channel) -> Filter(LP+Delay+Limiter SUB)
```

### 6.2 未来 5.1 引擎配置（规划示例）

```yaml
mixers:
  to_5_1:
    channels:
      in: 6
      out: 6
    mapping: []   # 由配置管理器根据 channel_map 生成
filters:
  hp_fl: { type: BiquadCombo, parameters: { type: LinkwitzRileyHighpass, freq: 100, order: 4 } }
  lp_sub: { type: BiquadCombo, parameters: { type: LinkwitzRileyLowpass, freq: 100, order: 4 } }
pipeline:
  - type: Mixer
    name: to_5_1
  - type: Filter
    channels: [0]
    names: [hp_fl, delay_fl, limit_fl]
  # ... FC / BL / BR / LFE 同理
```

具体通道号由 `docs/channel_mapping.md` 和 `docs/config_spec.md` 统一定义。

## 7. 测试与验收

每个阶段必须有对应测试：

| 阶段 | 测试方法 |
| --- | --- |
| 输入适配 | 播放已知 WAV，验证声道布局与格式 |
| 重映射 | 单声道测试音逐通道注入，验证路由 |
| Bass Management | 50Hz 正弦只出现在 SUB；1kHz 只出现在卫星 |
| 每声道处理 | 逐个启用 PEQ/Delay/Limiter，验证响应 |
| 端到端 | `scripts/run_validation.sh` + 真实硬件测量 |

现有自动化测试见 `tests/test_2_1_signal_chain.py`。
