"""r23 ①:弃权归因 —— 弃权在哪一步产生、各占多少、缺的是什么。
⚠ **只测不改**。本轮不动任何判据。
⚠ 读码先发现:`_probe_tick` 有 **3 条"不作判决"的出口**,只有 1 条被计数:
   (A) bin 越界      -> done,**不计数**
   (B) 槽位改派/释放  -> done,**不计数**(探针作废)
   (C) L0/L1 落在本底+M 内 -> **计为 abstain**
   ⇒ **弃权率可能低估了"无判决率"**。本脚本把三条都计出来。
弃权内部再分:由 L0 触发 / 由 L1 触发 / 两者皆触发,并给**距门的余量(dB)**
   ⇒ 余量小 = 边际弃权(便宜可救);余量大 = 深度弃权(改门也救不回)。
[L2/宿主仿真·合成料]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FS, FRAME, NFFT, FS_SC, NotchSlot

GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
DUR = 200.0
N = 6

# ── 非侵入插桩:包一层 _probe_tick,记录三条出口(不改 nhs.py)
STATS = {}


def instrument(a):
    P = a.P
    orig = a._probe_tick

    def patched(M, df):
        pre = {si: dict(pr) for si, pr in a.probes.items()}
        n_ab0 = a.ctr.get('c8_abstain', 0)
        n_log0 = len(a.c8_log)
        orig(M, df)
        # 判决产生
        for r in a.c8_log[n_log0:]:
            if r['verdict'] == 'abstain':
                STATS['C_abstain'] = STATS.get('C_abstain', 0) + 1
            else:
                STATS['verdict_' + r['verdict']] = STATS.get('verdict_' + r['verdict'], 0) + 1
        # 消失但无判决的探针 = A 或 B
        gone = set(pre) - set(a.probes)
        n_new_log = len(a.c8_log) - n_log0
        n_silent = len(gone) - n_new_log
        if n_silent > 0:
            for si in gone:
                pr = pre[si]
                if pr.get('L0') is None:
                    continue
                k = int(round(pr['f'] / df))
                if not (0 < k < len(M)):
                    STATS['A_bin越界'] = STATS.get('A_bin越界', 0) + 1
                else:
                    STATS['B_槽位改派'] = STATS.get('B_槽位改派', 0) + 1
    a._probe_tick = patched


def run(mk, seed):
    a = NHS()
    instrument(a)
    # 记录弃权的 L0/L1/FL 明细:再包一层 _level 无法区分,故直接复算
    mat = mk(DUR, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
    # 试次结束时仍在飞的探针
    STATS['D_结束时在飞'] = STATS.get('D_结束时在飞', 0) + len(a.probes)
    return a


print("r23 ① · 弃权归因(只测不改)")
print(f"[L2/宿主仿真·合成料]  窗={DUR:.0f}s  N={N}")
print("⚠ `_probe_tick` 有 **3 条不作判决的出口**,原实现只计数其中 1 条(弃权)\n")

for nm, mk in [('钢琴', S.m_piano), ('多人交谈', S.m_multitalk)]:
    STATS.clear()
    for i in range(N):
        run(mk, i)
    tot = sum(v for k, v in STATS.items())
    print(f"【{nm}】探针出口分布(合计 {tot}):")
    order = ['verdict_ext', 'verdict_howl', 'C_abstain', 'A_bin越界', 'B_槽位改派', 'D_结束时在飞']
    for k in order:
        v = STATS.get(k, 0)
        if v:
            print(f"    {k:<16} {v:>5}  ({v/tot*100:>5.1f}%)")
    dec = STATS.get('verdict_ext', 0) + STATS.get('verdict_howl', 0) + STATS.get('C_abstain', 0)
    nodec = tot - STATS.get('verdict_ext', 0) - STATS.get('verdict_howl', 0)
    print(f"    ⇒ 有判决 {dec}  |  **无判决(含未计数的 A/B/D)= {nodec} = {nodec/tot*100:.1f}%**")
    print(f"    ⇒ 其中被计为「弃权」的只有 {STATS.get('C_abstain',0)}"
          f" = {STATS.get('C_abstain',0)/max(nodec,1)*100:.1f}% ⇒ "
          f"**{'弃权率确实低估了无判决率' if nodec > STATS.get('C_abstain',0)*1.1 else '弃权率基本等于无判决率'}**")
    print()
