# RK3399 Linux 板卡接入指南

> 硬件细节见 `docs/hardware_rk3399.md`，管线定义见 `docs/audio_pipeline.md`。

## 1. 为什么用 RK3399

RK3399（双 A72 + 四 A53）跑 2.1 分频、EQ、低音管理和限幅绰绰有余；I2S0 支持 8 声道 TDM，后续 5.1/7.1 也能先做算法验证。V1 不需要换 RK3588 或树莓派。

## 2. 系统选型

V1 使用 **Ubuntu 24.04 LTS（arm64）rootfs + 厂商 BSP 内核**，原因与对比见 `docs/linux_os_selection.md`。优先复用 iTOP SDK 的内核/设备树/固件，只把用户态 rootfs 换成 Ubuntu minimal；若厂商已有 Ubuntu 镜像（iTOP 光盘/SDK 中通常提供），可直接烧录并在其上安装依赖。

### 2.1 启动策略（推荐）

当前板卡刷的是 Android 8，不建议直接擦除：

- **保留 eMMC 上的 Android**，作为备选/演示系统；
- **从 SD 卡（或 USB）启动 Ubuntu**，用于本项目开发；
- RK3399 的启动选择由 boot 拨码/烧录工具控制，开发完成后可再决定量产固件方案；
- Android 开发环境保留，用于编译 BSP 内核/固件，或后续做手机遥控 App。

## 3. 硬件连接

```text
RK3399 Linux 板卡
  ├─ USB Host ─> USB 3 声道声卡 ─> TPA3116 2.1 功放 ─> L/R/SUB
  ├─ AP6354   ─> 蓝牙 A2DP 输入
  ├─ ALC5651  ─> 模拟 Line-in / 耳机监听
  └─ 以太网    ─> 调试、后续网络流媒体
```

## 4. 内核与设备树要点

确认内核开启/设备树配置：

- ALSA：`CONFIG_SND_ALOOP`（回环验证）、`CONFIG_SND_SOC_ROCKCHIP_I2S`、ALC5651 的 ASoC 驱动；
- 蓝牙：`CONFIG_BT`、`CONFIG_BT_HCIUART`、`CONFIG_BT_HCIUART_BCM`（AP6354 对应 Broadcom 蓝牙方案），dts 中配置 `BT_REG_ON`/`WL_REG_ON`；
- WiFi：SDIO 接口对应 `brcmfmac` 驱动，需正确加载 NVRAM；
- USB Audio：`CONFIG_SND_USB_AUDIO`。

## 5. 系统准备

1. 使用配套 Linux SDK 编译并烧录系统，确认网络连通。
2. 查看音频设备：

```bash
aplay -l
arecord -l
cat /proc/asound/cards
```

3. 确认 ALC5651 设备出现，例如 `plughw:CARD=rockchiprk3399,DEV=0`。
4. 插入 USB 声卡，记录设备名，例如 `plughw:CARD=USB,DEV=0`。
5. 安装依赖：

```bash
sudo apt update
sudo apt install -y python3 python3-yaml git curl bluez pipewire wireplumber
```

6. 安装 CamillaDSP：优先使用官方 aarch64 Linux 预编译包，或 `cargo install camilladsp`。

## 6. 无硬件验证

```bash
sudo modprobe snd-aloop
bash scripts/run_validation.sh
```

`configs/2.1.yml` 使用 ALSA 回环，适合先验证系统集成。

## 7. 接入 USB 声卡

编辑 `configs/2.1.usb.yml`，把 `plughw:CARD=USB,DEV=0` 改为实际设备名，然后启动：

```bash
camilladsp configs/2.1.usb.yml
```

先用测试音验证声道顺序：

```bash
aplay -D plughw:CARD=USB,DEV=0 assets/test_tones/left_1k.wav
aplay -D plughw:CARD=USB,DEV=0 assets/test_tones/right_1k.wav
aplay -D plughw:CARD=USB,DEV=0 assets/test_tones/sub_50.wav
```

## 8. 蓝牙 A2DP 输入

AP6354 使用 UART HCI + BlueZ：

```bash
bluetoothctl
scan on
pair <phone-mac>
trust <phone-mac>
connect <phone-mac>
```

配置 PipeWire 将蓝牙 sink 路由到 ALSA loopback，CamillaDSP 从 loopback 采集。V1 使用 SBC/AAC；LDAC/aptX 需要评估模块编解码能力。

## 9. 模拟 Line-in（ALC5651）

用 `alsamixer` / `amixer` 打开 Line-in 并设置增益：

```bash
amixer -c 0 sset 'IN1' 30
amixer -c 0 sset 'Capture' 20
arecord -D plughw:CARD=rockchiprk3399,DEV=0 -f S16_LE -c 2 -r 48000 /tmp/linein.wav
```

再把该 ALSA 设备作为 CamillaDSP 输入源之一（参考 `docs/config_spec.md`）。

## 10. systemd 服务（规划）

建议以 systemd 管理常驻服务：

```ini
[Unit]
Description=CamillaDSP theater engine
After=pipewire.service

[Service]
ExecStart=/usr/local/bin/camilladsp /etc/theater/configs/2.1.usb.yml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 11. 常见排查

| 现象 | 排查 |
| --- | --- |
| `aplay -l` 无 USB 声卡 | 检查 USB 枚举、`dmesg`、UAC 兼容性 |
| 蓝牙连不上 | 检查 AP6354 供电、`BT_REG_ON`、dts、固件/NVRAM |
| ALC5651 无声音 | `amixer` 查看 PA/DAC 状态，确认 I2S 时钟和格式 |
| 输出爆音 | 检查启动顺序、限幅、淡入淡出、功放静音脚时序 |
