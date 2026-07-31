# PX4 动态陷波参考件 — 第三方代码入库说明

## 来源与许可
- **上游**:PX4-Autopilot(https://github.com/PX4/PX4-Autopilot),取自 `main` 分支,取件日 **2026-07-31**。
- **许可**:**BSD 3-Clause License**,全文见同目录 `LICENSE-PX4.txt`(Copyright (c) 2012-2025 PX4 Development Team)。
- **合规核验(lead 2026-07-31)**:BSD-3 条件① 要求源码再分发须保留版权声明与免责声明 —— 四个源文件文件头**均含完整 BSD-3 声明**,已逐一核验(`GyroFFT.cpp` / `GyroFFT.hpp` "Copyright (c) 2020-2022";`NotchFilter.hpp` "Copyright (C) 2019-2021";`VehicleAngularVelocity.cpp`)。**原文一字未改**。
- **纪律**:本目录文件**只读参考**。任何改写/移植产物写到本项目自己的源码树,并在其文件头注明 "derived from PX4-Autopilot, BSD-3-Clause" + 保留上游版权声明。

## 取了什么、为什么
路线 DEC-0007 = 陷波式啸叫抑制(NHS)。PX4 的陀螺动态陷波与 NHS **同构**(实时找窄带峰 → 有限陷波器组去压 → 跟踪/回收),且已量产验证。详见 `research/D0c_nhs_scout.md` §1.6-1.10。

| 文件 | 行数 | 内容 |
|---|---|---|
| `GyroFFT.cpp` / `.hpp` | 743 / 176 | **检测器**:Q15 定点实 FFT(CMSIS-DSP)→ **Quinn 第二估计器 bin 内插** → SNR 判据(:514,与 PAPR 同构)→ 频带门 → 最近频率配对 → **0.25 bin 近邻豁免**(:525)→ 7 点中值 → **100ms 老化回收**(:632) |
| `NotchFilter.hpp` | 298 | RBJ biquad DF1 模板;**`setParameters(sample_freq, notch_freq, bandwidth)` 仅三参数、无深度** —— 已核实的缺口 |
| `VehicleAngularVelocity.cpp` | 981 | **陷波器组分配/回收**:索引绑定、0.1Hz 迟滞才重算系数、峰失踪即 disable、谐波间隔 ≥ 半带宽 |
| `SensorGyroFft.msg` | 15 | 峰频率/SNR 数据结构(每轴 3 峰) |

## ⚠ 使用前必读(三条)
1. **参数一个都不能抄**:PX4 场景 fs≈1kHz/N=256(分辨率 3.9Hz);我们 48kHz 照搬 N=256 得 187Hz 分辨率**不可用**,须 N=2048-4096。详见 D0c §1.10。
2. **它没有"该不该压"的判断**:陀螺域每个窄带峰都是噪声;我们域**大部分窄带峰是人声/音乐**。IMSD 判据与啸叫/人声区分**全部自研**。
3. **GPL 隔离纪律(R-AFC-3)**:Betaflight / ArduPilot 的同类设计是 **GPL-3.0**,**只读文档与 PR 讨论,严禁阅读或参考其代码**。本目录只放 BSD-3 的 PX4 件。

## 关联
DEC-0007(路线与风险 R-AFC-1 专利 / R-AFC-2 许可污染 / R-AFC-3 GPL 隔离)｜`research/D0c_nhs_scout.md`
