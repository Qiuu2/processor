# D0c 定向调查:陷波式啸叫抑制(NHS)开源与工程惯例(草稿,待独立 critic 审)

- **缘起**:DEC-0007 锁定首攻=反馈抑制、8 点陷波。W0 的 `afc` 路是按广义 AFC 广撒网,路线锁定后需窄而深补搜。
- **执行**:`afc-scout`(claude-fable-5,2026-07-31),14 轮 WebSearch + 12 次定向抓取。
- **⚠ 定级纠正(作者终审)**:调查员原文将"厂商公开手册"标为 **L2**——按 `GOVERNANCE_CONFDSP §1` 这是**错的**:L2 专指仿真/工具实算(MATLAB/numpy/桌面跑),厂商标称/手册值等同 datasheet = **L4**。本文件所有厂商参数一律 **[L4/厂商手册]**,不得当实测。此纠正本身记为 C2 类越级拦截。
- 本地存档:`research/sources/vendor_manuals/{Shure_DFR22_manual.pdf, dbx_AFS2_manual.pdf}`。

---

## 1. 核心结论

**可商用 license 的完整 NHS 实现(检测+自动分配陷波的运行时状态机)——任何语言、任何生态,均未找到。**
GitHub topic `howling-suppression` 全量仅 2 仓库;LV2/VST/JSFX/Faust/Pd/SuperCollider/Teensy/ESP32 各生态扫过均无;商业闭源(Waves X-FDBK)除外。
→ **运行时代码 100% 自研**;能借的是**设计参数、系数公式、定点范式、测试素材**。

## 2. 可用构件(license 已核)
| 件 | license | 用途 | 限制 |
|---|---|---|---|
| **CMSIS-DSP** biquad DF1 Q15/Q31 + **32x64_q31 高精度版**(64-bit 累加、2.62 格式、postShift 缩放) | Apache-2.0(仓库页已核) | 定点 biquad **定标策略/guard bit/postShift 结构可整体照搬** | ARM 内在指令,SHARC+ 须重写;仅滤波核,无检测/分配 |
| **Ryuk17/noise-xorcist**(含 `HowlingAugment` 啸叫场景合成) | Apache-2.0(已核) | **检测器 ROC 测试床、测试信号生成** | Python/PyTorch,非运行时 |
| **RBJ Audio EQ Cookbook** notch 系数公式 | W3C Note(W0 已核) | 陷波系数 | 公式层,无障碍 |

**不可用**:aubio(GPL,只能离线);Mathilda11/Speech-processing、cirilln/Automatic_Feedback_Suppression、yiliang2333(均无 LICENSE = 保留权利);中文站二次转载合集(出处不明,不碰)。

## 3. 厂商工程参数惯例(**全部 [L4/厂商手册]**,D2 参数字典 NHS 章节的起草基线)

| 厂商/型号 | 陷波数 | 带宽档 | 深度与步长 | 回收/释放 | 检测 |
|---|---|---|---|---|---|
| **Shure DFR22** | 16/通道(默认前 8 固定 + 后 8 动态) | High-Q:加深时 Q→101(1/70 oct);**Low-Q:恒 Q=14.42(1/10 oct)** | 先浅后深,同频复发则加深(步长 dB 未公开) | 用尽时替换**最旧动态**;Auto Clear 1-99 小时后撤除;Lock 后冻结 | — |
| **dbx AFS2** | 24/通道(固定 0-24 可配,默认 12+12) | **恒带宽/恒Q 混合**:SPEECH <76Hz 恒 11Hz、≥76Hz Q=7;MUSIC/SPEECH <260Hz 恒 9Hz、≥260Hz Q=29;MUSIC <927Hz 恒 8Hz、≥927Hz Q=116 | — | **LIFT AFTER 5s–60min;按 3dB 步进缓抬试探,抬至 0dB 无复发才撤;抬升中复发立即回挂并重置计时** | 检测路 **Virtual HPF OFF/30-500Hz**;灵敏度 **±6.0dB** |
| **Sabine FBX-901** | 9(固定+动态) | **1/10 或 1/5 oct 恒Q**(-3dB 功率点度量) | 最深 **-50dB** | — | 频率分辨率 1/20 oct;**找到并消除一次啸叫典型 0.4s@1kHz** |
| **Biamp Tesira** | ≤16 bands | 浮动 Narrow=1/40 oct / Wide=1/10 oct | Max Depth 限深参数 | 固定+浮动 | — |
| **QSC Q-SYS** | **8-32 可配** | **1/5、1/10、1/20、1/80 oct,低频带宽下限 15Hz** | — | 动态降下后进 Standby,**Reclaim Time 5-120s** 防反复弹进弹出 | Feedback Threshold **-70~-20dB**;判据"幅度须超全谱平均一个内部定义量"(PAPR 类) |
| **Rane Note 158**(设计哲学,2005) | — | **宽而浅优于窄而深**(耐温度/路径漂移) | **单陷波目标衰减仅 2-3dB**;"若算法在放 20dB 以上深陷波,说明有问题" | 架构:固定先分配→浮动可回收→**全耗尽时宽带减益+可编程恢复时间兜底** | 弱谐波乐器(长笛类)是误检主源 |

### 3.1 ⚠ 增益收益的口径冲突(**须 CTO 知悉,勿对外承诺**)
- **Shure DFR22 手册**:GBF 改善预期 **6-9dB**;ring-out 时通常比首啸点提升 3-9dB;5-8 个陷波后收益递减。
- **Rane Note 158**:自动陷波仅 **2-3dB**;对比自适应 AFC **>10dB**、移频 **2-6dB**。
> 两者相差 3 倍以上。可能原因:测量口径不同(单陷波 vs 全系统)、厂商自宣传 vs 独立设计笔记、房间条件差异。**结论:任何 GBF 数字在本项目 L1 实测前不得进规格书或宣传**;D14 须把"MSG/GBF 提升"列为必测项并定义清楚测量方法。

## 4. 定点实现注意事项(有出处)
1. **结构**:定点用 **DF1**(4 状态),DF2T 是浮点首选(CMSIS-DSP 文档)。
2. **低频高Q精度**:极点近单位圆,状态字长需比输入多约 **2·log₂(fs/fc)** bit;48kHz 下 100Hz 陷波 ≈ 多 **18 bit** → 32-bit 样本必须 **64-bit 累加或误差反馈**。
3. **误差反馈/噪声整形**:Dattorro, JAES 36(11):851-878, 1988(CCRMA 免费 PDF);Rane《Second-Order Digital Filters Done Right》。
4. **系数动态更新防爆音**:通用方案(复域极零插值/coupled form)复杂;**NHS 有天然捷径且有厂商佐证**——新陷波从 0dB 渐深(Shure"先浅后深")、撤除按 3dB 缓抬(dbx LIFT),**深度小步变化 + DF1 状态连续即无爆音**,无需通用变系数方案。
5. **SHARC+ 侧**:ADI **EE-436**(ADSP-2159x,含 IIR accelerator 级联 biquad 示例码);低阶 IIR 用核心比 accelerator 更省周期(EngineerZone)。
6. CMSIS 32x64 Q31 实操红线:Q31 直接型输入须**预降 2 bit 至 [-0.25, 0.25)** 防累加器回绕。
7. **⚠ 定/浮点口径待确认**:DEC-0006 锁"定点",但 SHARC+ 原生 32/40-bit 浮点;若走浮点,低频高Q问题转为浮点状态精度问题,**biquad 状态建议双精度或保留误差反馈**。W1 须明确本模块口径。

## 5. 两条设计修正建议(有出处,应进 D2)
- **a) 纯恒Q 下探低频会窄到失效且定点精度崩** → 必须加**恒带宽下限**(dbx 8-11Hz / QSC 15Hz)。我们 PRD/竞品口径只有"1/10、1/5 恒Q",缺这条。
- **b) 参数字典预留更窄档位**(1/20、1/40、1/80 oct)给音乐模式,**V1 可不实现但字段留位**(改字典=改协议+UI+预设,代价高)。

## 6. 8 点决策的外部印证
厂商区间:Sabine 9 / QSC 8-32 / Biamp 16 / Shure 16 / dbx 24。**Shure 明言 5-8 个后收益递减** → 会议场景 8 点合理,DEC-0007 的选择有外部支撑 [L4]。恒Q 1/10 与 1/5 档位与 Shure Low-Q(14.42≈1/10 oct)、Sabine 完全对齐。

## 7. 结论:能借多少 / 必须自研什么
**能借(主要省在设计参数与验证侧)**:状态机全部设计参数无须凭空发明(固定+动态分配、round-robin 回收、渐深/缓抬 3dB 步长、reclaim 5-120s 防抖、低频恒带宽下限、检测 HPF 30-500Hz、灵敏度 ±6dB、单陷波 2-3dB 目标、-50dB 上限)——五家厂商互相印证;biquad 定点范式(CMSIS)+ 系数公式(RBJ)+ 检测判据公式(van Waterschoot,W0 已核)+ 测试素材生成(noise-xorcist)。
**必须自研(无可借代码)**:①谱峰跟踪 + 六判据检测器;②分配/加深/锁定/回收/兜底状态机;③SHARC+ 优化 biquad bank。

## 8. 覆盖与盲区
- **未找到**:可商用完整 NHS 状态机(任何语言);可商用六判据检测库;Sabine 官方白皮书原文(仅经销商数据页);Behringer FBQ2496 的 1/60 oct 声称 [待核];Shure DFR22 加深步长 dB 值(未公开)。
- **检索限制**:美区引擎,Gitee/知网站内未能深挖(中文生态仍是盲区,与 W0 结论一致)。
- 新增论文线索:"Robust and early howling detection based on a sparsity measure", J. Audio Speech Music Proc. 2025 — 是否随文放码 [待核]。
