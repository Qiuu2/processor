#!/bin/bash
# r76 并行起跑 —— 13 个 worker(12 核)。⛔ 未经 critic 评审。
# 每个 worker 独立日志 + 独立输出路径(D6-j)。
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

go () {  # tag src fix tlow oracle
  setsid nohup python3 r76_cell.py --src "$2" --fix "$3" --tlow "$4" --oracle "$5" --tag "$1" \
      > "r76_cell_$1.log" 2>&1 &
  echo "launched $1 pid=$!"
}

# ── 主栅格 T_low = −45 ────────────────────────────────────────────
go s60f0 -60 0 -45 1
go s60f1 -60 1 -45 0
go s40f0 -40 0 -45 1
go s40f1 -40 1 -45 0
go s30f0 -30 0 -45 1
go s30f1 -30 1 -45 0
go s20f0 -20 0 -45 1
go s20f1 -20 1 -45 0
go s10f0 -10 0 -45 1
go s10f1 -10 1 -45 0
# ── 臂 T:只动 T_low(−50),两端 ──────────────────────────────────
go t50s60 -60 0 -50 0
go t50s20 -20 0 -50 0
# ── 固定 G 表 ────────────────────────────────────────────────────
setsid nohup python3 r76_fixedG.py > r76_fixedG.log 2>&1 &
echo "launched fixedG pid=$!"
