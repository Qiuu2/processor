# 生成提示词（在新项目里粘贴给 Claude Code）
> 用法：把整个 `ee-agent-team-starter/` 放进新项目仓库，在新项目里打开 Claude Code，粘贴下面这段。

---

你是新项目「硬件电子工程师多-Agent 系统」的架构师。仓库里有一个
`ee-agent-team-starter/`，是从一个音频硬件研发项目提炼的、经实战打磨的框架 + 治理。
请把【框架+治理】原样继承、把领域落到电子/PCB/EDA 工程，生成一套全新配置。

先读这些：
- `00_governance/GOVERNANCE_EE.md`（**治理底座，原样加载**：L0-L4 分级 / 铁律 / C1-C8 门 / 三道关 / 不可逆-L1 清单 / 假绿纪律）
- `00_governance/LESSONS_SEED.md`（元教训，种进各 agent 的 soul/memory）
- `ROSTER_EE.md`（角色清单 / DAG / L 分级 EE 校准 / critic §4 域清单骨架）
- `01_architecture/SKILL_ITC_reference.md`（架构/协议/状态机/DAG 骨架——学结构，别抄音频域举例）
- `01_architecture/team_config_ITC_reference.md`（角色-模型表 / commit 纪律 / 变更审计 模板）
- `02_agent_templates/*`（project-manager / critic / structure / testing 四件套模板——
  structure≈机械, testing≈Bring-up 可大量复用；其余当「专家 agent 长什么样」的样例）

【原样继承（只改举例，别改规则）】
1. GOVERNANCE_EE.md 全套（分级/铁律/C门/三道关/不可逆-L1/假绿纪律）
2. 放行纪律：独立 critic verdict 前不 release/出图；in-context 自审不算门；修正稿同等过门
3. 总控编排是唯一对人汇报节点；critic 横切、可直接 rebut 任何 agent
4. 四件套解剖：profile(身份/职责/接口) / soul(价值观/行为/反模式，种 LESSONS_SEED)
   / skill(方法/清单) / memory(**从空开始**，只放一句「新项目，从空累积」+ 元教训链接)

【按 EE 域重写】
- critic 的 skill.md §4 域清单 + 专项门：按 ROSTER_EE §4 骨架重写（ERC/DRC/IPC-7351/
  热·EMC/单一货源/合规/跨文档矛盾/测试缺口/假绿）
- 各专家 skill.md：填该域真实方法与检查项（原理图/BOM 选型/DFM 工艺/…）
- team_config 角色-模型表：用 ROSTER_EE §1 的 9 个角色
- 「不可逆→L1」触发清单：用 GOVERNANCE_EE §2（Gerber/打样/采购/BOM冻结/EVT-DVT-PVT）

【生成角色（按架构图）】
编排：orchestrator（总控编排）
专家：requirements-arch / schematic / bom-sourcing / dfm-process / mechanical /
     bringup-test / doc-governance
横切：critic
基础设施（非 agent，写「接入契约」文档而非四件套）：共享服务层(RAG+知识图谱/元件BOM主
数据·EOL/工件库溯源) + EDA 适配层(Altium/PADS/AutoCAD/CorelDRAW 的 MCP桥+脚本+
导出BOM/网表/Gerber/DXF)。契约核心：工具跑了≠跑对了，产出须回验。

【产出顺序】
先只给我：① 角色清单 + 每角色一句定位 ② DAG 依赖草图 ③ L 分级 EE 校准表
（让我确认）——**别一口气生成 9×4 个文件**。我确认后，你再逐个展开
CLAUDE.md / SKILL.md / .claude/team_config.md / 各 agents/<role>/{profile,soul,skill,memory}.md 全文。
