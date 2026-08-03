#!/usr/bin/env python3
"""生成 chdsp_tables.h(dB↔线性 查表)。
表长选择依据见 D34_FIXEDPOINT_CONVENTION_v0.1.md §7 与 check_fixed.c CHK-7。
⚠ 本脚本是表的唯一来源;表改了要重跑本脚本并重跑 CHK-7。
"""
import math, sys, os

EXP2_BITS = 7                 # 128 项 + 1 端点
LOG2_BITS = 7
EXP2_N = 1 << EXP2_BITS
LOG2_N = 1 << LOG2_BITS

# 2^(i/N) ∈ [1,2],存 Q2.29(2.0 = 2^30,int32 内)
exp2_tab = [int(round(2.0 ** (i / EXP2_N) * (1 << 29))) for i in range(EXP2_N + 1)]
# log2(1 + i/N) ∈ [0,1],存 Q0.31
log2_tab = [int(round(math.log2(1.0 + i / LOG2_N) * (1 << 31))) for i in range(LOG2_N + 1)]
log2_tab = [min(v, (1 << 31) - 1) for v in log2_tab]

K = math.log2(10) / 20.0
K_Q40 = int(round(K * (1 << 40)))
INVK_Q24 = int(round((1.0 / K) * (1 << 24)))     # 1/K = 20/log2(10) ≈ 6.0206

def emit(f, name, vals, per_line=6):
    f.write(f"static const int32_t {name}[{len(vals)}] = {{\n")
    for i in range(0, len(vals), per_line):
        f.write("    " + ", ".join(f"{v:11d}" for v in vals[i:i + per_line]) + ",\n")
    f.write("};\n\n")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chdsp_tables.h")
with open(out, "w") as f:
    f.write("/* 自动生成 —— 由 gen_tables.py 产出,⛔ 请勿手改。\n"
            " * 门禁状态:未过门(随 chdsp_fixed.h 一同送审)。\n */\n")
    f.write("#ifndef CHDSP_TABLES_H\n#define CHDSP_TABLES_H\n#include <stdint.h>\n\n")
    f.write(f"#define CHDSP_EXP2_BITS {EXP2_BITS}\n#define CHDSP_EXP2_N {EXP2_N}\n")
    f.write(f"#define CHDSP_LOG2_BITS {LOG2_BITS}\n#define CHDSP_LOG2_N {LOG2_N}\n")
    f.write(f"/* K = log2(10)/20 = {K:.17f} */\n")
    f.write(f"#define CHDSP_K_Q40    ((int64_t){K_Q40})\n")
    f.write(f"#define CHDSP_INVK_Q24 ((int64_t){INVK_Q24})\n\n")
    f.write("/* 2^(i/128),Q2.29,i = 0..128 */\n")
    emit(f, "chdsp_exp2_tab_q29", exp2_tab)
    f.write("/* log2(1 + i/128),Q0.31,i = 0..128 */\n")
    emit(f, "chdsp_log2_tab_q31", log2_tab)
    f.write("#endif /* CHDSP_TABLES_H */\n")

print(f"wrote {out}: exp2 {len(exp2_tab)} entries, log2 {len(log2_tab)} entries, "
      f"K_Q40={K_Q40}, INVK_Q24={INVK_Q24}")
print(f"表内存合计 = {(len(exp2_tab)+len(log2_tab))*4} B")
