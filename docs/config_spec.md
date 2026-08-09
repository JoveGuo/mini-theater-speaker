# 配置规范（Config Spec）

> 状态：草稿（V1 评审稿）

## 1. 配置分层

系统使用两层配置：

| 层级 | 内容 | 示例 |
| --- | --- | --- |
| Profile（产品层） | 声道拓扑、输入输出、Bass Management、预设 | `configs/profiles/2.1.yml`（规划） |
| Engine（引擎层） | 当前 DSP 引擎（CamillaDSP）可直接加载的配置 | `configs/2.1*.yml` |

V1 先直接维护引擎层配置；配置管理器（`theaterd`）落地后，由 Profile 生成 Engine 配置。

## 2. Profile 字段定义

```yaml
id: theater-2.1
version: 1
engine: camilladsp

samplerate: 48000
chunksize: 1024

input:
  - id: usb-in
    type: alsa
    device: "plughw:CARD=USB,DEV=0"
    channels: 2
    format: S16_LE
  - id: bt-a2dp
    type: pipewire
    node: bluez_output.xx
    channels: 2
    format: FLOAT32LE
  - id: line-in
    type: alsa
    device: "plughw:CARD=rockchiprk3399,DEV=0"
    channels: 2
    format: S16_LE

output:
  id: usb-out
  type: alsa
  device: "plughw:CARD=USB,DEV=0"
  channels: 3
  format: S32_LE

channel_map:
  input_layout: [FL, FR]
  output_layout: [FL, FR, LFE]
  physical:
    - logical: FL
      alsa_channel: 0
    - logical: FR
      alsa_channel: 1
    - logical: LFE
      alsa_channel: 2

bass_management:
  enabled: true
  crossover_hz: 100
  filter: LinkwitzRiley
  order: 4
  lfe_gain_db: 0.0
  sub_phase_deg: 0
  satellite_inputs: [FL, FR]
  sub_outputs: [LFE]

processing:
  pre:
    master_volume_db: -12.0
    balance: 0.0
  per_channel:
    FL:
      peq: []
      delay_ms: 0.0
      gain_db: 0.0
      limiter_db: -0.5
    FR:
      peq: []
      delay_ms: 0.0
      gain_db: 0.0
      limiter_db: -0.5
    LFE:
      peq: []
      delay_ms: 0.0
      gain_db: 0.0
      limiter_db: -0.5

presets:
  - id: music
    master_volume_db: -12.0
  - id: movie
    master_volume_db: -10.0
  - id: night
    master_volume_db: -20.0
    compression: light
```

## 3. 字段说明

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 唯一标识，如 `theater-2.1` |
| `engine` | 是 | DSP 引擎类型，目前仅 `camilladsp` |
| `samplerate` | 是 | DSP 处理采样率，固定 48000 |
| `input[]` | 是 | 可用输入列表，`id` 全局唯一 |
| `output` | 是 | 播放设备与通道数 |
| `channel_map` | 是 | 逻辑声道与物理通道映射（见 `docs/channel_mapping.md`） |
| `bass_management` | 否 | 低频管理参数；关闭则输入 LFE 直通 |
| `processing` | 否 | 前级与每声道处理参数 |
| `presets` | 否 | 场景预设 |

## 4. 从 Profile 生成 CamillaDSP 配置

生成规则：

1. 根据 `channel_map.input_layout` 生成输入 mixer；
2. 根据 `output_layout` 生成通道集合；
3. 若启用 Bass Management：
   - 非 LFE 逻辑声道接高通；
   - `sub_outputs` 接低通，输入为 `satellite_inputs + 输入 LFE`；
4. 每声道按 `processing.per_channel` 生成 PEQ -> Delay -> Gain -> Limiter；
5. 最后根据 `physical` 表重排输出通道。

生成器属于 `theaterd` 的配置管理模块（规划），当前可以先用手工维护的 `configs/2.1*.yml`。

## 5. 配置校验要求

所有配置必须通过 `scripts/validate_config.py`。校验规则：

- `samplerate`、`chunksize` 为正数；
- 输入声道数等于 `channel_map.input_layout` 长度；
- 输出声道数等于 `output.channels`；
- 每个逻辑输出声道都有对应的 `physical` 映射；
- Bass Management 开启时，分频点 > 0 且存在 SUB 输出；
- 未映射的物理通道显式静音。

## 6. 文件组织（规划）

```text
configs/
  profiles/            # 产品层 profile（2.1、5.1、7.1...）
  generated/           # 由 profile 生成的引擎配置
  2.1.yml              # V1 手工维护的 CamillaDSP 配置
  2.1.stdin.yml
  2.1.file.yml
  2.1.usb.yml
```

## 7. 变更流程

1. 修改 profile；
2. 重新生成引擎配置；
3. 运行 `bash scripts/run_validation.sh`；
4. 在目标硬件上用测试音验证声道顺序；
5. 提交时附上通道映射表变化说明。
