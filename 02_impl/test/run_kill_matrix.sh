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

MUTS=(
  CHDSP_BROKEN_WRAP           # chdsp_fixed:窄化回绕
  CHDSP_BROKEN_TRUNC          # chdsp_fixed:截断代替就近舍入
  CHDSP_BROKEN_NOEF           # chdsp_fixed:关掉二阶误差反馈
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
  echo "杀伤矩阵:${#MUTS[@]}/${#MUTS[@]} 全部被杀死  ⇒ PASS"
  exit 0
else
  echo "⛔ 杀伤矩阵:$survived 个变异存活 ⇒ **对应检查不依赖被测物,必须补检查或删变异**"
  exit 1
fi
