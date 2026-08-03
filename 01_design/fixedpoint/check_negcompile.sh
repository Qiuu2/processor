#!/usr/bin/env bash
# CHK-10:负向编译测试 —— D-1「用接口不允许来防,不用文档提醒来防」的机械证明。
#   N1..N5 必须【编译失败】(量纲错误被类型层挡住)
#   P1..P3 必须【编译通过】(护栏没挡掉正当用法 —— 团队纪律 D6-y 的第二个方向)
# ⛔ 门禁状态:未过门。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CC="${CC:-gcc}"
CFLAGS="-std=gnu99 -Wall -Wextra -Werror -I${HERE}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
mk() { cat > "$TMP/t.c"; }
expect_fail() {
  local tag="$1" desc="$2"
  if $CC $CFLAGS -c "$TMP/t.c" -o "$TMP/t.o" >"$TMP/err.txt" 2>&1; then
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 竟然编译通过了(类型层没挡住)"; fail=$((fail+1))
  else
    echo "  [PASS] $tag  $desc  ⇒ 编译失败(符合预期)"; pass=$((pass+1))
  fi
}
expect_ok() {
  local tag="$1" desc="$2"
  if $CC $CFLAGS -c "$TMP/t.c" -o "$TMP/t.o" >"$TMP/err.txt" 2>&1; then
    echo "  [PASS] $tag  $desc  ⇒ 编译通过(符合预期)"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  $desc  ⇒ ⛔ 正当用法被挡掉了"; sed 's/^/         /' "$TMP/err.txt" | head -5; fail=$((fail+1))
  fi
}

echo "CHK-10  负向编译测试(CHDSP_STRICT_TYPES=1)"
echo "  编译器: $($CC --version | head -1)"
echo

HDR='#define CHDSP_STRICT_TYPES 1
#include "chdsp_fixed.h"'

# ---- N1: 把 io 样本(Q0.31)传给收链内样本(Q4.27)的函数 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_io_q0_31_t io = chdsp_io_from_raw(123);
    chdsp_sat_t st;
    (void)chdsp_smp_to_io(io, &st);      /* ⛔ 需要 smp,给了 io */
}
EOF
expect_fail N1 "io(Q0.31) 当 smp(Q4.27) 用"

# ---- N2: 把系数传给收样本的函数 ----
mk <<EOF
$HDR
void f(void) {
    chdsp_coef_q4_27_t c = chdsp_coef_from_raw(1);
    chdsp_sat_t st;
    (void)chdsp_smp_to_io(c, &st);       /* ⛔ 系数不是样本(同 Q 格式,不同量纲) */
}
EOF
expect_fail N2 "coef 当 smp 用(Q 格式相同、量纲不同)"

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
expect_fail N3 "跨定标裸相加(io + smp)"

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
expect_fail N4 "dB 当线性增益用(本项目最贵的一类量纲错)"

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
expect_fail N5 "调用方自己写 (acc >> 27)"

echo
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
echo "CHK-10 合计: PASS=$pass  FAIL=$fail"
exit $(( fail == 0 ? 0 : 1 ))
