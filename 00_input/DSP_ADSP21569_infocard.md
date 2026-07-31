# ADSP-21569 芯片信息卡 + 平台资料复制清单 — 原文入库件
> 来源:CTO ｜ 接收:2026-07-30(本会话粘贴)｜ 入库:2026-07-30(铁律六,<24h)｜ 台账:decisions_log 外部输入台账 ｜ 关联:DEC-0006(选型)
> **L 标转录口径**:下文所有 [L1] 为 **ITC 项目(同芯片)实测口径**,其行内出处(ds:xxx / R14 / F4 handoff 等)指向 ITC 项目文件;在本项目引用时登记为 `[L1/ITC同芯片实测,场景迁移待本项目复核]`。原文一字未改。

---

一、芯片信息卡(数字带 L 标)
项	值	来源
主控	ADSP-21569,SHARC+ 单核 ≤1GHz float(不是双核——旧 yaml 那个 dual core 是错值)	[L1] ds:153 / DEC-S3-PROC-01
家族	ADSP-2156x(21562/63/65/66/67/69)——datasheet/HW ref 通用	ADI 官方
浮点	原生 IEEE 32/40/64-bit float 硬件;但本项目锁定点(MCPS 效率考量,非硬件限制)	—
实时硬底	48kHz / 64 样本/帧 → 750 fps;周期 1.3333ms = 1,333,333 cyc @1GHz	[L1]
FIRA 加速器	1024-word 系数 + 1024-deep 延迟线,4×32-bit MAC(定点 32×32→80-bit accum),定点≤1024 taps,ACM 模式 TCB 链可无限通道,定点/浮点皆可	fira_fit_assessment.md:38-50
FIRA 官方加速	3.07×(裕量 2.878×)——⚠禁用 3.13× 混 build 值;引用须连体呈现 §8 未计入清单	[L1] R14 CLOSED
板上真实算力	30-50 cyc/MAC(含 cache/中断),禁用理想 1cyc/MAC 记账——桌面 33×/17× vs 板上 1.32×,差 ~25× 就栽在这	[L1] ds:234
工具链	CrossCore Embedded Studio(CCES)2.12.1(免费,需 license 注册) + SHARC Audio Module BSP	已在手
Codec	ADAU1962A(DAC/8ch) + ADAU1979(ADC) + ADAU1963,TDM	datasheets/
Cache 坑	DMA 输出读前 只 invalidate 不 flush,SHARC 用 <sys/cache.h> flush_data_buffer——不是 ARM 的 adi_cache_invalidate	F4 handoff:29-31

二、复制清单(三层)
🟢 第 1 层:ADI 官方料 —— 整包复制,100% 可复用(与产品无关)
knowledge_base/ezkit/bsp/(244M)。这些是 ADI 自己的文档,换任何产品只要芯片同,照搬。
目录	大小	内容
bsp/datasheets/	17M	2156x datasheet + codec(ADAU1962A/1979/1963) + flash/LTC
bsp/hw_reference/	17M	ADSP-21569 HW Reference(上板必读)
bsp/app_notes/	8.8M	⭐Using 2156x FIR/IIR Accelerators(FIRA 圣经+code) + System Optimization Techniques(算力预算) + Power(ee414)
bsp/sw_reference/	5.9M	SHARC+ Core Programming Reference
bsp/reference_design/	46M	ev-somcrr / ev-21569-som 原理图设计库
bsp/ibis_models/ + bsp/fira_headers/	156K	IBIS/BSDL 仿真模型 + FIRA legacy 头
bsp/a2b/	2.6M	A2B 开发详解(若新项目用 A2B)
bsp/installers_windows/	47M	CCES/EZKIT 安装包(Linux 开发可跳过,你已有 .deb)
最小集(省掉 47M Windows 安装包 + 若不用 A2B):约 95M。
🟡 第 2 层:踩坑攒的平台知识 —— 真金,复制并去产品化
这些是你这个项目用命换来的、换产品也用得上的芯片/板级本事:
sprint6/STAGE4_BRINGUP_CHECKLIST.md          130行 上板静默无声/杂音32坑(采样率档/TDM帧错位/SRU路由/cache)
sprint3/audit/ezkit_bringup_checklist.md     284行 EZKIT bring-up(JTAG/boot mode/供电跳线)
.claude/skills/dsp-algorithm/SKILL.md        115行 ⭐FIRA集成5件套+假绿验证+30-50cyc/MAC(去掉波束/几何段)
sprint3/dsp/tree_filterbank.{c,h}            355行 定点参考实现:Q15×Q31→Q46→Q31+饱和原语(SHARC定点范式)
sprint2/dsp/cces_template/                    ~1.5k行 CCES工程骨架(.ldf内存布局/TDM DMA/SIMD)
knowledge_base/ezkit/prep/PREP-*.md          三份:DSP迁移/HW bring-up/cycle方法学

---
> 入库注:清单标题写「三层」但正文仅见 🟢/🟡 两层;第 3 层(推测=产品相关不可复用件,按 ITC README 惯例丢弃)待 CTO 确认或补发。
