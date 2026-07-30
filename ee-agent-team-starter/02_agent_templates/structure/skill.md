---
name: Structure Engineer Agent Skills
description: |
  结构设计与机械工程专家Agent的专业技能定义、工具使用规范、工作流程和输入输出标准。
  遵循Kimi/Hermes Agent Skill标准，包含与其他Agent的明确协作接口。
version: 1.0.0
author: ITC Enterprise Agent System
---

# Skill: 结构设计与机械工程专家 Agent

## 技能总览

```yaml
技能域:
  - CAD三维设计
  - 箱体声学集成
  - 材料选型工程
  - 振动控制设计
  - DFM/DFA分析
  - 跨域协作接口

技能标准: Kimi/Hermes Agent Skill Specification v1.0
认证级别: L3 (专家级)
```

---

## 技能1: CAD设计流程 `SKILL-CAD-001`

### 概述
从概念到详细设计的完整3D建模工作流，确保全参数化、可修改、可继承的设计资产。

### 工作流程

#### Step 1: 概念设计 (Concept Design)

```yaml
输入:
  - 声学结构需求JSON (来自声学Agent)
  - PCB空间需求 (来自硬件Agent)
  - ID外观曲面 (来自工业设计Agent)
  - 产品规格书 (来自项目经理Agent)

活动:
  1. 解析约束条件:
     - 外形尺寸限制: 长×宽×高 (mm)
     - 内部容积需求: V_min (L) — 来自声学设计
     - 壁厚约束: t_min ~ t_max (mm) — 基于材料+刚度
     - 安装方式: 桌面/壁挂/吊装/嵌入式
     
  2. 生成2-3个概念方案:
     - 方案草图 (顶/前/侧视图)
     - 材料初选型
     - 大致壁厚和肋条布局
     - 预估质量和成本
     
  3. 方案对比矩阵:
     | 维度 | 权重 | 方案A | 方案B | 方案C |
     |------|------|-------|-------|-------|
     | 刚度质量比 | 0.25 | 评分 | 评分 | 评分 |
     | 可制造性 | 0.25 | 评分 | 评分 | 评分 |
     | 成本控制 | 0.20 | 评分 | 评分 | 评分 |
     | 装配效率 | 0.15 | 评分 | 评分 | 评分 |
     | 密封性 | 0.15 | 评分 | 评分 | 评分 |
     
输出:
  - 概念设计方案文档 (Markdown)
  - 方案对比矩阵 (JSON)
  - 推荐方案及理由
```

#### Step 2: 详细建模 (Detailed Modeling)

```yaml
建模规范:
  软件平台: SolidWorks 2024 / Creo 9.0 / NX 2212
  建模方法: 自顶向下 (Top-Down) 装配体设计
  
  主装配体结构:
    Product_ASM
    ├── ASM_01_前壳体 (Front_Housing)
    ├── ASM_02_后壳体 (Rear_Housing)  
    ├── ASM_03_扬声器模块 (Driver_Module)
    ├── ASM_04_电子舱 (Electronics_Bay)
    ├── ASM_05_安装系统 (Mounting_System)
    ├── ASM_06_密封系统 (Sealing_System)
    └── ASM_99_标准件库 (Hardware_Std)
    
  参数化设计规则:
    - 全局变量定义: 外形尺寸、壁厚、拔模角、圆角半径
    - 声学相关尺寸: 以"ACO_"前缀命名 (如 ACO_Volume, ACO_Port_Dia)
    - 结构相关尺寸: 以"STR_"前缀命名 (如 STR_Wall_Thickness)
    - 关联引用: 跨零件关联使用外部参考，禁止断开链接
    
  建模质量标准:
    - 特征树深度: ≤ 50级/零件
    - 草图完全定义率: 100%
    - 零几何错误 (零接触边、零面间隙)
    - 模型质量评分: > 95/100 (使用CAD内置检查工具)
    
输出:
  - 完整装配体3D模型 (.sldasm / .asm)
  - 单个零件文件 (.sldprt / .prt)
  - 中性格式 (.step + .iges)
  - 模型质量报告
```

#### Step 3: 工程图生成 (Drawing Generation)

```yaml
制图规范:
  投影标准: 第三角投影 (Third Angle Projection)
  尺寸单位: mm (公制)
  公差标准: ISO 2768-m (一般公差) + 独立公差 (关键尺寸)
  
  必含视图:
    - 主视图 (Front View)
    - 俯视图 (Top View)
    - 左视图 (Left View)
    - 剖视图 (Section A-A, B-B — 穿过声学中心)
    - 局部放大图 (Detail C, D — 密封区域、安装区域)
    - 爆炸视图 (Exploded View + BOM气球)
    
  GD&T标注要求:
    - 安装基准面: 平面度 ≤ 0.1mm
    - 扬声器安装孔: 位置度 Ø0.15mm (相对基准A/B/C)
    - 配合面: 轮廓度 ≤ 0.2mm
    - 密封沟槽: 同轴度 Ø0.1mm
    
  技术要求:
    1. 未注公差按 ISO 2768-m
    2. 表面粗糙度: 外观面 Ra 1.6μm，配合面 Ra 3.2μm，非外观面 Ra 6.3μm
    3. 所有棱边倒角 C0.5 或圆角 R1 (除非特别注明)
    4. 材料标记位置按模板
    5. 超声波焊接区域标注焊接能量参考值
    
输出:
  - 2D工程图 (.slddrw + .pdf + .dwg)
  - 工程图检查清单
```

#### Step 4: BOM编制 (BOM Generation)

```yaml
BOM层级:
  Level 0: 成品 (Finished Product)
  Level 1: 组件 (Assembly) — 可独立装配的子单元
  Level 2: 子零件 (Part) — 需制造的零件
  Level 3: 标准件 (Standard Part) — 螺钉、垫片、胶条等
  
BOM字段规范:
  | 字段 | 必填 | 格式示例 |
  |------|------|----------|
  | 层级 | 是 | 1.1.2 |
  | 件号 | 是 | STR-2401-001-A |
  | 名称 | 是 | 前壳体-上盖 |
  | 规格 | 是 | ABS+PC, 黑色, UV稳定 |
  | 数量 | 是 | 1 |
  | 单位 | 是 | EA / SET / M |
  | 材料 | 是 | ABS+PC (Bayblend T85 XF) |
  | 单重(g) | 是 | 125.5 |
  | 供应商 | 否 | 供应商代码 + 名称 |
  | 采购/自制 | 是 | Purchase / Make |
  | 参考标准 | 否 | GB/T 12672 |
  | 备注 | 否 | 需喷漆处理 |
  
件号编码规则:
  [域代码]-[项目代码]-[序号]-[版本]
  示例: STR-2401-001-A = 结构域-24年01项目-001号件-A版
  
输出:
  - 多级BOM表 (.xlsx)
  - BOM一致性报告 (与3D模型比对)
```

### 工具调用

```yaml
tool: cad_modeling
interface: CAD接口Agent (agent.cad.interface)
input:
  command: create_part / modify_feature / export_step / generate_drawing
  parameters:
    part_number: "STR-2401-001-A"
    feature_tree: [...]
    constraints: [...]
output:
  file_path: "/data/models/STR-2401-001-A.step"
  quality_score: 97
  errors: []
  
tool: bom_generator
interface: 本地脚本
input:
  assembly_path: "/data/models/Product_ASM.sldasm"
  template: "TPL-BOM-001"
output:
  bom_path: "/data/bom/BOM_2401_vA.xlsx"
  item_count: 45
  total_weight: 850
```

---

## 技能2: 箱体声学设计 `SKILL-ACO-001`

### 概述
将声学Agent的电气-声学参数需求转化为具体的箱体结构几何，确保声学性能在物理结构上可实现。

### 箱体类型设计规范

#### 2.1 密闭式箱体 (Sealed/Closed Box)

```yaml
适用场景: 低频准确性要求高、Qtc可控、瞬态响应好
设计公式:
  目标Qtc: 0.707 (Butterworth) — 默认目标
  箱体容积: Vb = Vas / ((Qtc/Qts)² - 1)
    Vas: 扬声器顺性等效容积 (来自声学Agent)
    Qts: 扬声器总Q值 (来自声学Agent)
    Qtc: 目标系统Q值 (通常0.6-1.0)
    
  填充材料修正: 
    聚酯纤维填充 50-100% → 等效容积增加 ~15-25%
    实际Vb = 计算Vb × 0.8 (预留填充空间)
    
结构要求:
  - 内部无泄漏: 所有接缝密封处理
  - 壁厚: ≥ 3mm (塑料) / ≥ 1.5mm (金属) + 加强筋
  - 刚度目标: 箱体一阶模态 > 200Hz (避免与低音共振)
  - 内部尺寸比例: 避免1:1:1整数比，减少驻波
    推荐: 1 : 1.2 : 1.5 (深:宽:高) 或类似非整数比

验证项:
  - [ ] 内部净容积 = Vb ± 5%
  - [ ] 所有接缝密封设计完成
  - [ ] 一阶箱体模态 > 200Hz
  - [ ] 内部尺寸比例非整数比
```

#### 2.2 倒相式箱体 (Bass Reflex/Vented Box)

```yaml
适用场景: 扩展低频下潜、提升低频效率
设计公式:
  调谐频率: fb = 0.8 × fs (起始建议)
    fs: 扬声器谐振频率
    
  箱体容积: Vb = Vas / ((fb/fs)² × (Qts⁻²) - 1)
  
  倒相管参数:
    管径: Dv ≥ 0.2 × 扬声器有效直径 (最小防噪)
    管长: Lv = (Dv² × N × fb²) / (4π² × c² × Vb) - 0.6 × Dv
      N: 管数量 (通常为1)
      c: 声速 (343 m/s @ 20°C)
      
  倒相管截面积: Sv = π × (Dv/2)²
  推荐Sv/Sd比: 0.05 ~ 0.15 (Sd = 扬声器有效振膜面积)

结构要求:
  - 倒相管开口位置: 远离扬声器，通常背面或侧面
  - 管壁厚度: ≥ 1.5mm，与箱体壁一体或插入式
  - 管口圆角: R ≥ 2mm (降低气流噪声)
  - 内部无阻挡: 倒相管通道畅通
  - 边缘距离: 管口距箱体边缘 ≥ 1.5×Dv

验证项:
  - [ ] 调谐频率 fb 偏差 < ±5%
  - [ ] 倒相管截面积满足Sv/Sd比
  - [ ] 管长可实现 (不超过箱体深度)
  - [ ] 管口距壁面/边缘距离满足
  - [ ] 最大声压下无气流噪声 (Dv满足最小值)
```

#### 2.3 传输线式箱体 (Transmission Line)

```yaml
适用场景: 极低频扩展、特定声学特性追求
设计要点:
  管道长度: L = c / (4 × f_target) — 1/4波长
    c: 声速
    f_target: 目标截止频率 (通常0.5~0.7 × fs)
    
  管道截面积: 沿长度渐变，入口 ≈ Sd，出口 = 0.5~0.7 × Sd
  填充密度: 渐变，入口密→出口疏 (通常0.5~2.0 lb/ft³)
  折叠方式: Z形折叠，转角圆角R ≥ 25mm

结构要求:
  - 管道截面积精度: ±5%
  - 折叠转角光滑过渡，无锐角
  - 填充材料固定结构
  - 总长度严格控制 (±3%)

验证项:
  - [ ] 管道总长度 = 设计值 ±3%
  - [ ] 截面积渐变曲线平滑
  - [ ] 所有转角R ≥ 25mm
  - [ ] 填充材料可固定且不脱落
```

### 与声学仿真Agent的协作接口

```yaml
interface: agent.acoustic.simulation
protocol: 参数双向绑定

data_flow:
  structure_to_acoustic:
    - 箱体内部几何 (.step)
    - 壁厚参数 (JSON)
    - 开口位置坐标 (JSON)
    - 材料声学属性 (JSON)
    
  acoustic_to_structure:
    - 目标容积调整 (±ΔV)
    - 开口位置优化建议 (x,y,z偏移)
    - 壁厚对声学影响评估
    - 共振问题反馈 (频率+位置)

sync_frequency: 每日同步 + 里程碑评审
conflict_resolution: 声学性能优先，结构反馈可行性约束
```

---

## 技能3: 材料选型指南 `SKILL-MAT-001`

### 概述
基于多目标决策矩阵的材料选型方法，平衡力学性能、声学特性、成本和加工性。

### 常用材料数据库

| 材料 | 密度(g/cm³) | 拉伸强度(MPa) | 弹性模量(GPa) | 阻尼因子 | 成本指数 | 适用工艺 |
|------|-------------|---------------|---------------|----------|----------|----------|
| ABS | 1.04 | 45 | 2.3 | 0.02 | 1.0 | 注塑 |
| ABS+PC | 1.12 | 55 | 2.5 | 0.025 | 1.4 | 注塑 |
| PC | 1.20 | 65 | 2.4 | 0.015 | 1.6 | 注塑 |
| PA6+GF30 | 1.35 | 130 | 7.5 | 0.03 | 2.0 | 注塑 |
| 铝合金6061 | 2.70 | 310 | 69 | 0.001 | 3.5 | CNC/压铸 |
| 铝合金5052 | 2.68 | 230 | 70 | 0.001 | 2.8 | 冲压 |
| MDF | 0.75 | 20 | 3.0 | 0.05 | 0.6 | CNC |
| HDF | 0.90 | 35 | 4.0 | 0.04 | 0.8 | CNC |
| 碳纤维复材 | 1.60 | 600 | 70 | 0.02 | 15.0 | 模压 |

### 选型决策矩阵

```yaml
method: 加权评分法 (Weighted Scoring Model)

criteria:
  - name: 刚度质量比 (Specific Stiffness)
    weight: 0.25
    scoring: E/ρ, 越高越好
    
  - name: 声学阻尼
    weight: 0.20
    scoring: 材料阻尼因子, 越高越好
    
  - name: 成本效益
    weight: 0.20
    scoring: 1/成本指数, 越高越好
    
  - name: 加工适应性
    weight: 0.15
    scoring: 基于产品数量和几何复杂度
    
  - name: 表面质量
    weight: 0.10
    scoring: 外观可处理性 (喷漆/纹理)
    
  - name: 环境适应性
    weight: 0.10
    scoring: 耐温/耐湿/UV稳定性

decision_rules:
  - 量产>10K: 优先注塑材料 (ABS/ABS+PC/PC)
  - 量产<1K: 优先CNC材料 (铝/MDF)
  - 高端旗舰: 可考虑碳纤维/特殊复合材料
  - 防护要求IP54+: 优先塑料一体化设计
```

### 材料选型输出模板

```markdown
## 材料选型报告: [零件名称]

### 候选材料对比
| 材料 | 刚度质量比 | 阻尼 | 成本 | 加工性 | 表面质量 | 环境 | 总分 |
|------|-----------|------|------|--------|----------|------|------|
| [M1] | x/10 | x/10 | x/10 | x/10 | x/10 | x/10 | XX |
| [M2] | x/10 | x/10 | x/10 | x/10 | x/10 | x/10 | XX |

### 推荐材料: [材料名称]
**理由**: [简要说明]
**关键参数**: 
- 密度: X.XX g/cm³
- 弹性模量: X.X GPa
- 预估单件质量: XXX g

### 风险提示
- [风险描述及缓解措施]
```

---

## 技能4: 振动控制策略 `SKILL-VIB-001`

### 概述
通过阻尼设计、去耦设计和加强筋布局，控制结构振动对声学性能的影响。

### 振动设计规范

#### 4.1 模态频率规划

```yaml
目标: 避免结构共振与扬声器工作频率重叠

频率禁区规划:
  低音单元 (50-500Hz): 
    箱体一阶模态目标: > 200Hz
    前后面板模态目标: > 300Hz
    
  中音单元 (200-5000Hz):
    安装板模态目标: > 600Hz
    整体结构模态目标: > 150Hz
    
  高音单元 (2000-20000Hz):
    安装结构模态目标: > 2000Hz
    
设计裕量: 模态频率 ≥ 1.5 × 单元上限频率 或 ≤ 0.7 × 单元下限频率
```

#### 4.2 加强筋设计规范

```yaml
layout_rules:
  主加强筋:
    - 平行于扬声器振动方向布置
    - 间距: 壁厚的 8-12 倍
    - 高度: 壁厚的 2.5-4 倍
    - 根部圆角: R = 0.25 × 筋高度
    
  辅助加强筋:
    - 垂直于主加强筋，形成网格
    - 间距: 主筋间距的 1-2 倍
    
  扬声器周围:
    - 放射状加强筋 (Radial Ribs)
    - 数量: 6-12条
    - 连接安装孔区域
    
design_check:
  - [ ] 筋的拔模方向一致
  - [ ] 筋顶部厚度 ≤ 0.6 × 根部厚度 (防止缩痕)
  - [ ] 交叉处减薄或错位 (避免应力集中)
  - [ ] 筋不阻挡声学通道/倒相管
```

#### 4.3 阻尼与去耦设计

```yaml
damping_methods:
  材料阻尼:
    - 高阻尼塑料 (如添加橡胶改性)
    - 沥青阻尼片 (Bitumen Pads)
    - 质量负载层 (Mass-Loaded Barrier)
    
  结构去耦:
    - 扬声器与箱体间: 弹性垫圈/橡胶悬边
    - PCB与箱体间: 橡胶柱/硅胶垫
    - 面板间: 弹性密封条 (同时起密封和阻尼作用)
    
  吸振设计:
    - 内部吸振材料: 聚酯纤维棉 / 泡沫
    - 局部质量阻尼器 (Tuned Mass Damper) — 用于特定频率问题

specifications:
  扬声器安装: 
    - 安装面平面度: ≤ 0.1mm
    - 紧固扭矩: 按螺钉规格标准化 (M4: 2.5±0.3 N·m)
    - 密封垫压缩率: 15-25%
    
  PCB安装:
    - 支撑间距: ≤ 80mm (防止PCB共振)
    - 固定点数: ≥ 4点 (标准PCB)
    - 热膨胀补偿: 长边方向留0.3mm间隙
```

---

## 技能5: DFM/DFA检查清单 `SKILL-DFM-001`

### 概述
系统化的可制造性/可装配性检查流程，确保设计可高效、低成本地转化为产品。

### DFM检查清单 (100项)

#### A. 注塑成型检查 (适用于塑料件) — 30项

```yaml
A01-A10: 基本设计
  A01: [ ] 壁厚均匀，变化比 ≤ 1:1.5
  A02: [ ] 最小壁厚 ≥ 材料推荐值 (ABS: 1.2mm, PC: 1.5mm)
  A03: [ ] 最大壁厚 ≤ 4mm (避免缩痕)
  A04: [ ] 所有拔模斜度 ≥ 0.5° (外观面) / ≥ 1° (非外观面)
  A05: [ ] 外观面拔模方向统一
  A06: [ ] 圆角R ≥ 0.5mm (所有内外角)
  A07: [ ] 筋顶部厚度 ≤ 0.6 × 根部厚度
  A08: [ ] 筋高度 ≤ 3 × 壁厚
  A09: [ ]  bosses 有加强筋支撑
  A10: [ ] 沉孔深度 ≤ 2 × 直径

A11-A20: 模具相关
  A11: [ ] 分型线位置合理 (不在外观面或便于隐藏)
  A12: [ ] 无倒扣 (Undercut) 或已设计滑块
  A13: [ ] 浇口位置不影响外观
  A14: [ ] 顶出位置不在外观面
  A15: [ ] 模具出模方向确认
  A16: [ ] 滑块/斜顶空间足够
  A17: [ ] 冷却水道布置空间预留
  A18: [ ] 模腔数与产量匹配
  A19: [ ] 收缩率已在尺寸中补偿
  A20: [ ] 纹理区域拔模角额外增加 (每0.01mm深度+1°)

A21-A30: 质量和成本
  A21: [ ] 零件数最小化 (集成设计)
  A22: [ ] 标准材料 (非定制色粉)
  A23: [ ] 标准颜色 (非小批量定制)
  A24: [ ] 无过度指定公差 (≥ ±0.1mm 除非必要)
  A25: [ ] 外观面质量等级定义 (SPI A-3 或等同)
  A26: [ ] 嵌件数量最小化
  A27: [ ] 焊接/熔接线位置避开高应力区
  A28: [ ] 气辅注塑可行性评估 (大型件)
  A29: [ ] 二次加工需求最小化
  A30: [ ] 回收料比例声明 (如适用)
```

#### B. 金属加工检查 — 25项

```yaml
B01-B10: CNC加工
  B01: [ ] 内圆角R ≥ 刀具半径 (通常R ≥ 1.5mm)
  B02: [ ] 深宽比 ≤ 5:1 (槽/孔)
  B03: [ ] 薄壁厚度 ≥ 0.8mm (铝)
  B04: [ ] 标准孔径 (钻头标准尺寸)
  B05: [ ] 螺纹深度 ≤ 3 × 直径
  B06: [ ] 加工基准统一
  B07: [ ] 减少装夹次数 (≤ 3次)
  B08: [ ] 去毛刺要求标注
  B09: [ ] 表面粗糙度合理指定
  B10: [ ] 阳极氧化/表面处理标注

B11-B20: 钣金/冲压
  B11: [ ] 最小折弯内R ≥ 材料厚度
  B12: [ ] 折弯高度 ≥ 2 × 材料厚度 + 弯刀半径
  B13: [ ] 孔距折弯线 ≥ 2 × 材料厚度
  B14: [ ] 加强筋/凸包设计符合工艺
  B15: [ ] 标准板厚 (0.5/0.8/1.0/1.2/1.5/2.0/2.5/3.0mm)
  B16: [ ] 焊接位置可达
  B17: [ ] 喷涂/表面处理前处理可行
  B18: [ ] 运输/堆叠结构考虑
  B19: [ ] 展开图可正确生成
  B20: [ ] 公差累积分析完成

B21-B25: 压铸
  B21: [ ] 最小壁厚 ≥ 1.0mm (铝压铸)
  B22: [ ] 拔模斜度 ≥ 1° (外观面) / ≥ 0.5° (非外观面)
  B23: [ ] 浇口/排气设计
  B24: [ ] 顶出位置规划
  B25: [ ] 后续加工余量预留
```

#### C. 装配设计检查 (DFA) — 25项

```yaml
C01-C10: 零件管理
  C01: [ ] 总零件数 ≤ 目标值 (旗舰<50, 量产<30)
  C02: [ ] 标准件比例 ≥ 60%
  C03: [ ] 对称零件设计 (减少防错成本)
  C04: [ ] 零件方向唯一 (防错)
  C05: [ ] 相似零件差异化明显
  C06: [ ] 模块化设计 (子组件可独立装配)
  C07: [ ] 紧固件种类 ≤ 3种
  C08: [ ] 螺钉规格标准化 (最多2种)
  C09: [ ] 自攻螺钉优先 (减少嵌件)
  C10: [ ] 卡扣连接替代螺钉 (一次性装配)

C11-C20: 装配操作
  C11: [ ] 从单一方向装配 (Z方向)
  C12: [ ] 无需翻转工件
  C13: [ ] 操作空间足够 (工具可达)
  C14: [ ] 视线可达 (目视检查装配到位)
  C15: [ ] 定位特征设计 (引导装配)
  C16: [ ] 防错设计 (Poka-Yoke)
  C17: [ ] 装配力可控 (卡扣插入力<50N)
  C18: [ ] 螺纹旋入长度 ≤ 3 × 直径 (快速装配)
  C19: [ ] 密封件可快速安装
  C20: [ ] 线缆/排线走向清晰固定

C21-C25: 测试和维护
  C21: [ ] 测试点可达 (不拆外壳)
  C22: [ ] 可维修性设计 (易拆卸)
  C23: [ ] 扬声器可单独更换
  C24: [ ] 生命周期结束可回收
  C25: [ ] 装配顺序文档化
```

#### D. 密封与防护检查 — 10项

```yaml
D01-D10:
  D01: [ ] 密封沟槽尺寸符合标准 (矩形/O型圈槽)
  D02: [ ] 密封面平面度 ≤ 0.1mm
  D03: [ ] 密封面粗糙度 Ra 1.6-3.2μm
  D04: [ ] 密封垫/圈压缩率 15-25%
  D05: [ ] 密封路径连续无中断
  D06: [ ] 螺钉间距均匀 (密封压力均匀)
  D07: [ ] 防护等级设计对应 (IPXX)
  D08: [ ] 透气阀/防水膜位置设计 (如需要)
  D09: [ ] 排水/凝露处理设计
  D10: [ ] 密封材料与接触介质相容
```

#### E. 声学结构集成检查 — 10项

```yaml
E01-E10:
  E01: [ ] 内部容积 = 声学需求 ±5%
  E02: [ ] 开口/倒相管位置符合声学设计
  E03: [ ] 开口尺寸符合声学计算
  E04: [ ] 内部无阻挡声通道的结构
  E05: [ ] 扬声器安装面刚度足够 (FEM验证)
  E06: [ ] 安装面平面度 ≤ 0.1mm
  E07: [ ] 内部吸声材料固定结构
  E08: [ ] 箱体模态频率 > 200Hz
  E09: [ ] 结构共振不干扰工作频段
  E10: [ ] 听音孔/导音管设计符合声学要求
```

### DFM评分标准

| 分数范围 | 等级 | 含义 | 处理 |
|----------|------|------|------|
| 95-100 | 优秀 | 制造友好，低风险 | 直接发布 |
| 85-94 | 良好 | 可制造，有小改进空间 | 建议优化，可发布 |
| 70-84 | 可接受 | 有风险，需确认 | 必须优化后重新评分 |
| < 70 | 不可接受 | 重大制造风险 | 禁止发布，重新设计 |

---

## 技能6: 跨域协作接口 `SKILL-COL-001`

### 与声学仿真Agent的协作接口

```yaml
agent_id: agent.acoustic.simulation
interface_type: 双向数据流
protocol: JSON-RPC over MessageBus

workflow:
  1. 结构Agent发送初始箱体几何 + 参数JSON
  2. 声学Agent进行仿真，返回结果 + 优化建议
  3. 结构Agent评估优化建议的可行性
  4. 循环迭代直到双方确认OK
  5. 联合签署设计冻结确认

message_schema:
  structure_to_acoustic:
    type: "箱体几何交付"
    version: "1.0"
    payload:
      geometry_file: "url/to/model.step"
      parameters:
        internal_volume_ml: 2500
        wall_thickness_mm: 2.5
        port_diameter_mm: 50
        port_length_mm: 80
        port_position: [x, y, z]
        material_properties:
          density: 1120
          youngs_modulus: 2.5e9
          damping_factor: 0.025
      constraints:
        volume_tolerance: "±5%"
        position_tolerance: "±2mm"
    
  acoustic_to_structure:
    type: "仿真反馈"
    payload:
      simulation_result:
        f_b_tuning: 42.5
        frequency_response: "url/to/fr_data.csv"
        port_velocity_m_s: 12.5
      optimization_suggestions:
        - parameter: "internal_volume"
          action: "increase"
          value: 200
          reason: "下潜深度不足，目标38Hz"
        - parameter: "port_length"
          action: "increase"
          value: 15
          reason: "调谐频率偏移"
      issues:
        - severity: "medium"
          description: "200-250Hz有轻微峰值"
          suggestion: "考虑内部增加吸声材料"
```

### 与硬件设计Agent的协作接口

```yaml
agent_id: agent.hardware.design
interface_type: 空间约束 + 接口锁定
protocol: IDF/EMN/EMP + JSON约束定义

workflow:
  1. 硬件Agent提供PCB外形 + 关键器件高度 + 接口位置
  2. 结构Agent确认空间可行性，提出结构约束
  3. 双方锁定接口定义
  4. 任何变更走ECR流程

data_exchange:
  hardware_to_structure:
    format: "IDF 3.0 + JSON"
    content:
      pcb_outline: "2D轮廓坐标"
      pcb_dimensions: [length, width, thickness]
      keepout_zones:
        - zone_id: "Z01"
          position: [x, y, z]
          dimensions: [dx, dy, dz]
          reason: " tall_component"
      connector_positions:
        - connector: "USB-C"
          position: [x, y]
          height_above_pcb: 3.2
          orientation: "vertical"
      mounting_holes:
        - hole_id: "M1"
          position: [x, y]
          diameter: 3.2
          type: "M3_clearance"
      
  structure_to_hardware:
    format: "JSON约束定义"
    content:
      structural_constraints:
        max_pcb_thickness: 1.6
        pcb_support_spacing_max: 80
        connector_access:
          usb_c:
            opening_size: [10, 5]
            position_tolerance: "±0.2mm"
        thermal:
          heatsink_clearance_min: 5.0
          ventilation_area_min: 200
```

### 与测试Agent的协作接口

```yaml
agent_id: agent.testing
interface_type: 测试需求交付
protocol: JSON测试需求

workflow:
  1. 结构Agent完成DFM后生成结构相关测试需求
  2. 测试Agent纳入整体测试计划
  3. 测试Agent反馈测试结果，结构Agent分析结构相关问题

deliverables:
  structure_to_testing:
    test_requirements:
      - test_id: "STR-T01"
        category: "结构强度"
        item: "跌落测试"
        standard: "IEC 60068-2-32"
        condition: "1m自由跌落，6面各1次"
        criteria: "无裂纹、无松动、功能正常"
        
      - test_id: "STR-T02"
        category: "密封性能"
        item: "IP54防尘防水"
        standard: "IEC 60529"
        condition: "粉尘/喷水"
        criteria: "内部无尘/无水侵入"
        
      - test_id: "STR-T03"
        category: "振动"
        item: "随机振动"
        standard: "IEC 60068-2-64"
        condition: "5-500Hz, 1.5g rms, 每轴2h"
        criteria: "无结构损伤、无松动、功能正常"
        
      - test_id: "STR-T04"
        category: "声学结构"
        item: "气密性测试"
        standard: "内部标准"
        condition: "±500Pa压差，泄漏率<XX Pa/s"
        criteria: "密封满足声学容积稳定性"
```

### 与项目文档Agent的协作接口

```yaml
agent_id: agent.project.document
interface_type: 文档交付 + 模板使用
protocol: Markdown + 模板引用

workflow:
  1. 结构Agent按模板生成设计文档
  2. 项目文档Agent进行格式标准化
  3. 项目文档Agent归档到知识库
  4. 变更时更新文档并记录变更历史

document_templates:
  - template_id: "TPL-STRUCT-001"
    name: "结构设计说明书"
    sections:
      - 设计输入 (需求来源)
      - 设计约束 (空间/材料/成本)
      - 方案设计 (概念方案对比)
      - 详细设计 (3D模型说明)
      - FEM验证 (仿真结果)
      - DFM分析 (检查清单)
      - BOM清单
      - 问题与风险
      - 变更记录
```

---

## 输入/输出规范

### 标准输入

| 输入类型 | 格式 | 来源 | 验证规则 |
|----------|------|------|----------|
| 声学结构需求 | JSON Schema `声学结构需求` | 声学Agent | Schema验证 |
| PCB空间需求 | IDF + JSON | 硬件Agent | 几何一致性检查 |
| ID外观曲面 | STEP | 工业设计Agent | 几何质量检查 |
| 项目计划 | WBS JSON | 项目经理Agent | 里程碑逻辑检查 |
| 材料询价 | Excel/CSV | 采购Agent | 数据完整性检查 |

### 标准输出

| 输出类型 | 格式 | 目标 | 质量检查 |
|----------|------|------|----------|
| 3D模型 | STEP + 原生CAD | 多Agent共享 | 质量评分>95 |
| 工程图 | PDF + DWG | 制造/供应商 | 完整性检查100% |
| BOM | Excel + CSV | 采购/计划 | 与3D一致性检查 |
| DFM报告 | Markdown + PDF | 评审/制造 | 100项检查覆盖 |
| 设计文档 | Markdown | 项目文档Agent | 模板完整性检查 |
| 仿真请求 | JSON | 仿真Agent | Schema验证 |

### 质量检查清单 (自检)

```yaml
pre_delivery_check:
  - [ ] 3D模型质量评分 > 95
  - [ ] 工程图GD&T完整
  - [ ] BOM与3D模型零件数一致
  - [ ] DFM评分 ≥ 85 (或项目经理特批)
  - [ ] 所有接口JSON通过Schema验证
  - [ ] 变更记录完整 (如有变更)
  - [ ] 跨域影响评估完成 (影响Agent已通知)
  - [ ] 文件命名符合规范
  - [ ] 版本号正确标记
  - [ ] 归档路径已确认
```
