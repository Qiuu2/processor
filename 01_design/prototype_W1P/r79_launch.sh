#!/bin/bash
# r79 等预算线 NN×bw_oct ≡ 1.00 oct。12 worker(12 核),NN=24 按单种子拆(它最重)。
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
go () {  # tag nn bw t60 seeds
  setsid nohup python3 r79_cell.py --nn "$2" --bw "$3" --ncand 48 --tag "$1" \
      --t60 "$4" --seeds "$5" > "r79_cell_$1_T$4_s${5//,/}.log" 2>&1 &
  echo "launched $1 NN=$2 T60=$4 seeds=$5 pid=$!"
}
for t in 0.2 0.5; do
  go N08  8 0.125        $t 0,1,2
  go N10 10 0.1          $t 0,1,2
  go N16 16 0.0625       $t 0,1,2
  for s in 0 1 2; do go N24 24 0.0416666667 $t $s; done
done
