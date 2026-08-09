# RK3399 SDK 板级 Bring-up 状态与下一步计划

> 检查日期：2026-08-09  
> SDK 路径：`Z:\Code\rk3399_linux_sdk_v2.0`  
> 板级配置：`device/rockchip/rk3399/BoardConfig.mk`，`RK_KERNEL_DTS=itop-3399_linux-lvds`

## 1. SDK 现状（已确认）

| 项目 | 状态 |
| --- | --- |
| 内核 | 4.4.179（Rockchip BSP），`rockchip_linux_defconfig` |
| 内核构建 | `./build.sh kernel` 等价于 `make ARCH=arm64 rockchip_linux_defconfig && make ARCH=arm64 itop-3399_linux-lvds.img` |
| ALC5651（rt5651） | 驱动已启用（`CONFIG_SND_SOC_RT5651=y`），dts 已配置：`rt5651@1a`（I2C1）、`i2s0`、声卡 `realtek,rt5651-codec` |
| USB Audio | 已启用（`CONFIG_SND_USB_AUDIO=y`） |
| snd-aloop | 未启用，需要打开（用于无硬件回环验证） |
| HDMI 音频 | 通过 i2s2 已启用 |
| SPDIF | dts 中 `status = "disabled"`，需要时再打开 |
| WiFi | dts 默认 `WIFI_RTL8822CS`；`CONFIG_CYW_BCMDHD` 未启用。若板载芯片是 AP6354，当前 WiFi 驱动不匹配 |
| 蓝牙 | `CONFIG_BT=y`、H4 已启用，但 `CONFIG_BT_HCIUART_BCM` 未启用，AP6354 蓝牙当前不可用 |
| AP6354 固件 | SDK 已包含：`fw_bcm4354a1_ag.bin`、`nvram_ap6354.txt`、`BCM4354A2.hcd` / `bcm4354a1.hcd`（`external/rkwifibt/firmware/broadcom/all/`） |
| Ubuntu 镜像 | `ubuntu/ubuntu_1604.img`（3.2GB）。文件名与“20.04 无桌面版”不一致，需在板端确认实际版本 |

## 2. 待确认项

1. **板载 WiFi/BT 芯片型号**：SDK dts 默认 RTL8822CS，但硬件资料里是 AP6354。请在板端确认：

```bash
ls /sys/bus/sdio/devices/*/device
dmesg | grep -iE "wlan|bluetooth|brcm|rtl|sdio"
ip link
```

也可以直接看模块丝印。

2. **Ubuntu 实际版本**：

```bash
cat /etc/os-release
uname -a
```

如果输出不是 `20.04`，需要拿到正确的 ubuntu20_64bit 无桌面版镜像。

3. **当前内核是否由这套 SDK 编译**：`uname -r` 与 SDK 内 `kernel/.config` 是否能对上，决定后续是增量编译还是全量重刷。

## 3. 下一步开发清单

### 3.1 板端基线确认（不改代码）

```bash
# 音频设备
aplay -l
arecord -l
cat /proc/asound/cards

# 蓝牙/WiFi 状态
rfkill list
bluetoothctl list
ip link

# 存储与分区（后续刷内核需要）
cat /proc/partitions
```

确认：

- rt5651 声卡是否出现；
- USB 声卡插入后能否被识别；
- WiFi/BT 当前是否可用；
- SSH 与网络是否可用（后续 apt 安装依赖）。

### 3.2 内核与设备树调整（在 SDK 中进行）

以板载芯片确认为 **AP6354** 为前提：

1. 修改 `kernel/arch/arm64/boot/dts/rockchip/itop-3399_linux-board.dtsi`：
   - 把 `#define WIFI_RTL8822CS 1` 注释掉；
   - 增加 `#define WIFI_AP6354 1` 分支，节点内容参考现有 `WIFI_AP6356s` 分支，`wifi_chip_type = "ap6354"`，GPIO 保持不变。
2. 修改 `kernel/arch/arm64/configs/rockchip_linux_defconfig`：
   - `CONFIG_CYW_BCMDHD=y`（AP6354 WiFi，SDK 使用 Rockchip cywdhd 驱动）；
   - `CONFIG_BT_HCIUART_BCM=y`（Broadcom 蓝牙 UART）；
   - `CONFIG_SND_ALOOP=y`（回环验证）；
   - 关闭 `CONFIG_RTL8822CS`（避免与 AP6354 冲突）。
3. 重新编译并打包：

```bash
cd /path/to/rk3399_linux_sdk_v2.0
./build.sh kernel
./build.sh firmware
./build.sh updateimg
```

或按板端烧录工具只更新 `boot.img`/`resource.img`。

### 3.3 固件部署到 rootfs

AP6354 需要把 SDK 内固件放入 Ubuntu 系统：

```bash
# WiFi（Rockchip cywdhd 默认查找 /vendor/etc/firmware 或 /system/etc/firmware）
sudo mkdir -p /vendor/etc/firmware
sudo cp fw_bcm4354a1_ag.bin /vendor/etc/firmware/
sudo cp nvram_ap6354.txt /vendor/etc/firmware/

# 蓝牙（hci_bcm 默认查找 /lib/firmware/brcm/）
sudo mkdir -p /lib/firmware/brcm
sudo cp BCM4354A2.hcd /lib/firmware/brcm/
```

文件位于 SDK：

```text
external/rkwifibt/firmware/broadcom/all/WIFI_FIRMWARE/fw_bcm4354a1_ag.bin
external/rkwifibt/firmware/broadcom/all/WIFI_FIRMWARE/nvram_ap6354.txt
external/rkwifibt/firmware/broadcom/all/BT_FIRMWARE/BCM4354A2.hcd
```

如果走 upstream `brcmfmac` 路线，则改用 `/lib/firmware/brcm/brcmfmac4354-sdio.bin` + `brcmfmac4354-sdio.txt`，并调整 dts compatible；V1 优先沿用 SDK 的 cywdhd 路线，减少改动。

### 3.4 音频用户态安装

```bash
sudo apt update
sudo apt install -y alsa-utils bluez pulseaudio-module-bluetooth \
  python3 python3-yaml git curl network-manager wpasupplicant
```

CamillaDSP 使用官方 aarch64 预编译包或 `cargo install camilladsp`，安装到 `/usr/local/bin`，用 systemd 管理。

### 3.5 音频链路验证

1. `sudo modprobe snd-aloop`，跑仓库 `scripts/run_validation.sh`；
2. 插入 USB 3 声道声卡，用 `configs/2.1.usb.yml` 验证 L/R/SUB；
3. ALC5651 Line-in 经 `arecord` 验证；
4. 蓝牙 A2DP sink 配对手机，把音频路由到 CamillaDSP 输入；
5. 接 TPA3116 功放，逐通道验证物理声道。

## 4. 风险与注意

| 风险 | 说明 |
| --- | --- |
| rootfs 版本不确定 | `ubuntu_1604.img` 文件名可疑；16.04 已 EOL，若确认是 16.04，需要换成 20.04 镜像 |
| WiFi 芯片型号不确定 | dts 默认 RTL8822CS；如果板子实际是 RTL8822CS，则不需要切 AP6354，直接验证即可 |
| 内核 4.4 较老 | 以厂商 BSP 为基线，不追上游；应用层不依赖内核版本 |
| cywdhd 的 Android 路径 | 驱动默认找 `/vendor/etc/firmware`，Ubuntu 下需要手动建目录；如遇问题再评估 brcmfmac 路线 |

## 5. 与项目里程碑的关系

本文件对应 `docs/roadmap.md` 的 M2（RK3399 平台接入）。完成后即可进入 M3（2.1 硬件与调音）。
