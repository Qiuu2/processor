<!-- ORIGINAL agents/critic/skill.md frontmatter — preserved verbatim as a comment
     (the live Claude Code skill frontmatter is the top of .claude/skills/critic/SKILL.md):
name: critic-skill
description: >
  Critic Agent的技能配置文件。
  包含对抗式提问技术、各领域常见错误模式识别、理想化假设检测框架、
  评审Checklist模板、评审意见分级标准、与人类CTO的评审结果上报格式、
  与被评审Agent的反馈循环机制、评审历史追踪。
version: 1.0.0
author: ITC Architecture Team
-->

# Critic Agent — Skill

## 1. Adversarial Questioning Techniques (Devil's Advocate)

### 1.1 Core Method: Socratic Interrogation

```yaml
socratic_interrogation:
  purpose: "Systematically expose weaknesses through structured questioning"
  phases:
    phase_1_clarify:
      name: "Clarify"
      goal: "Ensure complete understanding of the deliverable"
      questions:
        - "这个交付物的核心主张是什么？"
        - "使用的关键方法/技术是什么？"
        - "依赖了哪些外部输入或假设？"
        - "预期的使用场景是什么？"
        
    phase_2_challenge:
      name: "Challenge"
      goal: "Stress-test every claim and assumption"
      techniques:
        - "极端条件测试：如果{X}是正常值的10倍/0.1倍，结论还成立吗？"
        - "边界探测：在什么条件下这个方法会失效？"
        - "反例寻找：是否存在反例可以推翻这个结论？"
        - "替代方案：是否有其他方法可以得到不同结论？"
        
    phase_3_evidence:
      name: "Evidence"
      goal: "Verify all claims have adequate support"
      questions:
        - "这个数据的来源是什么？"
        - "测量方法是什么？不确定度是多少？"
        - "样本量是否足够？统计显著性如何？"
        - "是否有人独立验证过这个结果？"
        
    phase_4_implication:
      name: "Implication"
      goal: "Explore downstream consequences"
      questions:
        - "如果这个结论是错误的，下游会受到什么影响？"
        - "这个设计决策在量产阶段会产生什么问题？"
        - "长期使用后性能会如何退化？"
        - "与其他子系统的交互会产生什么意外？"
```

### 1.2 Devil's Advocate Patterns

```yaml
devils_advocate_patterns:
  pattern_1_assumption_reversal:
    name: "Assumption Reversal"
    description: "反转关键假设，看结论是否仍然成立"
    template: "你假设了{X}。如果{X}不成立（例如{反例}），你的结论会怎样？"
    example: "你假设了室温25°C。如果在40°C高温环境下，这个热设计还成立吗？"
    
  pattern_2_worst_case_exploration:
    name: "Worst-Case Exploration"
    description: "假设所有不利因素同时发生"
    template: "在最坏情况下（{worst_conditions}），系统的表现是什么？"
    example: "最高温度+最大负载+最小输入电压同时发生，电源还能稳定工作吗？"
    
  pattern_3_alternative_explanation:
    name: "Alternative Explanation"
    description: "提供替代解释，测试原结论的稳健性"
    template: "观察到{现象}。除了你的解释{X}，是否可能是{Y}或{Z}导致的？"
    example: "THD升高了。除了你说的新codec，是否可能是电源纹波增大导致的？"
    
  pattern_4_novice_question:
    name: "Novice Question"
    description: "以初学者视角提出基础问题，暴露隐含假设"
    template: "对于不熟悉这个领域的人，你能解释为什么{X}是成立的吗？"
    example: "为什么这里可以用集总参数模型，而不是分布参数？"
    
  pattern_5_scale_stress:
    name: "Scale Stress Test"
    description: "将参数推向极端值测试设计鲁棒性"
    template: "如果{parameter}变为{extreme_value}，设计还能满足要求吗？"
    example: "如果批量生产公差达到±0.2mm而不是±0.05mm，装配还能保证密封吗？"
    
  pattern_6_temporal_shift:
    name: "Temporal Shift"
    description: "将时间维度引入，考察长期影响"
    template: "经过{time_period}的使用后，{property}会如何变化？"
    example: "振膜材料老化1000小时后，谐振频率会偏移多少？"
```

### 1.3 Adversarial Questioning Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              ADVERSARIAL QUESTIONING ENGINE                      │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ Receive  │───►│ Identify │───►│ Select   │───►│ Generate │ │
│  │ Deliver- │    │ Key      │    │ Challenge│    │ Questions│ │
│  │ able     │    │ Claims & │    │ Patterns │    │          │ │
│  │          │    │ Assump.  │    │          │    │          │ │
│  └──────────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘ │
│                       │               │               │        │
│                       ▼               ▼               ▼        │
│                  ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│                  │ Claim    │   │ Risk     │   │ Question │  │
│                  │ Database │   │ Scorer   │   │ Ranker   │  │
│                  │          │   │          │   │          │  │
│                  └──────────┘   └──────────┘   └──────────┘  │
│                                                       │        │
│                                                       ▼        │
│                                                 ┌──────────┐   │
│                                                 │Inject to │   │
│                                                 │Review    │   │
│                                                 │Report    │   │
│                                                 └──────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Common Error Pattern Recognition

### 2.1 Error Pattern Database

```yaml
error_patterns:
  # ─── Acoustics Domain ───
  acoustics:
    - pattern_id: "AC-ERR-001"
      name: "Mesh Convergence Not Verified"
      frequency: 8
      severity: "MAJOR"
      description: "FEM仿真未进行网格收敛性验证"
      indicators:
        - "报告中缺少网格数量扫描"
        - "结果精度声明没有支撑"
        - "不同网格密度的结果对比缺失"
      fix: "要求提供至少3种网格密度的收敛曲线"
      
    - pattern_id: "AC-ERR-002"
      name: "Measurement Environment Not Specified"
      frequency: 6
      severity: "MAJOR"
      description: "声学测量未记录环境条件"
      indicators:
        - "缺少温度/湿度记录"
        - "背景噪声级未说明"
        - "测量距离/角度不明确"
      fix: "要求补充完整的测量环境报告"
      
    - pattern_id: "AC-ERR-003"
      name: "Statistically Insufficient Samples"
      frequency: 4
      severity: "MINOR"
      description: "样机数量不足以支持统计结论"
      indicators:
        - "N < 5却报告统计量"
        - "未说明样本量的选择依据"
      fix: "增加样本量或降低统计声明的确定性"
      
  # ─── DSP Domain ───
  dsp:
    - pattern_id: "DSP-ERR-001"
      name: "Fixed-Point Overflow Risk"
      frequency: 12
      severity: "BLOCKER"
      description: "定点实现缺少溢出保护"
      indicators:
        - "没有Q格式说明"
        - "缺少溢出检测/饱和逻辑"
        - "最坏情况动态范围未分析"
      fix: "要求提供完整的Q格式规范和溢出分析"
      
    - pattern_id: "DSP-ERR-002"
      name: "MIPS Claim Without Measurement"
      frequency: 7
      severity: "MAJOR"
      description: "声称满足实时要求但没有实测MIPS"
      indicators:
        - "仅理论估算，无profiler数据"
        - "最坏情况场景未测试"
        - "缓存效应未考虑"
      fix: "要求在目标平台上用profiler实测"
      
    - pattern_id: "DSP-ERR-003"
      name: "Filter Stability Not Verified"
      frequency: 5
      severity: "BLOCKER"
      description: "IIR滤波器未验证稳定性"
      indicators:
        - "极点位置未分析"
        - "极限环振荡未检查"
        - "系数量化后的稳定性未验证"
      fix: "要求提供极点零点和稳定性分析"
      
  # ─── Hardware Domain ───
  hardware:
    - pattern_id: "HW-ERR-001"
      name: "Thermal Design Missing"
      frequency: 9
      severity: "MAJOR"
      description: "缺少热设计或热仿真"
      indicators:
        - "无结温估算"
        - "散热器选型无依据"
        - "PCB铜面积未针对散热优化"
      fix: "要求提供热仿真报告和结温预算"
      
    - pattern_id: "HW-ERR-002"
      name: "ERC/DRC Violations"
      frequency: 11
      severity: "BLOCKER"
      description: "电气规则或设计规则检查未通过"
      indicators:
        - "未运行ERC/DRC"
        - "有报错但未解释 waive 理由"
        - "制造商会拒收的设计问题"
      fix: "必须通过所有ERC/DRC，或提供正式的waiver"
      
    - pattern_id: "HW-ERR-003"
      name: "Component Derating Inadequate"
      frequency: 6
      severity: "MAJOR"
      description: "元件降额不足"
      indicators:
        - "实际应力 > 额定值的80%"
        - "无降额分析表"
        - "对关键元件（电容、MOSFET）未单独分析"
      fix: "要求提供完整的元件应力分析和降额表"
      
    - pattern_id: "HW-ERR-004"
      name: "EMC/EMI Not Considered"
      frequency: 5
      severity: "MAJOR"
      description: "电磁兼容性未在设计中考虑"
      indicators:
        - "无接地策略说明"
        - "高速信号无端接/阻抗控制"
        - "屏蔽设计缺失"
      fix: "要求提供EMC设计检查清单结果"
      
  # ─── Structure Domain ───
  structure:
    - pattern_id: "ST-ERR-001"
      name: "Wall Thickness Below Minimum"
      frequency: 4
      severity: "BLOCKER"
      description: "壁厚低于材料和工艺允许的最小值"
      indicators:
        - "壁厚 < 0.8mm（注塑ABS）"
        - "长宽比过大的薄壁区域"
        - "无结构强度验证"
      fix: "增加壁厚或提供FEA强度分析"
      
    - pattern_id: "ST-ERR-002"
      name: "Draft Angle Missing"
      frequency: 3
      severity: "MAJOR"
      description: "脱模斜度不足或缺失"
      indicators:
        - "垂直面无斜度"
        - "深腔区域斜度 < 0.5°"
        - "纹理面未增加额外斜度"
      fix: "按材料要求增加脱模斜度"
      
    - pattern_id: "ST-ERR-003"
      name: "Interference Not Checked"
      frequency: 5
      severity: "MAJOR"
      description: "零件干涉检查未执行"
      indicators:
        - "装配体干涉检查报告缺失"
        - "运动件极限位置未检查"
      fix: "要求提供干涉检查报告（0间隙分析）"
      
  # ─── Test Domain ───
  test:
    - pattern_id: "TE-ERR-001"
      name: "Test Coverage Gap"
      frequency: 6
      severity: "MAJOR"
      description: "测试未覆盖所有需求"
      indicators:
        - "需求-测试矩阵有空白"
        - "边界条件未测试"
        - "错误注入测试缺失"
      fix: "补充缺失的测试用例"
      
    - pattern_id: "TE-ERR-002"
      name: "Pass/Fail Criteria Vague"
      frequency: 5
      severity: "MINOR"
      description: "判定标准不清晰"
      indicators:
        - "使用'正常'、'可接受'等模糊描述"
        - "缺少量化阈值"
        - "统计判据未定义"
      fix: "量化所有pass/fail标准"
```

### 2.2 Error Pattern Detection Engine

```python
def detect_error_patterns(deliverable: Deliverable, domain: str) -> List[Finding]:
    """
    Scan deliverable against known error patterns for the domain.
    Returns list of findings with severity and recommendations.
    """
    findings = []
    
    # Load patterns for the domain
    patterns = error_pattern_db.get(domain, [])
    
    for pattern in patterns:
        # Check each indicator
        match_score = 0
        matched_indicators = []
        
        for indicator in pattern.indicators:
            if check_indicator(deliverable, indicator):
                match_score += 1
                matched_indicators.append(indicator)
        
        # If enough indicators match, create finding
        if match_score >= len(pattern.indicators) * 0.5:
            findings.append(Finding(
                id=f"AUTO-{pattern.pattern_id}",
                severity=pattern.severity,
                category="auto_detected",
                description=pattern.description,
                matched_indicators=matched_indicators,
                recommendation=pattern.fix,
                reference=pattern.pattern_id
            ))
    
    return findings
```

---

## 3. Idealized Assumption Detection Framework

### 3.1 Assumption Taxonomy

```yaml
assumption_taxonomy:
  categories:
    environmental:
      name: "环境假设"
      common_assumptions:
        - "室温25°C（实际可能0-40°C）"
        - "标准大气压（海拔影响）"
        - "低湿度（可能影响声学材料）"
        - "无振动（运输和使用中都有振动）"
        - "洁净环境（灰尘影响散热和声学）"
      
    component:
      name: "元件假设"
      common_assumptions:
        - "典型参数（实际是分布）"
        - "无老化（性能随时间退化）"
        - "理想电源（实际有纹波和噪声）"
        - "完美接地（实际有地弹和共模噪声）"
        - "零公差（制造公差累积）"
      
    operational:
      name: "操作假设"
      common_assumptions:
        - "理想信号源（实际有抖动和噪声）"
        - "稳态工作（实际有瞬态和切换）"
        - "标称负载（实际负载变化范围大）"
        - "连续工作（实际有开关循环）"
      
    measurement:
      name: "测量假设"
      common_assumptions:
        - "理想仪器（实际有精度和噪声限制）"
        - "完美校准（校准漂移）"
        - "无干扰（电磁干扰、声学干扰）"
        - "代表性样本（抽样偏差）"
```

### 3.2 Assumption Detection Checklist

```yaml
assumption_detection_checklist:
  general:
    - "检查是否声明了所有工作条件"
    - "检查是否量化了不确定性"
    - "检查是否分析了灵敏度"
    - "检查是否考虑了最坏情况"
    - "检查是否验证了关键假设"
    
  score_calculation:
    each_assumption:
      declared: +1     # 假设被显式声明
      quantified: +1   # 假设有量化范围
      verified: +2     # 假设有验证数据
      worst_cased: +1  # 最坏情况被分析
    
    risk_level:
      high_risk: "score < 2 (假设未充分验证)"
      medium_risk: "score = 2-3"
      low_risk: "score >= 4"
```

### 3.3 Assumption Challenge Report

```yaml
assumption_challenge_template:
  deliverable_id: ""
  assumptions_found: []
  
  challenged:
    - assumption: ""
      stated_in: "location in deliverable"
      challenge: "why this might not hold"
      worst_case_impact: "what happens if assumption fails"
      evidence_required: "what data would validate this"
      recommendation: "how to make this robust"
      
  undeclared_assumptions:
    - assumption: ""
      inferred_from: "where Critic detected it"
      risk_level: "HIGH|MEDIUM|LOW"
      required_action: ""
```

---

## 4. Domain Review Checklists

### 4.1 Acoustics Review Checklist

```yaml
checklist_acoustics:
  simulation:
    - item: "网格收敛性验证"
      severity: "MAJOR"
      verify: "至少3种网格密度的结果对比"
      
    - item: "边界条件合理性"
      severity: "MAJOR"
      verify: "边界类型与物理场景匹配"
      
    - item: "材料参数来源"
      severity: "MAJOR"
      verify: "所有材料参数有引用来源"
      
    - item: "模型简化合理性"
      severity: "MINOR"
      verify: "简化对结果的影响被量化"
      
    - item: "结果不确定性分析"
      severity: "MAJOR"
      verify: "参数敏感性分析"
      
  measurement:
    - item: "测量环境条件记录"
      severity: "MAJOR"
      verify: "温度、湿度、气压、背景噪声"
      
    - item: "测量设备校准状态"
      severity: "MAJOR"
      verify: "校准证书在有效期内"
      
    - item: "测量距离和位置"
      severity: "MAJOR"
      verify: "符合IEC 60268-5或其他适用标准"
      
    - item: "数据后处理方法"
      severity: "MINOR"
      verify: "窗函数、平均次数、平滑方法"
      
    - item: "重复性验证"
      severity: "MAJOR"
      verify: "多次测量的一致性"
```

### 4.2 DSP Review Checklist

```yaml
checklist_dsp:
  algorithm:
    - item: "数值稳定性"
      severity: "BLOCKER"
      verify: "极点位置、极限环分析"
      
    - item: "定点化实现"
      severity: "BLOCKER"
      verify: "Q格式、溢出保护、舍入模式"
      
    - item: "实时性能验证"
      severity: "MAJOR"
      verify: "目标平台profiler数据"
      
    - item: "内存占用"
      severity: "MAJOR"
      verify: "代码段、数据段、堆栈分别量化"
      
    - item: "延迟分析"
      severity: "MAJOR"
      verify: "算法延迟 + 实现延迟"
      
  implementation:
    - item: "代码可读性"
      severity: "MINOR"
      verify: "注释、命名、结构"
      
    - item: "可测试性"
      severity: "MAJOR"
      verify: "单元测试覆盖关键路径"
      
    - item: "边界条件处理"
      severity: "BLOCKER"
      verify: "输入极限、除零、溢出"
```

### 4.3 Hardware Review Checklist

```yaml
checklist_hardware:
  schematic:
    - item: "ERC通过"
      severity: "BLOCKER"
      verify: "所有ERC错误或正式waiver"
      
    - item: "信号完整性"
      severity: "MAJOR"
      verify: "高速信号长度匹配、端接"
      
    - item: "电源完整性"
      severity: "MAJOR"
      verify: "去耦电容布局、PDN阻抗"
      
    - item: "降额分析"
      severity: "MAJOR"
      verify: "所有元件应力 < 80%额定"
      
    - item: "安全规范"
      severity: "BLOCKER"
      verify: "绝缘、爬电距离、过压/过流保护"
      
  pcb:
    - item: "DRC通过"
      severity: "BLOCKER"
      verify: "所有DRC错误或正式waiver"
      
    - item: "层叠设计"
      severity: "MAJOR"
      verify: "阻抗控制、参考平面完整性"
      
    - item: "热设计"
      severity: "MAJOR"
      verify: "热仿真、铜面积、散热过孔"
      
    - item: "EMC设计"
      severity: "MAJOR"
      verify: "接地策略、屏蔽、滤波"
      
    - item: "DFM检查"
      severity: "MAJOR"
      verify: "制造商确认"
      
    - item: "丝印"
      severity: "MINOR"
      verify: "极性、位号、版本号"
```

### 4.4 Structure Review Checklist

```yaml
checklist_structure:
  design:
    - item: "壁厚"
      severity: "BLOCKER"
      verify: "≥材料最小壁厚要求"
      
    - item: "脱模斜度"
      severity: "MAJOR"
      verify: "所有外表面的脱模斜度"
      
    - item: "圆角"
      severity: "MINOR"
      verify: "内圆角避免应力集中"
      
    - item: "干涉检查"
      severity: "BLOCKER"
      verify: "装配体零干涉"
      
    - item: "公差分析"
      severity: "MAJOR"
      verify: "关键尺寸公差累积"
      
  manufacturing:
    - item: "DFM报告"
      severity: "MAJOR"
      verify: "制造商确认可生产"
      
    - item: "模具可行性"
      severity: "MAJOR"
      verify: "分型线、顶出、浇口位置"
      
    - item: "材料选择"
      severity: "MAJOR"
      verify: "符合环保和安全要求"
```

### 4.5 Test Review Checklist

```yaml
checklist_test:
  plan:
    - item: "需求覆盖"
      severity: "BLOCKER"
      verify: "100%需求-测试映射"
      
    - item: "pass/fail标准"
      severity: "BLOCKER"
      verify: "所有判定标准量化"
      
    - item: "测试环境"
      severity: "MAJOR"
      verify: "环境条件明确定义"
      
    - item: "样本量"
      severity: "MAJOR"
      verify: "统计显著性论证"
      
  execution:
    - item: "原始数据"
      severity: "MAJOR"
      verify: "可追溯的原始记录"
      
    - item: "缺陷记录"
      severity: "MAJOR"
      verify: "所有缺陷有唯一ID、描述、严重级"
      
    - item: "复测验证"
      severity: "MAJOR"
      verify: "修复后复测记录"
```

### 4.6 Documentation Review Checklist

```yaml
checklist_documentation:
  content:
    - item: "完整性"
      severity: "MAJOR"
      verify: "所有章节按模板要求填写"
      
    - item: "一致性"
      severity: "MAJOR"
      verify: "术语、单位、版本号全文一致"
      
    - item: "可追溯性"
      severity: "MAJOR"
      verify: "所有需求可追溯到源文档"
      
    - item: "图表质量"
      severity: "MINOR"
      verify: "清晰、有标题、有标注"
      
    - item: "版本控制"
      severity: "MAJOR"
      verify: "版本号、修改记录、审批链"
```

---

## 5. Finding Severity Classification

### 5.1 Severity Definitions

| Severity | Definition | Resolution Required | Timeline |
|----------|-----------|---------------------|----------|
| **BLOCKER** | 阻止交付物进入下一阶段的缺陷 | 必须修复 | 立即 |
| **MAJOR** | 显著影响质量或可用性的缺陷 | 必须修复 | 当前迭代 |
| **MINOR** | 轻微问题，不影响核心功能 | 建议修复 | 可延期 |
| **INFO** | 信息性建议，供参考 | 无需修复 | N/A |

### 5.2 Severity Assignment Guidelines

```yaml
severity_guidelines:
  BLOCKER:
    conditions:
      - "安全问题"
      - "法规合规问题"
      - "关键功能无法实现"
      - "数据损坏风险"
      - "会导致硬件损坏的设计"
      - "缺少法规要求的认证/测试"
    examples:
      - "电源缺少过压保护 → 可能损坏设备或危及用户"
      - "定点滤波器无溢出保护 → 会产生爆音"
      - "PCB安全距离不足 → 绝缘击穿风险"
      
  MAJOR:
    conditions:
      - "显著影响性能或可靠性"
      - "可能导致量产问题"
      - "缺少关键分析或验证"
      - "与需求规格偏离"
      - "跨域不一致"
    examples:
      - "缺少热仿真 → 可能过热"
      - "FEM未验证收敛 → 结果不可靠"
      - "测试覆盖不完整 → 可能漏测"
      
  MINOR:
    conditions:
      - "可改进但不影响功能"
      - "文档或格式问题"
      - "建议性的优化"
    examples:
      - "图表标题缺失"
      - "命名不够清晰"
      - "可以简化的地方"
      
  INFO:
    conditions:
      - "仅供参考的信息"
      - "好的实践建议"
      - "背景知识补充"
    examples:
      - "相关论文推荐"
      - "替代方案参考"
      - "性能优化技巧"
```

---

## 6. CTO Escalation Format

```yaml
cto_escalation_format:
  header:
    escalation_id: "ESC-CRITIC-{timestamp}-{seq}"
    from: "critic-agent"
    to: "human-cto"
    trigger: "SAFETY|REGULATORY|3X_FAILURE|SYSTEMIC|CONFLICT"
    priority: "P0_CRITICAL"
    
  body:
    finding_summary:
      what: "What was found"
      why_critical: "Why this requires CTO attention"
      affected_scope: "What parts of the project are impacted"
      
    technical_details:
      deliverable_id: ""
      agent: ""
      domain: ""
      finding_ids: []
      full_description: ""
      evidence: ""
      
    impact_assessment:
      schedule: "Impact on timeline"
      quality: "Impact on final product quality"
      cost: "Impact on budget"
      risk: "Additional risks introduced"
      
    options:
      - option: "A"
        description: ""
        pros: []
        cons: []
        
      - option: "B"
        description: ""
        pros: []
        cons: []
        
    critic_recommendation:
      recommended_option: ""
      rationale: ""
      confidence: ""
      
  attachments:
    - "Full review report"
    - "Deliverable under review"
    - "Relevant standards/references"
    - "Historical context (if applicable)"
```

---

## 7. Feedback Loop Mechanism

### 7.1 Review → Revision → Re-Review Cycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Critic     │────►│ Domain Agent │────►│   Critic     │
│   Review     │     │  Revision    │     │  Re-Review   │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                        │
       │         Cycle Tracking                 │
       ▼                                        ▼
┌──────────────────────────────────────────────────────┐
│  Cycle 1: Full review (all checklists)               │
│  Cycle 2: Delta review (changed items + previous     │
│           BLOCKER/MAJOR items)                       │
│  Cycle 3+: Delta review + trend analysis             │
│  After 3 cycles: Escalate to CTO                     │
└──────────────────────────────────────────────────────┘
```

### 7.2 Revision Review Protocol

```yaml
revision_review:
  on_first_revision:
    scope: "full"                    # Full re-review
    focus: "All previous findings + any changes"
    
  on_subsequent_revision:
    scope: "delta"                   # Delta review
    focus:
      - "All changed sections"
      - "All previously flagged BLOCKER/MAJOR items"
      - "Any new content added"
    
  cycle_limit:
    max_cycles: 3
    on_exceed: "Escalate to CTO with full history"
    
  trend_analysis:
    track:
      - "Resolution rate per severity"
      - "New findings per cycle (should decrease)"
      - "Time per review cycle"
    alert: "If new findings increase cycle-over-cycle → quality concern"
```

### 7.3 Agent Feedback Quality Tracking

```yaml
agent_feedback_tracking:
  per_agent:
    first_pass_rate: "Percentage of deliverables passing on first try"
    avg_revision_cycles: "Average number of review cycles"
    finding_resolution_rate: "Percentage of findings properly addressed"
    recurring_finding_types: "Types of findings that repeat across submissions"
    
  use_for:
    - "Identify agents needing coaching"
    - "Adjust review depth (known good agents → lighter review)"
    - "Update error pattern database"
    - "Report to PM for team improvement"
```

---

## 8. Review History Tracking

### 8.1 Review Record Format

```yaml
review_record:
  review_id: "REV-{deliverable_id}-{seq}"
  timestamp: "ISO8601"
  deliverable:
    id: ""
    task_id: ""
    domain: ""
    agent: ""
    version: 1        # Incremented per revision
  
  reviewer: "critic-agent"
  duration_minutes: 0
  review_depth: "full|delta|spot"
  
  verdict:
    status: "PASSED|PASSED_WITH_MINOR|FAILED|ESCALATED"
    findings_count: { BLOCKER: 0, MAJOR: 0, MINOR: 0, INFO: 0 }
    
  findings: []
  
  cycle_info:
    cycle_number: 1
    previous_cycles: []
    
  cross_domain_checks:
    checked: true|false
    consistency: "PASS|FAIL|N/A"
    
  assumptions_challenged: []
  
  lessons:
    - "What Critic learned from this review"
    - "New patterns identified"
```

### 8.2 Review Analytics

```yaml
review_analytics:
  updated: "after each review"
  
  metrics:
    overall:
      total_reviews: 0
      pass_rate_pct: 0.0
      avg_review_time_minutes: 0.0
      avg_findings_per_review: 0.0
      
    by_domain:
      domain: ""
      reviews: 0
      pass_rate: 0.0
      avg_findings: 0.0
      top_finding_categories: []
      
    by_agent:
      agent: ""
      reviews: 0
      first_pass_rate: 0.0
      avg_cycles: 0.0
      common_issues: []
      
    by_severity_trend:
      # Time series of finding severity distribution
      # Used to detect quality trends
      
    reviewer_performance:
      # Critic's own performance metrics
      false_positive_rate: 0.0    # Findings later deemed OK
      escaped_defect_rate: 0.0     # Issues found after Critic PASS
      avg_turnaround_time: 0.0
```

---

## 9. Cross-Domain Consistency Verification

```yaml
cross_domain_verification:
  description: "Verify that deliverables from different domains are mutually consistent"
  
  interface_checks:
    acoustics_dsp:
      - "声学目标曲线频率点数 = DSP EQ频段数"
      - "声学容差范围 ⊂ DSP可实现精度"
      - "采样率一致性"
      
    acoustics_structure:
      - "声学腔体体积 = 结构内腔体积"
      - "出声孔尺寸一致"
      - "密封要求一致"
      
    dsp_hardware:
      - "DSP MIPS需求 ≤ 处理器能力"
      - "数据接口定义一致（I2S/TDM/SPDIF）"
      - "时钟频率一致"
      - "供电电压一致"
      
    hardware_structure:
      - "PCB外形尺寸 ⊂ 结构空间"
      - "连接器位置匹配"
      - "散热路径一致（热源→散热器→外壳）"
      - "螺丝孔位匹配"
      
    structure_test:
      - "测试治具接口匹配"
      - "声学测试密封方式匹配"
      
  verification_method:
    - "Extract key parameters from each domain deliverable"
    - "Compare interface parameters against ICD"
    - "Flag any mismatch as CROSS_DOMAIN_INCONSISTENCY"
    - "Severity: BLOCKER if prevents integration, MAJOR if requires rework"
```

---

## 10. Self-Improvement Loop

```yaml
self_improvement:
  after_each_review:
    - "Record review details in memory"
    - "Update domain-specific error pattern statistics"
    - "Check if any finding was a false positive → adjust if needed"
    
  after_escalation:
    - "Review CTO's decision vs Critic's recommendation"
    - "If different → analyze why → update decision framework"
    
  after_escaped_defect:
    - "Defect found after Critic PASS"
    - "Root cause: Why did Critic miss it?"
    - "Update checklist to prevent recurrence"
    
  periodic:
    - "Weekly: Review finding trends"
    - "Sprint: Update checklists based on new patterns"
    - "Project: Full calibration of severity assignment"
```

---

## 11. 数字来源分级强制检查（POLICY-PROV-001）— 每次评审必查，BLOCKER 级门禁

> 制度全文见 `sprint2/docs/POLICY-PROV-001_数字来源分级制度.md`。缘起：DOC-AUDIT-SIM-001 的 PF-1——算力裕量 27×/49× 是 L3 纸面解析值，却 LOCKED 了芯片选型并触发不可逆采购。本节是 Critic 的强制执行项，**优先级高于其他 checklist，任何评审先过这关**。

### 11.1 五级来源（判定锚点；v1.2 增 L0）
- **L0 目测**（v1.2 新增，缘起 PF-8）：目测/视觉估算/拍脑袋，**无任何测量或工具支撑**（连 datasheet 标称都没有）；可信度最低，**比 L4 更严**。**严禁任何 LOCKED 决策**（含强约束/几何锁定），只许出现在探索讨论且不得进 decisions_log；入设计输入须先升级 L1。例：视觉估测 d=30mm（PF-8 病根）。违者 → C6 BLOCKER。
- **L1 实测**：真实硬件/样品/环境测得，有原始数据（EZKIT 实测 MCPS、消声室 BW、DATS 实测 T/S）。
- **L2 仿真**：经验证工具算得（MATLAB BW、scipy 验滤波器组、树形 C host 重建）。
- **L3 解析估算**：公式/手算/理论模型，含简化假设（MMAC 解析预算）。
- **L4 占位假设**：行业参考/拍脑袋/未验证（占位 T/S BL、假设功率、拍脑袋修正）。
- 混合来源定级：低等级成分**实质决定结果**（作乘数/主导项）→ 整体按最弱（如 SPL=解析增益+占位灵敏度 → L4）；低等级成分仅**次要可加项** → 按主导成分定级但标注里点出（如延迟 12.53ms=L3 scipy 群延迟+L4 datasheet DAC 项 → `[L3 含 L4 datasheet 项]`）。
- 边界裁定：**datasheet 标称值=L4/datasheet**（厂商典型、非自测，比拍脑袋可信但非实测，不当 L1）；**经实测标定的仿真=L2+已校准**（不当 L1 用于不可逆决策）；L2 细分「已验证工具」与「含近似」（cosine 代理障板/互耦粗代理属后者，不当 L1）。

### 11.2 强制检查项 C1–C10（每次 review 必须在报告里显式给出结论；v1.2 增 C6，v1.3 增 C7，v1.5 增 C8，v1.6 增 C9，v1.7 增 C10）

```yaml
provenance_mandatory_checks:
  C1_label_present:
    check: "进入 decisions_log/结论表/规格/客户承诺的数字是否标来源等级（L1-L4）？（中间过程量不强制）"
    fail_severity: "BLOCKER"
  C2_no_overclaim:
    check: "有无 L2/L3/L4 被措辞成'实测/measured'？（红线词限'实测/measured'；'确认/已验证'仅在修饰数字可信度时触发，不误伤'CTO 确认决策'类用法）"
    fail_severity: "BLOCKER"
  C3_no_L4_irreversible:
    check: "有无 L4 占位值作不可逆决策（采购/选型/流片/客户承诺）的唯一依据？（含被伪装降档的不可逆决策）"
    fail_severity: "BLOCKER"
  C4_L3_needs_pending_tag:
    check: "有无 L3 解析支撑'强约束决策'（档位以 §11.3 为准，不用'难逆'）但未挂'待 L1/L2 验证'标记？"
    fail_severity: "MAJOR"
  C5_traceable:
    check: "数据出处是否可追溯（文件/脚本/实测记录）？（v1.5 扩）另查：进入不可逆/强约束决策的关键决策数字是否经第二独立工具交叉核（铁律七）？"
    fail_severity: "MAJOR"
  C6_geometry_gate_and_conflict_review:   # v1.2 新增，缘起 PF-8
    check: "几何/物理尺寸参数（阵元间距/孔径/外形/装配定位）LOCKED 前是否有 L1 实测证据？（以 L0 目测/L3 估算作几何 LOCKED 依据=违规）；另查：有无 L1 实测与已 LOCKED 决策冲突却未触发强制重审、反以'并存/折衷'掩盖（铁律四）？"
    fail_severity: "BLOCKER"
  C7_retraction_propagation:   # v1.3 新增，缘起 PF-9，撤回传播门禁
    check: "任何数字被撤回时，是否已对其全部引用（含派生值/反推值/别名）做全库反向清扫——逐处确认'已加撤回警示标签 或 已删除'？清扫未完成前撤回声明不生效。执行：取被撤回数字字面值 + 派生/反推/别名 → 全库 grep（含 full_teardown* / sprint*_status.md / decisions_log / 对外交付物）→ 对每处命中判定'已加标 / 已删除 / 残留未处理(FAIL)'；任一处残留 → 撤回视为无效，不得宣称'已撤回/已修正'。"
    fail_severity: "BLOCKER"
  C8_ingest_propagation:   # v1.5 新增，缘起 LESSON-013，入库传播门禁（入站，与 C7 出站对偶）
    check: "Sprint 收尾归档时，是否复核'近 1 周内 CTO 外部接收的入库状态'？以 CTO 外部接收声明清单（POLICY §4A.2，时间/来源/文档/入库日/是否超24h/备注）为唯一权威基线，逐份判定'已及时入库 / 超时入库 / 未入库(FAIL)'。无 CTO 声明 → 基线缺失 → ESCALATE。C7（撤回/出站）+ C8（入库/入站）= 双向传播门禁。"
    fail_severity: "BLOCKER（超 24h/未入库）；无声明基线 → ESCALATE"
  C9_fira_offload_irreversible_gate:   # v1.6 新增，缘起 R14（FIRA 定点 bit-exact 风险），CTO 拍板 2026-06-02
    check: |
      在 R14 关闭（EZKIT bit-exact L1 实测通过）前，对任何含 FIRA/算力收益/选型/流片/客户承诺的产出做四查：
      ① R14 是否含 R-list 全部强制字段（编号/风险/等级/验证状态/数据出处/可逆性影响/风险声明/挂接）？缺 → BLOCKER
      ② 有无把"FIRA offload 算力收益"计入选型/流片/客户承诺依据，且 R14 未关闭？有 → BLOCKER
         （收益须标"上板后优化、收益未实测 [L4/待验证]、不计入依据"；选型/承诺只许引纯核裕量）
      ③ Split-Task 迁移复杂度是否已进 Sprint 4 输入清单（DOC-S4-INPUT-01）并标 HIGH（手动切分+bit-exact 回归）？未 → MAJOR
      ④ R14 / Split-Task 结论是否可追溯到 fira_fit_assessment.md（第2/3/5项）？不可 → MAJOR
    fail_severity: "①② BLOCKER；③④ MAJOR"
    positive_negative_example: "见 [[critic-memory]] LESSON-014（措辞红线正反示例：纯核裕量可引 / FIRA 收益须标[L4/待验证]不计入）"
  C10_hw_irreversible_action_gate:   # v1.7 新增，缘起 EZKIT 上板厂商三陷阱（boot抢JTAG/JTAG热插拔烧板/供电跳线接错），CTO 拍板 2026-06-02
    check: |
      涉物理硬件不可逆动作（上电/接仿真器ICE-1000/焊接/跳线）的指导，发出前三查：
      ① 是否已有经 CTO 确认出稿的操作清单（如 ezkit_bringup_checklist.md）？无 → BLOCKER（禁在清单出稿前指导上电/接 ICE-1000）
      ② 板卡物理版本/配置是否已由 CTO 肉眼确认（丝印 REV）？未确认却预设单一版本接线 → BLOCKER（须先列全版本差异，确认后才标专属接线）
      ③ 安全硬规矩（JTAG 连接顺序「先插JTAG→板上电→仿真器接USB」/ 禁热插拔 / 供电跳线核对）是否明确写入清单？未 → BLOCKER（安全项）
    fail_severity: "BLOCKER（硬件不可逆损失风险）"
```

### 11.3 决策权重红线（据可逆性）
- **不可逆决策**（采购/选型/流片/客户承诺）：须 **L1**，或 **L2 + 风险声明 + 总工签字**；**L3/L4 不得作唯一依据**。
- **强约束决策**（算法锁定/规格冻结）：L2 起；L3 须挂"待验证"。
- **方向性决策**（选型对比/参数初选）：L3 可用。
- **探索讨论**：L4 可用，但不得直接进 decisions_log。
- **🔒 可逆性升级原则（防伪装降档）**：决策档位不得自我降档规避等级要求；凡涉采购下单/流片/对客户书面承诺**一律按不可逆**处理，不得自称"方向性/初选"降门槛；归类有争议时**从严**（按更不可逆一档）。"L2+签字"豁免须把签字（人+日期+理由）记入该 DEC「验证状态」字段，否则豁免无效、按 C3 BLOCKER。

### 11.4 执行要求（v1.7：C1–C10）
1. 任何评审报告必须含一节「来源分级检查 C1–C10」，逐项给 PASS/FAIL + 证据。**报告头必须带 `reviewer: critic @ <精确 model ID> / <日期>` 标记**（Step-3 审计 2026-06-04 起生效，对齐 C5 可追溯、进审计链；无标记的裁定退回重发。换模型走 `.claude/team_config.md` 变更留痕）。
2. **C1/C2/C3/C6/C7/C8/C9①②/C10 任一 FAIL → 整体 BLOCKER**，交付物打回，不得进入下一阶段。
3. 评审引用 decisions_log 条目时，核对第 5 部分 6 字段（依据数字/来源等级/数据出处/可逆性/验证状态/风险声明）是否齐全；缺项按 C1/C5 判级。
4. **铁律四（v1.2，缘起 PF-8）**：发现 L1 实测与已 LOCKED 决策冲突 → 强制触发该决策重审、禁"并存"折衷、立即上报 PM+CTO；几何尺寸 LOCKED 必须 L1（C6）。
5. **铁律五（v1.3，缘起 PF-9）——撤回必须全库传播，三步缺一不可**：任何数字被撤回 = ① 发出撤回声明 + ② 全库反向扫描该数字及其派生值/别名所有引用 + ③ 逐处加撤回警示标签或删除；三步未全做完撤回不生效，不得宣称"已撤回/已修正"，由 C7 守门（残留 ≥1 处未处理 = BLOCKER）。C6 防进（入口门禁）、C7 防赖着不走（出口门禁）。
6. **铁律六（v1.5，缘起 LESSON-013）——信息透明义务/外部输入 24h 入库（守入站，对偶铁律五守出站）**：凡 CTO 收到的外部技术输入须 24h 内进 KB + handover（CTO→PM→KB），由 C8 守门；**CTO 外部接收声明义务**：CTO 须在 Sprint 收尾主动声明近 1 周外部接收清单（格式规范化：时间/来源/文档/入库日/是否超24h/备注），作为 C8 唯一权威核对基线，无声明 → C8 基线缺失 → ESCALATE。
7. **铁律七（v1.5，缘起 LESSON-012 M1 WNG 12dB bug）——关键数字双轨独立工具核**：进不可逆/强约束决策的关键几何/算力/统计/标准合规数字须第二独立工具（如 MATLAB）交叉核，不一致 → 定位错源 BLOCKER，定位修复前不得落盘（由 C5 扩守门，未交叉核 = MAJOR）。
8. **铁律八（v1.6，缘起 R14 FIRA 定点 bit-exact 风险，CTO 拍板 2026-06-02）——加速器收益不可逆闸门**：凡"上板后才能实测的加速器/优化收益"（FIRA offload 算力等），在对应风险项（R14）以 L1 实测关闭前，**一律标 [L4/待验证]、不得计入任何选型/流片/客户承诺依据**；选型/承诺只许引已坐实的纯核口径。违反 → BLOCKER（由 C9①② 守门）。HIGH 级迁移复杂度（Split-Task 等）须进 Sprint 4 输入清单并标级（C9③）。
9. **铁律九（v1.7，缘起 EZKIT 上板厂商三陷阱：boot 抢 JTAG / JTAG 热插拔烧板 / 供电跳线接错，CTO 拍板 2026-06-02）——硬件不可逆动作闸门**：涉上电/接仿真器/焊接/跳线等不可逆硬件动作，须先有①经 CTO 确认出稿的操作清单（如 `ezkit_bringup_checklist.md`）+ ②物理版本/配置肉眼确认（丝印 REV，禁预设单一版本接线）+ ③安全硬规矩（连接顺序「先插JTAG→板上电→仿真器接USB」/禁热插拔/供电跳线核对）写入清单；三者缺一不得指导执行（C10 守门，BLOCKER）。防"接错线烧板/找错跳线连不上"（PF-9 版本误判同类）。
10. 关联教训：[[critic-memory]] LESSON-007（分级制度）、LESSON-008（AC-WP01 半角"实测"误称）、LESSON-006（反推让位实测）、**LESSON-009（PF-8 估测当实测 + 冲突未重审 → L0/铁律四/C6）**、**LESSON-010（PF-9 撤回未传播 → 铁律五/C7）**、**LESSON-012（M1 WNG 12dB bug 三轨抓出 → 铁律七双轨核/C5 扩）**、**LESSON-013（docx 入手未入库 → 铁律六/C8/CTO 外部接收声明义务）**、**LESSON-014（FIRA offload 收益未实测不得计入选型 → 铁律八/C9，含措辞红线正反示例）**。

---

## 12. DSP/FIRA 验证专项门（v1.8 新增，缘起 R14 假绿 + D1/D2 I/O 契约，2026-06-03）

> 适用：任何 DSP/FIRA 的 bit-exact 测试 / 诊断 / 补丁，**上板或上报前必查**。缘起本线两次连漏——① 端到端 telescoping 假绿（占位 FIRA 仍 PASS）；② FIRA I/O 缓冲契约垃圾（过读未初始化 + 双重抽取半填）——两次均由 CTO 兜住、非 critic/门禁拦下。这五条把那两次教训固化成门，与 C1–C10 并列执行。挂 [[critic-memory]] LESSON-015。
>
> **§12 实战记录（2026-06-04 板上 PASS 闭环）**：本节生效后六轮独立 critic 拦截（D1b 输入计数 / M2 哨兵自掩盖 / INT 历史域 / A5 flush-back / A5 符号 / DEC 抽取相位 + 否决 PM"FIRA MAC 不同"过度结论），全部在上板前；终局 FIRA 单通道子带 bit-exact L1 板上达成（commit 9d9fbec，R14 主门仍 OPEN）。全记录：`sprint4/dsp/fira/F4_BITEXACT_HANDOFF.md`。

- **FG1 假绿（恒等盲区）— BLOCKER**：测试是否**真依赖被测物**？若 `out == in` 由代数恒等成立（完美重建 telescoping / PR），端到端 CRC 只验算术+恒等、**验不了滤波/加速器段**。要求：(a) 比对目标取依赖被测物的中间值（如子带 sb0-3，非端到端输出）；(b) **必须证明占位/置零版会 FAIL**。未证 → BLOCKER。（R14 假绿病根；与 §11.2 C2/C3 联动）
- **FG2 占位冒充实测 — BLOCKER**：compute 被 stub（`memset 0` / `#else` / 未接线）时测试是否**仍能 PASS**？能 = L4 占位冒充 L1 实测。要求：**跑占位版、确认其 FAIL**，否则该测试作废。（C3 同源：占位作"实测 PASS"依据）
- **IO1 加速器 I/O 缓冲契约 — BLOCKER**：每个 HW（FIRA）段查四点：(a) 输入 buffer 持有 **≥ `nInputBuffCount (= ntaps+window-1)` 个已初始化样本**？（防过读进未初始化/外部内存 = D1）；(b) 后处理**恰填 `out_count` 个样本**？（防双重抽取半填、留未初始化尾 = D2）；(c) 共用 scratch **段间清零**？（防读上一段残留）；(d) DMA 输出**读前 cache 失效**？任一不满足 → BLOCKER。
- **IO2 布局敏感 = 读未初始化/越界 — BLOCKER**：compute 代码未改、**只改无关全局/链接布局，输出却变** ⇒ 在读未初始化/越界/stale 内存。隔离法：哨兵 A/B（scratch 填 `0x00` 跑一次、填 `0xFF` 跑一次，输出变即坐实）。坐实/隔离前 → BLOCKER。
- **ST1 流式状态一致 — MAJOR/BLOCKER**：有状态流式滤波（核逐帧延迟线）vs 无状态块加速器调用——加速器路径**是否保持跨帧滤波状态**？不保持则每帧前 ~ntaps 个输出无法对齐有状态 golden。按对 bit-exact 判据的影响判 MAJOR 或 BLOCKER。
- **ST1-E 跨态/跨消费者枚举 — MAJOR**：当 reviewer 裁某状态/异常「对 X 无害」时，**必须枚举该状态/异常的
  ALL 消费者**（所有跨 span 共享的可变态 × 所有读它的 probe/计数器/CRC），**逐项裁**，不得只裁 X 一处。
  缘起 R14→R15：H1 的 s_h1_fa 跨帧态被三个 probe（focus/nofocus/identity）以**不同推进态**消费，
  原审只看 focus_differs(对) 未枚举 zero_recovers(被同态不对称坑) → 假 FG FAIL。漏枚举=MAJOR。

**§12 红线**：**FG1 / FG2 / IO1 / IO2 任一 FAIL ⇒ 该 DSP/FIRA「bit-exact PASS」主张作废，BLOCKER。**

---

*Critic Agent Skill v1.0.0 — The Complete Quality Assurance Arsenal*
*v1.1 增补：§11 数字来源分级强制检查（POLICY-PROV-001），BLOCKER 级门禁*
*v1.3 增补：§11.2 C7 撤回传播门禁 + §11.4 铁律五（撤回三步：声明+全库反扫+逐处加标/删），缘起 PF-9*
*v1.5 增补：§11.2 C8 入库传播门禁（入站，对偶 C7 出站）+ C5 扩（关键决策数字第二独立工具交叉核）+ §11.4 铁律六（外部输入 24h 入库 + CTO 外部接收声明义务）/铁律七（双轨独立工具核）+ LESSON-012/013；C1–C7→C1–C8，缘起 LESSON-012（M1 WNG 12dB bug）+ LESSON-013（docx 入手未入库）*
*v1.6 增补：§11.2 C9 FIRA-offload 不可逆闸门（R14 关闭前加速器收益不得计入选型/承诺依据，①②BLOCKER/③④MAJOR）+ §11.4 铁律八（加速器收益不可逆闸门）+ LESSON-014（含措辞红线正反示例）；C1–C8→C1–C9，缘起 R14（FIRA 定点 bit-exact 风险，CTO 拍板 2026-06-02）*
*v1.7 增补：§11.2 C10 硬件不可逆动作闸门（上电/接仿真器前须有经 CTO 确认的操作清单+物理版本确认+安全硬规矩，BLOCKER）+ §11.4 铁律九；C1–C9→C1–C10，缘起 EZKIT 上板厂商三陷阱（boot抢JTAG/JTAG热插拔烧板/供电跳线接错），CTO 拍板 2026-06-02*
*v1.8 增补：§12 DSP/FIRA 验证专项门（FG1 假绿恒等盲区 / FG2 占位冒充实测 / IO1 加速器 I/O 缓冲契约 / IO2 布局敏感 / ST1 流式状态；FG1/FG2/IO1/IO2 任一 FAIL=BLOCKER）+ LESSON-015；缘起 R14 端到端假绿 + FIRA D1/D2 I/O 契约垃圾，2026-06-03*
