#!/bin/bash
# r88 流水:闸门 → (过才)主对比 → 归并。⛔ 未经 critic 评审。预注册 = PREREG_r88.txt
# ⛔ 不用 timeout 包。cell 不再套 setsid(本脚本已 setsid;再套会让 wait 提前返回)
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
echo "[$(date +%H:%M:%S)] 闸门起跑(G2 配置断言 + G1 器械能力空测)"
python3 r88_gate.py > r88_gate.log 2>&1
rc=$?
echo "[$(date +%H:%M:%S)] 闸门退出码 = $rc"
if [ "$rc" -ne 0 ]; then
  echo "⛔⛔ 闸门未过 ⇒ **主对比没有启动**(D6-ap)。"; echo "GATE_FAILED" > r88_STATUS.txt; exit 1
fi
echo "[$(date +%H:%M:%S)] 闸门通过 ⇒ 起 6 个 cell"
go () { nohup python3 r88_cell.py --t60 "$2" --sd "$3" --tag "$1" > "r88_cell_$1.log" 2>&1 & echo "  launched $1 pid=$!"; }
go t02s0 0.2 0; go t02s1 0.2 1; go t02s2 0.2 2
go t05s0 0.5 0; go t05s1 0.5 1; go t05s2 0.5 2
wait
for i in $(seq 1 60); do n=$(ls r88_cell_*.json 2>/dev/null | wc -l); [ "$n" -ge 6 ] && break; echo "[$(date +%H:%M:%S)] 等待落盘 $n/6"; sleep 10; done
echo "[$(date +%H:%M:%S)] 归并"
python3 r88_merge.py > r88_merge.log 2>&1
echo "[$(date +%H:%M:%S)] 归并退出码 = $? ⇒ 输出 r88_plant_out.txt"
echo "DONE" > r88_STATUS.txt
