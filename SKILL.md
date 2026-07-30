---
name: confdsp-team-workflow
description: >
  CONF-DSP-88 会议数字音频处理器多-Agent 协作系统入口:
  四层+一横切架构、通信协议、任务状态机、项目 DAG、人审门与启动流程。
  治理底座见 00_governance/GOVERNANCE_CONFDSP.md,团队法见 .claude/team_config.md。
metadata:
  version: 0.1.0
  project: CONF-DSP-88
---

# CONF-DSP-88 Multi-Agent Workflow

## 1. 架构:四层 + 一横切
```
HUMAN CTO ──(关键节点审/不可逆签核/escalation)──┐
  CRITIC(横切,先审后发,可直接 rebut 任何角色)   │
  ORCHESTRATION: orchestrator(WBS/DAG/门禁;唯一对人汇报)
  DOMAINS: system-architect / channel-dsp / adaptive-dsp / platform-fw / host-software / verification
  EXECUTION: 工具层(C 工具链/MATLAB·numpy/音频分析/EDA 无;工具跑了≠跑对了,产出须回验)
```
核心原则:**所有产出先过独立 critic,再进下一环节或交 CTO。**

## 2. 通信(Claude Code Agent Teams,隐式团队)
- spawn:`Agent(name=<role>, model=按 team_config)`;寻址:`SendMessage({to: <role>})`。
- peer-challenge ON:teammate 直连互怼;critic BLOCKER 即时冻结工件,不经 lead。
- 消息最少字段:任务ID / 类型(派单|状态|评审|escalation)/ 引用的 DEC·假设编号 / 数字一律带 L 标。
- critic verdict 头强制:`reviewer: critic @ <精确模型ID> / <日期>`,无标退回。

## 3. 任务状态机(精简版)
```
PENDING → ASSIGNED → IN_PROGRESS → REVIEW(独立critic) → PASSED → COMPLETED(→commit/归档)
                          ↑              └ FAILED ────────┘(打回修正,修正稿同等过门)
任意态 → ESCALATED(安全/不可逆门/3次评审不过/跨域僵局 → CTO)
```
- REVIEW 只能由独立 critic 出 verdict;PASSED 且涉不可逆清单项 → 加 HUMAN_GATE(CTO 签核)。

## 4. 项目 DAG(v1.0,随 sprint 滚动维护)
```
PRD/CTO输入 ─→ system-architect
  ├─ D1 信号流(含AEC参考路径)+D13 预算+参数字典 ─→ channel-dsp(D3det/D4)
  │                                               └→ adaptive-dsp(D3adp/D5/D10)
  ├─ 参数字典 ─→ D9 协议(architect 自持) ─→ host-software(D11,协议第一客户端)
  ├─ 路由/预设模型(D6) ─→ host-software + platform-fw(预设持久化)
  └─ 资源预算/时钟域接口 ─→ platform-fw(D7 Dante/AES67, D8, D12)
channel-dsp+adaptive-dsp ─→ D2 参数阈值表(汇总入参数字典) ─→ D9/D11 同步
platform-fw ─→ 传输层/设备发现/OTA接口 ─→ host-software
全部 ─→ verification(D14 验收判据+bring-up) ─→ orchestrator ─→ [人审门]
critic 横切:每个交付物 REVIEW 态必经;不可逆清单项另加 CTO 门
外部输入(DSP候选资料/上游厂家软件)→ 铁律六 24h 入库 → 选型评估/对标工单
```
关键耦合:**参数字典是单点事实源**(DSP 模块↔协议↔UI↔预设文件四方引用同一张表)。

## 5. 人审门(CTO Gate)
| Gate | 触发 | 内容 |
|---|---|---|
| G1 计划批准 | orchestrator 出 WBS+DAG,critic 过 | 整体计划/优先级 |
| G2 架构评审 | D1/D13/参数字典 v1 过 critic | 链路拓扑、链序(A9)、预算口径 |
| G3 选型批准 | DSP 候选评估 + Dante 方案评估完成 | **不可逆:L2+风险声明+签字 起步,量产冻结待 L1** |
| G4 协议/格式冻结 | D9 真机联调 L1、预设格式迁移验证、USB VID/PID 与描述符定稿 | **不可逆:签核后对外发布** |
| G5 板级/发布放行 | bring-up 完成、指标 L1、OTA 断电实测、AES67 第三方设备互通 L1 | **不可逆:量产烧录/对外承诺(含 AES67 兼容声明)** |

## 6. 启动序列
1. CTO 提供输入(已完成:PRD+口径确认 DEC-0003;待:DSP 资料、上游软件)。
2. orchestrator 建 WBS+DAG → critic 审 → G1。
3. 首批工单(建议):W1 system-architect 出 D1+D13 草案+参数字典 schema(全 L3/L4 标注,等平台资料);W2 adaptive-dsp 出链序提案(A9)供 G2;W3 DSP 资料到 → 选型评估(C9 口径分离)。
4. 各 teammate 上岗序:读 CLAUDE.md → 治理 → 本文件 → 自己四件套;memory 从空累积。

## 7. 度量(诚实起步,不虚构 SLA)
跟踪:评审轮次/交付物、BLOCKER 密度、假绿捕获数、L 标覆盖率、外部输入入库时延。数据从真实 sprint 累积,不预设目标值。
