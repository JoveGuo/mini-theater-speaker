# Linux 系统选型

> 状态：建议稿，待 V1 评审确认  
> 结论：**Ubuntu LTS（arm64）rootfs + 厂商 BSP 内核**（Debian 同源，作为备选）

## 1. 需求约束

本项目对 Linux 系统的核心诉求：

- 快速迭代：经常安装/更新音频栈（BlueZ、PipeWire、ALSA）、Python、Web 组件；
- 成熟的音频生态：A2DP、USB Audio、I2S、S/PDIF、CamillaDSP；
- 厂商 BSP 支持：RK3399 的 ALC5651、AP6354 需要厂商内核/固件；
- 可产品化：systemd 服务、看门狗、后续 OTA；
- 换 SoC 友好：应用层和音频管线不应绑定某个发行版。

## 2. 方案对比

| 维度 | Buildroot | Debian | Ubuntu | Yocto | OpenWrt |
| --- | --- | --- | --- | --- | --- |
| 开发迭代速度 | 慢，改包需重新构建 | 快，apt 即装即用 | 快 | 慢，bitbake 全量构建 | 中 |
| 音频/蓝牙生态 | 需手工集成，PipeWire/CamillaDSP 不在默认包集 | 好：bluez、pipewire、alsa-utils 都有 | 好，版本较新 | 可控，但需自己写 recipe | 差，面向路由/网关 |
| BSP/驱动适配 | 需自行集成厂商内核 | 可用厂商 BSP 内核 + Debian rootfs | 同左，镜像更重 | 需厂商 layer 或自维护 | 不适合 |
| 镜像体积 | 最小 | 小~中（minimal 约 300MB） | 较大 | 可裁剪 | 最小 |
| 量产/OTA | swupdate 可行，工作量大 | apt/RAUC/swupdate 都可行 | snap/apt | RAUC/swupdate 成熟 | opkg |
| 团队门槛 | 中-高 | 低 | 低 | 高 | 中 |
| 适合场景 | 功能定型后的批量生产 | 开发验证 + 中小批量产品 | 开发验证 | 大型产品线、强可复现性要求 | 路由器/网关 |

## 3. 推荐方案

**Ubuntu 24.04 LTS（arm64）minimal + iTOP/Rockchip BSP 内核**

理由：

1. **与现有经验匹配**：Android 开发环境的主机通常就是 Ubuntu，`apt`、系统命令和排错思路可以直接平移，学习成本最低；
2. **技术栈匹配**：BlueZ、PipeWire、ALSA、Python3 都是 apt 包；CamillaDSP 用官方 aarch64 预编译包或 `cargo install`，不依赖发行版仓库；
3. **生态与资料最多**：Ubuntu 教程、论坛和厂商资料最丰富，遇到问题最容易搜到答案；
4. **镜像来源充足**：iTOP-3399 官方提供 Ubuntu 镜像；Armbian 也提供 RK3399 的 Ubuntu 24.04 minimal 镜像可做内核/rootfs 参照；
5. **内核策略清晰**：保留厂商 BSP 内核（确保 ALC5651/AP6354 驱动和固件可用），只替换 rootfs 为 Ubuntu minimal；
6. **支持期明确**：Ubuntu 24.04 LTS 标准支持至 2029，Ubuntu Pro 可延至 2034；26.04 LTS 支持至 2031/2036；
7. **产品化路径平滑**：先 Ubuntu 跑通，若未来出货量大、定制深，再迁移 Yocto/Buildroot；应用层和音频 profile 不受影响。

> Debian 与 Ubuntu 同源，apt 命令、软件包和系统结构几乎一致；如果后续发现 Ubuntu 太重或想要更保守的基线，切回 Debian 的成本很低。

## 4. 备选与排除

| 系统 | 结论 | 原因 |
| --- | --- | --- |
| Debian | 备选 | 与 Ubuntu 同源、更轻、更保守；切换成本低 |
| Yocto | 量产阶段再评估 | 可复现性和裁剪最好，但开发周期长，V1 阶段过重 |
| Buildroot | 量产阶段再评估 | 镜像最小，但音频/Web/Python 生态维护成本高 |
| OpenWrt | 排除 | 面向网络设备，Bluetooth A2DP、PipeWire、CamillaDSP 生态差 |

## 5. 落地建议

```text
BSP 内核（厂商 SDK / Armbian 内核）
  + Ubuntu 24.04 LTS arm64 minimal rootfs
  + bluez / pipewire / wireplumber / alsa-utils / python3
  + CamillaDSP（官方预编译或 cargo，固定版本）
  + systemd 服务（camilladsp、theaterd、monitor）
```

优先检查 iTOP 光盘/SDK 是否提供现成 Ubuntu 镜像：有则先烧录跑通硬件；若版本过旧（如 16.04），再用厂商 BSP 内核 + Ubuntu 24.04 minimal rootfs 重建。

V1 阶段以“能跑通、能快速改”优先；量产化时再决定是否需要 Yocto/Buildroot。

## 6. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| BSP 内核版本较旧 | 不追上游内核，以厂商 SDK 为基线；应用层不依赖具体内核版本 |
| CamillaDSP 不在 Ubuntu 仓库 | 使用官方发布包或 cargo，锁定版本并做校验 |
| AP6354 固件/NVRAM 依赖厂商 | 保留 BSP 中的固件与设备树配置 |
| OTA 尚未规划 | 产品化阶段评估 RAUC/swupdate 或自建 apt 仓库 |

## 7. 为什么不用 Android（即使板子现成）

用户当前板卡刷的是 Android 8，开发环境也已搭好，但本项目**不建议以 Android 作为运行底座**：

| 障碍 | 说明 |
| --- | --- |
| DSP 引擎不兼容 | CamillaDSP 是 Linux 用户态程序，依赖 ALSA/PipeWire；Android 用 AudioFlinger/Audio HAL 独占音频设备，无法直接跑现有管线 |
| A2DP sink 需要厂商补丁 | Android 默认是 A2DP source（把声音发给耳机/音箱），要做“蓝牙音箱”接收手机音频，需要改 Rockchip SDK 的 `profile_supported_a2dp_sink` 并重新编译，版本脆弱 |
| 多声道与自定义 DSP 受限 | USB 3/6/8 声道输出、Bass Management、每声道 EQ 都不是 Android 正常支持路径，需要重写 Audio HAL |
| 控制面不透明 | IR/GPIO/看门狗/Web UI 用 Android init + Java 框架实现更重，迭代更慢 |
| 系统老旧 | Android 8（2017）早已停止维护，蓝牙与音频栈陈旧，不适合作为新产品基线 |

**Android 开发环境仍有价值**，但用途应该放在：

- 编译/提取 BSP 内核、设备树、AP6354/ALC5651 固件；
- 后续开发手机端遥控 App（通过 HTTP/WebSocket 控制 Linux DSP）；
- 双系统模式下保留 eMMC Android 作为备选或演示系统。

推荐的过渡方案：**保留 eMMC 上的 Android，从 SD 卡启动 Ubuntu**（见 `docs/linux_rk3399_setup.md`），既不影响现有环境，又能以最快速度进入我们的音频管线开发。
