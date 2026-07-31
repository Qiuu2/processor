# 硬件 Bring-up 准备简报 — EV-21569-EZKIT 上电前必查清单

**文档**：PREP-HW-EZKIT-BRINGUP-01 | **作者**：hardware-design teammate | **日期**：2026-06-01
**对象**：CTO（物理板已在手） | **战略地位**：Sprint 3 R1 命门（算力实测）P0 路径
**资料状态**：21 份 vendor PDF + BSP **尚未入库**。本简报基于 ADI SHARC / EZKIT 通用领域认知，凡具体数值/型号标注 **待 vendor_docs 确认**，资料到位后精读填实。

> 总原则：**先连通（JTAG）→ 先用仿真器加载（不碰 flash）→ 后验供电**。开发调试阶段全程走 emulator boot，把"烧 flash"推迟到算力实测拿到 [L1] 数据之后，最大化降低首板风险。

---

## 1. ICE-1000 / JTAG 连接

**接口形态**
- ADI ICE-1000 是低成本 JTAG/SWD 仿真器，对 SHARC/SHARC+ 走 **JTAG**。ICE-1000 标准提供 **10-pin 2×5、1.27mm 间距（0.05"）** 的 mini 排线（区别于早期 14-pin ADI JTAG header）。**EZKIT 上对应的调试 header 引脚数/间距/丝印（J 几）待 vendor_docs（EZKIT 原理图 + manual）确认** — 21569 EZKIT 可能同时板载 USB 调试链路（板载仿真器）或仅留 ICE 排针，需核实板子是"裸 header 需外接 ICE-1000"还是"板载 debug + 另留 ICE header"。
- ICE-1000 经 **USB（Micro-USB/Type-C，待确认）** 连 PC，由 CCES 驱动；首次插入需识别 ADI 仿真器驱动（CCES 安装包内含）。

**CCES 里配 emulator**
1. CCES → 新建/编辑 **Debug Configuration**（Application with CrossCore Debugger）。
2. **Processor**：选 ADSP-21569（SHARC+ 单核，DEC-S3-PROC-01 LOCKED）。
3. **Connection type / Debug interface**：选 **ICE-1000**（区别于 ICE-2000 / EZ-KIT 板载仿真器）。
4. **Platform/Session**：选对应 21569 平台，JTAG。
5. 加载 .dxe 到 core，运行/单步。

**首次握手要点**
- 接线前**先确认目标板已上电**（ICE-1000 不给目标供电，通过 Vref 引脚检测目标电平）。
- JTAG 速率首连用**保守低速（如 5–10MHz 或更低）**，握手稳定后再提速，避免长排线/信号完整性导致 scan chain 失败。
- 排线**方向/第 1 脚对齐**（红线/丝印三角），插反可能无响应。
- 若 CCES 报 "cannot connect / scan chain error"：依次查 ① 目标供电 ② JTAG header 未焊跳线/0R ③ boot mode 是否锁死内核 ④ 复位是否被外部拉住。

---

## 2. Boot mode / 启动配置

**21569 boot 模式（通用认知）**：由 **SYS_BMODE[] 引脚**在复位时采样决定 boot 源，典型含：
- **No-boot / Emulator boot（idle，等仿真器加载）** ← **开发调试阶段首选**
- **SPI master boot（板载 SPI flash 启动）** ← 量产/脱机运行
- **UART slave / SPI slave 等 host boot**

> **具体 BMODE 编码值、模式枚举、引脚电平组合，待 vendor_docs（21569 datasheet Boot Modes 表 + HW reference System Boot 章）确认。不臆造编码。**

**EZKIT 上的拨码/跳线**：一般用 **BMODE 拨码开关（SW_BMODE）** 设 boot 源。**具体开关位号、ON/OFF 与 BMODE 对应表，待 vendor_docs（EZKIT manual "Boot Mode" 配置表 + 原理图 BMODE 网络）确认。**

**调试阶段该选哪个**：**emulator / no-boot 模式**——复位后内核空转等 CCES 经 JTAG 直接加载 .dxe。理由：R1 命门是**算力 cycle 实测**，全程在 CCES 调试器加载/运行/读 profiler，**不需要也不应烧 SPI flash**，避免镜像格式/启动头出错变砖。flash boot 留到 [L1] 数据拿到、需脱机 demo 时再做。

---

## 3. 供电与跳线

**供电方式**：EZKIT 类板通常支持 **外部 DC 桶形插孔（barrel jack）** 主供电，部分可 USB 供电。**21569 EZKIT 的额定电压/电流（典型可能 +5V 或 +12V）、插孔极性（中心正/负）、是否配原装适配器、能否纯 USB 供电，全部待 vendor_docs（EZKIT manual 电源章 + 原理图电源树页）确认 —— 最易烧板环节，绝不臆测电压。**

**关键供电跳线/分流**：各电压轨常串 **电流测量跳线/0R（measurement jumper）**。首次上电**保持出厂默认全部短接/装上**，不要为测电流先拆，避免某轨断电导致部分上电。可能有 **电源源选择跳线**（外部 DC vs USB），确认与实际供电一致。**具体位号/默认状态待 vendor_docs 确认。**

**上电安全顺序（防烧板）**
1. **先目视**：无异物/短接、跳线在出厂默认位、确认供电参数（查到 manual 前不上电）。
2. **先供电、后接 USB/JTAG**：用确认过的适配器先供电，观察电源指示 LED 正常、无异味/发烫。
3. 稳定数秒后插 ICE-1000 / USB → CCES connect。
4. **多电压轨上电时序由板载 PMIC/稳压器保证**（core/IO/DDR/PLL；原则 Core→I/O→模拟）。**我方不改板，只需用对输入电压**，时序交给板子。
5. 断电反序：CCES disconnect → 拔 JTAG → 断主供电。
6. **首次上电勿带负载**（不接喇叭阵列/功放，先裸板跑 cycle 实测）。

> 红线：在 manual 标明的额定输入电压/极性确认之前，**不上电**。错压/反极性是首板最高烧毁风险。

---

## 4. 待抽取清单（资料入库后核实）

- **EZKIT 原理图（vendor_docs/ schematic PDF）**：电源树页（插孔电压/极性、稳压拓扑、各轨、电源 LED 位号）→§3；BMODE 网络页（接哪个拨码）→§2；JTAG/debug header 页（位号/引脚数 10/14、间距、Vref）→§1；电流测量跳线页→§3。
- **EV-21569-EZKIT manual / HW reference**：Power 章（额定电压/电流、适配器、USB 供电）→§3；Boot/BMODE 配置 + 拨码表→§2；Jumper settings 汇总（出厂默认）→§3；Debug/Emulation 章（板载仿真器 vs ICE-1000、CCES 连接）→§1；LED/push-button 章（电源/状态 LED、复位按钮位号）→§3。
- **ADSP-21569 datasheet**：Boot Modes 表（BMODE 编码）→§2；电气规格（各轨标称/容差、复位时序、绝对最大额定）→§3；JTAG/Test 章（引脚、Vref）→§1。
- **EE-notes**：ICE-1000/CCES 连接、JTAG 速率排障类应用笔记→§1。
- **BSP / CrossCore SDK example（bsp/）**：21569 example 的 Debug Configuration / .ldf → 参考 emulator session 配置与内存布局（移交 dsp-algorithm 作工程骨架基准）。

---

**交付状态**：上电前 checklist（资料未入库版）。所有标 **待 vendor_docs 确认** 项不可当事实使用；资料入库后精读 §4 文档对应章节回填，再交 critic 评审。下一步依赖：CTO 拷入 vendor_docs/bsp → 触发精读。
