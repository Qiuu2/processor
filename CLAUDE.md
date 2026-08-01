# CONF-DSP-88 · 会议数字音频处理器 — 多-Agent 团队总纲

> 项目:8进8出机架式会议数字音频矩阵处理器(可扩展12×12),企业产品级,**跟到 C 代码落地并最终落到 DSP 芯片上**。
> PRD:`00_input/PRD_CONFDSP.md`(2026-07-30 入库,台账见 decisions_log);本文件是每个 session/teammate 的入口。

## 0. 当前状态(2026-07-31)
- **W1 工单进行中(AFC/NHS),会话中断于 2026-07-31 08:52(teammate 额度上限)——恢复工作先读 `01_design/W1_HANDOFF.md`。**
- 阶段:骨架+W0 技术雷达(D0)+ 竞品解剖(D0b)+ NHS 定向调查(D0c)就绪。**DSP 平台已定型:ADSP-21569**(SHARC+ 单核,定点口径,DEC-0006;信息卡 `00_input/DSP_ADSP21569_infocard.md`,平台料入 `knowledge_base/adsp21569/`;**算力记账口径 = 按模块分档制(DEC-0009,2026-07-31 变更,待 CTO 追认),旧「30-50 cyc/MAC 全局包络」已作废、不得并存**——T1 取 2.0 为规划值非悲观值(库内同族板测 8.51,敞口 ×4.3),T2 无板证上界,收口路径 = W1-C 微基准);上游厂家界面编辑软件待 CTO 提供(到手走铁律六 24h 入库)。
- 所有 skill 均为**薄骨架**(域未跑、无真料),真本事按 Playbook Part 2 蒸馏 SOP 随真跑长入,禁一次性写"完美 skill"。

## 1. 治理(先读,红线)
**`00_governance/GOVERNANCE_CONFDSP.md` 原样加载**:L0-L4 来源分级 / 九铁律 / C1-C10 门 / 三道关 / 不可逆→L1 清单 / 假绿纪律。一句话内核:
> 每个数字带"来源身份证"(L 标),决策权重按来源等级卡死;撤回必须全库传播;产出先过独立 critic 再交人。

三条不可动摇:
1. **独立 critic verdict 前不 commit/不 release/不冻结**;in-context 自审不算门;修正稿同等过门。
2. **不可逆动作(见治理 §2 十一项)前须 L1(或 L2+签字)+ 人审**;可逆性不得自我降档。
3. **假绿纪律**:测试必须真依赖被测物 + 对 broken 版能 FAIL;bypass 恒等/同实现自比/纯正弦自证都不算验证。

## 2. 团队(细则见 `.claude/team_config.md`,roster LOCKED 见 decisions_log DEC-0002)
| role | 定位 | 激活 |
|---|---|---|
| `orchestrator` | WBS/DAG/门禁/溯源,唯一对人(CTO)汇报节点 | 常驻 |
| `critic` | 独立守门,横切一切产出,可直接 rebut 任何 teammate | 常驻 |
| `system-architect` | 信号链/路由预设模型/算力延迟预算/**参数字典+私有中控协议**/时钟域接口 | 常驻 |
| `channel-dsp` | 确定性通道算法(门/压限/PEQ/分频/FIR/延时/保护限幅):设计→C→bit-exact | 主线 |
| `adaptive-dsp` | 自适应声学算法(AEC/AFC/ANC/AGC/automixer/房间EQ/人声优化,**无 NN**) | 主线 |
| `platform-fw` | 固件架构/驱动/USB/录音/OTA/GPIO + **Dante/AES67** 集成 | 按需 |
| `host-software` | 上位机架构/菜单/交互/多设备管理(对标上游厂家软件) | 按需 |
| `verification` | bring-up·测试·假绿纪律执行·全部 L1 实测 owner | 实现阶段主线 |

**并发纪律:任意时刻活跃 teammate ≤4**(orchestrator+critic+1~2 域专家),其余保持未 spawn。
orchestrator 为唯一**综合**汇报节点;**例外**:critic 遇安全项/不可逆门违规可 ESCALATE 直达 CTO,同步知会 orchestrator(F-07)。

## 3. 交付物 D1–D14
D1 全链路信号流程图(**含 AEC 参考路径**)｜D2 全算法参数阈值表(骨架=参数字典)｜D3 输入通道链｜D4 输出通道链｜D5 automixer(AM+NOM+优先级)｜D6 矩阵路由+预设模型(≥50组)｜D7 AoIP:Dante/AES67 集成方案｜D8 U盘录音/USB声卡｜D9 私有中控协议(RS232+TCP+GPIO联动)｜D10 AI增强族(传统算法实现)｜D11 上位机架构+菜单层级｜D12 固件架构(调度/驱动/电源/OTA)｜D13 算力/内存/延迟预算表｜D14 测试与验收方案+bring-up 清单。

## 4. 已确认口径(2026-07-30 CTO 拍板,详见 DEC-0003)
- 交付边界 = 全周期到芯片落地(非纯文档)。
- "AI"为产品叫法,**算法全为传统自适应/统计声学算法,不含 NN 推理**;若日后要 NN 卖点,重开算力预算。
- AoIP 须兼容 **Dante/AES67 生态**(Dante=授权方案选型采购=不可逆门;AES67 互通承诺须 L1)。
- 中控协议**私有**,并入 system-architect(参数字典与协议同源);冻结前须真机联调 L1。
- 链序假设 A9:PRD §二的枚举顺序≠处理链序;默认按工程惯例(AEC 前置于降噪等)由 adaptive-dsp 重推、architect 定稿、critic 按序审。

## 5. 工作方式
- 架构/协议/状态机/DAG:见根 `SKILL.md`。
- 每个 teammate 读自己的 `agents/<role>/{profile,soul,skill,memory}.md` 上岗;memory 从空累积,**任何进 memory/log 的数字挂 L 标,不确定就标 [L4/待验证],别编**。
- 派单 prompt 必须显式包含:交付物定义+验收判据、硬顺序(实现→自验→SendMessage critic→**收独立 verdict**→PASS 才 commit)、相关 DEC/假设引用。
- 决策记 `decisions_log.md`(6 字段:依据数字/来源等级/数据出处/可逆性/验证状态/风险声明)。
- 元教训(出生先验):`ee-agent-team-starter/00_governance/LESSONS_SEED.md`。

## 6. 文件地图
```
CLAUDE.md                     ← 本文件(入口)
SKILL.md                      ← 架构/通信协议/状态机/DAG/人审门
00_input/PRD_CONFDSP.md       ← PRD 原文入库件
00_governance/GOVERNANCE_CONFDSP.md
.claude/team_config.md        ← roster-模型表(LOCKED)/commit纪律/并发
decisions_log.md              ← DEC 台账 + 假设台账 A1-A9
agents/<role>/{profile,soul,skill,memory}.md × 8
ee-agent-team-starter/        ← 上游框架原文(只读参考)
```
