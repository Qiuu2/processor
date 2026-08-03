#!/bin/bash
# r78 并行起跑 —— 5 配置 × 2 个 T60 层 = 10 worker(12 核)。⛔ 未经 critic 评审。
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
go () {  # tag shape match t60
  setsid nohup python3 r78_cell.py --shape "$2" --match "$3" --tag "$1" --t60 "$4" \
      > "r78_cell_$1_T$4.log" 2>&1 &
  echo "launched $1/T$4 pid=$!"
}
for t in 0.2 0.5; do
  go C1 0.2   none  $t     # (1/5 , →1/5 )  现状基线
  go C2 0.125 none  $t     # (1/8 , →1/8 )  两职同动,合规点
  go C3 0.1   none  $t     # (1/10, →1/10)  两职同动,合规下沿
  go C4 0.125 0.2   $t     # (1/8 , 1/5  )  ⭐ 只动形状
  go C5 0.2   0.125 $t     # (1/5 , 1/8  )  ⭐ 只动匹配窗
done
