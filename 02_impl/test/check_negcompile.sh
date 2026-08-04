#!/usr/bin/env bash
# 负编译检查 —— **硬闸门**,且**不是假绿**。⛔ 门禁状态:未过门。
#
# ============================================================================
# ⭐⭐ 本文件是对 critic BLOCKER 的直接回应
# ----------------------------------------------------------------------------
# critic 对 01_design/fixedpoint/check_negcompile.sh 的判定(成立,我接受):
#   `expect_fail` 只问「编译是否失败」⇒ **任何编译错误都算 PASS**
#   实证:①把 chdsp_apply_gain 改名(N4 唯一测到的接口消失)⇒ 仍 8/8 PASS
#         ②把 chdsp_fixed.h 整个拿走(被测物完全消失)      ⇒ 仍 5/5 PASS
#   ⇒ **结论是真的,假的是它的证明。**
#
# 本文件的三道修法:
#   (A) **匹配预期的那条具体错误**:每个负例声明 `want=<正则>`,编译器输出里
#       必须命中该正则才算杀死;⛔ "编译失败"本身不算。
#   (B) **前置存活自检**:先证明头文件在、被引用的符号在。缺一即 exit 1
#       ⇒ 「被测物消失」不可能再冒充「类型约束生效」。
#   (C) **机制对照臂**:同样的负例在 `CHDSP_STRICT_TYPES=0` 下必须**全部编译通过**
#       ⇒ 证明失败确实来自强类型,而不是片段本身写错。
#       (这条对照是 critic 补造的,我原件没有。原样纳入。)
#
# ⭐ 自查:「这个检查失败时,会阻止什么?」⇒ 阻止 run_all.sh 通过 ⇒ 阻止交付。
# ============================================================================
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
FIXED="$(cd "$ROOT/../01_design/fixedpoint" && pwd)"
CC="${CC:-gcc}"
INC="-I$ROOT/src -I$FIXED"
CFLAGS="-std=gnu99 -Wall -Wextra $INC"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

# ---------- (B) 前置存活自检 ----------
echo "负编译检查(硬闸门)"
echo "  --- (B) 前置存活自检:被测物必须真的在 ---"
preflight_bad=0
for f in "$FIXED/chdsp_fixed.h" "$ROOT/src/chdsp_config.h" "$ROOT/src/chdsp_biquad.h" \
         "$ROOT/src/chdsp_dynamics.h"; do
  if [ ! -f "$f" ]; then echo "    ⛔ 缺文件 $f"; preflight_bad=1; fi
done
for sym in chdsp_apply_gain chdsp_smp_to_io chdsp_io_to_smp chdsp_acc_to_smp \
           chdsp_bq_process1 chdsp_gate_gain1; do
  if ! grep -qE "\b$sym\b" "$FIXED/chdsp_fixed.h" "$ROOT/src"/*.h 2>/dev/null; then
    echo "    ⛔ 符号 $sym 在被测头文件里找不到 ⇒ 负例测的是【不存在的接口】"
    preflight_bad=1
  fi
done
# 正面编译自检:一个必然合法的片段必须编得过,否则环境本身坏了
cat > "$TMP/pf.c" <<'EOF'
#include "chdsp_biquad.h"
#include "chdsp_dynamics.h"
int f(void){ chdsp_smp_q4_27_t a = chdsp_smp_from_raw(1); return chdsp_smp_raw(a); }
EOF
if ! $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -c "$TMP/pf.c" -o "$TMP/pf.o" 2>"$TMP/pf.log"; then
  echo "    ⛔ 合法片段编译失败 ⇒ 编译环境/包含路径本身有问题:"; head -3 "$TMP/pf.log" | sed 's/^/       /'
  preflight_bad=1
fi
if [ $preflight_bad -ne 0 ]; then echo "  ⛔ 前置自检失败 ⇒ 本检查无意义,直接 FAIL"; exit 1; fi
echo "    文件在 / 符号在 / 合法片段编得过 ✓"
echo

# ---------- 负例:必须因【预期的那条具体错误】而失败 ----------
run_neg() {
  local tag="$1" want="$2" desc="$3"
  local log="$TMP/${tag}.log"
  if $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -c "$TMP/t.c" -o "$TMP/t.o" >"$log" 2>&1; then
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 竟然编译通过(类型层没挡住)"; fail=$((fail+1)); return
  fi
  if grep -qE "$want" "$log"; then
    echo "  [PASS] $tag  $desc  ⇒ 命中预期错误 /$want/"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 失败了,但**不是预期的那条错误**(可能是片段本身写错/被测物消失)"
    head -3 "$log" | sed 's/^/         /'; fail=$((fail+1))
  fi
}
mk(){ cat > "$TMP/t.c"; }
HDR='#include "chdsp_biquad.h"
#include "chdsp_dynamics.h"'

echo "  --- (A) 负例:必须因【预期的那条具体错误】失败 ---"

mk <<EOF
$HDR
void f(void){ chdsp_io_q0_31_t io = chdsp_io_from_raw(1); chdsp_sat_t st;
              (void)chdsp_smp_to_io(io, &st); }
EOF
run_neg N1 'incompatible type|expected .chdsp_smp_q4_27_t' "io(Q0.31) 当 smp(Q4.27) 用"

mk <<EOF
$HDR
void f(void){ chdsp_coef_q4_27_t c = chdsp_coef_from_raw(1); chdsp_sat_t st;
              (void)chdsp_smp_to_io(c, &st); }
EOF
run_neg N2 'incompatible type|expected .chdsp_smp_q4_27_t' "coef 当 smp 用(同 Q 格式,不同量纲)"

mk <<EOF
$HDR
void f(void){ chdsp_io_q0_31_t a = chdsp_io_from_raw(1);
              chdsp_smp_q4_27_t b = chdsp_smp_from_raw(1);
              chdsp_smp_q4_27_t c = a + b; (void)c; }
EOF
run_neg N3 'invalid operands' "跨定标裸相加(io + smp)"

mk <<EOF
$HDR
void f(void){ chdsp_db_q23_8_t d = chdsp_db(6); chdsp_smp_q4_27_t x = chdsp_smp_from_raw(1);
              chdsp_sat_t st; (void)chdsp_apply_gain(x, d, &st); }
EOF
run_neg N4 'incompatible type|expected .chdsp_gain_q4_27_t' "dB 当线性增益用"

mk <<EOF
$HDR
void f(void){ chdsp_acc_t acc; chdsp_smp_q4_27_t y; chdsp_acc_clear(&acc);
              y = (chdsp_smp_q4_27_t)(acc >> 27); (void)y; }
EOF
run_neg N5 'invalid operands|conversion to non-scalar' "调用方自己写 (acc >> 27)"

mk <<EOF
$HDR
void f(void){ chdsp_pow_q8_54_t p = chdsp_pow_from_raw(0); chdsp_smp_q4_27_t x;
              x = p; (void)x; }
EOF
run_neg N6 'incompatible type' "功率域(Q8.54)当样本(Q4.27)用"

mk <<EOF
$HDR
void f(void){ chdsp_slope_q16_15_t s = chdsp_slope_from_raw(1); chdsp_db_q23_8_t d;
              d = s; (void)d; }
EOF
run_neg N7 'incompatible type' "斜率(Q16.15)当 dB(Q23.8)用"

echo
echo "  --- (C) 机制对照臂:同样七个负例在 STRICT_TYPES=0 下必须【全部编译通过】 ---"
echo "      ⇒ 证明上面的失败来自【强类型】,不是片段本身写错(critic 补造的对照,原样纳入)"
ctrl_bad=0
declare -a SNIP=(N1 N2 N3 N4 N6 N7)   # N5 的移位在裸整数下本就合法,单列说明
for tag in "${SNIP[@]}"; do
  case $tag in
    N1) mk <<EOF
$HDR
void f(void){ chdsp_io_q0_31_t io = chdsp_io_from_raw(1); chdsp_sat_t st;
              (void)chdsp_smp_to_io(io, &st); }
EOF
;;
    N2) mk <<EOF
$HDR
void f(void){ chdsp_coef_q4_27_t c = chdsp_coef_from_raw(1); chdsp_sat_t st;
              (void)chdsp_smp_to_io(c, &st); }
EOF
;;
    N3) mk <<EOF
$HDR
void f(void){ chdsp_io_q0_31_t a = chdsp_io_from_raw(1);
              chdsp_smp_q4_27_t b = chdsp_smp_from_raw(1);
              chdsp_smp_q4_27_t c = a + b; (void)c; }
EOF
;;
    N4) mk <<EOF
$HDR
void f(void){ chdsp_db_q23_8_t d = chdsp_db(6); chdsp_smp_q4_27_t x = chdsp_smp_from_raw(1);
              chdsp_sat_t st; (void)chdsp_apply_gain(x, d, &st); }
EOF
;;
    N6) mk <<EOF
$HDR
void f(void){ chdsp_pow_q8_54_t p = chdsp_pow_from_raw(0); chdsp_smp_q4_27_t x;
              x = p; (void)x; }
EOF
;;
    N7) mk <<EOF
$HDR
void f(void){ chdsp_slope_q16_15_t s = chdsp_slope_from_raw(1); chdsp_db_q23_8_t d;
              d = s; (void)d; }
EOF
;;
  esac
  if $CC $CFLAGS -Wno-error -DCHDSP_STRICT_TYPES=0 -c "$TMP/t.c" -o "$TMP/t.o" >"$TMP/c_$tag.log" 2>&1; then
    echo "    [对照 OK] $tag 在 STRICT=0 下编译通过 ⇒ 该负例的失败确由强类型造成"
  else
    echo "    [⛔ 对照失败] $tag 在 STRICT=0 下也编不过 ⇒ 片段本身有问题,该负例无效"
    head -2 "$TMP/c_$tag.log" | sed 's/^/         /'; ctrl_bad=$((ctrl_bad+1))
  fi
done
echo "    (N5 不列入对照:acc 右移在裸整数下本就合法,其失败-通过翻转正是预期)"

echo
echo "  --- 正当用法必须编译通过(护栏的第二个方向,D6-y) ---"
expect_ok(){ local tag="$1" desc="$2"
  if $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -c "$TMP/t.c" -o "$TMP/t.o" >"$TMP/p.log" 2>&1; then
    echo "  [PASS] $tag  $desc"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  $desc ⇒ ⛔ 正当用法被挡掉"; head -3 "$TMP/p.log"|sed 's/^/         /'; fail=$((fail+1)); fi }
mk <<EOF
$HDR
void f(void){ chdsp_smp_q4_27_t a = chdsp_smp_from_raw(1), b = a; (void)b; }
EOF
expect_ok P1 "同类型赋值"
mk <<EOF
$HDR
void f(void){ chdsp_io_q0_31_t io = chdsp_io_from_raw(1<<20); chdsp_sat_t st;
              chdsp_sat_reset(&st); (void)chdsp_smp_to_io(chdsp_io_to_smp(io), &st); }
EOF
expect_ok P2 "经转换函数"
mk <<EOF
$HDR
void f(void){ chdsp_bq_t b; chdsp_sat_t st; chdsp_bq_init(&b); chdsp_sat_reset(&st);
              (void)chdsp_bq_process1(&b, chdsp_smp_from_raw(1), &st); }
EOF
expect_ok P3 "biquad 正常调用"

echo
echo "  合计: PASS=$pass  FAIL=$fail  对照失败=$ctrl_bad"
if [ $fail -eq 0 ] && [ $ctrl_bad -eq 0 ]; then echo "  ⇒ PASS"; exit 0
else echo "  ⛔ FAIL"; exit 1; fi
