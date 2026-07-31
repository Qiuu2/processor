# EV-21569-EZKIT 物理上板 Bring-up 检查清单

> 产出方：hardware-design teammate ｜ 任务等级：P0
> 用途：解锁 R1（算力命门）/ R14（FIRA bit-exact）/ X2（SPL 重算）三线的唯一前置动作
> 防御：PF-9（版本误判＝找错跳线＝厂商预警丢失类）
> 纯文档提取，未跑仿真。6 项信息逐项挂文档出处（文件名 + 页码），无出处该项 FAIL。

---

## 🔒🔒🔒 安全闸门（最高优先级，先读这一段）🔒🔒🔒

**在本清单出稿 + CTO 肉眼确认板子物理版本（看丝印 REV 字样）之前：**

> ### ⛔ 严禁实际接 ICE-1000 / AD-HP530ICE 仿真器
> ### ⛔ 严禁给开发板上电

**原因**：板子有 V1.0 / V1.2 / V2.1 三版，三版的 USBi/JTAG 引出方式、板载电源开关有无、供电跳线接法**各不相同**（见下方三版差异表）。
版本未确认 + 专属接线未回填 = 接线依据不明。此时若动手，可能直接踩中以下三个**厂商已警告的致命陷阱**（任一踩中即不可逆损板或连不上）：

| # | 致命陷阱 | 后果 | 出处 |
|---|---------|------|------|
| 陷阱① | **Boot 模式抢 JTAG**：开关停在 SPI FLASH BOOT，上电后板子直接 BOOT flash 里的程序（尤其 flash 里是错误程序），JTAG 仿真器抢不过，连不上 DSP | 连不上 / DSP 进非正常态 | 文档2 p3 |
| 陷阱② | **JTAG 热插拔烧硬件**：ADI DSP 仿真器**不支持热插拔**，带电插拔 JTAG，一旦出问题 99% 因带电插拔烧毁硬件 | 损板（不可逆） | 文档2 p4 |
| 陷阱③ | **供电跳线 JP1 接错**：JP1 跳 0=核心板独立供电 / 跳 1=底板给核心板供电，接错供电关系 | 供电异常 | 文档1 p6 |

**解除闸门的条件（两个都满足才可动手）**：
1. ✅ 本清单已出稿（6 项 + 三版差异表齐全）
2. ✅ CTO 已肉眼看板子丝印，确认物理版本 REV，并在下方「三版差异表」对应版本的回填位填入专属接线

---

## 挂接既有 ID

- 解锁：**R1**（算力命门）/ **R14**（FIRA bit-exact）/ **X2**（SPL 重算）
- 陷阱来源：tutorials 第 **1** 号（上电/初检）、第 **2** 号（在线调试）
- 防御：**PF-9**（版本误判＝找错跳线＝预警丢失类）

---

## 资料出处索引（本清单引用的文件）

| 简称 | 完整文件名 | 路径 |
|------|-----------|------|
| 文档0 | 0. ADSP-21569EVB开发板的硬件更新说明.pdf | knowledge_base/ezkit/vendor_docs/tutorials/ |
| 文档1 | 1. ADSP-21569EVB开发板的初始状态说明（请首先看我，涉及到上电和初检）.pdf | knowledge_base/ezkit/vendor_docs/tutorials/ |
| 文档2 | 2. ADSP-21569EVB开发板在线调试程序的详细说明.pdf | knowledge_base/ezkit/vendor_docs/tutorials/ |
| DS | ADSP-2156x-Datasheet-EN.pdf | knowledge_base/ezkit/bsp/datasheets/ |
| 原理图V1.0 | ADSP21569底板原理图V1.0（老款，无USBi接口）.pdf | knowledge_base/ezkit/vendor_docs/schematics/V1.0/ |
| 原理图V1.2 | ADSP21569底板V1.2（2024年最新，USBi接口单独引出）.pdf | knowledge_base/ezkit/vendor_docs/schematics/V1.2/ |
| 原理图V2.1 | AD-EXKIT-双A2B底板（2026最新改版）.pdf | knowledge_base/ezkit/vendor_docs/schematics/V2.1/ |

---

## 三版差异表（V1.0 / V1.2 / V2.1）★缺版本=FAIL★

> ⚠️ 板子物理版本由 CTO 肉眼看丝印确认（agent 查不到手上是哪版）。下表覆盖三版全部，**不预设版本**。

| 项目 | V1.0（老款） | V1.2（2024 改款） | V2.1（2026 双 A2B 改版） | 出处 |
|------|-------------|------------------|--------------------------|------|
| **USBi / JTAG 引出** | ❌ **第一版没把 USBi 接口留出来**，需另配一个**转接卡**才能用 | ✅ **单独引出了 USBi 的 JTAG**，用户直接插就好 | ✅ 已是改款后形态（USBi 单独引出，沿用 V1.2 改进） | 文档0 p1（"第一版没有把 USBi 接口留出来，所以做了一个转接卡，改款后我们把这个硬件小问题解决了，单独留出了 USBi 的 JTAG"）；原理图V1.0 文件名标注"老款，无USBi接口"；原理图V1.2 文件名标注"USBi接口单独引出" |
| **板载电源开关** | ❌ 无开关：直接插电源就上电（容易误操作） | ✅ **新版加了一个开关，默认 OFF**，插上电源也不会上电；拨到 **ON** 才给板子供电 | ✅ 有电源开关（沿用新版改进） | 文档0 p2（"有兄弟说开发板直接插电源就上电，容易误操作，我们新版就加了一个开关，默认是 OFF…拨开关到 ON，才可以给板子供电"） |
| **JTAG 连接方式** | 经**转接卡** + USBi JTAG 模块接入（14pin） | USBi JTAG **直接插**（已单独引出），14pin | 同 V1.2，直接插，14pin | 文档0 p1；文档1 p3（核心板"14PIN JTAG"）；文档2 p1（AD-HP530ICE 仿真器）、p4（14PIN 防呆） |
| **核心板** | ADSP-21569-SOM REV 1.0 | ADSP-21569-SOM REV 1.0（核心板原理图同名） | ADSP-21569-SOM（核心板原理图同名） | 文档1 p2/p3（丝印"ADSP-21569-SOM REV 1.0"）；各版目录均含"ADSP21569核心板原理图.pdf" |
| **底板丝印（实物照片所见，仅供 CTO 比对）** | — | 照片可见"AD-EXKIT REV 1.1"/"AD-EXKIT REV 1.2" | "AD-EXKIT REV 1.2"（文档0 p1 照片） | 文档1 p2（"AD-EXKIT REV 1.1"）；文档0 p1（"AD-EXKIT REV 1.2"） |

> **判版要点（给 CTO）**：
> - 看底板上**有没有电源开关**（拨动开关，标 ON/OFF）→ 有=V1.2/V2.1 改款；无=V1.0 老款。
> - 看 **USBi/JTAG 是否单独引出可直插**（无需转接卡）→ 可直插=V1.2/V2.1；需转接卡=V1.0。
> - 看底板丝印 **AD-EXKIT REV x.x** 字样 + 是否双 A2B 接口（V2.1 为双 A2B 底板）。
>
> ⚠️ 注意：实物丝印的 "AD-EXKIT REV 1.1/1.2" 与厂商资料目录的 "底板 V1.0/V1.2/V2.1" 命名体系不完全等同，**最终以 CTO 肉眼判定的"有无开关 / 是否需转接卡 / 是否双 A2B"三特征为准**，不以单一 REV 数字锁版本。

---

## 6 项提取信息（逐项挂出处）

### 项①　三版差异（USBi 引出 / 板载电源开关 / JTAG 连接方式）

完整差异见上方「三版差异表」。要点速览：
- **USBi 引出**：V1.0 无（需转接卡）｜ V1.2 单独引出可直插 ｜ V2.1 同 V1.2。
- **板载电源开关**：V1.0 无（插电即上电）｜ V1.2 有（默认 OFF，拨 ON 才供电）｜ V2.1 有。
- **JTAG 连接方式**：均为 14PIN JTAG；V1.0 经转接卡，V1.2/V2.1 直插。
- **不预设手上是哪版**——板子物理版本由 CTO 肉眼看丝印确认。

**出处**：文档0 p1（USBi/转接卡）、文档0 p2（电源开关 OFF/ON）；文档1 p3（14PIN JTAG）；原理图V1.0/V1.2/V2.1 文件名标注。

✅ 有出处 — PASS


### 项②　JTAG / 仿真器连接（接法 + 14pin 防呆 + 连接顺序硬规矩 + 禁热插拔）

**硬件清单**（文档2 p1）：ADSP-21569EVB 开发板 ×1 ｜ **AD-HP530ICE 仿真器** ×1（CCES 中识别为 **ICE-1000 Emulator**，见文档2 p5 设备管理器 "CrossCore Tools → ICE-1000 Emulator"）｜ USB 线 ×1 ｜ 5V2A 电源适配器 ×1。

**14pin 防呆方向**（文档2 p4）：
- 开发板 14 针 JTAG 口故意**断了一根针**（不是坏，是防反插设计）；仿真器 14PIN 母口对应有一个孔被**堵上**。
- 断针与堵孔一一对应 → 物理上插反就插不进，达到**防反插（防呆）**目的。
- 此设计源自 ADI JTAG 设计规范文档 **EE68**，写入规范要求用户这么设计，避免仿真器插反烧硬件。

**连接顺序硬规矩（必须严格按序，文档2 p4）**：
1. **先插 JTAG**（断电状态下，把仿真器排线插上板子 14pin）；
2. **再给板子上电**；
3. **再给仿真器上电**（USB 线接电脑）。

> ⛔ **禁热插拔（陷阱②，文档2 p4）**：ADI 的 DSP 仿真器**不支持热插拔**，务必、必须**在断电情况下插或拔 JTAG**，千万不要带电操作。据 ADI 20 年仿真器经验：一旦出问题，烧毁硬件 99% 是因为带电插拔 → **严禁带电插拔 JTAG 头**。

**正确连接后的状态判据**（文档2 p4）：仿真器 **Power 灯亮**、其他三个灯不亮；开发板**底板 Power 灯亮**、**核心板 LED5 亮**、其他都不亮。

**出处**：文档2 p1（硬件清单）、p4（14pin 防呆 / EE68 / 连接顺序 / 禁热插拔 / 连接后状态）、p5（设备管理器识别为 ICE-1000）。

✅ 有出处 — PASS


### 项③　Boot 模式开关（调试用 BMODE 设置 + 丝印位置 + 拨向图）

**丝印位置**：板上一个**三向拨码开关**，丝印标 **BOOT MODE**，三个拨位从上到下标 **BMODE0 / BMODE1 / BMODE2**（对应开关位置 1 / 2 / 3）；左侧标 **0**、右侧标 **1**（拨向 0 或 1）。（文档2 p3）

**SYS_BMODE 编码表（Table 7. Boot Modes，权威出处＝官方 datasheet）**：

| SYS_BMODE[n] | Boot Mode |
|---|---|
| 000 | No boot |
| 001 | SPI2 flash |
| 010 | External SPI2 host |
| 011 | External UART0 host |
| 100 | External LP0 host |
| 101 | Octal SPI flash |
| 110 / 111 | Reserved |

> 注：SYS_BMODE2 pin 仅 BGA 封装适用（DS p18 表注）。

**本板出厂 BOOT 设置**：板载做的是 SPI FLASH，正常脱机跑用 SPIFLASH boot，开关拨为 **BMODE0:1 / BMODE1:0 / BMODE2:0**。（文档2 p3）

> ⛔ **调试时必须改（破解陷阱①）**：调试是在线调程序、不是让系统 BOOT。若开关停在 SPI BOOT，硬件上电后板子直接 BOOT flash 里的程序，**JTAG 仿真器抢不过，连不上 DSP**（尤其 flash 里写了错误程序会让 DSP 进非正常态，导致仿真器无法连接 DSP）。
> **解决办法（文档2 p3-p4）**：调试 21569 时，直接把开关拨到**非 SPI BOOT 模式** —— **BMODE0、BMODE1、BMODE2 全部拨到 0**（=No boot），即可让 JTAG 顺利连上。

**拨向图（调试态，文字化）**：
```
        0 │ 1
BMODE0  ■─┤        ← 拨到 0
BMODE1  ■─┤        ← 拨到 0
BMODE2  ■─┤        ← 拨到 0
      BOOT MODE
（三个拨位全部拨向左侧 0 = No boot = 调试态）
```

**出处**：文档2 p2（Table 7 截图）、p3（丝印 BOOT MODE / 拨向图 / SPIFLASH 设置 / 抢 JTAG 警告）、p4（调试态 BMODE 全 0）；DS p18（Table 7. Boot Modes 官方权威表 + BMODE2 BGA 注）。

✅ 有出处 — PASS


### 项④　供电（5V2A / MINI USB + 跳线 JP1 + 新版电源开关 ON/OFF）

- **供电规格**：核心板可用 **5V2A 电源适配器**独立供电，供电接口是 **MINI USB 接口**。（文档1 p6）
- **供电跳线 JP1（⚠️ 陷阱③，特别注意）**：丝印标 **JP1 / POWER**。
  - **JP1 跳到 0** = 核心板**独立供电**；
  - **JP1 跳到 1** = 由**底板给核心板供电**。
  - （文档1 p6 给了两张特写：「底板给核心板供电」「核心板自己独立供电」。）
  - 接错供电关系会导致供电异常 → **上电前必须先核对 JP1 跳位与你的供电方式一致**。
- **新版板载电源开关 ON/OFF**（仅 V1.2/V2.1 改款有，V1.0 无此开关）：默认 **OFF**，插上电源也不会上电；**拨到 ON** 才给板子供电。（文档0 p2）

> 组合关系：用底板 5V2A 供整板时，JP1 跳 1（底板给核心板供电）；核心板单独拿 MINI USB 5V2A 时，JP1 跳 0（核心板独立供电）。**具体以 CTO 确认的供电方式 + 板版本回填位为准。**

**出处**：文档1 p6（5V2A / MINI USB / JP1 跳 0/1 / 两张特写）；文档0 p2（新版电源开关 OFF→ON）。

✅ 有出处 — PASS


### 项⑤　上电正确状态判据（哪些 LED 应亮 / 流水灯 / 异常如何判）

**A. 核心板单独供电（仅核心板）**：正常供电后，板子上**只亮一个 LED 灯 = LED5**。（文档1 p6）

**B. 核心板 + 底板组合，正确上电后**（flash 内预烧了出厂程序，文档1 p7）：
1. 底板 **POWER 灯亮**；底板供电指示亮；5V2A 供电指示亮；
2. 核心板的 **LED0 / LED1 / LED2 三个灯自己跑流水灯**（流水灯亮）；
3. 音频通路可用：绿色=音频输入接口（IN1-2 / IN2-3 / IN3-4 模拟输入），黑色=音频输出接口（OUT1-2…OUT11-12 / HEADPHONE），接上即可播放音乐。

**C. 仿真器接上后的正确状态**（文档2 p4）：仿真器 **Power 灯亮**、其余三灯不亮；底板 **Power 灯亮**、核心板 **LED5 亮**、其余不亮。

**D. 在线运行一个工程后**（如 LED 例程，文档2 p20）：核心板可见 **LED0/1/2 以及 LED6/7/4 共 6 个灯一起闪烁**，表示程序正常运行。

**异常判据**：
- 上电后核心板**一个灯都不亮**（连 LED5 都不亮）→ 供电异常：查电源开关是否拨到 ON（文档0 p2）、查 JP1 跳位是否接对（文档1 p6）、查 5V2A/MINI USB 是否插好。
- **流水灯不跑 / 音频不通** → flash 内出厂程序状态异常，或供电不足。
- **接仿真器后连不上 DSP** → 大概率 BOOT 开关没拨到 No boot（BMODE 全 0），flash boot 抢了 JTAG（文档2 p3）；用项⑥ 的 ICE Test 定位（文档2 p13-14）。

**出处**：文档1 p6（核心板单独 LED5）、p7（组合上电 POWER+流水灯 LED0/1/2+音频接口）；文档2 p4（接仿真器后状态）、p20（运行后 6 灯闪烁）；文档0 p2 / 文档1 p6（异常排查依据）。

✅ 有出处 — PASS


### 项⑥　CCES 连接配置（Session 路径 + platform 字符串）

**软件版本**：CCES **2.11.1**（ADI 软件不向下兼容，固定此版本；文档2 p1）。

**ICE 链路自检（Run → Debug Configurations… → Session Wizard → Configurator → Target Configurator → Test → ICE Test）**（文档2 p9-p14）：
- Type：**ICE-1000**（说明仿真器已正确装好驱动并被 CCES 识别）
- Device ID：**0**
- JTAG TCLK Frequency：**5**
- 点 Start，5 步全部打钩才算链路 OK：
  1. Opening Emulator Interface
  2. Resetting ICEPAC module
  3. Testing ICEPAC memory
  4. **1 JTAG device(s) detected**
  5. Performing scan test（如 358.67 KBytes/s）
- 第 1-3 步出错 ≈ 软件问题（关软件 / 断电重来 / 重装软件）；第 4-5 步出错 ≈ PC/仿真器/板链路（板没上电？板与仿真器没插好？仿真器坏？）。

**新建 Session 路径（SHARC → ADSP-21569 → Emulator → platform 字符串）**（文档2 p15-p18）：
1. **Run → Debug Configurations…** → 双击 **Application with CrossCore Debugger** → Session Wizard。
2. **Select Processor**：Processor family = **SHARC**；Processor type = **ADSP-21569**。→ Next
3. **Select Connection Type**：选 **Emulator**。→ Next
4. **Select Platform**：选 **`ADSP-21569 via ICE-1000`**
   （同列表另有 `ADSP-21569 via ICE-1500`、`ADSP-21569 via ICE-2000`；本板仿真器识别为 ICE-1000，**选 ICE-1000**）。→ Finish
5. Session 配置摘要字符串：**Target: Emulation Debug Target ｜ Platform: `ADSP-21569 via ICE-1000` ｜ Processor: ADSP-21569**。
6. 先 **Apply**，再 **Debug**。

> **platform 字符串（回填/核对用）**：`ADSP-21569 via ICE-1000`
> （早期文档截图里 Target Configurator 模板列表用的是 `ADSP-21569 (1 processor) via ICE-2000` 占位示例，但最终新建 Session 时 Select Platform 选的是 `ADSP-21569 via ICE-1000`；文档2 p9 vs p18。**以 ICE-1000 为准**。）

**结束调试规矩**（文档2 p20）：下班/结束调试时，**不要直接关软件断电** —— 要先在软件里**断开软硬件链接**（disconnect），再断电。

**出处**：文档2 p1（CCES 2.11.1）、p9-p14（ICE Test：Type/Device ID/TCLK/5 步判据）、p15-p18（Session Wizard：SHARC→ADSP-21569→Emulator→platform 字符串 `ADSP-21569 via ICE-1000`）、p20（结束调试先 disconnect）。

✅ 有出处 — PASS


---

## 逐步可操作上电流程（编号步骤，可打勾）

> ⛔ **执行前置条件**：顶部安全闸门两个条件已满足（清单已出稿 + CTO 已确认版本并回填专属接线）。否则**不得执行 step 1 以后任何带电/接线动作**。

**Phase 0 — 断电准备（全程板子不带电）**
- [ ] 0-1　CTO 已肉眼看丝印，确认板子物理版本（有无电源开关 / 是否需转接卡 / 是否双 A2B），并填好「回填位」专属接线。（项①）
- [ ] 0-2　确认板子当前**未上电**（电源未插 / 新版电源开关在 OFF）。（文档0 p2）
- [ ] 0-3　核对供电跳线 **JP1** 跳位与计划供电方式一致（0=核心板独立 / 1=底板供电）。（项④，文档1 p6）
- [ ] 0-4　把 **BOOT MODE** 三位拨码全部拨到 **0**（BMODE0/1/2=0，No boot），破解 boot 抢 JTAG。（项③，文档2 p3-4）

**Phase 1 — 断电态接 JTAG（顺序硬规矩 step 1）**
- [ ] 1-1　**仍断电**，按 14pin 防呆方向（断针对堵孔）把仿真器排线插上板子 JTAG 口，不可插反、不可硬怼。（项②，文档2 p4）

**Phase 2 — 给板子上电（顺序硬规矩 step 2）**
- [ ] 2-1　接 5V2A / MINI USB 电源到对应供电口。（项④，文档1 p6）
- [ ] 2-2　若为新版（有电源开关）：把电源开关拨到 **ON**。（文档0 p2）
- [ ] 2-3　看 LED 判据：底板 **POWER 灯亮** + 核心板 **LED5 亮**（仅核心板供电时只 LED5）；出厂程序在跑时 LED0/1/2 **流水灯**。异常→回 Phase 0 查开关/JP1/电源。（项⑤，文档1 p6-7）

**Phase 3 — 给仿真器上电（顺序硬规矩 step 3）**
- [ ] 3-1　仿真器 USB 线接电脑。（文档2 p4）
- [ ] 3-2　看判据：仿真器 **Power 灯亮**、其余三灯不亮；底板 Power 亮、核心板 LED5 亮。（文档2 p4）
- [ ] 3-3　设备管理器确认 **CrossCore Tools → ICE-1000 Emulator**；若未自动装驱动，手动指向 `CCES 安装目录\Setup`。（文档2 p5）

> ⛔ **全程禁热插拔**：以上任何时刻要拔/插 JTAG，**必须先断电**（板 + 仿真器都断电）。带电插拔 JTAG = 99% 烧板。（项②，文档2 p4）

**Phase 4 — CCES 链路自检（ICE Test）**
- [ ] 4-1　CCES 2.11.1：Run → Debug Configurations → Session Wizard → Configurator → Target Configurator → Test。（项⑥，文档2 p9）
- [ ] 4-2　ICE Test：Type=**ICE-1000**，Device ID=**0**，TCLK=**5**，点 Start。
- [ ] 4-3　确认 5 步全打钩（含 "1 JTAG device(s) detected" + scan test 通过）。出错按 1-3 步=软件 / 4-5 步=链路 分流定位。（文档2 p13-14）

**Phase 5 — 建 Session + 跑验证程序**
- [ ] 5-1　新建 Session：SHARC → **ADSP-21569** → **Emulator** → Platform **`ADSP-21569 via ICE-1000`**，Apply→Debug。（项⑥，文档2 p15-18）
- [ ] 5-2　跑 LED 例程，确认核心板 **LED0/1/2 + LED6/7/4 共 6 灯一起闪**＝链路全通。（文档2 p20）

**Phase 6 — 收尾**
- [ ] 6-1　结束调试时：先在 CCES 内 **disconnect 断开软硬件链接**，再断电；不要直接关软件断电。（项⑥，文档2 p20）
- [ ] 6-2　拔 JTAG 前**先断电**（板 + 仿真器）。（项②，文档2 p4）

---

## CTO 版本确认后回填位（agent 标专属接线）

> 三版接线见上方差异表；**CTO 确认丝印 REV 后，本清单由 agent 标出对应版本专属接线**。在此之前以下为待回填空位，不锁定单一版本。

**【待 CTO 确认 REV 后回填专属接线】**

- CTO 确认的物理版本：`________`（V1.0 老款 / V1.2 改款 / V2.1 双A2B改版；依据：有无电源开关 / 是否需转接卡 / 是否双A2B）
- 该版本 **USBi/JTAG 专属接法**：`________`（V1.0=经转接卡接 USBi JTAG 模块；V1.2/V2.1=USBi JTAG 直插 14pin）
- 该版本 **电源开关动作**：`________`（V1.0=无开关，插电即上电，更要注意先拨 BMODE；V1.2/V2.1=拨 OFF→ON）
- 该版本 **JP1 供电跳位**：`________`（0=核心板独立 / 1=底板供电，按实际供电方式定）
- 该版本 **上电 LED 判据补充**：`________`（核对实物 LED 丝印编号）

> ⚠️ 回填前严禁接 ICE-1000 / 上电（见顶部安全闸门）。

---

*ezkit_bringup_checklist.md ｜ hardware-design teammate ｜ 纯文档提取*
