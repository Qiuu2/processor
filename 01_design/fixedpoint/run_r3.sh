#!/usr/bin/env bash
# r1 验证跑批。⛔ 门禁状态:未过门。
# 纪律:①输出路径带轮次后缀,不复用 ②先清 build 产物 ③结果自带 deps 行
#
# ============================================================================
# ⭐ 2026-08-04 整改 · channel-dsp 实例 #2 · 闭 critic MAJOR-1
# ----------------------------------------------------------------------------
# critic 的判定(成立):
#   ①「变异存活」的报警分支**不可达**:
#        grep ... | grep -v ... | sed ...  || echo "⛔ 该变异存活!"
#      管道退出码 = 最后一个命令(sed)的退出码 = 恒 0 ⇒ `||` 后面永远不执行。
#      而 PREREG_FP_r1.txt:115 把「变异存活 ⇒ 该条作废」写成了**正式的证伪条件**
#      ⇒ 该证伪条件在交付件里没有任何能触发的东西(D6-v:没有 owner 的证伪条件 =
#        没有证伪条件)。本轮三个变异恰好都被杀死,所以没出事;**下一次新增变异时,
#        存活会表现为"标题下面空一行"。**
#   ② GOOD / NEG / REF 三个退出码**只被打印,不被消费**(脚本经 tee 退出,恒 0)
#      ⇒ D6-ap:「这个检查失败时会阻止什么?」答案是"什么也不阻止"。
#
# 本次整改:
#   · 变异存活 ⇒ 显式计数 + 记入 rc_all(不再靠管道退出码)
#   · 阴性对照有 FAIL ⇒ 记入 rc_all
#   · GOOD / NEG / REF 全部记入 rc_all
#   · 脚本以 rc_all 退出(⛔ 不再恒 0);tee 的退出码用 PIPESTATUS 绕开
# ⇒ 自查:「本脚本失败时会阻止什么?」⇒ 非 0 退出 ⇒ 阻止本轮结果被当作通过。
# ============================================================================
set -u
rc_all=0
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
CC="${CC:-gcc}"
CFLAGS="-std=gnu99 -O2 -Wall -Wextra -I."
OUT="results_fp_r3.txt"

echo "清 build 产物..." >&2
rm -rf build_r3 bitexact_strict0.txt bitexact_strict1.txt db_table_c.txt
mkdir -p build_r3

sha() { sha256sum "$1" | cut -c1-16; }

{
echo "================================================================================"
echo "results_fp_r2  —  定点格式与量纲约定 · 第 2 轮(r1 两条不达标后的独立再观测)"
echo "预注册: PREREG_FP_r1.txt@$(sha PREREG_FP_r1.txt) + PREREG_FP_r2_addendum.txt@$(sha PREREG_FP_r2_addendum.txt) + PREREG_FP_r3_addendum.txt@$(sha PREREG_FP_r3_addendum.txt)"
echo "门禁状态: 未过门(未经独立 critic 评审)"
echo "跑批时间: $(date -Iseconds)"
echo "deps: chdsp_fixed.h@$(sha chdsp_fixed.h), chdsp_fixed.c@$(sha chdsp_fixed.c),"
echo "      chdsp_tables.h@$(sha chdsp_tables.h), check_fixed.c@$(sha check_fixed.c),"
echo "      gen_tables.py@$(sha gen_tables.py), ref_fixed.py@$(sha ref_fixed.py)"
echo "编译器: $($CC --version | head -1)"
echo "已清 build 产物: 是(rm -rf build_r3 + 全部输出 txt)"
echo "================================================================================"
echo

echo "################ 1. 好版本(出货构建) ################"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 check_fixed.c chdsp_fixed.c -o build_r3/chk_good -lm || exit 1
( cd build_r3 && ./chk_good ); GOOD=$?
echo "好版本退出码 = $GOOD"
echo

echo "################ 2. 坏版本(假绿纪律:必须 FAIL) ################"
for BR in CHDSP_BROKEN_WRAP CHDSP_BROKEN_TRUNC CHDSP_BROKEN_NOEF; do
  echo "---- 坏版本: -D$BR=1 ----"
  $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -D$BR=1 check_fixed.c chdsp_fixed.c -o build_r3/chk_$BR -lm || exit 1
  ( cd build_r3 && ./chk_$BR ) > build_r3/out_$BR.txt 2>&1
  RC=$?
  grep -E '^\s*\[(PASS|FAIL)\]' build_r3/out_$BR.txt | sed 's/^/    /'
  echo "    坏版本 $BR 退出码 = $RC  (非 0 = 被杀死,符合假绿纪律)"
  echo
done

echo "################ 2b. 杀伤矩阵(FORCE_GOOD_ASSERT=1:同一份好判据跑在坏模块上) ################"
for BR in CHDSP_BROKEN_WRAP CHDSP_BROKEN_TRUNC CHDSP_BROKEN_NOEF; do
  $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -DCHDSP_CHECK_FORCE_GOOD_ASSERT=1 -D$BR=1 \
      check_fixed.c chdsp_fixed.c -o build_r3/kill_$BR -lm || exit 1
  ( cd build_r3 && ./kill_$BR ) > build_r3/kill_$BR.txt 2>&1
  echo "  ---- 变异 $BR ----"
  echo "    被杀死的 CHK(不含 CHK-0 的构建自检):"
  # ⛔ 整改(critic MAJOR-1):不得再用 `管道 || echo` —— 管道退出码恒 0,报警永不触发。
  #    改为**显式计数**,并把结论记进 rc_all(⇒ 存活会真的阻止本脚本通过)。
  n_kill=$(grep -E '^\s*\[FAIL\]' build_r3/kill_$BR.txt | grep -vc 'CHK-0')
  if [ "$n_kill" -gt 0 ]; then
    grep -E '^\s*\[FAIL\]' build_r3/kill_$BR.txt | grep -v 'CHK-0' | sed 's/^/      /'
    echo "    ⇒ 该变异被 $n_kill 条 CHK 杀死 ✓"
  else
    echo "      ⛔ 无 —— **该变异存活!**"
    echo "      ⇒ 命中 PREREG_FP_r1.txt:115 的证伪条件:对应 CHK 不依赖被测物,该条作废"
    rc_all=1
  fi
done
# 阴性对照:好模块 + 好判据,不应有 FAIL
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -DCHDSP_CHECK_FORCE_GOOD_ASSERT=1 \
    check_fixed.c chdsp_fixed.c -o build_r3/kill_none -lm || exit 1
( cd build_r3 && ./kill_none ) > build_r3/kill_none.txt 2>&1
echo "  ---- 阴性对照(无变异)----"
if grep -qE '^\s*\[FAIL\]' build_r3/kill_none.txt; then
  echo "    ⛔ 无变异时也有 FAIL ⇒ 上面的杀死**不可归因于变异**:"
  grep -E '^\s*\[FAIL\]' build_r3/kill_none.txt | sed 's/^/      /'
  rc_all=1
else
  echo "    无 FAIL ✓ ⇒ 上面的杀死确实由变异引起,不是检查本身红的"
fi
echo

echo "################ 3. CHK-9 强类型开关的数值中立性 ################"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 check_fixed.c chdsp_fixed.c -o build_r3/chk_s1 -lm
$CC $CFLAGS -DCHDSP_STRICT_TYPES=0 check_fixed.c chdsp_fixed.c -o build_r3/chk_s0 -lm
( cd build_r3 && ./chk_s1 >/dev/null 2>&1 ; ./chk_s0 >/dev/null 2>&1 )
if [ -f build_r3/bitexact_strict1.txt ] && [ -f build_r3/bitexact_strict0.txt ]; then
  N1=$(wc -l < build_r3/bitexact_strict1.txt)
  D=$(diff -q build_r3/bitexact_strict1.txt build_r3/bitexact_strict0.txt >/dev/null 2>&1 && echo SAME || echo DIFF)
  echo "  STRICT=1 vs STRICT=0:$N1 个样本,逐位 $D"
  # 阳性对照:证明这个比对器【认得出】差异(团队纪律:24/24 相同 ∧ 强制错值出现差异)
  sed '5000s/.*/999999/' build_r3/bitexact_strict0.txt > build_r3/bitexact_forced_bad.txt
  D2=$(diff -q build_r3/bitexact_strict1.txt build_r3/bitexact_forced_bad.txt >/dev/null 2>&1 && echo SAME || echo DIFF)
  echo "  阳性对照(强制把第 5000 行改成错值):逐位 $D2  ⇒ 比对器 $( [ "$D2" = DIFF ] && echo 认得出差异 || echo ⛔无分辨力 )"
  # ⛔ 整改(critic MAJOR-1 / D6-ap):这两条原来只打印,不阻断
  [ "$D"  = SAME ] || { echo "  ⛔ STRICT=1 与 =0 数值不一致"; rc_all=1; }
  [ "$D2" = DIFF ] || { echo "  ⛔ 阳性对照失败:比对器无分辨力 ⇒ 上一行的 SAME 无意义"; rc_all=1; }
else
  echo "  ⛔ 逐位输出文件缺失"
  rc_all=1
fi
echo

echo "################ 4. CHK-10 负向编译测试 ################"
bash check_negcompile.sh; NEG=$?
echo "CHK-10 退出码 = $NEG"
echo

echo "################ 5. 第二轨(python 独立重写)对表 ################"
( cd build_r3 && python3 ../ref_fixed.py ); REF=$?
echo "第二轨退出码 = $REF"
echo

echo "================================================================================"
echo "汇总: 好版本=$GOOD(0=全过) 负向编译=$NEG 第二轨=$REF"
# ⛔ 整改(critic MAJOR-1 ②):这三个退出码原来只被打印,不被消费。现在全部消费。
[ "$GOOD" -eq 0 ] || { echo "⛔ 好版本(出货构建)有 FAIL"; rc_all=1; }
[ "$NEG"  -eq 0 ] || { echo "⛔ 负向编译 CHK-10 未通过"; rc_all=1; }
[ "$REF"  -eq 0 ] || { echo "⛔ 第二轨对表未通过"; rc_all=1; }
if [ $rc_all -eq 0 ]; then echo "本轮: PASS(全部环节通过)"
else echo "⛔ 本轮: FAIL —— 上面至少一环未通过,本轮结果不得被当作通过"; fi
echo "================================================================================"
exit $rc_all
} 2>&1 | tee "$OUT"
rc_all=${PIPESTATUS[0]}          # ⛔ tee 恒 0,必须用 PIPESTATUS 取回块的退出码

echo "结果已写入 $HERE/$OUT (退出码 $rc_all)" >&2
exit $rc_all
