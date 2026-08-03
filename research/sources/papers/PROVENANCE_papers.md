# 论文来源台账(2026-08-02)

来源:`https://ftp.esat.kuleuven.be/pub/sista/vanwaterschoot/reports/`(作者自存预印本)
除标注外,均为 **ESAT-SISTA 技术报告版**,与期刊/会议版内容可能有细微差异 ⇒ **引用页码/公式号须以正式版为准**。
"Fifty Years" 由 CTO 提供(IEEE Xplore 正式版)。

| 文件 | 原始编号 | 正式出处 | 对应综述引用 |
|---|---|---|---|
| Fifty_Years...(CTO 提供) | 08-13 | Proc. IEEE 99(2), 2011 | — |
| vanWaterschoot_Moonen_2010_JAES_howling_detection_criteria | lirias 425246 | J. Audio Eng. Soc., Nov 2010 | [63] |
| vanWaterschoot_Moonen_2009_AES126_howling_detection_criteria_conf | 08-216 | AES 126th Conv., May 2009 | [62] |
| vanWaterschoot_Moonen_2009_EUSIPCO_assessing_AFC_performance | 09-01 | EUSIPCO 2009, pp.1997-2001 | [82] |
| vanWaterschoot_Moonen_2009_SigProc_AFC_audio | 07-30 | Signal Process. 89(11), 2009 | [111] |
| vanWaterschoot_Moonen_2007_TASLP_polezero_pareq | 06-177 | IEEE TASLP 15(8), 2007 | [125] |
| vanWaterschoot_Moonen_2008_ICASSP_AFC_warped_allpole | 07-177 | ICASSP 2008 | [110] |
| vanWaterschoot_Moonen_2007_dually_regularized_RPE_AFC_AEC | 07-49 | EUSIPCO 2007 | [104] |
| Rombouts_..._2007_JAES_PEM-AFROW_implementation | 05-258 | J. Audio Eng. Soc. 55(11), 2007 | [103] |
| Rombouts_..._2006_proactive_notch_filtering_AFC | 06-81 | IEEE Benelux/DSP Valley, 2006 | [52] |
| Rombouts_..._2004_AFC_long_paths_nonstationary_source | 04-151 | EUSIPCO 2004 | [100] |
| Rombouts_..._2005_identification_undermodelled_RIR | 05-156 | IWAENC 2005 | [150] |

## ⛔ 仍缺(付费墙,需 CTO 提供)
| 综述引用 | 文献 | 为什么要 | 拦阻点 |
|---|---|---|---|
| **[2]** | Schroeder, "Improvement of acoustic-feedback stability by frequency shifting", JASA 36(9):1718-1724, 1964 | **"≈10 dB 理论上界"的源头**,整条 MSG 上界挂在它上面 | AIP Cloudflare + 付费 |
| [28] | Osmanovic, Clarke, Velandia, "An in-flight low latency acoustic feedback cancellation algorithm", AES 123rd Conv. Preprint 7266, 2007 | 综述推荐的检出方法 | AES E-Library 付费 |
| [161] | Spriet, Eneman, Moonen, Wouters, "Objective measures for real-time evaluation of AFC algorithms in hearing aids", EUSIPCO 2008 | 别人怎么定义 MSG 测法(对账我们的方法学) | 付费/RG 登录 |
| [134] | Haneda, Makino, Kaneda, "Common acoustical pole and zero modeling of room transfer functions", IEEE TSAP 2(2), 1994 | 可能解释我们那个 4σ 过度分散 | IEEE 付费 |

---

## ⛔ 溯源更正(2026-08-03,由 `sd-tool` 核一手件时抓获,四处全部成立)

**更正 1 · 文件名张冠李戴** —— `Eneman_etal_2009_*.pdf` → **`Spriet_Moonen_Wouters_2009_*`**。
该 PDF 首页作者为 **Ann Spriet, Marc Moonen, Jan Wouters**(EUSIPCO 2009, Glasgow),**没有 Eneman**。

**⛔⛔ 更正 2 · 该文【不含 SD】,也【不含 w_ERB 闭式】—— 它不是 SD 的来源**
- 全文 `distortion` 命中 **0**;它定义的是 **FSR / TVC / PCR / ASG**。
- 其 `I_ERB,i` 只有一句描述、**没有公式**,并指向教科书 **[7] B. Moore, *An Introduction to the Psychology of Hearing*, 5th ed., 2003**。
- **SD 真正出处 = Spriet, Eneman, Moonen, Wouters, EUSIPCO 2008 Lausanne —— 【不在库内】。**
  (Eneman 确为 2008 篇作者之一 ⇒ 推测是把 2008 Lausanne 与 2009 Glasgow 混成一篇。)
> **⇒ lead 于 2026-08-03 报给 CTO 的「ANSI 那处偏离不必接受,库里已有闭式」——【整条撤回】。**
> **⇒ 库内没有任何一手件给出 `w_ERB` 闭式;ANSI S3.5-1997 Table 2 仍不在库。**

**⛔ 更正 3 ·「300–6500 vs Nyquist」不是同一个量的两种说法**
`300–6500 Hz` 是 **FSR** 的加权带(另一篇的另一个测度;同篇 TVC/PCR 又用 500–6500)。
**SD 原文两处(2011 式111 / 2010 式32)一致写 Nyquist interval,彼此不矛盾。**
> **⇒ lead 据此立的「F32 在【文献内部】的实例」——【撤回】。那个不一致是我方把两个不同测度混为一谈造出来的。**

**更正 4 · `w(f) ∝ 1/ERB(f)` 是【推导】不是【引文】**,须写成显式推导并标注,不得冒充原文。

**⭐ 附带收获:更贴题的一手件就在库内**
`vanWaterschoot_Moonen_2010_JAES_howling_detection_criteria.pdf` **式 (32),页 937**,上下文**正是 NHS**(非 HA AFC),`S_d` 写作 "howling-compensated signal"。**建议以它为 SD 主引。** 另给工作点:**mean SD averaged over 30 s ≤ t ≤ 60 s**。
