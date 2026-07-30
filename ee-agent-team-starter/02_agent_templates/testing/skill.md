---
name: Testing & Validation Agent Skills
description: |
  测试验证专家Agent的专业技能定义、工具使用规范、工作流程和输入输出标准。
  遵循Kimi/Hermes Agent Skill标准，包含与其他Agent的明确协作接口。
version: 1.0.0
author: ITC Enterprise Agent System
---

# Skill: 测试验证专家 Agent

## 技能总览

```yaml
技能域:
  - 测试用例生成
  - 音频性能测试
  - 声学特性测试
  - 环境可靠性测试
  - 自动化测试框架
  - 测试数据分析
  - 跨域协作接口

技能标准: Kimi/Hermes Agent Skill Specification v1.0
认证级别: L3 (专家级)
```

---

## 技能1: 测试用例生成方法 `SKILL-TST-001`

### 概述
系统化生成高质量测试用例，确保测试覆盖完整、边界条件充分、场景真实。

### 测试设计方法

#### 1.1 等价类划分

```yaml
method: Equivalence Partitioning

rules:
  - 有效等价类: 满足规格要求的输入集合，至少1个用例
  - 无效等价类: 不满足规格要求的输入集合，每个类型至少1个用例
  
example_frequency_response:
  parameter: 输入频率 (Hz)
  valid_classes:
    - class: "低频段"
      range: [20, 200]
      samples: [20, 50, 100, 200]
    - class: "中频段"
      range: [200, 5000]
      samples: [250, 1000, 3150, 5000]
    - class: "高频段"
      range: [5000, 20000]
      samples: [6300, 10000, 16000, 20000]
  invalid_classes:
    - class: "超低频"
      range: [<20]
      samples: [10, 15]
    - class: "超高频"
      range: [>20000]
      samples: [22000, 25000]
    - class: "无效输入"
      values: [0, -100, null]
```

#### 1.2 边界值分析

```yaml
method: Boundary Value Analysis

rules:
  - 取边界值及边界两侧各1个值
  - 如果输入是范围，取: min-1, min, min+1, max-1, max, max+1
  - 如果输入是集合，取: 第一个、最后一个、空集、超集
  
example_power_test:
  parameter: 输入功率 (W)
  specification: [0.1, 50]
  boundary_values:
    - 0.05 (低于最小值)
    - 0.1 (最小值)
    - 0.15 (最小值+)
    - 25 (中值)
    - 49 (最大值-)
    - 50 (最大值)
    - 55 (超过最大值)
  
  special_boundaries:
    - 0 (零功率 — 静音测试)
    - 100%_rated (额定功率)
    - 110%_rated (过载测试)
    - clip_point (削波点)
```

#### 1.3 场景测试

```yaml
method: Scenario Testing

scenarios_catalog:
  category_power_on:
    - "冷启动: 室温20°C，首次上电"
    - "热启动: 连续工作4小时后重启"
    - "快速开关: 1秒内关-开-关-开"
    - "低电压启动: 供电电压为额定值90%"
    - "过压保护: 供电电压为额定值120%"
    
  category_signal:
    - "标准信号: 1kHz正弦波@额定功率"
    - "音乐信号: 粉红噪声/真实音乐片段"
    - "突发信号: 10ms burst@最大功率"
    - "扫频信号: 20Hz-20kHz对数扫频"
    - "直流偏移: 含50mV直流偏移的信号"
    
  category_environment:
    - "标准环境: 23°C ± 5°C, 45-75%RH"
    - "低温工作: 0°C启动并运行"
    - "高温工作: 40°C连续运行"
    - "高湿环境: 40°C/93%RH"
    - "温度冲击: -10°C ↔ +40°C, 转换<5min"
    
  category_user:
    - "最大音量连续播放8小时"
    - "频繁音量调节 (每10秒调节一次)"
    - "多设备切换 (蓝牙/AUX/光纤轮换)"
    - "异常操作: 所有按键同时按下"
```

#### 1.4 测试用例模板

```yaml
test_case_template:
  case_id: "TC-AUD-001"
  title: "频率响应测试 - 1W额定条件下20Hz-20kHz频响平坦度"
  priority: P1 (阻塞性)
  category: "音频性能"
  
  preconditions:
    - 样品预热30分钟
    - 标准环境条件 (23±5°C, 45-75%RH)
    - APx515校准有效期内
    - 样品SN记录完成
    
  test_steps:
    1. "连接样品至APx515: 样品输出→APx模拟输入"
    2. "设置信号源: 对数扫频20Hz-20kHz, 1W@4Ω等效电压"
    3. "执行频率响应测量 (RMS方法)"
    4. "记录左通道频响曲线数据"
    5. "记录右通道频响曲线数据"
    6. "计算相对于1kHz的dB偏差"
    
  expected_results:
    - "20Hz-20kHz频响相对于1kHz: -3dB ~ +3dB"
    - "左右通道差异: ≤1dB (20Hz-20kHz)"
    - "无明显峰值 (>+5dB) 或谷值 (<-6dB)"
    
  pass_criteria:
    - "所有频率点在规格范围内 → Pass"
    - "任何频率点超出规格 → Fail"
    - "左右通道差异>1.5dB → 标记为观察项"
    
  test_data_recording:
    - "频响曲线原始数据 (.csv)"
    - "关键频率点表格 (20/50/100/1k/5k/10k/20k Hz)"
    - "左右通道差异曲线"
    
  related_spec: "SPEC-AUD-001"
  related_requirement: "REQ-SYS-012"
  automation_status: "已自动化 (script: test_freq_response.py)"
```

### 测试用例分级

| 优先级 | 分类 | 执行时机 | 覆盖率目标 |
|--------|------|----------|------------|
| P0 | 冒烟测试 | 每次构建 | 核心功能100% |
| P1 | 阻塞性 | 每轮完整测试 | 规格要求100% |
| P2 | 重要 | 里程碑测试 | 主要场景100% |
| P3 | 一般 | 回归测试/时间允许 | 典型场景覆盖 |
| P4 | 次要 | 按需 | 可选补充 |

---

## 技能2: 音频性能测试流程 `SKILL-TST-002`

### 概述
使用Audio Precision等精密仪器执行标准化音频性能测试，获取频率响应、THD+N、动态范围等关键指标。

### 标准测试项目

#### 2.1 频率响应测试 (Frequency Response)

```yaml
test_id: "AUD-001"
name: "频率响应"
standard: "IEC 60268-5, AES17"
instrument: "Audio Precision APx515 或同等级"

procedure:
  1. 连接: 被测设备输出 → APx模拟输入 (平衡或非平衡)
  2. 设置参考电平: 1kHz @ rated_power × 0.1 (通常)
  3. 测量信号: 对数扫频 20Hz - 20kHz
  4. 记录: 幅度vs频率曲线
  5. 归一化: 相对于1kHz电平的dB偏差
  
specification_template:
  pass_band: "20Hz - 20kHz"
  deviation_limit: "±3dB (相对于1kHz)"
  channel_balance: "≤1dB (L-R, 20Hz-20kHz)"
  
reporting:
  - 频响曲线图 (dB vs Hz, 对数频率轴)
  - 关键频率点数值表
  - 左右通道差异图
  - 与规格限的对比图
```

#### 2.2 THD+N测试 (Total Harmonic Distortion + Noise)

```yaml
test_id: "AUD-002"
name: "总谐波失真加噪声"
standard: "IEC 60268-5, AES17"
instrument: "Audio Precision APx515 或同等级"

procedure:
  1. 设置测量带宽: 20Hz - 20kHz (AES17 brickwall filter)
  2. 设置测量方法: "THD+N Amplitude" (含噪声)
  3. 测量点:
     - 功率扫描: 0.01W → rated_power → clip_point
     - 频率点: 20Hz, 50Hz, 100Hz, 1kHz, 5kHz, 10kHz
  4. 记录: THD+N(%) vs 功率/频率
  
specification_template:
  at_1w_1khz: "<0.1% (-60dB)"
  at_rated_power_1khz: "<0.5% (-46dB)"
  at_100hz_1w: "<0.2% (-54dB)"  # 低频通常较高
  
reporting:
  - THD+N vs 功率曲线 (1kHz)
  - THD+N vs 频率曲线 (1W)
  - 频谱图 (显示各次谐波分量)
  - 与规格限对比表
```

#### 2.3 动态范围测试 (Dynamic Range)

```yaml
test_id: "AUD-003"
name: "动态范围"
standard: "AES17"
instrument: "Audio Precision APx515 或同等级"

procedure:
  method: "AES17 CCIF-IMD derived"
  1. 输入: -60dBFS CCIF双音信号 (19kHz + 20kHz)
  2. 测量: 20kHz附近的噪声+失真
  3. 计算: 动态范围 = 满幅dB - (-60dBFS处测得的dB)
  
  alternative_method: "THD+N at -60dBFS"
  1. 输入: -60dBFS 1kHz正弦波
  2. 测量: THD+N
  3. 动态范围 = 20 × log10(1 / THD+N_ratio) + 60dB
  
specification_template:
  min_dynamic_range: ">90dB (A-weighted)"
  typical: ">95dB"
  
reporting:
  - 动态范围数值 (dB A-weighted)
  - 测量方法说明
  - 频谱图证据
```

#### 2.4 信噪比测试 (Signal-to-Noise Ratio)

```yaml
test_id: "AUD-004"
name: "信噪比"
standard: "IEC 60268-5"
instrument: "Audio Precision APx515 或同等级"

procedure:
  1. 测量参考输出: 1kHz @ rated_power, 记录电平Vref
  2. 断开信号源/静音输入
  3. 测量输出噪声: A-weighted and unweighted
  4. SNR = 20 × log10(Vref / Vnoise)
  
specification_template:
  snr_a_weighted: ">90dB"
  snr_unweighted: ">85dB"
  
reporting:
  - SNR(A) 和 SNR(未计权) 数值
  - 噪声频谱图
  -  hum_components: 50/100/150Hz 噪声检查
```

#### 2.5 串扰测试 (Crosstalk)

```yaml
test_id: "AUD-005"
name: "通道串扰"
standard: "IEC 60268-5"
instrument: "Audio Precision APx515 或同等级"

procedure:
  1. 左通道输入1kHz @ rated_power
  2. 右通道静音/接地
  3. 测量右通道输出电平
  4. 串扰 = 20 × log10(V_right / V_left)
  5. 重复反向 (右→左)
  6. 扩展频率: 100Hz, 1kHz, 10kHz
  
specification_template:
  at_1khz: "<-70dB"
  at_10khz: "<-60dB"
  
reporting:
  - 串扰 vs 频率曲线
  - L→R 和 R→L 数值
```

### 音频测试完整项目清单

| 测试ID | 测试项目 | 标准 | 自动化 | 优先级 |
|--------|----------|------|--------|--------|
| AUD-001 | 频率响应 | IEC 60268-5 | 是 | P1 |
| AUD-002 | THD+N vs 功率 | IEC 60268-5 | 是 | P1 |
| AUD-003 | THD+N vs 频率 | IEC 60268-5 | 是 | P1 |
| AUD-004 | 动态范围 | AES17 | 是 | P1 |
| AUD-005 | 信噪比 | IEC 60268-5 | 是 | P1 |
| AUD-006 | 通道串扰 | IEC 60268-5 | 是 | P1 |
| AUD-007 | 增益误差 | 内部标准 | 是 | P2 |
| AUD-008 | 通道平衡 | IEC 60268-5 | 是 | P1 |
| AUD-009 | 互调失真 (IMD) | IEC 60268-5 | 是 | P2 |
| AUD-010 | 直流偏移 | 内部标准 | 是 | P2 |
| AUD-011 | 输出阻抗 | IEC 60268-5 | 是 | P3 |
| AUD-012 | 最大输出电平 | IEC 60268-5 | 是 | P1 |
| AUD-013 | 残余噪声 | 内部标准 | 是 | P2 |
| AUD-014 | 电源纹波抑制 | 内部标准 | 否 | P2 |

---

## 技能3: 声学测试流程 `SKILL-TST-003`

### 概述
在消声室或标准声学环境中测量声学特性，包括声压级、指向性、阻抗等。

#### 3.1 消声室测试

```yaml
environment: "半消声室 (Hemi-anechoic chamber)"
background_noise: "<20dBA"
cutoff_frequency: "<100Hz"
temperature: "23±2°C"
humidity: "50±20%RH"

measurement_system:
  microphone: "B&K 4190 或同等级1/2英寸测量传声器"
  mic_preamp: "B&K 2669"
  audio_interface: "RME Fireface UFX+ 或同等级"
  analysis_software: "Listen SoundCheck / Klippel NFS / REW"
  
microphone_positions:
  far_field: 
    distance: "1.0m from acoustic center"
    height: "tweeter height"
    angles: "0°, ±15°, ±30°, ±45°, ±60°, ±75°, ±90° (水平)"
    
  near_field:
    distance: "<0.1m from each driver"
    purpose: "低频单元独立响应 (避开房间影响)"

standard_tests:
  on_axis_response:
    name: "轴向频率响应"
    signal: "对数扫频 20Hz-20kHz"
    level: "94dB SPL @ 1m (标准) 或 rated_power"
    output: "SPL(dB) vs Frequency(Hz)"
    
  off_axis_response:
    name: "偏轴频率响应"
    angles: "0°, ±15°, ±30°, ±45°, ±60°, ±90°"
    purpose: "评估指向性和听音窗口"
    output: "极坐标图 / 瀑布图"
    
  directivity_index:
    name: "指向性指数"
    calculation: "DI = 10×log10(轴向功率/全空间平均功率)"
    output: "DI(dB) vs Frequency"
    
  impedance:
    name: "阻抗曲线"
    method: "恒流法或电压比法"
    range: "20Hz-20kHz"
    output: "|Z|(Ω) + Phase(°) vs Frequency"
    parameters: "Re, Fs, Qms, Qes, Qts, Vas"
```

#### 3.2 声压级测试

```yaml
test_id: "ACO-001"
name: "最大声压级 (Maximum SPL)"
standard: "AES2-2012 / IEC 60268-5"

procedure:
  1. 测量位置: 1m, on-axis
  2. 信号: 粉红噪声 (IEC 60268-1 标准谱形)
  3. 方法: 逐渐增加电平至规定失真限值
  4. 记录: 长期SPL (continuous) 和短期SPL (peak)
  
specification_template:
  max_spl_continuous: ">95dB @ 1m (IEC pink noise, THD<3%)"
  max_spl_peak: ">100dB @ 1m"
  
reporting:
  - SPL数值 (dB, 计权方式标注)
  - 对应THD+N水平
  - 限制因素说明 (功放限制/单元限制)
```

#### 3.3 长时间稳定性测试

```yaml
test_id: "ACO-002"
name: "功率压缩与热稳定性"
standard: "AES2-2012"

procedure:
  1. 信号: 粉红噪声 IEC标准谱
  2. 初始测量: 94dB SPL @ 1m 时的频响 (基准)
  3. 连续播放: rated_power × 0.5 (长期功率)
  4. 定时测量: 每10分钟测量频响 (持续8小时)
  5. 计算: 各频率点的SPL变化 (压缩)
  
pass_criteria:
  max_compression: "<3dB @ any frequency"
  thermal_recovery: "<1dB difference after 1h cooldown"
  
reporting:
  - SPL变化 vs 时间曲线
  - 压缩量 vs 频率曲线
  - 热恢复验证数据
```

---

## 技能4: 环境可靠性测试 `SKILL-TST-004`

### 概述
模拟产品在实际使用和运输中可能遇到的各种环境应力，验证产品可靠性。

#### 4.1 温度测试

```yaml
test_id: "ENV-001"
name: "高温工作测试"
standard: "IEC 60068-2-2 (Test Bd)"

procedure:
  1. 样品在室温下功能检查 (Pass)
  2. 放入温箱，设定 +40°C (或规格值)
  3. 温度稳定后 (通常2h)，上电工作
  4. 持续工作 16h (或规格值)
  5. 期间每2h进行功能检查
  6. 结束后恢复室温2h，最终功能检查
  
pass_criteria:
  - "全程功能正常"
  - "音频性能变化 < ±1dB (相对于室温基准)"
  - "无结构变形、无材料软化/变色"
  - "无异常噪声、无保护误触发"
```

```yaml
test_id: "ENV-002"
name: "低温工作测试"
standard: "IEC 60068-2-1 (Test Ad)"

procedure:
  1. 样品在室温下功能检查
  2. 放入温箱，设定 0°C (或规格值，如-10°C)
  3. 温度稳定2h后上电
  4. 持续工作 4h
  5. 期间每1h功能检查
  6. 结束后恢复室温，最终检查
  
pass_criteria:
  - "全程功能正常"
  - "启动时间 < 30s (从低温启动)"
  - "音频性能变化 < ±1.5dB"
  - "无冷凝水侵入 (如适用)"
```

#### 4.2 湿热测试

```yaml
test_id: "ENV-003"
name: "恒定湿热测试"
standard: "IEC 60068-2-78 (Test Cab)"

procedure:
  conditions: "40°C / 93%RH"
  duration: "96h (4天)"
  powered: "非工作状态 (unpowered)"
  
  steps:
    1. 初始检查和测量
    2. 放入恒温恒湿箱，设定条件
    3. 96h后取出，在标准环境下恢复2h
    4. 最终功能检查和测量
    5. 拆解检查内部是否有凝露/腐蚀
    
pass_criteria:
  - "功能正常"
  - "绝缘电阻 > 2MΩ"
  - "内部无可见凝露/腐蚀"
  - "外观无起泡/变色"
```

#### 4.3 振动测试

```yaml
test_id: "ENV-004"
name: "随机振动测试 (运输)"
standard: "IEC 60068-2-64 (Test Fh)"

procedure:
  1. 样品按运输包装状态固定于振动台
  2. 测试条件 (非包装产品):
     frequency: "5-500Hz"
     psd: "1.5g rms"
     duration: "每轴2h (X/Y/Z三轴共6h)"
  3. 测试前后功能检查
  4. 测试后拆解检查内部松动/损伤
  
pass_criteria:
  - "全程功能正常"
  - "无结构松动/脱落"
  - "无焊点开裂/器件脱落"
  - "性能变化 < ±1dB"
```

#### 4.4 跌落测试

```yaml
test_id: "ENV-005"
name: "自由跌落测试"
standard: "IEC 60068-2-32 (Test Ed)"

procedure:
  1. 样品按运输包装状态 (或裸机，依规格)
  2. 从指定高度自由跌落到水泥地面
  3. 跌落面顺序:
     - 1次: 底面
     - 1次: 顶面
     - 1次: 前面
     - 1次: 后面
     - 1次: 左面
     - 1次: 右面
     - 1次: 角跌落 (最脆弱角)
  height: "1.0m (或规格值)"
  
pass_criteria:
  - "功能正常"
  - "无影响安全的裂纹/锐边"
  - "无内部器件脱落/短路风险"
  - "外观损伤在允许范围内"
```

### 环境测试项目矩阵

| 测试ID | 测试项目 | 标准 | 条件 | 时长 | 优先级 |
|--------|----------|------|------|------|--------|
| ENV-001 | 高温工作 | IEC 60068-2-2 | +40°C | 16h | P1 |
| ENV-002 | 低温工作 | IEC 60068-2-1 | 0°C | 4h | P1 |
| ENV-003 | 恒定湿热 | IEC 60068-2-78 | 40°C/93%RH | 96h | P1 |
| ENV-004 | 随机振动 | IEC 60068-2-64 | 5-500Hz, 1.5g | 6h(三轴) | P1 |
| ENV-005 | 自由跌落 | IEC 60068-2-32 | 1.0m | 7次 | P1 |
| ENV-006 | 温度循环 | IEC 60068-2-14 | -10°C↔+40°C | 10 cycles | P2 |
| ENV-007 | 高温贮存 | IEC 60068-2-2 | +55°C | 72h | P2 |
| ENV-008 | 低温贮存 | IEC 60068-2-1 | -20°C | 72h | P2 |
| ENV-009 | 盐雾测试 | IEC 60068-2-11 | 5% NaCl, 35°C | 48h | P2 (户外产品) |
| ENV-010 | UV老化 | ISO 4892 | UV-B, 60°C | 500h | P3 (户外产品) |

---

## 技能5: 自动化测试框架 `SKILL-TST-005`

### 概述
基于Python的自动化测试框架，集成Audio Precision仪器，实现高效、可重复的批量测试。

### 框架架构

```yaml
framework_name: "ITC-AudioTest-Framework"
language: "Python 3.11+"
dependencies:
  - "pyaudio_precision >= 2.1"  # APx API封装
  - "numpy >= 1.24"
  - "scipy >= 1.10"
  - "pandas >= 2.0"
  - "matplotlib >= 3.7"
  - "pytest >= 7.4"
  - "influxdb-client >= 1.36"
  - "jira >= 3.5"

architecture:
  layers:
    - layer: "测试脚本层 (Test Scripts)"
      content: "具体测试用例实现，调用API层"
      example: "test_freq_response.py, test_thd_n.py"
      
    - layer: "API封装层 (Instrument API)"
      content: "仪器设备控制封装，统一接口"
      classes: 
        - "APxController: Audio Precision控制"
        - "EnvironmentChamber: 温箱控制"
        - "VibrationController: 振动台控制"
        
    - layer: "数据处理层 (Data Processing)"
      content: "测量数据处理、统计计算"
      classes:
        - "FrequencyResponseAnalyzer"
        - "THDAnalyzer"
        - "StatisticalCalculator (Cpk, etc.)"
        
    - layer: "报告生成层 (Reporting)"
      content: "测试报告自动生成"
      classes:
        - "TestReportGenerator (Markdown/PDF)"
        - "DataPlotter (matplotlib封装)"
        
    - layer: "数据存储层 (Data Storage)"
      content: "测试数据持久化"
      interfaces:
        - "InfluxDBClient: 时序数据存储"
        - "JiraClient: 缺陷管理"
        - "FileStorage: 本地文件存储"
```

### APx接口代码示例

```python
# test_freq_response.py - 频率响应自动化测试
from itc_test_framework import APxController, TestReporter
from itc_test_framework.utils import spec_check
import pytest

class TestFrequencyResponse:
    
    @pytest.fixture(scope="class")
    def apx(self):
        """连接APx仪器"""
        controller = APxController()
        controller.connect("USB::0x1234::0x5678::INSTR")
        controller.load_sequence("templates/freq_response.apxseq")
        yield controller
        controller.disconnect()
    
    @pytest.fixture
    def dut_config(self):
        """被测设备配置"""
        return {
            "sample_rate": 48000,
            "rated_power": 30,  # W
            "impedance": 4,     # Ohm
            "reference_level": 2.0  # Vrms (1W@4Ω ≈ 2V)
        }
    
    def test_freq_response_passband(self, apx, dut_config):
        """AUD-001: 频率响应通带测试"""
        # 设置测量参数
        apx.set_generator_level(dut_config["reference_level"])
        apx.set_frequency_range(20, 20000)
        
        # 执行测量
        result = apx.measure_frequency_response()
        
        # 保存原始数据
        result.save_raw_data(f"data/AUD-001_{self.sample_id}.csv")
        
        # 规格检查
        freq = result.frequency
        magnitude = result.magnitude_db
        
        # 归一化到1kHz
        ref_idx = np.argmin(np.abs(freq - 1000))
        magnitude_norm = magnitude - magnitude[ref_idx]
        
        # 检查规格: ±3dB (20Hz-20kHz)
        mask_passband = (freq >= 20) & (freq <= 20000)
        max_dev = np.max(np.abs(magnitude_norm[mask_passband]))
        
        assert max_dev <= 3.0, \
            f"频率响应偏离 {max_dev:.2f}dB, 超出 ±3dB 规格"
        
        # 记录结果
        TestReporter.record(
            test_id="AUD-001",
            sample_id=self.sample_id,
            value=max_dev,
            unit="dB",
            limit="±3dB",
            result="Pass" if max_dev <= 3.0 else "Fail"
        )
    
    def test_channel_balance(self, apx, dut_config):
        """AUD-008: 通道平衡测试"""
        result = apx.measure_channel_balance()
        
        balance_db = np.abs(result.left_db - result.right_db)
        max_imbalance = np.max(balance_db)
        
        assert max_imbalance <= 1.0, \
            f"通道不平衡 {max_imbalance:.2f}dB, 超出 1dB 规格"
        
        TestReporter.record(
            test_id="AUD-008",
            sample_id=self.sample_id,
            value=max_imbalance,
            unit="dB",
            limit="≤1dB",
            result="Pass" if max_imbalance <= 1.0 else "Fail"
        )
```

### CI/CD集成

```yaml
# .github/workflows/audio_test.yml
name: Audio Performance Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  audio_test:
    runs-on: [self-hosted, audio-lab]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          
      - name: Check instrument calibration
        run: python -m itc_test_framework cal-check
        
      - name: Run smoke tests (P0)
        run: pytest tests/smoke/ -v --tb=short
        
      - name: Run audio performance tests (P1)
        if: github.event_name == 'pull_request'
        run: pytest tests/audio/ -v --tb=short --html=report.html
        
      - name: Run full test suite (P1+P2)
        if: github.ref == 'refs/heads/main'
        run: pytest tests/ -v --tb=short --html=report.html
        
      - name: Upload test results
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: |
            report.html
            data/
            logs/
```

---

## 技能6: 测试数据分析 `SKILL-TST-006`

### 概述
运用统计方法对测试数据进行深度分析，实现Pass/Fail判定、趋势识别和制程能力评估。

### 统计分析规范

#### 6.1 描述性统计

```yaml
required_statistics:
  - name: "样本量 (N)"
    description: "有效测量次数"
    
  - name: "均值 (Mean)"
    description: "算术平均值"
    formula: "x̄ = (Σxi) / N"
    
  - name: "标准差 (Std Dev)"
    description: "样本标准差"
    formula: "s = √(Σ(xi - x̄)² / (N-1))"
    
  - name: "最大值 (Max)"
  - name: "最小值 (Min)"
  - name: "范围 (Range)"
    formula: "Max - Min"
    
  - name: "中位数 (Median)"
  - name: "四分位距 (IQR)"
    formula: "Q3 - Q1"
```

#### 6.2 制程能力分析

```yaml
capability_indices:
  Cp:
    description: "潜在制程能力"
    formula: "(USL - LSL) / (6 × s)"
    interpretation:
      "Cp ≥ 1.33": "制程能力充足"
      "1.0 ≤ Cp < 1.33": "制程能力尚可，需关注"
      "Cp < 1.0": "制程能力不足，需改善"
      
  Cpk:
    description: "实际制程能力 (考虑偏移)"
    formula: "min[(USL - x̄)/(3s), (x̄ - LSL)/(3s)]"
    interpretation:
      "Cpk ≥ 1.33": "良好"
      "1.0 ≤ Cpk < 1.33": "合格但需改善"
      "Cpk < 1.0": "不合格"
      
  Pp/Ppk:
    description: "过程性能指数 (长期，含组间变异)"
    usage: "PVT/量产阶段使用"
```

#### 6.3 趋势分析规则

```yaml
trend_rules:
   Western_Electric:
    - rule: "1点超出3σ控制限 → 异常"
    - rule: "连续9点在中心线同一侧 → 趋势"
    - rule: "连续6点递增或递减 → 趋势"
    - rule: "连续14点交替上下 → 异常"
    - rule: "2/3点超出2σ (同侧) → 预警"
    - rule: "4/5点超出1σ (同侧) → 预警"
    
  响应措施:
    预警: "增加监控频率，通知项目经理Agent"
    趋势: "停止测试，调查原因，联系设计Agent"
    异常: "立即停止，隔离批次，启动8D分析"
```

### 数据分析报告模板

```markdown
## 数据分析报告: [测试项目]

### 1. 数据概览
- 样本量: N = XX
- 测试日期: YYYY-MM-DD ~ YYYY-MM-DD
- 测试设备: [设备型号/序列号]

### 2. 描述性统计
| 统计量 | 左通道 | 右通道 | 规格限 |
|--------|--------|--------|--------|
| 均值 | X.XX | X.XX | — |
| 标准差 | X.XX | X.XX | — |
| 最大值 | X.XX | X.XX | USL: X |
| 最小值 | X.XX | X.XX | LSL: X |
| Cpk | X.XX | X.XX | ≥1.33 |

### 3. 分布分析
- 直方图 + 正态拟合
- Shapiro-Wilk正态性检验: W = X.XX, p = X.XX
- 结论: [正态/非正态分布]

### 4. 趋势分析
- 控制图 (X-bar / R-chart)
- 违反规则: [无 / 规则#X, 样本#Y]
- 趋势判断: [稳定 / 向上趋势 / 向下趋势]

### 5. 结论与建议
- 总体判定: [通过 / 有条件通过 / 不通过]
- 主要发现: [关键发现]
- 建议措施: [如有]
```

---

## 技能7: 跨域协作接口 `SKILL-COL-001`

### 与代码执行Agent的协作接口

```yaml
agent_id: agent.code.execution
interface_type: 自动化脚本执行
protocol: Python脚本 + 返回JSON

workflow:
  1. 测试Agent编写/更新自动化测试脚本
  2. 提交到代码仓库
  3. CI Agent触发代码执行Agent
  4. 代码执行Agent在测试工位执行脚本
  5. 返回测试结果JSON
  6. 测试Agent分析结果并生成报告

script_standards:
  naming: "test_{category}_{item}.py"
  structure:
    - "导入区 (imports)"
    - "配置区 (CONFIG - 可调参数)"
    - "Fixture定义 (设备连接)"
    - "测试函数 (pytest格式)"
    - "数据记录 (TestReporter调用)"
    
  code_quality:
    - "遵循PEP 8"
    - "类型注解 (type hints)"
    - "docstring 每个函数"
    - "错误处理 try-except"
    - "日志记录 logging"

execution_result_format:
  ```json
  {
    "test_run_id": "TR-20240315-001",
    "timestamp": "2024-03-15T09:30:00Z",
    "total_tests": 25,
    "passed": 23,
    "failed": 2,
    "skipped": 0,
    "duration_seconds": 420,
    "results": [
      {
        "test_id": "AUD-001",
        "test_name": "频率响应测试",
        "status": "Pass",
        "value": 2.3,
        "unit": "dB",
        "limit": "±3dB",
        "sample_id": "SN2401001",
        "data_file": "data/AUD-001_SN2401001.csv"
      }
    ],
    "environment": {
      "temperature": 23.2,
      "humidity": 52,
      "apx_serial": "AP515-12345",
      "cal_due_date": "2024-06-15"
    }
  }
  ```
```

### 与数据库Agent的协作接口

```yaml
agent_id: agent.database
interface_type: 测试数据存储与历史对比
protocol: InfluxDB Line Protocol + REST API

data_schema:
  measurement: "audio_test_results"
  tags:
    - project_id: "PRJ-2401"
    - sample_id: "SN2401001"
    - test_id: "AUD-001"
    - test_name: "freq_response"
    - channel: "left"
    - operator: "auto"
  fields:
    - value: 2.3
    - limit_upper: 3.0
    - limit_lower: -3.0
    - pass_fail: 1  # 1=Pass, 0=Fail
  timestamp: "2024-03-15T09:30:00Z"

queries:
  history_comparison:
    query: |
      SELECT mean("value"), stddev("value"), count("value")
      FROM "audio_test_results"
      WHERE "test_id" = 'AUD-001'
      AND "project_id" =~ /PRJ-23.*/
      GROUP BY "project_id"
    purpose: "与历史项目对比性能水平"
    
  trend_analysis:
    query: |
      SELECT "value"
      FROM "audio_test_results"
      WHERE "test_id" = 'AUD-001'
      AND "sample_id" =~ /SN2401.*/
      ORDER BY time
    purpose: "批次内趋势分析"
    
  cpk_calculation:
    query: |
      SELECT mean("value"), stddev("value")
      FROM "audio_test_results"
      WHERE "test_id" = $test_id
      AND "sample_id" =~ /$batch_pattern/
    purpose: "计算Cpk"
    post_processing: "Python统计计算"
```

### 与缺陷管理Agent的协作接口

```yaml
agent_id: agent.defect.tracking
interface_type: 缺陷生命周期管理
protocol: JIRA REST API v2

defect_workflow:
  states:
    - "新建 (New)"
    - "确认 (Confirmed)"
    - "已指派 (Assigned)"
    - "修复中 (In Progress)"
    - "待验证 (Resolved)"
    - "已验证 (Verified)"
    - "关闭 (Closed)"
    - "拒绝 (Rejected)"
    
  transitions:
    testAgent_can:
      - "New → Confirmed"  # 确认缺陷有效
      - "Resolved → Verified"  # 验证修复
      - "Resolved → Reopened"  # 验证未通过
      
    auto_triggers:
      - "Critical缺陷 → 立即通知项目经理Agent"
      - "24h未指派 → 自动升级"
      - "验证通过 → 自动关闭"

defect_template:
  ```json
  {
    "project": {"key": "ITC"},
    "issuetype": {"name": "Bug"},
    "summary": "[测试] 左通道THD+N@100Hz超标",
    "description": "详见测试报告TR-20240315-001",
    "priority": {"name": "High"},
    "labels": ["audio", "thd", "left-channel"],
    "customfield_test_id": "AUD-002",
    "customfield_sample_id": "SN2401003",
    "customfield_measured_value": "0.35%",
    "customfield_spec_limit": "0.1%",
    "customfield_test_data": "data/AUD-002_SN2401003.csv"
  }
  ```
```

### 与各领域Agent的协作

```yaml
collaboration_with_design_agents:
  structure_agent:
    input: "结构测试需求 (跌落/振动/密封)"
    output: "结构问题反馈、失效分析"
    feedback_format: |
      问题描述 + 失效照片 + 测试条件 + 建议改进
      
  acoustic_agent:
    input: "声学性能规格"
    output: "实测声学数据、偏差分析"
    feedback_format: |
      实测频响/THD/阻抗 + 与目标对比 + 偏差根因分析
      
  hardware_agent:
    input: "电气测试需求"
    output: "电气性能数据、故障分析"
    feedback_format: |
      功耗/信噪比/EMI数据 + 与规格对比 + 热点分析
      
  firmware_agent:
    input: "功能测试需求 (DSP/控制)"
    output: "功能验证结果、bug报告"
    feedback_format: |
      功能Pass/Fail + 边界条件行为 + 日志分析
```

---

## 输入/输出规范

### 标准输入

| 输入类型 | 格式 | 来源 | 验证规则 |
|----------|------|------|----------|
| 测试需求规格 | JSON Schema `测试需求` | 各设计Agent | Schema验证 + 覆盖率检查 |
| 样品信息 | JSON | 项目经理Agent | SN唯一性 + 状态有效性 |
| 设备校准数据 | JSON | 设备管理Agent | 校准有效期内 |
| 自动化脚本 | Python | 本Agent/代码库 | 代码审查 + 单元测试 |
| 历史测试数据 | InfluxDB查询 | 数据库Agent | 数据完整性校验 |

### 标准输出

| 输出类型 | 格式 | 目标 | 质量检查 |
|----------|------|------|----------|
| 测试计划 | Markdown + Excel | 项目经理Agent | WBS覆盖率100% |
| 测试用例集 | Markdown + JSON | 各领域Agent | 追溯矩阵完整 |
| 测试报告 | Markdown + PDF | 项目经理Agent + 评审Agent | 数据可追溯 |
| 缺陷报告 | JIRA JSON + Markdown | 缺陷管理Agent | 可复现性验证 |
| 自动化脚本 | Python | 代码执行Agent | 代码覆盖率>90% |
| 数据分析报告 | Markdown + Excel | 项目经理Agent | 统计方法正确 |

### 质量检查清单 (自检)

```yaml
pre_delivery_check:
  - [ ] 测试设备在校准有效期内
  - [ ] 样品SN记录完整
  - [ ] 测试条件符合规格要求
  - [ ] 原始数据文件保存完整
  - [ ] 数据处理计算正确 (抽样复核)
  - [ ] 统计计算 (Cpk/趋势) 方法正确
  - [ ] Pass/Fail判定依据规格 (非主观)
  - [ ] 缺陷报告可复现
  - [ ] 报告模板字段完整
  - [ ] 数据已上传数据库Agent
  - [ ] 异常结果已通知相关Agent
```
