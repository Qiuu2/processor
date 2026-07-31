# D0c 定向调查:陷波式啸叫抑制(NHS)开源与工程惯例(草稿,待独立 critic 审)

- **缘起**:DEC-0007 锁定首攻=反馈抑制、8 点陷波。W0 的 `afc` 路是按广义 AFC 广撒网,路线锁定后需窄而深补搜。
- **执行**:`afc-scout`(claude-fable-5,2026-07-31),14 轮 WebSearch + 12 次定向抓取。
- **⚠ 定级纠正(作者终审)**:调查员原文将"厂商公开手册"标为 **L2**——按 `GOVERNANCE_CONFDSP §1` 这是**错的**:L2 专指仿真/工具实算(MATLAB/numpy/桌面跑),厂商标称/手册值等同 datasheet = **L4**。本文件所有厂商参数一律 **[L4/厂商手册]**,不得当实测。此纠正本身记为 C2 类越级拦截。
- 本地存档:`research/sources/vendor_manuals/{Shure_DFR22_manual.pdf, dbx_AFS2_manual.pdf}`。

---

## 1. 核心结论(v2,2026-07-31 四路补搜后修订)

> **修订表述**(原 v1 写"均未找到",易被读成"不存在"):
> **无可商用 license 的完整 NHS 实现(检测+多陷波分配/加深/回收状态机);但存在 ①可商用的陷波器/组件级件 ②数个完整参考实现,均因 license 只能研读。**

补搜后已找到**四个完整 NHS 形态**,全部不可商用:Espressif `esp-adf-libs/HOWL`(闭源 blob + "仅限 Espressif 产品"许可)、`dariosanfilippo/automatic_larsen_suppression`(Faust,GPL-3.0)、`cirilln/Automatic_Feedback_Suppression`(Pd patch,无 license)、`yiliang2333`(Simulink,无 license)。
→ 但 **"运行时代码 100% 自研"这一判断已被推翻**(见 §1.6):**音频域之外**存在 BSD-3 的、已量产的同构实现(PX4 无人机陀螺动态陷波),其**检测器 + 陷波器组分配/回收**可直接移植,粗估可省 ~50% 工作量。

### 1.6 ⭐⭐ 结论推翻:PX4-Autopilot 陀螺动态陷波(BSD-3,可直接移植)
**最强命中不在音频域,而在飞控陀螺动态陷波。** lead 已**独立核验主源**(非采信转述):
- `LICENSE` 顶层 = **BSD 3-Clause**(Copyright 2012-2025 PX4 Development Team)✓
- `src/modules/gyro_fft/GyroFFT.cpp` 文件头 = BSD 3-clause 全文 ✓
- **SNR 判据(:514)**`10*log10((N-1)*peak_magnitude/(bin_mag_sum - peak_magnitude))` —— **与 PAPR(峰-均值比)公式同构,可直接取用** ✓
- **近邻豁免迟滞(:525)**`peak_close = fabsf(freq_adjusted - peak_frequencies_prev[peak_prev]) < resolution_hz*0.25f`,`if (snr_acceptable || peak_close)` —— **现成的 IPMP 式帧间持续性判据** ✓
- **老化回收(:632)**`timestamp_sample - _last_update > 100_ms → NAN` ✓
- 另有:Q15 定点实 FFT(CMSIS-DSP `arm_rfft_q15`)、**Quinn 第二估计器**做 bin 内插(:268)、7 点中值滤波、最近频率配对。

**可移植的四个文件**:`gyro_fft/GyroFFT.{cpp,hpp}`(检测器)、`mathlib/math/filter/NotchFilter.hpp`(RBJ biquad DF1)、`sensors/vehicle_angular_velocity/VehicleAngularVelocity.cpp`(**陷波器组分配/回收**:索引绑定、0.1Hz 迟滞重算系数防抖、峰失踪即 disable、谐波间隔 ≥ 半带宽)。
**移植难度**:低-中。C++ 但基本 C 风格;外部依赖仅 CMSIS-DSP(Apache-2.0);需剥离 uORB 消息层;带宽 clamp 与频带门按 48kHz 重标定。
**★ 已核实的关键缺口**:`NotchFilter::setParameters(sample_freq, notch_freq, bandwidth)` **仅三参数、无深度/衰减** [lead 核验主源] —— 全深陷波,我们要的"先浅后深/复发递进/静默回退"**全域无同构实现**,必须自研(见 §1.8)。

### 1.7 其他域可商用件(license 已核)
| 域 | 件 | license | 可用部分 |
|---|---|---|---|
| 工频去嗡 | **MNE-Python** `notch_filter(method='spectrum_fit')` | BSD-3 | **多锥度(DPSS)F 检验 + Bonferroni 校正**的统计判据——唯一"有统计显著性判据的自动窄带正弦检出";批处理,定位为慢速检测层非主环 |
| 工频去嗡 | MEEGkit `dss_line_iter` | BSD-3 | **"何时停手"判据**:残差降到拟合基线以下即停 → 对应"陷够深了吗" |
| 工频去嗡 | zapline-plus 的**阈值数值**(代码 GPL 不可用,论文数值可引) | — | PNPR 工程化初值:6Hz 滑窗、比左右各 1/3 邻域均值高 **>4dB** 判离群峰 [EEG 尺度,音频须重标定] |
| 生物声学 | **scikit-maad** `maad.rois` | BSD-3 | 谱图二值化 + 自适应阈值 + 形态学 + 最小面积 → 判据可照搬成 C |
| 正弦建模 | **LibXtract** | MIT,**纯 C** | `xtract_peak_spectrum` / `xtract_harmonic_spectrum` / 谱质心 → 供 PAPR/PHPR 计算,可直接嵌入 |
| ANF | yewentai ANF-LMS | MIT | 定点 Q 格式 ANF 骨架(课程作业级,目标频率写死,无检测器) |

**不可用(记录以免重复调查)**:PAMGuard(GPL-3)、silbido(**无 license**,学术金标准 tonal contour 追踪只能读论文)、Betaflight/ArduPilot(GPL-3,**设计必读、代码严禁抄**)、GNSS-SDR(GPL-3)、KalmANF(GPL-3)、sms-tools/openMHA(AGPL)、zapline-plus(GPL-3)。
**该领域未找到**:LOFAR/DEMON 被动声呐线谱检测无可用开源;SOGI-FLL / Regalia 格型 ANF 无可商用成熟 C 实现;音频域自动去嗡无"可商用+自动检测"实现。

### 1.8 六判据 ↔ 同构域对照(自研范围的精确边界)
| 判据 | 同构实现 | 结论 |
|---|---|---|
| PTPR 峰-阈值 | PX4 `MIN_SNR` + 频带门;PAMGuard 绝对阈值 | 可取用 |
| **PAPR 峰-均值** | **PX4 :514 公式完全同构** | **可直接抄** |
| PNPR 峰-邻域 | zapline-plus(6Hz 窗/±1/3 邻域/+4dB)、PAMGuard 五级噪声估计 | 阈值作初值,音频重标定 |
| PHPR 峰-谐波 | ArduPilot 谐波族、PX4 ESC-RPM 路径 | **反向用**:那边"是谐波就一起挂",我们"是谐波就别当啸叫" |
| IPMP 帧间持续 | PX4 最近频率配对 + 0.25bin 豁免 + 7点中值 + 100ms 老化 | 可直接移植(注意 §1.9 专利) |
| **IMSD 帧间幅度斜率** | **全域无对应物** | **必须自研** |
> IMSD 无处可抄有结构性原因:振动与工频干扰都是**稳态**的,那些域从不需要区分"正在长起来的啸叫"与"稳态存在的合法窄带信号"。**这正是啸叫检测的真正难点,也是我们必须自研的核心。**

### 1.9 ⚠⚠ 专利警示(须转法务,已入 decisions_log)
**US9794695B2 "Detection of whistling in an audio system"**,受让人 **GN Hearing A/S**,优先权 2009-12-29,**状态 active,预计 2032-03-03 到期**(同族 US8477976)[L4/Google Patents,调查员核到]。
权利要求核心:用**"平均频率(谱质心)在连续信号块之间的稳定性"**判定啸叫,辅以功率门限与频段限制(典型 1–6.5kHz)。
> **影响**:若我们把"频率稳定度"做成**主判据**,须法务过权利要求范围。注意 PX4 的 IPMP 式帧间配对本质也是频率稳定性判据——移植时需评估。**本条不是法务意见,是撞见的事实,转 CTO/法务。**

### 1.10 自研/移植工作量粗估 [L4/估算,未验证,仅供排期]
- 谱峰检测器 + 频率内插 + 帧间配对 + 中值 + 老化 → **PX4 直接移植 ~30-35%**(几十万台飞行器上跑过的定点实时代码)
- 陷波器 biquad + 系数更新迟滞 → PX4 + iir1(MIT)**~10%**
- 判据阈值初值(PAPR/PNPR)→ zapline-plus/PAMGuard 省调参试错 **~5%**
- 谐波判据谱特征基础件 → LibXtract(MIT,C)**~5%**
- **必须自研 ~45-50%**:IMSD 判据、**陷波深度递进与回退策略**、**啸叫 vs 人声持续元音/乐音的区分**、48kHz 会议场景阈值标定、与 AEC/AGC 的交互顺序(关联 A9)
> 一句话:同构迁移能整块拿走**检测器骨架**与**陷波器组管理骨架**;但**"判什么才算啸叫"和"陷多深"**没有任何同构域能代劳——因为只有我们的干扰会伪装成人声。

### 1.1 ⚠ 两条许可污染教训(本轮实证,写入选型纪律)
1. **chapro 仓库内部自相矛盾**:`LICENSE` 文件 = **CC0-1.0**,但 `README` 写 **CC BY-NC-SA**(NC=禁商用)。v1 的"chapro CC0 已核"**只核了 LICENSE 文件,判定推翻为存疑**。若 BY-NC-SA 为作者本意 → chapro 商用完全不可用;Tympan 自身 MIT 声明是缓冲但上游 provenance 存疑。**处置:挂风险声明,量产前须法务澄清或联系 BTNRH 书面确认。**
2. **许可洗白**:`hm-li0420/Howling-Suppression` 标 MIT,实为将无 license 的 `chenwj1989/pyHowling` 整包 vendor 后整仓改标——**该 MIT 无授权效力**。
> **纪律**:今后 license 判定不得只看 LICENSE 文件——须并查 README/文件头/上游来源;标称宽松许可但含第三方 vendor 代码者,一律按"来源存疑"处理。

### 1.2 ⭐ 结构三方独立佐证(方向性支持自研设计)
| 来源 | 说的结构 |
|---|---|
| van Waterschoot & Moonen(文献) | 六判据 PTPR/PAPR/PHPR/PNPR/IPMP/IMSD 组合检测 |
| **Espressif `README_HOWL.md`**(厂商侧,算法结构公开) | FFT → **PAPR/PHPR/PNPR(+可选 IMSD)** → 动态 biquad 陷波 + **全局增益回落** → 静音期渐进恢复 |
| **Rane Note 158**(设计哲学) | 固定→浮动→**耗尽时宽带减益兜底**;单陷波仅 2-3dB |
三个独立来源指向同一套结构(**多判据检测 + 动态陷波 + 增益兜底 + 恢复机制**),我们的自研设计按此展开有外部支撑 [L4]。

### 1.3 本轮新增可商用件
| 件 | license | 用途 |
|---|---|---|
| **`pareq.m`**(KU Leuven,van Waterschoot 本人) | BSD(资源页声明) | 极点-零点法设计二阶 IIR 参数 EQ/陷波——**六判据论文作者亲写的系数计算参考** |
| **yewentai ANF-LMS**(TMS320C5515) | MIT(LICENSE 原文已核) | C+汇编 **Q 格式定点陷波器范式**(仅单频追踪,无状态机) |
| **WebRTC AEC3 `anti_howling_gain`** | BSD-3 | 高带能量超低带即压增益的**宽带钳制思路**(非 NHS,思路级) |
| KUL PEM 自适应滤波 MATLAB | BSD | AFC 方法论参考(非 NHS) |
| michaellass/ladspa-notch-harmonics | MIT | 平凡静态陷波组,参考价值低 |

### 1.4 关键文献线索(verification 直接受益)
**van Waterschoot & Moonen, "Comparative evaluation of howling detection criteria in notch-filter-based howling suppression", AES 126th Convention (2009)** —— 比 v1 引的 JAES 2010 更对口(专讲 NHS 检测判据对比),**官网注明数据集+音频示例在线**(https://tvanwate.github.io/publications/)。若可获取 → D14 检测器测试素材有着落。

### 1.5 被证伪的假设(诚实记录)
- **"MATLAB File Exchange 会有一堆 BSD 啸叫抑制代码"** —— **假**。实测 "howling" 搜索 **0 结果**;acoustic feedback / feedback cancellation 方向亦无啸叫抑制条目。(此为 lead 的猜想,已证伪。)
- **"Larsen 术语盲区会有收获"** —— **真**。Faust 的 `automatic_larsen_suppression` 用 howling 系关键词完全搜不到。

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

## 8b. 四路补搜的覆盖证据(2026-07-31,证明"没找到"是搜过的)

| 路 | 打的洞 | 覆盖手段 | 结论 |
|---|---|---|---|
| `nhs-cn` | 中文生态(前两轮自认盲区) | ~20 轮中文检索:Gitee/GitCode/CSDN/知乎/电子发烧友 + 杰理·山景·炬芯·中科蓝讯·乐鑫·瑞芯微 + 声网·TRTC·网易云信·大象声科 + 学位论文 | **不推翻**。中文圈陷波 NHS 内容**实质单一源头 = pyHowling(无 license)**;国内商用实现全为芯片绑定二进制 |
| `nhs-terms` | 术语盲区 + 非 GitHub 托管站 | 逐个检索 Larsen(法/意/西)/feedback destroyer·eliminator/GBF·MSG/ring out/日韩德术语 ✕ GitLab·Codeberg·SourceForge·Bitbucket·**MATLAB FEX**·Zenodo·HuggingFace·OSF·CCRMA·KUL·kokkinizita | **不推翻**,但证实术语盲区真实存在(Faust 件仅 Larsen 可搜到) |
| `nhs-inside` | 大项目内部模块 | **28 个仓库 shallow clone + 全树 grep**(howling/larsen/feedback-suppress/adaptive-notch/afc/anti-howling),命中逐行核验 | **不推翻**。阴性名单:Ardour/Audacity/OBS/Jamulus/SonoBus/Mumble/linphone/FreeSWITCH/Asterisk/pjproject/baresip/Janus/mediasoup/PipeWire/PulseAudio/speexdsp/Elk Sushi/Bela/sc3-plugins/pure-data/pd-else/Csound/faustlibraries/DaisySP/Teensy Audio 等 |
| `nhs-isomorph` | 同构领域算法迁移 | 机械/振动(飞控陀螺)、工频去嗡(EEG/生物医学)、电力 ANF、生物声学/水声窄带、正弦建模、助听器 whistle detection;license 全核 GitHub API spdx + PX4 逐行核文件头 | **★ 推翻原结论**:PX4(BSD-3)可直接移植检测器+陷波器组管理,~50% 工作量可省。预期高的三域反而低于预期(声呐无开源、ANF 无可商用 C、音频去嗡无可商用自动检测) |

**检索基础设施受限(影响"未知未知"的兜底能力)**:grep.app 被 Vercel 盾拦、Sourcegraph 需登录、无 gh 凭证不能用 GitHub code search、Debian codesearch 需 key ⇒ **全局跨库代码索引缺位**,名单外项目只能靠 web 检索兜底;Gitee 站内搜索 JS 渲染抓不到、知乎 403、CSDN 521、知网付费墙 ⇒ 中文侧仍有残余盲区,需人工浏览器或国内网络补。

## 8. 覆盖与盲区(v1 原文,保留)
- **未找到**:可商用完整 NHS 状态机(任何语言);可商用六判据检测库;Sabine 官方白皮书原文(仅经销商数据页);Behringer FBQ2496 的 1/60 oct 声称 [待核];Shure DFR22 加深步长 dB 值(未公开)。
- **检索限制**:美区引擎,Gitee/知网站内未能深挖(中文生态仍是盲区,与 W0 结论一致)。
- 新增论文线索:"Robust and early howling detection based on a sparsity measure", J. Audio Speech Music Proc. 2025 — 是否随文放码 [待核]。
