# RK3399 SDK 板级 Bring-up 状态与下一步计划

> 检查日期：2026-08-09（已根据板端确认更新）
> SDK 路径：`Z:\Code\rk3399_linux_sdk_v2.0`  
> 板级配置：`device/rockchip/rk3399/BoardConfig.mk`，`RK_KERNEL_DTS=itop-3399_linux-lvds`

## 1. 板端已确认信息

- Ubuntu 实际版本为 **20.04 无桌面版**；`ubuntu/ubuntu_1604.img` 只是统一刷机时的文件名，不代表系统版本；
- WiFi/蓝牙芯片为 **RTL8822CS**（板载丝印确认），与 SDK 默认设备树一致；
- Ubuntu 系统已成功启动。

## 2. SDK 现状（已确认）

| 项目 | 状态 |
| --- | --- |
| 内核 | 4.4.179（Rockchip BSP），`rockchip_linux_defconfig` |
| 内核构建 | `./build.sh kernel` 等价于 `make ARCH=arm64 rockchip_linux_defconfig && make ARCH=arm64 itop-3399_linux-lvds.img` |
| ALC5651（rt5651） | 驱动已启用（`CONFIG_SND_SOC_RT5651=y`），dts 已配置：`rt5651@1a`（I2C1）、`i2s0`、声卡 `realtek,rt5651-codec` |
| USB Audio | 已启用（`CONFIG_SND_USB_AUDIO=y`） |
| snd-aloop | 未启用，需要打开（用于无硬件回环验证） |
| HDMI 音频 | 通过 i2s2 已启用 |
| SPDIF | dts 中 `status = "disabled"`，需要时再打开 |
| WiFi（RTL8822CS） | dts `wifi_chip_type = "rtl8822cs"`，`CONFIG_RTL8822CS=y` 内置驱动，WiFi 固件内置于驱动源码（`hal8822c_fw.c`），预期 `wlan0` 可直接出现，需板端验证 |
| 蓝牙（RTL8822CS） | 走 Realtek UART H5：SDK 提供预编译 `hci_uart.ko`（`external/rkwifibt/realtek/bluetooth_uart_driver/`）和 `rtk_hciattach` 源码；固件 `rtl8822cs_fw` / `rtl8822cs_config` **未在 SDK 中找到**，需板端确认或向 Realtek/厂商获取 |
| 蓝牙固件路径 | `rtk_hciattach` 固定从 `/lib/firmware/rtlbt/` 读取 `rtl8822cs_fw` 与 `rtl8822cs_config` |
| 蓝牙 UART | dts 使用 uart0（`/dev/ttyS0` 预期）；SDK 里的 `bt_realtek_start` / `rk_wifi_init.c` 默认写的是 `/dev/ttyS4`，板端需以实际设备名为准 |

## 3. 待板端确认/验证

```bash
# WiFi 是否出现
ip link
nmcli dev status
dmesg | grep -iE "wlan|8822|sdio|rtl"

# 蓝牙串口设备名
ls -l /dev/ttyS*

# 蓝牙固件是否已在系统里
ls -l /lib/firmware/rtlbt/
find / -iname "*8822*" 2>/dev/null

# 蓝牙控制器是否出现
hciconfig -a
bluetoothctl list
```

重点确认：

1. `wlan0` 是否存在（存在则 WiFi 无需改内核）；
2. 蓝牙实际挂在哪个 tty（`/dev/ttyS0` 还是 `/dev/ttyS4`）；
3. `/lib/firmware/rtlbt/` 里是否已有 RTL8822CS 固件。

## 4. 下一步开发清单

### 4.1 板端基线确认（不改代码）

```bash
# 音频设备
aplay -l
arecord -l
cat /proc/asound/cards

# 网络
ip addr
ping -c 3 archive.ubuntu.com
```

确认 rt5651 声卡、USB 声卡、WiFi/蓝牙状态，以及 SSH/网络是否可用。

### 4.2 内核调整（当前只需一项）

在 `kernel/arch/arm64/configs/rockchip_linux_defconfig` 中开启：

```text
CONFIG_SND_ALOOP=y
```

WiFi/蓝牙**不需要改 dts**，因为板载芯片与 SDK 默认配置一致（RTL8822CS + `wifi_chip_type = "rtl8822cs"`）；蓝牙走 SDK 提供的 out-of-tree `hci_uart.ko`，也不需要改内核 BT 选项。

重新编译并打包：

```bash
cd /path/to/rk3399_linux_sdk_v2.0
./build.sh kernel
./build.sh firmware
./build.sh updateimg
```

> 5.1/7.1 阶段再评估 `CONFIG_SND_SOC_ROCKCHIP_I2S_TDM=y`，V1 不需要。

### 4.3 RTL8822CS 蓝牙用户态部署

1. 确认/放置固件：

```bash
sudo mkdir -p /lib/firmware/rtlbt
sudo cp rtl8822cs_fw /lib/firmware/rtlbt/
sudo cp rtl8822cs_config /lib/firmware/rtlbt/
```

固件如系统里没有，需要从：

- 原厂 Android 镜像的 `/vendor/etc/firmware/` 或 `/system/etc/firmware/` 提取；
- Realtek/瑞昱官方渠道获取；
- 同型号其它开发板固件中复制。

2. 编译 `rtk_hciattach`（SDK 源码在 `external/rkwifibt/realtek/rtk_hciattach/`，有 Makefile）：

```bash
cd external/rkwifibt/realtek/rtk_hciattach
make CC=aarch64-linux-gnu-gcc   # 或直接在板子上 make
sudo cp rtk_hciattach /usr/local/bin/
```

3. 拷贝蓝牙串口驱动模块：

```bash
sudo cp external/rkwifibt/realtek/bluetooth_uart_driver/hci_uart.ko /lib/modules/$(uname -r)/
sudo depmod -a
```

4. 启动蓝牙（tty 名按板端确认结果替换）：

```bash
sudo modprobe bluetooth
sudo insmod /lib/modules/$(uname -r)/hci_uart.ko
sudo rtk_hciattach -n -s 115200 /dev/ttyS0 rtk_h5 &
sudo hciconfig hci0 up
```

5. 用 BlueZ + PulseAudio（或 PipeWire）配置 A2DP sink，参考 SDK 的 `external/rkwifibt/bt_realtek_start`，但把 `/dev/ttyS4` 改成实际 tty。

### 4.4 WiFi 验证

```bash
ip link set wlan0 up
nmtui   # 或 wpa_supplicant + dhclient
```

若 `wlan0` 不出现，再查 `dmesg`、rfkill 和 dts 电源/复位 GPIO。

### 4.5 音频用户态安装

```bash
sudo apt update
sudo apt install -y alsa-utils bluez pulseaudio-module-bluetooth \
  python3 python3-yaml git curl network-manager wpasupplicant
```

CamillaDSP 使用官方 aarch64 预编译包或 `cargo install camilladsp`，安装到 `/usr/local/bin`，用 systemd 管理。

### 4.6 音频链路验证

1. `sudo modprobe snd-aloop`，跑仓库 `scripts/run_validation.sh`；
2. 插入 USB 3 声道声卡，用 `configs/2.1.usb.yml` 验证 L/R/SUB；
3. ALC5651 Line-in 经 `arecord` 验证；
4. 蓝牙 A2DP sink 配对手机，把音频路由到 CamillaDSP 输入；
5. 接 TPA3116 功放，逐通道验证物理声道。

## 5. 风险与注意

| 风险 | 说明 |
| --- | --- |
| RTL8822CS 蓝牙固件缺失 | SDK 未携带 `rtl8822cs_fw` / `rtl8822cs_config`，需从 Android 镜像或 Realtek 获取 |
| 蓝牙 tty 不确定 | dts 接 uart0，但 SDK 脚本默认 `/dev/ttyS4`，必须以板端 `ls /dev/ttyS*` 为准 |
| 内核 4.4 较老 | 以厂商 BSP 为基线，不追上游；应用层不依赖内核版本 |
| Ubuntu 20.04 的 PipeWire 版本较旧 | V1 可先用 PulseAudio；需要新版 PipeWire 时再评估 PPA/backports |

## 6. 与项目里程碑的关系

本文件对应 `docs/roadmap.md` 的 M2（RK3399 平台接入）。完成后即可进入 M3（2.1 硬件与调音）。
