#!/usr/bin/env bash
# 魔数扫描 —— **硬闸门**。⛔ 门禁状态:未过门。
# ⭐ 失败时阻止什么:阻止 run_all.sh 通过 ⇒ 阻止交付。
# 规则:仍在动的尺寸(FIR 抽头 / 分频阶数 / 陷波数 / PEQ 段数 / 帧长 / 通道数)
#      只能出现在 chdsp_config.h;其它 .c/.h 里出现其字面量即违规。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; SRC="$(cd "$HERE/../src" && pwd)"
bad=0
# 被禁的字面量 → 应当用的宏
declare -A M=( [512]=CHDSP_OUT_FIR_TAPS [256]=CHDSP_OUT_FIR_TAPS [128]=CHDSP_OUT_FIR_TAPS
               [48000]=CHDSP_FS_HZ )
echo "魔数扫描(硬闸门)"
for f in "$SRC"/*.c "$SRC"/*.h; do
  base="$(basename "$f")"
  [ "$base" = "chdsp_config.h" ] && continue
  for num in "${!M[@]}"; do
    # 只看代码行:排除注释行与文档行
    hits=$(grep -nE "(^|[^0-9A-Za-z_])$num([^0-9A-Za-z_]|$)" "$f" \
           | grep -vE '^\s*[0-9]+:\s*(\*|/\*|//|\s*\*)' | grep -vE '^\s*[0-9]+:\s*\*' || true)
    if [ -n "$hits" ]; then
      echo "  [⛔] $base 出现字面量 $num(应用 ${M[$num]}):"
      echo "$hits" | sed 's/^/       /' | head -3
      bad=$((bad+1))
    fi
  done
done
if [ $bad -eq 0 ]; then echo "  无魔数 ⇒ PASS"; exit 0
else echo "  ⛔ $bad 处魔数 ⇒ FAIL"; exit 1; fi
