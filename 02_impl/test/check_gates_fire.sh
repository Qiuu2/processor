#!/usr/bin/env bash
# 元检查:**证明每一道闸门真的会响**。⛔ 门禁状态:未过门。
#
# ⭐ 缘起:critic 判 check_negcompile 为 BLOCKER(检查存在但不会响);
#    lead 要求「按『这个检查失败时会阻止什么』自查一遍全部自验」。
#    ⇒ 光自查不够 —— **自查也可能只是又一段文字**。本文件把它做成可执行的:
#      故意弄坏每一道闸门该守的东西,断言该闸门**确实变红**。
#    ⇒ 全部在 /tmp 的拷贝上做,⛔ 原件不动。
#
# ============================================================================
# ⭐⭐ 2026-08-04 扩充 · channel-dsp 实例 #2
# ----------------------------------------------------------------------------
# 前任版本覆盖 run_all.sh 的 6 环中的 4 环(1/2/3/3b/4 的一部分),**漏了 3 条**,
# 而漏掉的那 3 条恰好是本项目已经栽过跟头的形态:
#
#   ⛔ 漏 1(最重要)· 杀伤矩阵只测了【阴性对照臂】,没测【存活检测臂】
#      G5 弄坏 LR 极性 ⇒ 好版本自己就红 ⇒ 测的是"阴性对照会不会响"。
#      **但杀伤矩阵真正的作用是"变异存活时报警"** —— 那一路从没被测过。
#      这正是 critic MAJOR-1 在 fixedpoint/run_r3.sh 里抓到的同型缺陷
#      (`管道 || echo` 的报警分支恒不可达)。⇒ 新增 G6 直接测它。
#
#   ⛔ 漏 2 · 第二轨 bit-exact(第 5 环)与强类型中立性(第 6 环)完全没有元检查
#      ⇒ 新增 G7 / G8。
#
#   ⛔ 漏 3 · **没有人测过 run_all.sh 自己会不会聚合失败**
#      —— 每一环都红了,总闸门却可能 exit 0(fixedpoint/run_r3.sh 就正是如此:
#         第二轨 exit 1 写在归档件里,整轮仍 exit 0)。⇒ 新增 G9 测聚合。
#
#   另:G3 只覆盖负编译的【前置存活自检】臂(被测物消失)。
#      而 critic 预警的真实场景是"接口演进真的打开了量纲缺口" ⇒ 新增 G3b 覆盖【诊断内容判据】臂。
#
# ⭐ 自查:「本检查失败时,会阻止什么?」
#    ⇒ exit 1 ⇒ run_all.sh 第 0 环失败 ⇒ 整个 run_all.sh 非 0 ⇒ 阻止交付。
#    ⛔ **元检查不过,别的闸门的绿都不算数** —— 所以它是 run_all.sh 的【前置】而不是末环。
# ============================================================================
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"
FIXED="$(cd "$ROOT/../01_design/fixedpoint" && pwd)"
pass=0; fail=0
CC="${CC:-gcc}"
mkwork(){ local w="$1"; rm -rf "$w"; mkdir -p "$w/01_design"; cp -r "$ROOT" "$w/02_impl"; cp -r "$FIXED" "$w/01_design/fixedpoint"; mkdir -p "$w/02_impl/build"; }

# ⭐⭐ 变异必须【真的应用上】,否则"闸门没响"是二义的:
#    到底是闸门坏了,还是变异根本没打进去?
#    ⇒ 本轮首跑 G1/G2 就栽在这:sed 没匹配上(`#  define` 有两个空格),
#      变异静默失效,而结果读起来像"闸门不会响"。
#    ⇒ 这与团队纪律 D6-w 同源:凡写入操作,须核【写入是否发生】。
mutate(){ local f="$1" expr="$2"
  local before after
  before=$(sha256sum "$f" | cut -d' ' -f1)
  sed -i "$expr" "$f"
  after=$(sha256sum "$f" | cut -d' ' -f1)
  if [ "$before" = "$after" ]; then
    echo "  ⛔ 变异未生效:$f 内容未变(sed 未匹配)⇒ 本条元检查无意义,直接 FAIL"
    fail=$((fail+1)); return 1
  fi
  return 0
}
# 追加式变异也要核【写入是否发生】(同 D6-w)
append_mut(){ local f="$1"; local before after
  before=$(sha256sum "$f" | cut -d' ' -f1); cat >> "$f"
  after=$(sha256sum "$f" | cut -d' ' -f1)
  if [ "$before" = "$after" ]; then
    echo "  ⛔ 追加未生效:$f 内容未变 ⇒ 本条元检查无意义,直接 FAIL"; fail=$((fail+1)); return 1; fi
  return 0
}
expect_red(){ local tag="$1" desc="$2" cmd="$3" w="$4"
  if ( cd "$w/02_impl" && eval "$cmd" ) >/dev/null 2>&1; then
    echo "  [FAIL] $tag  $desc ⇒ ⛔ 闸门**没有响**"; fail=$((fail+1))
  else
    echo "  [PASS] $tag  $desc ⇒ 闸门确实变红"; pass=$((pass+1)); fi }
# 阴性对照:同一条命令在【未变异】的树上必须是绿的,否则"变红"不可归因于变异
expect_green(){ local tag="$1" desc="$2" cmd="$3" w="$4"
  if ( cd "$w/02_impl" && eval "$cmd" ) >/dev/null 2>&1; then
    echo "  [PASS] $tag  $desc ⇒ 未变异时确实是绿的 ⇒ 上一条的红可归因于变异"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  $desc ⇒ ⛔ 未变异时就是红的 ⇒ 上一条的红**不可归因于变异**"; fail=$((fail+1)); fi }

echo "元检查:每一道闸门真的会响吗(硬闸门)"
echo "  覆盖 run_all.sh 的第 0(本文件)/1/2/3/3b/4/5/6 环 + 总聚合"
echo

# ---------------------------------------------------------------- 第 1 环:严格编译 + 编译期断言
W=/tmp/gates_a; mkwork $W
mutate $W/02_impl/src/chdsp_config.h 's/^#  define CHDSP_OUT_FIR_TAPS        256/#  define CHDSP_OUT_FIR_TAPS        1024/' &&
expect_red G1 "把 FIR 抽头改成超预算的 1024 ⇒ 编译期断言应拦住" \
  "$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -c src/chdsp_biquad.c -o /dev/null" $W

# ---------------------------------------------------------------- 第 2 环:魔数扫描
W=/tmp/gates_b; mkwork $W
mutate $W/02_impl/src/chdsp_delay.h 's|^#define CHDSP_DELAY_H|#define CHDSP_DELAY_H\nstatic const int chdsp_magic_probe = 512;|' &&
expect_red G2 "在非 config 头里写入魔数 512 ⇒ 魔数扫描应拦住" \
  "bash test/check_no_magic.sh" $W

# ---------------------------------------------------------------- 第 3b 环:负编译 · 前置存活自检臂
W=/tmp/gates_c; mkwork $W
mutate $W/01_design/fixedpoint/chdsp_fixed.h 's/chdsp_apply_gain/chdsp_apply_gain_X/g' &&
expect_red G3 "把被测接口改名 ⇒ 负编译的【前置存活自检】应拦住" \
  "bash test/check_negcompile.sh" $W

# ---------------------------------------------------------------- 第 3b 环:负编译 · 诊断内容判据臂
# ⭐ 这一条测的是 critic 真正预警的场景:接口还在,但**量纲缺口被真的打开了**。
#    前置存活自检对它无能为力(符号都在)⇒ 只有 (A) 的诊断内容判据能抓。
W=/tmp/gates_c2; mkwork $W
mutate $W/01_design/fixedpoint/chdsp_fixed.h \
  's/chdsp_apply_gain(chdsp_smp_q4_27_t x, chdsp_gain_q4_27_t g/chdsp_apply_gain(chdsp_smp_q4_27_t x, chdsp_db_q23_8_t g/' &&
expect_red G3b "让 apply_gain 改收 dB(真的打开量纲缺口,符号仍在)⇒ 负编译应拦住" \
  "bash test/check_negcompile.sh" $W

# ---------------------------------------------------------------- 第 3 环:模块自验
W=/tmp/gates_d; mkwork $W
mutate $W/02_impl/test/check_modules.c 's/p2 == 1 \&\& p4 == 0/p2 == 0 \&\& p4 == 0/' &&
expect_red G4 "把一条断言改成错的 ⇒ 模块自验应变红并非 0 退出" \
  "$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint test/check_modules.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o /tmp/g4 -lm && /tmp/g4" $W

# ---------------------------------------------------------------- 第 4 环:杀伤矩阵 · 阴性对照臂
W=/tmp/gates_e; mkwork $W
mutate $W/02_impl/src/chdsp_biquad.c 's|^    return ((order % 4) == 2) ? 1 : 0;.*|    return 0;|' &&
expect_red G5 "把 LR 极性规则改坏 ⇒ 杀伤矩阵的【阴性对照】应变红" \
  "bash test/run_kill_matrix.sh" $W

# ---------------------------------------------------------------- 第 4 环:杀伤矩阵 · 存活检测臂 ⭐⭐
# ⛔ 这是前任版本最大的漏洞:G5 只证明"好版本自己红了会被发现",
#    **没有证明"变异活下来了会被发现"** —— 而后者才是杀伤矩阵存在的理由。
#    做法:往 MUTS 里注入一个在被测物中【零消费者】的宏 ⇒ 该"变异"与好版本逐位等价
#    ⇒ 必然存活 ⇒ 杀伤矩阵必须因此变红。
W=/tmp/gates_f; mkwork $W
if mutate $W/02_impl/test/run_kill_matrix.sh \
     's/^MUTS=(/MUTS=(\n  CHDSP_BROKEN_META_NOOP      # 元检查注入:零消费者 ⇒ 必然存活/'; then
  n_use=$(grep -rc "CHDSP_BROKEN_META_NOOP" $W/02_impl/src/*.c $W/02_impl/src/*.h $W/02_impl/test/check_modules.c 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
  if [ "$n_use" -ne 0 ]; then
    echo "  ⛔ G6 前提不成立:注入的宏在被测物中出现 $n_use 次(应为 0)⇒ 它未必存活 ⇒ 本条无意义"
    fail=$((fail+1))
  else
    expect_red G6 "注入一个必然存活的变异(被测物零消费者)⇒ 杀伤矩阵应报存活并变红" \
      "bash test/run_kill_matrix.sh" $W
  fi
fi

# ---------------------------------------------------------------- 第 5 环:第二轨 bit-exact
# 扰动 C 实现(⛔ 不动 py 轨)⇒ 两轨必须对不上 ⇒ 第 5 环变红。
BITEXACT_CMD="$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint test/emit_bitexact.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o build/emit -lm && cd build && ./emit && python3 ../ref/ref_modules.py"
W=/tmp/gates_g; mkwork $W
expect_green G7pre "未变异时第二轨对表" "$BITEXACT_CMD" $W
W=/tmp/gates_g2; mkwork $W
if append_mut $W/02_impl/src/chdsp_biquad.c <<'EOF'
/* 元检查注入:只扰动 C 轨,py 轨不动 ⇒ 第二轨必须报出差异 */
chdsp_smp_q4_27_t chdsp_meta_perturb(chdsp_smp_q4_27_t x);
EOF
then
  mutate $W/02_impl/src/chdsp_biquad.c \
    's|^    return chdsp_biquad_df1(&b->cur, &b->st, x, sat);|    return chdsp_smp_from_raw(chdsp_smp_raw(chdsp_biquad_df1(\&b->cur, \&b->st, x, sat)) + 1);|' &&
  expect_red G7 "只扰动 C 轨的 biquad 输出(+1 LSB)⇒ 第二轨对表应变红" "$BITEXACT_CMD" $W
fi

# ---------------------------------------------------------------- 第 6 环:强类型开关的数值中立性
# 注入一个【只在 STRICT=0 下生效】的扰动 ⇒ STRICT=1 与 =0 数值不再相同 ⇒ 第 6 环变红。
NEUTRAL_CMD="$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -DCHDSP_STRICT_TYPES=0 test/emit_bitexact.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o build/emit0 -lm \
 && $CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -DCHDSP_STRICT_TYPES=1 test/emit_bitexact.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o build/emit1 -lm \
 && cd build && ./emit0 && mv bitexact_bq_out.txt s0.txt && ./emit1 && diff -q s0.txt bitexact_bq_out.txt"
W=/tmp/gates_h; mkwork $W
expect_green G8pre "未变异时 STRICT=1 与 =0 逐位相同" "$NEUTRAL_CMD" $W
W=/tmp/gates_h2; mkwork $W
if mutate $W/02_impl/src/chdsp_biquad.c \
     's|^    if (b->bypass) { return x; }.*|    if (b->bypass) { return x; }\n#if !CHDSP_STRICT_TYPES\n    x = chdsp_smp_from_raw(chdsp_smp_raw(x) + 1);   /* 元检查注入:只在 STRICT=0 下扰动 */\n#endif|'; then
  expect_red G8 "注入只在 STRICT=0 下生效的扰动 ⇒ 强类型中立性应变红" "$NEUTRAL_CMD" $W
fi

# ---------------------------------------------------------------- 总聚合:run_all.sh 自己会不会红 ⭐
# ⛔ 每一环都会红 ≠ 总闸门会红。fixedpoint/run_r3.sh 就正是"环红了、总闸门仍 exit 0"。
#    ⇒ 这一条测的是【聚合】本身。
#    CHDSP_GATES_META=1 让被调的 run_all.sh 跳过第 0 环,避免无限递归。
W=/tmp/gates_i; mkwork $W
mutate $W/02_impl/test/check_modules.c 's/p2 == 1 \&\& p4 == 0/p2 == 0 \&\& p4 == 0/' &&
expect_red G9 "弄坏一条模块自验断言 ⇒ **run_all.sh 整体**应非 0 退出(聚合不吞错)" \
  "CHDSP_GATES_META=1 bash test/run_all.sh" $W

rm -rf /tmp/gates_a /tmp/gates_b /tmp/gates_c /tmp/gates_c2 /tmp/gates_d /tmp/gates_e \
       /tmp/gates_f /tmp/gates_g /tmp/gates_g2 /tmp/gates_h /tmp/gates_h2 /tmp/gates_i
echo
echo "  合计: PASS=$pass  FAIL=$fail"
[ $fail -eq 0 ] && { echo "  ⇒ 全部闸门(含总聚合)确实会响 ⇒ PASS"; exit 0; } \
                || { echo "  ⛔ 有闸门不会响 ⇒ FAIL(⛔ 此时别的闸门的绿都不算数)"; exit 1; }
