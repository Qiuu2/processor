#!/bin/bash
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
echo "[$(date +%H:%M:%S)] r88b 闸门(解析先验)"
python3 r88b_gate.py > r88b_gate.log 2>&1; rc=$?
echo "[$(date +%H:%M:%S)] 闸门退出码 = $rc"
if [ "$rc" -ne 0 ]; then echo "⛔⛔ 闸门未过 ⇒ 主对比没有启动"; echo "GATE_FAILED" > r88b_STATUS.txt; exit 1; fi
go () { nohup python3 r88b_cell.py --t60 "$2" --sd "$3" --tag "$1" > "r88b_cell_$1.log" 2>&1 & echo "  launched $1 pid=$!"; }
go t02s0 0.2 0; go t02s1 0.2 1; go t02s2 0.2 2; go t05s0 0.5 0; go t05s1 0.5 1; go t05s2 0.5 2
wait
for i in $(seq 1 60); do n=$(ls r88b_cell_*.json 2>/dev/null | wc -l); [ "$n" -ge 6 ] && break; sleep 10; done
python3 r88b_merge.py > r88b_merge.log 2>&1
echo "[$(date +%H:%M:%S)] 归并退出码 = $? ⇒ r88b_plant_out.txt"; echo "DONE" > r88b_STATUS.txt
