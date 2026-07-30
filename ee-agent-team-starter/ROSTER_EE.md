# EE 团队名册 + DAG + L 分级校准（新项目起点）
> 按你的架构图预映射。新 Claude 展开各 agent 四件套时以此为准。

## 1. 角色清单（编排 1 + 阶段专家 7 + 横切 critic 1）
| 层 | role（建议 id） | 一句定位 | 模型建议 |
|---|---|---|---|
| 编排 | `orchestrator`（总控编排） | 规划/WBS/DAG、NPI 门禁、全程溯源；唯一对人汇报节点 | 最强档 |
| 专家 | `requirements-arch`（需求·架构） | 需求→架构分解、供电/时钟/接口拓扑、指标预算 | 中高 |
| 专家 | `schematic`（原理图） | 原理图设计、内含 ERC、网络/供电完整性 | 中高 |
| 专家 | `bom-sourcing`（BOM·选型·成本） | 选型/BOM/成本/EOL/单一货源、供应商实价实期 | 中 |
| 专家 | `dfm-process`（DFM·工艺） | DFM/DFA、内含 DRC + IPC-7351 焊盘/工艺规则 | 中 |
| 专家 | `mechanical`（机械/结构） | 结构/外壳/装配/干涉、DXF 交换 ← 复用 ITC structure | 中 |
| 专家 | `bringup-test`（Bring-up·测试） | 上电/测试用例/EVT-DVT-PVT、**假绿纪律** ← 复用 ITC testing | 中高 |
| 专家 | `doc-governance`（版本·文档治理） | 版本/变更/文档一致性/溯源归档 ← 复用 ITC project-document | 中 |
| 横切 | `critic`（对抗查漏） | 红队评审、跨文档矛盾/热EMC余量/单一货源/合规/测试缺口 ← 复用 ITC critic | 最强档（深度最重要） |

**非 agent（是基础设施，写「接入契约」不写四件套）**：
- 共享服务层：知识库 RAG + 知识图谱 / 元件·BOM 主数据·EOL / 共享工件库·溯源
- EDA 适配层：Altium/PADS/AutoCAD/CorelDRAW 的 MCP 桥 + PADS VBScript/Corel VBA 脚本 + 导出流水线（BOM/网表/Gerber/DXF）。**契约核心：工具跑了≠跑对了，产出须回验。**

## 2. DAG 草图（NPI 主干）
```
需求·架构 ─┬─> 原理图 ──> BOM·选型·成本 ─┐
           │      │                        ├─> DFM·工艺 ──> [人审门: Gerber/打样] ──> Bring-up·测试
           └──────┴──> 机械/结构 ──────────┘                                              │
                                                                                          v
   版本·文档治理  贯穿全程          Critic 横切每个交付物（②后、人审门前）        [人审门: EVT/DVT/PVT]
```
- 硬门（实线）：ERC / Gerber 出图 / 打样 / EVT / DVT / PVT，各设一门 = 「不可逆→L1+签字」。
- Critic（虚线，建议性）：在每个专家产出后、人审门前对抗查漏。

## 3. L 分级 EE 校准表（把 GOVERNANCE_EE §1 落到具体产物）
| 产物/数字 | L1 长什么样 | 常见 L4 陷阱（要拦） |
|---|---|---|
| 热余量 | 实测热成像/热电偶 | datasheet θJA typical 直接用 |
| 电流/功耗预算 | 实测/在真网表上 SPICE | 手册 typ 值相加、没算裕量 |
| 时序/SI | 实测眼图/场求解器 | 「应该够」拍脑袋 |
| BOM 成本/货期 | 供应商实报价+日期 | 占位价、去年的价、无日期 |
| DRC/ERC 干净 | 在**当前最终 layout/网表**上 clean | 在空的/旧版/默认规则上 clean（假绿） |
| 元件可供性 | 实时库存/EOL 状态 | 「应该还在产」 |

## 4. Critic §4 域清单骨架（新项目 critic 的 skill.md §4 照此重写）
- **原理图**：ERC 是否在真网表跑、悬空网络/单点电源/去耦缺失/上下拉、供电树完整。
- **BOM/选型**：单一货源、EOL/NRND、封装与库不符、占位价、MOQ/长交期未标风险、每项 L 标。
- **DFM/工艺**：DRC 在最终 layout 跑、IPC-7351 焊盘、间距/环宽/阻焊、拼板/工艺边、可制造性。
- **热/EMC**：余量来源 L 级、回流路径、屏蔽/滤波、认证前置。
- **跨文档矛盾**：原理图↔BOM↔layout↔机械 DXF 一致性（位号/封装/尺寸）。
- **测试缺口**：EVT/DVT/PVT 覆盖、假绿（验证器是否依赖被测物）、可测试性 DFT。
- **每条**给 PASS/FAIL + 证据 + 严重度（BLOCKER/MAJOR/MINOR）。
