#!/usr/bin/env bash
# CHK-10:负向编译测试 —— D-1「用接口不允许来防,不用文档提醒来防」的机械证明。
#   N1..N5 必须因【预期的那条具体错误】编译失败(量纲错误被类型层挡住)
#   P1..P3 必须【编译通过】(护栏没挡掉正当用法 —— 团队纪律 D6-y 的第二个方向)
# ⛔ 门禁状态:未过门。
#
# ============================================================================
# ⭐⭐ 2026-08-04 整改 · channel-dsp 实例 #2 · 直接闭 critic BLOCKER-1
# ----------------------------------------------------------------------------
# critic 的判定(成立,我接受):
#   旧 `expect_fail` 只问 `$CC -c` 是否返回非 0 ⇒ **任何编译错误都算 PASS**,
#   包括「这个测试要测的接口已经不存在了」。
#   critic 的两条实证:
#     A  把 chdsp_apply_gain 改名 ⇒ N4(本项目最贵的一类量纲错)什么也没测 ⇒ 仍 8/8 PASS
#     B  把 chdsp_fixed.h 整个拿走(被测物完全消失)⇒ N1–N5 仍 5/5 PASS
#   ⇒ 治理 §5 红线原句:「验证器在占位/恒等/旧文件上照样 PASS = 假绿,比没验更危险」
#   ⇒ D6-d「拿掉被测物,这个数应该等于多少?」答案应是 0/5,旧实测是 5/5。
#
# ⚠ 必须同时说清:**被检查的机制本身是有效的**,假的只是它的证明。
#   critic 补造的对照(同样片段把 CHDSP_STRICT_TYPES 从 1 改成 0)⇒ 5/5 翻转。
#
# 本次三道修法(缺一不可):
#   (A) **匹配预期的那条具体错误**:每个负例声明 `want=<正则>`,编译器输出必须命中
#       才算杀死;⛔「编译失败」本身不算。命中 file not found / implicit declaration
#       一律判 FAIL(那是被测物消失,不是被类型层挡住)。
#   (B) **前置存活自检**:先证明头文件在、每个负例点名的符号在、一个必然合法的片段
#       编得过。缺一即 exit 1 ⇒「被测物消失」不可能再冒充「类型约束生效」。
#   (C) **机制对照臂**:同样负例在 CHDSP_STRICT_TYPES=0 下必须**全部编译通过**
#       ⇒ 证明失败确由强类型造成,而非片段本身写错。(critic 补造的对照,原样纳入。)
#
# ⭐ 自查:「这个检查失败时,会阻止什么?」
#    ⇒ exit 1 ⇒ run_r3.sh 的 NEG 非 0 ⇒ run_r3.sh 整体 exit 1(见该脚本 2026-08-04 整改)
#    ⇒ 阻止本轮结果被当作通过。
#
# 复核方式(critic 可原样重跑):
#    实证 A  sed -i 's/chdsp_apply_gain/chdsp_apply_gain_v2/g' chdsp_fixed.h  ⇒ 必须 FAIL
#    实证 B  mv chdsp_fixed.h /tmp/                                          ⇒ 必须 FAIL
#    正常构建                                                                ⇒ 仍 8/8 PASS
# ============================================================================
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CC="${CC:-gcc}"
CFLAGS="-std=gnu99 -Wall -Wextra -I${HERE}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0; ctrl_bad=0
mk() { cat > "$TMP/t.c"; }

echo "CHK-10  负向编译测试(CHDSP_STRICT_TYPES=1)"
echo "  编译器: $($CC --version | head -1)"
echo

# ---------------------------------------------------------------------------
# (B) 前置存活自检 —— 被测物必须真的在
# ---------------------------------------------------------------------------
echo "  --- (B) 前置存活自检:被测物必须真的在 ---"
preflight_bad=0
if [ ! -f "$HERE/chdsp_fixed.h" ]; then
  echo "    ⛔ 缺文件 $HERE/chdsp_fixed.h"; preflight_bad=1
else
  # 每个负例点名的符号都必须在头文件里 —— 少一个,对应负例就是在测【不存在的接口】
  for sym in chdsp_io_q0_31_t chdsp_smp_q4_27_t chdsp_coef_q4_27_t chdsp_db_q23_8_t \
             chdsp_gain_q4_27_t chdsp_acc_t chdsp_io_from_raw chdsp_smp_from_raw \
             chdsp_coef_from_raw chdsp_io_to_smp chdsp_smp_to_io chdsp_apply_gain \
             chdsp_db chdsp_acc_clear chdsp_io_raw chdsp_sat_reset; do
    if ! grep -qE "\b${sym}\b" "$HERE/chdsp_fixed.h"; then
      echo "    ⛔ 符号 $sym 在被测头文件里找不到 ⇒ 相关负例测的是【不存在的接口】"
      preflight_bad=1
    fi
  done
fi
# 正面编译自检:一个必然合法的片段必须编得过,否则是环境/包含路径坏了,不是类型层在起作用
cat > "$TMP/pf.c" <<'EOF'
#define CHDSP_STRICT_TYPES 1
#include "chdsp_fixed.h"
int f(void){ chdsp_smp_q4_27_t a = chdsp_smp_from_raw(1); return (int)chdsp_smp_raw(a); }
EOF
if ! $CC $CFLAGS -c "$TMP/pf.c" -o "$TMP/pf.o" 2>"$TMP/pf.log"; then
  echo "    ⛔ 合法片段编译失败 ⇒ 编译环境/包含路径本身有问题:"
  head -3 "$TMP/pf.log" | sed 's/^/       /'
  preflight_bad=1
fi
if [ $preflight_bad -ne 0 ]; then
  echo "  ⛔ 前置自检失败 ⇒ 本检查无意义,直接 FAIL(⛔ 不得报 PASS)"
  exit 1
fi
echo "    头文件在 / 16 个符号全在 / 合法片段编得过 ✓"
echo

# ---------------------------------------------------------------------------
# (A) 负例:必须因【预期的那条具体错误】而失败
# ---------------------------------------------------------------------------
# ⛔ 这两类命中一律判 FAIL:它们说明被测物没了,而不是类型层挡住了
DISQUALIFY='No such file or directory|没有那个文件|implicit declaration|隐式声明|undeclared|未声明'

expect_fail() {
  local tag="$1" want="$2" desc="$3"
  local log="$TMP/${tag}.log"
  if $CC $CFLAGS -c "$TMP/t.c" -o "$TMP/t.o" >"$log" 2>&1; then
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 竟然编译通过了(类型层没挡住)"; fail=$((fail+1)); return
  fi
  if grep -qE "$DISQUALIFY" "$log"; then
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 失败原因是【被测物不存在】,不是被类型层挡住"
    head -3 "$log" | sed 's/^/         /'; fail=$((fail+1)); return
  fi
  if grep -qE "$want" "$log"; then
    echo "  [PASS] $tag  $desc  ⇒ 命中预期错误 /$want/"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 失败了,但**不是预期的那条错误**(片段本身写错?接口变了?)"
    head -3 "$log" | sed 's/^/         /'; fail=$((fail+1))
  fi
}
expect_ok() {
  local tag="$1" desc="$2"
  if $CC $CFLAGS -c "$TMP/t.c" -o "$TMP/t.o" >"$TMP/err.txt" 2>&1; then
    echo "  [PASS] $tag  $desc  ⇒ 编译通过(符合预期)"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 正当用法被挡掉了"
    sed 's/^/         /' "$TMP/err.txt" | head -5; fail=$((fail+1))
  fi
}

HDR='#define CHDSP_STRICT_TYPES 1
#include "chdsp_fixed.h"'

echo "  --- (A) 负例:必须因【预期的那条具体错误】失败 ---"

# ---- N1: 把 io 样本(Q0.31)传给收链内样本(Q4.27)的函数 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_io_q0_31_t io = chdsp_io_from_raw(123);
    chdsp_sat_t st;
    (void)chdsp_smp_to_io(io, &st);      /* ⛔ 需要 smp,给了 io */
}
EOF
expect_fail N1 'incompatible type|expected .chdsp_smp_q4_27_t' "io(Q0.31) 当 smp(Q4.27) 用"

# ---- N2: 把系数传给收样本的函数 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_coef_q4_27_t c = chdsp_coef_from_raw(1);
    chdsp_sat_t st;
    (void)chdsp_smp_to_io(c, &st);       /* ⛔ 系数不是样本(同 Q 格式,不同量纲) */
}
EOF
expect_fail N2 'incompatible type|expected .chdsp_smp_q4_27_t' "coef 当 smp 用(Q 格式相同、量纲不同)"

# ---- N3: 两种样本直接相加 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_io_q0_31_t  a = chdsp_io_from_raw(1);
    chdsp_smp_q4_27_t b = chdsp_smp_from_raw(1);
    chdsp_smp_q4_27_t c = a + b;         /* ⛔ 跨定标裸相加 */
    (void)c;
}
EOF
expect_fail N3 'invalid operands' "跨定标裸相加(io + smp)"

# ---- N4: 把 dB 当线性增益用 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_db_q23_8_t d = chdsp_db(6);
    chdsp_smp_q4_27_t x = chdsp_smp_from_raw(1000);
    chdsp_sat_t st;
    (void)chdsp_apply_gain(x, d, &st);   /* ⛔ dB 不是线性增益 */
}
EOF
expect_fail N4 'incompatible type|expected .chdsp_gain_q4_27_t' "dB 当线性增益用(本项目最贵的一类量纲错)"

# ---- N5: 绕过接口自己对累加器移位 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_acc_t acc;
    chdsp_smp_q4_27_t y;
    chdsp_acc_clear(&acc);
    y = (chdsp_smp_q4_27_t)(acc >> 27);  /* ⛔ 自选移位 —— 本头文件要消灭的写法 */
    (void)y;
}
EOF
expect_fail N5 'invalid operands|conversion to non-scalar' "调用方自己写 (acc >> 27)"

echo
# ---------------------------------------------------------------------------
# (C) 机制对照臂 —— critic 补造,原样纳入
# ---------------------------------------------------------------------------
echo "  --- (C) 机制对照臂:同样负例在 STRICT_TYPES=0 下必须【全部编译通过】 ---"
echo "      ⇒ 证明上面的失败来自【强类型】,不是片段本身写错(D6-d 的机械形式)"
CTRL_HDR='#define CHDSP_STRICT_TYPES 0
#include "chdsp_fixed.h"'
ctrl_one() {
  local tag="$1"
  if $CC $CFLAGS -Wno-error -c "$TMP/t.c" -o "$TMP/t.o" >"$TMP/c_$tag.log" 2>&1; then
    echo "    [对照 OK] $tag 在 STRICT=0 下编译通过 ⇒ 该负例的失败确由强类型造成"
  else
    echo "    [⛔ 对照失败] $tag 在 STRICT=0 下也编不过 ⇒ 片段本身有问题,该负例无效"
    head -2 "$TMP/c_$tag.log" | sed 's/^/         /'; ctrl_bad=$((ctrl_bad+1))
  fi
}
mk <<EOF
$CTRL_HDR
void f(void) { chdsp_io_q0_31_t io = chdsp_io_from_raw(123); chdsp_sat_t st;
               (void)chdsp_smp_to_io(io, &st); }
EOF
ctrl_one N1
mk <<EOF
$CTRL_HDR
void f(void) { chdsp_coef_q4_27_t c = chdsp_coef_from_raw(1); chdsp_sat_t st;
               (void)chdsp_smp_to_io(c, &st); }
EOF
ctrl_one N2
mk <<EOF
$CTRL_HDR
void f(void) { chdsp_io_q0_31_t a = chdsp_io_from_raw(1);
               chdsp_smp_q4_27_t b = chdsp_smp_from_raw(1);
               chdsp_smp_q4_27_t c = a + b; (void)c; }
EOF
ctrl_one N3
mk <<EOF
$CTRL_HDR
void f(void) { chdsp_db_q23_8_t d = chdsp_db(6); chdsp_smp_q4_27_t x = chdsp_smp_from_raw(1000);
               chdsp_sat_t st; (void)chdsp_apply_gain(x, d, &st); }
EOF
ctrl_one N4
echo "    (N5 不列入对照:acc 右移在裸整数下本就合法,其失败→通过的翻转正是预期)"

echo
echo "  --- 正当用法必须编译通过(护栏的第二个方向,D6-y) ---"
# ---- P1: 同类型赋值 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_smp_q4_27_t a = chdsp_smp_from_raw(1);
    chdsp_smp_q4_27_t b = a;
    (void)b;
}
EOF
expect_ok P1 "同类型赋值"

# ---- P2: 经函数做定标转换 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_io_q0_31_t io = chdsp_io_from_raw(1 << 20);
    chdsp_smp_q4_27_t s = chdsp_io_to_smp(io);
    chdsp_sat_t st; chdsp_sat_reset(&st);
    (void)chdsp_smp_to_io(s, &st);
}
EOF
expect_ok P2 "经 chdsp_io_to_smp / chdsp_smp_to_io 转换"

# ---- P3: 取 raw 值做 I/O 打包 ----
mk <<EOF
$HDR
#include <stdint.h>
int32_t f(chdsp_io_q0_31_t x) { return chdsp_io_raw(x); }
EOF
expect_ok P3 "chdsp_io_raw() 取值(打 TDM 帧的正当用法)"

echo
echo "CHK-10 合计: PASS=$pass  FAIL=$fail  对照失败=$ctrl_bad"
if [ $fail -eq 0 ] && [ $ctrl_bad -eq 0 ]; then echo "CHK-10 ⇒ PASS"; exit 0
else echo "CHK-10 ⇒ ⛔ FAIL"; exit 1; fi
