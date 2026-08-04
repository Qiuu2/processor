#!/usr/bin/env bash
# ⭐⭐ 变异自证 —— **硬闸门**,且是杀伤矩阵的【前置】。⛔ 门禁状态:未过门。
#
# ============================================================================
# 为什么这道闸门必须在杀伤矩阵【之前】
# ----------------------------------------------------------------------------
# 杀伤矩阵回答的是「打开这个宏之后有检查变红吗」,
# **不是**「这个宏真的做了它名字声称的那件事吗」。
#
# 前任实证(memory 任务三):`CHDSP_BROKEN_HPF_AFTER_DYN` 声称"把 HPF 挪到动态之后",
# 实际挪到了 AEC 钩子之后 —— **仍在动态之前**。它当时"存活"了,反而逼人去看。
# ⇒ **若它恰好被别的检查杀死,就会留下一条【假的杀伤记录】。**
# ⇒ **存活是可见的,假杀伤是隐形的** —— 而一份 16/16 的报告看起来完美无缺。
#
# ⇒ ∴ 规则:**探针没变 ⇒ 该变异无效 ⇒ ⛔ 不许进杀伤矩阵,不计入杀伤率。**
#
# ⭐ 自查:「本检查失败时,会阻止什么?」
#    ⇒ exit 1 ⇒ run_all.sh 非 0 ⇒ 阻止交付。
#    ⛔ 并且:任一变异自证失败 ⇒ 该轮杀伤率**作废**(不是"扣一分"),因为分母不可信。
#
# 两个 Phase,分工是本质的:
#   Phase A(结构)· 链序类变异声称的是【位置】,行为探针证不了位置。
#      ⇒ 用 `gcc -E` 读**预处理后的真实调用顺序**,断言声称的先后关系确实翻转。
#      ⇒ 这才是能抓住"挪了,但没挪到声称的地方"的那一种。
#   Phase B(行为)· 其余变异声称的是【某个可测量的行为】。
#      ⇒ probe_mutants.c 打印全部探针读数;本脚本对变异 M 只比 M 自己那一行。
# ============================================================================
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
FIXED="$(cd "$ROOT/../01_design/fixedpoint" && pwd)"
CC="${CC:-gcc}"
CFLAGS="-std=gnu99 -O2 -I$ROOT/src -I$FIXED"
SRC="$ROOT/src/chdsp_biquad.c $ROOT/src/chdsp_detector.c $ROOT/src/chdsp_delay.c \
     $ROOT/src/chdsp_dynamics.c $ROOT/src/chdsp_fir.c $ROOT/src/chdsp_chain.c $ROOT/src/chdsp_notch.c \
     $FIXED/chdsp_fixed.c"
B="$ROOT/build_mv"; rm -rf "$B"; mkdir -p "$B"
pass=0; fail=0

echo "================================================================"
echo "变异自证(硬闸门 · 杀伤矩阵的前置)"
echo "  规则:探针读数未变 ⇒ 该变异没做到它声称的事 ⇒ ⛔ 不得进杀伤矩阵"
echo "================================================================"

# ---------------------------------------------------------------------------
# Phase A:结构探针 —— 读预处理后的**真实调用顺序**
# ---------------------------------------------------------------------------
# 用法:order_of <宏定义串> <函数名> <正则>  ⇒ 打印该正则在该函数体内首次命中的序号
order_of() {
  local defs="$1" fn="$2" pat="$3"
  $CC $CFLAGS $defs -E "$ROOT/src/chdsp_chain.c" 2>/dev/null \
    | sed -n "/^[a-z].*$fn(/,/^}/p" \
    | grep -n "$pat" | head -1 | cut -d: -f1
}
# 断言:好版本里 A 在 B 之前,变异版里 A 在 B 之后(⇒ 位置关系确实翻转了)
phase_a_flip() {
  local tag="$1" macro="$2" fn="$3" patA="$4" patB="$5" nameA="$6" nameB="$7"
  local ga gb ma mb
  ga=$(order_of ""            "$fn" "$patA"); gb=$(order_of ""            "$fn" "$patB")
  ma=$(order_of "-D$macro=1"  "$fn" "$patA"); mb=$(order_of "-D$macro=1"  "$fn" "$patB")
  if [ -z "$ga" ] || [ -z "$gb" ] || [ -z "$ma" ] || [ -z "$mb" ]; then
    echo "  [FAIL] $tag  ⛔ 探针取不到位置(好 $nameA=$ga $nameB=$gb / 变异 $nameA=$ma $nameB=$mb)"
    echo "         ⇒ 探针本身失效 ⇒ 本条自证无意义,判 FAIL(⛔ 不得当作通过)"
    fail=$((fail+1)); return
  fi
  printf "  %-28s 好版本: %s@%s %s@%s   变异后: %s@%s %s@%s\n" \
         "$macro" "$nameA" "$ga" "$nameB" "$gb" "$nameA" "$ma" "$nameB" "$mb"
  if [ "$ga" -lt "$gb" ] && [ "$ma" -gt "$mb" ]; then
    echo "  [PASS] $tag  ⇒ $nameA 确实从 $nameB【之前】挪到了【之后】—— 变异名副其实"
    pass=$((pass+1))
  else
    echo "  [FAIL] $tag  ⛔ 位置关系**没有按声称的方向翻转**"
    echo "         ⇒ 这正是前任踩过的坑:挪了,但没挪到声称的地方"
    echo "         ⇒ 该变异无效,⛔ 不许进杀伤矩阵(它的"被杀死"会是一条假记录)"
    fail=$((fail+1))
  fi
}
# 断言:某段代码在好版本里存在、在变异版里消失
phase_a_gone() {
  local tag="$1" macro="$2" fn="$3" pat="$4" what="$5"
  local g m
  g=$($CC $CFLAGS -E "$ROOT/src/chdsp_chain.c" 2>/dev/null | sed -n "/^[a-z].*$fn(/,/^}/p" | grep -c "$pat")
  m=$($CC $CFLAGS -D$macro=1 -E "$ROOT/src/chdsp_chain.c" 2>/dev/null | sed -n "/^[a-z].*$fn(/,/^}/p" | grep -c "$pat")
  printf "  %-28s 好版本出现 %s 次 ⇒ 变异后 %s 次(%s)\n" "$macro" "$g" "$m" "$what"
  if [ "$g" -gt 0 ] && [ "$m" -eq 0 ]; then
    echo "  [PASS] $tag  ⇒ 该段确实被移除了 —— 变异名副其实"; pass=$((pass+1))
  else
    echo "  [FAIL] $tag  ⛔ 该段没有按声称被移除 ⇒ 变异无效,不许进杀伤矩阵"; fail=$((fail+1))
  fi
}

echo
echo "--- Phase A:结构探针(链序类变异声称的是【位置】)---"
phase_a_flip A1 CHDSP_BROKEN_HPF_AFTER_DYN chdsp_in_ch_process \
  'chdsp_bq_chain_process(&ch->hpf' 'chdsp_gate_gain1' 'HPF' '门'
# ⚠ A2 的声称方向与 A1 相反:好版本 PEQ 在分频【之后】,变异把它提到【之前】。
#   ⇒ 传参顺序必须是(分频, PEQ)才对得上 phase_a_flip 的「A 从 B 之前挪到之后」语义。
#   〔留痕:首跑我按 (PEQ, 分频) 传,自证报 FAIL —— 那是**我的断言方向写反**,不是变异无效。
#    读数本身(好 PEQ@126 分频@117 ⇒ 变异 PEQ@114 分频@117)当时就已证明变异是名副其实的。
#    ⇒ 记一条:自证探针报 FAIL 时,**先问是被测物错了还是判据错了** —— 与
#      「被测量选错时 PASS 和 FAIL 都不是证据」同族。〕
phase_a_flip A2 CHDSP_BROKEN_CHAIN_ORDER chdsp_out_ch_process \
  'chdsp_bq_chain_process(&ch->xo_hp' 'chdsp_bq_chain_process(&ch->peq' '分频' 'PEQ'
phase_a_gone A3 CHDSP_BROKEN_XO_POLARITY chdsp_out_ch_process \
  'xo_polarity_flip' '极性翻转段'

# ⭐ A4(r13):hook_afc 必须在陷波器组【之前】—— 这是「AFC 本块请求、本块生效」的结构前提。
#   ⚠ 为什么用结构探针而不是行为探针:行为探针只能测"全链第 0 块能量",而链上**任何**改动
#     (限幅前视、陷波不写系数…)都会带动它 ⇒ 对"位置"这个主张太粗,会产出一堆假连带。
#     ⇒ 实测过:它确实被 LIM_NOLOOK 与 NOTCH_NOWRITE 两条带动。
#   ⇒ **位置的主张,用位置去证。**
phase_a_flip A4 CHDSP_BROKEN_AFC_AFTER_NOTCH chdsp_in_ch_process \
  'chdsp_hook_run(&ch->hook_afc' 'chdsp_bq_chain_process(&ch->notch' 'AFC钩子' '陷波器组'

# ---------------------------------------------------------------------------
# Phase B:行为探针
# ---------------------------------------------------------------------------
echo
echo "--- Phase B:行为探针(只比该变异自己那一行读数)---"
if ! $CC $CFLAGS "$HERE/probe_mutants.c" $SRC -o "$B/probe_good" -lm 2>"$B/build_good.log"; then
  echo "  ⛔ 好版本探针编译失败 ⇒ 本闸门无意义,直接 FAIL"
  sed 's/^/    /' "$B/build_good.log" | head -10; exit 1
fi
"$B/probe_good" > "$B/good.txt" 2>&1 || { echo "  ⛔ 好版本探针运行失败"; exit 1; }
n_probe=$(grep -c '^PROBE ' "$B/good.txt")
echo "  好版本探针读数 $n_probe 条 ✓"

# 变异宏 → 它声称改变的那个探针 TAG
declare -A CLAIM=(
  [CHDSP_BROKEN_WRAP]=P_WRAP
  [CHDSP_BROKEN_TRUNC]=P_TRUNC
  [CHDSP_BROKEN_NOEF]=P_NOEF
  [CHDSP_BROKEN_BQ_NORAMP]=P_BQ_NORAMP
  [CHDSP_BROKEN_BQ_TIE_FREE]=P_BQ_TIE_FREE
  [CHDSP_BROKEN_POW_NARROW]=P_POW_NARROW
  [CHDSP_BROKEN_DET_ONEDIR]=P_DET_ONEDIR
  [CHDSP_BROKEN_GATE_NEGATIVE]=P_GATE_NEGATIVE
  [CHDSP_BROKEN_NO_HYST]=P_NO_HYST
  [CHDSP_BROKEN_LIM_NOLOOK]=P_LIM_NOLOOK
  [CHDSP_BROKEN_COMP_HARDKNEE]=P_COMP_HARDKNEE
  [CHDSP_BROKEN_FIR_ASYM]=P_FIR_ASYM
  [CHDSP_BROKEN_FIR_NOBYPASS]=P_FIR_NOBYPASS
  [CHDSP_BROKEN_BUTTER_COS]=P_BUTTER_COS
  [CHDSP_BROKEN_BESSEL_RBJ]=P_BESSEL_RBJ
  [CHDSP_BROKEN_XO_UNIT]=P_XO_UNIT
  [CHDSP_BROKEN_NOTCH_EVICT_FIXED]=P_NOTCH_EVICT
  [CHDSP_BROKEN_NOTCH_RESET_ALL]=P_NOTCH_RESET
  [CHDSP_BROKEN_GUARD_BY_S]=P_GUARD_BY_S
  [CHDSP_BROKEN_NOTCH_MRU]=P_NOTCH_MRU
  [CHDSP_BROKEN_NOTCH_NOWRITE]=P_NOTCH_NOWRITE
  [CHDSP_BROKEN_HOOK_SKIP]=P_HOOK_SKIP
  [CHDSP_BROKEN_NO_SATTEL]=P_NO_SATTEL
  [CHDSP_BROKEN_SLOPE_CONV]=P_SLOPE_CONV
  [CHDSP_BROKEN_XO_NORANGE]=P_XO_NORANGE
  [CHDSP_BROKEN_BUTTER_KOFF]=P_BUTTER_KOFF
  [CHDSP_BROKEN_BESSEL_SCALE]=P_BESSEL_SCALE
  [CHDSP_BROKEN_LR_ODD_OK]=P_LR_ODD_OK
  [CHDSP_BROKEN_FIRSTORDER]=P_FIRSTORDER
  [CHDSP_BROKEN_SMOOTH_FIXED]=P_SMOOTH_FIXED
  [CHDSP_BROKEN_GATE_ENUM]=P_GATE_ENUM
  [CHDSP_BROKEN_COEF_NOCONST]=P_COEF_NOCONST
)

# ---------------------------------------------------------------------------
# ⭐⭐ 断言 ②:它**没声称要改的**那些行为,逐位没变
# ---------------------------------------------------------------------------
# 缘起(lead 转 critic 在设计侧 d34_analysis.py 查出的两条):
#   ① 一个名叫「系数退化到 16-bit」的变异,**顺手把结构约束量化也关了**
#      ⇒ 拆开跑:16bit ∧ 关约束 = FAIL 6;只 16bit = FAIL 4(EXP-3c/4a 不再被杀)
#      ⇒ **那两条杀伤记在了错的原因上。**
#   ② docstring 宣称 4 个 broken 模式,只实现了 2 个 ⇒ 另两个跑起来一个字节都没变,
#      而结果头**照印**「坏版本开关: xo_order」⇒ 归档件看起来完全像「该变异存活」。
#
# ⇒ 这是形态⑤的**镜像**:
#     形态⑤ = 变异**没实现**它声称的缺陷;
#     本条   = 变异**实现了它没声称的**缺陷。
#   ⇒ 两者都产出【假的杀伤记录】,而假杀伤是隐形的。
#
# ⇒ 规则:除 CLAIM 的那条探针外,其余探针**必须逐位不变**;
#   确有**物理上不可分割**的连带效应时,须在 ALSO 里**显式声明并写明理由**
#   ⇒ ⛔ 声明是留痕,不是豁免:任何**未声明**的连带变化一律 FAIL。
declare -A ALSO=(
  [CHDSP_BROKEN_TRUNC]="P_NOEF"
  [CHDSP_BROKEN_BUTTER_COS]="P_BUTTER_KOFF"
  [CHDSP_BROKEN_BUTTER_KOFF]="P_BUTTER_COS"
  [CHDSP_BROKEN_BESSEL_RBJ]="P_BESSEL_SCALE"
  [CHDSP_BROKEN_BESSEL_SCALE]="P_BESSEL_RBJ"
  [CHDSP_BROKEN_GATE_ENUM]="P_GATE_NEGATIVE P_NO_HYST"
  [CHDSP_BROKEN_SMOOTH_FIXED]="P_DET_ONEDIR P_LIM_NOLOOK P_COMP_HARDKNEE"
  [CHDSP_BROKEN_WRAP]="P_NO_SATTEL"
)
declare -A ALSO_WHY=(
  [CHDSP_BROKEN_TRUNC]="舍入模式**就是量化器的一部分**,而 P_NOEF 测的正是量化误差功率 ⇒ 同一处改动的第二个观测面,不是第二个缺陷"
  [CHDSP_BROKEN_BUTTER_COS]="两条探针都读 butter_q 的输出(一条 BW3、一条 BW4)⇒ 同一个函数的两个观测面"
  [CHDSP_BROKEN_BUTTER_KOFF]="同上,方向相反"
  [CHDSP_BROKEN_BESSEL_RBJ]="两条探针都读 Bessel 系数(一条 a1 之和、一条 max|b|)⇒ 同一族系数的两个观测面"
  [CHDSP_BROKEN_BESSEL_SCALE]="同上,方向相反"
  [CHDSP_BROKEN_SMOOTH_FIXED]="chdsp_smooth_from_ms 是**全部检测器共用**的平滑系数函数 ⇒ 冻住它,门/压限/限幅的时间常数一起变。这是改动点本身的作用域,不是三个缺陷"
  [CHDSP_BROKEN_WRAP]="把饱和换成回绕 ⇒ **根本不再发生饱和** ⇒ chdsp_sat_tripped 永不为真 ⇒ 链内饱和计数必然归零。⇒ 是同一处改动的必然后果,不是第二个缺陷"
  [CHDSP_BROKEN_GATE_ENUM]="⚠ 这一条要说清:门的**行为完全没变**,变的是状态的【数值编码】(CLOSED 从 0 变 1)。P_GATE_NEGATIVE / P_NO_HYST 读的正是 (int)g.state ⇒ 它们的读数必然跟着编码走。⇒ 是**表示**的连带,不是第二个缺陷"
)
# ---------------------------------------------------------------------------
# ⛔ 名单对表(整改 2026-08-04 · critic 02impl MAJOR-3)
# ---------------------------------------------------------------------------
# critic 的实证:从 CLAIM 里**删掉一个变异登记** ⇒ 本脚本报 PASS=15 /「分母可信」/ exit 0,
# 而杀伤矩阵仍然跑 16 个 ⇒ **少自证的那一个照样进了矩阵、照样计入杀伤率。**
# ⇒ 「自证覆盖了全部变异」这句话**没有任何机械手段守着** —— 它只是一句话。
# ⇒ 修法:直接从 run_kill_matrix.sh 读 MUTS/FIXED_MUTS,取**对称差**,非空即 FAIL。
KM="$HERE/run_kill_matrix.sh"
echo
echo "--- 名单对表:自证覆盖面 vs 杀伤矩阵名单(⛔ 对称差必须为空)---"
if [ ! -f "$KM" ]; then
  echo "  ⛔ 找不到 $KM ⇒ 无法对表 ⇒ 判 FAIL(⛔ 不得当作通过)"; fail=$((fail+1))
else
  km_list=$(sed -n '/^\(MUTS\|FIXED_MUTS\)=(/,/^)/p' "$KM" \
            | grep -oE 'CHDSP_BROKEN_[A-Z0-9_]+' | sort -u)
  # 结构类变异不走行为探针(它们由 Phase A 覆盖)⇒ 显式登记,⛔ 不是默默豁免
  STRUCT="CHDSP_BROKEN_HPF_AFTER_DYN CHDSP_BROKEN_CHAIN_ORDER CHDSP_BROKEN_XO_POLARITY CHDSP_BROKEN_AFC_AFTER_NOTCH"
  self_list=$( { for k in "${!CLAIM[@]}"; do echo "$k"; done; for k in $STRUCT; do echo "$k"; done; } | sort -u)
  only_km=$(comm -23 <(echo "$km_list") <(echo "$self_list"))
  only_sv=$(comm -13 <(echo "$km_list") <(echo "$self_list"))
  echo "  杀伤矩阵 $(echo "$km_list" | grep -c .) 个 / 自证覆盖 $(echo "$self_list" | grep -c .) 个"
  if [ -z "$only_km" ] && [ -z "$only_sv" ]; then
    echo "  [PASS] 名单对表  ⇒ 对称差为空 ⇒ **进矩阵的每一个都自证过**,杀伤率的分母可信"
    pass=$((pass+1))
  else
    [ -n "$only_km" ] && { echo "  [FAIL] ⛔ 在杀伤矩阵里、但**没有自证**:"; echo "$only_km" | sed 's/^/         /'; }
    [ -n "$only_sv" ] && { echo "  [FAIL] ⛔ 自证登记了、但**不在杀伤矩阵里**(死登记):"; echo "$only_sv" | sed 's/^/         /'; }
    echo "         ⇒ 杀伤率的分母不可信 ⇒ 本轮杀伤结论作废"
    fail=$((fail+1))
  fi
fi
echo

for M in "${!CLAIM[@]}"; do
  TAG="${CLAIM[$M]}"
  gv=$(grep "^PROBE $TAG " "$B/good.txt" | awk '{print $3}')
  if [ -z "$gv" ]; then
    echo "  [FAIL] $M  ⛔ 好版本里没有探针 $TAG ⇒ 该变异没有自证探针"; fail=$((fail+1)); continue
  fi
  if ! $CC $CFLAGS -D$M=1 "$HERE/probe_mutants.c" $SRC -o "$B/probe_$M" -lm 2>"$B/b_$M.log"; then
    echo "  [FAIL] $M  ⛔ 变异版探针编译失败 ⇒ 无法自证"; sed 's/^/         /' "$B/b_$M.log" | head -3
    fail=$((fail+1)); continue
  fi
  "$B/probe_$M" > "$B/o_$M.txt" 2>&1
  mv=$(grep "^PROBE $TAG " "$B/o_$M.txt" | awk '{print $3}')
  if [ -z "$mv" ]; then
    echo "  [FAIL] $M  ⛔ 变异版探针未输出 $TAG"; fail=$((fail+1)); continue
  fi
  printf "  %-30s %-18s 好=%-22s 变异=%-22s\n" "$M" "$TAG" "$gv" "$mv"
  # ---- 断言 ①:声称要改的,确实变了 ----
  if [ "$gv" != "$mv" ]; then
    echo "  [PASS] $M ①  ⇒ 声称改变的量确实变了 —— 变异名副其实"; pass=$((pass+1))
  else
    echo "  [FAIL] $M ①  ⛔ **读数没变** ⇒ 该变异没做到它声称的事(形态⑤)"
    echo "         ⇒ ⛔ 不许进杀伤矩阵;若它在矩阵里「被杀死」,那是一条【假的杀伤记录】"
    fail=$((fail+1))
  fi
  # ---- 断言 ②:没声称要改的,逐位没变 ----
  allowed=" $TAG ${ALSO[$M]:-} "
  stray=""
  while read -r _p tag val; do
    [ "$_p" = "PROBE" ] || continue
    case "$allowed" in *" $tag "*) continue ;; esac
    gval=$(grep "^PROBE $tag " "$B/good.txt" | awk '{print $3}')
    [ "$gval" = "$val" ] || stray="$stray $tag(好=$gval 变异=$val)"
  done < "$B/o_$M.txt"
  if [ -z "$stray" ]; then
    if [ -n "${ALSO[$M]:-}" ]; then
      echo "  [PASS] $M ②  ⇒ 其余探针逐位未变(已声明连带:${ALSO[$M]} —— ${ALSO_WHY[$M]})"
    else
      echo "  [PASS] $M ②  ⇒ 其余探针**逐位未变** ⇒ 该变异只注入了它声称的那一个缺陷"
    fi
    pass=$((pass+1))
  else
    echo "  [FAIL] $M ②  ⛔ **未声明的连带变化**:$stray"
    echo "         ⇒ 该变异注入了【不止一个】缺陷 ⇒ 杀伤会归错因(critic 在设计侧抓到的同型)"
    echo "         ⇒ ⛔ 不许进杀伤矩阵:要么拆成两个变异,要么在 ALSO 里声明并写明理由"
    fail=$((fail+1))
  fi
done

echo
echo "================================================================"
echo "变异自证合计: PASS=$pass  FAIL=$fail"
if [ $fail -eq 0 ]; then
  echo "⇒ 全部变异名副其实 ⇒ 杀伤矩阵的分母可信 ⇒ PASS"; exit 0
else
  echo "⛔ 有变异未通过自证 ⇒ **本轮杀伤率作废**(分母不可信,不是扣一分)⇒ FAIL"; exit 1
fi
