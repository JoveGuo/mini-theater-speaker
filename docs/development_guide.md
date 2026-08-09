# 开发指南

## 1. 仓库结构

```text
configs/                 CamillaDSP 配置
docs/                    设计文档
scripts/                 测试音、校验、模拟脚本
tests/                   自动化测试
assets/test_tones/       生成的 WAV 测试音
build/                   运行产物（不入库）
```

## 2. 分支与提交

- 当前开发分支：`theater_2.1_V1.0`；
- 新工作先开短生命周期分支：
  - `docs/*`：文档；
  - `feat/*`：功能；
  - `fix/*`：修复；
- 提交信息用中文或英文均可，但需说明“改了什么、为什么”；
- 涉及配置变更时，提交说明必须包含通道映射变化。

## 3. 文档规范

- 文档统一 UTF-8、Markdown；
- 新增功能必须先更新对应设计文档再写代码（或同步提交）；
- 相对链接使用 `docs/xxx.md` 形式；
- 管线相关变更必须同步更新：
  - `docs/audio_pipeline.md`
  - `docs/channel_mapping.md`
  - `docs/config_spec.md`

## 4. 代码规范

- Python 使用 `python3` + 标准库优先，减少运行时依赖；
- 新增 DSP/路由代码不得硬编码声道编号，必须读取配置；
- 声道名统一使用 `FL/FR/FC/LFE/BL/BR/SL/SR`；
- 日志使用结构化文本，便于 `journalctl` 排查。

## 5. 质量门禁

提交前必须通过：

```bash
bash scripts/run_validation.sh
```

该命令会：

1. 生成测试音；
2. 校验全部 CamillaDSP 配置；
3. 运行信号链自动化测试。

新增/修改配置后，必须补充对应的校验规则（`scripts/validate_config.py`）。该脚本优先使用 PyYAML；在未安装 PyYAML/Ruby 的环境下，会使用内置的精简 YAML 解析器处理本仓库的配置子集。

## 6. 新增一个声道 profile 的检查清单

以新增 5.1 为例：

- [ ] 定义 `channel_map`（输入布局、输出布局、物理映射）；
- [ ] 更新 Bass Management 求和集合；
- [ ] 更新 `docs/channel_mapping.md`；
- [ ] 更新 `docs/config_spec.md` 示例；
- [ ] 生成引擎配置并放入 `configs/`；
- [ ] 更新 `validate_config.py` 校验规则；
- [ ] 生成 6 声道测试音并增加路由测试；
- [ ] 在硬件上逐通道验证物理接线。

## 7. 协作流程

1. 在 Issue/任务中明确范围；
2. 从 `theater_2.1_V1.0` 切分支；
3. 实现并自测；
4. 提交 PR，附测试结果；
5. 评审通过后合并；
6. 里程碑退出条件满足后打 tag。
