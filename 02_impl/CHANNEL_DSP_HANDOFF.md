# channel-dsp 交接件(实例 #2)

```
⛔ 门禁状态:本文件是交接/状态记录,不是交付件,不构成任何放行依据。
   本文件描述的所有产出均为【未过门】(未经独立 critic 评审)。
实例    : channel-dsp 实例 #2 @ claude-opus-5[1m]
上岗    : 2026-08-04 ~13:53
前任    : 实例 #1(2026-08-04 约 13:50 退役,无交接件)
```

## §0 当前在做什么(⭐ 恢复工作先读这一节)

**状态:lead 派单的 ①②③④⑤⑥ **全部完成并实跑验证**。已报 lead,等 critic 或下一步指示。**

**最终基线(2026-08-04,实跑)**:`02_impl/test/run_all.sh` → **exit 0**,81 秒,共 9 环:

| 环 | 内容 | 结果 |
|---|---|---|
| 0 | ⭐ 元检查(闸门会不会响)**前置** | 13/13 PASS |
| 1 | 严格编译 `-Werror` | PASS |
| 2 | 魔数扫描 | PASS |
| 3 | 模块自验 | 35/35 PASS |
| 3b | 负编译(诊断内容判据) | 10/10 PASS |
| 3c | ⭐ **变异自证**(杀伤矩阵前置) | 18/18 PASS |
| 4 | 杀伤矩阵 | **18/18 全杀** |
| 5 | 第二轨 bit-exact | PASS |
| 6 | 强类型中立性 | PASS |

`01_design/fixedpoint/run_r3.sh` → **exit 0**(整改后;整改前它**恒 exit 0**,见 §4)。

---

## §1 ⚠ 上岗时校正了 lead 派单里的两处事实

| lead 派单说 | 实际 |
|---|---|
| ②「前任只加了描述问题的注释,没修」 | **`02_impl/test/check_negcompile.sh` 是前任重写的新件,三道修法全在,实跑 10/10**。⛔ 但 critic 点名的那一份 —— `01_design/fixedpoint/check_negcompile.sh` —— **原封未动**,且 `run_r3.sh:87` 仍在调它 ⇒ BLOCKER 只闭了一半 |
| ③「把 check_gates_fire.sh 接到 run_all.sh 上」 | 该文件**已存在且 5/5 PASS**,但**未接进 run_all.sh**;且只覆盖 6 环中的 4 环 |
| ⑤「同一模型可能还传到了 `02_impl/test/check_modules.c`」 | **否定** —— 实测 `check_modules.c` / `ref_modules.py` 里**没有**噪声模型 |

---

## §2 已完成什么(带路径)

### ① `S>1` 残留(critic MAJOR-4)—— 5 处 + **反扫另查出 6 处**
- 改:`01_design/fixedpoint/chdsp_fixed.h` §12、`D34_FIXEDPOINT_CONVENTION_v0.1.md` §0/§3.3/§3.2.2、
  `D34_CONSTANT_LEDGER_v0.1.md` A3/C 段引言/C3/F 汇总
- ⭐ **反扫另查出 6 处 critic 清单外的**:`18.089 / 18.09` 这个**由旧值推出的数**传到了
  `D34_CONSTANT_LEDGER` §F(那句"建议写进 D2 参数字典并锁死")、`D3D4_CONSTANT_LEDGER` B14、
  `D3D4_CHANNEL_CHAIN` §0 表 + §3⑥。
  **实证**:`18.089` 是**二分求出的越界点**,在该值处实扫 max|b| = **16.0002 ⇒ 已越界**;
  可锁的是解析包络 **18.0618**。⇒ 全部改为 18.0618。
- 归档:`01_design/fixedpoint/check_envelope_r4.py` + `results_envelope_r4.txt`

### ② 负编译 BLOCKER + `run_r3.sh`(critic BLOCKER-1 / MAJOR-1)
- 重写 `01_design/fixedpoint/check_negcompile.sh`:(A) 命中预期错误正则 + 排除
  `file not found`/`implicit declaration`;(B) 前置存活自检(16 个符号);(C) `STRICT_TYPES=0` 对照臂
- 三条实证:改名 ⇒ FAIL ✓;拿走头文件 ⇒ FAIL ✓;**把 `apply_gain` 改收 dB(真打开量纲缺口,符号仍在)⇒ FAIL** ✓
- `run_r3.sh`:存活报警改显式计数 + 硬中止;`GOOD/NEG/REF` 全部消费;`PIPESTATUS` 取回块退出码
- 并同步修 **m-2**(含端点错一格):下界 −109.816 → **−109.8125**(−109.816 是**首个越界格**,|err| 0.010003 > 0.01)

### ③ 元检查扩充 + 接线
- `02_impl/test/check_gates_fire.sh`:5 → **13 条**,新增 G3b/G6/G7/G8/G9/G10
- 接进 `run_all.sh` 作**第 0 环前置**(`CHDSP_GATES_META=1` 防递归)

### ④ 变异自证(杀伤矩阵前置)
- 新增 `02_impl/test/probe_mutants.c`(15 条行为探针)+ `check_mutants_valid.sh`
- **Phase A 结构探针**:`gcc -E` 读预处理后的**真实调用顺序**,断言位置关系按声称方向翻转
  ⇒ 这才抓得住前任那个「挪了但没挪到声称的地方」
- **Phase B 行为探针**:每个变异只比它自己那一行读数
- G10 阳性对照:**复现前任的原始错误形态** ⇒ 自证确实变红 ✓

### ⑤ §6.4 全链噪声底(critic MAJOR-2)
- `D34_FIXEDPOINT_CONVENTION` §6.4 拆成 6.4.1(各节增益=1)+ **6.4.2(最坏合法增益)**
- 独立复算:① −164.32(模型精确)② −164.49 ③ −160.12 ④ **−91.64**(+72.68 dB)
  ④′ **D3 输入链 −76.97**(+85.59 dB)⇒ ⛔ 突破 PRD −106 达 14.36 dB
- 传播已改:`d34_chain/d34_analysis.py` EXP-5、`D3D4_CHANNEL_CHAIN` §0/§6、`D3D4_CONSTANT_LEDGER` E8
- 归档:`d34_chain/check_noise_chain_r5.py` + `results_noise_chain_r5.txt`
- ⛔ **未动格式**(Q4.27 / EF / DF1 全不变)

### ⑥ C 第二批:分频补全(r8)
- 预注册 `d34_chain/PREREG_D34_r8_xover.txt`(⛔ 写于跑批前)
- `d34_chain/xover_r8.py` + `results_xover_r8.txt`:EXP-9/9b/10/11 全过
- 实现 `02_impl/src/chdsp_biquad.{h,c}`:`chdsp_bq_design_first_order()`、
  `chdsp_bq_design_xover2()`(BW/LR/Bessel × 1..8 阶)、Bessel 归一化极点表
- 测试 `check_modules.c` CHK-X1…X6;新增 2 个变异 + 自证探针
- 文档:`D3D4_CHANNEL_CHAIN` §8 的 **Y7/Y8 已闭**、§4③ 加 Bessel 求和警告;
  `D3D4_CONSTANT_LEDGER` 新增 §G(G1–G6)

---

## §3 下一步(未做,已显式记录)

| # | 项 | 归属 |
|---|---|---|
| N-1 | Bessel **群延迟平坦度**(它真正的卖点)—— 本轮未测 | 我,下一批 |
| N-2 | 陷波器组 `notch_mode` **零消费者**(D6-ao 接线缺口) | 我,下一批 |
| N-3 | §6.4.2 配置 ④ 的**处置**(大增益放链尾 / 限累计增益 / 参数字典约束)三选一 | ⛔ 须 lead 路由 + architect/D2 |
| N-4 | critic 放行条件里我**没做**的:MAJOR-3(厂家锚点降级)、MAJOR-5(§9.3 LR8 行)、MAJOR-6(第二轨措辞)、m-1/m-3…m-11 | ⛔ 未做,lead 未派 |
| N-5 | P-1…P-4(D6-x 限定串表、C3 入 D2、§12 三条、§1.3 动态范围合并) | ⛔ critic 明写「须由 lead 路由」 |

---

## §4 ⚠ 我踩过的坑 / 必须知道的(⭐ 最值钱的一节)

1. **⛔⛔ `run_all.sh` 自己曾是「不会响的闸门」** —— 它的 `rc_all=1` 写在 `{...} | tee` 的**子 shell** 里,
   赋值出不来,`exit $rc_all` 永远取外层的 0。**实证:弄坏一条断言 ⇒ 结果文件白纸黑字
   「⛔ 总闸门: FAIL」,而 `echo $?` = 0。**
   ⇒ 与 critic 在 `run_r3.sh` 抓到的 MAJOR-1 ② 同一缺陷,只是长在**总闸门**上。
   ⇒ 前任的元检查没抓到它,因为**只测单道闸门会不会红,没测总闸门会不会聚合**。已补 G9。
2. **⛔ r3 那一轮是「带着一个 FAIL 通过的」** —— 归档件 `results_fp_r3.txt` 里写着
   「第二轨结果: 未通过 T1a」「第二轨退出码 = 1」,而 `run_r3.sh` 只**打印** REF 不**消费**。
   ⇒ critic 写「本轮三个变异恰好都被杀死,所以没出事」——**其实出了事,只是不在变异那一路**。
   ⇒ 处置:py 轨补 `chk_retired()`(与 C 轨 `RETIRED()` 同语义),T1a 退役,另立 T1b/T1b+。
3. **⭐ 反扫的特征串必须连「由旧值推出的数」一起取。** critic 的串是
   `11.2148` ∧ `经验扫描界` ∧ `S>1`,而 `18.089` **一个都不含** —— 它是派生值,漏了 6 处。
4. **⭐ 自证探针报 FAIL 时,先问是被测物错了还是判据错了。** A2 首跑 FAIL 是**我的断言方向写反**
   (该变异的声称方向与 A1 相反),不是变异无效。
5. **⭐ 变异/写入必须核「是否真的生效」。** 我的 G10 首跑 sed 没匹配上,被 `mutate()` 的 sha 守卫拦下;
   实证 C 的 sed 命中 0 行,我差点把那次 vacuous 的运行当成通过。
6. **⛔ `16 << 27` 在 int32 里溢出成负数** ⇒ 我写的 CHK-X1 判据一度恒假。
   「Q4.27 的上界」在 raw 域**根本表示不出来**(|c|<16 ⟺ raw ≤ INT32_MAX)。
7. **⭐ `butter_q` 曾用 cos** —— 对偶数阶给出**同一 Q 集合、顺序相反**(∴ 当时是对的),
   **奇数阶不等**(n=3:0.5774 vs 正确 1.0)。加奇数阶时照搬会**静默产出错的滤波器**。
   已改 sin + CHK-X4 逐位回归证明偶数阶未变。
8. **⭐ Bessel 不能走逐节 RBJ。** Butterworth/LR 各节共用同一 ω0 ⇒「逐节各自预畸」与
   「整支预畸一次」重合;**Bessel 各节 ω0 不同 ⇒ 重合消失**,照搬会使 8 阶高通差 **91.7 dB**。
9. **⭐ 参数表写了、实现拒绝** 这类缺口不会被任何"跑绿了吗"式检查发现。
   判别法:**拿参数表的取值域去遍历实现的返回码**,而不是拿实现的能力去写测试。
10. **纪律**:不 commit(归档由 lead 做)、不 spawn 子 agent、不联系其他 teammate(只报 lead)。
    ⚠ 2026-08-04 14:05 lead 有一次归档 commit **把我在飞的改动一起收进去了**(`254be02`),
    属正常归档(带 `[未过门]`),但**注意 HEAD 可能已含未完成状态**。
