# DSP 上板迁移准备简报 — tree_filterbank → EV-21569-EZKIT (CCES)

**作者**：dsp-algorithm teammate | **日期**：2026-06-01 | **任务**：Sprint 3 R1 命门 P0（算力 [L2]→[L1] 实测路径）
**标签纪律**：本简报全为**桌面 [L2] 推断 + 待抽取清单**，不声称任何 SHARC [L1] 实测。MCPS 17×(16ch)/33×(8ch) 仍是桌面值，上板 cycle 实测才能转 [L1]。

> ⚠️ **入手即发现的记忆冲突（须 PM/CTO 知悉）**：`agents/dsp-algorithm/memory.md §2.3` 仍把 ADSP-21569 记为"**dual SHARC+ cores / 原生浮点 / 定点非必须**"。这与本任务 + `knowledge_base/ezkit/INDEX.md` + DEC-S3-PROC-01 锁定的"**单核 1GHz + 定点 Q15/Q31/Q46 路线**"直接矛盾。memory 是旧通用条目，**以 INDEX/任务为准**；建议 memory.md §2.3 打废止/更正 banner（防误引，POLICY-PROV-001 精神）。下文按**单核定点**口径推进。

---

## 1. 现状盘点

**已成型（桌面 [L2] 闭环）**：
- `tree_filterbank.c/h` 算法完整：3 级 dyadic 差分金字塔分析/合成，63 抽头半带原型，4 子带，broadside DAS（增益钩子 `q31_mul` 已留，当前全 1.0）。
- **已定点**：Q15 系数 × Q31 状态 → Q46(int64) 累加 → `>>15` 回 Q31。无浮点、无除法、无动态分配，缓冲全由调用者静态分配 —— 已是嵌入式友好写法。
- **已饱和（PF-4 FIX-01）**：`sat_i64_to_i32`（回量化点）、×2 内插点、`sat_add_i32`（合成端 int32 相加）三处钳位已加；半带核 Σ|h|=1.731>1 的对抗溢出已兜底，配 −4.8dB 系统 headroom 约定。`TFB_DISABLE_SAT` 回归开关保留 bit-exact 对照。
- **已验证**：PR 重建 ~300dB（代数 telescoping），Q31 算术 SNR 172–175dB，端到端定点 vs 浮点 74.6–78.7dB（Q15 字长主导），相位漂移 0。回归基准 `tree_verify.c` / `tree_verify_adversarial.c` + `tree_io_sat/unsat.csv` 已在库。
- **MCPS 实测挂钩已预埋**：`tree_filterbank.h` 的 `ENABLE_CPU_LOAD_MEASUREMENT` + `TFB_LOAD_START/STOP` 宏（cycle 计数器 / GPIO 翻转两法），目前是占位声明（`g_tfb_cyc_reg` 等待填实际寄存器）。

**迁移到 SHARC+ 还差什么**：
1. 平台寄存器/外设层全缺：SPORT TDM、DMA ping-pong、cycle 计数器寄存器、GPIO —— `cces_skeleton` 仅为**描述文档**，无可编译工程 + `.ldf` + 真实 ADI driver 调用。
2. **骨架与算法不一致需统一**：`cces_skeleton_description.md` 的 `dsp_main.c`/`bf_broadside.c` 仍用 **`float`** 写（Step1-6 全 float），且文件名是 `dyadic_analysis.c` 而非已成型的 `tree_filterbank.c`。要么把骨架改成调 `tfb_analyze/tfb_synthesize`（推荐，复用已验证定点核），要么废弃骨架的算法层。
3. 系数注入未接线：`tfb_set_coeffs()` 要喂 `fir_coeffs.h`（63 抽头 Q15），骨架里 `fir_coeffs.h` 还是空壳/历史 437 抽头核残留。
4. 8ch 并行未落地：现 `tfb_*` 是**单通道**接口；8ch 需循环调用 8 份 `TreeChannelState`（状态内存 ×8），骨架的 `dyadic_analysis_8ch` 尚未对接。

---

## 2. SHARC+ (ADSP-21569 单核) 上板关键技术点

| 维度 | 桌面 C 现状 | 21569/CCES 上要改 / 确认 |
|---|---|---|
| **内存布局 (.ldf)** | `int32_t a1[256]`… 等大局部数组在栈上（`tfb_analyze`/`synthesize` 各 ~数 KB 栈帧） | SHARC+ 有 L1（block0/1/2/3，最快、单周期）+ L2。**热点（半带延迟线 state[63]×8ch、DMA buf）放 L1**；系数/低速率级状态放 L2。大局部数组要么搬成静态分配落到指定 section，要么确认 L1 栈够大。`.ldf` 需显式 section 放置 + DMA buf 对齐。 |
| **SIMD / 双计算单元** | 朴素标量 MAC 循环 | SHARC+ 每核含可并行的乘加 + SIMD（PEx/PEy）。63 抽头半带卷积是 MAC 主体，靠编译器向量化或 intrinsics 把吞吐拉到 ~1–2 MAC/cycle。**半带核约半数抽头为 0**（.c 注释已点明）—— 零系数跳过表可把 MAC 数砍半，是头号优化。 |
| **FIR 硬件加速器** | 不用 | 21569 有 FIR/IIR 硬件加速器（待 datasheet 确认实际型号支持）。但本结构是**多级抽取/内插 + 帧内级联**，加速器更适合定长全速率 FIR，未必直接套用；**首次实测建议先用纯 C 核测基线 MCPS**，加速器作为后续优化项，不挡 R1。 |
| **TDM 8ch DMA** | 无 | SPORT0 TDM 主机，8 slot × 32bit @48k，BCLK 12.288MHz；DMA ping-pong 2 buf（2048B/buf）。DMA buf 必须 L1 + 字节对齐；帧回调里**只置 `g_frame_ready` 标志，算法不进 ISR**（WCET 可预测）。FSYNC 极性/主从模式 = 待核实 U4（拆机逻辑分析仪定）。 |
| **定点指令映射 (Q46 移位)** | `(int64_t)h*state` 累加，`acc>>15`，`(int64_t)a*b>>31` | SHARC+ 定点 MAC 用 40bit/64bit 累加器（MR 寄存器）。确认 `int64_t` 累加映射到硬件长累加器而非软件仿真；`>>15`/`>>31` 回量化的舍入模式（截断 vs 四舍五入）要与桌面一致以保 bit-exact 回归。`sat_i64_to_i32` 可能映射到硬件饱和模式位（省分支）。 |

**桌面写法在 CCES/21569 上要改的点**：
- `memset`/`<string.h>` → 确认 CCES runtime 支持，或换 ADI 优化版；
- 大栈局部数组 → 静态 + section 放置（见上）；
- `g_tfb_cyc_reg` 占位 → 换成 `*pREG_..._CCNT` 或 CCES `cycles()`/`__builtin_emuclk`；GPIO 占位 → `*pREG_PORTx_DATA_SET/_CLR`；
- 编译器 pragma（`#pragma loop_unroll`、`#pragma SIMD_for`）补到半带卷积循环；
- 字节序/对齐（`#pragma align`）给 DMA buffer。

---

## 3. 待抽取清单（资料入库 vendor_docs/ 21 份 PDF + bsp/ SDK 后）

**从 datasheet / HW reference (vendor_docs/)**：
- ADSP-21569 **数据手册** → 确认：单核确认、L1 各 block 大小与单周期访问规则、L2 大小、SHARC+ 定点 MAC 累加器宽度（40/64bit）与饱和模式位、是否含 FIR/IIR 硬件加速器及其约束。
- **HW Reference Manual** → SPORT TDM 寄存器、DMA 描述符链/ping-pong 配置、cycle/性能计数寄存器名（CCNT/EMUCLK/PM counter）、GPIO PORT 寄存器。
- **EV-21569-EZKIT manual + 原理图** → boot mode 跳线、ICE/JTAG 接口、板载 codec（ADAU 系列？）的 TDM 接线 + MCLK 来源（喂 SPORT 时序）、可用 GPIO 引出脚（GPIO 翻转法测 WCET 用）。
- **EE-notes** → 找"cycle counting / profiling on SHARC+"、"SPORT TDM example"、"DMA ping-pong audio"相关应用笔记。

**从 BSP / SDK (bsp/)**：
- **example project**：找 `SHARC Audio` / `TDM talkthrough` / `SPORT loopback` 直通例程 → 直接做第 0 步直通验证 + 抄 SPORT/DMA 初始化。
- **BSP 头文件**：`adi_sport.h`（确认 `ADI_SPORT_CONFIG` 字段名）、`adi_dma.h`、`cdef21569.h`/`def21569.h`（`pREG_*` 寄存器宏）、`platform`/`pinmux` 头（codec 引脚复用）。
- **CCES runtime / .ldf 模板**：21569 默认 `app.ldf` → 改 section 放置（L1 热点 / L2 系数）。
- **`cycles.h` / 性能计数 API**：确认 CCES 提供的 `cycles()` 或周期寄存器读取方式，替换 `g_tfb_cyc_reg` 占位。

---

## 4. 迁移到首次 cycle 实测的最短路径（分步）

> 目标：从现有 C 到板上测出 MCPS。**最短路径 = 先单通道、纯 C 核、bypass 信号链，只为拿 cycle 数**，功能完整性靠桌面回归已保证，不在首测阻塞。

0. **[前置]** CCES 2.12.1 安装 + license（资料已在手 `/home/it1234/下载/`）；资料入库触发本清单精读。
1. **建可编译 CCES 工程**：21569 空工程 + 默认 `.ldf`，把 `tree_filterbank.c/h` + `fir_coeffs.h`(63 抽头 Q15) 加入，`tfb_set_coeffs` 接线。先**纯编译过 + 桌面回归向量 `tree_io_*.csv` 板上跑通 bit-exact**（证明迁移无功能漂移）。
2. **接 cycle 计数**：`ENABLE_CPU_LOAD_MEASUREMENT=1`，`g_tfb_cyc_reg` 填真实周期寄存器（从 def21569.h 抽），`TFB_LOAD_START/STOP` 包住单通道 `tfb_analyze→(broadside 增益)→tfb_synthesize`。
3. **首测单通道 MCPS**：喂一帧 64 样本 Q31（先用片内测试向量，**不依赖 TDM**），读 cycles/frame → MCPS = cycles × FS / FRAME / 1e6。这是**最早能出的 [L1] 数**，不等硬件 bring-up TDM。（FRAME=64 @ Fs=48k → 帧周期 1.333ms，与 testing 简报口径一致）
4. **外推 + 实测 8ch/16ch**：单通道 ×8 / ×16（循环 8/16 份 `TreeChannelState`），实测满负载 cycles/frame，验证 WCET < 帧周期 1.333ms 且裕量目标 ≥10×。对照桌面 17×(16ch)/33×(8ch)[L2] → **R1 关闭判据**。
5. **[并行/后置]** 待 hardware-design bring-up TDM + DMA 后，接真实 8ch 输出链路做端到端，limiter/子带均衡为 P2 不挡首测。

**关键纪律**：步骤 1 的板上 bit-exact 回归是迁移正确性的门，**必须先过**再信步骤 3 的 cycle 数；否则测的是错算法的 MCPS。半带零系数跳过等优化在拿到**基线 MCPS 之后**再做（先测裸核，后优化，免得优化掩盖真实裕量）。

---

*交付物：本简报（PM 落盘）。无文件写操作，未上板，未生成 sub-agent。MCPS 数字仍 [L2]，待步骤 3-4 转 [L1]。*
