#!/usr/bin/env bash
# 杀伤矩阵 —— **硬闸门**。⛔ 门禁状态:未过门。
#
# ⭐ 自查(lead 指示):「这个检查失败时,会阻止什么?」
#    答:**任一变异存活 ⇒ 本脚本 exit 1 ⇒ 阻止 run_all.sh 通过、阻止交付。**
#    ⛔ 本脚本不打印"仅供参考"的行;每一条都进退出码。
#
# 做法:同一份**好判据**(check_modules.c 不随变异改变)跑在每个坏模块上,
#       必须 FAIL(退出码非 0)。阴性对照:无变异时必须 PASS。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
FIXED="$(cd "$ROOT/../01_design/fixedpoint" && pwd)"
CC="${CC:-gcc}"
CFLAGS="-std=gnu99 -O2 -Wall -Wextra -I$ROOT/src -I$FIXED"
SRC="$HERE/check_modules.c $ROOT/src/chdsp_biquad.c $ROOT/src/chdsp_detector.c \
     $ROOT/src/chdsp_delay.c $ROOT/src/chdsp_dynamics.c $ROOT/src/chdsp_fir.c \
     $ROOT/src/chdsp_chain.c $FIXED/chdsp_fixed.c"
BUILD="$ROOT/build_kill"
rm -rf "$BUILD"; mkdir -p "$BUILD"

# ⚠ 变异必须跑在【拥有它的那个检查二进制】上。
#   chdsp_fixed 的三个变异(WRAP/TRUNC/NOEF)由 01_design/fixedpoint/check_fixed.c 拥有,
#   check_modules.c 不测它们 ⇒ 若放在这里跑,会"存活"而给出错误的杀伤率。
#   ⇒ 它们在 FIXED_MUTS 里,单独用 check_fixed 跑。
FIXED_MUTS=(
  CHDSP_BROKEN_WRAP
  CHDSP_BROKEN_TRUNC
  CHDSP_BROKEN_NOEF
)
MUTS=(
  CHDSP_BROKEN_BQ_NORAMP      # biquad:系数直接跳变
  CHDSP_BROKEN_BQ_TIE_FREE    # biquad:HPF/LPF 自由量化
  CHDSP_BROKEN_POW_NARROW     # detector:功率状态截回 Q4.27
  CHDSP_BROKEN_DET_ONEDIR     # detector:attack/release 不分方向
  CHDSP_BROKEN_GATE_NEGATIVE  # dynamics:门改否定式豁免
  CHDSP_BROKEN_NO_HYST        # dynamics:去掉迟滞
  CHDSP_BROKEN_LIM_NOLOOK     # dynamics:去掉限幅前视
  CHDSP_BROKEN_COMP_HARDKNEE  # dynamics:软拐点退化为硬拐点
  CHDSP_BROKEN_FIR_ASYM       # fir:抽头非对称
  CHDSP_BROKEN_FIR_NOBYPASS   # fir:关闭时不透传
  CHDSP_BROKEN_CHAIN_ORDER    # chain:D4 把 PEQ 放到分频之前
  CHDSP_BROKEN_XO_POLARITY    # chain:忽略 LR 极性规则
  CHDSP_BROKEN_HPF_AFTER_DYN  # chain:D3 把 HPF 放到动态之后
)

echo "================================================================"
echo "杀伤矩阵(硬闸门)  变异数 = ${#MUTS[@]}"
echo "================================================================"

# ---- 阴性对照:无变异必须通过 ----
if ! $CC $CFLAGS $SRC -o "$BUILD/good" -lm 2>"$BUILD/good_build.log"; then
  echo "⛔ 好版本编译失败:"; sed 's/^/    /' "$BUILD/good_build.log"; exit 1
fi
if ! "$BUILD/good" > "$BUILD/good.txt" 2>&1; then
  echo "⛔ 阴性对照失败:**无变异时就有 FAIL** ⇒ 杀伤结论不可归因于变异"
  grep -E '^\s*\[FAIL\]' "$BUILD/good.txt" | sed 's/^/    /'
  exit 1
fi
echo "  阴性对照(无变异):PASS ✓  ⇒ 下面的杀死可归因于变异"
echo

survived=0
total=$(( ${#MUTS[@]} + ${#FIXED_MUTS[@]} ))

# ---- 地基件(chdsp_fixed)的变异:跑它自己的检查二进制 ----
FSRC="$FIXED/check_fixed.c $FIXED/chdsp_fixed.c"
if $CC -std=gnu99 -O2 -Wall -Wextra -I$FIXED $FSRC -o "$BUILD/fx_good" -lm 2>/dev/null; then
  for M in "${FIXED_MUTS[@]}"; do
    # ⚠ 自审抓出的同型缺陷:原写法**没有区分【编译失败】与【被检查杀死】**
    #   —— 编译失败时可执行文件不存在,子 shell 也返回非 0 ⇒ 会被记成"已杀死"
    #   ⇒ 那就是一个【不会响的报警】,与 critic 判 BLOCKER 的负编译同型。
    if ! $CC -std=gnu99 -O2 -Wall -Wextra -I$FIXED -DCHDSP_CHECK_FORCE_GOOD_ASSERT=1 -D$M=1 \
         $FSRC -o "$BUILD/fx_$M" -lm 2>"$BUILD/fb_$M.log"; then
      echo "  [编译失败] $M ⇒ ⛔ 不算杀死"; sed 's/^/      /' "$BUILD/fb_$M.log" | head -2
      survived=$((survived+1)); continue
    fi
    ( cd "$BUILD" && ./fx_$M ) > "$BUILD/fo_$M.txt" 2>&1
    if [ $? -ne 0 ]; then
      k=$(grep -E '^\s*\[FAIL\]' "$BUILD/fo_$M.txt" | grep -v 'CHK-0' | awk '{print $2}' | tr '\n' ' ')
      echo "  [已杀死] $M  ⇐ $k  (由 check_fixed 拥有)"
    else
      echo "  [⛔ 存活] $M  —— 由 check_fixed 拥有,却没被抓到"; survived=$((survived+1))
    fi
  done
else
  echo "  ⛔ check_fixed 编译失败 ⇒ 地基件的三个变异无法判定"; survived=$((survived+3))
fi

for M in "${MUTS[@]}"; do
  if ! $CC $CFLAGS -D$M=1 $SRC -o "$BUILD/m_$M" -lm 2>"$BUILD/b_$M.log"; then
    echo "  [编译失败] $M"; sed 's/^/      /' "$BUILD/b_$M.log" | head -3; survived=$((survived+1)); continue
  fi
  "$BUILD/m_$M" > "$BUILD/o_$M.txt" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    killers=$(grep -E '^\s*\[FAIL\]' "$BUILD/o_$M.txt" | awk '{print $2}' | tr '\n' ' ')
    echo "  [已杀死] $M  ⇐ $killers"
  else
    echo "  [⛔ 存活] $M  —— **没有任何检查抓到它**"
    survived=$((survived+1))
  fi
done

echo
echo "================================================================"
if [ $survived -eq 0 ]; then
  echo "杀伤矩阵:$total/$total 全部被杀死  ⇒ PASS"
  exit 0
else
  echo "⛔ 杀伤矩阵:$survived 个变异存活 ⇒ **对应检查不依赖被测物,必须补检查或删变异**"
  exit 1
fi
