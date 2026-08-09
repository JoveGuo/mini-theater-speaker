# RK3399 硬件平台说明

> 数据来源：iTOP-3399 开发板光盘资料《01 PCB_SCH_DATASHEET》  
> 覆盖：RK3399、ALC5651、AP6354 及音频相关接口

## 1. 平台定位

RK3399 是 V1 验证平台：

- 双 Cortex-A72 + 四 Cortex-A53，跑 CamillaDSP 的 2.1 处理绰绰有余；
- I2S0 支持 8 声道 TDM，后续 5.1/7.1 无需换 SoC 即可做算法验证；
- 板载 ALC5651 与 AP6354，提供模拟输入和蓝牙能力；
- 后续量产可替换为更低成本或更高算力的 SoC，应用层不绑定平台。

## 2. RK3399 音频相关接口

依据《Rockchip_RK3399_Datasheet_V2.1》：

| 接口 | 能力 | 用途 |
| --- | --- | --- |
| I2S0/PCM0 | 8 声道 | 主输出/外部多声道 DAC（TDM） |
| I2S1/PCM1 | 2 声道 | 板载 ALC5651 |
| S/PDIF | TX | 光纤/同轴输出（后续） |
| HDMI | TX + CEC | 视频输出，音频回传需外接 HDMI RX |
| USB 3.0 / 2.0 | - | USB 多声道 DAC、U 盘音源 |
| SDIO0 | 4-bit | AP6354 WiFi |
| UART | 多路 | AP6354 蓝牙 HCI、调试 |
| I2C0~I2C8 | - | 板载外设控制（ALC5651 等） |

## 3. 板载音频芯片 ALC5651

依据《ALC5651-CGT.pdf》：

| 项目 | 规格 |
| --- | --- |
| 类型 | 双声道 CODEC |
| DAC | 2 个模拟 DAC，4 通道播放路径（经 2 组 I2S 或 TDM） |
| ADC | 2 个模拟 ADC，4 通道录音路径 |
| 采样率 | 8k ~ 192kHz，24-bit |
| 数字接口 | 2 组 I2S/PCM；TDM 最多 8 槽 |
| 控制接口 | I2C |
| 内置 DSP | 7 段 EQ、DRC/AGC、ASRC、SounzReal 音效 |
| 输出 | 立体声耳机放大 + Line-out，约 1Vrms 满幅 |
| 输入 | 立体声 Line-in、麦克风（带 boost） |

对本项目的意义：

- **V1 角色**：模拟 AUX 输入（Line-in -> ADC -> I2S1 -> DSP）和耳机/线路监听；
- **不是 2.1 主输出**：只有 2 个模拟 DAC，无法原生输出 L/R/SUB 三路；
- **5.1/7.1 可行性**：可通过 TDM 挂多片 ALC5651（每片 2 DAC）或外接多声道 DAC；更推荐 I2S0 外接专业多声道 DAC。

## 4. WiFi/蓝牙模块 AP6354

依据《AP6354 datasheet_V1.1》：

| 项目 | 规格 |
| --- | --- |
| WiFi | 802.11 a/b/g/n/ac 2x2 MIMO，最高 867 Mbps |
| 蓝牙 | BT 4.1（1/2/3 Mbps），Class 1/2 |
| WiFi 接口 | SDIO 3.0（4-bit，SDR104） |
| BT 接口 | UART（HCI，最高 4 Mbps）+ PCM（语音） |
| 供电 | VBAT 3.0~4.8V、VDDIO 1.7~3.6V |
| 工作温度 | -10°C ~ 65°C |

对本项目的意义：

- 蓝牙 A2DP 播放走 UART HCI + BlueZ；
- PCM 口面向传统语音，本项目不使用；
- 天线/布局参考开发板设计，量产时注意 WiFi/BT 共存与干扰。

> 注意：当前手头板卡丝印确认实际芯片为 **RTL8822CS**，与资料手册里的 AP6354 不同；软件适配以实际芯片为准（见 `docs/rk3399_sdk_bringup.md`）。

## 5. V1 音频链路

```text
输入：
  USB PCM  ----------------> RK3399 USB Host
  蓝牙 A2DP ---------------> AP6354 ---> BlueZ
  模拟 AUX ----------------> ALC5651 Line-in ---> I2S1

处理：
  RK3399 运行 PipeWire + CamillaDSP（48kHz 浮点）

输出：
  USB 3 声道 DAC ---> TPA3116 2.1 功放 ---> FL / FR / SUB
```

## 6. 推荐 V1 输出硬件

| 器件 | 选型建议 | 说明 |
| --- | --- | --- |
| USB DAC | 3 声道（或 6/8 声道兼容） | 需支持 S32_LE 或 S24_LE；优先选择 Linux 免驱 UAC2 设备 |
| 功放 | TPA3116 2.1（或 2xTPA3116 + 低音炮功放） | D 类，24V 供电，散热良好 |
| 卫星单元 | 3~4 寸全频 | 分频点 100Hz 附近可用 |
| 低音炮 | 6~8 寸，带箱体 | 推荐有源或独立功放通道 |
| 电源 | 24V 5A（功放）+ 板载电源 | 余量 ≥ 30% |

## 7. 后续扩展

| 方向 | 硬件变化 |
| --- | --- |
| 5.1 | USB 6/8 声道 DAC + 5.1 功放，或 I2S0 TDM + 8 声道 DAC |
| 7.1 | 8 声道 DAC + 8 声道功放 |
| HDMI ARC | 增加 HDMI RX/ARC 子板 |
| 换 SoC | 只要保留 USB Audio 与 I2S/TDM，软件管线无需重构 |
