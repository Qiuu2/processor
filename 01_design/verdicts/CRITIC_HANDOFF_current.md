# CRITIC 交接件(活文件 · 随进展更新)

> **门禁状态:本文件不是 verdict,不构成任何放行。**
> reviewer: critic @ claude-opus-5[1m] / 2026-08-04
> 实例:critic 第 2 实例(前任 `critic-w1c` 2026-08-04 ~13:50 探活不可达,无交接件)
> 最后更新:2026-08-04 14:2x(第一优先出件后)

## 0. 当前断点(⛔ 恢复工作先读这行)
- **第一优先【已出件】**:`critic_D3D4_CHAIN_v0.1_verdict_20260804.md` = **FAIL**(2B/5M/7m)。已报 lead。
- **第二优先【已出正式件】**:`critic_02impl_r1_verdict_20260804.md` = **FAIL**(1B/5M/4m)。
  版本锁 = **`review/02impl-r1` = `8402198`**(lead 建的冻结点;我在独立 worktree 上评的,没碰作者工作树)。
  中止件 `critic_02impl_INTERIM_20260804.md` 已被它取代(结论一致,正式件更全)。
- **第三优先【已出件】**:`critic_r87_F76-F80_verdict_20260804.md` = **PASS-with-conditions**(0B/1M/2m)。
  四条放行条件全是「写一句话」级,⛔ 不需重跑任何实验。
- **⇒ 三件全部出正式件并已报 lead。**
- **⇒ 下一件 = W1-P 收口件三件(`01_design/W1P_CLOSEOUT/`)** —— lead 排的第 3 项,CTO 要拿它做路线决定。
  ⚠ 它是**合成件**,不含新测量 ⇒ 评审重点 = 它引用的每个数的**限定串有没有在引用时掉光**(D6-t/D6-x),
  而那些数我多半已经审过。**⇒ 要新 tag 时向 lead 要 `-r2`。**

## 1. 评审队列与状态
| # | 标的 | 状态 | verdict |
|---|---|---|---|
| 1 | `D3D4_CHANNEL_CHAIN_v0.1.md` + `d34_chain/` | ✅ **FAIL** | `critic_D3D4_CHAIN_v0.1_verdict_20260804.md` |
| 2 | `02_impl/` C 实现第一批 | ✅ **FAIL** | `critic_02impl_r1_verdict_20260804.md`(锁 `review/02impl-r1`=`8402198`) |
| 3 | r87 收口件 F76–F80 | ✅ **PASS-with-conditions** | `critic_r87_F76-F80_verdict_20260804.md` |

## 1c. 第三优先已坐实的(细节见 verdict)
```
✅ lead 问的那个区分【成立】,我从原始 JSON 独立核(不是读它的报告):
   t05s1 两臂逐字段 diff = 空集;F3_dropped 0→0;r86a 阳性对照独立复现同一格不可达
✅ 负结论强度【对】,而且执行者低估了自己:它把一条本可支持自己结论的数据点主动划掉了
   ⭐ 最强的一点(它没邀功):修法恰恰在【损害发生的那两条种子】上起了作用
      (深度 −15.00→−18.00 / −16.50→−18.00),而 ΔMSG 两条都 δ=0.00 ⇒ D6-ar② 的最强形式
⛔ MAJOR-1(别人没怀疑过的)PREREG_r87b.txt:119 的 Hg3 护栏【符号是反的】
   δ = 修后−基线,ΔMSG 越大越好(我从 JSON 核了方向:m 越大 ⇒ dmsg 越大)
   ⇒ 「δ > +0.354(变差)⇒ 判有害」:真有害(δ=−0.50)不响;真改善(δ=+0.50)响并判"有害"
   ⇒ 本轮没出事的唯一原因是执行者没按字面执行(且是朝对自己不利的方向纠的)
   ⇒ 修法:⛔ 不改预注册原件,FINDINGS 补留痕 + 下一份改 δ < −0.354 + 立双向代入自查
m-1 证伪条件① 要求"其余四条 δ≠0",而"全零"(最可能的结果)落在它的盲区
m-2 标题层「1/6 变差」丢了「一格(弱)」这个限定 —— 而 lead 派单的转述里它已经掉光了(D6-t)
```

## 1b. 第二优先已坐实的(细节见中止件)
```
⛔ BLOCKER-1  check_gates_fire.sh:67-71 的 expect_red 判据 = 「命令返回非 0」
              ⇒ 分不清「闸门响了」与「命令根本跑不起来」= 前任 expect_fail 那条 BLOCKER 的同型
              实证:把 G10 要调的 check_mutants_valid.sh 拿走 ⇒ G10 仍报「闸门确实变红」
              ⭐ 而它长在【为回应上一条同型 BLOCKER 而新建的文件里】= D6-l 教科书复发
              expect_red 被 11 道闸门使用;其中 9 道没有阴性对照(expect_green 已定义、零使用)
✅ 前任 BLOCKER(expect_fail 假绿)两处都真的闭了 —— 我用前任自己的两条实证复核,exit 1/1 ✓
   ⚠ lead 派单与作者交接件都说"未修",两条现在都不成立(fixedpoint 那份 14:21 被重写)
✅ 16 个变异逐点核完:15 个只注入声称的缺陷;唯一例外 GATE_NEGATIVE 多删了 HOLD 状态
   ⇒ C 侧【没有】我在 d34_analysis.py 抓到的那种"一个变异两个缺陷"问题
✅ lead 那份假绿分类的五个形态,作者五条都改对了(且都带前提自检)
⭐ CHK-C1b 正是我 D3/D4 MAJOR-2 要求的那一步(饱和粘滞位 vs Q4.27 余量)⇒ 设计件应引它
```
⚠ **我自己犯过一次并已更正**:第一次用 `bash ... | tail; echo $?` 读退出码 ⇒ 读到 `tail` 的 ——
正是前任在 `run_r3.sh:55` 抓到的管道退出码缺陷。重测后结论不变。

## 2. 第一优先的判定摘要(细节见 verdict)
```
BLOCKER-1  配套件清单/自验表停在 r7,承重三条结论(f_lo*=105.2 / 8.02× / 拒绝率)只在 r10–r12
           而 r8–r12 是唯一出现过 FAIL 的五轮(r8=3, r9=6, r10=5),其中 5 条在 r11 无预注册改判 RETIRED
           ⚠ 坏消息本身没被藏(§5.9 白纸黑字写"0 段 ⇒ 不可用");断的是【可复核性】
BLOCKER-2  杀伤矩阵 `qcoef` 同时注入两个缺陷(16-bit ∧ 关结构约束)
           实证:只 16-bit ⇒ EXP-3c/EXP-4a 【不再被杀】⇒ 5 条杀伤 2 条归错因
           另:docstring 宣称 4 个变异,只实现 2 个;--broken=xo_order 印标签而不改行为
MAJOR-1    EXP-1a(§0 第一条承重结论)没有任何变异杀得死,且构造上近乎恒真
MAJOR-2    31.14 dB 是差值不是余量;EXP-1 自己的工作点下两种顺序都不饱和(−8.00 vs 余量 +24.08)
           临界配置存在且在量程内:满刻度 + 2 段 +15 dB @40 Hz ⇒ PEQ 在前 +30.00 dBFS 越余量
MAJOR-3    噪声底漏级间增益(前任 MAJOR-2 原样传播,一字未改)
           ⭐ 本件更严重:它有 comp_makeup(0…+20 dB)⇒ 出厂可配点上差 6.57–15.16 dB
MAJOR-4    「阶数 mod 4」单位自相矛盾:§4③ 表头把 12/24/36/48 叫"阶数",而 mod4 按 2/4/6/8 算
           xo_slope 参数用的正是 dB/oct ⇒ 实现方会读反 ⇒ LR2/LR6 深谷(我复算 65.86/56.32 dB)
MAJOR-5    §9 自验只讲 r1–r6 五条证伪,r8–r12 那 8 条 FAIL 只字未提
C 门        C4 FAIL / C5 FAIL(BLOCKER 成因);C1 PASS-with-minor;C2/C3/C7/C8/C9 PASS
```

## 3. ⚠ 已发生且须继续盯的流程项
- **D6-s 失守**:被审件在评审窗口内被改并 commit(`254be02`,14:05),**未告知 critic**。
  同一 commit 还动了 `02_impl/test/check_modules.c`(我的第二优先)与前任版本锁内的
  `D34_CONSTANT_LEDGER` / `D34_FIXEDPOINT_CONVENTION` / `fixedpoint/check_fixed.c` / `ref_fixed.py`。
  **⇒ 开评第二优先前必须先锁版并记 sha256/mtime。**
- `254be02` 里 `check_modules.c` 的改动 = CHK-B1b 的注释改写(把"证伪 chdsp_fixed.h:446"改成
  "chdsp_fixed.h §12 已按 critic MAJOR-4 改正")⇒ **前任那条 S>1 残留可能已修,须核现状。**

## 4. 未追完的线索(⭐ 下一个实例从这里接)
### 第二优先(02_impl)开评清单
- [ ] **先锁版**(sha256 + mtime),并把清单发 lead,引 D6-s
- [ ] `check_negcompile.sh` 的 `expect_fail` 假绿:前任实证「拿掉被测物仍 5/5 PASS」。
      ⚠ `254be02` 之前的那次 commit 已改过该文件(+174 行)⇒ **须重做前任那两条实证,不得读代码判**
- [ ] `chdsp_fixed.h:446` 的 S>1 残留 —— 按上面 §3 第二条,可能已修,核现状
- [ ] ⭐ **杀伤矩阵 16 个变异逐个核「是否真的只注入了它声称的缺陷」** ——
      我在 D3/D4 侧已抓到同型(BLOCKER-2),**C 侧几乎必然有同样的问题,优先查这个**
- [ ] `check_gates_fire.sh`(新增,未 commit 时已存在)是什么、闸门是否真能阻断(D6-ap)
- [ ] `run_all.sh` / `run_kill_matrix.sh` 的退出码是否被消费(前任对 `run_r3.sh` 开过同型 MAJOR-1)
- [ ] `ref_modules.py` 是否与 C 侧同式转写(前任对 `ref_fixed.py` 开过 MAJOR-6 同型)
### 第一优先的遗留(已入 verdict,列此备忘)
- [ ] P-1:`f_lo*=105.2` 入 D6-x 表 —— ⭐ 我已复核它对求和口径与频带上沿**都稳健**(四种组合同为 105.18 Hz)
- [ ] P-2:§7 四条路由项我复核后**四条都成立**
- [ ] P-3:D6-s 需要一个 commit 时会拦人的机制

## 5. 我的复算脚本(可原样重跑,均不 import 被审件)
```
/tmp/claude-1000/-home-it1234-processor/530be877-.../scratchpad/
  critic_d34chain_A.py   LR 极性 / 级联 DC-Nyquist / 求和平坦度 + 我造的"不加结构约束"对照
  critic_d34chain_B.py   REF 群延迟两轨 / f_lo* 四种口径组合 / 噪声底级间增益
  critic_d34chain_C.py   变异归因分离 / LR2 网格差异 / 噪声底的现实工作点
  critic_d34chain_D.py   31.14 dB vs Q4.27 余量 24.08 dB
  killrepro/             被审件拷贝 + mutA.py(只 16-bit,保留结构约束)
```

## 6. 环境/权限备忘
- 不 commit;不 spawn 子 agent;联系他人报 lead 路由;可 ESCALATE 直达 CTO(F-07)
- 现役实例名单只以 `01_design/W1_HANDOFF.md` §0 表为准
