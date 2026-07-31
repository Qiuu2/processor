# 简报：EV-21569-EZKIT Cycle Count 测量方法学（R1 命门 P0 收口）

**文档**：PREP-TST-EZKIT-001 | **作者**：testing teammate | **日期**：2026-06-01
**目标**：把 4 子带 FIR filterbank 算力从 17×(16ch)/33×(8ch) **[L2 桌面/纸面]** 升级为板上 MCPS **[L1 实测]**
**被测对象**：`sprint3/dsp/tree_filterbank.c`（4 子带 dyadic 树形半带 FIR，Q15×Q31→Q46→Q31 定点，含 PF-4 节点①饱和修复）
**核心纪律**：本简报全部价值在于"能区分 L1 实测 vs L2 桌面估算"——下文凡具体寄存器/宏名未经 vendor_docs 核实者，明确标 **[待 vendor_docs/SDK 确认]**，不编造。

---

## 1. SHARC+ Cycle 测量手段（CCES / ADSP-21569）

四类手段，按"侵入性低→高 / 精度高→低"排列。具体符号待 SDK 头文件核实。

| 手段 | 机制 | 精度 | 适用场景 | 主要坑 |
|------|------|------|----------|--------|
| **核心周期计数寄存器**（SHARC+ 自由运行 cycle counter，疑 `EMUCLK`/`EMUCLK2` 或 `CCNT`，**名称待确认**） | 读寄存器差值 `end−start`，硬件级零开销 | **最高**（逐周期，1GHz→1cyc=1ns） | per-block 精确计数，L1 首选 | 64-bit 计数读高低两半防回绕；读寄存器本身有固定偏置，须空测标定扣除 |
| **`cycles()` / 等价 CCES 宏** | CCES runtime 封装上面计数器，成对调用取差 | 高（含宏调用固定偏置） | 代码内打点最方便，L1 推荐主用 | 宏名/头文件 **[待 SDK 确认]**；必须空测扣偏置；编译优化可能重排打点（用 `volatile`/内存屏障围栏） |
| **`__builtin_emuclk()` 类内建** | 编译器直发读计数器指令 | 高 | 替代宏、规避函数调用开销 | 内建是否存在/拼写 **[待 CCES 编译器手册确认]**；同样需扣偏置 |
| **CCES 统计 profiler** | 采样 PC 计数器统计热点分布 | **中/低**（统计采样） | 找热点、看函数占比，**不作 MCPS 终值** | 漏短路径、统计误差大；emulator 经 JTAG 引额外开销 → **只能定性** |

**计数污染源（协议必须控制）**：中断（ISR/DMA 完成中断计进去→关中断或剔除）；Cache/SRAM 布局（冷 vs 热 cache 差异巨大→取稳态块）；流水线/编译优化（`-O` 级、SIMD、stall→锁定配置并记录）；计数器读取偏置（空测扣除）。

---

## 2. 被测协议（per-block 周期 → MCPS @1GHz）

**被测函数**：`tree_filterbank.c` per-block 入口（4 子带树 + 8ch beamformer 求和）。

**block 定义**（与 dsp-algorithm 对齐：**B=64 sample/通道、Fs=48kHz、帧周期 1.333ms**；8ch 基线 / 16ch 对照上限，两档都测）。

**测量步骤**：
1. **冻结配置**：固定编译选项（优化级/SIMD/内存放置）、固定输入数据集、关无关中断；全部进 run log。
2. **空测标定**：背靠背读计数器测固定偏置 `c_overhead`。
3. **排除一次性 setup**：系数注入 `tfb_set_coeffs`、DMA/TDM 配置、首次冷 cache 块 **不计入**稳态值，单独记 `setup cycles`。
4. **稳态计时**：连喂 `N`(≥100) block，逐 block 记 `c_block=(end−start)−c_overhead`，丢弃前若干热身块。
5. **统计取值**：`avg=median(c_block)`（中位数抗离群）；`worst=max(c_block)`，并用**对抗满量程/多音激励**单独触发最坏路径（呼应 PF-4：节点①溢出只在对抗激励暴露，最坏路径须同类激励）。
6. **换算 MCPS @1GHz**：`blocks_per_sec=Fs/B`；`MCPS=cycles_per_block×blocks_per_sec/1e6`；占用率=MCPS/1000。**报 worst-case MCPS 为裕量判据**，average 仅参考。
7. **裕量**：`裕量×=1000 MCPS(1GHz预算)/worst-case MCPS`，与 [L2] 17×/33× 对位，得 R1 真值。

**报告口径**：worst-case 与 average 都列；8ch 与 16ch 都列；标注含/不含 setup；标注激励类型（DC 单位增益 vs 对抗满量程）。

---

## 3. L1 判据（防 PF-1 复发红线）

PF-1 教训 = 纸面 27×/49× 被当"已验证 LOCKED"。L1 实测必须**全部**满足，缺一即仍 [L2]：

- [ ] **真板**：物理 EV-21569-EZKIT 运行，非 simulator/桌面 host。
- [ ] **真时钟**：核实实跑 1GHz（或记录实际 CCLK 据此换算，不假设标称）。
- [ ] **真数据**：代表性音频激励（含对抗满量程多音，覆盖节点①最坏路径），非 DC=1 占位。
- [ ] **真计数器**：硬件 cycle 计数器/`cycles()`/内建取精确周期，**不**用 statistical profiler 充终值。
- [ ] **可复现**：≥100 block、≥3 次独立运行，报 median+max+离群处理；run-to-run 偏差记录。
- [ ] **偏置已扣 + setup 已隔离**。
- [ ] **配置可追溯**：编译选项/SIMD/内存布局/中断状态/激励/CCLK 全进 run log。

**红线**：① simulator/桌面值禁标 [L1]；② 每个 MCPS 挂"板号+日期+配置 hash+激励+N"否则不进 decisions_log；③ profiler 统计值永不作 R1 关闭依据；④ worst-case 未用对抗激励测得 → 不得声称 worst-case（PF-4 已证 DC 漏溢出，同理漏最坏周期）；⑤ 实测 vs [L2] 偏差需根因分析（流水线/cache/中断=PF-5 范畴），不得无解释吞掉。

---

## 4. 待抽取清单（资料入库后）

- **cycle 计数寄存器章节**：21569 HW Reference / SHARC+ Core 编程模型——确认计数器**确切名称/位宽/回绕**及读取指令序列。
- **`cycles()` 宏定义**：CCES runtime / SHARC Audio Toolbox 头（疑 `cycle_count.h`/`cycles.h`）——原型、依赖、固定偏置。
- **`__builtin_emuclk` 类内建**：CCES 编译器手册——是否存在、拼写、用法。
- **Profiler 文档**：CCES IDE User Guide profiler 章——采样机制、JTAG 开销（确认只作定性）。
- **计时 example**：`bsp/` benchmark/cycle-count 范例（SHARC Audio BSP 常带 talkthrough/FIR benchmark）——复用其计时围栏与偏置标定写法。
- **中断/cache 配置**：HW reference cache + 中断控制器章——测量窗口关中断、控制 L1/L2 cache 冷/热。
- **CCLK/PLL 实际频率**：EZKIT manual 时钟树/跳线——确认上板实际 CCLK 是否 1GHz（防"假设 1GHz"）。
- **TDM/DMA block 大小**：BSP audio framework——确认 per-block 实际 B 与通道数，对齐 §2。

---

**给 PM 的回流**：
1. **block 参数缺口已闭合**：B=64/Fs=48k/8ch·16ch（dsp 简报已给，口径一致）。
2. **最坏路径激励复用 PF-4 教训**：worst-case MCPS 必须用对抗满量程多音激励，DC=1 会同时漏溢出与漏最坏周期。
3. **CCLK 真值不可假设**：换算须用上板实测 CCLK，不可默认标称 1GHz——防 PF-1 具体落点。
4. **profiler 不可当终值**：只能定性找热点，R1 关闭须用硬件 cycle 计数器。
5. **相关文件**：被测源 `sprint3/dsp/tree_filterbank.c`；回归基准 `tree_verify.c`/`tree_verify_adversarial.c`；CCES 骨架 `sprint3/dsp/cces_skeleton/`。

---

*本简报为方法学准备，不含实测数据（资料未入库、未上板）。具体寄存器/宏名标 [待确认] 者须 vendor_docs/bsp 精读坐实后方可写入测试脚本。R1 关闭唯一合法路径 = 满足 §3 全部判据的 [L1] MCPS。*
