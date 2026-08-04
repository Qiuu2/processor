#!/usr/bin/env bash
# D3/D4 C 实现 —— 总闸门。⛔ 门禁状态:未过门。
# ⭐ 任一环失败 ⇒ 本脚本 exit 1 ⇒ 阻止交付。⛔ 没有"仅供参考"的环节。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"
FIXED="$(cd "$ROOT/../01_design/fixedpoint" && pwd)"
CC="${CC:-gcc}"; CFLAGS="-std=gnu99 -O2 -Wall -Wextra -Werror -I$ROOT/src -I$FIXED"
OUT="$ROOT/results_impl_r1.txt"
rm -rf "$ROOT/build" "$ROOT/build_kill"; mkdir -p "$ROOT/build"
sha(){ sha256sum "$1"|cut -c1-16; }
rc_all=0
{
echo "================================================================================"
echo "results_impl_r1 —— D3/D4 C 实现 · 总闸门"
echo "门禁状态: 未过门(未经独立 critic 评审)"
echo "时间: $(date -Iseconds)"
echo "deps: $(for f in "$ROOT"/src/*.h "$ROOT"/src/*.c; do printf '%s@%s ' "$(basename $f)" "$(sha $f)"; done)"
echo "      check_modules.c@$(sha $HERE/check_modules.c) ref_modules.py@$(sha $ROOT/ref/ref_modules.py)"
echo "编译器: $($CC --version|head -1)"
echo "================================================================================"

echo; echo "### 1. 严格编译(-Werror,强类型)"
if $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -c $ROOT/src/*.c -o /dev/null 2>&1; then :; fi
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

echo; echo "### 4. 杀伤矩阵(硬闸门)"
bash "$HERE/run_kill_matrix.sh" || rc_all=1

echo; echo "### 5. 第二轨 bit-exact(硬闸门)"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 "$HERE/emit_bitexact.c" "$ROOT"/src/*.c "$FIXED/chdsp_fixed.c" \
    -o "$ROOT/build/emit" -lm 2>&1 || rc_all=1
( cd "$ROOT/build" && ./emit && python3 "$ROOT/ref/ref_modules.py" ) || rc_all=1

echo; echo "### 6. 强类型开关的数值中立性(硬闸门)"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=0 "$HERE/emit_bitexact.c" "$ROOT"/src/*.c "$FIXED/chdsp_fixed.c" \
    -o "$ROOT/build/emit0" -lm 2>&1 || rc_all=1
( cd "$ROOT/build" && ./emit0 && mv bitexact_bq_out.txt s0.txt && ./emit >/dev/null )
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
} 2>&1 | tee "$OUT"
exit $rc_all
