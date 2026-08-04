#!/bin/bash
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
go(){ nohup python3 r91_conv.py --t60 "$2" --sd "$3" --tag "$1" > "r91_cell_$1.log" 2>&1 & echo "  $1 pid=$!"; }
go t02s0 0.2 0; go t02s1 0.2 1; go t02s2 0.2 2; go t05s1 0.5 1; go t05s2 0.5 2
wait
echo "DONE" > r91_STATUS.txt
