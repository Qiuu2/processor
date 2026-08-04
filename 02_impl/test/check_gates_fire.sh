#!/usr/bin/env bash
# 元检查:**证明每一道闸门真的会响**。⛔ 门禁状态:未过门。
#
# ⭐ 缘起:critic 判 check_negcompile 为 BLOCKER(检查存在但不会响);
#    lead 要求「按『这个检查失败时会阻止什么』自查一遍全部自验」。
#    ⇒ 光自查不够 —— **自查也可能只是又一段文字**。本文件把它做成可执行的:
#      故意弄坏每一道闸门该守的东西,断言该闸门**确实变红**。
#    ⇒ 全部在 /tmp 的拷贝上做,⛔ 原件不动。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"
FIXED="$(cd "$ROOT/../01_design/fixedpoint" && pwd)"
pass=0; fail=0
mkwork(){ local w="$1"; rm -rf "$w"; mkdir -p "$w/01_design"; cp -r "$ROOT" "$w/02_impl"; cp -r "$FIXED" "$w/01_design/fixedpoint"; }

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
expect_red(){ local tag="$1" desc="$2" cmd="$3" w="$4"
  if ( cd "$w/02_impl" && eval "$cmd" ) >/dev/null 2>&1; then
    echo "  [FAIL] $tag  $desc ⇒ ⛔ 闸门**没有响**"; fail=$((fail+1))
  else
    echo "  [PASS] $tag  $desc ⇒ 闸门确实变红"; pass=$((pass+1)); fi }

echo "元检查:每一道闸门真的会响吗(硬闸门)"

W=/tmp/gates_a; mkwork $W
mutate $W/02_impl/src/chdsp_config.h 's/^#  define CHDSP_OUT_FIR_TAPS        256/#  define CHDSP_OUT_FIR_TAPS        1024/' &&
expect_red G1 "把 FIR 抽头改成超预算的 1024 ⇒ 编译期断言应拦住" \
  "gcc -std=gnu99 -O2 -I src -I ../01_design/fixedpoint -c src/chdsp_biquad.c -o /dev/null" $W

W=/tmp/gates_b; mkwork $W
mutate $W/02_impl/src/chdsp_delay.h 's|^#define CHDSP_DELAY_H|#define CHDSP_DELAY_H\nstatic const int chdsp_magic_probe = 512;|' &&
expect_red G2 "在非 config 头里写入魔数 512 ⇒ 魔数扫描应拦住" \
  "bash test/check_no_magic.sh" $W

W=/tmp/gates_c; mkwork $W
mutate $W/01_design/fixedpoint/chdsp_fixed.h 's/chdsp_apply_gain/chdsp_apply_gain_X/g' &&
expect_red G3 "把被测接口改名 ⇒ 负编译的前置存活自检应拦住" \
  "bash test/check_negcompile.sh" $W

W=/tmp/gates_d; mkwork $W
mutate $W/02_impl/test/check_modules.c 's/p2 == 1 \&\& p4 == 0/p2 == 0 \&\& p4 == 0/' &&
expect_red G4 "把一条断言改成错的 ⇒ 模块自验应变红并非 0 退出" \
  "gcc -std=gnu99 -O2 -I src -I ../01_design/fixedpoint test/check_modules.c src/*.c ../01_design/fixedpoint/chdsp_fixed.c -o /tmp/g4 -lm && /tmp/g4" $W

W=/tmp/gates_e; mkwork $W
mutate $W/02_impl/src/chdsp_biquad.c 's|^    return ((order % 4) == 2) ? 1 : 0;.*|    return 0;|' &&
expect_red G5 "把 LR 极性规则改坏 ⇒ 杀伤矩阵的阴性对照应变红" \
  "bash test/run_kill_matrix.sh" $W

rm -rf /tmp/gates_a /tmp/gates_b /tmp/gates_c /tmp/gates_d /tmp/gates_e
echo "  合计: PASS=$pass  FAIL=$fail"
[ $fail -eq 0 ] && { echo "  ⇒ 五道闸门全部确实会响 ⇒ PASS"; exit 0; } || { echo "  ⛔ 有闸门不会响 ⇒ FAIL"; exit 1; }
