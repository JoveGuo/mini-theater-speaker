# 声道映射规范

> 状态：草稿（V1 评审稿）

## 1. 目的

统一“逻辑声道”、“ALSA 通道顺序”、“物理扬声器”三者之间的映射关系，避免 2.1 升级 5.1/7.1 时出现声道错乱。

## 2. 逻辑声道命名

系统内部统一使用以下逻辑声道名：

| 名称 | 含义 |
| --- | --- |
| FL | Front Left（左前） |
| FR | Front Right（右前） |
| FC | Front Center（中置） |
| LFE | Low Frequency Effects（低音炮 / .1） |
| BL | Back Left（左后，5.1） |
| BR | Back Right（右后，5.1） |
| SL | Side Left（左侧环绕，7.1） |
| SR | Side Right（右侧环绕，7.1） |
| TFL/TFR | Top Front Left/Right（天空声道，7.1.4） |
| TBL/TBR | Top Back Left/Right（天空声道，7.1.4） |

## 3. 常见布局

### 3.1 2.0 / 2.1

```text
逻辑: FL, FR          (2.0)
逻辑: FL, FR, LFE     (2.1)
物理: 0=FL, 1=FR, 2=LFE
```

### 3.2 5.1（ALSA 标准顺序）

```text
逻辑: FL, FR, FC, LFE, BL, BR
物理: 0=FL, 1=FR, 2=FC, 3=LFE, 4=BL, 5=BR
```

> 注意：ITU 播放习惯顺序为 L R C LFE Ls Rs，与 ALSA 顺序相同；部分源设备可能使用 L R Ls Rs C LFE 等自定义顺序，必须通过输入映射表纠正。

### 3.3 7.1（ALSA 标准顺序）

```text
逻辑: FL, FR, FC, LFE, BL, BR, SL, SR
物理: 0=FL, 1=FR, 2=FC, 3=LFE, 4=BL, 5=BR, 6=SL, 7=SR
```

### 3.4 7.1.4（未来）

```text
地面 8 声道: FL, FR, FC, LFE, BL, BR, SL, SR
天空 4 声道: TFL, TFR, TBL, TBR
```

## 4. 当前 2.1 实现

现有 CamillaDSP 配置使用数字通道号，其含义固定为：

| 通道号 | 逻辑声道 | 物理扬声器 |
| --- | --- | --- |
| 0 | FL | 左卫星 |
| 1 | FR | 右卫星 |
| 2 | LFE | 低音炮 |

`configs/2.1*.yml` 中的 `to_2_1` mixer 即实现 `stereo -> FL/FR/LFE` 的映射。

## 5. 映射规则

1. **输入布局显式声明**：任何输入源都必须声明声道顺序，不允许假设。
2. **输出映射显式声明**：物理通道顺序由配置指定，代码不硬编码。
3. **LFE 语义唯一**：Bass Management 的 SUB 输出与输入源的 LFE 是同一逻辑声道，但处理位置不同：
   - 输入 LFE：源本身携带的低频声道；
   - 输出 SUB：Bass Management 合成的低音炮信号。
4. **未使用声道置静音**：输出通道多于逻辑声道时，未映射通道必须输出静音或禁用，避免噪声。
5. **配置可回放**：每份 profile 必须可生成明确的通道表，便于测试和审计。

## 6. 配置示例

```yaml
channel_map:
  input_layout: [FL, FR]        # 输入是 stereo
  output_layout: [FL, FR, LFE]  # 逻辑输出
  physical:
    - logical: FL
      alsa_channel: 0
    - logical: FR
      alsa_channel: 1
    - logical: LFE
      alsa_channel: 2
```

5.1 示例：

```yaml
channel_map:
  input_layout: [FL, FR, FC, LFE, BL, BR]
  output_layout: [FL, FR, FC, LFE, BL, BR]
  physical:
    - logical: FL
      alsa_channel: 0
    - logical: FR
      alsa_channel: 1
    - logical: FC
      alsa_channel: 2
    - logical: LFE
      alsa_channel: 3
    - logical: BL
      alsa_channel: 4
    - logical: BR
      alsa_channel: 5
```

## 7. 验证方法

- 使用左右声道 1kHz 测试音、50Hz 测试音逐通道注入；
- 用 `aplay -D plughw:CARD=...` 直接播放 6 声道 WAV，确认物理接线顺序；
- 自动化测试断言：`FL` 声道信号只能出现在物理通道 0，`LFE` 只能出现在 SUB 通道等。
