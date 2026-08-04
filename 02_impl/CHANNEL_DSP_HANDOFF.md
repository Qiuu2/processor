# channel-dsp 交接件(实例 #2)

```
⛔ 门禁状态:本文件是交接/状态记录,不是交付件,不构成任何放行依据。
   本文件描述的所有产出均为【未过门】。
实例    : channel-dsp 实例 #2 @ claude-opus-5[1m]
上岗    : 2026-08-04
前任    : 实例 #1(2026-08-04 约 13:50 退役,无交接件)
```

## §0 当前在做什么(⭐ 恢复工作先读这一节)

**状态:①② 已完成(含 critic MAJOR-1 与 m-2)。正在做 ③(元检查覆盖 + 接进 run_all.sh)。**

### ⚠ 上岗时校正了 lead 派单里的两处事实(先看这个,免得重做)

| lead 派单说 | 实际 | 影响 |
|---|---|---|
| ②「前任只加了描述问题的注释,没修」 | **`02_impl/test/check_negcompile.sh` 是前任重写的新件,三道修法(A 命中预期错误 / B 前置存活自检 / C STRICT=0 对照臂)全在,实跑 10/10 PASS**。⛔ 但 critic 点名的那一份 —— `01_design/fixedpoint/check_negcompile.sh` —— **原封未动**,且 `run_r3.sh:87` 仍在调它 | BLOCKER 只闭了一半 ⇒ ② 的工作面是 **fixedpoint 那一份** |
| ③ check_gates_fire.sh「接到 run_all.sh 上」 | 该文件**已存在且实跑 5/5 PASS**,但**未接进 `run_all.sh`** | 需补接线 + 补覆盖 |

**基线(上岗当场实跑,2026-08-04 ~13:56)**:`run_all.sh` **exit 0**,六环全过,杀伤矩阵 **16/16 全杀**;`check_gates_fire.sh` **5/5 PASS**。

## §1 任务清单(lead 派单,按优先级)

| # | 事项 | 状态 |
|---|---|---|
| ① | `chdsp_fixed.h:446` 的 `S>1` 残留 + 另外 4 处(h:444 / 约定文档 §0 / 台账 A3 / 台账 F 汇总) | 未开始 |
| ② | `check_negcompile.sh` BLOCKER:`expect_fail` 只问"编译是否失败" | 未开始 |
| ③ | `check_gates_fire.sh` 看懂 + 补全闸门覆盖 + 接到 `run_all.sh` 前置 | 未开始 |
| ④ | 变异自证(进杀伤矩阵前先用探针证明该变异真的改了它声称改的行为) | 未开始 |
| ⑤ | §6.4 全链噪声底(critic MAJOR-2):修数与适用范围,⛔ 不动格式;同步 `d34_chain/d34_analysis.py` EXP-5 与可能的 `check_modules.c` | 未开始 |
| ⑥ | C 第二批(按 `D3D4_CHANNEL_CHAIN_v0.1.md` 链序;⛔ 不碰 NHS/AEC/AGC/automixer) | 未开始 |

## §2 已完成什么(带路径)

(暂无)

## §3 下一步

读完上岗材料 → 从 ① 开始(它影响 ⑥ 要写的代码)。

## §4 我踩过的坑 / 必须知道的

- **纪律**:不 commit(归档由 lead 做)、不 spawn 子 agent、不联系其他 teammate(只报 lead)。
- **critic verdict 没推翻的**:六条格式裁决(Q0.31/Q4.27 · 饱和禁回绕 · RTN 禁截断 · DF1 禁 DF2 · EF 必选 · HPF/LPF 结构约束量化)全部站得住,可继续按它们写 C。§3.2.0 解析界经 critic 用更宽扫描域独立复核成立且紧。
- **闸门判据**:「这个检查失败时,会阻止什么?」答"什么也不阻止" ⇒ 它是输出不是检查。
