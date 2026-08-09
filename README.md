# mini-theater-speaker

从零开发的家庭音响系统。当前阶段基于 RK3399 Linux 平台验证 2.1 声道软件链路（左右卫星 + 低音炮），架构和音频管线按可平滑升级到 5.1 / 7.1 设计。

## 当前状态

- 分支：`theater_2.1_V1.0`
- 已完成：2.1 信号链参考实现、CamillaDSP 配置、测试音与自动化测试
- 进行中：系统架构与音频管线详细设计文档

## 设计文档

完整文档索引见 [docs/README.md](docs/README.md)，重点：

- [系统架构](docs/architecture.md)
- [Audio Pipeline 定义](docs/audio_pipeline.md)
- [声道映射规范](docs/channel_mapping.md)
- [配置规范](docs/config_spec.md)
- [RK3399 硬件平台说明](docs/hardware_rk3399.md)
- [开发路线图](docs/roadmap.md)

## V1 信号链

```text
USB PCM / 蓝牙 A2DP / 模拟 Line-in（立体声）
  -> 输入选择与归一化（48kHz）
  -> 声道重映射（stereo -> FL/FR/LFE）
  -> Bass Management（Linkwitz-Riley 4 阶 @ 100Hz）
  -> 每声道 PEQ / Delay / Gain / Limiter
  -> USB 3 声道 DAC -> TPA3116 2.1 功放 -> 扬声器
```

## 快速验证

无需 DSP 引擎和音频硬件：

```bash
bash scripts/run_validation.sh
```

等价步骤：

```bash
python3 scripts/generate_test_tones.py --with-raw
python3 scripts/validate_config.py configs/2.1.yml configs/2.1.stdin.yml configs/2.1.file.yml configs/2.1.usb.yml
python3 -m unittest discover -s tests -p "test_*.py"
```

## 仓库结构

```text
configs/                 CamillaDSP 配置
docs/                    设计文档
scripts/                 测试音、校验、信号链模拟
tests/                   自动化测试
assets/test_tones/       生成的 WAV 测试音
build/                   运行产物（不入库）
```

## 里程碑

| 阶段 | 目标 |
| --- | --- |
| M0 | 文档与架构（当前） |
| M1 | 2.1 软件验证（基本完成） |
| M2 | RK3399 平台接入（蓝牙/USB/Line-in） |
| M3 | 2.1 硬件与调音 |
| M4 | 产品化完善 |
| M5 | 5.1 升级 |
| M6 | 7.1 / 7.1.4 与换芯 |

详见 [docs/roadmap.md](docs/roadmap.md)。
