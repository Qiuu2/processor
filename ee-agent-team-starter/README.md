# EE Agent Team Starter Kit
> 从一个音频硬件研发多-Agent 项目提炼的**框架 + 治理精华**，用来在新项目
> 「硬件电子工程师多-Agent 系统」里快速起一套 agent team 配置。

## 这是什么 / 怎么用（两步）
1. 把**整个 `ee-agent-team-starter/` 文件夹**拷进新项目仓库根目录。
2. 在新项目里打开 Claude Code，把 `GENERATION_PROMPT.md` 的内容**粘贴进去**。
   那个 Claude 会读本 kit → 先给你「角色清单+DAG+L分级表」确认 → 再展开生成
   CLAUDE.md / SKILL.md / team_config.md / 各 agent 四件套。

> 简言之：**本 kit 是「喂给新项目 Claude 的学习材料 + 生成指令」**，不是最终配置本身。
> 最终的 EE 配置文件由新项目的 Claude 在新仓库里、结合真实上下文生成（并从空开始记忆）。

## 文件清单
| 文件 | 性质 | 用途 |
|---|---|---|
| `GENERATION_PROMPT.md` | ⭐**先用这个** | 粘贴给新项目 Claude 的生成指令 |
| `00_governance/GOVERNANCE_EE.md` | ⭐**原样加载** | 治理底座：L0-L4/铁律/C1-C8门/三道关/不可逆-L1/假绿纪律（EE版） |
| `00_governance/LESSONS_SEED.md` | 原样种入 | 域无关元教训（带触发器），种进各 agent soul/memory |
| `ROSTER_EE.md` | 起点蓝图 | 9 角色 + DAG + L分级EE校准 + critic §4 域清单骨架 |
| `00_governance/POLICY-PROV-001_ITC_reference.md` | 深度参考 | 治理原文（音频域），要更细节时查 |
| `01_architecture/SKILL_ITC_reference.md` | 骨架参考 | 四层+一横切架构/协议/状态机/DAG（学结构，别抄音频举例） |
| `01_architecture/team_config_ITC_reference.md` | 骨架参考 | 角色-模型表/commit纪律/变更审计 模板 |
| `02_agent_templates/project-manager/*` | 高复用模板 | 编排 agent 四件套（80% 可用） |
| `02_agent_templates/critic/*` | 高复用模板 | critic 四件套（§1-3,5-11 留；**§4/§12 换 EE**） |
| `02_agent_templates/structure/*` | 可复用模板 | ≈ 机械/结构 agent |
| `02_agent_templates/testing/*` | 可复用模板 | ≈ Bring-up·测试 agent（带假绿纪律） |

## 带走 / 丢弃 的分界
- 🟢 **带走（域无关精华）**：治理（L分级/门/三道关/不可逆-L1/假绿纪律）、四层架构、
  四件套解剖、critic 方法论、元教训、commit/放行纪律。
- 🔴 **丢弃/重写（音频项目特定）**：所有 `memory.md` 累积内容（**本 kit 已不含**，防污染）、
  声学/DSP/FIRA 域方法、critic 的声学/DSP 清单、具体 sprint/decisions。

## 三条必须守住的红线（否则精华就丢了）
1. **GOVERNANCE_EE.md 原样加载**——分级、门、三道关是这套的真金，别精简。
2. **独立 critic 是硬门**，agent 自审不算；修正稿同等过门；不可逆动作前 L1+人审签字。
3. **确定性验证器（ERC/DRC/IPC）防假绿**——必须证明它跑在当前真网表/真 layout 上、对 broken 版能 FAIL。

---
*生成：从 itc-enterprise-workflow 提炼，2026-07。memory 一律未随带（防跨项目污染）。*
