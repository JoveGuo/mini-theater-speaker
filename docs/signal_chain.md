# 信号链总览

> 完整定义见 [docs/audio_pipeline.md](audio_pipeline.md)，声道规范见 [docs/channel_mapping.md](channel_mapping.md)。

## V1 信号链

```text
USB PCM / 蓝牙 A2DP / 模拟 Line-in（立体声）
  -> 输入选择与归一化（48kHz）
  -> 声道重映射（stereo -> FL/FR/LFE）
  -> 前级处理（音量/增益）
  -> Bass Management（LR4 @ 100Hz）
  -> 每声道 PEQ / Delay / Gain / Limiter
  -> 输出重映射（FL=0, FR=1, LFE=2）
  -> USB 3 声道 DAC -> TPA3116 2.1 功放 -> 扬声器
```

## 与 5.1/7.1 的关系

2.1 只是管线的一个 profile：

- 增加声道时，输入布局、Bass Management 求和集合、输出映射同步扩展；
- 管线阶段本身不变；
- 当前 CamillaDSP 配置：`configs/2.1*.yml`。
