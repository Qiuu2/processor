# D0 技术雷达(v1.0 — 独立门已过:critic-w0 PASSED_WITH_MINOR 2026-07-30;待 CTO 第三关)

- 输入:W0A 扫描池(run wf_879bf05f-24f,2026-07-30,12 维度 197 候选)+ 反驳式核验结果(14+16+8+6+11+7+8+10+12+16+13+10 = 131 项核验对象,全部 exists=confirmed)。
- 修订原则:核验裁定优先于扫描原文;观望/规避项未核验,其 license/能力一律按「未核」处理。
- 全文纪律:一切能力/成熟度结论 = [L4/文献],未经本团队实测;license 结论分「已核主源」/「未核」两档;未核项禁入选型依据。

---

## 0. 结论速览

### 最值得站上去的肩膀(≤10)

1. **AEC 自研基座:SpeexDSP AEC(BSD-3 已核)+ Soo-Pang 1990 MDF + Valin 2007 学习率 + Enzner-Vary 2006 Kalman + Hänsler-Schmidt 专著**——文献-代码互证链完整(mdf.c 头注直接引用前两文)。警戒:官方 API 文档建议 filter_length 对应 100–500ms,项目 512ms 尾长属超范围使用,须当「待验证假设」实测,不是已核能力。
2. **WebRTC audio_processing 家族(AEC3 / NS / Transient Suppressor,BSD-3 + PATENTS 已核)**——AEC 双讲标杆参考、可移植的 NS(噪声估计+维纳增益+语音概率);法务备案须记「BSD-3-Clause + 专利授权(含诉讼终止条款)」,分发随附 LICENSE+PATENTS;Transient 已从主干删除,采用即锁历史版本自维护。
3. **通道条 DSP 全套依据:CMSIS-DSP(Apache-2.0 已核)+ RBJ Audio EQ Cookbook(W3C Note)+ Giannoulis 2012 压缩器教程 + ITU-R BS.1770-5 真峰值算法(PDF 已核)**——EQ/动态/限幅的公式与规范出处齐备,MIT 补充件(Signalsmith basics、Iir1、FFTConvolver)license 全干净。
4. **USB/存储三件套:TinyUSB(MIT 已核)+ FatFs(1-clause BSD 等价、明示允许闭源,已核)+ littlefs(BSD-3 已核)**——UAC1/UAC2 + MSC host + FAT 文件系统 + 内部掉电安全存储,零传染。
5. **OTA:MCUboot(Apache-2.0 已核)+ orlp/ed25519(zlib)或 Monocypher(CC0/BSD-2 双许可)**——MCU 档签名升级完整路线;Linux 档 RAUC(LGPL-2.1+)/U-Boot bootcount。
6. **自动混音自研规格书:Dugan 1975 JAES + US3992584A(已过期专利,公有领域,权利要求即算法规格)+ Biamp/Shure/QSC/BSS 厂商参数惯例(NOM 10log、off-atten -40dB、hold 1000ms、NOMA 1–6dB 可调等,全部主源核到)**——算法小、自研成本低、无授权障碍。
7. **啸叫抑制:van Waterschoot & Moonen JAES 2010 判据体系(PTPR/PAPR/PHPR/PNPR/IPMP/IMSD)+ Proc. IEEE 2011 综述 + chapro(CC0-1.0)/Tympan(MIT)两份可商用 AFC 参考码**——检测判据、陷波、AFC 三条线均有主源支撑。
8. **房间测量/自动 EQ 上位机线:Farina ESS + Müller-Massarani + pyfar/pyrato(MIT 已核)+ Ramos-López 2006 IIR 自动设计 + AutoEq 优化器(MIT 已核)**——「上位机算系数、固件只执行 biquad」路线的完整素材。
9. **控制协议设计参照系:QRC/TTP/SSC/Shure 命令集四份公开厂商协议文档(逐条主源核验)+ OSC 1.0(CC BY)+ tinyosc(ISC)/oscpack(MIT)/Ember+(BSL-1.0)可用编解码件**。
10. **上位机:Qt 6(LGPLv3 轨,Essentials 可闭源动态链接)或 Dear ImGui + ImPlot(MIT)+ mjansson/mdns(public domain)/QMdnsEngine(MIT)**——注意 Qt 路线频谱组件坑(见下)。

### 最危险的坑(≤3)

1. **「宽松 license」里的专利/条款暗礁(全部已核实):** WebRTC PATENTS 诉讼终止条款随代码传递(含 PulseAudio 提取版);chapro 为 CC0-1.0——CC0 明文不放弃专利权,它又是唯一拟直改进固件的 AFC 参考码,商用前须对 BTNRH 做 FTO 排查;ADI sam-baremetal-sdk 实为 BSD-3-Clause-**Clear**(明示不授予专利权);Bank parfilt 与 Novak 扫频作者站代码均非商用/无许可,只能按论文自写;Qt Graphs(Qt Charts 接替者)GPL-only,LGPL 社区版下频谱图必须自绘或购商业版;JUCE 闭源必须付费席位;FatFs 开 exFAT 需 Microsoft 专利授权(但嵌入式 Linux 内核 5.7+ 路径经 OIN 覆盖免费——平台选型改变该合规成本)。
2. **能力宣称与主源不符(核验推翻/降级,选型时不得引用扫描原文):** Mbed TLS 任何已发布版本**均无 EdDSA/Ed25519 签名**(PR #5800 关闭未合并,后续跟踪 #5819),若签名选型定 Ed25519 它不能当验签后端;REW 的 HTTP API 自动扫频**需付费 Pro upgrade**,不是免费能力;Windows usbaudio2.sys 官方明文「异步 OUT 仅支持显式反馈端点」「共享模式不支持 >8 通道」——UAC2 描述符设计的硬约束;SpeexDSP 512ms 尾长超官方建议区间;ITU-T P.862 已 superseded 且 ITU 于 2024-01-05 删除过期文本,PESQ/POLQA 参考实现商用授权未解决。
3. **生态空白无解,只能自研或商务:** 裸机/RTOS DSP 上不存在成熟宽松许可的完整 AES67 栈(现实路径 = flexPTP/PTPd + 自研 RTP/发现层,或 Dante OEM——而 Dante 的 64x64/Ultimo 2-4ch/DEP 平台等关键规格公开渠道核不到,须商务书面确认,生态规模 550 厂商/3800+ 产品(2023-09,Wikipedia)属实);「会议 AEC+自动混音+矩阵」品类无任何整机级开源对等项目;PA 域无生产级 license 友好的开源啸叫抑制库。

---

## 1. 雷达总表(12 维度,档位经核验修正)

图例:档位 = 采用候选 / 评估 / 观望 / 规避;license 栏「已核」= 反驳式核验到主源(附 evidence_url),「未核」= 观望/规避跳过项或核验未闭合,**禁入选型依据**。

### 1.1 aec(回声消除)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| SpeexDSP AEC (libspeexdsp, mdf.c) | oss | 采用候选 | 已核:BSD-3-Clause,无专利条款(https://raw.githubusercontent.com/xiph/speexdsp/master/COPYING) | MDF 频域自适应 AEC,纯 C、定点/浮点、尾长可配,嵌入式最常移植基线 | 低活跃;**512ms 尾长超官方建议 100–500ms 区间,收敛/算力须实测(待验证假设)**;双讲弱于现代方案;需自研后滤波补强 |
| WebRTC AEC3 | oss | 评估 | 已核:BSD-3 + PATENTS 专利授权(含诉讼终止条款)(https://webrtc.googlesource.com/src/+/refs/heads/main/LICENSE) | 生产级第三代 AEC:分带、内置延迟估计、非线性残余抑制、舒适噪声;双讲开源标杆 | C++/abseil 耦合深,裸机移植成本高,定位参考/上位机;主干含 neural_residual_echo_estimator 子目录,「固件无 NN」红线需构建裁剪 |
| webrtc-audio-processing (freedesktop 提取版) | oss | 评估 | 已核:BSD-3(Google 2011 原文,经 Debian sources 核验)(https://sources.debian.org/src/webrtc-audio-processing/latest/COPYING/) | AEC3 不拖全 WebRTC 树的独立构建途径(meson,1.x 含 AEC3) | 桌面向,固件不现实;上游 PATENTS 条款随提取版一并传递 |
| Soo & Pang 1990 MDF 论文 | paper | 采用候选 | N/A(论文)(佐证:https://github.com/xiph/speexdsp/blob/master/libspeexdsp/mdf.c) | 512ms 尾长分块频域自适应滤波的算法出处(IEEE TASSP 38(2):373-376) | 收敛控制简单,需叠加 Valin/Kalman 类步长控制 |
| Valin 2007 双讲学习率 | paper | 采用候选 | N/A(arXiv:1602.08044 开放获取)(https://arxiv.org/abs/1602.08044) | 连续学习率替代硬判决 DTD(IEEE TASLP 15(3):1030-1034),即 SpeexDSP 实际控制策略 | 强非线性回声下泄漏估计偏差 |
| Hänsler & Schmidt 专著 | paper | 采用候选 | N/A(Wiley-IEEE 2004, ISBN 9780471453468)(https://www.wiley.com/en-us/Acoustic+Echo+and+Noise+Control:+A+Practical+Approach-p-9780471453468) | AEC 全链路(自适应+控制+后滤波)设计总纲 | 付费书;扫描给的第二条 Wiley 链接格式可疑,以 p-9780471453468 为准 |
| Benesty/Gänsler NCC/FNCC 双讲检测 | paper | 评估 | N/A(论文)(https://www.sciencedirect.com/science/article/abs/pii/S0165168405003166) | 互相关类 DTD(2000 TSAP + 2006 FNCC) | FNCC 依赖 FRLS 中间量,MDF 路线需重推导;2001 频域 NCC 一篇未单独核到主源 |
| Enzner & Vary 2006 频域 Kalman | paper | 采用候选 | N/A(论文)(https://dblp.org/rec/journals/sigpro/EnznerV06.html) | 频域状态空间 Kalman 一体化步长控制/双讲免检测(Signal Processing 86(6):1140-1156) | 协方差调参是难点;「分块版 PBFDKF」为合理延伸非原文内容 |
| Breining et al. 1999 综述 | paper | 评估 | N/A(论文)(https://ieeexplore.ieee.org/document/774933/) | AEC 系统级架构综述(IEEE SPM 16(4):42-69) | 1999 年止,不含 Kalman 频域路线 |
| ITU-T G.168 | standard | 采用候选 | N/A(ITU-T 建议书,2007 起免费公开)(https://www.itu.int/rec/T-REC-G.168/en) | ERLE 定义、收敛/双讲测试序列与 CSS 信号;现行 (04/15)+2022 勘误 | 线路 EC 标准非声学 EC,限值不可照搬;ERLE/CSS 细节属领域共识,未逐条核文本 |
| ITU-T G.167(withdrawn)+ P.340 | standard | 评估 | N/A(ITU 建议书;G.167 Withdrawn 已核)(https://www.itu.int/rec/T-REC-G.167-199303-W/en) | 声学 AEC 性能指标历史框架;**核验修正:G.167 由 P.340(2000)(第1-5章)与 G.161(2002)(第6章)共同承接——验收规格须把 G.161 一并入列** | P.340 现行版条款未逐条核阅 |
| Microsoft AEC Challenge 数据集 | dataset | 评估 | 已核:代码 MIT;数据 AS-IS 逐源混合(LibriVox 公有领域/AudioSet CC-BY-4.0/Freesound CC0/DEMAND CC-BY-SA-3.0)(https://github.com/microsoft/AEC-Challenge) | >10,000 台真实设备录音+合成集,单讲/双讲,附全带宽 AECMOS(README 核实) | CC-BY-SA 子集传染、CC-BY 署名义务;消费级近场为主,会议室长混响覆盖不足,需自采补充 |
| pyaec (ewan-xu) | tool | 评估 | 已核:Apache-2.0(GitHub API)(https://api.github.com/repos/ewan-xu/pyaec) | 自适应滤波 Python 黄金参考合集(425 stars,2021-11 后未更新,API 核实) | 无双讲完整链路;个人维护,公式需自核 |
| PFDKF (echocatzh) | oss | 评估 | 已核:MIT(GitHub API)(https://api.github.com/repos/echocatzh/PFDKF) | 分块频域 Kalman Python 实现(58 stars,2023-01 后未更新) | 「对应 Kuech/Mabande/Enzner 2014」论文映射未从 README 独立核到,采用前自行比对公式 |
| AECMOS | tool | 观望 | 未核(评测脚本随仓库 MIT;ONNX 模型条款[待核],核验跳过) | 无参考回声质量评分 | 48kHz 专业场景校准性未知;模型条款未核 |

规避:PJSIP pjmedia——GPL-2.0-or-later,闭源固件不可链接;其 EC 后端可直接取 BSD 上游,无必要经由 PJSIP。
已剔除:无(14 项核验对象全部 exists=confirmed,无 misdescribed)。

### 1.2 anc(降噪)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| WebRTC Noise Suppression | oss | 采用候选 | 已核:BSD-3 + PATENTS(诉讼终止条款)(https://webrtc.googlesource.com/src/+/refs/heads/main/LICENSE) | 噪声谱估计+维纳增益+语音概率(主干 30 个文件实核);量产于 Chrome/Meet | 主干无定点 nsx(已移除);C++ 需移植;分发随附 LICENSE+PATENTS;48kHz 支持未逐行核验 |
| SpeexDSP preprocessor | oss | 采用候选 | 已核:BSD-3-Clause(https://raw.githubusercontent.com/xiph/speexdsp/master/COPYING) | 纯 C:DENOISE/AGC/VAD/DEREVERB/残余回声抑制控制项全实核;MCRA 类估计+Ephraim-Malah 增益 | 算法老,瞬态噪声无能为力;48kHz 低延迟需重调参数 |
| Martin 2001 最小值统计 | paper | 采用候选 | N/A(论文,IEEE TSAP 9(5):504-512)(https://www.scirp.org/reference/referencespapers?referenceid=909002) | 噪声 PSD 估计经典 | 噪声突升有 1–1.5s 跟踪滞后 |
| Cohen 2003 IMCRA | paper | 采用候选 | N/A(论文,IEEE TSAP 11(5):466-475)(https://cris.technion.ac.il/en/publications/noise-spectrum-estimation-in-adverse-environments-improved-minima-2/) | 恶劣环境噪声估计 | 实现细节多、调参敏感 |
| Cohen & Berdugo 2001 OM-LSA | paper | 采用候选 | N/A(论文;作者站 MATLAB 代码授权未核,不可假定可商用)(https://israelcohen.com/wp-content/uploads/2018/05/sp_Nov2001.pdf) | OM-LSA 增益+MCRA,避免音乐噪声(PDF 首页实核) | 增益下限等需按会议场景调优 |
| Ephraim & Malah MMSE-STSA/Log-MMSE | paper | 采用候选 | N/A(论文,DOI 10.1109/TASSP.1984.1164453 与 1985.1164550 双核)(https://api.crossref.org/works/10.1109/TASSP.1984.1164453) | 谱幅度 MMSE 增益规则源头 | 贝塞尔/指数积分需查表近似 |
| Cappé 1994 | paper | 采用候选 | N/A(论文,DOI 10.1109/89.279283)(https://api.crossref.org/works/10.1109/89.279283) | 音乐噪声机理与调参指导 | 无实现 |
| Gerkmann & Hendriks 2012 SPP | paper | 采用候选 | N/A(论文;作者页 PDF 实核;MATLAB 代码授权未核)(https://uol.de/fileadmin/user_upload/mediphysik/ag/speech/download/paper/gerkmann_unbiasedMMSE_TASL2012.pdf) | 免 VAD、低跟踪延迟噪声估计(摘要逐条核实) | 持续发言下轻微高估需护栏;原链接已 301 至 uol.de |
| WebRTC Transient Suppressor | oss | 评估 | 已核:BSD-3 + PATENTS(https://chromium.googlesource.com/external/webrtc/+/ad34dbe934/webrtc/modules/audio_processing/transient/transient_detector.cc) | Daubechies-8 小波包检测 + FFT 域抑制 + UpdateKeypress() 门控(源码实核) | **已实核确认从当前 main 删除**——采用=锁定历史 revision 自维护;误杀辅音需实测 |
| Talmon/Hirszhorn/Cohen/Gannot 瞬态抑制 | paper | 评估 | N/A(论文,两篇均核)(https://israelcohen.com/wp-content/uploads/2018/05/IWAENC2012_Hirszhorn.pdf) | 键盘/敲门瞬态抑制文献线(非 NN);无现成可商用开源实现的判断未发现反例 | 部分方法算力/缓冲不满足 <12ms;需自研 |
| Rangachari & Loizou 2006 | paper | 评估 | N/A(论文,DOI 10.1016/j.specom.2005.08.005)(https://api.crossref.org/works/10.1016/j.specom.2005.08.005) | 高非稳态快速噪声跟踪 | Loizou 书配套代码有出版社版权;utdallas PDF 链接证书失效 |
| Godsill & Rayner《Digital Audio Restoration》 | paper | 评估 | N/A(Springer 1998,DOI 10.1007/978-1-4471-1561-8)(https://api.crossref.org/works/10.1007/978-1-4471-1561-8) | AR 模型点击检测+插值修复 | 偏离线,实时化需原型验证 |
| athena-signal(滴滴) | oss | 评估 | 已核:Apache-2.0(LICENSE 原文)(https://raw.githubusercontent.com/athena-team/athena-signal/master/LICENSE) | C 语言 8 模块语音前端(AEC/HPF/DOA/MVDR/GSC/VAD/NS/AGC),NS 基于 MCRA(README 实核) | 仅 15 次提交、低活跃;16kHz 为主;「滴滴开源」系业界通识非仓库自述 |
| DEMAND 噪声库 | dataset | 采用候选 | 已核但元数据自相矛盾:Zenodo 权利页 CC BY 4.0 vs 描述文字 CC BY-SA 3.0——均允许商用;再分发衍生音频按更严 BY-SA 3.0 履行(https://zenodo.org/records/1227121) | 16 通道环境噪声,48k/16k 双版本(页面记 15 段录音;「18 种环境」为项目全集口径) | 对外发布混合音频前建议向作者澄清许可 |
| ETSI ES 202 396-1 噪声库 | standard | 评估 | 未核(公开目录无任何条款文件,[待核]仍未解决,**商用测试条款禁入依据**)(https://docbox.etsi.org/stq/Open/EG%20202%20396-1%20Background%20noise%20database) | 双耳/立体声实录背景噪声(目录三文件夹实核) | 目录 2026-07 现 'NEW LOCATION.txt',数据库迁移中链接可能失效;docbox 沿用旧编号 EG 202 396-1 |
| QUT-NOISE | dataset | 评估 | 已核:数据 CC BY-SA(版本号未标注,需下载包内 LICENSE.txt);代码 BSD(https://research.qut.edu.au/saivt/databases/qut-noise-databases-and-protocols/) | 长时实录环境噪声+QUT-NOISE-TIMIT 协议代码 | SA 对衍生再分发传染;会议室场景占比不高 |

规避:WHAM!——CC BY-NC 4.0 非商用,直接排除。
观望(未核):libspecbleach/noise-repellent(LGPL-2.1,固件静态链接不可行)、Microsoft DNS-Challenge(逐源混合含可能 NC,[待核])、RNNoise(NN,范围外)。
已剔除:无(16 项全部 confirmed)。

### 1.3 afc(啸叫抑制/反馈消除)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| van Waterschoot & Moonen JAES 2010 | paper | 采用候选 | N/A(AES 付费)(https://www.aes.org/e-lib/browse.cfm?elib=15738) | 啸叫检测判据统一框架(PTPR/PAPR/PHPR/PNPR/IPMP/IMSD,判据体系经 Alkaher 2022 p.968 交叉证实);多判据组合误检 33%→3% | 阈值需按 48kHz 扩声场景自标定 |
| van Waterschoot & Moonen Proc. IEEE 2011 | paper | 采用候选 | N/A(IEEE 付费)(https://www.semanticscholar.org/paper/d0819743fc22dd9825857b94a0d45489259eb3a2) | 声反馈控制 50 年总纲(99(2):288-327,DOI 10.1109/JPROC.2010.2090998) | 2011 年止 |
| chapro (BTNRH) | oss | 评估 | 已核:CC0-1.0——**注意 CC0 明文不放弃专利/商标权,无 Apache 式专利授权**(https://raw.githubusercontent.com/BoysTownOrg/chapro/master/LICENSE) | 助听器纯 C 库,afc_process.c NLMS 类 AFC;25 stars,pushed 2024-07-11 | 唯一可直改进固件的 AFC 参考——**商用前建议对 BTNRH 做 AFC 专利 FTO 排查(核验新增)**;助听器场景假设需重调 |
| Mounir et al. 2025 NINOS²-T | paper | 评估 | N/A(论文开放获取);配套代码 MIT(https://link.springer.com/article/10.1186/s13636-025-00399-1) | l2/l4 稀疏度早期啸叫/振铃检测+标注数据集,优于 6 个基线 | 代码仓仅 3 commits,论文复现级;需 C 化 |
| Gil-Cacho et al. EUSIPCO 2009 RANF | paper | 评估 | N/A(论文)(https://vbn.aau.dk/en/publications/regularized-adaptive-notch-filters-for-acoustic-howling-suppressi/) | 三并行正则化自适应陷波:零帧延迟、复杂度极低、纯音防护(摘要实核) | 无公开代码;多啸叫点行为需仿真 |
| Alkaher & Cohen 2022 | paper | 评估 | N/A(CC BY 4.0,PDF 版权页实核)(https://israelcohen.com/wp-content/uploads/2022/11/acoustics-04-00060.pdf) | 扩声场景两级时域啸叫检测(Soft Howling Detection + False-Alarm Detection) | 无公开实现 |
| Berdahl & Harris DAFx 2010 频移法 | paper | 评估 | N/A(CCRMA 公开 PDF)(https://ccrma.stanford.edu/~eberdahl/Papers/DAFx2010BerdahlHarris.pdf) | 频移平滑环路响应提升 MSG(混响环境有效,PA/会议适用;「数dB MSG」为 Schroeder 路线通行结论) | 论文自注:助听器场景收益不显著;仅适合语音模式 |
| Tympan_Library(BTNRH AFC 移植) | oss | 评估 | 已核:MIT(LICENSE 原文)(https://raw.githubusercontent.com/Tympan/Tympan_Library/main/LICENSE) | F32 浮点实时 AFC;**核验修正:扫描引用的 AudioEffectFeedbackCancel_F32.h 已 404,现行为 AudioFeedbackCancelNLMS_F32 与 AudioFeedbackCancelNFXLMS_F32(后者附 Neely 2022 白皮书,值得补充评估)**;149 stars,pushed 2026-07-28 | 强耦合 Teensy(Cortex-M7)/arm_math,需剥离 |

规避:openMHA——AGPL-3.0,固件与上位机均不可链接;chenwj1989/python_howling_suppression——无 license;marc1701/FACT——无 license 且停更。
观望(未核):dbx AFS2(商用专有,竞品规格基准:24 陷波/Q≈116/Fixed+Live)、Li et al. Sensors 2021(线性相位 FIR 陷波,群延迟与 <12ms 冲突)、yewentai/ANF(MIT,耦合 TI C5515)。
已剔除:无(8 项全部 confirmed)。

### 1.4 automix(自动混音)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| Dugan 1975 JAES 论文 | paper | 采用候选 | N/A(AES 付费)(https://www.aes.org/e-lib/browse.cfm?elib=2683) | 增益共享 automix 原理主源(JAES 23:442-449,主动/被动语音区、自适应阈值门控,摘要实核) | 工程参数需参照厂商文档调优 |
| US3992584A(Dugan 专利) | paper | 采用候选 | N/A(专利 Expired-Lifetime,1993-11-16 届满,公有领域,已核)(https://patents.google.com/patent/US3992584A/en) | 权利要求即算法规格:每通道衰减 dB=低于总和电平的 dB 数,总增益恒定(原文逐字核实) | 「Dugan」为在用商标,产品宣传不得使用 |
| Biamp Cornerstone 文档 | paper | 采用候选 | N/A(厂商公开文档,仅设计参考)(https://support.biamp.com/General/Audio/Automixer_basics) | NOM 10log(NOM)、每倍增 -3dB、上限 8麦/9dB、off-atten 默认 -40dB、hold 默认 1000ms、Isolation Factor 0–2.00(默认 1.00)——全部主源核到 | 行为级描述;Isolation Factor 在 Tesira 帮助页而非 basics 页 |
| Shure SCM820 指南 + insights | paper | 采用候选 | N/A(公开手册 ©2017 Shure)(https://www.avc-group.com/assets/products/Shure/pdfs/shure-um-scm820.pdf) | NAT/MaxBus/NOMA/Max NOM(1=filibuster 至无限)/Last Mic Lock On/主席优先(Override In)逐项手册核实;**核验修正:NOMA 为每倍增 1–6dB 可调,-3dB 只是惯例值** | 手册载 Patent Notice US 5,999,631 且 "Other patents pending"——勿复刻在效专利权利要求;gain-before-feedback 定量表述在 DFR 章节(6-9dB)非 NOMA 章节 |
| leafac/reaper Automixer JSFX | oss | 评估 | 已核:MIT(LICENSE 原文,©2023 Leandro Facchinetti)(https://raw.githubusercontent.com/leafac/reaper/main/LICENSE) | 带 track priority 的增益共享参考实现(64 通道=REAPER 每轨上限,README 核实) | **核验警示:系第三方 'original REAPER JSFX extension' 的衍生作品,上游 license 未核——仅可算法阅读,严禁直接复制代码入闭源固件** |
| QSC Q-SYS / BSS 门控 automixer 文档 | paper | 评估 | N/A(厂商公开帮助文档)(http://help.qsys.com/Content/Schematic_Library/auto_mixer_gated.htm) | 绝对/相对阈值(噪声地板跟踪)、hold、Depth、Max NOM、优先级(Q-SYS Auto/Priority/Filibuster;BSS 1-32 级)——主源核到 | **核验修正:两家主源均无独立 decay 参数(仅 hold/Off Gain),扫描 'hold/decay' 措辞略超主源**;原 q-syshelp.qsc.com 已 301 至 help.qsys.com |

规避:shadowfaxster/AutomixerVST——无 LICENSE,且依赖闭源 VST2 SDK。
观望(未核):Waves Dugan Automixer 手册(行为对标)、Perez-Gonzalez & Reiss 2009(音乐向)、De Man et al. 2017(综述)、Sound Devices Automatic Mixing 101(科普)。
已剔除:无(6 项全部 confirmed)。

### 1.5 dsp-blocks(基础 DSP 块)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| CMSIS-DSP (Arm) | oss | 采用候选 | 已核:Apache-2.0(顶层 LICENSE,含标准专利授权)——扫描所称「个别 aarch64 MIT」未单独核到,均宽松不影响(https://raw.githubusercontent.com/ARM-software/CMSIS-DSP/main/LICENSE) | FIR/biquad/FFT/矩阵,q7-f64 全类型,纯 C+Helium/Neon(官方文档核实) | 非 Arm 核只剩纯 C 路径;SBOM 全树扫描确认许可构成 |
| RBJ Audio EQ Cookbook(W3C Note) | standard | 采用候选 | N/A(W3C Note 2021-06-08,经 RBJ 授权,已核)(https://www.w3.org/TR/audio-eq-cookbook/) | 全套 biquad 系数公式(LPF/HPF/BPF/notch/allpass/peaking/shelf) | BLT 奈奎斯特翘曲需校正(实现细节) |
| SciPy signal | tool | 采用候选 | 已核:BSD-3(LICENSE.txt)(https://raw.githubusercontent.com/scipy/scipy/main/LICENSE.txt) | firwin/firwin2/remez/minimum_phase/freqz(官方文档核实);离线设计、系数导出,固件无牵连 | 线性相位群延迟约束属设计问题非工具风险 |
| Giannoulis et al. JAES 2012 | paper | 采用候选 | N/A(JAES 60(6):399-408,AES $33)(https://www.aes.org/e-lib/browse.cfm?elib=16354) | 数字压缩器设计权威教程(拓扑/检波/攻击释放) | 无 |
| ITU-R BS.1770-5 (2023) | standard | 采用候选 | N/A(PDF 免费下载已实核)(https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf) | Annex 2 真峰值五级流程(-12.04dB→4x 过采样→低通→绝对值→dB TP),含 48 阶 4 相 FIR 系数表(原文核实) | 4x 过采样算力+约 0.5–1ms 延迟计入 <12ms 预算 |
| Signalsmith limiter 文章 + basics 库 | oss | 评估 | 已核:MIT(dsp 与 basics 两仓)(https://github.com/Signalsmith-Audio/basics) | lookahead 限幅(peak-hold+FIR 平滑包络,max 100ms;Limiter 类在 basics 仓) | C++ header-only,定点移植需改写;单人维护 |
| Iir1 (Bernd Porr) | oss | 评估 | 已核:MIT(GitHub API spdx;**仓库根目录无 LICENSE 文件,直链 404,合规扫描注意**)(https://api.github.com/repos/berndporr/iir1) | Butterworth/Chebyshev/RBJ 逐样本 IIR,可导入 scipy SOS;2025-07 仍有提交 | 已移除椭圆滤波器等需数值优化的设计 |
| FFTConvolver (HiFi-LoFi) | oss | 评估 | 已核:MIT(仓库页)(https://github.com/HiFi-LoFi/FFTConvolver) | 实时分块 FFT 卷积 + TwoStage 非均匀分块(README 核实) | **「处理期零额外算法延迟」未在 README 明示,采用前以源码/实测确认(核验降级为待实证)**;FFT 后端需换平台优化版 |
| 音箱保护限幅文献组(Klippel JAES 2016 + AN28 + Linea) | paper | 评估 | N/A(JAES ©AES;AN28/Linea 白皮书公开,已实际下载核验)(https://www.klippel.de/fileadmin/klippel/Files/Know_How/Application_Notes/AN_28_Evaluation_of_Loudspeaker_Protection_Systems.pdf) | 热/位移保护知识源;**核验修正:AN28 实题 'Loudspeaker Limits and Protection Systems',是测试/评估笔记非限幅器设计;热限幅设计依据实为 Linea DE3457-01 + Giannoulis 框架** | Klippel JAES 2016 即专利密集自适应路线(KCS 前身)——自研走静态热/位移限幅绕开自适应权利要求 |
| Faust | tool | 评估 | 已核:编译器 LGPL-2.1+(COPYING.txt);官方 FAQ 明文生成代码不受 LGPL 约束、未修改标准库兼容闭源(https://faustdoc.grame.fr/manual/faq/) | DSP 描述语言→C 代码生成流水线 | 生成代码内联的每个 .lib 许可仍须逐一复核(GitHub spdx=NOASSERTION 系多许可混合) |
| MATLAB DSP System/Audio Toolbox | commercial | 评估 | 已核:商业专有(MathWorks 产品页)(https://www.mathworks.com/products/dsp-system.html) | FIR/IIR/多速率设计、定点建模、C 代码生成(含 ARM 部署) | MATLAB Coder 生成代码部署条款未核,采用前按当期条款核对 |

规避:KFR——GPL-2.0+/商业双许可,闭源固件不可用;chowdsp_utils——所需 DSP 模块恰为 GPLv3。
观望(未核):TI DSPLIB+MATHLIB(BSD-3 按 SDK 清单,TI 平台锁定)、XMOS lib_audio_dsp(XMOS Public Licence V1,限 XMOS 硅片)、ADI SigmaStudio(专有,ADI 锁定)、ESP-DSP(Apache-2.0,ESP32 算力存疑)、DaisySP(MIT,音乐向)、Cycfi Q(MIT,重模板 C++)。
已剔除:无(11 项全部 confirmed)。

### 1.6 aoip(网络音频)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| AES67-2023 标准 | standard | 采用候选 | N/A(标准文档;会员免费/非会员付费属实,「约 $50-100」价格未核到主源)(https://en.wikipedia.org/wiki/AES67) | PTP 1588-2008(2023 版增 1588-2019)、RTP L16/L24、48kHz 强制、SDP;2023-12 发布核实 | 发现/连接管理留白;2018→2023 逐条差异未核;**扫描的 aes.org 博客链接已 404(站点迁移 aes2.org),证据链接需更新** |
| Audinate Dante OEM 平台 | commercial | 采用候选 | 授权性质已核、**条款原文未核**(商业闭源 OEM;官方 legal 页 403,证据=登录墙行为+Wikipedia,不足「已核主源」档——F-01)(https://en.wikipedia.org/wiki/Dante_(networking)) | 会议市场事实标准;生态可更新为 550 厂商/3800+ 产品(2023-09);Brooklyn/Ultimo/Broadway 家族属实 | **「Brooklyn 3 64x64」「Ultimo 2-4ch」「DEP=Cortex-A Linux+在线激活」「AES67 兼容模式」均未能公开主源核到——采用决策若依赖这些规格,必须商务书面确认**;供应商锁定 |
| flexPTP | oss | 评估 | 已核:MIT(仓库页+API 双核,无附加条款)(https://github.com/epagris/flexPTP) | MCU 级 PTP:OC 主/从、E2E+P2P、L2/L4、802.1AS;移植 STM32F4/F7/H7、TM4C1294、FRDM-K64F,另有实验性 POSIX 移植 | 「<100ns 同步」为项目自述非第三方实测;需按目标 MCU 硬件时戳改底层;仅 PTP,RTP/发现层自研 |
| PTPd | oss | 评估 | 已核:BSD-2-Clause(COPYRIGHT 原文,无广告/专利条款;GitHub spdx=NOASSERTION 系多版权人聚合)(https://raw.githubusercontent.com/ptpd/ptpd/master/COPYRIGHT) | PTPv2 守护进程,微秒级(自述);历史移植广泛 | 上游停滞;README 自带 IEEE 1588 专利提示;移植 fork 质量参差 |
| GStreamer(rtpL16/L24 + GstPtpClock) | oss | 评估 | 已核:LGPL(官方 licensing FAQ;FAQ 未标版本号,通行 2.1;部分官方插件可链外部 GPL 库——逐插件过 license)(https://gstreamer.freedesktop.org/documentation/frequently-asked-questions/licensing.html) | 上位机 AES67 流监听/注入/互通测试;GstPtpClock=1588-2008 slave-only、无 BC/TC、软件时间戳(官方文档核实) | 产品级同步不够(软件时戳);rtpL16/L24 未单独直核官方模块页(Collabora 教程佐证) |
| AES67 PlugFest 报告 + AES-R16-2016 | paper | 评估 | 未核(获取条款[待核]未解决——aes.org docID 检索页全 404,采用前从 aes2.org 人工确认)(https://aimsalliance.org/wp-content/uploads/2019/04/AES67-SMPTE-ST-2110-Commonalities-and-Constraints-Updated-April-2019.pdf) | 官方互通测试实录;AES-R16=AES67 与 ST 2059-2 的 PTP 参数建议(AIMS 文档确认) | **核验更正:华盛顿 2015 报告编号为 AES-R15-2015(扫描漏标,勿记在 R12 名下)**;「伦敦 24 厂商 36 产品」与作者细节未核到 |
| Wireshark | tool | 采用候选 | 已核:GPL-2.0(README 原文,[待核]已闭环)(https://gitlab.com/wireshark/wireshark/-/raw/master/README.md) | PTPv2 解析器直核(Announce priority1/2、domainNumber 等);RTP/SDP/SAP 内置 | 仅内部研发用、不随产品分发,GPL 无碍 |

规避:linuxptp——GPL(版本[待核],因规避档未核;若架构含 Linux SoC 拟按独立进程解禁,须先补核版本+法务评估);bondagit/aes67-linux-daemon——GPL-3.0(可作内部测试对端,不入产品);ravenna-alsa-lkm——GPL-3.0 内核模块。
观望(未核):SMPTE ST 2110-30(广播扩展)、RAVENNA(开放技术声明)、Statime(MIT/Apache-2.0,Rust 1588-2019)、nmos-cpp(Apache-2.0,上位机/网关侧)。
已剔除:无(7 项全部 confirmed)。

### 1.7 usb-storage(USB 声卡与录音存储)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| TinyUSB | oss | 采用候选 | 已核:MIT(LICENSE 原文,无附加)(https://raw.githubusercontent.com/hathach/tinyusb/master/LICENSE) | UAC1/UAC2 设备类 + Host MSC,50+ MCU 家族(README/docs 核实) | Host 侧成熟度低于 Device;UAC2 多通道描述符需自调 |
| FatFs (ChaN) | oss | 采用候选 | 已核:FatFs License=1-clause BSD 等价,appnote 明示允许闭源商用再分发(https://elm-chan.org/fsw/ff/doc/appnote.html) | FAT/exFAT 文件系统,纯 C89;三项关键宣称(掉电损坏窗口/单文件 2^32-1 上限/exFAT 需 MS 专利授权)appnote 原文核实 | 无掉电安全保证,须 f_sync 策略;exFAT 合规见专条 |
| WAV 掉电恢复策略 | standard | 采用候选 | N/A(**核验定性修正:type 标 standard 实为行业做法+修复类文章,非正式标准**)(https://wav.repair/articles/recover-a-damaged-wav-recording) | 周期回写 header+事后按实际字节数重建(机理主源核实;bytes 4-7/40-43 偏移为通用 RIFF 常识,非来源支撑) | 无开源固件级参考实现,「采用」=采用该策略自研;需连同 FAT 目录项/簇链一起 f_sync |
| Windows usbaudio2.sys 公开资料 | standard | 采用候选 | N/A(Microsoft 官方文档)(https://learn.microsoft.com/en-us/windows-hardware/drivers/audio/usb-2-0-audio-drivers) | Win10 1703+ 内置 UAC2 类驱动;**核验反出更硬官方约束:异步 OUT 仅支持显式反馈端点(不支持隐式反馈);共享模式不支持 >8 通道** | 8ch 回录恰在界内,>8ch 复合方案撞墙;「Win11 22621 校验更严」为社区说法未核实,不作设计依据 |
| CherryUSB | oss | 评估 | 已核:Apache-2.0(LICENSE 原文,标准专利授权)(https://raw.githubusercontent.com/cherry-embedded/CherryUSB/master/LICENSE) | UAC1/UAC2 + host MSC,DWC2/MUSB/CHIPIDEA/EHCI/XHCI(约 2k stars 属实) | **「持续发版 v1.6.x」未从主源确认(文档里程碑 V1.4.3),采用前核对当前 release**;CDNS3/DWC3 未支持 |
| littlefs | oss | 评估 | 已核:BSD-3(LICENSE.md,Arm+authors,无专利条款)(https://raw.githubusercontent.com/littlefs-project/littlefs/master/LICENSE.md) | COW 强掉电安全、磨损均衡、RAM 有界(README 逐条核实);定位=内部 flash 预设/日志/断点状态 | PC 不识别,不适合直读 U 盘 |
| RF64/BW64(BS.2088) | standard | 评估 | N/A(公开标准,免费获取)(https://www.itu.int/rec/R-REC-BS.2088/en) | ds64 64 位尺寸突破 4GB;**BS.2088-2 于 2025-11 批准现行——扫描时效性宣称核验属实** | 消费级播放软件支持不佳;一般场景优先分段普通 WAV |
| exFAT 商用授权 | commercial | 评估 | 已核:MS 专利授权计划真实、Tuxera 官方列名合作方(https://www.microsoft.com/en-us/legal/intellectualproperty/tech-licensing/programs) | FatFs 开 exFAT 确需授权;**核验推翻扫描过宽宣称(overstated):Linux kernel 5.7+ 内核 exFAT 经 OIN 覆盖免费——「FAT32 规避 vs 付费」二选一漏掉了「嵌入式 Linux 走内核实现」第三路径** | 平台选型含 Linux 时重算该合规成本 |

规避:wavfix——AGPL-3.0,仅思路参考(RIFF 修复逻辑简单,自研成本低)。
观望(未核):Zephyr usbd_uac2(Apache-2.0,绑 Zephyr)、Reliance Edge(GPLv2/商业)、XMOS lib_xua(XMOS 硅片限定;「DSP+XMOS USB 桥」拓扑值得架构评审对比)。
已剔除:无(8 项全部 confirmed;exFAT 条目 capability_verdict=overstated,已按上修正保留)。

### 1.8 ota(固件升级)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| MCUboot | oss | 采用候选 | 已核:Apache-2.0(LICENSE;捆绑 tinycrypt 为 BSD-3)(https://raw.githubusercontent.com/mcu-tools/mcuboot/main/LICENSE) | swap/overwrite/direct-XIP/RAM-load 四策略、swap 断电续传、test-swap 自动 revert、RSA/ECDSA/Ed25519 + imgtool(design.html 逐项核实) | 官方 port 集中 Cortex-M;非 Arm DSP 需自写 boot port |
| orlp/ed25519 | oss | 采用候选 | 已核:zlib(README 明文)(https://github.com/orlp/ed25519) | 便携 ANSI C Ed25519(SUPERCOP ref10),零依赖,可嵌 bootloader 验签 | 多年低活跃,安全跟踪自担 |
| Monocypher | oss | 采用候选 | 已核:CC0-1.0 OR BSD-2-Clause 双许可任选(LICENCE.md 原文)(https://raw.githubusercontent.com/LoupVaillant/Monocypher/master/LICENCE.md) | 单文件嵌入式加密库;默认 EdDSA-BLAKE2b(非标准),标准 Ed25519 为可选模块(官网核实) | 与标准工具链互通须启用可选模块 |
| RAUC | oss | 采用候选 | 已核:LGPL-2.1-or-later(README 明文)(https://raw.githubusercontent.com/rauc/rauc/master/README.rst) | Linux 档 A/B 原子升级:X.509/OpenSSL 验签、PKCS#11/HSM、U-Boot/Barebox/GRUB/EFI 集成、断电安全(README 核实) | 仅 Linux 架构适用;独立进程不链接自研代码,LGPL 合规判断合理 |
| libsodium | oss | 评估 | 已核:ISC(LICENSE)(https://raw.githubusercontent.com/jedisct1/libsodium/master/LICENSE) | 上位机签名端/Linux 档 Ed25519(crypto_sign 系官方文档核实) | 裸机偏大,设备端另选小库 |
| SWUpdate | oss | 评估 | 已核:主体 GPL-2.0-only;库 LGPL-2.1+;另含 BSD/MIT/ISC/CC0/文档 CC-BY-SA-4.0(官方 licensing 页,比扫描清单更全)(https://sbabic.github.io/swupdate/licensing.html) | 单/双 copy、streaming、加密签名、Lua 钩子、hawkBit 对接(官方文档核实) | Linux 独立进程合规,但公司若对设备内 GPL 一刀切则降规避 |
| IETF SUIT 架构 RFC 9019 | standard | 评估 | N/A(IETF RFC 公开)(https://www.rfc-editor.org/info/rfc9019) | IoT 固件升级架构与 manifest 设计参照;**核验定性修正:Informational RFC 非 Standards Track,评审材料勿称「标准」** | 全量 CBOR/COSE 过重,裁剪借鉴 |
| Interrupt(Memfault)DFU 系列 | paper | 评估 | N/A(博客;示例代码许可复用前单独核对)(https://interrupt.memfault.com/blog/device-firmware-update-cookbook) | 多级 bootloader(Bootloader/Loader/App/Updater)架构+STM32F429 示例(2020-06-23,Baldassari,核实) | 思路无风险,代码许可另核 |
| Mbed TLS | oss | 评估(**限 ECDSA/RSA 路线**) | 已核:Apache-2.0 OR GPL-2.0-or-later 双许可任选(LICENSE 明文)(https://raw.githubusercontent.com/Mbed-TLS/mbedtls/development/LICENSE) | ECDSA/RSA 验签、TLS 通道;MCUboot 可选 crypto 后端 | **核验推翻(overstated):任何已发布版本均无 EdDSA/Ed25519 签名(PR #5800 关闭未合并、后续拆分跟踪 #5819;ChangeLog 零记录、仅有 X25519 ECDH)——签名选型定 Ed25519 则本条不可用,改配 orlp/ed25519 或 Monocypher** |
| U-Boot bootcount/altbootcmd | oss | 评估 | 已核:GPL-2.0-or-later 为主,逐文件 SPDX;standalone 应用明确不视为衍生作品(Licenses/README)(https://raw.githubusercontent.com/u-boot/u-boot/master/Licenses/README) | bootlimit 超限走 altbootcmd 回滚;FIT 签名校验(rsa2048/ecdsa256)——官方文档核实 | 独立镜像行业通行;义务=提供 U-Boot 修改源码;redundant env 才断电安全 |

规避:wolfBoot——GPL-3.0(商业授权可购,另计)。
观望(未核):Mender(Apache-2.0 客户端;云编排过重)、Eclipse hawkBit(EPL-2.0 服务端)、Rugix(MIT/Apache-2.0,新兴)、RT-Thread OTA(Apache-2.0 包;rt_ota 闭源核心库条款[待核],升档前须补核)。
已剔除:无(10 项全部 confirmed;Mbed TLS 能力宣称按核验修正保留)。

### 1.9 control(控制协议)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| QSC Q-SYS QRC | commercial | 采用候选 | 已核:专有协议、文档公开免登录(https://help.qsys.com/Content/External_Control_APIs/QRC/QRC_Commands.htm) | JSON-RPC 2.0/TCP:1710、NUL 分帧、ChangeGroup 订阅、Logon、60s 超时+NoOp 保活——全部主源逐条核到 | 仅设计参照;JSON 解析在低端 MCU 成本需评估 |
| Biamp Tesira TTP | commercial | 采用候选 | 已核:专有协议、v4.2 规范 PDF 公开(https://downloads.biamp.com/assets/docs/default-source/control/tesira_text_protocol_v4-2_jan22.pdf?sfvrsn=100c2497_46) | RS-232/Telnet/SSH、InstanceTag 语法、会话级订阅(断线失效)、分级登录——v4.2 全文核验 | 会话级订阅断线重连是集成痛点,自研协议考虑订阅持久化 |
| Sennheiser SSC | commercial | 采用候选 | 已核:专有协议、TI 1245 v1.8.0(161 页)公开(CDN 对非浏览器 UA 403,建议本地存档)(https://www.sennheiser.com/globalassets/digizuite/41940-en-ti_1245_v1.8.0_sennheiser_sound_control_protocol_tcc2_en.pdf) | OSC 地址树→嵌套 JSON、null 作 getter、UDP:45/TCP/HTTP(S)/SSH——PDF 原文核到 | 各产品线文档版本分裂,以 TCC2 版为准 |
| Shure Command Strings (P300/MXA910) | commercial | 采用候选 | 已核:专有协议、官方站公开(JS 渲染,经文档镜像核验)(https://www.shure.com/en-US/docs/commandstrings/P300) | TCP:2202、尖括号定界、GET/SET→REP、参数变更主动 REP、全文无鉴权(反面教材)——核到 | 「REP 向所有连接广播」的「所有」未逐字核到;定长填充设计老派 |
| OSC 1.0 规范 | standard | 采用候选 | 已核:规范文本 CC BY(页脚标注),自由实现(https://opensoundcontrol.stanford.edu/spec-1_0.html) | 地址模式匹配、类型标签、Bundle+时间戳(规范原文核实) | 无鉴权/会话/可靠传输语义,只借鉴地址模型 |
| Ember+ (Lawo) | oss | 评估 | 已核:BSL-1.0(LICENSE.TXT 原文,无附加条款,闭源静态链接可行)(https://raw.githubusercontent.com/Lawo/ember-plus/master/LICENSE.TXT) | libember(C++)/libember_slim(C):BER 树形参数模型、订阅、电平流 | BER/ASN.1 复杂、生态偏广电;文档 PDF 是否同许可未单独核 |
| AES70/OCA | standard | 评估 | N/A(开放标准;Alliance 明示自由实现、无需入会,主源核实)(https://ocaalliance.com/what-is-aes70/) | 对象模型+OCP.1+订阅/发现的标准化参照 | 全量实现对 8x8 过度设计;技术细节在标准文本内,Alliance 页展示有限(2018/2023 版本号未在该页出现) |
| Symetrix Composer Control Protocol | commercial | 评估 | 已核:专有协议、v7.0 PDF 公开——**扫描官方链接已 404,本轮经镜像全文核验,雷达证据链接需更换/存档**(https://audiobrains.com/data/symetrix/others/Composer-Control-Protocol-v7.0-080918.pdf) | RS-232/TCP/UDP:48631、控制号 1-10000、PUE/PUD/PUI(20ms-30s)/PUT 阈值推送节流——全文核到 | 整型控制号可读性差;全文未见鉴权 |
| Extron SIS | commercial | 评估 | 已核:专有协议,散见产品手册(tech92 页有 bot 防护,经手册 PDF 核验)(https://aca.im/driver_docs/Extron/PDU_IPL_T_PCS4.pdf) | 极简命令、必有应答+错误码(E12-E28 见手册,E01 见于其他型号)、verbose 0-3——手册核到 | 按型号碎片化,无统一规范文本 |
| tinyosc | oss | 评估 | 已核:ISC(LICENSE 原文)(https://raw.githubusercontent.com/mhroth/tinyosc/master/LICENSE) | 极简 vanilla C OSC 编解码,可进固件;**核验修正(偏保守方向):README 实际支持 bundle 解析/写入与 timetag,扫描「bundle/时间戳支持有限」高估了限制** | 仅编解码,无传输/订阅层 |
| oscpack | oss | 评估 | 已核:MIT+非约束性回寄请求条款(LICENSE 原文,明确 non-binding)(https://raw.githubusercontent.com/RossBencina/oscpack/master/LICENSE) | C++ OSC 打包/解包+最小 UDP 收发(上位机侧) | 基本停更(版权止 2004-2013);TCP 分帧自实现 |
| Crestron Certified Drivers SDK | tool | 评估 | 已核:专有 SDK,文档站公开免登录,受 Crestron 条款约束(https://sdkcon78221.crestron.com/sdk/Crestron_Certified_Drivers_SDK/Content/Topics/Overview/Overview.htm) | 驱动构建/测试流程、SIMPL/SIMPL#Pro 参考 | **核验补充:Overview 明示「开发新设备类型」与需受限信息的样例驱动不受支持——Crestron 对接规划应纳入**;底层 CIP 不公开 |

规避:AES70.js——GPL-2.0,固件与闭源上位机均不可引入。
观望(未核):Harman HiQnet(专有文档)、OCAMicro/OcaToolsAndDemos(OCA Alliance EULA,含赔偿义务,法务评审前不入固件)、liblo(LGPL-2.1+,POSIX)、Freed & Schmeder NIME 2009(OSC1.1/SLIP 分帧)、AMX NetLinx(专有文档)。
已剔除:无(12 项全部 confirmed)。

### 1.10 room-eq(房间校正/声学测量)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| Farina ESS 原始文献 | paper | 采用候选 | N/A(论文,AES 108th Conv. 2000)(https://www.aes.org/e-lib/browse.cfm?elib=10211) | 指数扫频同时测 IR 与失真(摘要核实) | 工程细节(淡入淡出/时钟漂移/重测逻辑)自补 |
| Müller & Massarani | paper | 采用候选 | N/A(JAES 49(6):443-471, 2001)(https://aes.org/publications/elibrary-page/?id=10189) | 扫频测量工程百科(抗失真/抗时变/SNR) | 无 |
| pyfar + pyrato | oss | 采用候选 | 已核:MIT(两仓 LICENSE 原文)(https://raw.githubusercontent.com/pyfar/pyfar/main/LICENSE) | exponential_sweep、regularized_spectrum_inversion、deconvolve、分数倍频程平滑(API 文档逐项核实)+房间声学参数 | 纯 Python,仅上位机/原型 |
| RBJ Cookbook(W3C Note) | standard | 采用候选 | N/A(W3C Note 2021-06-08 已核)(https://www.w3.org/TR/audio-eq-cookbook/) | 固件 biquad 级联的系数出处 | 定点低频高 Q 需双精度累加/DF1 |
| Ramos & López 2006 | paper | 采用候选 | N/A(JAES 54(12):1162-1178)(https://aes.org/publications/elibrary-page/?id=13893) | 测量响应→SOS 链参数 EQ 自动设计(心理声学优化) | 需自行实现;优化在上位机 |
| Karjalainen 等模态衰减 / FZ-ARMA | paper | 采用候选 | N/A(论文;**扫描自认未核的卷期页码已补核闭合:JAES 50(11):867-878 与 50(12):1012-1029, 2002**)(https://research.aalto.fi/en/publications/frequency-zooming-arma-modeling-of-resonant-and-reverberant-syste) | 驻波/模态识别与衰减参数估计 | 实现复杂度中等,上位机原型先行 |
| Cecchi/Carini/Spors 2018 综述 | paper | 采用候选 | N/A(Applied Sciences 8(1):16,开放获取;MDPI 页 403,经 DOI 多源确认;CC BY 未从页面直读)(https://www.mdpi.com/2076-3417/8/1/16) | 房间响应均衡技术选型总览 | 无 |
| Toole/Olive 保守校正原则 | paper | 采用候选 | N/A(Olive 2009 AES preprint 7960;Toole 3rd ed. Routledge 2017)(https://aes.org/publications/elibrary-page/?id=15154) | 「只削峰不填谷」的可引用出处 | **核验小疵:AES 页作者为 Olive/Jackson/Devantier/Hunt 四人,扫描多列 'Hess, S.',正式引用前核对** |
| REW | tool | 评估 | 已核:专有免费;EULA 允许商业使用、禁再分发/逆向/衍生(EULA 原文)(https://www.roomeqwizard.com/eula.html) | 测量标杆+HTTP API(127.0.0.1:4735, Swagger) | **核验推翻(overstated):API 自动扫频测量需付费 Pro upgrade,非免费能力;「V5.40 起提供」未获主源确认——产线自动化预算须计入 Pro 授权并留存条款记录** |
| Novak 同步扫频 | paper | 评估 | N/A(JAES 63(10):786-798, 2015;**[待核]已闭合:作者站代码无任何许可声明=保留权利,商用不可搬运**)(https://ant-novak.com/pages/sss/) | 相位同步扫频+谐波分析(失真/产线自检) | 只能按论文重实现 |
| Mäkivirta/Karjalainen 模态均衡 | paper | 评估 | N/A(JAES 51(5):324-343, 2003)(https://aes.org/publications/elibrary-page/?id=12226) | 主动模态均衡(降模态衰减率) | Genelec 专利风险提示未核验;V1 只做幅度削峰 |
| Bank parfilt | paper | 评估 | N/A(论文可自由重实现;**作者页代码条款已核原文:'Non-commercial use permitted'——MATLAB 代码及其移植严禁进商业产品**)(https://home.mit.bme.hu/~bank/parfilt/) | 固定极点并联二阶节 EQ(线性最小二乘) | 按论文公式自写 |
| AutoEq (jaakkopasanen) | oss | 评估 | 已核:MIT(LICENSE 原文)(https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/LICENSE) | 目标响应→PEQ 优化器(Fc/Q/gain 约束,PyPI autoeq)(README 核实) | 耳机向,房间前端自加 |
| python-acoustics / acoustic-toolbox | oss | 评估 | 已核:BSD-3(LICENSE 原文)(https://raw.githubusercontent.com/python-acoustics/python-acoustics/master/LICENSE) | 倍频程/房间声学参数/ISO 计算 | **核验更正:原仓库 2024-02-07 已 ARCHIVED(只读),比扫描「维护放缓」严重——选型直接转 acoustic-toolbox fork(fork 许可本轮未单独核)** |
| MATLAB Audio Toolbox 房间均衡示例 | commercial | 评估 | **unresolved:示例代码复用条款无公开主源,维持未核——禁入选型依据,产品移植前须 MathWorks 书面确认**(页面存在:https://www.mathworks.com/help/audio/ug/automated-design-of-audio-filters-for-room-equalization.html) | IR 测量→lsqnonlin 优化 12 段 PEQ(10 peaking+2 shelf)的算法参照 | 仅算法参照,代码不可默认可移植 |
| Elliott & Nelson 1989 | paper | 评估 | N/A(JAES 37(11):899-907)(https://aes.org/publications/elibrary-page/?id=6063) | 多点误差平方和最小化均衡 | 采多点平均思想+IIR 执行,不照搬自适应 FIR |

规避:PORC——无 license 且系 Bank 非商用代码移植(双重污染);DRC-FIR——GPL-3.0-or-later[未核原文],且长 FIR 混合相位与 <12ms 冲突。
观望(未核):Dirac Live(商业 OEM,买侧代表)、EQilibrium(MIT 标注,太新单人)、autoeq/pierreaubert(无 license,只读思路)。
已剔除:无(16 项全部 confirmed;REW 能力按核验修正保留)。

### 1.11 host-ui(上位机)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| Qt 6 (Widgets/QML) | oss | 采用候选 | 已核:商业+社区 GPLv3/LGPLv3 双轨;Essentials 走 LGPLv3 可闭源动态链接;严禁商业/社区混用(qt.io 原文)(https://doc.qt.io/qt-6/licensing.html) | 跨平台上位机主框架,音频行业最常见 | **核验坐实:Qt6 GPL-only 名单含 Qt Graphs(Charts/DataVis 接替者)/Quick 3D/MQTT/CoAP/HTTP Server 等——LGPL 路线下频谱/EQ 曲线必须自绘或购商业版**;LGPLv3 重链接义务 |
| Dear ImGui | oss | 采用候选 | 已核:MIT(LICENSE.txt,©2014-2026 Omar Cornut)(https://raw.githubusercontent.com/ocornut/imgui/master/LICENSE.txt) | 即时模式工具型 UI(输出顶点缓冲交宿主 3D 管线渲染;docking 分支存在) | 皮肤化/本地化/无障碍弱;自带窗口+渲染后端 |
| ImPlot | oss | 采用候选 | 已核:MIT(LICENSE 原文补核)(https://raw.githubusercontent.com/epezent/implot/master/LICENSE) | 实时曲线/热图/柱状;「数万至数十万点」与 README 逐字吻合 | EQ 拖拽编辑与对数频轴需自写 |
| mdns (mjansson/mdns) | oss | 采用候选 | 已核:Public domain(README:无限制再分发/修改;**无 MIT 备选文本,公有领域献弃在部分法域效力存疑,采用时法务留痕**)(https://github.com/mjansson/mdns) | header-only 跨平台 mDNS/DNS-SD,零动态分配(README 逐条核实);固件侧响应器可复用 | 偏底层,自管 socket/事件循环 |
| QMdnsEngine | oss | 评估(**核验下调:能力 unverified**) | 已核:MIT(LICENSE.txt 原文)(https://raw.githubusercontent.com/nitroshare/qmdnsengine/master/LICENSE.txt) | Qt 原生 mDNS(RFC 6762,README 确认) | **「服务发布/浏览/IPv4v6 解析」在 README 无特性清单、文档托管 CI 站未核到——选型定稿前源码级确认,或直接用 mjansson/mdns(能力已全核)** |
| JUCE 8/9 | oss | 评估 | 已核:AGPLv3/JUCE 9 商业双轨(LICENSE.md 现指向 JUCE 9 EULA);**价格档已实核关闭缺口:Starter 免费(≤$20k)、Indie $40/月或 $800 永久(≤$300k)、Pro $175/月或 $3,500 永久(12 个月起订)、旧版升级 7 折**(https://raw.githubusercontent.com/juce-framework/JUCE/master/LICENSE.md) | 音频特化框架,EQ/频谱控件生态最丰富 | 闭源必须付费席位;禁再造框架类产品;营收口径含间接收入 |
| Frequalizer (ffAudio) | oss | 评估 | 已核:BSD-3(LICENSE.md,Daniel Walz)(https://raw.githubusercontent.com/ffAudio/Frequalizer/master/LICENSE.md) | 六段 PEQ+可拖拽曲线+频谱叠加(README 核实)——EQ 曲线交互参考 | 构建依赖 JUCE(AGPL/商业),仅借鉴移植、不整包复用 |
| Avalonia UI | oss | 评估 | 已核:MIT(核心);XPF 按 app/平台收费商业品(官方页确认)(https://github.com/AvaloniaUI/Avalonia) | .NET 跨平台 XAML 桌面框架 | 音频控件生态为零,全自绘 |
| Tauri | oss | 评估 | 已核:MIT OR Apache-2.0('MIT or MIT/Apache 2.0 where applicable',统一按 MIT 履行即可)(https://github.com/tauri-apps/tauri) | Rust+系统 WebView 桌面壳(WRY:WebView2/WKWebView/WebKitGTK) | 三平台引擎不同,渲染一致性逐平台验证 |
| Electron | oss | 评估 | 已核:MIT(LICENSE 原文)(https://raw.githubusercontent.com/electron/electron/main/LICENSE) | Chromium+Node 桌面壳,渲染一致性最好 | 体积/内存大;mDNS npm 依赖(bonjour-service 等)license 未核,选该路线须补 |
| imgui-knobs | oss | 评估 | 已核:MIT(LICENSE,©2022 Simon Altschuler)(https://raw.githubusercontent.com/altschuler/imgui-knobs/main/LICENSE) | 7 种 knob 变体(Tick/Dot/Wiper/WiperOnly/WiperDot/Stepped/Space,精确属实) | 仅旋钮,小体量 |
| webaudio-controls | oss | 评估 | 已核:Apache-2.0(**[待核]已解除**,LICENSE 全文+README 双确认)(https://raw.githubusercontent.com/g200kg/webaudio-controls/master/LICENSE) | WebComponents 旋钮/推子/开关/参数显示/键盘 | 视觉偏演示;无 EQ 曲线/矩阵网格组件 |
| 竞品调音软件文档集(Q-SYS/Tesira/Symetrix/ProVisionaire/BSS/Xilica/Shure) | commercial | 评估 | 部分已核(2/7:Q-SYS、Biamp 官方在档;其余 5 条未核):专有文档,仅在线查阅对标,不得复制视觉资产(https://help.qsys.com/Content/Q-Sys_Designer/001_Q-Sys_Designer_Overview.htm) | 上位机信息架构/矩阵网格交互对标素材 | schematic 自由布线范式与固定架构产品定位不同,对标取舍 |

规避:x42 meters.lv2——GPL,仅可读表计标准(IEC 60268-10/-17、EBU R128)后独立实现。
观望(未核):VSTGUI(BSD-style)、iPlug2/IGraphics(zlib-like)、Flutter desktop(BSD-3)、WPF(MIT,仅 Windows)、Apple mDNSResponder/Bonjour(Apache-2.0[未核];Windows 再分发条款未核)、Avahi(LGPL-2.1+[未核],仅 Linux)。
已剔除:无(13 项全部 confirmed)。

### 1.12 reference(整机参照/标准/竞品)

| 名称 | 类型 | 档位 | License(核验) | 能干什么 | 风险 |
|---|---|---|---|---|---|
| DSP Concepts Audio Weaver / AWE Core | commercial | 评估 | 已核:专有商业(Designer 三版);**运行时/royalty 条款非公开**(https://dspconcepts.com/en/audio-weaver) | 嵌入式音频框架「整套买」头部选项:bare-metal/RTOS/Linux 多核,模块库官方口径 400+/500+/600+ 不一,16 家半导体伙伴(含 ST/NXP/ADI/TI/Qualcomm) | **核验警示:「按核授权/按席位/每次启动联网校验」三项宣称唯一出处(社区论坛)已 404,官方页无此说明——按未证实处理,商务接触时书面确认(联网校验若属实影响产线/离线开发)** |
| ADI SigmaStudio / SS for SHARC + SAM baremetal SDK | commercial | 评估 | corrected:SigmaStudio 免费属性未从 analog.com 直核(页面抓取失败,凭 wiki);SS for SHARC 需付费 CCES(wiki 证实);**sam-baremetal-sdk [待核]已解决=BSD-3-Clause-Clear——Clear 变体明示不授予任何专利权,IP 评估须记入**(https://raw.githubusercontent.com/analogdevicesinc/sam-baremetal-sdk/master/LICENSE) | 图形化环境+预制算法块,SigmaDSP(ADAU1452/66/67)与 SHARC | 平台锁定;算法块黑盒;AEC 级算法仍需自研或买 IP |
| AES17-2020 | standard | 采用候选 | N/A(付费标准;aes2.org 商店证实会员 $0/非会员 $50-100)——**证据缺口:扫描链接已 404(AES 站迁移),AES17 专页未能抓到,「AP 测试仪内置 AES17 模式」未核到主源,定档前补有效链接**(https://aes2.org/publications/standards-store/) | 数字音频设备电性能测量(THD+N/动态范围/频响)验收骨架 | 会议语音链路指标需 ITU-T P 系补齐 |
| IEC 60268 系列(-3 放大器 / -16 STI) | standard | 采用候选 | N/A(付费:60268-3:2018 与 60268-16:2020 均现行,PDF 约 €506-540/份,EVS 渠道核实)(https://www.evs.ee/en/iec-60268-3-2018) | 模拟口特性与测量、STI 语音可懂度 | 整套购齐费用不低;GB/T 12060 采标途径未核 |
| ITU-T P.340 / P.341 | standard | 采用候选 | N/A(ITU 免费公开;P.340 (05/00)+Amd.2(2019) in force、P.341 (03/11) in force 核实)(https://www.itu.int/rec/T-REC-P.340/en) | 免提终端 TCLw/双讲/切换特性——会议 DSP 整机语音验收最贴切参照系;P.341 宽带 150-7000Hz | P.340 主体为 2000 年版,现代会议设备需裁剪 |
| ITU-T G.167 + G.168 | standard | 评估 | N/A(ITU;G.167 Withdrawn、G.168 (04/15)+2022 勘误 in force 核实)(https://www.itu.int/rec/T-REC-G.167/en) | AEC/线路 EC 指标框架 | **核验推翻(overstated):扫描称 G.167「无直接替代」与 ITU 主源矛盾——内容由 P.340(2000)+G.161(2002)明确承接,规格制定直接引 P.340/G.161(本 JSON 内 aec 维度表述正确,reference 维度自相矛盾处以此更正);「覆盖至 400ms 回声路径」条款未读原文核对** |
| Biamp Tesira 公开架构资料 | commercial | 评估 | 已核:专有文档公开可阅(©Biamp,免登录)(https://support.biamp.com/Tesira/Programming/AEC_in_Tesira) | AEC Input/Processing/Reference 三块划分、逐通道/单通道 reference、信号流路由(页面逐项核实)——免费公开的会议 DSP 工程参照系 | 只讲拓扑不讲算法;商标注意 |
| Shure IntelliMix P300 资料 | commercial | 评估 | 已核:专有文档公开(©Shure)(https://www.shure.com/en-US/products/mixers/p300) | 与本机形态最接近竞品:8ch 麦处理(AEC+NR+AGC)+IntelliMix automix+矩阵+delay/comp/PEQ(产品页几乎逐字核实) | 算法黑盒;Shure 自动调参在授专利 US11985488 未核,不影响文档参照 |
| CamillaDSP | oss | 评估 | 已核:GPL-3.0 与 MPL-2.0 双许可任选;**启用 asio-backend(Windows ASIO)构建时仅 GPLv3**——扫描此条精确无误(https://github.com/HEnquist/camilladsp) | matrix mixer+级联 biquad+FFT 卷积 FIR+WebSocket 控制+YAML pipeline(全部证实;1000+ stars/1754 commits) | MPL 轨取代码须文件级 copyleft;上位机 Windows ASIO 构建即触 GPL |
| ITU-T P.862 (PESQ) / P.863 (POLQA) | standard | 评估 | 未核(参考实现商用授权[待核]仍 unresolved——OPTICOM 等权利方条款不得按已核处理)(https://www.itu.int/rec/T-REC-P.862/en) | 语音质量客观评分(研发回归指标) | **核验推翻(overstated):P.862 已 superseded,ITU 于 2024-01-05 删除过期文本并指引改用 P.863 系——「文本免费公开」表述过时;纳入 CI 前须专项法务核实,或改用开源 ViSQOL** |

规避:aes67-linux-daemon——GPL-3.0(归 aoip 维度同条);ravennakit——AGPL-3.0[未核];Elk Audio OS/Sushi——AGPL-3.0(商业许可可购,公司状态/报价不明)。
观望(未核):freeDSP aurora(CC-BY-SA-4.0 硬件/文档;固件许可[待核];8x8 硬件分层参照)、QSC Q-SYS System Description(x86 软件 DSP 路线对照)、DSPPA DP8005(国产直接竞品,产品页级)、OLMS(GPL-3.0,PC 路线)。
已剔除:无(10 项全部 confirmed;Audio Weaver/G.167/P.862 宣称按核验修正保留)。

---

## 2. D1–D14 borrow/build 映射表

> 编号已按项目 WBS(CLAUDE.md §3 的 D1-D14)重排,括号注明子域(作者终审修正:合成稿原用自造编号)。另注:D2(参数阈值表)与 D13(预算表)为横切交付物,由各行的参数惯例/算力口径素材间接支撑,不单列行。

| 交付物 | 借用什么(具体候选) | 仍需自研什么 |
|---|---|---|
| D3(输入链·AEC) | SpeexDSP mdf.c(BSD-3,直接移植基线);Soo-Pang MDF / Valin 2007 / Enzner-Vary Kalman / Hänsler-Schmidt(算法与控制理论);WebRTC AEC3(结构参考:延迟估计/残余抑制/分带);pyaec+PFDKF(Python 黄金参考);G.168/P.340+G.161(指标) | 512ms 尾长下收敛/算力实测与调优(超官方建议区间);残余回声后滤波补强;双讲控制工程化;目标 DSP 的 FFT/SIMD 适配;非线性回声补偿(未专项调查,缺口) |
| D3(输入链·ANC 降噪) | SpeexDSP preprocessor + WebRTC NS(可移植参考);Martin/IMCRA/Gerkmann SPP(噪声估计);Ephraim-Malah/OM-LSA/Cappé(增益规则);athena-signal(C 参考) | 48kHz 低延迟参数化;瞬态(键盘)抑制完整实现(Talmon 线简化版或锁版 WebRTC Transient 自维护);音乐噪声调参;与 AEC 后滤波联合设计 |
| D3(输入链·AFC 啸叫抑制) | JAES 2010 六判据 + NINOS²-T(检测);RANF/Alkaher(低延迟检测);RBJ notch(陷波执行);chapro/Tympan NLMS-NFXLMS(AFC 参考码);Berdahl 频移法(辅助);dbx AFS2(规格对标) | 生产级 16 点陷波+固定/动态分配整机实现(无现成开源库,本维度最大空白);48kHz 扩声场景判据阈值标定;chapro 路线的 BTNRH 专利 FTO |
| D5 自动混音 | Dugan 1975 + US3992584A(算法规格,公有领域);Biamp/Shure/QSC/BSS 参数惯例(NOM 10log、NOMA 1-6dB、off-atten -40dB、hold 1000ms、优先级模式);leafac/reaper JSFX(算法阅读,禁复制) | 全部 C 实现(无可嵌入开源库);门控/增益共享统一参数表;主席优先逻辑;与 AEC/矩阵的联动;避开 Shure 在效专利权利要求 |
| D3/D4 通道确定性 DSP(EQ/动态/延时) | CMSIS-DSP(执行);RBJ Cookbook(系数);Giannoulis 2012(压缩器);SciPy(离线设计);Iir1/Signalsmith(参考实现);Faust(原型流水线) | 定点化与平台适配;参数平滑/无爆音切换;整链路 <12ms 延迟预算管理 |
| D1/D6 信号流与矩阵路由架构 | CamillaDSP(pipeline/mixer 抽象与配置模型参照);Tesira/P300 公开架构(功能定义);Audio Weaver/SigmaStudio(商用对照) | 8x8 矩阵引擎本体;场景/预设系统;整机信号流(无任何整机级开源对等项目) |
| D4(输出链·限幅与音箱保护) | BS.1770-5(真峰值检波规范+FIR 系数表);Signalsmith limiter(lookahead 结构);Linea DE3457-01(整定方法);Klippel AN28(评估方法) | 真峰值 lookahead 限幅 C 实现(无 license 干净的独立开源库);静态热/位移限幅模型(绕开 Klippel 系自适应专利) |
| D10(AI 增强·房间测量与自动 EQ) | Farina/Müller-Massarani/Novak(测量方法);pyfar/pyrato(上位机工具链);Ramos-López/AutoEq/Elliott-Nelson(拟合引擎);Karjalainen(模态);Toole/Olive(策略);REW(对标基准,API 需 Pro) | 上位机测量向导整合;只削峰策略引擎;固件系数下发协议;Bank/Novak 代码不可用,均按论文自写 |
| D7 网络音频(AoIP:Dante/AES67) | AES67-2023(规范);flexPTP 或 PTPd(PTP 组件);GStreamer/Wireshark/aes67-linux-daemon(测试对端与排障);AES-R16(PTP 参数);Dante OEM(买路线) | 裸机上 RTP 收发+媒体时钟恢复+SAP/SDP 发现层(无成熟宽松许可栈,最大空白);或 Dante 商务条款确认与集成 |
| D8 USB 声卡与 U 盘录音 | TinyUSB/CherryUSB(UAC+MSC 栈);FatFs(文件系统);usbaudio2.sys 官方约束(显式反馈、≤8ch);RF64/BW64(>4GB 格式);littlefs(内部存储);wavfix(思路) | UAC2 多通道描述符+三大 OS 实测矩阵;WAV 掉电安全录音固件(周期回写+f_sync 策略,无开源范例);U 盘兼容性测试矩阵;exFAT 合规决策(FAT32-only / 付费 / Linux 路径) |
| D12(固件架构·OTA/bootloader) | MCUboot(MCU 档)+orlp/ed25519 或 Monocypher(验签);RAUC/SWUpdate/U-Boot(Linux 档);RFC 9019+Interrupt 系列(manifest/流程设计) | 非 Cortex-M DSP 的 boot port 与 flash_map;上位机直推传输协议(Ymodem/自定义分包,未调查);防回滚安全存储(依芯片) |
| D9 中控协议 | QRC/TTP/SSC/Shure(设计惯例:分帧/寻址/订阅/保活/鉴权);OSC 1.0+tinyosc/oscpack(编码与实现件);Symetrix(推送节流);Extron(错误码/verbose);Ember+/AES70(对象模型参照) | 自有协议规范(含鉴权——行业普遍缺位,可做差异化);固件协议栈;订阅持久化;Crestron/AMX 对接模块(CIP/ICSP 不公开,走公开 SDK 层) |
| D11 上位机软件 | Qt6(LGPL 轨)或 ImGui+ImPlot+imgui-knobs;mjansson/mdns(发现,固件侧可复用);Frequalizer(EQ 曲线交互参考);竞品文档集(信息架构对标) | 频谱/EQ 曲线组件(Qt 路线必须自绘,Qt Graphs GPL-only);矩阵网格控件(各栈均无现成,确定自绘);设备管理/固件升级 UI |
| D14 测试与验收体系 | AES17/IEC 60268-3、-16/P.340+P.341+G.161/G.168(标准);AEC-Challenge/DEMAND/QUT-NOISE(语料);Wireshark/GStreamer(互通);pyfar+SciPy(测量) | 会议室长混响自采语料;U 盘/OS 兼容矩阵;啸叫主观听测方案(无现成文献);ETSI 噪声库与 PESQ/POLQA 授权澄清后才可纳入 |

---

## 3. 测试资产清单(商用测试可用性标注)

| 资产 | 类型 | 商用测试可用性 | 备注 |
|---|---|---|---|
| Microsoft AEC Challenge | 数据集 | 内部回归测试可用(已核:代码 MIT;数据逐源:LibriVox PD/AudioSet CC-BY-4.0/Freesound CC0/DEMAND CC-BY-SA-3.0) | 衍生音频对外发布须逐子集合规;会议室长混响覆盖不足需自采 |
| DEMAND | 数据集 | 内部测试可用(已核;Zenodo 元数据 CC BY 4.0 vs CC BY-SA 3.0 自相矛盾) | 对外发布按更严 BY-SA 3.0 或向作者澄清 |
| QUT-NOISE | 数据集 | 商用允许(已核:CC BY-SA,版本号未标;代码 BSD) | 精确合规需下载包内 LICENSE.txt;SA 传染衍生再分发 |
| ETSI ES 202 396-1 噪声库 | 标准附件 | **未核,禁入正式测试规程**——公开目录无条款文件,须向 ETSI 澄清 | 2026-07 目录现 'NEW LOCATION.txt',迁移中 |
| DNS-Challenge 噪声 | 数据集 | 未核(观望):逐源混合含可能 NC | 瞬态/键盘类别有用,用前逐源核 |
| WHAM! | 数据集 | **不可用:CC BY-NC 4.0(规避)** | — |
| NINOS²-T 标注数据集 | 数据集 | 论文开放获取、代码 MIT(已核) | 啸叫检测器评测 |
| ITU-T G.168 / P.340+P.341 / G.161 | 标准 | 免费公开(ITU),实现不受限(已核状态) | G.168 为线路 EC,限值不可照搬;G.161 系核验新增,验收规格须入列 |
| AES17-2020 | 标准 | 付费(会员 $0/非会员 $50-100,aes2.org) | 证据链接待补(AES 站迁移) |
| IEC 60268-3:2018 / -16:2020 | 标准 | 付费(约 €506-540/份,EVS 核实) | GB/T 12060 采标途径未核 |
| ITU-R BS.1770-5 | 标准 | 免费(PDF 已核),算法可实现 | 真峰值检波规范 |
| ITU-T P.862/P.863 | 标准 | **参考实现商用授权 unresolved,未核禁用**;P.862 已 superseded、文本已删除 | 替代:开源 ViSQOL(算法维度,未入本池) |
| AECMOS | 工具 | 未核(观望):ONNX 模型条款[待核] | 48kHz 专业场景校准性未知 |
| REW | 工具 | 使用免费(商业使用 EULA 允许,已核);**API 自动化需付费 Pro** | 禁捆绑分发/逆向;留存 EULA 记录 |
| Wireshark | 工具 | 内部研发可用(GPL-2.0 已核,不随产品分发) | PTP/RTP/SDP/SAP 排障 |
| GStreamer | 工具 | 上位机/测试对端(LGPL 已核) | 软件时戳,仅测试级同步 |
| pyfar/pyrato、SciPy、pyaec、PFDKF | 工具 | MIT/BSD/Apache 已核,上位机与原型自由使用 | 不进固件 |
| aes67-linux-daemon | 工具 | 内部测试对端可用(GPL-3.0,不入产品) | AES67 互通廉价对端 |
| 竞品文档集(Tesira/P300/Q-SYS 等) | 对标素材 | 在线查阅可用,不得复制资产 | 功能规格/默认参数参照 |

---

## 4. 缺口清单(not_covered 汇总去重 + 核验失败/未决项 = 自研或补查清单)

### 4.1 确认的能力空白(自研项)
1. 「开箱即用、明确支持 512ms 尾长、含完整双讲控制」的生产级开源 AEC C 库不存在(aec 维度最大缺口)。
2. PA/扩声域生产级、license 友好的开源啸叫抑制库不存在——JAES 2010 判据 + IIR 陷波组 + chapro 式 AFC 拼装自研。
3. 可嵌入 C 固件的宽松 license automix 库不存在(全部是 DAW 插件/脚本形态)——按论文/过期专利+厂商惯例自研(算法小)。
4. license 干净、生产级的独立开源「真峰值 lookahead 限幅」C 库不存在——按 BS.1770+Signalsmith/Giannoulis 自研。
5. 裸机/RTOS DSP 完整开源 AES67 栈(PTP+RTP+发现+媒体时钟恢复)不存在——PTP 组件+自研,或商用模块。
6. 固件级 WAV 掉电安全录音开源范例不存在——策略自研;U 盘品牌兼容性 quirks 无权威清单,自建测试矩阵。
7. 「会议 AEC+自动混音+矩阵」无整机级开源对等项目;矩阵路由网格 UI 控件各技术栈均无现成,自绘。
8. 嵌入式 DSP 固件内完整自动房间校正开源 C 实现不存在——「上位机算系数、固件执行 biquad」为既定路线。
9. 陷波音质损伤的专项主观评估文献未检索到——需自建听测方案。
10. 键盘/敲击脉冲噪声可商用独立测试集未找到——可能需自录。

### 4.2 未核/未决项(补查清单,按影响排序)
1. **PESQ/POLQA 参考实现商用授权(使用条款未决)**——纳入 CI 前专项法务核实。
2. **ETSI ES 202 396-1 噪声文件商用测试/再分发条款(使用条款未决)**+数据库迁移跟踪。
3. **MATLAB Audio Toolbox 示例代码复用条款(unresolved)**;MATLAB Coder 生成代码部署条款。
4. **Dante 关键规格**(Brooklyn 3 64x64/Ultimo 2-4ch/DEP 平台/AES67 兼容模式)与授权价格/起订/认证费——商务书面确认。
5. **Audio Weaver 授权模式**(按核/席位/联网校验)——官方出处已 404,商务确认。
6. **chapro/BTNRH AFC 专利 FTO**(CC0 无专利授权,核验新增)。
7. **AES17 专页有效主源链接 + AES-R 系报告获取条款**(AES 站迁移导致证据链断裂)。
8. 商用授权算法库条款未逐家核:VOCAL/Adaptive Digital/Fraunhofer(AEC)、Alango 等(NS)、Waves X-FDBK/Sabine(AFC)、Dirac 等(房间校正 OEM)。
9. 平台耦合库待定平台后补核:NatureDSP(HiFi 系)、TI DSPLIB 版本条款、ADI CCES/SHARC 库、NXP/ST 算法包、DSP 自带 USB 栈与 boot 机制、国产 SoC SDK。
10. 其余未核零星:AECMOS ONNX 条款、linuxptp GPL 版本、rt_ota 闭源库条款、Bonjour Windows 再分发条款、Electron 路线 mDNS npm 库、acoustic-toolbox fork 许可、freeDSP aurora 固件许可、barebox 主源、ITU-T P.831/P.832、RWTH AIR 房间 IR 库、AES67-2023 vs 2018 逐条差异、G.168 ERLE/CSS 条文逐条核对、SMPTE/JT-NM 新互通体系、IEEE 1588 专利态势、Shure《Audio Systems Guide for Meeting Facilities》官方下载页、OSC 生态 REAPER Stash 上游脚本许可、QMdnsEngine 能力源码级确认、CherryUSB 当前 release、FFTConvolver 延迟宣称实测、Qt 商业版价格、rePhase 可商用性、Loizou 书配套代码、Cohen/Gerkmann 主页代码条款。
11. 链接维护:AES(aes.org→aes2.org 全量)、Symetrix v7.0 PDF(404,存镜像)、Gerkmann(301→uol.de)、Rangachari(TLS 失效)、Tympan 文件路径、QSC(301→help.qsys.com)、Sennheiser PDF(本地存档)。

### 4.3 非 NN 范围外记录(不展开)
DTLN-aec/DeepFilterNet 系、RNNoise、Deep AHS 系、NN 自动混音(automix-toolkit)、neural_residual_echo_estimator(WebRTC 主干构建裁剪点)。

---

## 5. 对 G3 选型的输入:平台耦合发现

| 候选 | 绑定平台 | 影响 |
|---|---|---|
| CMSIS-DSP | Arm Cortex-M(MVE/DSP 扩展)/Cortex-A(Neon) | 非 Arm 核只剩纯 C 参考路径,失去性能优势 |
| TI DSPLIB/MATHLIB | TI C64x+/C66x/C674x 内联指令 | 非 TI 选型完全不可用;选 TI 则升采用候选 |
| XMOS lib_audio_dsp / lib_xua | 许可限 XMOS 硅片(XMOS Public Licence V1) | 等同平台锁定;「DSP+XMOS USB 桥」拓扑值得架构评审对比 |
| ADI SigmaStudio / SS for SHARC / SAM SDK | ADI SigmaDSP/SHARC;SS for SHARC 需付费 CCES | 平台锁定;SAM SDK 为 BSD-3-Clear(无专利授权) |
| ESP-DSP | Xtensa/RISC-V(ESP32) | 8x8 全矩阵算力吃紧,平台本身大概率不成立 |
| flexPTP | STM32F4/F7/H7、TM4C1294、K64F(Cortex-M+EMAC 硬件时戳) | DSP 芯片 EMAC 是否有 1588 时戳硬件是选型前提 |
| Statime | Rust 工具链;示例耦合 STM32+smoltcp | 无 Rust 能力则仅作 1588-2019 行为参考 |
| Dante DEP | 宣称 Arm Cortex-A + Linux(**未核,商务确认**) | 裸机 DSP 路线只能走外挂模块(占 PCB/BOM) |
| linuxptp / RAUC / SWUpdate / U-Boot / Avahi / GStreamer | 嵌入式 Linux | 仅「Linux SoC + DSP 协处理」架构适用;GPL 独立进程路径需法务评估 |
| MCUboot | 官方 port 集中 Cortex-M + Zephyr/mynewt 系 flash HAL | 非 Cortex-M DSP 需自写 boot port(工作量中等) |
| Zephyr usbd_uac2 | Zephyr RTOS 整体 | 不可单独抽用;DSP 平台大概率不在支持列表 |
| TinyUSB / CherryUSB | 按 USB IP 移植(DWC2/MUSB/CHIPIDEA/EHCI 等) | DSP 用非常见 IP 需自写 porting |
| Tympan_Library | Teensy(Cortex-M7)/arm_math | AFC 代码需剥离框架 |
| yewentai ANF | TI C5515(C55x 汇编) | 汇编部分不可移植 |
| Qt/JUCE/Avalonia/Tauri/Electron | 桌面(上位机侧) | 与固件平台无关;Qt Graphs GPL-only 影响绘图子选型 |
| WebRTC AEC3 / webrtc-audio-processing | 桌面级 C++/abseil | 固件不现实,定位上位机/基准 |
| Audio Weaver | 16 家半导体伙伴(官方页) | 弱耦合但绑其工具链与授权服务 |

结论要点:目前池内嵌入式组件以 Arm Cortex-M 生态覆盖最全(CMSIS-DSP+TinyUSB+MCUboot+flexPTP 可拼出完整底座);选 TI/ADI 传统 DSP 核则 DSP 库靠厂商、USB/boot/PTP 均需自写 port;「Linux SoC(网络/控制面)+ DSP(音频面)」双芯架构可解锁 RAUC/U-Boot/linuxptp/exFAT-OIN 一批组件,但引入 GPL 进程级合规评估。

---

## 6. 覆盖与盲区声明

1. **中文生态未覆盖(12/12 维度一致自认):** 国内厂商闭源 SDK(声网/腾讯/讯飞/声加等)、国产 DSP/SoC(进芯/杰理/中科蓝讯/全志/炬芯)算法库、国产 AoIP 模块、知网/Gitee 中文论文与开源、信创 OS(UOS/麒麟)UAC 兼容性——均未调查。仅命中 athena-signal、CherryUSB、RT-Thread、DSPPA DP8005 四个锚点。如需补齐,专项中文检索。
2. **各维度 not_covered 原样保留:** 已在第 4 节汇总去重;逐维度原文见扫描池 JSON(/home/it1234/processor/research/sources/w0a_sweep_results.json),本报告不删减。
3. **能力/成熟度结论全部 = [L4/文献]:** 本报告任何「支持/量产于/表现标杆」等表述均来自文献与主源文档核验,**无一经本团队实测**;不得当作已验证性能引用。尤其:SpeexDSP 512ms、flexPTP <100ns、PTPd 微秒级、FFTConvolver 零延迟、AEC3 会议室长尾适配性,均为自述/推断,待实测。
4. **license 结论两档:**「已核主源」= 反驳式核验抓到 LICENSE/EULA/权利页原文或权威 API(本报告已逐条附 evidence_url);「未核」= 观望/规避跳过项与 3 个条款未决项(字段级 unresolved 1 项:MATLAB 示例;na 且使用条款未决 2 项:PESQ/POLQA 参考实现、ETSI 噪声库——F-02 对账口径)——未核项一律禁入选型依据。
5. **核验覆盖率:** 131/197 候选经反驳式核验(观望/规避 66 项按规则跳过);131 项存在性全部 confirmed,0 项 not_found/misdescribed,故无剔除条目;capability 裁定(作者终审按 journal 核对修正):supported 124、overstated 5(Mbed TLS EdDSA、REW API 需 Pro、exFAT 宣称过宽、G.167「无替代」、P.862 文本状态过时)、unverified 2(QMdnsEngine 能力清单、AES17「AP 内置模式」宣称)——5 项 overstated 已在总表按核验修正,不得引用扫描原文。
6. **核验手段限制:** IEEE Xplore/ScienceDirect/Wiley/MDPI/mdpi、analog.com、Extron、audinate.com 等存在反爬/付费墙,相应条目经 Crossref/dblp/作者主页 PDF/出版社目录/Debian sources 等多源交叉;两个会话的 WebSearch 配额中途耗尽,余量改 WebFetch 直抓主源完成;SigmaStudio「免费」与 AES17 专页留有次级证据缺口。
