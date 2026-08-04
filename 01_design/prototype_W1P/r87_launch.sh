#!/bin/bash
# r87 流水:**闸门 → (过才)主扫描 → 归并**。⛔ 未经 critic 评审。预注册 = PREREG_r87b.txt
# ⛔ 不用 timeout 包(前一实例被自己的 timeout 杀掉,退出码 143,白跑一轮)
cd /home/it1234/processor/01_design/prototype_W1P
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

echo "[$(date +%H:%M:%S)] 闸门起跑(G1 配置断言 + G2 修法可达性)"
python3 r87_gate.py > r87_gate.log 2>&1
rc=$?
echo "[$(date +%H:%M:%S)] 闸门退出码 = $rc"
if [ "$rc" -ne 0 ]; then
  echo "⛔⛔ 闸门未过 ⇒ **主扫描没有启动**(这就是中止条件该有的样子,D6-ap)。"
  echo "GATE_FAILED" > r87_STATUS.txt
  exit 1
fi

echo "[$(date +%H:%M:%S)] 闸门通过 ⇒ 起 6 个 cell(每种子一个 worker,独立日志/输出,D6-j)"
# ⚠ cell **不再套 setsid**:本脚本自身已 setsid 脱离会话;若 cell 再 setsid,
#   setsid 可能 fork ⇒ 直接子进程秒退 ⇒ `wait` 提前返回 ⇒ 归并读到半成品。
go () {  # tag t60 sd
  nohup python3 r87_cell.py --t60 "$2" --sd "$3" --tag "$1" > "r87_cell_$1.log" 2>&1 &
  echo "  launched $1 pid=$!"
}
go t02s0 0.2 0
go t02s1 0.2 1
go t02s2 0.2 2
go t05s0 0.5 0
go t05s1 0.5 1
go t05s2 0.5 2
wait
# 双保险:确认 6 份 json 都已落盘再归并(⛔ 不让归并读半成品)
for i in $(seq 1 60); do
  n=$(ls r87_cell_*.json 2>/dev/null | wc -l)
  [ "$n" -ge 6 ] && break
  echo "[$(date +%H:%M:%S)] 等待 cell 落盘 $n/6"
  sleep 10
done
echo "[$(date +%H:%M:%S)] 6 个 cell 全部结束 ⇒ 归并"
python3 r87_merge.py > r87_merge.log 2>&1
echo "[$(date +%H:%M:%S)] 归并退出码 = $? ⇒ 输出 r87_dmsg_out.txt"
echo "DONE" > r87_STATUS.txt
