---
name: itc-enterprise-workflow
description: >
  ITC (In-The-Can) 企业级多Agent协作系统入口技能。
  面向音频硬件研发企业的四层+一横切架构，涵盖声学、DSP、硬件、结构、测试五大工程领域，
  并含专利文献与项目文档两个支持型领域Agent，由评审Agent横切所有领域进行质量守门。
  本技能定义系统整体架构、通信协议、
  状态机、依赖图规范及启动流程。
metadata:
  version: 1.0.1
  author: ITC Architecture Team
  category: enterprise-workflow
  industry: audio-hardware
---

# ITC Enterprise Multi-Agent Workflow

## 1. System Architecture: 四层 + 一横切

```
┌─────────────────────────────────────────────────────────────┐
│                    HUMAN CTO / 总工程师                        │
│              （关键节点Review · 最终决策 · Escalation）          │
└──────────────┬──────────────────────────────┬───────────────┘
               │ 实线=任务调度   虚线=评审反馈      │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ◄─────────── CROSS-CUTTING LAYER ───────────►             │
│                  CRITIC AGENT 评审Agent                       │
│         （质量守门员 · 对抗式提问 · 拦截低级错误 · 先审后发）      │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┬───────────────▼───────────────┐
│      ORCHESTRATION LAYER    │      DOMAINS LAYER            │
│     Project Manager Agent   │  ┌──────┐ ┌──────┐ ┌──────┐  │
│    （Scrum Master + Tech    │  │声学Agent│ │DSP Agent│ │硬件Agent│  │
│      Lead · 状态机 · 调度）   │  └──────┘ └──────┘ └──────┘  │
│                             │  ┌──────┐ ┌──────┐ ┌──────┐  │
│                             │  │结构Agent│ │测试Agent│ │专利Agent│  │
│                             │  └──────┘ └──────┘ └──────┘  │
│                             │  ┌──────┐                    │
│                             │  │文档Agent│                    │
│                             │  └──────┘                    │
└──────────────┬──────────────┴───────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────────────────────▼───────────────┐
│                    EXECUTION LAYER                           │
│    工具调用 · 代码执行 · 文档生成 · 数据分析 · 仿真计算            │
│              （Python · CAD · SPICE · MATLAB等）              │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 Layer Definitions

| Layer | Name | Responsibility | Key Agents |
|-------|------|----------------|------------|
| L1 | **Human Layer** | 总工程师(CTO)决策、关键review、escalation处理 | Human CTO |
| L2 | **Cross-Cutting Layer** | 质量守门，所有产出先过critic再交付 | Critic Agent |
| L3 | **Orchestration Layer** | 项目总调度、状态机管理、DAG维护、任务派发 | Project Manager Agent |
| L3 | **Domains Layer** | 领域专业工作：声学/DSP/硬件/结构/测试 + 专利文献/项目文档 | 7 Domain Agents |
| L4 | **Execution Layer** | 工具执行、代码运行、数据计算 | Tool Callers |

### 1.2 Cross-Cutting Principle

> **核心原则：所有Agent产出必须先经过Critic Agent评审，才能进入下一环节或提交人类Review。**

```
Domain Agent ──产出──► Critic Agent ──通过──► Project Manager ──► 下一环节/人类Review
                           │
                           └── 不通过 ──► 反馈修正 ──► Domain Agent（循环直到通过）
```

---

## 2. Communication Protocol

### 2.1 Line Types

| Line Style | Meaning | Direction | Trigger |
|------------|---------|-----------|---------|
| **实线 (───)** | 任务调度 | PM → Domain Agent | 任务分配、状态变更、优先级调整 |
| **虚线 (- - -)** | 评审反馈 | Critic → Domain Agent / PM | 评审意见、质量拦截、修正要求 |
| **粗线 (═══)** | 人类介入 | Human ↔ PM / Critic | 关键决策、escalation、最终审批 |
| **点线 (···)** | 状态同步 | Agent ↔ PM | 进度汇报、状态更新、阻塞报告 |

### 2.2 Message Format

All inter-agent messages follow this envelope format:

```yaml
message:
  id: "MSG-{timestamp}-{seq}"
  type: "TASK_ASSIGN | STATUS_UPDATE | REVIEW_FEEDBACK | ESCALATION | DECISION_REQUEST"
  from: "agent-name"
  to: "agent-name | broadcast"
  timestamp: "ISO8601"
  payload: {}
  priority: "P0_CRITICAL | P1_HIGH | P2_NORMAL | P3_LOW"
  trace_id: "TRACE-{project_id}-{workflow_id}"  # for distributed tracing
```

---

## 3. Task State Machine

```
                    ┌─────────────┐
                    │   PENDING   │◄────────────┐
                    │  （待分配）  │             │
                    └──────┬──────┘             │
                           │ PM assigns         │
                           ▼                    │
                    ┌─────────────┐             │
                    │  ASSIGNED   │             │
                    │  （已分配）  │             │
                    └──────┬──────┘             │
                           │ Agent accepts      │
                           ▼                    │
              ┌───►┌─────────────┐              │
              │    │ IN_PROGRESS │              │
         reject  │  （执行中）   │              │
              │    └──────┬──────┘              │
              │           │ Agent submits        │
              │           ▼                      │
              │    ┌─────────────┐    ┌─────────┴─────────┐
              │    │    REVIEW   │───►│   AUTO_REJECTED   │
              └───┐│  （评审中）  │    │  （自动打回PENDING） │
                  │ └──────┬──────┘    └───────────────────┘
                  │        │ Critic reviews
                  │        ▼
                  │ ┌─────────────┬─────────────┐
                  │ │   PASSED    │   FAILED    │
                  └─┤  （已通过）  │  （未通过）  │
                    └──────┬──────┘──────┬──────┘
                           │             │
                           ▼             ▼
                    ┌─────────────┐    (loop back
                    │   COMPLETED │     to PENDING)
                    │   （已完成） │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐     ┌──────────┐     ┌──────────┐
   │  MERGED  │     │ ARCHIVED │     │ REJECTED │
   │（已合并）  │     │（已归档）  │     │（已否决）  │
   └──────────┘     └──────────┘     └──────────┘
```

### 3.1 State Transitions

| From → To | Trigger | Actor | SLA |
|-----------|---------|-------|-----|
| PENDING → ASSIGNED | PM创建任务并指派 | Project Manager | 立即 |
| ASSIGNED → IN_PROGRESS | Domain Agent接受任务 | Domain Agent | 1h内 |
| IN_PROGRESS → REVIEW | 提交产出物 | Domain Agent | 按任务SLA |
| REVIEW → PASSED | Critic评审通过 | Critic Agent | 2h内 |
| REVIEW → FAILED | Critic发现BLOCKER/MAJOR | Critic Agent | 2h内 |
| REVIEW → AUTO_REJECTED | 超时未审/Agent放弃 | Auto-timeout | 24h |
| PASSED → COMPLETED | PM确认完成 | Project Manager | 1h内 |
| PASSED → HUMAN_REVIEW | 需要人类决策 | Project Manager | 按CTO SLA |
| FAILED → PENDING | 打回修正 | Critic Agent | 立即 |
| COMPLETED → MERGED | 合并到主线 | Project Manager | 按流程 |
| COMPLETED → ARCHIVED | 归档记录 | Project Manager | 定期 |
| * → ESCALATED | P0问题/阻塞 > 4h | Any Agent | 立即 |

---

## 4. Dependency Graph (DAG) Specification

### 4.1 DAG Structure

All tasks form a Directed Acyclic Graph. Cycles are forbidden and validated at creation time.

```yaml
dependency_graph:
  nodes:
    - task_id: "TASK-001"
      name: "Acoustic Cavity Simulation"
      domain: "acoustics"
      estimated_hours: 8
      priority: "P1_HIGH"
      
    - task_id: "TASK-002"
      name: "DSP Algorithm Design"
      domain: "dsp"
      estimated_hours: 12
      priority: "P1_HIGH"
      
    - task_id: "TASK-003"
      name: "PCB Layout"
      domain: "hardware"
      estimated_hours: 6
      priority: "P2_NORMAL"
      
    - task_id: "TASK-004"
      name: "Structural Enclosure Design"
      domain: "structure"
      estimated_hours: 10
      priority: "P1_HIGH"
      
    - task_id: "TASK-005"
      name: "Integration Test"
      domain: "test"
      estimated_hours: 16
      priority: "P0_CRITICAL"

  edges:
    - from: "TASK-001"    # Acoustic → DSP
      to: "TASK-002"
      type: "data_dependency"
      description: "DSP needs acoustic target curve"
      
    - from: "TASK-002"    # DSP → Hardware
      to: "TASK-003"
      type: "resource_dependency"
      description: "PCB needs DSP chip pinout"
      
    - from: "TASK-001"    # Acoustic → Structure
      to: "TASK-004"
      type: "spatial_dependency"
      description: "Enclosure needs cavity dimensions"
      
    - from: "TASK-003"    # Hardware → Test
      to: "TASK-005"
      type: "execution_dependency"
      description: "Test needs PCB prototype"
      
    - from: "TASK-004"    # Structure → Test
      to: "TASK-005"
      type: "execution_dependency"
      description: "Test needs enclosure prototype"
```

### 4.2 Dependency Types

| Type | Description | Example |
|------|-------------|---------|
| `data_dependency` | Task B needs data from Task A | Acoustic sim → DSP design |
| `resource_dependency` | Task B needs resources from Task A | DSP spec → PCB layout |
| `spatial_dependency` | Physical space/design dependency | Cavity → Enclosure |
| `execution_dependency` | Task B can only execute after A | PCB fab → Integration test |
| `review_dependency` | Task B needs A's review passed | All → Critic review |

### 4.3 Critical Path Calculation

PM Agent computes critical path after each state change:

```python
def compute_critical_path(dag) -> List[Task]:
    """Return the longest path from any root to any leaf."""
    for task in dag.topological_sort():
        task.earliest_start = max(
            dep.earliest_finish for dep in task.dependencies,
            default=0
        )
        task.earliest_finish = task.earliest_start + task.estimated_hours
    
    critical_path = max(dag.paths(), key=lambda p: p.total_duration)
    return critical_path
```

---

## 5. Workflow Initialization

### 5.1 Startup Sequence

```
Step 1: Human CTO provides project brief → Project Manager
        └── Input: 产品需求书(PRD)、约束条件、里程碑日期

Step 2: Project Manager creates WBS + DAG
        └── Decomposes PRD into tasks across 5 domains
        └── Identifies dependencies between tasks
        └── Assigns priorities and estimates

Step 3: Project Manager submits plan → Critic Agent
        └── Critic reviews: WBS完整性、依赖合理性、风险评估充分性
        └── If FAILED → PM revises plan
        └── If PASSED → proceed

Step 4: Critic review passed → Human CTO Review
        └── CTO approves/rejects the overall plan
        └── If approved → workflow officially starts

Step 5: Project Manager dispatches tasks per DAG
        └── Root tasks (no dependencies) → assigned first
        └── Subsequent tasks → assigned when dependencies COMPLETED
```

### 5.2 Project Manager Entry Point

```yaml
workflow_start:
  trigger: "Human CTO submits PRD"
  entry_agent: "project-manager"
  entry_skill: "agents/project-manager/skill.md"
  inputs:
    - "prd_document.md"
    - "constraints.yaml"    # budget, timeline, resources
    - "milestones.json"     # key dates
  outputs:
    - "project_plan.yaml"   # WBS + DAG + assignments
    - "risk_register.md"    # identified risks
    - "schedule.json"       # Gantt-style timeline
```

---

## 6. Agent Directory

```
itc-enterprise-workflow/
├── SKILL.md                              # ← This file (入口)
├── agents/
│   ├── project-manager/                  # 项目总调度
│   │   ├── profile.md                    #   身份定义
│   │   ├── soul.md                       #   核心驱动力与价值观
│   │   ├── skill.md                      #   技能与工作流
│   │   └── memory.md                     #   可学习记忆
│   │
│   ├── critic/                           # 评审Agent (横切)
│   │   ├── profile.md                    #   身份定义
│   │   ├── soul.md                       #   核心驱动力与价值观
│   │   ├── skill.md                      #   评审技能与流程
│   │   └── memory.md                     #   评审知识库
│   │
│   ├── acoustic-simulation/             # 声学仿真领域Agent
│   │   ├── profile.md, soul.md, skill.md, memory.md
│   │
│   ├── dsp-algorithm/                    # DSP算法领域Agent
│   │   ├── profile.md, soul.md, skill.md, memory.md
│   │
│   ├── hardware-design/                  # 硬件设计领域Agent
│   │   ├── profile.md, soul.md, skill.md, memory.md
│   │
│   ├── structure/                        # 结构领域Agent
│   │   ├── profile.md, soul.md, skill.md, memory.md
│   │
│   ├── testing/                          # 测试领域Agent
│   │   ├── profile.md, soul.md, skill.md, memory.md
│   │
│   ├── literature-patent/                # 专利文献领域Agent
│   │   ├── profile.md, soul.md, skill.md, memory.md
│   │
│   └── project-document/                 # 项目文档领域Agent
│       ├── profile.md, soul.md, skill.md, memory.md
```

### 6.1 Agent Roles Summary

| Agent | Directory | Role | Layer | Reports To |
|-------|-----------|------|-------|------------|
| Project Manager | `project-manager` | Scrum Master + Tech Lead | Orchestration | Human CTO |
| Critic | `critic` | Quality Gatekeeper | Cross-Cutting | Human CTO (escalation) |
| Acoustics | `acoustic-simulation` | Acoustic engineer | Domains | PM + Critic |
| DSP | `dsp-algorithm` | DSP algorithm engineer | Domains | PM + Critic |
| Hardware | `hardware-design` | PCB/FW engineer | Domains | PM + Critic |
| Structure | `structure` | Mechanical engineer | Domains | PM + Critic |
| Test | `testing` | V&V engineer | Domains | PM + Critic |
| Literature/Patent | `literature-patent` | Patent & literature researcher | Domains | PM + Critic |
| Project Document | `project-document` | Documentation specialist | Domains | PM + Critic |

---

## 7. Human CTO Intervention Points

### 7.1 Mandatory Review Gates

```
Gate 1: Project Plan Approval
  └── Trigger: PM完成WBS+DAG，Critic评审通过
  └── Action: CTO批准/修改/否决整体计划
  └── SLA: 48h

Gate 2: Architecture Review
  └── Trigger: 各领域完成架构设计，Critic评审通过
  └── Action: CTO评审跨领域架构一致性
  └── SLA: 24h

Gate 3: Prototype Go/No-Go
  └── Trigger: 首轮原型完成，集成测试结果就绪
  └── Action: CTO决定是否进入下一轮迭代
  └── SLA: 24h

Gate 4: Final Design Approval
  └── Trigger: 所有设计完成，Critic最终评审通过
  └── Action: CTO批准进入量产
  └── SLA: 72h
```

### 7.2 Escalation Triggers

| Condition | Escalation Path | Response Time |
|-----------|----------------|---------------|
| BLOCKER issue > 4h unresolved | Agent → PM → CTO | CTO: 2h |
| Cross-domain conflict | PM + Critic → CTO | CTO: 4h |
| Budget/timeline overrun risk | PM → CTO | CTO: 8h |
| Safety/regulatory concern | Any → Critic → CTO (immediate) | CTO: 1h |
| Quality gate repeated failure (>3x) | Critic → CTO | CTO: 4h |

---

## 8. Critic Agent Cross-Cutting Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Acoustics  │    │     DSP     │    │   Hardware  │    │  Structure  │
│   Agent     │    │   Agent     │    │   Agent     │    │   Agent     │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       └──────────────────┼──────────────────┼──────────────────┘
                          ▼                  ▼
                   ┌─────────────┐
                   │    CRITIC   │◄────────────────────────────────┐
                   │    AGENT    │   （所有产出必须经过此关卡）        │
                   │             │                                 │
                   │ • 对抗式提问  │                                 │
                   │ • 假设检测    │◄────────────────────────────────┘
                   │ • 边界条件追问 │   （从Execution Layer获取验证数据）
                   │ • 标准对照    │
                   └──────┬──────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │ PASSED │  │ FAILED │  │ ESCAL  │
         └───┬────┘  └───┬────┘  └───┬────┘
             │           │           │
             ▼           ▼           ▼
          下一环节      打回修正      上报CTO
```

### 8.1 Critic Review Protocol

1. **Receive**: Critic receives deliverable from Domain Agent via PM
2. **Screen**: Quick scan for obvious errors (format, completeness)
3. **Deep Review**: Domain-specific checklist + adversarial questioning
4. **Cross-Domain Check**: Verify consistency with other domains' outputs
5. **Grade**: Assign severity (BLOCKER/MAJOR/MINOR/INFO)
6. **Report**: Send review report to PM + Domain Agent
7. **Track**: Record in memory for pattern learning

---

## 9. Execution Layer Integration

### 9.1 Available Tool Categories

| Category | Tools | Used By |
|----------|-------|---------|
| **Simulation** | COMSOL (声学), SPICE (电路), MATLAB (DSP) | Acoustics, DSP, Hardware |
| **CAD** | SolidWorks, AutoCAD, Altium Designer | Structure, Hardware |
| **Analysis** | Python (NumPy/SciPy), Jupyter | All domains |
| **Testing** | Audio Precision, Klippel, SoundCheck | Test |
| **Documentation** | Markdown, LaTeX, Draw.io | All domains |
| **PM** | JIRA-style task tracking, Gantt charts | Project Manager |

### 9.2 Tool Call Pattern

```yaml
tool_execution:
  agent: "{domain_agent}"
  tool: "{tool_name}"
  inputs: "{structured_params}"
  outputs: "{structured_results}"
  validation:
    - "output_format_check"
    - "value_range_check"
    - "consistency_with_prev_results"
  review_required: true  # always true → goes to Critic
```

---

## 10. Metrics & Observability

### 10.1 System Health Metrics

```yaml
metrics:
  throughput:
    - tasks_completed_per_day
    - review_cycle_time_avg  # submit → pass time
    - critical_path_adherence  # actual vs planned
  
  quality:
    - critic_findings_per_deliverable
    - false_positive_rate
    - revision_cycles_avg  # how many tries to pass critic
  
  health:
    - blocked_tasks_count
    - escalation_frequency
    - sla_breach_rate
```

### 10.2 Dashboard

PM Agent maintains a real-time project dashboard:

```
┌─────────────────────────────────────────────────────────────────┐
│ ITC Project Dashboard  [Project: ITC-Pro-2024-Q2]               │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│ Progress     │ Quality      │ Schedule     │ Risks              │
│ ██████░░ 67% │ Cycles: 1.8  │ On Track     │ ⚠ 2 Medium        │
│ 8/12 tasks   │ Issues: 23   │ CPI: 0.98    │ ✖ 0 Critical      │
│ 2 in review  │ FP rate: 5%  │ EAC: 45 days │ ⚡ 1 Escalation   │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial architecture definition |
| 1.0.1 | 2026-05-27 | 文档对齐磁盘实际：领域Agent目录改名（acoustic-simulation/dsp-algorithm/hardware-design/testing），补登 literature-patent 与 project-document 两个Agent；Domain Agents 计数 5→7 |

---

*ITC Enterprise Multi-Agent System v1.0.1 — Four Layers + One Cross-Cut Architecture*
