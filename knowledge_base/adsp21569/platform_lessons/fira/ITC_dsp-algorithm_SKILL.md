---
name: dsp-algorithm
description: >-
  DSP algorithm expert for the ITC directional column speaker (ADSP-21569 SHARC+).
  Use for beamforming (DAS / subband / Dolph-Chebyshev) design, fixed-point (Qxx)
  porting and bit-exact verification, FIRA hardware-accelerator integration and
  postscale/Q-alignment, SHARC compute-budget / cycle / MCPS analysis, and the R14
  bit-exact closure work. Produces code as ASCII-only for the CCES SHARC target,
  change-blocks not full-file rewrites, and obeys CLAUDE.md governance (L-grading,
  C9/iron-rule-8 now RELEASED — R14 closed 2026-06-04; FIRA benefit enters selection
  under DEC-S4-C9-RELEASE-01's honest-denominator terms: pair with the §8 uncounted list
  (43-379 MCPS) and quote the official 3.07x, not 3.13x mixed-build).
---

<!-- CANONICAL source of record for the dsp-algorithm skill (DEC-S6-GOVERNANCE-SLIM-04,
     2026-07-20): the former 660-line copy at agents/dsp-algorithm/skill.md was reduced to a
     pointer — edit skill content ONLY here. Persona/memory: agents/dsp-algorithm/{profile,soul,memory}.md -->
<!-- 旧内嵌 frontmatter 存史: name "DSPAlgorithmAgent_Skill" / v1.0.0 / ITC Enterprise Multi-Agent System -->

# DSP 算法专家 Agent — 技能（项目焊接版）

> **本 skill 从真跑蒸馏**（`agents/dsp-algorithm/memory.md` + FIRA handoff `sprint4/dsp/fira/F4|F5|F7*` + `sprint5/H1|H2*` + `sprint2/docs/decisions_log.md`），**不是预制模板**。
> 项目化（roadmap#5，DEC-S6-GOVERNANCE-SLIM-05）：上一版是 2024 通用 DSP 模板 + **错平台**（ADAU1467/MVDR/GSC/HRTF/Ambisonics），已砍，见文末「已移除」。
> **结构**：**A** 项目真本事（逐条带出处）｜**B** 通用骨架（标注，非本项目蒸馏）｜**C** 缺口（保持薄、不编造）。
> **铁则**：每个数字挂 L 标（[L1 实测]/[L2 仿真]/[L3 解析]/[L4 占位]）；**绝不把 L2/L3/L4 说成"实测/measured"**。

---

# A. 项目真本事（蒸馏所得，每条带出处）

## A0. 锁定平台 & 几何（一切前提，先吃）
- **芯片 = ADSP-21569 SHARC+ 单核，≤1GHz float**（**不是双核**——旧 yaml `dual core` 是离群错值，ds:153 坐实单核）。原生 IEEE 32/40/64-bit float 硬件，但**路线锁定点**（MCPS 效率，非硬件限制）。`← memory.md:301,314; F7_MARGIN_MATERIAL.md:87; DEC-S3-PROC-01`
- **内存 = 640KB L1 + 1024KB L2；无 ARM/OS/网络/显示。** `← decisions_log.md:64（DEC-S1-004）,204（Gate-2 LOCKED）`
- **几何 = N16 / d55mm / L825mm / Dolph-Chebyshev −20dB / 8×A/B 对称串联 / broadside-only。** `← DEC-S3-GEOM-01`
- **信号链 = 单 mono 输入 → 8 通道各自 Dolph 加权；8 DAC 经 {c,15−c} A/B 串联驱 16 单元。无 16 独立通道，DSP 内无跨通道求和。** `← F5_8CH_HANDOFF.md:26; DEC-S4-R1-8CH-01`
- **FIRA 加速器** = 1024-word 系数 + 1024-deep 延迟线，4×32-bit MAC（定点 32×32→80-bit accum），定点最多 1024 taps（无多迭代），ACM 模式 TCB 链可无限通道；定点/浮点皆可。`← fira_fit_assessment.md:38-50`
- **帧 = 48kHz / 64 样本 → 750 fps；周期 1.3333ms = 1,333,333 cyc @1GHz**（实时硬底）。`← H2_PASSLINE_DERIVATION.md:87; M2_BEAM_WEIGHTING_SURVEY.md:78`
- **核算法 = 4 子带二进树 halfband FIR（63-tap 原型，3 抽/插级），每通道 9 个 FIR 段。** `← fira_fit_assessment.md:6,96; fira_tree.h:65 (FIRA_SEGS_PER_CHAN=9)`

## A1. FIRA 加速器集成配方（bit-exact 上板已达成 [L1/EZKIT]）
- **已达成**：FIRA 子带定点 bit-exact 上板——单通道 commit **`9d9fbec`**（golden crc `0x2E0D8C6E`，FIRA==核逐位）；8 通道 commit **`44a99e8`**（`g_f5_pass_all=1`，8 锚全中，8 golden 互异）。`← F4_BITEXACT_HANDOFF.md:12,18; F5_8CH_HANDOFF.md:11,18-19`
- **定点算术形状（唯一收敛口径）**：`Q15 系数 × Q31 态 → Q46(int64) 累加 → >>15 回 Q31`。新加权/系数一律沿用这个 >>15 截断点，不新开截断级。`← fira_fit_assessment.md:121 (tree_filterbank.c:6,99,104)`
- **集成 5 件套**（缺一出垃圾/假绿，逐条见 A3）：①postscale Q-align；②DECIMATION ratio 语义（输入计数 `ntaps+ratio*window-1`）；③INT/DEC **分采样域**存跨帧历史；④共用 scratch **段间清零**；⑤DMA 输出读前 **cache 只 invalidate 不 flush**（SHARC 用 `<sys/cache.h> flush_data_buffer`，非 ARM 的 `adi_cache_invalidate`）。`← decisions_log.md:626; F4_BITEXACT_HANDOFF.md:29-31`
- **验证粒度**：比对**依赖滤波的子带中间值 sb0–3**，**不是端到端**（`out==in` 端到端 CRC = telescoping 恒等，占位 FIRA 也 PASS，见 A5-FG1）。`← decisions_log.md:636`

## A2. Dolph 权重 & M2 beam pipeline
- **Dolph-Cheb −20dB 8 路 Q15 表**（冻结、三轨核过，勿板上重算）：`[28404,16525,20371,24031,27287,29934,31802,32768]`（下标 0=边→7=中心；SLL −20.00dB / BW@1k 29.269° **[L2/dual-track]**）。scipy/Barbiere 闭式/MATLAB 三轨 diff 2.3e-12、量化逐位同。`← F5_8CH_HANDOFF.md:25 (F5-C, commit ae4a837); sprint4/dsp/fira/dolph_w8_q15.h`
- **M2 beam pipeline（上板 PASS）**：输入级 `(w_q15·x_q31)>>15` 再进 FIRA；权重 = **+0 边际 MCPS**；可选子带 frac-delay 聚焦 = **+49.03 MCPS[L1]**。近场 1m 相对指向 18dB@2k/9dB@1k **[L1 近场·相对]**（**相对证据，非远场规格**，远场待 R3）。`← M2_BEAM_WEIGHTING_SURVEY.md:21,34; MEMORY test3-diagnosis-state`
- **通道→物理位置映射**（选项 B）：广侧 v1 权重下标重排即可（每路滤波相同）；**v2 加 frac-delay 聚焦后延迟也随位置变，须一并 permute**。`← M2_CHMAP_FIX; BEAM_POLARITY_CLOSURE`

## A3. 坑 + 触发器库（看到症状先查这里，各挂事故号）
- **端到端 CRC "PASS" 却验不了滤波** → telescoping 恒等假绿 → 取子带中间值 + 证占位版 FAIL。`← R14, decisions_log.md:633`
- **DECIMATION 段输出垃圾** → 输入计数用了 `ntaps+window-1`，应 `ntaps+ratio*window-1`（过读 D1/D1b）。`← F4_BITEXACT_HANDOFF.md:27`
- **"sb0 过 / sb1-3 帧边失配"** → INT 跨帧历史在**错采样域**（raw vs zero-stuffed），会伪装成 postscale 问题 → 分域存历史。`← F4_BITEXACT_HANDOFF.md:29`
- **postscale 读全零** → flush 把 memset 零写回盖了 DMA 数据 → 改 **invalidate-only**（A5 flush-back）。`← F4_BITEXACT_HANDOFF.md:30`
- **FIRA 残差呈 `0,−10,0,+22…`** → 抽取相位不一致（FIRA 偶相/核奇相），**可修相位，非"MAC 不同/需容差"**（曾否决 PM 此过度结论）。`← F4_BITEXACT_HANDOFF.md:32`
- **桌面裕量 33×/17× vs 板上 1.32×，差 ~25×** → 桌面按理想 1cyc/MAC 记账，板上真实 **30-50 cyc/MAC + cache/中断** → 用 30-50 包络，**禁理想 1cyc/MAC**。`← decisions_log.md:234; F7_MARGIN_MATERIAL.md:190`
- **compute 没改、只改无关全局/布局，输出却变** → 读未初始化/越界/stale（IO2）→ 哨兵 0x00/0xFF A/B 隔离。`← critic/SKILL.md:1135`
- **周期激励 count>0 就判"绿"** → 存在性 ≠ 正确性（62× 率错照绿）→ 加**率在带判据**（FG-B'）+ CCNT wall 实测率。`← memory.md:636`
- **裁"某态对 X 无害"** → 必须枚举该态 **ALL 消费者**逐项裁（ST1-E）；缘起 `s_h1_fa` 被 3 个 probe 以不同推进态消费致假失配。`← critic/SKILL.md:1137 (R14→R15)`

## A4. 量化判据 & 口径纪律（L 标齐——数字生命线）
- **实时硬底**：WCET < 1.333ms 帧周期。`← M2_BEAM_WEIGHTING_SURVEY.md:78`
- **正式阈值 = T2 ≥ 1.5×（带闭合条件）**。演进：≥10×（写死目标，源 [L2] 33×/17×）→ **板上 [L1] 推翻**（8ch 实测 1.32×）→ 临时 ≥1.0× → **FINAL T2≥1.5×**。现状（口径分清，勿混）：**整系统 best 2.14×[L4] 达标 / 纯算法 2.52×[L1]（L1 锚，非产品级）/ 系统-worst 1.46×[L4] 差 2.7% 未达**（待 WO-S5-H2 harness）。`← COMPUTE_LINE_CLOSURE_LANDING.md:15,38 (DEC-S4-CRITERION-01-FINAL)`
- **核 8ch FIRA 需求 = 347.45 MCPS [L1/EZKIT]**（463,273 cyc×750/1e6）；聚焦增量 **49.03 MCPS[L1]**（65,371 cyc）。`← H2_PASSLINE_DERIVATION.md:17,18`
- **纯核（无 FIRA）8ch = 0.92×[L1推导] @1GHz → 实时 FAIL**（F5-B 独立链板测 cyc 之比）→ **FIRA 从可选转必需**。`← F7_MARGIN_MATERIAL.md:117`
- **FIRA 加速：核-8ch 裕量 2.878× [L1推导]；官方加速比 = 3.07× [L1推导]（in-build）。3.13×（混 build）= 伪值，禁入选型/对外。** `← R14_RULING_PROPAGATION.md:44,60`
- **诚实分母（C9/DEC-S4-C9-RELEASE-01）**：任何 2.878×/3.07× **必须连体呈现 §8 未计入清单 43-379 MCPS → 整系统残余 1.38-2.56×[L4]，绝不单独示人。** `← R14_RULING_PROPAGATION.md:58-60`
- **板证因子 30-50 cyc/MAC（强制）**；kernel 权重环实测 8.51 cyc/MAC。`← decisions_log.md:234; M2_BEAM_WEIGHTING_SURVEY.md:34`
- **★口径纪律（R27/R42 病根，禁混三口径）**：①**wall-clock/需求 MCPS**（cyc×750/1e6，含加速器忙等，与 CCLK 无关）②**争用-ledger**（both_max−base）③**纯核 MMAC**（理想 1cyc/MAC，已退役）。三者互不可比，不得相互称"矛盾/达标"。`← F7_MARGIN_MATERIAL.md:29-56; H2_PASSLINE_DERIVATION.md:54`

## A5. DSP 假绿纪律（反 critic §12：测试必须依赖被测物）
- **FG1 telescoping 恒等（BLOCKER）**：`out==in` 代数恒等 → CRC 只验算术非滤波 → 取依赖滤波的中间值 + 证置零版 FAIL。
- **FG2 占位冒充（BLOCKER）**：compute 被 stub（memset0/#else/未接线）还 PASS = L4 冒充 L1 → **跑占位版确认其 FAIL**。
- **IO1 缓冲契约（BLOCKER）4 查**：输入 ≥ `ntaps+window-1` 已初始化；恰填 `out_count`；scratch 段间清零；DMA 输出读前 cache 失效。
- **IO2 布局敏感（BLOCKER）**：compute 没改、只改布局输出变 → 读未初始化/越界/stale → 哨兵隔离。
- **ST1/ST1-E 流式态（MAJOR/BLOCKER）**：有状态逐帧延迟线 vs 无状态块加速器——加速器路径是否保持跨帧态？裁"无害"须枚举全部消费者。`← 上列 FG1/FG2/IO1/IO2/ST1 全条 = critic/SKILL.md:1132-1137（§12）；§12 上板前拦下 6 处 F4_BITEXACT_HANDOFF.md:23-34`

## A6. 冻结文件 & 交付纪律
- **`tree_filterbank.c` 冻结**——任何改动重开 R14 bit-exact（同源纪律）。`← F7_MARGIN_MATERIAL.md:180`
- **交付**：ASCII-only（CCES SHARC 目标）；change-block 非整文件重写；只读比对；**独立 critic verdict 前不 commit**。`← 本 skill frontmatter；commit 纪律`

---

# B. 通用骨架（通用 DSP 方法，**非本项目蒸馏**；有用则用，别当项目本事）

## B1. 定点化通用法（Q 格式选择 / 溢出分析 / 精度验证）
- **Q 格式选择**：按信号动态范围定整数/小数位；系数×态相乘后累加位宽 = 两者之和，回写前截断（本项目具体口径见 A1 = Q15×Q31>>15）。
- **溢出分析**：逐级算最坏幅度增益，加饱和（SAT）或预缩放；FIRA 内部 80-bit accum 一般不溢，回写 Q31 才是截断点。
- **精度验证**：定点 vs 浮点偏差判据——线性算法 bit-exact 或 SNR>60dB（本项目取 bit-exact，见 A1）。

## B2. MATLAB → C 原型流程
- MATLAB/numpy 浮点原型 → 定点建模 → C 移植 → 板上 bit-exact 回归。原型与 C 须**同源同参**（本项目 Dolph 表即三轨同源，见 A2）。

## B3. 波束设计通用框架
- 数据无关波束（DAS/延时求和、幅度锥化如 Dolph-Cheb）= 本项目在用（A0/A2）。
- **自适应/超指向（MVDR/GSC/Frost 等）本项目不用**（固定广侧 Dolph、单 mono、无 16 独立通道）——见「已移除」；若未来立项差分-FIB/超指向，另起（见 C）。

---

# C. 缺口 / 未跑过（保持薄、不编造；要用先蒸馏）
- **角度偏转 = 未建 + 数学不可达**：{c,15−c} A/B 串联使 broadside 成硬件属性；需 16ch 硬件叉（Gate-2 不可逆）+ 触发 SC-S3-GEOM-01 d 重议。v1 只做聚焦。`← STEERING_HEADROOM_SCAN.md:6,34,57; DEC-S3-DSP-03, DEC-S5-STEER-V1-01`
- **EQ/限幅（O1）= 已定未上板**：精简 2-3 biquad 母线 EQ + **必需**每通道限幅器；EQ 未接线，成本 [L4] 29-60 MCPS，段数待 R3。`← eq_prd/EQ_PRD_DECISION_MATERIAL.md:3; H2_PASSLINE_DERIVATION.md:105`
- **T2 系统-worst（1.46×）未闭**：待 WO-S5-H2 DMA/ISR harness 上板收窄 WCET 保守项。`← COMPUTE_LINE_CLOSURE_LANDING.md:15,183`
- **真冷 cache WCET 未测**：H1 只是**下界**（I-cache 预热）；禁把 `g_h1_cyc_8ch_max` 当完整 WCET。`← H1_WCET_WORKORDER.md:57,119`
- **近场聚焦效力 = [L2 仿真] only**（焦点增益 4.85-8.09dB）；R3 消声室门开着。`← M2_BEAM_WEIGHTING_SURVEY.md:117; DEC-S5-V1-SCOPE-01`
- **子带-FIB = 未建**（项目内 A2 "FIB" 是窄用法 ≠ 文献差分 FIB）。`← MEMORY fib-cbt-literature`

---

# 已移除（项目化 roadmap#5 砍掉的错/无关内容，存档说明）
- **MVDR / GSC / 子带MVDR / Frost / PCA-ICA**（§1.2/1.4/1.5）：自适应波束，与固定广侧 Dolph、单 mono、无 16 独立通道**无关**。`← 原 SKILL.md:38-146`
- **HRTF（双耳）/ Ambisonics / 通用 DRC**（§3）：与 mono 广侧柱无关（本项目 O1 是精简母线 EQ+限幅，见 C）。`← 原 SKILL.md:243-326`
- **ADAU1467 / 294.912MHz / 600MIPS / dual-16bit SIMD**（§6.2）：**错平台**（本项目 = 21569 SHARC+ 单核，见 A0）。`← 原 SKILL.md:539-564`
- memory.md 里 2024 假测试/假项目（PRJ-2024）+ ADAU1467/HiFi4 yaml 亦属同类，另行清理（persona 层）。
