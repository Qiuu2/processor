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
     $ROOT/src/chdsp_chain.c $ROOT/src/chdsp_notch.c $FIXED/chdsp_fixed.c"
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
  CHDSP_BROKEN_BUTTER_COS     # biquad(r8):butter_q 退回 cos 式 ⇒ 奇数阶 BW 静默算错
  CHDSP_BROKEN_BESSEL_RBJ     # biquad(r8):Bessel 退回逐节 RBJ ⇒ 高阶高通错到 90 dB
  CHDSP_BROKEN_XO_UNIT        # biquad(r9):极性 mod 4 算在 dB/oct 上 ⇒ LR2/LR6 深谷
  CHDSP_BROKEN_NOTCH_EVICT_FIXED  # notch(r10):回收时把固定槽也算进候选
  CHDSP_BROKEN_NOTCH_RESET_ALL    # notch(r10):复位动态槽时把固定槽也清掉
  CHDSP_BROKEN_GUARD_BY_S         # biquad(r11):包络守卫退回按 S 守 ⇒ CHK-B1b 声称要防的回退
  CHDSP_BROKEN_NOTCH_MRU          # notch(r12):回收最新而不是最早(LRU→MRU)
  CHDSP_BROKEN_NOTCH_NOWRITE      # notch(r12):只记簿记不写系数
  CHDSP_BROKEN_HOOK_SKIP          # chain(r12):AGC 插入点不再被调用
  CHDSP_BROKEN_NO_SATTEL          # chain(r12):链内饱和不计数(C-B 遥测失效)
  CHDSP_BROKEN_SLOPE_CONV         # biquad(r12):dB/oct→阶数 换算因子写错
  CHDSP_BROKEN_XO_NORANGE         # biquad(r12):极性函数去掉量程守卫
  CHDSP_BROKEN_BUTTER_KOFF        # biquad(r12):butter_q 的 k 偏一位
  CHDSP_BROKEN_BESSEL_SCALE       # biquad(r12):Bessel 归一化写错 ⇒ 系数放大
  CHDSP_BROKEN_LR_ODD_OK          # biquad(r12):LR 接受奇数阶
  CHDSP_BROKEN_FIRSTORDER         # biquad(r12):一阶节系数写错
  CHDSP_BROKEN_SMOOTH_FIXED       # detector(r12):平滑系数不随 tau 变
  CHDSP_BROKEN_GATE_ENUM          # dynamics(r12):安全状态挪离 0 ⇒ 全 0 初始化落错侧
  CHDSP_BROKEN_COEF_NOCONST       # fixed(r12):系数界退回只靠 int32 边界
  CHDSP_BROKEN_AFC_AFTER_NOTCH    # chain(r13):hook_afc 挪到陷波之后 ⇒ 请求晚一块生效
  CHDSP_BROKEN_BESSEL_FREEQ       # biquad(r15):Bessel 退回自由量化 ⇒ 绕过 CHK-5f 守卫
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


# ============================================================================
# ⭐ 杀伤覆盖率(整改 2026-08-04 · critic 02impl MAJOR-5)
# ----------------------------------------------------------------------------
# critic 是**手工**数出「29 条检查里 14 条没有任何变异杀得死」的,而这个比例在 r2 变差
# (14/29 → 21/40)——**没有任何机械手段在跟踪它**,所以变差了也没人知道。
# ⇒ 本段把它变成可测量的:
#     全部检查 tag  ∖  在任一变异下出现过 [FAIL] 的 tag  =  【无证伪证据】的检查
# ⇒ 并做成**棘轮**:超过 config 里登记的上限即 FAIL。
#   ⛔ 为什么是棘轮而不是"必须为 0":现在就要求 0 会让构建长期红,而红着的闸门没人看;
#      棘轮**只允许变好**,新增检查若不配变异会当场把数顶上去 ⇒ 立刻可见。
#   ⚠ 那个上限是【我登记的数】,不是判据 —— 它必须随整改单调下降,⛔ 不许往上调。
# ============================================================================
all_tags=$(grep -oE '^\s*\[(PASS|FAIL)\] +CHK-[A-Za-z0-9]+' "$BUILD/good.txt" \
           | grep -oE 'CHK-[A-Za-z0-9]+' | sort -u)
killed_tags=$(cat "$BUILD"/o_*.txt "$BUILD"/fo_*.txt 2>/dev/null \
           | grep -oE '^\s*\[FAIL\] +CHK-[A-Za-z0-9]+' \
           | grep -oE 'CHK-[A-Za-z0-9]+' | sort -u)

# ---- 两类【正当】的无杀手,各自有理由,且都是【推导出来的/显式声明的】,⛔ 不是手工塞进来的 ----
# (a) 回归项:critic MAJOR-4 已判定它们零分辨力 —— 那正是给它们加标注的理由。
#     ⇒ 从 good.txt 里**按标注推导**,⛔ 不手工维护名单(手工名单会变成藏东西的地方)。
#   ⚠ 只取每行【第一个】 CHK tag —— 标注里还写着"分辨力在 CHK-Y1c"之类的**替代条**,
#     若把整行的 tag 都抓进来,会把那些**有分辨力的替代条**也一起豁免掉(首版就是这个错:
#     6 条回归项被数成 12 条)。⇒ 豁免名单错误地变大 = 欠账被低估。
regress_tags=$(grep -E '保留为回归项' "$BUILD/good.txt" \
           | sed -nE 's/^[^C]*\b(CHK-[A-Za-z0-9]+).*/\1/p' | sort -u)
# (b) 前提自检:它们断言的是【测试台自己有分辨力】,不是产品行为
#     ⇒ 产品变异本就不该杀死它们。必须**显式声明 + 写明理由**(同自证的 ALSO 机制)。
PRECOND="CHK-Y1c0 CHK-Y2b0 CHK-N5a CHK-C3a CHK-T4a CHK-A1a"
PRECOND_WHY="断言测试台的工作点落在有分辨力的区间(不是产品行为)⇒ 产品变异不该杀它们"
precond_tags=$(echo "$PRECOND" | tr ' ' '\n' | grep -c . >/dev/null; echo "$PRECOND" | tr ' ' '\n' | sort -u)

uncovered=$(comm -23 <(echo "$all_tags") <(echo "$killed_tags"))
debt=$(comm -23 <(echo "$uncovered") <(printf '%s\n' $regress_tags $precond_tags | sort -u))
n_all=$(echo "$all_tags" | grep -c .)
n_unc=$(echo "$uncovered" | grep -c .)
n_reg=$(echo "$regress_tags" | grep -c .)
n_pre=$(echo "$PRECOND" | wc -w)
n_debt=$(echo "$debt" | grep -c .)

echo
echo "================================================================"
echo "杀伤覆盖率(MAJOR-5)—— ⛔ 三类分开,合成一个数会掩盖差别"
echo "  检查总数 $n_all;无任何变异杀得死 $n_unc,其中:"
echo "    · 回归项 $n_reg 条 —— critic MAJOR-4 已判零分辨力,加标注即为此(按标注自动推导)"
echo "    · 前提自检 $n_pre 条 —— $PRECOND_WHY"
echo "    · ⛔ **真欠账 $n_debt 条** —— 声称测产品行为,却没有任何变异能杀死它:"
echo "$debt" | sed 's/^/         /'
LIMIT=${CHDSP_KILL_UNCOVERED_MAX:-0}
if [ "$n_debt" -gt "$LIMIT" ]; then
  echo "  ⛔ 真欠账 $n_debt > 登记上限 $LIMIT ⇒ **覆盖率变差** ⇒ FAIL"
  echo "     ⇒ 新增检查必须同时新增能杀死它的变异,⛔ 不得只加检查"
  survived=$((survived+1))
else
  echo "  ⇒ 真欠账 $n_debt ≤ 登记上限 $LIMIT ✓(棘轮:只许降,⛔ 不许上调上限)"
fi

# ---- 棘轮的【已知失效模式】:它只在有人试图上调时才响 ----
# lead 指出:**「不新增检查」本身永远不会触发棘轮** ⇒ 一个人可以靠不写新检查让它永远安静,
# 而那正是我们最不想要的行为。⇒ 棘轮只防退步,不促前进。
# ⇒ 处置:记账 + 停滞时**显眼报出**(⛔ 不 FAIL —— 欠账不降可能是本轮在做别的,
#   把它做成 FAIL 会逼人为了绿而乱补变异,那比停滞更坏)。
HIST="$HERE/kill_coverage_history.txt"
echo "$(date -Iseconds) debt=$n_debt limit=$LIMIT total=$n_all" >> "$HIST"
n_same=$(awk '{print $2}' "$HIST" | tail -5 | sort -u | wc -l)
n_rows=$(wc -l < "$HIST")
if [ "$n_rows" -ge 3 ] && [ "$n_same" -eq 1 ]; then
  echo
  echo "  ⚠⚠ 停滞告警:最近 $(( n_rows < 5 ? n_rows : 5 )) 轮「真欠账」一直是 $n_debt,没有下降。"
  echo "     ⇒ 棘轮**只防退步、不促前进** —— 不写新检查就永远不会触发它。"
  echo "     ⇒ 若本轮确实在做别的,忽略;若连续多轮如此,说明这笔账在被绕开。"
  echo "     ⇒ 账本:$HIST"
fi

echo
echo "================================================================"
if [ $survived -eq 0 ]; then
  echo "杀伤矩阵:$total/$total 全部被杀死  ⇒ PASS"
  exit 0
else
  echo "⛔ 杀伤矩阵:$survived 个变异存活 ⇒ **对应检查不依赖被测物,必须补检查或删变异**"
  exit 1
fi
