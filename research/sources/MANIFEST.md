# 第三方材料来源清单

**本目录及 `knowledge_base/adsp21569/bsp/` 下的 PDF 与 zip 多数【不入 git】**(见根 `.gitignore`)。
理由:①第三方版权材料不可再分发;②git 全量存储二进制,入库即永久占用每一次 clone。

**需要时按下表自取。** 已入库的少数几份为历史遗留(先于本清单提交),不再新增。

## 学术论文(`research/sources/papers/`)
除 Schroeder 1964 与 Alkaher 2022 外,均取自作者自存预印本服务器:
`https://ftp.esat.kuleuven.be/pub/sista/vanwaterschoot/reports/`

| 文件 | 报告号 | 正式出处 |
|---|---|---|
| vanWaterschoot_Moonen_2010_JAES_howling_detection_criteria | lirias 425246 | J. Audio Eng. Soc., Nov 2010 |
| vanWaterschoot_Moonen_2009_AES126_howling_detection_criteria_conf | 08-216 | AES 126th Conv., May 2009 |
| vanWaterschoot_Moonen_2009_EUSIPCO_assessing_AFC_performance | 09-01 | EUSIPCO 2009, pp.1997-2001 |
| vanWaterschoot_Moonen_2009_SigProc_AFC_audio | 07-30 | Signal Process. 89(11), 2009 |
| vanWaterschoot_Moonen_2007_TASLP_polezero_pareq | 06-177 | IEEE TASLP 15(8), 2007 |
| vanWaterschoot_Moonen_2008_ICASSP_AFC_warped_allpole | 07-177 | ICASSP 2008 |
| vanWaterschoot_Moonen_2007_dually_regularized_RPE_AFC_AEC | 07-49 | EUSIPCO 2007 |
| Rombouts_..._2007_JAES_PEM-AFROW_implementation | 05-258 | JAES 55(11), 2007 |
| Rombouts_..._2006_proactive_notch_filtering_AFC | 06-81 | IEEE Benelux/DSP Valley 2006 |
| Rombouts_..._2004_AFC_long_paths_nonstationary_source | 04-151 | EUSIPCO 2004 |
| Rombouts_..._2005_identification_undermodelled_RIR | 05-156 | IWAENC 2005 |
| Schroeder_1964_JASA_feedback_stability_frequency_shifting | — | JASA 36(9):1718-1724, 1964(CTO 提供) |
| Fifty_Years_of_Acoustic_Feedback_Control(未入库) | 08-13 | Proc. IEEE 99(2), 2011(CTO 提供) |

⚠ 预印本为 ESAT-SISTA 技术报告版,**引用页码/公式号须以正式版为准**。

## 仍缺(付费墙)
| 文献 | 用途 |
|---|---|
| Osmanovic, Clarke, Velandia, AES 123rd Conv. Preprint 7266 (2007) | 综述推荐的检出方法 |
| Spriet, Eneman, Moonen, Wouters, EUSIPCO 2008 | MSG 测法的第三方定义 |
| Haneda, Makino, Kaneda, IEEE TSAP 2(2), 1994 | 可能解释临界点分布的 4σ 过度分散 |

## 标准 / 厂家手册
ITU-T G.168 / P.340 / P.341 — 自 ITU 官网获取(付费或成员访问)。
ADI 手册、数据手册、应用笔记、参考设计 — 自 analog.com 按型号 ADSP-21569 / ADSP-2156x 下载。
竞品手册(dbx AFS2、Shure DFR22)— 厂商官网公开下载。
