# RK3399 Linux 板卡接入指南

## 为什么可用

RK3399 是双 Cortex-A72 + 四 Cortex-A53，跑 CamillaDSP 的 2.1 分频、EQ、低音管理和限幅绰绰有余；后续 5.1/7.1 虚拟环绕也可先用它做算法验证。第一阶段不需要换 RK3588 或 Pi 4B。

## 硬件连接

```text
RK3399 Linux 板卡
  USB 口 -> USB 2.1/5.1 声卡
  声卡 3 路模拟输出 -> TPA3116 2.1 功放
  功放 -> 左卫星 + 右卫星 + 低音炮
```

## 系统准备

1. 使用配套 Linux SDK 编译并烧录系统。
2. 确认系统已启动并连接网络。
3. 插入 USB 2.1/5.1 声卡，执行：

```bash
aplay -l
arecord -l
```

4. 记录声卡名称，例如 `plughw:CARD=USB,DEV=0`。
5. 安装依赖：

```bash
sudo apt update
sudo apt install -y python3 python3-yaml git curl
```

6. 安装 CamillaDSP。优先使用官方 aarch64 Linux 预编译包，或使用 `cargo install camilladsp`。

## 运行验证

把仓库同步到板卡后：

```bash
cd Theater_speaker_projects
bash scripts/run_validation.sh
```

这会生成测试音、校验配置并运行信号链模拟。然后编辑 `configs/2.1.usb.yml`，把 `plughw:CARD=USB,DEV=0` 改成实际声卡名称，再启动 CamillaDSP 加载该配置。

## ALSA 回环验证

如果暂时没有声卡，可以加载 ALSA 回环模块，用 `configs/2.1.yml` 做无硬件验证：

```bash
sudo modprobe snd-aloop
```

## 蓝牙输入

在 RK3399 Linux 上使用 BlueZ + PipeWire 配置 A2DP sink，然后把蓝牙音频路由到 CamillaDSP 的输入节点。首版使用 SBC/AAC，LDAC 后续评估。
