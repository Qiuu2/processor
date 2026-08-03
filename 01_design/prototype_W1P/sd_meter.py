"""频率加权对数谱失真 SD —— NHS 的**音质轴**(与 msg_meter 的增益轴配对使用)。

╔═══════════════════════════════════════════════════════════════════════════╗
║ 门禁状态:**未过门**。本文件未经独立 critic verdict,                        ║
║ 不得 release / 冻结 / 被下游引用 / 对外承诺。自测结论见                      ║
║ r68_sd_selftest_out.txt。                                                  ║
╚═══════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════
一、定义与一手出处(**已逐字核对 PDF 原文,不是转述**)
═══════════════════════════════════════════════════════════════════════════
    SD(t) = sqrt( ∫₀^(fs/2) w_ERB(f) · [ 10·log₁₀( S_d(f,t) / S_v(f,t) ) ]² df )

**出处 A(主引,与我们的用例同域=NHS)**:
  van Waterschoot & Moonen, "Howling Detection and Suppression ... ",
  **J. Audio Eng. Soc. 58(11), 2010,式 (32),页 937**。
  原文:S_d = short-term PSD of the **howling-compensated signal**,
        S_v = short-term PSD of the **source signal**;
        w_ERB(f) = "a weighting function that gives equal weight to each
        auditory critical band **in the Nyquist interval**, following
        **Table 2 of the ANSI standard S3.5-1997**"。

**出处 B(同一式子,HA-AFC 语境)**:
  van Waterschoot & Moonen, "Fifty Years of Acoustic Feedback Control",
  **Proc. IEEE 99(2), Feb 2011,式 (111),页 319**(PDF 第 33 页)。
  该处补齐了谱估计口径:"The short-term PSD is estimated as the **squared
  magnitude of the short-term DFT**, which is calculated using **50%
  overlapping data windows of length M = 2048 at fs = 16 kHz, or M = 4096
  at fs = 44.1 kHz**. The integration in (111) is then approximated by a
  **summation over the DFT frequency bins**. **Both the mean and maximum**
  value of the SD measure will be used in the evaluation."

**⚠ SD 的原始出处两篇综述都指向同一篇,且【不在本库】**:
  A. Spriet, K. Eneman, M. Moonen, J. Wouters, "Objective Measures for
  Real-Time Evaluation of Adaptive Feedback Cancellation Algorithms in
  Hearing Aids", **EUSIPCO 2008, Lausanne**(= 2011 综述 [161] = 2010 JAES [37])。
  ⇒ 本实现依据的是**两篇综述的转述**,不是 SD 的原始论文。[L2/综述原文]

═══════════════════════════════════════════════════════════════════════════
二、⚠ 溯源勘误(派单转述有误,以下以原文为准)
═══════════════════════════════════════════════════════════════════════════
`research/sources/papers/Eneman_etal_2009_EUSIPCO_objective_evaluation_feedback_reduction.pdf`
  1. **作者不含 Eneman**。首页抬头 = "OBJECTIVE EVALUATION OF FEEDBACK
     REDUCTION TECHNIQUES IN HEARING AIDS — **Ann Spriet, Marc Moonen,
     Jan Wouters**", EUSIPCO 2009, Glasgow。⇒ 文件名张冠李戴。
  2. **该文没有 SD**(全文 grep "distortion" = 0 命中)。它定义的是
     FSR(式1)/ TVC(式2,3)/ PCR(式4)/ ASG,**没有一个是 SD**。
  3. **该文没有给 w_ERB 的闭式**。原文只有一句:"The weight I_ERB,i gives an
     equal weight to each auditory critical band B_i **between 300 Hz and
     6500 Hz**, defined by the equivalent rectangular bandwidth (ERB) of
     auditory filters **[7]**",其 [7] = B. Moore, *An Introduction to the
     Psychology of Hearing*, 5th ed., 2003 —— **是教科书指针,不是公式**。
  ⇒ **本模块不声称"实现了 Eneman 的 ERB 闭式"**。库内无任何一手件给出该闭式。

  4. **"300–6500 Hz vs Nyquist" 不是同一个量的两种写法**:
     300–6500 是 **FSR**(另一篇论文的另一个测度)的加权带;同篇 TVC/PCR 用的
     又是 500–6500。SD 原文两处(2010 式32 / 2011 式111)**一致地**写 Nyquist
     interval,**彼此不矛盾**。
     ⇒ 本模块两列的正确命名是:
        `full` = **SD 原文口径**(0 – fs/2);
        `in`   = **我方选择**,带宽借自 FSR(300–6500 Hz)。
        **不得**把 `in` 说成"文献的另一种 SD 口径"。

═══════════════════════════════════════════════════════════════════════════
三、这个数到底在测什么(报数前必须先写这三句)
═══════════════════════════════════════════════════════════════════════════
**被测对象**:处理后信号相对**源信号**的**逐 bin 对数谱偏差**,按听觉临界带
              等权后求**加权均方根**,单位 dB。它是**频谱形状被改动了多少**
              的度量。

**混淆面(四条,必须随数一起报)**:
  1. **它不是可懂度/MOS,也不是"难听程度"**。它对偏差**平方**后求和 ⇒ 一个
     20 dB 的窄陷波和一个 2 dB 的宽倾斜可以给出相同的 SD,但听感完全不同。
  2. **⚠ SD 对偏差【方向】完全盲**:交换两个入参 (processed↔source) 会让
     10log₁₀ 比值整体变号,而 SD 取平方 ⇒ **数值逐位不变**(自测 M7 已实测证实)。
     ⇒ **SD 无法区分"挖了 20 dB"与"抬了 20 dB"**;也**无法**用它发现入参写反。
     ⇒ 故本模块签名为 **keyword-only**,从结构上堵死写反。
  3. **它不做时间对齐**。原文亦不做。处理链的群延时会被读成谱失真 ⇒
     **SD 会偏高**。陷波器有群延时 ⇒ 本表在深陷波下含一份延时贡献,未分离。
  4. **数值随频带口径变**:同一个 1 kHz 陷波,`in`(300–6500)与 `full`
     (0–24000)可差约 1.35×(权重被全带稀释)。⇒ **恒返回两列,不提供单值接口。**

**偏离声明(原文没写/我们改了的)**:
  - **M = 4096 @ fs = 48 kHz**:原文只给 16 kHz→2048、44.1 kHz→4096 两档。
    48 kHz 不在原文档位内,取 4096(窗长 85.3 ms,最接近原文 44.1 kHz 档的
    92.9 ms)。**记为偏离**。
  - **窗型 = Hann**:原文两处都只写 "data windows",**未指定窗型** ⇒ 我方选择。
  - **w_ERB 用 Glasberg–Moore ERB 闭式**,**不是** ANSI S3.5-1997 Table 2。
    ANSI 标准原件不在库 ⇒ **Table 2 变体不实现,报 N/A**(不查表、不拟合、不编)。
    **不得声称二者等价。**
  - **w(f) ∝ 1/ERB(f) 是推导,不是引文**:原文只说"每个临界带等权";临界带
    密度 = 1/ERB(f) 带/Hz ⇒ ∫_band w df ≡ const。这一步是我们推的。
  - **归一化到 Σp = 1**:原文未写。若不归一化,量纲为 dB·√Hz,且"平坦衰减
    X dB ⇒ SD = X"不成立。⇒ 归一化是被**自测 B**钉死的定义性选择。
  - **谱地板 / 帧门限**:原文未写。见 `sd_measure` docstring。

  - **平均时间窗 t_window 默认 None(全时长)= 我方选择**。**原文自己用的是
    30 s ≤ t ≤ 60 s**(JAES 2010 p.937,原文工作点,见 `T_WINDOW_JAES2010`),但那
    绑定在原文的仿真时序上(60 s / 四等长阶段各 15 s / t=45 s 路径突变)⇒
    **本模块不自动套用**。区别已在工作点向量里留痕(`t_window` vs `t_window_lit`)。

D6(工作点向量):每个 SD 数附完整工作点 + **每一项的来源身份证**
  (`workpoint['provenance']`:原文 / 原文·偏离 / 我方选择 / 我方推导),
  含 `{fs, M, hop, overlap, window, band_in, band_full, weighting_law, normalize,
      psd_est, integration, report, floor_db, gate_db, frame_time_def,
      t_window, t_window_lit, t_window_lit_binding, time_align, erb_formula, cite_sd,
      deviation, ansi_table2_variant}`。
[L2/综述原文 + L3/教科书闭式 + L1/无(未上板)]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

FS_DEFAULT = 48000.0

# `in` 列的带宽:借自 Spriet/Moonen/Wouters 2009 EUSIPCO 的 **FSR**(式1)加权带。
# ⚠ 这**不是** SD 原文口径(SD 原文 = Nyquist interval)。见模块头 §二.4。
BAND_FSR = (300.0, 6500.0)

# Glasberg & Moore 1990 的 ERB_N 闭式(f 单位 Hz):ERB(f) = 24.7·(4.37·f/1000 + 1)
# [L3/教科书闭式] —— 出自 B. Moore, *An Introduction to the Psychology of Hearing*
# (= Spriet 2009 的 [7]);**本库无一手件载此式**,亦**非** ANSI S3.5-1997 Table 2。
ERB_A = 24.7
ERB_B = 4.37

# 原文明确给出的 (fs → M) 档位。48 kHz 不在其中,见模块头「偏离声明」。
M_BY_FS = {16000: 2048, 44100: 4096}
M_FALLBACK = 4096

CITE_SD = ("van Waterschoot & Moonen 2010 JAES 58(11) 式(32) p.937 "
           "[同式: 2011 Proc.IEEE 99(2) 式(111) p.319]; "
           "原始出处 Spriet et al. EUSIPCO 2008 Lausanne (不在本库)")
CITE_ERB = ("Glasberg & Moore 1990 ERB_N 闭式,经 B. Moore 教科书 [L3]; "
            "**非** ANSI S3.5-1997 Table 2(标准原件不在库,该变体未实现)")

# ─────────────────────────────────────────────────────────────────────────
# 原文的平均时间窗 —— **这是原文的工作点,不是我们的选择**(留痕用)
# ─────────────────────────────────────────────────────────────────────────
# JAES 2010 p.937 原文:"We will evaluate the **mean SD, averaged over the time
#   interval 30 s ≤ t ≤ 60 s**, which corresponds to the preferential mode of
#   operation of the sound reinforcement system (because it allows for a high
#   electroacoustic forward path gain)."
T_WINDOW_JAES2010 = (30.0, 60.0)

# ⚠⚠ 该区间**绑定在原文自己的仿真时序上,不是可移植常数**。
# 原文仿真(JAES 2010 p.936 / Proc.IEEE 2011 p.318)= 60 s,**四个等长阶段各 15 s**:
#     0–15 s   增益 K1(若不做反馈控制则留 3 dB 增益裕度),让算法先部分收敛
#    15–30 s   增益 20log₁₀K(t) 线性升至 K2 = K1 + ΔK(**越过失稳点**)
#    30–45 s   增益固定在 K2
#    t = 45 s  反馈路径突变(话筒移位 1 m)
#    45–60 s   增益仍固定在 K2,新路径
# ⇒ **30–60 s = 第 3+4 阶段 = 增益已固定在抬高后的 K2 的那两段**,且跨过路径突变。
# ⇒ **台架时序不同,该区间就没有意义。故本模块【不自动套用】**:`t_window` 默认 None
#   (全时长),要用原文口径必须由调用方显式传入,且须先确认自家台架时序可比。
T_WINDOW_JAES2010_BINDING = (
    "绑定原文仿真时序:总长 60 s / 四等长阶段各 15 s / 增益于 15–30 s 线性升至 K2 越过失稳点 / "
    "t=45 s 反馈路径突变 ⇒ 30–60 s = 增益固定在 K2 的第 3+4 阶段。台架时序不同则不可套用。"
)

# ─────────────────────────────────────────────────────────────────────────
# 工作点每一项的**来源身份证**(治理铁律:每个数字带 L 标 / 分清原文与我方)
#   「原文」   = 两篇综述明文规定
#   「原文·偏离」= 原文有规定但我们改了(必须能说出为什么)
#   「我方选择」 = 原文没写,我们定的
#   「我方推导」 = 原文给了要求但没给公式,由我们推出来的
# ─────────────────────────────────────────────────────────────────────────
WORKPOINT_PROVENANCE = {
    "fs":             "我方选择(台架采样率)",
    "M":              "原文·偏离(原文只给 16k→2048 / 44.1k→4096;48k 不在档位)",
    "hop":            "原文(50% 重叠)",
    "overlap":        "原文(50% 重叠)",
    "window":         "我方选择(原文只写 data windows,**未指定窗型**)",
    "band_full":      "原文(Nyquist interval)",
    "band_in":        "我方选择(带宽借自 Spriet/Moonen/Wouters 2009 的 FSR,**非** SD 原文口径)",
    "erb_formula":    "原文·偏离(原文依 ANSI S3.5-1997 Table 2;我们用 Glasberg–Moore 闭式,**不声称等价**)",
    "weighting_law":  "我方推导(原文只说「每个临界带等权」;w ∝ 1/ERB 是我们推的)",
    "normalize":      "我方选择(原文未写;取 Σp=1,由自测 B 钉死)",
    "psd_est":        "原文(|短时 DFT|²)",
    "integration":    "原文(对 DFT bin 求和近似积分)",
    "report":         "原文(**mean 与 max 都要报**)",
    "floor_db":       "我方选择(原文未规定)",
    "gate_db":        "我方选择(原文未规定)",
    "frame_time_def": "我方选择(原文未规定帧时间戳如何定义)",
    "t_window":       "我方选择(默认 None=全时长)—— 原文自己用的是 30–60 s,见 t_window_lit",
    "t_window_lit":   "原文(JAES 2010 p.937)—— 但绑定原文仿真时序,见 t_window_lit_binding",
    "time_align":     "原文·同(原文亦不做时间对齐)",
}


def erb_hz(f):
    """Glasberg–Moore ERB 带宽(Hz)。f 可为标量或数组。[L3/教科书闭式]"""
    return ERB_A * (ERB_B * np.asarray(f, float) / 1000.0 + 1.0)


def default_M(fs):
    """按原文档位取 M;fs 不在档位内则回退 4096 并**报出偏离**。

    返回 (M, deviation_note)。deviation_note 为 None 表示无偏离。"""
    fs_i = int(round(float(fs)))
    if fs_i in M_BY_FS:
        return M_BY_FS[fs_i], None
    return M_FALLBACK, (
        f"fs={fs_i} Hz 不在原文档位 {sorted(M_BY_FS)} 内;取 M={M_FALLBACK} "
        f"(窗长 {1000.0 * M_FALLBACK / fs_i:.1f} ms,最接近原文 44.1 kHz 档的 92.9 ms)"
    )


# ═════════════════════════════════════════════════════════════════════════
# 窗平滑偏置闸门 —— **用 SD 做跨 bw_oct 比较前必须过这道闸**
# ═════════════════════════════════════════════════════════════════════════
# 由来:短时 DFT 的谱分辨率有限,陷波带宽逼近窗主瓣宽时 STFT 把陷波「抹平」
#       ⇒ **SD 系统性低估失真,且方向恒偏向更窄的档**(窄档白得一份不存在的音质优势)。
# 标定:r69_smear_grid_out.txt,30 格实测(bw_oct{1/5,1/8,1/12} × f0{200,500,1k,2k,5k}
#       × M{4096,8192},深度 −20 dB),与定义式解析积分逐格对拍。[L2/宿主仿真]
#
# ⚠ 闸门只管**能不能比**,**不做偏置修正** —— 实测偏置不是 ratio 的单值函数
#   (同 BW 不同 Q 可差 2 pp;同一格换深度 −6→−30 dB 再摆最多 6.8 pp)⇒ 不可回归成公式。
MAINLOBE_BINS_HANN = 4.0        # Hann 窗主瓣宽 = 4 个 DFT bin

# 闸门阈值(r69 实测标定,取各 ratio 段内**观测到的最大 |偏置|** 定档)
SMEAR_GATE_OK = 3.0             # ratio ≥ 3   ⇒ 实测 |偏置| ≤ 0.6%
SMEAR_GATE_CAUTION = 1.0        # 1 ≤ ratio<3 ⇒ 实测 |偏置| ≤ 2.3%
#                                 ratio < 1   ⇒ 实测 |偏置| 4.8% – 15.8%


def bw_oct_to_hz(f0, bw_oct):
    """倍频程带宽 → 绝对带宽 Hz:BW = f0·(2^N − 1)/2^(N/2)。

    ⚠ `bw_oct` 是**常 Q**:同一个 bw_oct 在不同中心频率上的绝对带宽差一个数量级
      (1/12 oct 在 200 Hz 是 11.6 Hz,在 5 kHz 是 288.9 Hz)⇒ 窗平滑偏置也随之差一个量级。"""
    n = float(bw_oct)
    return float(f0) * (2.0 ** n - 1.0) / 2.0 ** (n / 2.0)


def mainlobe_hz(fs=FS_DEFAULT, M=None, window="hann"):
    """分析窗主瓣宽(Hz)。"""
    if window != "hann":
        raise ValueError(f"主瓣宽只对 hann 标定过;window={window!r} 未标定,不外推")
    if M is None:
        M, _ = default_M(fs)
    return MAINLOBE_BINS_HANN * float(fs) / float(M)


def smear_ratio(f0, bw_oct, fs=FS_DEFAULT, M=None, window="hann"):
    """陷波带宽 / 窗主瓣宽。**这是判可比性的自变量。**"""
    return bw_oct_to_hz(f0, bw_oct) / mainlobe_hz(fs, M, window)


def smear_verdict(ratio):
    """单格判定 → (tag, 说明)。tag ∈ {OK, CAUTION, NOT-COMPARABLE}。"""
    if ratio >= SMEAR_GATE_OK:
        return "OK", "实测 |偏置| ≤ 0.6%"
    if ratio >= SMEAR_GATE_CAUTION:
        return "CAUTION", "实测 |偏置| ≤ 2.3%,且随陷波深度再摆最多 ~1.6 pp"
    return "NOT-COMPARABLE", "实测 |偏置| 4.8%–15.8%,且随深度再摆最多 ~6.8 pp"


def cross_bw_comparable(cells, fs=FS_DEFAULT, M=None, window="hann", depths=None):
    """**跨 bw_oct 档比较 SD 之前调这个。**

    cells  : [(f0_Hz, bw_oct), ...] —— 打算放在同一张比较表里的全部格子
    depths : 各格的陷波深度 dB(可选)。深度不同会**再**引入偏置差 ⇒ 必须同档。

    返回 dict(ok, min_ratio, verdict, reason, per_cell)。

    判据(r69 实测标定 [L2/宿主仿真]):
      · 全部 ratio ≥ 3            ⇒ **可比**(档间偏置差 ≤ 0.6 pp)
      · 最小 ratio ∈ [1, 3)       ⇒ **有条件**:要分辨的 SD 差异须 > 3 × 档间偏置差(可达 2 pp)
      · 最小 ratio < 1            ⇒ **不可比**(档间偏置差 6–10 pp,**方向恒偏向窄档**)
      · 深度不同档                ⇒ **不可比**(同一格换深度即摆最多 6.8 pp)

    ⚠ 偏置方向是**恒定的**:窄档被低估得更多 ⇒ 不过闸就比,会**系统性选中更窄的 bw_oct**,
      而那份优势是测量假象。这不是随机误差,多跑几次不会平掉。"""
    per, ratios = [], []
    for f0, bw_oct in cells:
        r = smear_ratio(f0, bw_oct, fs, M, window)
        tag, why = smear_verdict(r)
        per.append(dict(f0=float(f0), bw_oct=float(bw_oct),
                        bw_hz=bw_oct_to_hz(f0, bw_oct), ratio=r, tag=tag, why=why))
        ratios.append(r)
    if not ratios:
        raise ValueError("cells 为空")
    mn = min(ratios)

    if depths is not None and len(set(round(float(x), 6) for x in depths)) > 1:
        return dict(ok=False, min_ratio=mn, verdict="NOT-COMPARABLE",
                    reason=f"陷波深度不同档 {sorted(set(depths))} —— 深度本身即引入最多 6.8 pp 偏置差",
                    per_cell=per)

    tag, why = smear_verdict(mn)
    return dict(ok=(tag == "OK"), min_ratio=mn, verdict=tag,
                reason=(f"最窄格 ratio={mn:.2f} ⇒ {tag}({why});"
                        + ("可直接跨档比较" if tag == "OK" else
                           "档间偏置差恒偏向窄档,不得直接跨档比较")),
                per_cell=per)


# ─────────────────────────────────────────────────────────────────────────
# 四个注入点(seam)。**自测的变异测试替换它们**,以证明本度量对 broken 版会 FAIL。
# 它们同时也是这段计算的自然分解点,不是为测试硬塞的开关。
# ⚠ 生产代码里没有"切换成错误实现"的参数 —— 变异只能由自测 monkeypatch 完成。
# ─────────────────────────────────────────────────────────────────────────
def _erb_weights_raw(freqs):
    """未归一化权重 w(f) ∝ 1/ERB(f)。

    **推导(非引文)**:原文要求"每个听觉临界带等权"。临界带在 f 处的密度是
    1/ERB(f) 带/Hz ⇒ 取 w ∝ 1/ERB(f) 可使 ∫_{第 i 带} w df ≡ 常数,即每带等权。"""
    return 1.0 / erb_hz(freqs)


def _normalize_weights(w):
    """归一化到 Σp = 1。**被自测 B 钉死**:否则"平坦衰减 X dB ⇒ SD = X"不成立。"""
    s = float(np.sum(w))
    if not np.isfinite(s) or s <= 0.0:
        raise ValueError("权重和非正,无法归一化")
    return w / s


def _ratio_db(S_proc, S_src):
    """逐 bin 的 10·log₁₀(S_d / S_v)(dB)。

    ⚠ 分母**必须**是**源信号**谱。用处理后信号自比 = 假绿(治理 §假绿纪律)。"""
    return 10.0 * np.log10(S_proc / S_src)


def _reduce(p, dev_db):
    """带内归约:sqrt( Σ p·dev² )。sqrt 与平方都是定义的一部分(见式 32/111)。"""
    return float(np.sqrt(np.sum(p * dev_db * dev_db)))


def _time_mask(frame_times, t_window):
    """按平均时间窗选帧;t_window=None ⇒ 全选。

    ⚠ 原文(JAES 2010 p.937)自己用的是 30 s ≤ t ≤ 60 s,但**那绑定在它自己的仿真
      时序上**(见 `T_WINDOW_JAES2010_BINDING`)⇒ 本模块**不自动套用**,须调用方显式给。"""
    if t_window is None:
        return np.ones(len(frame_times), dtype=bool)
    t0, t1 = float(t_window[0]), float(t_window[1])
    return (frame_times >= t0) & (frame_times <= t1)


# ─────────────────────────────────────────────────────────────────────────
# 返回类型:**结构上不可能拿到"一个 SD"**
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SDBand:
    """单个频带口径下的 SD。**mean 与 max 都在,原文要求两个都报。**"""
    name: str
    lo_hz: float
    hi_hz: float
    n_bins: int
    mean_db: float
    max_db: float
    per_frame_db: np.ndarray

    def __float__(self):
        raise TypeError(
            "SDBand 不可退化为单个数:原文要求 mean 与 max 都报。"
            "请显式取 .mean_db 或 .max_db。")


@dataclass(frozen=True)
class SDResult:
    """SD 测量结果。**恒含两列**(`in` = 300–6500 我方选择 / `full` = SD 原文口径)。

    与 msg_meter.MSGMeter.msg() 的两口径接口同源:让"忘了标频带"在类型层无法再犯。"""
    band_in: SDBand
    band_full: SDBand
    n_frames: int
    n_frames_used: int
    workpoint: dict
    note: str = ""

    def __float__(self):
        raise TypeError(
            "SDResult 不可退化为单个数:SD 的数值随频带口径变(实测 in vs full 可差 ~1.35×)。"
            "请显式取 .band_in 或 .band_full,并在报数时标出用的是哪一列。")

    def describe(self):
        """一行式报数(带工作点),供写进 *_out.txt。"""
        wp = self.workpoint
        head = (f"SD[in {self.band_in.lo_hz:.0f}-{self.band_in.hi_hz:.0f}Hz] "
                f"mean={self.band_in.mean_db:.4f} max={self.band_in.max_db:.4f} dB | "
                f"SD[full {self.band_full.lo_hz:.0f}-{self.band_full.hi_hz:.0f}Hz] "
                f"mean={self.band_full.mean_db:.4f} max={self.band_full.max_db:.4f} dB")
        wpx = (f"    D6: fs={wp['fs']:.0f} M={wp['M']} hop={wp['hop']} "
               f"overlap={wp['overlap']:.0%} win={wp['window']} "
               f"frames={self.n_frames_used}/{self.n_frames} "
               f"floor={wp['floor_db']:.0f}dB gate={wp['gate_db']:.0f}dB")
        tw = ("全时长(我方选择)" if wp['t_window'] is None
              else f"{wp['t_window'][0]:g}–{wp['t_window'][1]:g} s(调用方显式给)")
        wpt = (f"    平均时间窗: {tw} | 原文自己用的是 "
               f"{wp['t_window_lit'][0]:g}–{wp['t_window_lit'][1]:g} s [原文·JAES2010 p.937],"
               f"**未自动套用** —— {wp['t_window_lit_binding']}")
        wpc = f"    ERB: {wp['erb_formula']}"
        wps = f"    SD : {wp['cite_sd']}"
        out = [head, wpx, wpt, wpc, wps]
        if wp.get('deviation'):
            out.append(f"    ⚠ 偏离: {wp['deviation']}")
        if self.note:
            out.append(f"    ⚠ note: {self.note}")
        return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────
def _stft_power(x, M, hop, win):
    """短时功率谱 = |短时 DFT|²(原文原话:squared magnitude of the short-term DFT)。

    返回形状 (n_frames, M//2+1)。
    ⚠ SD 是**比值**度量 ⇒ 任何一致的谱标定常数都会约掉,故此处不做 PSD 标定。"""
    n = len(x)
    n_frames = 1 + (n - M) // hop
    idx = np.arange(M)[None, :] + hop * np.arange(n_frames)[:, None]
    X = np.fft.rfft(x[idx] * win[None, :], axis=1)
    return (X.real ** 2 + X.imag ** 2)


def _floor_per_frame(S, floor_db):
    """按**各信号自身**每帧峰值做相对地板。

    ⚠ 必须"各自相对",不能用同一个绝对地板:若用源信号的绝对地板去截处理后信号,
    平坦衰减 X dB 的算例会在低能 bin 上被截成比值 1 ⇒ **自测 B 会被地板毁掉**。
    各自相对时,S_d = g²·S_v ⇒ max(S_d) = g²·max(S_v) ⇒ 地板同比缩放 ⇒ 比值**逐位守恒**。"""
    peak = np.max(S, axis=1, keepdims=True)
    return np.maximum(S, peak * (10.0 ** (floor_db / 10.0)))


def sd_measure(*, processed, source, fs=FS_DEFAULT, M=None, overlap=0.5,
               window="hann", band_in=BAND_FSR, band_full=None,
               floor_db=-120.0, gate_db=-80.0, t_window=None):
    """测 SD(式 32 / 式 111)。**恒返回两列 × (mean, max)**。

    ⚠ **keyword-only**:SD 对入参顺序写反完全盲(混淆面 2),故从签名上堵死。

    参数
    ----
    processed : 处理后信号(原文 = howling-/feedback-compensated signal),1-D
    source    : **源信号**(原文 = source signal),1-D,与 processed 等长
    fs        : 采样率 Hz
    M         : 窗长。None ⇒ 按原文档位取(见 `default_M`),48 kHz 会报偏离
    overlap   : 重叠率,原文 = 0.5
    window    : "hann"(我方选择,原文未指定窗型)或 "rect"
    band_in   : `in` 列频带,默认 300–6500(借自 FSR,**非** SD 原文口径)
    band_full : `full` 列频带,None ⇒ (0, fs/2) = **SD 原文口径**
    floor_db  : 谱地板(dB,相对各信号每帧峰值)。原文未写;防 log(0)。
    gate_db   : 帧门限(dB,相对源信号最大帧能量)。原文未写;剔静音帧。
    t_window  : 平均时间窗 (t0, t1) 秒,按**帧中心**时刻选帧;None ⇒ 全时长。
                ⚠ **原文自己用的是 (30, 60) = `T_WINDOW_JAES2010`**,但那绑定在原文
                  的仿真时序上(60 s / 四等长阶段 / t=45 s 路径突变)⇒ **本函数不自动
                  套用**。要用原文口径须显式传入,且先确认自家台架时序可比。

    ⚠ 不做时间对齐(原文亦不做)⇒ 群延时会被读成谱失真,SD 偏高。见混淆面 3。
    """
    d = np.asarray(processed, dtype=float).ravel()
    v = np.asarray(source, dtype=float).ravel()
    if d.shape != v.shape:
        raise ValueError(f"processed 与 source 长度不等: {d.shape} vs {v.shape}")
    fs = float(fs)

    deviation = None
    if M is None:
        M, deviation = default_M(fs)
    M = int(M)
    if len(d) < M:
        raise ValueError(f"信号长度 {len(d)} < 窗长 M={M},无法成帧")
    hop = int(round(M * (1.0 - overlap)))
    if hop < 1:
        raise ValueError(f"overlap={overlap} 过大,hop={hop}")

    if window == "hann":
        win = np.hanning(M + 1)[:M]          # periodic Hann
    elif window == "rect":
        win = np.ones(M)
    else:
        raise ValueError(f"未知窗型 {window!r}")

    Sd = _stft_power(d, M, hop, win)
    Sv = _stft_power(v, M, hop, win)
    n_frames = Sd.shape[0]
    freqs = np.fft.rfftfreq(M, 1.0 / fs)

    # ── 帧门限:剔掉源信号近静音的帧(那里的谱比值无意义)
    frame_pow = np.sum(Sv, axis=1)
    ref = float(np.max(frame_pow)) if n_frames else 0.0
    note = ""
    if ref <= 0.0:
        keep = np.zeros(n_frames, dtype=bool)
        note = "源信号全零 ⇒ 无可用帧,SD 报 N/A(nan)"
    else:
        keep = frame_pow >= ref * (10.0 ** (gate_db / 10.0))
        if not keep.any():
            note = "所有帧低于帧门限 ⇒ SD 报 N/A(nan)"

    # ── 平均时间窗:按**帧中心**时刻选帧(帧时间戳定义 = 我方选择,原文未规定)
    frame_times = (np.arange(n_frames) * hop + M / 2.0) / fs
    keep = keep & _time_mask(frame_times, t_window)
    if not keep.any() and not note:
        note = (f"时间窗 {t_window} 与帧门限筛后无可用帧(信号 {len(d) / fs:.3f} s,"
                f"帧中心 {frame_times[0]:.3f}–{frame_times[-1]:.3f} s)⇒ SD 报 N/A(nan)")

    # ⚠ 只在**选中的帧**上算比值:被剔掉的帧可能是全零(0/0 → nan)。若先全算再筛,
    #   numpy 会抛 RuntimeWarning,把一个**本该无害**的情形变成噪声,日后真出问题时
    #   反而看不见。⇒ 先筛后算,顺带省掉无用计算。
    idx_keep = np.where(keep)[0]
    if len(idx_keep):
        dev = _ratio_db(_floor_per_frame(Sd[idx_keep], floor_db),
                        _floor_per_frame(Sv[idx_keep], floor_db))
    else:
        dev = np.zeros((0, Sd.shape[1]))

    if band_full is None:
        band_full = (0.0, fs / 2.0)

    bands = []
    for name, (lo, hi) in (("in", band_in), ("full", band_full)):
        mask = (freqs >= lo) & (freqs <= hi)
        nb = int(mask.sum())
        if nb == 0:
            raise ValueError(f"频带 {name}=({lo},{hi}) 内没有 DFT bin(M={M} 太短?)")
        p = _normalize_weights(_erb_weights_raw(freqs[mask]))
        if len(idx_keep):
            per = np.array([_reduce(p, dev[j, mask]) for j in range(dev.shape[0])])
            mean_db, max_db = float(per.mean()), float(per.max())
        else:
            per = np.zeros(0)
            mean_db = max_db = float("nan")
        bands.append(SDBand(name=name, lo_hz=float(lo), hi_hz=float(hi), n_bins=nb,
                            mean_db=mean_db, max_db=max_db, per_frame_db=per))

    wp = dict(fs=fs, M=M, hop=hop, overlap=float(overlap), window=window,
              band_in=tuple(float(x) for x in band_in),
              band_full=tuple(float(x) for x in band_full),
              floor_db=float(floor_db), gate_db=float(gate_db),
              t_window=(None if t_window is None
                        else (float(t_window[0]), float(t_window[1]))),
              t_window_lit=T_WINDOW_JAES2010,
              t_window_lit_binding=T_WINDOW_JAES2010_BINDING,
              frame_time_def="帧中心 t_i = (i·hop + M/2)/fs",
              weighting_law="w(f) ∝ 1/ERB(f)(我方推导自「每个临界带等权」)",
              normalize="Σp = 1",
              psd_est="|短时 DFT|²(原文原话)", integration="对 DFT bin 求和",
              report="mean 与 max 都报(原文要求)",
              time_align="不补偿(原文亦不做)",
              erb_formula=CITE_ERB, cite_sd=CITE_SD, deviation=deviation,
              ansi_table2_variant="N/A —— ANSI S3.5-1997 原件不在库,未实现,未拟合",
              provenance=WORKPOINT_PROVENANCE)

    return SDResult(band_in=bands[0], band_full=bands[1], n_frames=n_frames,
                    n_frames_used=int(keep.sum()), workpoint=wp, note=note)
