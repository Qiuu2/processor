---
name: project-manager-skill
description: >
  Project Manager Agent的技能配置文件。
  包含工作分解(WBS)方法、依赖图(DAG)构建与维护、任务状态机管理、
  调度算法、风险识别与escalation机制、与人类CTO的汇报格式、
  与Critic Agent的交互协议、与各领域Agent的任务派发接口。
version: 1.0.0
author: ITC Architecture Team
---

# Project Manager Agent — Skill

## 1. Work Breakdown Structure (WBS)

### 1.1 WBS Decomposition Method

```yaml
wbs_method:
  levels:
    L0: "Project"                    # 整个项目
    L1: "Domain Phase"               # 领域阶段 (声学/DSP/硬件/结构/测试)
    L2: "Work Package"               # 工作包 (可交付成果级别)
    L3: "Task"                       # 任务 (分配给单个Agent)
    L4: "Sub-task"                   # 子任务 (可选，Agent自行分解)
  
  decomposition_rules:
    - "每个L3任务分配给唯一一个Domain Agent"
    - "每个L3任务有明确的交付物和验收标准"
    - "每个L3任务预估工时 ≤ 16小时（超过需拆分）"
    - "每个L3任务有唯一的任务ID：TASK-{project}-{seq}"
    - "任务依赖必须在DAG中明确定义"
```

### 1.2 WBS Template for ITC Audio Hardware Project

```yaml
wbs_template:
  L1_acoustics:
    name: "声学设计与验证"
    L2_work_packages:
      - wp_id: "AC-WP01"
        name: "声学腔体设计"
        L3_tasks:
          - task: "腔体几何建模"
            agent: "acoustics-agent"
            deliverable: "3D腔体模型 + 体积/表面积报告"
            est_hours: 6
          - task: "FEM声学仿真"
            agent: "acoustics-agent"
            deliverable: "频响曲线仿真结果 + 收敛报告"
            est_hours: 12
          - task: "目标曲线定义"
            agent: "acoustics-agent"
            deliverable: "目标频响曲线文档 + 容差规格"
            est_hours: 4
            
      - wp_id: "AC-WP02"
        name: "声学测量与验证"
        L3_tasks:
          - task: "消声室测量方案"
            agent: "acoustics-agent"
            deliverable: "测量方案文档 + 设备清单"
            est_hours: 4
          - task: "原型声学测量"
            agent: "test-agent"
            deliverable: "测量数据报告 + 与仿真对比分析"
            est_hours: 8
          - task: "声学问题根因分析"
            agent: "acoustics-agent"
            deliverable: "问题清单 + 改进建议"
            est_hours: 6
            
  L1_dsp:
    name: "DSP算法开发"
    L2_work_packages:
      - wp_id: "DSP-WP01"
        name: "信号处理链路设计"
        L3_tasks:
          - task: "滤波器组设计"
            agent: "dsp-agent"
            deliverable: "滤波器系数 + 频率响应图"
            est_hours: 8
          - task: "动态范围处理"
            agent: "dsp-agent"
            deliverable: "压缩/限幅算法 + 参数表"
            est_hours: 6
          - task: "EQ曲线实现"
            agent: "dsp-agent"
            deliverable: "EQ参数 + 目标曲线匹配度报告"
            est_hours: 6
            
      - wp_id: "DSP-WP02"
        name: "实时性能优化"
        L3_tasks:
          - task: "MIPS预算分配"
            agent: "dsp-agent"
            deliverable: "各模块MIPS占用表 + 预算对比"
            est_hours: 4
          - task: "定点化实现"
            agent: "dsp-agent"
            deliverable: "定点化后的音频样本 + 精度报告"
            est_hours: 10
          - task: "延迟优化"
            agent: "dsp-agent"
            deliverable: "端到端延迟测量报告"
            est_hours: 6
            
  L1_hardware:
    name: "硬件设计与实现"
    L2_work_packages:
      - wp_id: "HW-WP01"
        name: "原理图设计"
        L3_tasks:
          - task: "器件选型"
            agent: "hardware-agent"
            deliverable: "BOM清单 + 选型依据文档"
            est_hours: 6
          - task: "放大电路设计"
            agent: "hardware-agent"
            deliverable: "原理图 + 仿真结果"
            est_hours: 8
          - task: "电源设计"
            agent: "hardware-agent"
            deliverable: "电源树 + 效率计算"
            est_hours: 6
            
      - wp_id: "HW-WP02"
        name: "PCB实现"
        L3_tasks:
          - task: "布局设计"
            agent: "hardware-agent"
            deliverable: "PCB布局图 + 关键信号长度报告"
            est_hours: 10
          - task: "热仿真验证"
            agent: "hardware-agent"
            deliverable: "温度分布图 + 热点分析报告"
            est_hours: 6
          - task: "DFM检查"
            agent: "hardware-agent"
            deliverable: "DFM报告 + 制造商确认"
            est_hours: 4
            
  L1_structure:
    name: "结构设计与开模"
    L2_work_packages:
      - wp_id: "ST-WP01"
        name: "外壳设计"
        L3_tasks:
          - task: "ID可行性评估"
            agent: "structure-agent"
            deliverable: "ID评估报告 + 修改建议"
            est_hours: 4
          - task: "3D结构设计"
            agent: "structure-agent"
            deliverable: "3D模型 + 壁厚分析报告"
            est_hours: 10
          - task: "声学结构协同"
            agent: "structure-agent"
            deliverable: "腔体配合尺寸 + 密封方案"
            est_hours: 6
            
      - wp_id: "ST-WP02"
        name: "模具与试产"
        L3_tasks:
          - task: "模具设计评审"
            agent: "structure-agent"
            deliverable: "模具评审报告 + 修改清单"
            est_hours: 6
          - task: "试产跟进"
            agent: "structure-agent"
            deliverable: "试产问题清单 + 解决方案"
            est_hours: 8
            
  L1_test:
    name: "测试验证"
    L2_work_packages:
      - wp_id: "TE-WP01"
        name: "测试方案"
        L3_tasks:
          - task: "测试计划编制"
            agent: "test-agent"
            deliverable: "测试计划文档 + 覆盖率矩阵"
            est_hours: 6
          - task: "自动化测试开发"
            agent: "test-agent"
            deliverable: "测试脚本 + 用例库"
            est_hours: 12
          - task: "环境搭建"
            agent: "test-agent"
            deliverable: "测试环境配置报告"
            est_hours: 4
            
      - wp_id: "TE-WP02"
        name: "验证执行"
        L3_tasks:
          - task: "功能测试"
            agent: "test-agent"
            deliverable: "测试报告 + 缺陷清单"
            est_hours: 10
          - task: "性能测试"
            agent: "test-agent"
            deliverable: "性能基准报告 + 对比数据"
            est_hours: 8
          - task: "可靠性测试"
            agent: "test-agent"
            deliverable: "可靠性测试报告 + MTBF估算"
            est_hours: 12
```

### 1.3 WBS Decomposition Process

```yaml
process_wbs:
  step_1: "Receive PRD from CTO"
  step_2: "Identify major deliverables (L1)"
  step_3: "Break down into work packages (L2)"
  step_4: "Decompose into assignable tasks (L3)"
  step_5: "Define dependencies between tasks"
  step_6: "Estimate effort for each task"
  step_7: "Assign to domain agents"
  step_8: "Submit WBS to Critic for review"
  step_9: "Revise based on Critic feedback"
  step_10: "Submit to CTO for approval"
```

---

## 2. Dependency Graph (DAG) Construction & Maintenance

### 2.1 DAG Building Algorithm

```python
def build_dag(tasks: List[Task]) -> DAG:
    """
    Build a validated DAG from task list.
    Raises CycleError if circular dependency detected.
    """
    dag = DAG()
    
    # Step 1: Add all nodes
    for task in tasks:
        dag.add_node(task.id, task)
    
    # Step 2: Add edges (dependencies)
    for task in tasks:
        for dep_id in task.dependencies:
            dag.add_edge(dep_id, task.id, type=task.dep_type)
    
    # Step 3: Validate (no cycles)
    if dag.has_cycle():
        cycles = dag.find_cycles()
        raise CycleError(f"Circular dependencies found: {cycles}")
    
    # Step 4: Compute topological order
    dag.topological_order = dag.topological_sort()
    
    # Step 5: Compute critical path
    dag.critical_path = compute_critical_path(dag)
    
    return dag
```

### 2.2 Dependency Detection Rules

```yaml
dependency_rules:
  # Automatically detected dependency types
  auto_detect:
    data_dependency:
      pattern: "Task B's input is Task A's output"
      example: "DSP算法设计 → 需要 ← 声学目标曲线"
      action: "Create data_dependency edge"
      
    resource_dependency:
      pattern: "Task B uses resource produced by Task A"
      example: "PCB布局 → 需要 ← DSP芯片引脚定义"
      action: "Create resource_dependency edge"
      
    spatial_dependency:
      pattern: "Physical design constraints between domains"
      example: "结构设计 → 需要 ← 声学腔体尺寸"
      action: "Create spatial_dependency edge"
      
  # Cross-domain interface dependencies
  interface_dependencies:
    check: "Review ICD (Interface Control Document) for declared interfaces"
    action: "Create interface_dependency edge for each declared interface"
    
  # Review dependencies (enforced by system)
  review_dependency:
    pattern: "All tasks → Critic → Next task"
    action: "Auto-create review_dependency edge"
    system_enforced: true
```

### 2.3 DAG Maintenance on Changes

```yaml
dag_maintenance:
  on_task_add:
    - "Add node to DAG"
    - "Parse dependencies from task spec"
    - "Validate no cycle introduced"
    - "Recompute critical path"
    - "Notify affected agents if schedule changes"
    
  on_task_remove:
    - "Remove node and all edges"
    - "Check for orphaned tasks"
    - "Recompute critical path"
    - "Notify downstream task owners"
    
  on_dependency_change:
    - "Update edge with new type/metadata"
    - "Validate no cycle introduced"
    - "Recompute critical path"
    - "If critical path changes → escalate to CTO if impact > 1 day"
    
  on_completion:
    - "Mark node as COMPLETED"
    - "Identify newly unblocked tasks"
    - "Add ready-to-assign tasks to dispatch queue"
    - "Update critical path (actuals vs planned)"
```

### 2.4 DAG Visualization Format

```
Critical Path: T001 → T005 → T012 → T018 (Total: 38h)

[AC-001] Acoustic FEM        [8h] ████████░░  IN_PROGRESS
  │
  ▼ data
[DSP-001] Filter Design     [6h] ░░░░░░░░░░  PENDING ◄── Critical
  │
  ├──► [HW-001] Schematic    [6h] ░░░░░░░░░░  PENDING
  │
  ▼ resource
[HW-002] PCB Layout        [10h] ░░░░░░░░░░  PENDING ◄── Critical
  │
  ├──► [ST-001] 3D Design    [8h] ░░░░░░░░░░  PENDING
  │
  ▼
[TE-001] Integration Test   [12h] ░░░░░░░░░░  PENDING ◄── Critical
```

---

## 3. Task State Machine Management

### 3.1 State Transition Enforcement

```yaml
state_machine:
  valid_transitions:
    PENDING:
      - to: ASSIGNED
        by: "project-manager"
        condition: "dependencies_met AND agent_available"
      - to: CANCELLED
        by: "project-manager"
        condition: "cto_approved_scope_change"
        
    ASSIGNED:
      - to: IN_PROGRESS
        by: "domain-agent"
        condition: "agent_accepts"
      - to: PENDING
        by: "domain-agent"
        condition: "agent_rejects_with_reason"
      - to: IN_PROGRESS
        by: "auto"
        condition: "agent_no_response_1h"  # auto-accept after 1h
        
    IN_PROGRESS:
      - to: REVIEW
        by: "domain-agent"
        condition: "deliverable_submitted"
      - to: PENDING
        by: "project-manager"
        condition: "agent_blocked_or_gives_up"
      - to: ESCALATED
        by: "auto"
        condition: "in_progress > 2x estimated AND no update"
        
    REVIEW:
      - to: PASSED
        by: "critic-agent"
        condition: "no BLOCKER AND no MAJOR findings"
      - to: PASSED_WITH_MINOR
        by: "critic-agent"
        condition: "only MINOR/INFO findings; agent_can_fix_post_pass"
      - to: FAILED
        by: "critic-agent"
        condition: "BLOCKER OR MAJOR findings"
      - to: AUTO_REJECTED
        by: "auto"
        condition: "review_pending > 24h"
        
    PASSED:
      - to: COMPLETED
        by: "project-manager"
        condition: "cto_not_required_or_cto_approved"
      - to: HUMAN_REVIEW
        by: "project-manager"
        condition: "cto_mandatory_gate"
      - to: REVIEW
        by: "project-manager"
        condition: "minor_fixes_required"
      
    PASSED_WITH_MINOR:
      - to: COMPLETED
        by: "project-manager"
        condition: "minor_fixes_committed"
      
    FAILED:
      - to: IN_PROGRESS
        by: "domain-agent"
        condition: "revision_submitted"
      - to: PENDING
        by: "project-manager"
        condition: "task_reassigned"
      - to: ESCALATED
        by: "project-manager"
        condition: "3x_failed"
      
    HUMAN_REVIEW:
      - to: COMPLETED
        by: "human-cto"
        condition: "cto_approves"
      - to: FAILED
        by: "human-cto"
        condition: "cto_rejects_with_feedback"
      - to: REVIEW
        by: "human-cto"
        condition: "cto_requests_changes"
      
    ESCALATED:
      - to: "any_previous_state"
        by: "human-cto"
        condition: "cto_resolves"
      - to: CANCELLED
        by: "human-cto"
        condition: "cto_cancels"
      
    COMPLETED:
      - to: ARCHIVED
        by: "project-manager"
        condition: "project_closed"
```

### 3.2 State Change Protocol

```yaml
state_change_protocol:
  on_state_change:
    - "Log transition with timestamp, actor, reason"
    - "Update DAG node color/state"
    - "Notify downstream task owners if their dependencies change"
    - "Update dashboard"
    - "Check if critical path affected"
    - "If critical path delay > 0.5 day → flag risk"
    - "If delay > 1 day → escalate to CTO"
    
  auto_transitions:
    ASSIGNED → IN_PROGRESS: 1_hour_timeout
    REVIEW → AUTO_REJECTED: 24_hour_timeout
    IN_PROGRESS → ESCALATED: 2x_estimate_timeout
```

---

## 4. Scheduling Algorithm

### 4.1 Priority + Dependency + Resource Scheduling

```python
def schedule_next_task(dag: DAG, agents: List[Agent]) -> Optional[TaskAssignment]:
    """
    Select next task to assign considering:
    1. Dependencies (all predecessors must be COMPLETED)
    2. Priority (critical path first, then priority level)
    3. Resource availability (agent capacity)
    4. Historical performance calibration
    """
    
    # Step 1: Find all tasks with met dependencies
    ready_tasks = [
        t for t in dag.tasks 
        if t.status == PENDING 
        and all(dep.status == COMPLETED for dep in t.dependencies)
    ]
    
    if not ready_tasks:
        return None
    
    # Step 2: Score each task
    for task in ready_tasks:
        task.schedule_score = compute_task_score(task, dag, agents)
    
    # Step 3: Select highest scoring task
    next_task = max(ready_tasks, key=lambda t: t.schedule_score)
    
    # Step 4: Find best agent
    available_agents = [
        a for a in agents 
        if a.domain == next_task.domain 
        and a.current_load < a.max_capacity
    ]
    
    if not available_agents:
        return None  # Will retry on next cycle
    
    best_agent = select_best_agent(next_task, available_agents)
    
    # Step 5: Apply calibration
    calibrated_hours = apply_calibration(next_task.est_hours, best_agent)
    
    return TaskAssignment(
        task=next_task,
        agent=best_agent,
        deadline=compute_deadline(calibrated_hours),
        priority=dynamic_priority(next_task, dag)
    )

def compute_task_score(task, dag, agents) -> float:
    """Composite scheduling score."""
    score = 0.0
    
    # Critical path bonus (weight: 0.40)
    if task in dag.critical_path:
        score += 0.40 * (1 + dag.slack_hours(task) / 100)
    
    # Priority level (weight: 0.25)
    priority_map = {P0_CRITICAL: 1.0, P1_HIGH: 0.75, P2_NORMAL: 0.50, P3_LOW: 0.25}
    score += 0.25 * priority_map[task.priority]
    
    # Fan-out bonus (weight: 0.20)
    downstream_count = len(task.downstream_tasks)
    score += 0.20 * min(downstream_count / 5.0, 1.0)
    
    # Risk penalty (weight: 0.15)
    risk_score = get_risk_score(task)
    score += 0.15 * (1.0 - risk_score)  # lower risk = higher score
    
    return score

def select_best_agent(task, available_agents) -> Agent:
    """Select agent with best track record for this task type."""
    scored = []
    for agent in available_agents:
        score = (
            agent.first_pass_rate * 0.4 +
            (1 - abs(agent.estimation_bias)) * 0.3 +
            (1 - agent.current_load / agent.max_capacity) * 0.3
        )
        scored.append((agent, score))
    return max(scored, key=lambda x: x[1])[0]
```

### 4.2 Dynamic Priority Adjustment

```yaml
dynamic_priority:
  trigger_conditions:
    - name: "Critical Path Threat"
      condition: "task.slack_hours < 4"
      action: "priority = P0_CRITICAL"
      notify: "cto_if_sprint_at_risk"
      
    - name: "Downstream Cascade"
      condition: "task has > 3 downstream tasks AND any downstream has < 8h slack"
      action: "priority += 1 level (max P0)"
      
    - name: "Agent Idle Prevention"
      condition: "agent.utilization < 30% AND ready_task exists for that domain"
      action: "bump matching tasks priority by 0.5 level"
      
    - name: "Deadline Proximity"
      condition: "days_to_deadline < 3 AND task not started"
      action: "priority = max(P1_HIGH, current)"
      notify: "agent + cto"
```

---

## 5. Risk Identification & Escalation

### 5.1 Risk Detection Engine

```yaml
risk_detection:
  monitoring_interval: "15 minutes"
  
  indicators:
    schedule_risks:
      - indicator: "Task in_progress_hours > 1.5 × estimated_hours"
        severity: "HIGH"
        action: "Ping agent; if no response in 30min, flag risk"
        
      - indicator: "Critical path task delayed > 0.5 day"
        severity: "CRITICAL"
        action: "Immediate notification to CTO with impact analysis"
        
      - indicator: "> 30% tasks in backlog not assigned"
        severity: "MEDIUM"
        action: "Review agent capacity; consider reallocation"
        
    quality_risks:
      - indicator: "Agent avg critic_cycles > 2.5 over last 5 tasks"
        severity: "HIGH"
        action: "Flag agent quality concern; consider pair review"
        
      - indicator: "Same task failed critic > 3 times"
        severity: "CRITICAL"
        action: "Escalate to CTO; recommend expert consultation"
        
    resource_risks:
      - indicator: "Agent load > 95% for > 4 hours"
        severity: "MEDIUM"
        action: "Redistribute pending tasks; consider parallel assignment"
        
      - indicator: "Domain agent unavailable (error/crash)"
        severity: "CRITICAL"
        action: "Immediate escalation; activate backup agent or human"
```

### 5.2 Escalation Report Format

```yaml
escalation_report:
  header:
    escalation_id: "ESC-{timestamp}-{seq}"
    level: "1|2|3|4"
    severity: "LOW|MEDIUM|HIGH|CRITICAL"
    triggered_by: "auto|pm|critic|agent"
    
  body:
    summary: "One-line description"
    detailed_description: "Full context"
    impact_analysis:
      affected_tasks: []
      schedule_impact_days: 0.0
      quality_impact: "description"
      cost_impact: "description"
    root_cause: "Analysis of why this happened"
    
  options:
    - option_id: "A"
      description: ""
      pros: []
      cons: []
      estimated_impact: ""
      
    - option_id: "B"
      description: ""
      pros: []
      cons: []
      estimated_impact: ""
      
  recommendation:
    recommended_option: "A|B"
    rationale: ""
    confidence: "HIGH|MEDIUM|LOW"
    
  request:
    decision_needed_by: "timestamp"
    specific_ask: "Clear statement of what decision is needed"
```

---

## 6. Communication Interfaces

### 6.1 Interface with Critic Agent

```yaml
critic_interface:
  # PM → Critic: Deliverable for review
  submit_for_review:
    message_type: "REVIEW_REQUEST"
    to: "critic-agent"
    payload:
      deliverable_id: "DEL-{task_id}-{version}"
      task_id: "TASK-{id}"
      task_name: ""
      domain: "acoustics|dsp|hardware|structure|test"
      agent: "agent_id"
      deliverable_type: "document|code|design|data|report"
      content: "{deliverable content or reference}"
      context:
        prd_reference: ""
        dependencies_met: []
        previous_reviews: []        # For revision submissions
      deadline: "review_due_timestamp"
    
  # Critic → PM: Review result
  receive_review_result:
    message_type: "REVIEW_RESULT"
    from: "critic-agent"
    payload:
      deliverable_id: ""
      verdict: "PASSED|FAILED|ESCALATE"
      findings:
        - severity: "BLOCKER|MAJOR|MINOR|INFO"
          category: ""
          description: ""
          location: ""
          suggestion: ""
      summary: "Overall assessment"
      recommended_action: ""
      
  # PM action based on result
  on_passed:
    - "Update task status: REVIEW → PASSED"
    - "If CTO gate required → route to HUMAN_REVIEW"
    - "If no CTO gate → mark COMPLETED"
    - "Notify agent of success"
    - "Queue downstream tasks for dispatch"
    
  on_failed:
    - "Update task status: REVIEW → FAILED"
    - "Send feedback to domain agent with critic findings"
    - "Set revision deadline (default: original estimate × 0.5)"
    - "Increment failure counter"
    - "If failure_count ≥ 3 → escalate to CTO"
    
  on_escalate:
    - "Create escalation report"
    - "Route to CTO immediately"
    - "Notify all affected agents"
```

### 6.2 Interface with Domain Agents

```yaml
domain_agent_interface:
  # PM → Agent: Task assignment
  assign_task:
    message_type: "TASK_ASSIGNMENT"
    to: "{domain-agent}"
    payload:
      task_id: "TASK-{id}"
      name: ""
      description: ""
      deliverable_spec: ""
      acceptance_criteria: []
      deadline: "timestamp"
      priority: "P0|P1|P2|P3"
      dependencies:
        met: []           # Already completed
        pending: []       # Not yet completed (heads-up)
      context:
        prd_excerpt: ""
        related_deliverables: []
      
  # Agent → PM: Status update
  receive_status_update:
    message_type: "STATUS_UPDATE"
    from: "{domain-agent}"
    payload:
      task_id: ""
      status: "IN_PROGRESS|BLOCKED|READY_FOR_REVIEW"
      progress_pct: 0      # Self-reported progress
      hours_spent: 0.0
      hours_remaining: 0.0
      blockers: []
      questions: []
      
  # Agent → PM: Deliverable submission
  receive_deliverable:
    message_type: "DELIVERABLE_SUBMIT"
    from: "{domain-agent}"
    payload:
      task_id: ""
      deliverable: ""
      self_check_completed: true
      known_issues: []
    next_action: "Route to Critic Agent for review"
```

### 6.3 Interface with Human CTO

```yaml
cto_interface:
  # PM → CTO: Daily status report
  daily_report:
    frequency: "daily 09:00 UTC"
    format: "Markdown (see profile.md template)"
    content:
      - executive_summary
      - completed_work
      - in_progress
      - review_queue
      - upcoming_tasks
      - risks_and_issues
      - decisions_needed
      
  # PM → CTO: Escalation
  escalation:
    trigger: "Risk level HIGH or above; or unresolved blocker > 4h"
    format: "Escalation report (see section 5.2)"
    sla: "CTO responds within 2-4h depending on level"
    
  # CTO → PM: Directives
  receive_directive:
    message_type: "CTO_DIRECTIVE"
    from: "human-cto"
    valid_directives:
      - "APPROVE_PLAN"
      - "MODIFY_SCOPE"
      - "REASSIGN_TASK"
      - "CHANGE_PRIORITY"
      - "ACCEPT_RISK"
      - "INJECT_RESOURCE"
      - "PAUSE_PROJECT"
      - "ABORT_PROJECT"
    action: "Acknowledge within 15min; execute within 1h; confirm completion"
    
  # CTO → PM: Gate decisions
  gate_review:
    gates: ["PLAN_APPROVAL", "ARCHITECTURE_REVIEW", "PROTOTYPE_GO_NOGO", "FINAL_APPROVAL"]
    format: "Gate review package with all deliverables and Critic summary"
    cto_response: "APPROVE|REJECT|REQUEST_CHANGES"
```

---

## 7. Dispatch Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DISPATCH ENGINE                              │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ New Task │───►│Deps Met? │───►│Agent     │───►│Critical  │ │
│  │ Added    │    │Check     │    │Available?│    │Path?     │ │
│  └──────────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘ │
│                       │               │               │        │
│                    NO │            NO │            YES│        │
│                       ▼               ▼               ▼        │
│                  ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│                  │Wait Queue│   │Wait Pool │   │Priority  │  │
│                  │          │   │          │   │Boost +   │  │
│                  │(check    │   │(retry on │   │Dispatch  │  │
│                  │ every    │   │ agent    │   │          │  │
│                  │ cycle)   │   │ free)    │   │          │  │
│                  └──────────┘   └──────────┘   └──────────┘  │
│                                                  │            │
│                                                  ▼            │
│                                            ┌──────────┐       │
│                                            │Assign to │       │
│                                            │Best Agent│       │
│                                            │+ Deadline│       │
│                                            └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Self-Diagnostics

```yaml
self_diagnostics:
  health_checks:
    - name: "DAG Integrity"
      interval: "every 15 min"
      check: "No cycles, all tasks reachable, critical path valid"
      
    - name: "Agent Availability"
      interval: "every 5 min"
      check: "All registered agents responsive"
      
    - name: "Queue Health"
      interval: "every 15 min"
      check: "No task stuck in any state > SLA"
      
    - name: "Critic Pipeline"
      interval: "every 30 min"
      check: "Review queue not backing up > 5 items"
      
  recovery_actions:
    agent_unresponsive:
      - "Retry ping × 3"
      - "If still no response → mark agent OFFLINE"
      - "Reassign queued tasks to other agents"
      - "Escalate to CTO if no backup agent"
      
    dag_corruption:
      - "Rebuild DAG from task records"
      - "Validate against last known good state"
      - "Alert CTO if unrecoverable"
```

---

*Project Manager Agent Skill v1.0.0 — The Complete Orchestration Toolkit*
