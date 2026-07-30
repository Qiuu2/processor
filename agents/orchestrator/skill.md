# orchestrator — Skill(薄骨架 v0.1)

## A. 项目真本事(蒸馏区)
(空)本项目未跑,无真料待蒸馏。真本事按 Playbook Part 2 蒸馏 SOP 长入(miner→CTO 核→A/B/C→独立 critic→commit),一个 skill 一条 DEC。

## B. 通用骨架(非本项目蒸馏,Claude 通识;使用前结合本项目校验)
- **WBS 分解**:项目→阶段→工作包→任务;每任务唯一 owner、明确交付物+验收判据、超一个工作日粒度即拆;任务依赖显式进 DAG,禁环。
- **派单 prompt 模板要素**:①背景+引用(DEC/假设/上游产出路径) ②交付物定义+验收判据 ③硬顺序(实现→自验→critic→verdict→commit) ④L 标要求 ⑤涉不可逆项的 C9/C10 提醒 ⑥截止/优先级。
- **门禁执行**:REVIEW 态只认带 reviewer 头的独立 verdict;PASSED+不可逆项→CTO 门;FAILED→打回并在新派单中列 findings 编号。
- **风险登记**:每 sprint 维护 R-list(编号/风险/等级/验证状态/出处/可逆性影响/风险声明/挂接工单)。
- **handoff 纪律**:teammate 不跨会话持久;交底包=角色四件套+当前工单+相关 DEC+上轮 verdict。
- **并发让位规则(≤4 硬限,F-10)**:优先级 critic 评审 > 不可逆门相关工单 > 关键路径工单 > 其他;域专家无活跃工单即休眠让位(respawn+handoff 交底成本计入排期);双 DSP 并行期 architect 无单则先休眠。

## C. 缺口(要用先补真料)
- 本项目真实 sprint 节奏/工时基线:无(禁编造估时)。
- 真实派单-评审-返工循环数据:待第一个 sprint 累积。
