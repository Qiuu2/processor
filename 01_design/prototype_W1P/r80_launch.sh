#!/bin/bash
# r80 合成实验:1 base + 7 Δf 档 = 8 worker。⛔ 未经 critic 评审。
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
setsid nohup python3 r80_cell.py --df 0 --base 1 --tag BASE > r80_cell_BASE.log 2>&1 &
echo "launched BASE pid=$!"
for d in 2 3 5 8 12 20 200; do
  t=$(printf "D%03d" $d)
  setsid nohup python3 r80_cell.py --df $d --tag $t > "r80_cell_$t.log" 2>&1 &
  echo "launched $t (Δf=$d Hz) pid=$!"
done
