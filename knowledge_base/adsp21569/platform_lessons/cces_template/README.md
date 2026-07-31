# ITC 定向音柱 — CCES 项目骨架

## 概述

ADSP-21569 SHARC+ 平台上运行的 Filter-and-Sum 子带波束形成器 C 代码框架。

## 目录结构

```
cces_template/
├── README.md            ← 本文件
└── src/
    ├── config.h         ← 全局参数宏（唯一配置入口）
    ├── main.c           ← 系统初始化 + 主循环 + DMA 回调框架
    ├── beamformer.h     ← 波束形成器接口定义
    ├── beamformer.c     ← 波束形成器核心实现
    ├── fir.h            ← FIR 滤波器接口（多相 + 分数延迟 + 整数延迟）
    ├── fir.c            ← FIR 滤波器实现（含 F-DSP-01 ×M 增益补偿）
    └── fir_coeffs.h     ← ★真实 scipy Kaiser FIR 系数（Q15，由 fir_design_verify.py 生成）
```

## 使用步骤

### 1. 导入 CCES 工程

在 CCES 中新建 ADSP-21569 工程，将 src/ 目录下所有文件加入工程。

### 2. FIR 系数（已就绪 — F-DSP-02 已修复）

`src/fir_coeffs.h` 已包含**真实 scipy Kaiser 设计系数**（互补差分低通滤波器组，
实测阻带 −58~−73dB），由 `sprint2/dsp/fir_design_verify.py` 生成，`beamformer.c`
已 `#include`。无需再手填占位系数。

如需重新设计（改截止/过渡带/阶数），重跑：

```bash
python3 sprint2/dsp/fir_design_verify.py   # 重新生成 fir_coeffs.h + reconstruction.png
cp sprint2/dsp/fir_coeffs.h cces_template/src/   # 更新到工程
```

> 注：`fir_coeffs.h` 提供 437 抽头全速率参考核（功能正确性验证用）。
> 量产落地推荐切换到 dyadic 树形半带核（63 抽头/级，算力 56 MMAC/s，
> 见 dsp_design.md「Critic 返工修订」节）。

### 3. 添加 math.h 依赖

fir.c 中 `frac_delay_fir_set_delay()` 使用了 `sinf()` 和 `sqrtf()`，
在 CCES 中链接 SHARC 数学库：
- Project → Properties → C/C++ Build → Libraries → 添加 `sharc_math`

### 4. 配置 SPORT/DMA

参考 SHARC Audio Toolbox 示例（`ss_tdm_loopback` 项目），
将 main.c 中 `sport_tdm_init()` 的伪代码替换为实际 CCES 驱动调用。

### 5. 关键参数调整

所有参数在 `config.h` 中修改：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `AUDIO_SAMPLE_RATE_HZ` | 48000 | 采样率 |
| `AUDIO_FRAME_SIZE` | 64 | 帧大小（samples） |
| `ARRAY_NUM_ELEMENTS` | 16 | 阵元数 |
| `ARRAY_ELEMENT_SPACING_MM` | 55 | 阵元间距（mm，L1 拆机实测 / DEC-S3-GEOM-01） |
| `BEAM_DEFAULT_STEER_ANGLE_DEG` | 0 | 默认波束指向角 |

## 算力预算（真实阶数，返工后）

| 指标 | dyadic 树形（推荐落地） | 全速率 437 抽头（参考实现） |
|------|----------------------|------------------------|
| 总算力 | **56.4 MMAC/s** | 1480 MMAC/s |
| 21569 保守口径 | 1500 MMAC/s | 1500 MMAC/s |
| 裕量 | **27×** | 1.0×（不可接受） |
| 核心波束 | 6.48 MMAC/s（< 100 CTO目标） | 27.6 MMAC/s |
| SRAM 占用 | **27.3 KB (1.6%)** | 127.8 KB (7.7%) |
| 重建平坦度(0.5-7kHz) | 0.004 dB（freqz 精确） | 0.004 dB |
| 系统延迟 | < 2.7 ms | < 2.7 ms |

> 当前 `beamformer.c` 使用全速率 437 抽头核作为"功能正确性参考实现"，
> 量产前切换到 dyadic 树形半带结构。详见 dsp_design.md「Critic 返工修订」。

## 待完成项（TODO）

- [x] ~~替换 FIR 系数占位符~~ → 已用 fir_coeffs.h 真实 scipy 系数（F-DSP-02 修复）
- [x] ~~增益补偿~~ → fir.c interpolate 已加 ×M 补偿（F-DSP-01 修复，C 级验证通过）
- [ ] 将参考实现切换为 dyadic 树形半带抽取（落地优化，算力 1480→56 MMAC/s）
- [ ] 实现 sport_tdm_init()（基于 CCES SPORT 驱动）
- [ ] 实现 sinf() 使用 SHARC math 库或 CORDIC 替代
- [ ] 硬件上验证 CPU 负载（GPIO 翻转 + 示波器）
- [ ] 添加 DRC/EQ 后处理模块
- [ ] 主循环添加波束指向控制接口（UART/SPI）
