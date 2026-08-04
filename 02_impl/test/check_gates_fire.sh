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
#   ⛔ 漏 2 · 第 5 环(一致性核/解析轨)与强类型中立性(第 6 环)完全没有元检查
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
# ============================================================================
# ⛔⛔ 2026-08-04 整改 · critic 02impl BLOCKER-1(r1 开、r2 维持)—— 我认,且理由扎心
# ----------------------------------------------------------------------------
# 原 expect_red 的判据 = 「命令返回非 0」⇒ **任何非 0 都算「闸门响了」**。
# critic 的实证:把 G10/G11 要调的 check_mutants_valid.sh **拿走** ⇒ 两道闸门仍报
# 「闸门确实变红」,元检查整体报 PASS —— 变红的真实原因是退出码 127(No such file)。
#
# ⇒ **这与前任 expect_fail 那条 BLOCKER 是同一个病**,而它长在【为回应那条 BLOCKER
#   而新建的文件里】;更难堪的是:**正确写法就在隔壁 check_mutants_valid.sh 的
#   phase_a_flip 里,同一个人、同一天写的** —— 它明确区分「探针取不到位置」与
#   「位置没翻转」,两种都判 FAIL。
# ⇒ **同一套逻辑,在一个文件里做对了、在另一个文件里做错了。**
#
# 三道修法(critic 原文,全部采纳):
#   ① **内容判据**:每道闸门声明 `want=<正则>`,被测命令的输出须命中【该闸门自己的失败特征】;
#      ⛔ 命中 `No such file` / `command not found` / `fatal error:` 一律判 FAIL。
#   ② **全部配阴性对照**:每条被测命令先在【未变异的树】上跑一遍,必须绿。
#      (⚠ 按命令去重跑,不按闸门 —— 同一条命令服务多道闸门时只需一次。)
#   ③ **立规**:凡以退出码判定被测物行为的函数,必须同时有【内容判据】+【阴性对照】。
#      全库现有三个:expect_fail ✓ / run_neg ✓ / expect_red —— 本次补齐第三个。
# ============================================================================

# 取消资格串:命中这些说明【命令根本没跑起来】,不是【闸门响了】
DISQ='No such file|command not found|没有那个文件|fatal error:|Permission denied|cannot execute'

# ⛔ 整改 2026-08-04:原来这些工作目录是**写死的 /tmp/gates_***。
#   而本脚本现在可以被**递归调用**(run_all 第 0 环 → 本脚本 → ensure_green 跑嵌套 run_all → …)
#   ⇒ 两次调用共用同一批路径,**内层的清理会删掉外层的基线树**
#   ⇒ 外层随后 `cd $BASE/02_impl` 失败 ⇒ 阴性对照红,而红的原因与被测物无关。
#   ⇒ 改为每次调用一个唯一根目录。⚠ 这与 D6-j 同族:输出路径不仅要唯一,还要**真的属于本次跑批**。
TMPROOT="$(mktemp -d -t chdsp_gates.XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT
BASE="$TMPROOT/base"
declare -A GREEN_DONE=()

# 阴性对照:同一条命令在【未变异】的基线树上必须绿。按命令去重。
ensure_green(){ local key="$1" desc="$2" cmd="$3"
  if [ -n "${GREEN_DONE[$key]:-}" ]; then return 0; fi
  GREEN_DONE[$key]=1
  local out rc
  out=$( ( cd "$BASE/02_impl" && eval "$cmd" ) 2>&1 ); rc=$?
  if [ $rc -eq 0 ]; then
    echo "  [PASS] base:$key  基线上「$desc」是绿的 ⇒ 下面的红可归因于变异"; pass=$((pass+1))
  else
    echo "  [FAIL] base:$key  ⛔ 基线上「$desc」就是红的 ⇒ 该命令的红**不可归因于变异**"
    # ⚠ 整改:原来这里把输出丢进 /dev/null ⇒ 阴性对照失败时**看不到为什么**。
    #   一个失败了却不说原因的器械,和不会响的闸门是同一类问题。
    echo "         ── 退出码 $rc,末 8 行 ──"
    printf '%s' "$out" | tail -8 | sed 's/^/         /'
    fail=$((fail+1)); fi }

# 闸门必须【因为它自己的失败特征】而变红
expect_red(){ local tag="$1" desc="$2" cmd="$3" w="$4" want="${5:-}"
  local out rc
  # ⭐ 器械自检(照抄 phase_a_flip 的形状):没有失败特征串 ⇒ 判据退化回「任何非 0」
  #   ⇒ 那正是本次 BLOCKER 的病 ⇒ **本条闸门无意义,判 FAIL,⛔ 不得当作通过**。
  if [ -z "$want" ]; then
    echo "  [FAIL] $tag  ⛔ 本闸门没有声明失败特征串(want)⇒ 判据退化成「任何非 0」"
    echo "         ⇒ 器械失效 ⇒ 本条元检查无意义(⛔ 不得当作通过)"
    fail=$((fail+1)); return; fi
  out=$( ( cd "$w/02_impl" && eval "$cmd" ) 2>&1 ); rc=$?
  if [ $rc -eq 0 ]; then
    echo "  [FAIL] $tag  $desc ⇒ ⛔ 闸门**没有响**"; fail=$((fail+1)); return; fi
  if printf '%s' "$out" | grep -qE "$DISQ"; then
    echo "  [FAIL] $tag  $desc ⇒ ⛔ 非 0 的原因是【命令没跑起来】,不是闸门响了"
    printf '%s' "$out" | grep -E "$DISQ" | head -2 | sed 's/^/         /'
    fail=$((fail+1)); return; fi
  if printf '%s' "$out" | grep -qE "$want"; then
    echo "  [PASS] $tag  $desc ⇒ 闸门确实变红(命中 /$want/)"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  $desc ⇒ ⛔ 红了,但**不是它自己那条失败特征**(/$want/ 未命中)"
    printf '%s' "$out" | tail -3 | sed 's/^/         /'; fail=$((fail+1)); fi }

echo "元检查:每一道闸门真的会响吗(硬闸门)"
echo "  ⛔ 判据 = 【非 0】∧【不是"跑不起来"】∧【命中该闸门自己的失败特征】,三者缺一不可"
mkwork $BASE          # 未变异的基线树,供全部阴性对照复用

echo "  覆盖 run_all.sh 的第 0(本文件)/1/2/3/3b/4/5/6 环 + 总聚合"
echo

# ---------------------------------------------------------------- 第 1 环:严格编译 + 编译期断言
ensure_green compile_bq "严格编译 chdsp_biquad.c" "$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -c src/chdsp_biquad.c -o /dev/null"
W=$TMPROOT/a; mkwork $W
mutate $W/02_impl/src/chdsp_config.h 's/^#  define CHDSP_OUT_FIR_TAPS        256/#  define CHDSP_OUT_FIR_TAPS        1024/' &&
expect_red G1 "把 FIR 抽头改成超预算的 1024 ⇒ 编译期断言应拦住" \
  "$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -c src/chdsp_biquad.c -o /dev/null" $W "size of array .chdsp_static_assert"

# ---------------------------------------------------------------- 第 2 环:魔数扫描
ensure_green no_magic "魔数扫描" "bash test/check_no_magic.sh"
W=$TMPROOT/b; mkwork $W
mutate $W/02_impl/src/chdsp_delay.h 's|^#define CHDSP_DELAY_H|#define CHDSP_DELAY_H\nstatic const int chdsp_magic_probe = 512;|' &&
expect_red G2 "在非 config 头里写入魔数 512 ⇒ 魔数扫描应拦住" \
  "bash test/check_no_magic.sh" $W "⛔|FAIL|魔数"

# ---------------------------------------------------------------- 第 3b 环:负编译 · 前置存活自检臂
ensure_green negcompile "负编译检查" "bash test/check_negcompile.sh"
W=$TMPROOT/c; mkwork $W
mutate $W/01_design/fixedpoint/chdsp_fixed.h 's/chdsp_apply_gain/chdsp_apply_gain_X/g' &&
expect_red G3 "把被测接口改名 ⇒ 负编译的【前置存活自检】应拦住" \
  "bash test/check_negcompile.sh" $W "前置自检失败|⛔ FAIL"

# ---------------------------------------------------------------- 第 3b 环:负编译 · 诊断内容判据臂
# ⭐ 这一条测的是 critic 真正预警的场景:接口还在,但**量纲缺口被真的打开了**。
#    前置存活自检对它无能为力(符号都在)⇒ 只有 (A) 的诊断内容判据能抓。
W=$TMPROOT/c2; mkwork $W
mutate $W/01_design/fixedpoint/chdsp_fixed.h \
  's/chdsp_apply_gain(chdsp_smp_q4_27_t x, chdsp_gain_q4_27_t g/chdsp_apply_gain(chdsp_smp_q4_27_t x, chdsp_db_q23_8_t g/' &&
expect_red G3b "让 apply_gain 改收 dB(真的打开量纲缺口,符号仍在)⇒ 负编译应拦住" \
  "bash test/check_negcompile.sh" $W "FAIL|⛔ FAIL"

# ---------------------------------------------------------------- 第 3 环:模块自验
ensure_green modules "模块自验" "$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint test/check_modules.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o $TMPROOT/gbase_m -lm && $TMPROOT/gbase_m"
W=$TMPROOT/d; mkwork $W
mutate $W/02_impl/test/check_modules.c 's/p2 == 1 \&\& p4 == 0/p2 == 0 \&\& p4 == 0/' &&
expect_red G4 "把一条断言改成错的 ⇒ 模块自验应变红并非 0 退出" \
  "$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint test/check_modules.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o $TMPROOT/g4 -lm && $TMPROOT/g4" $W "\\[FAIL\\]"

# ---------------------------------------------------------------- 第 4 环:杀伤矩阵 · 阴性对照臂
ensure_green killmatrix "杀伤矩阵" "bash test/run_kill_matrix.sh"
W=$TMPROOT/e; mkwork $W
mutate $W/02_impl/src/chdsp_biquad.c 's|^    return ((n % 4) == 2) ? 1 : 0;.*|    return 0;|' &&
expect_red G5 "把 LR 极性规则改坏 ⇒ 杀伤矩阵的【阴性对照】应变红" \
  "bash test/run_kill_matrix.sh" $W "阴性对照失败|存活|⛔"

# ---------------------------------------------------------------- 第 4 环:杀伤矩阵 · 存活检测臂 ⭐⭐
# ⛔ 这是前任版本最大的漏洞:G5 只证明"好版本自己红了会被发现",
#    **没有证明"变异活下来了会被发现"** —— 而后者才是杀伤矩阵存在的理由。
#    做法:往 MUTS 里注入一个在被测物中【零消费者】的宏 ⇒ 该"变异"与好版本逐位等价
#    ⇒ 必然存活 ⇒ 杀伤矩阵必须因此变红。
W=$TMPROOT/f; mkwork $W
if mutate $W/02_impl/test/run_kill_matrix.sh \
     's/^MUTS=(/MUTS=(\n  CHDSP_BROKEN_META_NOOP      # 元检查注入:零消费者 ⇒ 必然存活/'; then
  n_use=$(grep -rc "CHDSP_BROKEN_META_NOOP" $W/02_impl/src/*.c $W/02_impl/src/*.h $W/02_impl/test/check_modules.c 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
  if [ "$n_use" -ne 0 ]; then
    echo "  ⛔ G6 前提不成立:注入的宏在被测物中出现 $n_use 次(应为 0)⇒ 它未必存活 ⇒ 本条无意义"
    fail=$((fail+1))
  else
    expect_red G6 "注入一个必然存活的变异(被测物零消费者)⇒ 杀伤矩阵应报存活并变红" \
      "bash test/run_kill_matrix.sh" $W "存活"
  fi
fi

# ---------------------------------------------------------------- 第 5 环:第二轨 bit-exact
# 扰动 C 实现(⛔ 不动 py 轨)⇒ 两轨必须对不上 ⇒ 第 5 环变红。
BITEXACT_CMD="$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint test/emit_bitexact.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o build/emit -lm && cd build && ./emit && python3 ../ref/ref_modules.py"
ensure_green bitexact "实现一致性核 + 独立解析轨" "$BITEXACT_CMD"
W=$TMPROOT/g2; mkwork $W
if append_mut $W/02_impl/src/chdsp_biquad.c <<'EOF'
/* 元检查注入:只扰动 C 轨,py 轨不动 ⇒ 第二轨必须报出差异 */
chdsp_smp_q4_27_t chdsp_meta_perturb(chdsp_smp_q4_27_t x);
EOF
then
  mutate $W/02_impl/src/chdsp_biquad.c \
    's|^    return chdsp_biquad_df1(&b->cur, &b->st, x, sat);|    return chdsp_smp_from_raw(chdsp_smp_raw(chdsp_biquad_df1(\&b->cur, \&b->st, x, sat)) + 1);|' &&
  expect_red G7 "只扰动 C 轨的 biquad 输出(+1 LSB)⇒ 实现一致性核(A 轨)应变红" "$BITEXACT_CMD" $W "\\[FAIL\\]|不同|DIFF"
fi

# ---------------------------------------------------------------- 第 6 环:强类型开关的数值中立性
# 注入一个【只在 STRICT=0 下生效】的扰动 ⇒ STRICT=1 与 =0 数值不再相同 ⇒ 第 6 环变红。
NEUTRAL_CMD="$CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -DCHDSP_STRICT_TYPES=0 test/emit_bitexact.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o build/emit0 -lm \
 && $CC -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -DCHDSP_STRICT_TYPES=1 test/emit_bitexact.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o build/emit1 -lm \
 && cd build && ./emit0 && mv bitexact_bq_out.txt s0.txt && ./emit1 && diff -q s0.txt bitexact_bq_out.txt"
ensure_green neutral "强类型中立性" "$NEUTRAL_CMD"
W=$TMPROOT/h2; mkwork $W
if mutate $W/02_impl/src/chdsp_biquad.c \
     's|^    if (b->bypass) { return x; }.*|    if (b->bypass) { return x; }\n#if !CHDSP_STRICT_TYPES\n    x = chdsp_smp_from_raw(chdsp_smp_raw(x) + 1);   /* 元检查注入:只在 STRICT=0 下扰动 */\n#endif|'; then
  expect_red G8 "注入只在 STRICT=0 下生效的扰动 ⇒ 强类型中立性应变红" "$NEUTRAL_CMD" $W "differ|DIFF|不同|不一致"
fi

# ---------------------------------------------------------------- 第 3c 环:变异自证 ⭐⭐
# ⭐ 阳性对照必须**复现前任真实踩过的那个坑**,否则"16/16 自证全过"本身也只是一段文字:
#    把 CHDSP_BROKEN_HPF_AFTER_DYN 改回**它最初的错误形态** ——
#    HPF 挪到 AEC 钩子之后,但**仍在门/压缩之前** ⇒ 它没做到"挪到动态之后"。
#    ⇒ 变异自证必须因此变红。若不红,这道闸门就抓不住假杀伤。
ensure_green mutvalid "变异自证" "bash test/check_mutants_valid.sh"
W=$TMPROOT/j; mkwork $W
CH=$W/02_impl/src/chdsp_chain.c
# 第 2 处 `hpf` 调用 = `#if CHDSP_BROKEN_HPF_AFTER_DYN` 里那一处(真正"挪到动态之后"的)
L_HPF2=$(grep -n 'chdsp_bq_chain_process(&ch->hpf' "$CH" | sed -n 2p | cut -d: -f1)
L_ANC=$(grep -n 'chdsp_hook_run(&ch->hook_anc' "$CH" | head -1 | cut -d: -f1)
if [ -z "$L_HPF2" ] || [ -z "$L_ANC" ] || [ "$L_HPF2" -le "$L_ANC" ]; then
  echo "  ⛔ G10 前提不成立:定位失败(hpf2=$L_HPF2 anc=$L_ANC)⇒ 本条元检查无意义,FAIL"
  fail=$((fail+1))
else
  # ① 先删【动态之后】那一处(行号大,先删不影响 ② 的行号)
  # ② 再把同一调用插到 ANC 钩子之后 —— 仍在门/压缩【之前】= 前任的原始错误形态
  if mutate "$CH" "${L_HPF2}d" && \
     mutate "$CH" "${L_ANC}a\\    chdsp_bq_chain_process(\&ch->hpf, out, out, n, \&ch->sat);"; then
    expect_red G10 "把 HPF_AFTER_DYN 改回前任的错误形态(挪了但仍在动态之前)⇒ 变异自证应变红" \
      "bash test/check_mutants_valid.sh" $W "\\[FAIL\\]|杀伤率作废" "\\[FAIL\\]|不同|DIFF"
  fi
fi

# ---------------------------------------------------------------- 第 3c 环:自证【断言②】⭐⭐
# ⭐ 阳性对照必须复现 critic 在设计侧抓到的那一条:**一个变异注入了两个缺陷**
#    (`qsec()` 里名叫「系数退化到 16-bit」的变异顺手把结构约束量化也关了
#     ⇒ 两条杀伤记在了错的原因上)。
#    做法:让 CHDSP_BROKEN_NO_HYST **顺手**也改掉 FIR 的透传行为
#    ⇒ 它会动到未声明的 P_FIR_NOBYPASS ⇒ 断言② 必须变红。
W=$TMPROOT/k; mkwork $W
if mutate $W/02_impl/src/chdsp_fir.c \
     's/^#if CHDSP_BROKEN_FIR_NOBYPASS$/#if CHDSP_BROKEN_FIR_NOBYPASS || CHDSP_BROKEN_NO_HYST/'; then
  expect_red G11 "让一个变异顺手注入第二个缺陷 ⇒ 变异自证的【断言②】应变红" \
    "bash test/check_mutants_valid.sh" $W "未声明的连带变化|\\[FAIL\\]" "differ|DIFF|不同|不一致"
fi

# ---------------------------------------------------------------- 总聚合:run_all.sh 自己会不会红 ⭐
# ⛔ 每一环都会红 ≠ 总闸门会红。fixedpoint/run_r3.sh 就正是"环红了、总闸门仍 exit 0"。
#    ⇒ 这一条测的是【聚合】本身。
#    CHDSP_GATES_META=1 让被调的 run_all.sh 跳过第 0 环,避免无限递归。
ensure_green runall "总闸门 run_all.sh" "CHDSP_GATES_META=1 bash test/run_all.sh"
W=$TMPROOT/i; mkwork $W
mutate $W/02_impl/test/check_modules.c 's/p2 == 1 \&\& p4 == 0/p2 == 0 \&\& p4 == 0/' &&
expect_red G9 "弄坏一条模块自验断言 ⇒ **run_all.sh 整体**应非 0 退出(聚合不吞错)" \
  "CHDSP_GATES_META=1 bash test/run_all.sh" $W "总闸门: FAIL"

echo
echo "  合计: PASS=$pass  FAIL=$fail"
[ $fail -eq 0 ] && { echo "  ⇒ 全部闸门(含总聚合)确实会响 ⇒ PASS"; exit 0; } \
                || { echo "  ⛔ 有闸门不会响 ⇒ FAIL(⛔ 此时别的闸门的绿都不算数)"; exit 1; }
