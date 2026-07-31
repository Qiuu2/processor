# CONF-DSP-88 Agent Team — Roster & Model Tiering (LOCKED)

> 权威团队配置。任何 teammate spawn 必须对照本表;改任何角色的模型 = 改本表 + decisions_log 记一行(旧→新/日期/原因/谁批),禁静默改。
> 环境:Claude Code CLI ≥2.1.220,Agent Teams 实验特性已启用(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`,settings.json env 块)。
> **v2.1.178 起为隐式团队**:无 TeamCreate/TeamDelete;spawn 时用 `Agent` 工具 `name` 参数命名,即可被 `SendMessage({to: name})` 寻址。teammate **不跨会话持久**(/resume 后须重 spawn + 用四件套/handoff 重新交底;任务清单在 `~/.claude/tasks/` 留存)。

## 模型解析表(alias → 精确 ID,本环境)
| alias | 精确模型 ID | 代际 |
|---|---|---|
| `fable` | `claude-fable-5` | Fable 5(session 运行 `claude-fable-5[1m]` 1M 上下文) |
| `opus` | `claude-opus-5` | Opus 5 |
| `sonnet` | `claude-sonnet-5` | Sonnet 5 |
| `haiku` | `claude-haiku-4-5-20251001` | Haiku 4.5 |

新 spawn 默认**省略 model**(继承 session = Fable 5);按下表显式降档以控成本。

## Locked roster(role → model → 激活)
| role | model | 激活 | 说明 |
|---|---|---|---|
| orchestrator(lead) | session(`claude-fable-5[1m]`) | 常驻 | 唯一对 CTO 汇报节点 |
| critic | `fable` | 常驻 | 守门深度最重要,不降档 |
| system-architect | `fable` | 常驻 | 参数字典/预算/协议 单一事实源 |
| channel-dsp | `opus` | 主线 | 确定性算法,设计→C→bit-exact |
| adaptive-dsp | `fable` | 主线 | AEC/AFC/automixer 算法深度最重 |
| platform-fw | `sonnet` | 按需 | Dante/AES67 进实测阶段时评估拆出网络角色并升档 |
| host-software | `sonnet` | 按需 | — |
| verification | `sonnet` | 实现阶段主线 | 板级 bring-up 阶段临时升 `opus`(CTO 批) |

**并发纪律(HARD)**:任意时刻活跃 teammate ≤4。依据:MAST 实证(3-4 并发后收益递减)+ ITC 实战形态。超出需 CTO 批准并留痕。

## Peer-challenge protocol(ON)
- teammate 之间可直接 `SendMessage` 互发;critic 可**不经 lead** 直接 rebut 任何 teammate 的产出,BLOCKER 即时冻结该工件。
- lead 只仲裁:(a) teammate 间 BLOCKER 僵局;(b) 触发 CTO 门(不可逆清单/预算/ESCALATED)的事项。
- lead 仍是唯一对 CTO 汇报口(综合汇报),但不做 dsp↔critic 的强制中转。**例外(F-07)**:critic 遇安全项/不可逆门违规,ESCALATE 直达 CTO,同步知会 lead。

## Critic instance rotation(2026-07-30,F-02 修复——调和「三道关全新上下文」与「roster 常驻」)
- **可复用同一 critic 实例**:同一工单的评审链(初审→修正稿复审→…),保 findings 逐条闭环。
- **必须 spawn 全新实例**:①新工单/新交付物首审 ②skill 蒸馏全量核(SOP 第 6 步)③同一交付物第 3 次 FAILED 后的下一轮 ④critic 参与过该产出生成(自审禁令)⑤指定实例失联(Fallback 条款,不得以 in-context skill 替代)。
- 与 `agents/critic/profile.md` 互引;违反 = 流程偏差,原样上报 CTO。

## Interface contract discipline(2026-07-31,F-16/F5 修复 —— 缘起 W1 A/B 合同版本竞态)
> **缘起**:W1-A/W1-B 两份承重设计件在运行点(16ms vs 42.7ms)、检测 tap(入口 vs 出口)、精度判据(BW/4 vs BW/10)三点**完全相反**,而双方各自都以为"已对齐"。根因=接口合同无版本控制 + **双文档各自转述规范值**。双方自验均未发现,由 lead 例行核查 + architect 独立报告双向抓获。**物证**:W1-A 文内"≈21 Mop/s 两轨吻合"经 critic 定位实为 **42.7ms 运行点的数**被贴进 B3(29.1 Mop/s)默认表——竞态在单一文档内部留下的指纹。
> **机制强度评估(critic-w1 裁定)**:仅加版本号 = **必要但不充分**——即便带版本号,单份文档内部仍可能混入异版本数字。故立以下四条。

1. **接口合同独立成文件**:`01_design/contracts/<工单>_<双方>_interface_vX.Y.md`,**owner = 提供方**,是该接口的**唯一权威源**;文件头带 `合同版本 vX.Y / 生成时间 / 双方确认状态`。
2. **两侧文档只引版本号,禁止转述规范值**(转述=本次事故根因)。需要具体数值时引用合同文件路径+版本号+条款号,不得复制数字进本文。
3. **合同变更记台账**(旧→新 / 日期 / 双方确认),对齐治理 §7 变更审计。
4. **谈判结论先落合同文件、后改各自文档**;**禁止凭会话记忆各自更新**——「**共识只存在于消息流里 = 没有共识**」(措辞取自 adaptive-dsp 自诊)。
5. **收方义务**:合同条款与自己论证冲突时,**先据物理争一轮再接受**;"替对方结论找合理化"比单纯接受更危险——它会生成看似有据的文本,使下游(含 critic)更难发现问题。
6. **critic 必查项增补**:凡 ≥2 份文档共享接口,**契约段逐条对表**。

## Commit discipline(HARD RULE,继承 ITC F5-A/F7 教训)
- **独立 critic verdict 前不得 commit。** teammate 自己的对抗式自审不满足门禁——只有独立 critic teammate 出具的、带 `reviewer: critic @ <精确模型ID> / <日期>` 头的 verdict 才能放行。
- **硬顺序**:实现 → 桌面自验 → SendMessage critic → **收独立 verdict** → PASS 才 commit / BLOCKER·MAJOR 修复后重新过门。lead 在**每份派单 prompt**显式写入此顺序;先 commit 后 verdict = 流程偏差,原样上报 CTO,不得自行消化。
- **Fallback**:指定 critic 实例失联时,teammate 不得以"自己上下文里调 critic skill"充当独立门——停在未 commit 状态、回报 lead,由 lead spawn 全新 critic 补门。
- 唯一豁免:critic 明文预先豁免的纯笔误级修正。

## Three-gate verification(POLICY §4B 原样继承)
每轮产出(含修正稿):① 自动 verify/自验 = 初筛 NOT 门 → ② 独立 critic = 唯一放行门 → ③ CTO 常识审 = 兜底。不得假设"修过即对"。

## Change control
- 本表任何变更(模型/角色/并发上限)= 编辑本表 + decisions_log 一行(旧→新、日期、原因、批准人)。
- critic verdict 无 reviewer 头标记 → 退回重发(审计链,对齐 C5)。
