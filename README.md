# HiFi 回音壁 2.1 软件验证

这是一个从零开始的 HiFi 回音壁项目，当前阶段目标是先用最低硬件成本跑通 2.1 声道软件信号链：左右卫星音箱 + 低音炮。第一阶段不追求成品音质、杜比解码或量产外壳，只验证 DSP 架构、分频、低音管理、输入路由和调参流程。

## 当前信号链

```text
USB PCM / 蓝牙 A2DP / eARC PCM (立体声)
  -> CamillaDSP 低音管理
  -> L/R 高通 + 低音低通
  -> EQ / 延迟 / 限幅
  -> 3 通道输出: L, R, SUB
  -> USB 2.1/5.1 声卡 -> TPA3116 2.1 功放 -> 卫星音箱 + 低音炮
```

DSP 配置使用 [CamillaDSP](https://github.com/HEnquist/camilladsp)，默认分频点为 100Hz Linkwitz-Riley 4 阶。声道定义为 `0 = L`、`1 = R`、`2 = SUB`。

## 仓库结构

```text
configs/                 CamillaDSP YAML 配置
docs/                    信号链、测量方法和硬件清单
scripts/                 测试音生成、配置校验、信号链模拟
tests/                   无第三方依赖的自动化验证# HiFi 回音壁 2.1 软件验证

这是一个从零开始的 HiFi 回音壁项目，当前阶段目标是先用最低硬件成本跑通 2.1 声道软件信号链：左右卫星音箱 + 低音炮。第一阶段不追求成品音质、杜比解码或量产外壳，只验证 DSP 架构、分频、低音管理、输入路由和调参流程。

## 当前信号链

```text
USB PCM / 蓝牙 A2DP / eARC PCM (立体声)
  -> CamillaDSP 低音管理
  -> L/R 高通 + 低音低通
  -> EQ / 延迟 / 限幅
  -> 3 通道输出: L, R, SUB
  -> USB 2.1/5.1 声卡 -> TPA3116 2.1 功放 -> 卫星音箱 + 低音炮
```

DSP 配置使用 [CamillaDSP](https://github.com/HEnquist/camilladsp)，默认分频点为 100Hz Linkwitz-Riley 4 阶。声道定义为 `0 = L`、`1 = R`、`2 = SUB`。

## 仓库结构

```text
configs/                 CamillaDSP YAML 配置
docs/                    信号链、测量方法和硬件清单
scripts/                 测试音生成、配置校验、信号链模拟
tests/                   无第三方依赖的自动化验证
assets/test_tones/       生成的 WAV 测试音
build/                   运行产生的原始 PCM 和输出文件（不入库）
```

## 快速验证

先运行完整验证脚本：

```bash
bash scripts/run_validation.sh
```

它会生成测试音、校验 YAML 配置，并运行 2.1 信号链模拟测试。整个过程不需要 CamillaDSP 或任何音频硬件。

手动执行等价步骤：

```bash
python3 scripts/generate_test_tones.py --with-raw
python3 scripts/validate_config.py configs/2.1.yml configs/2.1.stdin.yml configs/2.1.file.yml
python3 -m unittest discover -s tests -p "test_*.py"
```

## 接入真实音频链路

1. 从 CamillaDSP 官方 Releases 下载对应系统二进制，或使用 `cargo install camilladsp`。
2. RK3399 Linux 板卡直接使用 `configs/2.1.usb.yml`，把 ALSA 设备名改成实际声卡，例如 `plughw:CARD=USB,DEV=0`；详细步骤见 `docs/linux_rk3399_setup.md`。
3. 先使用 `configs/2.1.stdin.yml` 用管道验证，再切换到真实声卡。
4. 安装 [CamillaGUI](https://github.com/HEnquist/camillagui-backend) 后，通过浏览器实时调整分频、延迟和 EQ。

## 第二阶段

立体声 2.1 验证通过后，再扩展 USB 5.1/7.1 PCM、eARC 多声道、多单元回音壁阵列和虚拟环绕。

assets/test_tones/       生成的 WAV 测试音
build/                   运行产生的原始 PCM 和输出文件（不入库）
```

## 快速验证

先运行完整验证脚本：

```bash
bash scripts/run_validation.sh
```

它会生成测试音、校验 YAML 配置，并运行 2.1 信号链模拟测试。整个过程不需要 CamillaDSP 或任何音频硬件。

手动执行等价步骤：

```bash
python3 scripts/generate_test_tones.py --with-raw
python3 scripts/validate_config.py configs/2.1.yml configs/2.1.stdin.yml configs/2.1.file.yml
python3 -m unittest discover -s tests -p "test_*.py"
```

## 接入真实音频链路

1. 从 CamillaDSP 官方 Releases 下载对应系统二进制，或使用 `cargo install camilladsp`。
2. RK3399 Linux 板卡直接使用 `configs/2.1.usb.yml`，把 ALSA 设备名改成实际声卡，例如 `plughw:CARD=USB,DEV=0`；详细步骤见 `docs/linux_rk3399_setup.md`。
3. 先使用 `configs/2.1.stdin.yml` 用管道验证，再切换到真实声卡。
4. 安装 [CamillaGUI](https://github.com/HEnquist/camillagui-backend) 后，通过浏览器实时调整分频、延迟和 EQ。

## 第二阶段

立体声 2.1 验证通过后，再扩展 USB 5.1/7.1 PCM、eARC 多声道、多单元回音壁阵列和虚拟环绕。
