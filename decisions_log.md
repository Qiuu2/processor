# CONF-DSP-88 decisions_log
> 每条含 6 字段:依据数字/来源等级/数据出处/可逆性/验证状态/风险声明(可合并行,不得缺项)。LOCKED 项变更须记旧→新/日期/原因/批准人。

---

## DEC-0001 治理采纳(2026-07-30,LOCKED)
- **决策**:原样继承 starter kit 治理(L0-L4/九铁律/C1-C10/三道关/不可逆→L1/假绿纪律),项目版落域文件 `00_governance/GOVERNANCE_CONFDSP.md`;C9/C10 域化为「选型收益闸」「硬件/发布不可逆动作闸」。
- 依据:AGENT_TEAM_PLAYBOOK Part 1 + POLICY-PROV-001 v1.8 ｜ 可逆性:强约束(修订须 CTO 批)｜ 验证:制度性条目,无数字 ｜ 批准:CTO 2026-07-30(本会话"确定")。

## DEC-0002 Roster v1.0(2026-07-30,LOCKED)
- **决策**:8 角色(orchestrator/critic/system-architect/channel-dsp/adaptive-dsp/platform-fw/host-software/verification),模型分档见 `.claude/team_config.md`;**并发 ≤4**;control-protocol 并入 system-architect(参数字典与协议同源);platform-fw 拆分触发条件=Dante/AES67 进实测阶段。
- 依据:阶段1 PRD 工作分解 + 外部反思(MAST arXiv:2503.13657 失效统计 42%/37%/21% [L4/文献引用];3-4 并发收益递减 [L4/文献];Q-SYS QRC=参数模型投影 [L4/厂商文档];van Waterschoot&Moonen 2011 AFC 独立域 [L4/文献])。
- 可逆性:**方向性/可逆**(组织类决策,增删角色留痕即可;F-04 修正 2026-07-30,原误标"强约束")｜ 上行文献统计为**背景引用,非决策依据数字** ｜ 验证:随 sprint 实践回填 ｜ 风险:文献结论未在本团队实测,并发上限若碍事按变更流程调 ｜ 批准:CTO 2026-07-30。

## DEC-0003 范围与口径(2026-07-30,LOCKED)
- **决策**(CTO 直接指示,本会话):
  1. 交付边界=全周期到芯片落地(固件 C+上位机+板级),企业产品级。
  2. DSP 平台未定型,候选资料 CTO 后送 → 选型评估工单,门槛 L2+签字起步、量产冻结待 L1。
  3. "AI"仅产品叫法:**全部传统自适应/统计声学算法,不含 NN 推理**;日后若要 NN 卖点须重开算力预算(记为范围变更)。
  4. AoIP 兼容 **Dante/AES67**;Dante 授权方案选型采购入不可逆清单;AES67 互通承诺须第三方设备 L1。
  5. 中控协议**私有**;冻结前真机联调 L1+签字。
  6. 上游厂家界面编辑软件可获得,CTO 后送 → 铁律六 24h 入库;定级口径:操作观察到的行为=对该软件行为的 L1,推断其内部协议/算法=L3/L4。
- 可逆性:范围级强约束 ｜ 验证状态:1/3/4/5 为 CTO 指示口径 **[CTO 指示 2026-07-30]**(权威指示不占用 L 级;F-06 修正,原误标"L1/CTO 指示");待办=DSP 资料入库、上游软件入库 ｜ 风险:Dante 授权成本/货期未知 [L4/待询价]。

## DEC-0004 critic 首审与修复(2026-07-30)
- **事件**:团队配置骨架首审,独立 critic(`reviewer: critic @ claude-fable-5 / 2026-07-30`)裁定 **FAILED**(BLOCKER F-01 PRD 未入库 + MAJOR F-02 critic 轮换纪律缺失 + MINOR×6 + INFO×2)。
- **修复**(同日):F-01 PRD 入库 `00_input/PRD_CONFDSP.md` + 台账补行 ｜ F-02 team_config 增「Critic instance rotation」纪律 ｜ F-03 C10 限定物理动作,发布类走 §2 清单+G4/G5 ｜ F-04 DEC-0002 改判方向性 ｜ F-05 本条追溯留痕:**critic skill §4 九门域清单 = 阶段1提纲⑤修订版,CTO 2026-07-30 确认** ｜ F-06 DEC-0003 验证状态改标 [CTO 指示] ｜ F-07 CLAUDE.md/team_config 补 escalation 例外 ｜ F-09 G 表补 AES67/USB 映射 ｜ F-10 orchestrator 补让位规则。
- **待 CTO 决**:F-08 `git init` + 首 commit 走完整三道关(涉版本库初始化,lead 不自行执行)。
- **R2 复审(同日)**:`reviewer: critic @ claude-fable-5 / 2026-07-30` 裁定 **PASSED_WITH_MINOR(附条件)**。F-01~F-07/F-09/F-10 闭环实证关闭;F-08 确认为开放项归 CTO 第三关;新增 F-11(critic skill:9 速查残留旧 C10 口径——已按 critic 明文豁免修法落地)、F-12(CLAUDE.md PRD 指针+文件地图——已落地)。
- **F-13 流程偏差留痕(原样,不粉饰)**:lead 自验声明「"OTA 发布/协议冻结前" 0 命中」失实——实际 grep 范围仅 `00_governance/`,未全库扫,critic/skill.md:9 残留被 R2 抓出。教训:**自验 grep 必须附 命令+范围+命中数,可复现才算数**;已入 orchestrator memory。
- 状态:**独立门(第二关)正式放行**——R1 FAILED → 修复 → R2 PASSED_WITH_MINOR → **豁免件核销回执**(同日,critic 逐项实证:F-11 措辞逐字一致、F-12 落地、F-13 留痕+根因、变更范围 mtime 无越界)。放行范围=配置骨架文档本身,不含 commit 动作(F-08 裁决前无 commit 可执行)。
- 待第三关(CTO 常识审),议程:①F-08 git init 裁决 ②PRD「一字未改」背书 ③DEC-0002 改判追认 ④两轮 verdict+核销回执归档;**CTO 过后本条补记第三关结果,闭环**。
- 后续纪律:新工单(W1 D1+D13 / W2 链序提案 / W3 选型评估)首审按 rotation 规② **spawn 全新 critic 实例**,不续用本工单链实例。
- **第三关(CTO 常识审)通过(2026-07-30,会话确认「没意见」)**:①F-08 批准——git init + 首 commit ②PRD 入库件 CTO 背书 ③DEC-0002 改判(强约束→方向性/可逆)追认 ④两轮 verdict+核销回执随首 commit 归档。**本工单(配置骨架)三道关全部闭环。** 首 commit = `ac93ded`(main,2026-07-30;本行为 critic 核销回执预授的行政留痕,随下一工单 commit 入库)。

## DEC-0005 W0 预研·技术雷达 D0(2026-07-30)
- **事件**:CTO 批准开 workflow 全量档(预算不设限、专利不深挖)。段1 扫描 12 路(12 agents,197 候选)→ 段2 反驳式核验+合成(13 agents,131 项承重结论逐条核:存在性 131/131、license 71 已核+1 corrected+1 unresolved、能力 5 项 overstated 推翻、2 项 unverified)→ 作者终审 2 处修正(D 编号按 WBS 重排、统计 124/5/2)→ **critic-w0(全新实例,rotation 规②)首审 PASSED_WITH_MINOR**(0B/0M/2MINOR/2INFO;第三轨直抓 6 条主源 0 偏差、9 个高特异性数字 0 幻觉)→ F-01~F-04 按修法落地。
- **产出**:`research/D0_tech_radar.md` v1.0 + `research/sources/`(w0a 扫描池/w0b 核验裁定/flags)。成本:25 agents,~166 万 subagent token [L1/用量计数]。
- **纪律**:雷达全部结论 = [L4/文献],license 分「已核主源/未核」两档,未核禁入选型依据;**本报告不触发任何选型**,选型仍走 G3。
- **可逆性**:方向性(文献基线)｜ 验证:能力/性能结论全部待实测回填 ｜ 风险:中文生态未覆盖(12/12 维度自认);观望/规避 66 项未复核档位合理性。
- **闭环回执(同日)**:critic-w0 独立复核落地稿——四条自验 grep 亲手重跑一致(F-13 教训执行)、四处修正区目检通过、未引入新错(:269/:315 旧措辞裁定与新口径不冲突免改)、commit 8c08de0 内容在列。**独立门侧评审链闭环。**
- **待第三关(CTO)议程**:①Dante 规格/授权商务书面确认(公开渠道核不到)②Audio Weaver 授权模式商务确认(唯一出处已 404)③中文生态专项补查是否开单 ④缺口清单 §4.2 优先级认可。CTO 过后本条补记。

## DEC-0006 DSP 主控选型 = ADSP-21569(2026-07-30,LOCKED,CTO 拍板)
- **决策**:主控 ADSP-21569(SHARC+ 单核 ≤1GHz;浮点硬件在手,项目锁**定点**口径——MCPS 效率考量非硬件限制)。工具链 CCES 2.12.1 + SAM BSP 已在手;codec ADAU1962A/1979/1963 TDM。G3 门:CTO 直接拍板(2026-07-30 本会话)= 签核。
- **依据数字**:FIRA 官方加速 3.07×(裕量 2.878×,禁引 3.13× 混 build 值)[L1/ITC R14 CLOSED];板上真实算力 **30-50 cyc/MAC 含 cache/中断**(禁 1cyc/MAC 理想记账,ITC 桌面/板上曾差 ~25×)[L1/ITC ds:234];实时硬底 48kHz/64帧=1,333,333 cyc/帧@1GHz [L1/ITC];单核非双核 [L1/ITC ds:153]。
- **来源等级**:L1——**跨项目转录口径:[L1/ITC同芯片板上实测,场景迁移待本项目复核]**。
- **数据出处**:`00_input/DSP_ADSP21569_infocard.md`;bulk 佐证材料待入 `knowledge_base/adsp21569/`。
- **可逆性**:不可逆(选型);开发板/工具链在手降低沉没成本;**量产采购冻结仍待本项目 D13 预算 L1 闭合**。
- **验证状态**:芯片级数据 ITC L1 已证;**本项目算法集(8ch AEC512ms+AFC16点+ANC+动态EQ+automixer 最坏同开)总算力预算未证——D13 按 30-50 cyc/MAC 口径重算 = 第一优先工单**。
- **风险声明**:①ITC 数据出自波束成形场景,算法构成不同,总量是否装得下未证;②FIRA 定点 ≤1024 taps:输出链 FIR(512-1024taps)用得上,**AEC 512ms 尾长(≈24576 taps 等效)不走时域 FIRA,须频域(MDF 类)核算,FIRA 加速不得计入 AEC 预算 [L3 推断,D13 复核]**;③定点口径下全链算法(尤其自适应类)定点化工作量计入排期;④单核无冗余,预算超限即砍功能或升家族(21567/66 同家族缓冲)。

## 假设台账(A1–A9)
| # | 假设 | 状态 |
|---|---|---|
| A1 | 交付边界=纯文档 | **作废**→DEC-0003.1(全周期) |
| A2 | DSP 平台未定、选型属本方案 | **确认**(DEC-0003.2) |
| A3 | 无 NN,传统算法 | **确认**(DEC-0003.3) |
| A4 | AoIP=私有 RTP | **作废**→DEC-0003.4(Dante/AES67) |
| A5 | 对标不逆向、协议不抄 | 有效;**待澄清**:与上游厂家是否有授权/OEM 关系(影响对标深度) |
| A6 | 上位机=Windows 桌面 | 待确认 [L3] |
| A7 | 12×12 仅扩展性说明 | 有效 [L3](← PRD §一.2"版本说明") |
| A8 | 硬件设计/认证不在本团队;bring-up/联调在 verification | 有效 [L3],随 DEC-0003.1 修订后口径 |
| A9 | PRD §二枚举顺序≠处理链序;按工程惯例重推(AEC 前置于降噪),architect 定稿 | **默认执行**(CTO 未异议,2026-07-30);链序定稿=LOCKED 项 |

## 外部输入台账(铁律六/C8 基线)
| 接收时间 | 来源 | 内容 | 入库日 | 超24h? | 备注 |
|---|---|---|---|---|---|
| 2026-07-30 | CTO | 产品需求书 PRD(会话粘贴全文) | 2026-07-30 | 否 | `00_input/PRD_CONFDSP.md`;F-01(BLOCKER)修复件,全库「← PRD §」引用基线 |
| 2026-07-30 | CTO | ADSP-21569 芯片信息卡+复制清单(会话粘贴) | 2026-07-30 | 否 | `00_input/DSP_ADSP21569_infocard.md`;选型 DEC-0006;bulk 资料**已复制核对**(2026-07-30 同日):bsp 93M/278文件 逐字节抽核一致+第2层 6 组全到位,溯源见 `platform_lessons/PROVENANCE.md`、清点见 `INVENTORY.md`;不含 a2b/installers(CTO 确认);bsp 二进制不入 git(清点单留痕);第3层=不复制件已关闭 |
| (待)| CTO | 上游厂家界面编辑软件 | — | — | 到手入库+对标工单(host-software/architect) |
