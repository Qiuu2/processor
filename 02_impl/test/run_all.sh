#!/usr/bin/env bash
# D3/D4 C 实现 —— 总闸门。⛔ 门禁状态:未过门。
# ⭐ 任一环失败 ⇒ 本脚本 exit 1 ⇒ 阻止交付。⛔ 没有"仅供参考"的环节。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"
FIXED="$(cd "$ROOT/../01_design/fixedpoint" && pwd)"
CC="${CC:-gcc}"; CFLAGS="-std=gnu99 -O2 -Wall -Wextra -Werror -I$ROOT/src -I$FIXED"

# ⛔⛔ 轮次(critic 02impl-r11 MAJOR-1,2026-08-05 修)
#   原先 OUT 写死 `results_impl_r1.txt`,而它当时已经是【第 11 轮】——
#   每一轮覆盖上一轮,且**文件名本身在误导**:按名字取用的人会以为拿到的是 r1。
#   ⇒ critic 原话:「git 里那 34 个版本救得回历史,救不回一个按文件名取用的人。」
# ⭐ 轮次不手工维护 —— 它由【评审 tag】自动导出,⛔ 不会因为有人忘了改而过期:
#   本轮 = 最大的 `review/02impl-rN` + 1(tag 由 lead 在送审时打,∴ 两 tag 之间就是下一工作轮)
#   ⇒ 拿不到 git/tag 时退回 `CHDSP_ROUND` 环境变量,再退回 `x`(⛔ 不假装知道轮次)
_last_tag_round="$(git -C "$ROOT" tag 2>/dev/null | sed -n 's|^review/02impl-r\([0-9]\{1,\}\)$|\1|p' | sort -n | tail -1)"
if [ -n "${_last_tag_round:-}" ]; then
  ROUND="r$((_last_tag_round + 1))"
  ROUND_SRC="自动导出:最大评审 tag review/02impl-r${_last_tag_round} + 1"
else
  ROUND="${CHDSP_ROUND:-rx}"
  ROUND_SRC="⚠ 未取到评审 tag ⇒ 用 CHDSP_ROUND 或占位 rx(⛔ 不假装知道轮次)"
fi
OUT="$ROOT/results_impl_$ROUND.txt"

# ⛔⛔ 覆盖闸门(critic 02impl-r12 m-1,2026-08-05)——【窄了洞,没堵上】的那一半
#   上一版把轮次接到评审 tag 上,消除了"永远叫 r1"那个洞;
#   ⇒ 而 `| tee "$OUT"` 是**截断写**:两个评审 tag 之间若有**多个工作轮**,
#     它们导出的 ROUND 相同 ⇒ 第二轮**静默覆盖**第一轮的归档件。
#   ⇒ ⭐ 旧洞是"永远 r1",新洞是"两轮同名" —— 洞窄了很多,而**后果是同一个**:
#     交付树上看不出曾经有过另一次跑批(尤其是红的那次)。
#   ⇒ ∴ 已存在即**拒绝覆盖并非 0 退出**;要覆盖必须**显式**写 CHDSP_OVERWRITE=1。
#   ⚠ 那个显式动作就是这条闸门的全部价值:它把【静默覆盖】变成【有意识的覆盖】。
# ⭐ 而【探针跑批不产归档件】—— 这一条比"给探针开个例外"更干净:
#   元检查(check_gates_fire.sh)会在真实树上递归调用本脚本当基线/阳性对照,
#   那种跑批**本来就不该**写交付树的归档件。⇒ 它写到临时文件,⛔ 从而与覆盖闸门无关。
#   ⚠ 若只是"给 CHDSP_GATES_META 开个例外",探针仍会覆盖归档件 —— 那正是本闸门要防的事。
if [ "${CHDSP_GATES_META:-0}" = "1" ]; then
  OUT="$(mktemp -t chdsp_metaprobe.XXXXXX)"
elif [ -e "$OUT" ] && [ "${CHDSP_OVERWRITE:-0}" != "1" ]; then
  echo "⛔ 归档件已存在:$OUT" >&2
  echo "⛔ 拒绝覆盖 —— 覆盖会让上一次跑批(可能是红的)从交付树上消失。" >&2
  echo "   ⇒ 若这是同一工作轮的重跑,请显式: CHDSP_OVERWRITE=1 bash test/run_all.sh" >&2
  echo "   ⇒ 若这是新的一轮,请先让 lead 打 review/02impl-r<N> tag(轮次由 tag 导出)。" >&2
  exit 3
fi
rm -rf "$ROOT/build" "$ROOT/build_kill"; mkdir -p "$ROOT/build"
sha(){ sha256sum "$1"|cut -c1-16; }
rc_all=0
{
echo "================================================================================"
echo "results_impl_$ROUND —— D3/D4 C 实现 · 总闸门"
echo "⭐ 本轮 = $ROUND   ($ROUND_SRC)"
echo "   ⚠ 轮次沿革(各轮总闸门状态 / FAIL 去向 / 引入后又被移除的东西)见"
echo "     02_impl/CHANNEL_DSP_HANDOFF.md §0.2【轮次沿革】"
echo "门禁状态: 未过门(未经独立 critic 评审)"
echo "时间: $(date -Iseconds)"
echo "deps: $(for f in "$ROOT"/src/*.h "$ROOT"/src/*.c; do printf '%s@%s ' "$(basename $f)" "$(sha $f)"; done)"
echo "      check_modules.c@$(sha $HERE/check_modules.c) ref_modules.py@$(sha $ROOT/ref/ref_modules.py)"
echo "编译器: $($CC --version|head -1)"
echo "================================================================================"

echo; echo "### 0. ⭐ 元检查:每一道闸门真的会响吗(**前置** —— 本环不过,下面的绿都不算数)"
if [ "${CHDSP_GATES_META:-0}" = "1" ]; then
  echo "  (跳过:本次由 check_gates_fire.sh 递归调用,避免无限递归)"
else
  if bash "$HERE/check_gates_fire.sh"; then
    echo "  ⇒ 元检查通过 ⇒ 下面各环的绿是有意义的"
  else
    echo "  ⛔ 元检查失败:至少一道闸门弄坏被测物后仍不变红"
    echo "  ⛔ ⇒ **下面各环的 PASS 不构成证据**(治理 §5 假绿纪律)"
    rc_all=1
  fi
fi

echo; echo "### 1. 严格编译(-Werror,强类型)"
ok=1
for f in "$ROOT"/src/*.c; do
  $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -c "$f" -o "$ROOT/build/$(basename $f).o" 2>&1 || ok=0
done
[ $ok -eq 1 ] && echo "  全部模块 -Werror 通过 ✓" || { echo "  ⛔ 编译失败"; rc_all=1; }

echo; echo "### 2. 魔数扫描(硬闸门)"
bash "$HERE/check_no_magic.sh" || rc_all=1

echo; echo "### 3. 模块自验(硬闸门)"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 "$HERE/check_modules.c" "$ROOT"/src/*.c "$FIXED/chdsp_fixed.c" \
    -o "$ROOT/build/chk" -lm 2>&1 || rc_all=1
"$ROOT/build/chk" || rc_all=1

echo; echo "### 3b. 负编译检查(硬闸门,已按 critic BLOCKER 重做)"
bash "$HERE/check_negcompile.sh" || rc_all=1

echo; echo "### 3c. ⭐ 变异自证(硬闸门 · **杀伤矩阵的前置**)"
echo "  ⇒ 每个变异先自证「它确实改变了它声称要改变的那个行为」,否则杀伤率的分母不可信"
if bash "$HERE/check_mutants_valid.sh"; then
  mut_valid=0
else
  mut_valid=1; rc_all=1
fi

echo; echo "### 3d. ⭐ 基线机制会不会响(硬闸门 · **杀伤矩阵的前置**,N-6)"
echo "  ⇒ C 侧目前【没有】常驻 FAIL ⇒ 登记为空 ⇒ 基线逻辑此刻是恒等式(空集 == 空集)"
echo "  ⛔ 而一个从未被证明会响的机制,与没有机制的区别只在于**它让人放心**"
echo "  ⇒ ∴ 在临时副本上人为造一条常驻 FAIL,逐条验四种走法(⛔ 不碰真实树)"
bash "$HERE/check_baseline_mech.sh" || rc_all=1

echo; echo "### 4. 杀伤矩阵(硬闸门)"
bash "$HERE/run_kill_matrix.sh" || rc_all=1
if [ $mut_valid -ne 0 ]; then
  echo "  ⛔ 上一环(变异自证)未通过 ⇒ **本轮杀伤率作废**"
  echo "  ⛔ ⇒ 上面的『N/N 全部被杀死』不构成证据:至少一个变异没做到它声称的事,"
  echo "       它的『被杀死』是一条【假的杀伤记录】,而假杀伤是隐形的。"
fi

echo; echo "### 5. 实现一致性核 + 铁律七的独立解析轨(硬闸门)"
echo "  ⛔ 两件事分开报(整改 · critic 02impl MAJOR-1):"
echo "     (A) 实现一致性核 —— ref_modules.py 是**同式转写**,只证转写忠实,⛔ 不证算法对"
echo "     (B) 铁律七的独立轨 —— 拿解析式做参照,与实现无共用代码"
echo "  ⚠ 原称「第二轨 bit-exact」,那个定级越了铁律七的界"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 "$HERE/emit_bitexact.c" "$ROOT"/src/*.c "$FIXED/chdsp_fixed.c" \
    -o "$ROOT/build/emit" -lm 2>&1 || rc_all=1
( cd "$ROOT/build" && ./emit && python3 "$ROOT/ref/ref_modules.py" ) || rc_all=1

echo; echo "### 6. 强类型开关的数值中立性(硬闸门)"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=0 "$HERE/emit_bitexact.c" "$ROOT"/src/*.c "$FIXED/chdsp_fixed.c" \
    -o "$ROOT/build/emit0" -lm 2>&1 || rc_all=1
( cd "$ROOT/build" && ./emit0 && mv bitexact_bq_out.txt s0.txt && ./emit >/dev/null ) || rc_all=1
if diff -q "$ROOT/build/s0.txt" "$ROOT/build/bitexact_bq_out.txt" >/dev/null 2>&1; then
  echo "  STRICT=1 vs 0:逐位 SAME ✓"
  sed '5000s/.*/999999/' "$ROOT/build/s0.txt" > "$ROOT/build/forced.txt"
  if diff -q "$ROOT/build/forced.txt" "$ROOT/build/bitexact_bq_out.txt" >/dev/null 2>&1; then
    echo "  ⛔ 阳性对照失败:强制错值后比对器仍说相同 ⇒ 无分辨力"; rc_all=1
  else echo "  阳性对照:强制错值 ⇒ DIFF ✓ ⇒ 上一行的 SAME 有意义"; fi
else echo "  ⛔ STRICT=1 与 =0 数值不一致"; rc_all=1; fi

echo; echo "================================================================================"
[ $rc_all -eq 0 ] && echo "总闸门: PASS(全部环节通过)" || echo "⛔ 总闸门: FAIL"
echo "================================================================================"
exit $rc_all           # ⭐ 见下方整改说明:块的退出码必须由块自己给出
} 2>&1 | tee "$OUT"
# ============================================================================
# ⛔⛔ 2026-08-04 整改 · channel-dsp 实例 #2 —— 本文件自己就是"不会响的闸门"
# ----------------------------------------------------------------------------
# 原写法:
#     rc_all=0
#     { ... rc_all=1 ... } 2>&1 | tee "$OUT"
#     exit $rc_all
# `{ ... } | tee` 使块运行在**子 shell** 里 ⇒ 块内对 rc_all 的赋值**出不来**
# ⇒ `exit $rc_all` 取的永远是外层那个 0 ⇒ **本脚本恒 exit 0。**
#
# 实证(2026-08-04,拷贝树上做):弄坏 check_modules.c 的一条断言 ⇒
#     结果文件里白纸黑字「⛔ 总闸门: FAIL」,而 `echo $?` = **0**。
#
# ⇒ 这与 critic 在 fixedpoint/run_r3.sh 抓到的 MAJOR-1 ② **是同一个缺陷**,
#   只是长在**总闸门**上 —— 即:六道闸门每一道都可能红,而**总闸门永远绿**。
# ⇒ 自查那句「这个检查失败时,会阻止什么?」在本文件上的答案曾经是:**什么也不阻止。**
# ⇒ 前任的元检查 check_gates_fire.sh 没抓到它,因为它只测【单道闸门会不会红】,
#   **没测【总闸门会不会聚合】** ⇒ 已补 G9 专测这一条。
#
# 修法:块内 `exit $rc_all`,块外用 PIPESTATUS 取回(⛔ tee 的退出码恒 0)。
# ============================================================================
rc_all=${PIPESTATUS[0]}
[ $rc_all -eq 0 ] || echo "⛔ 总闸门 FAIL ⇒ 本脚本以 $rc_all 退出,阻止交付" >&2
exit $rc_all
