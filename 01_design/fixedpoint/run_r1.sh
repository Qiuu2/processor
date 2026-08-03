#!/usr/bin/env bash
# r1 验证跑批。⛔ 门禁状态:未过门。
# 纪律:①输出路径带轮次后缀,不复用 ②先清 build 产物 ③结果自带 deps 行
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
CC="${CC:-gcc}"
CFLAGS="-std=gnu99 -O2 -Wall -Wextra -I."
OUT="results_fp_r1.txt"

echo "清 build 产物..." >&2
rm -rf build_r1 bitexact_strict0.txt bitexact_strict1.txt db_table_c.txt
mkdir -p build_r1

sha() { sha256sum "$1" | cut -c1-16; }

{
echo "================================================================================"
echo "results_fp_r1  —  定点格式与量纲约定 · 第 1 轮验证结果"
echo "预注册: PREREG_FP_r1.txt@$(sha PREREG_FP_r1.txt)"
echo "门禁状态: 未过门(未经独立 critic 评审)"
echo "跑批时间: $(date -Iseconds)"
echo "deps: chdsp_fixed.h@$(sha chdsp_fixed.h), chdsp_fixed.c@$(sha chdsp_fixed.c),"
echo "      chdsp_tables.h@$(sha chdsp_tables.h), check_fixed.c@$(sha check_fixed.c),"
echo "      gen_tables.py@$(sha gen_tables.py), ref_fixed.py@$(sha ref_fixed.py)"
echo "编译器: $($CC --version | head -1)"
echo "已清 build 产物: 是(rm -rf build_r1 + 全部输出 txt)"
echo "================================================================================"
echo

echo "################ 1. 好版本(出货构建) ################"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 check_fixed.c chdsp_fixed.c -o build_r1/chk_good -lm || exit 1
( cd build_r1 && ./chk_good ); GOOD=$?
echo "好版本退出码 = $GOOD"
echo

echo "################ 2. 坏版本(假绿纪律:必须 FAIL) ################"
for BR in CHDSP_BROKEN_WRAP CHDSP_BROKEN_TRUNC CHDSP_BROKEN_NOEF; do
  echo "---- 坏版本: -D$BR=1 ----"
  $CC $CFLAGS -DCHDSP_STRICT_TYPES=1 -D$BR=1 check_fixed.c chdsp_fixed.c -o build_r1/chk_$BR -lm || exit 1
  ( cd build_r1 && ./chk_$BR ) 2>&1 | grep -E '^\s*\[(PASS|FAIL)\]|^CHK|^  \[' | sed 's/^/    /'
  echo "    坏版本 $BR 退出码 = ${PIPESTATUS[0]}"
  echo
done

echo "################ 3. CHK-9 强类型开关的数值中立性 ################"
$CC $CFLAGS -DCHDSP_STRICT_TYPES=1 check_fixed.c chdsp_fixed.c -o build_r1/chk_s1 -lm
$CC $CFLAGS -DCHDSP_STRICT_TYPES=0 check_fixed.c chdsp_fixed.c -o build_r1/chk_s0 -lm
( cd build_r1 && ./chk_s1 >/dev/null 2>&1 ; ./chk_s0 >/dev/null 2>&1 )
if [ -f build_r1/bitexact_strict1.txt ] && [ -f build_r1/bitexact_strict0.txt ]; then
  N1=$(wc -l < build_r1/bitexact_strict1.txt)
  D=$(diff -q build_r1/bitexact_strict1.txt build_r1/bitexact_strict0.txt >/dev/null 2>&1 && echo SAME || echo DIFF)
  echo "  STRICT=1 vs STRICT=0:$N1 个样本,逐位 $D"
  # 阳性对照:证明这个比对器【认得出】差异(团队纪律:24/24 相同 ∧ 强制错值出现差异)
  sed '5000s/.*/999999/' build_r1/bitexact_strict0.txt > build_r1/bitexact_forced_bad.txt
  D2=$(diff -q build_r1/bitexact_strict1.txt build_r1/bitexact_forced_bad.txt >/dev/null 2>&1 && echo SAME || echo DIFF)
  echo "  阳性对照(强制把第 5000 行改成错值):逐位 $D2  ⇒ 比对器 $( [ "$D2" = DIFF ] && echo 认得出差异 || echo ⛔无分辨力 )"
else
  echo "  ⛔ 逐位输出文件缺失"
fi
echo

echo "################ 4. CHK-10 负向编译测试 ################"
bash check_negcompile.sh; NEG=$?
echo "CHK-10 退出码 = $NEG"
echo

echo "################ 5. 第二轨(python 独立重写)对表 ################"
( cd build_r1 && python3 ../ref_fixed.py ); REF=$?
echo "第二轨退出码 = $REF"
echo

echo "================================================================================"
echo "汇总: 好版本=$GOOD(0=全过) 负向编译=$NEG 第二轨=$REF"
echo "================================================================================"
} 2>&1 | tee "$OUT"

echo "结果已写入 $HERE/$OUT" >&2
