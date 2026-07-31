# STAGE4_BRINGUP_CHECKLIST — 阶段 4（实时音频通路）bring-up 预防清单

> 性质：2026-06-06 全天错误/教训的预防性总结（R24–R34 共 11 轮 critic 门 + 1 次 workflow 编排）。
> 适用：M1 透传 / H2R 重测 / O1 上板 / M2 算法入环——所有阶段 4 板上动作开工前过一遍。
> 分角色教训已同步写入 agents/{dsp-algorithm,critic,project-manager}/memory.md（repo 实际路径）。
> 维护：每轮板上返工后追加；条目带来源（critic 轮次 + commit）。

---

## A. 符号/头文件类（R25 MDMA 9-error 根源，今天代价最大的一类）

- [ ] **A1 写板代码前先符号预查**：凡 BSP/SSL 符号，先在本地 KB 例程里找实调（[L1-example-called]
      标 文件:行）；例程没调过的一律 [board-confirm] 占位+TODO，不许凭离线推测写完撞编译错。
      （来源：R25——离线猜 adi_mdma.h 单 handle 模型 → 板上 9 error 返工一轮）
- [ ] **A2 header 后缀非对称逐 driver 核**：同一 BSP 树里 adi_sport.h（无后缀）/adi_twi_2156x.h
      （_2156x）/adi_spu_v3.h（_v3）三种命名并存，且 adi_sport.h 与 adi_sport_2156x.h 同名双版并存。
      bring-up 第零步在安装版 2.12.1 include 树逐 driver 确认确切头名，不得假设例程（2.11.1）名字
      通用。（来源：R25 adi_mdma 无后缀版不存在 + R31 F31-MAJOR-1 + R32）
- [ ] **A3 派单文字与签名自相矛盾时不默认**：参数计数类矛盾（如「8 参」vs 列出 7 参）必须标
      [board-confirm-CRITICAL] 显式呈 CTO 板上数原文，不得默认采信任一方。
      （来源：R25 F25-BLOCKER-1）
- [ ] **A4 guard-stub 同源自证盲区**：stub 头若按与实现同一份情报写，参数计数/类型错永远测不出
      （mock 按 7 写、hook 按 7 调、永远 PASS）。同源情报项的唯一闭合 = 板上 grep 原文。
      （来源：R25——guard-check 结构性测不出 7v8）
- [ ] **A5 callback typedef 跨服务不外推**：A 服务的 callback 形状证明不了 B 服务用同一 typedef
      （adi_tmr 证明不了 adi_mdma）。异 typedef 时改签名，**永不强转**。（来源：R25 F25-MAJOR-1）
- [ ] **A6 手编工程 XML 后必跑 parser 验合法性**：.project/.cproject/system.svc 是 Eclipse XML，
      手编（改名/删 link/加注释）后必须 `python3 -c "import xml.etree.ElementTree as ET; ET.parse('<f>')"`
      验合法——⚠ **XML 注释内禁止 `--`（双连字符）**，否则 Eclipse 导入报「project description file is
      corrupted」。这是 CCES 工程组装的静默杀手（桌面 guard-stub 验不了工程 XML，只验 .c）。
      （来源：2026-06-08 .project hotfix——dsp 组装注释里 `tree -- 'CCES'` 破坏 XML，CTO 导入即报 corrupted）

## B. 内存放置/效度类（R24/R26——差点把自冲突假象当争用实测入账）

- [ ] **B1 测量缓冲放置 = 效度命门**：DMA/proxy 缓冲与被测工作集同 L1 block ⇒ 测到的是自冲突
      假象（产品不存在）。烧板前核 .map；不对就 `#pragma section("seg_l1_block1")`（ADI 例程同款，
      uninit 缓冲先例在档）。（来源：R24 F24-MAJOR-1 + R26 判定：三块全深居 Block 0）
- [ ] **B2 「地址连续」不是 block 归属证据**：必须 .ldf MEMORY 段边界 + 芯片 block 窗口双重裁定
      （Block 0 = 0x2403f0–0x26ffff，Block 1 = 0x2c0000–0x2effff，191/192 KB）。（来源：R26）
- [ ] **B3 pragma 桌面行为**：gcc 对 `#pragma section` 仅 -Wunknown-pragmas 警告不 FAIL；放置由
      板上 .map 重读证，**不由 guard-check 证**。不要 #ifdef 包裹 pragma。（来源：R26 F26-MAJOR-2）
- [ ] **B4 harness build ≠ 产品 build**：harness-only 产物（如 MDMA proxy 缓冲 pin 在 Block 1）
      不存在于产品 build——pin/放置决策必须基于**产品 build 的 .map**，不得把 harness .map 当产品
      事实。（来源：R34 抓总工④前提为假：产品 Block 1 实际空置 192KB）
- [ ] **B5 SPORT 缓冲落块待实证**：Block 1 = same-arbitration-class proxy，非 identical-segment
      实证；产品 SPORT RX/TX 缓冲实际落 L1 还是 L2 须 bring-up 核 .map 后才能声明
      「产品-representative」。（来源：R26 F26-MAJOR-1，义务持续）

## C. 测量口径/假绿类（R27——FG 全绿但 ISR 率错 62×）

- [ ] **C1 FG 存在性 ≠ 正确性**：count>0 ∧ off==0 只验「ISR 在触发」，验不了「率对」——62× 率错
      下 FG 照样绿。凡周期性激励，FG 必须升级为**率在带**判据（FG-B'：实测率落 [950,1050]Hz 外
      = FAIL 隔离）。（来源：R27 F27-MAJOR-2）
- [ ] **C2 软件重武装替代不了硬件周期**：过期 one-shot 上 callback 内 re-Enable，下次触发由软件
      延迟决定（数百-数千 SCLK）非编程周期 → 率坍缩数十倍。周期 ISR 用 continuous 硬件模式；
      没有就实测率兜底。（来源：R27 机理 + H2R 双版修复）
- [ ] **C3 率要实测不要反推**：ISR-on span 必须 CCNT wall 时戳包夹（span+count RAW 出齐）；
      反推 span 漏算 arm 间隙/BSP 开销时误差可达 6×（62k vs 10k）。（来源：R27 F27-MAJOR-1）
- [ ] **C4 稀疏事件单帧采样无统计意义**：~0.45 次/帧的事件单帧测增量=相位运气+首激活 cold
      （~2× warm）噪声；用 max-over-N + 冷暖隔离探针（首激活帧/稳态帧分采）。（来源：R27）
- [ ] **C5 聚合数先拆解再标签**：M_contention 20.59 MCPS 拆开 = 99.8% ISR 膨胀 + 0.2% DMA——
      标「DMA 争用」= 口径错。凡聚合实测数，入账前按机制拆解，relabel 强制随行（禁裸引）。
      （来源：R27 口径裁定 + DEC-S5-T2-CLOSURE-01 relabel 令）
- [ ] **C6 异常不解释不闭合**：base 偏 13.5% / inc_isr>联合增量——两个「能解释通」的异常背后
      一个是良性链差（CRC32 71,120 逐位对账）、一个是真 harness 缺陷。读数异常必须机理级解释
      + 量化对账后才入账。（来源：CTO 裁定 + R27 全程）
- [ ] **C7 跨 harness yardstick 必须同链**：拿无 CRC 的 H2 base 对含 CRC 的 H1 nofocus = 预期内
      13.5% 假警报。yardstick 设定时注明链内含物。（来源：R27 异常1）

## D. 帧/口径基数类（架构设计直接用，错了全链错）

- [ ] **D1 64 vs 120 双口径防混用**：64 = I/O 帧（BENCH_FRAME，块率 750Hz=FS/64 分母）；
      120 = 树内多级处理量（sz[4]={8,16,32,64} 之和，算 MMAC 用）。数据流用 64，成本账用 120。
      （来源：R33 数据表）
- [ ] **D2 buffer 尺寸重算不套例程**：例程 COUNT=300（既非 64 也非 256）；产品 TX = 8slot×64×4B×
      乒乓2 = 4096B；RX 依输入窗口决策（1/4/8 slot → 512/2048/4096B）。187.5Hz 的「256」来自
      Pipelined 例程，与 loopback 的 300 不同源。（来源：R34 ③重算）
- [ ] **D3 per-sample vs per-callback 开销分账**：拷贝/算法 work 是 per-sample（率无关恒定）；
      只有 per-callback 固定开销随块率涨（750 vs 187.5 差仅 ~0.55 MCPS）。评块率别把两类混在
      一起吓自己。（来源：R34 ①对消机制）
- [ ] **D4 「开的 slot 数 ≠ 实填的 slot 数」**：例程 SelectChannel 开 0..11 但回调只实填 8——
      读例程配置时数实填，不数开窗。（来源：R33/R34 4-in/8-out 真相）
- [ ] **D5 例程寄存器值不盲抄，位域逐个解码**：ALT 的 SAI_CTRL0=0x1B 注释写「48kHz」但 FS
      位域 [2:0]=011 实为「64-96kHz」档（48k 应 =010）——例程自身值与注释矛盾。M1 codec init
      每个寄存器值按 datasheet 位域表逐字段解码核对后才采用。（来源：R35 F35-INFO-1）
- [ ] **D6 总线帧宽 ≠ DMA buffer 尺寸**：RX buffer 只由 SPORT 实收（SelectChannel 捕获）slot
      数决定；ADC 总线帧的未收 slot 只耗 BCLK 时间不耗 DMA 空间（high-Z）。算 buffer 数捕获数。
      （来源：R35 承重澄清，P18 + ALT 4-of-8 双实证）

## E. 流程/多 agent 协作类（PM 侧）

- [ ] **E1 排队消息可能被合并吞**：给同一 agent 连发多单，回包可能只含最后一单——逐单核收，
      缺的 verdict 立即追讨（R29/R30 实例：三单连发只回 R31，追讨后补发）。
- [ ] **E2 流超时 = PM-direct 恢复**：agent API 中断后先查磁盘现场（git status + ls 产物），
      再按现场紧派单，不盲目重发原单。（来源：M1 调研实例两次恢复）
- [ ] **E3 机械落位先验证再 add**：apply 脚本 assert 失败必须中止 commit（25e9253 教训今天
      延续执行：python 改锚脚本带 assert 唯一性守卫）。
- [ ] **E4 长调研任务勿强制结构化输出**：schema 强制对多步研究型 agent 系统性失败；改磁盘
      中转（写文件+一行确认），核验员直读文件。（来源：workflow v1/v2 失败 → v3 成功）
- [ ] **E5 在档引用错按铁律五改锚留痕**：发现在档行号错引（fira_tree.c:49-52 实为饱和算术
      helper）→ 全库 grep 同错 → 改锚 + 原错自述留痕，数据侧先隔离不传播。（来源：R33）
- [ ] **E6 工程跨机传输用 git/zip，禁散文件**：CCES 工程（含 .project/.cproject/.svc/源码）跨机
      （Linux↔板机 Windows）传输必须整体 git pull 或 zip 打包——**散文件传输（微信/IM）会截断文本**，
      尤其 .project 截断 → Eclipse「project description file is corrupted」。文件级修复后**只需传改的
      那个文件**（git pull 最干净），不必整 folder 重传。（来源：2026-06-08 .project corrupted 双因：
      XML `--` + 疑似散文件截断）
- [ ] **E7 交付的工程 XML 过门前必跑 well-formed 校验**（见 A6）——critic 门对含 .project/.cproject/.svc
      的工程组装包，须把 `python3 -m xml.etree.ElementTree parse` 纳入机械校验（桌面 guard-stub 只验 .c，
      工程 XML 是盲区）。（来源：R41 PASS 却漏 XML 校验，板机导入才暴露）

- [ ] **E8 「功能通了」不能推「使能步成功」（硬件使能版反假绿）**：板上音频/功能通 ≠ 软件使能链
      生效——使能可能靠载板/上电默认（如 codec carrier default），软件路其实失败了，只在「默认 OFF
      的板」才暴露（换板静默无声）。返回码失败（rc≠0）但功能通时，**不许凭「通了」假定 rc=成功**；
      须读代码定位失败步 + 判它是否在功能依赖路径上。⚠ **rc 用 `|=` OR 多步会掩盖哪步失败**——要定位
      须 per-step 独立 rc（同 H2 ISR aggregate-hides-mechanism 教训）。（来源：R44 softcfg_rc=1 但音频通，
      F-SRU-1 未确认/换板风险 OPEN）

## F. 板侧固定动作（每次烧板前 60 秒过一遍）

- [ ] F1 冻结文件零触碰核（tree_filterbank.c / tfb_8ch.c / golden_ref.h / chirp_input.h /
      fir_coeffs_hb63.h / .ldf）
- [ ] F2 free-run 纪律：测量循环内禁断点，idle while(1) 一次读全
- [ ] F3 跑两遍，主数差 <0.1% 才入账
- [ ] F4 FG 任一不绿 = 数据隔离不入账不抢救（测准非测好）
- [ ] F5 C10：board-confirm-CRITICAL 项先清（本期：tmr continuous 枚举 / MDMA 形参原文 /
      ADI_CALLBACK 形参名 / .map 放置 / sizeof(int)）
- [ ] F6 读数回传 RAW 原值（不在板侧算 margin——C9），异常带原值报不修饰

---
*生成 2026-06-06，来源 commits ba3dfe7→b5878bf（R24–R34）。维护人：PM lead；变更过 critic 门。*
