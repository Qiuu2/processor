"""r23b:弃权内部分解 —— 由 L0 触发 / 由 L1 触发 / 两者;并给**距门余量**。
弃权条件:L0 ≤ 本底+M 或 L1 ≤ 本底+M(M = probe_floor_M = 10.0dB)
⇒ **余量小 = 边际弃权(便宜可救);余量大 = 深度弃权(改门也救不回)**
⚠ 只测不改。[L2/宿主仿真·合成料]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FRAME

GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
DUR = 200.0
N = 6

print("r23b · 弃权内部分解 + 距门余量")
print("[L2/宿主仿真·合成料]  只测不改")
print("弃权条件:L0 ≤ 本底+M  或  L1 ≤ 本底+M   (M = 10.0dB)")
print("⇒ **余量小 = 边际弃权(便宜可救);余量大 = 深度弃权(改门也救不回)**\n")

for nm, mk in [('钢琴', S.m_piano), ('多人交谈', S.m_multitalk)]:
    recs = []
    for sd in range(N):
        a = NHS()
        orig = a._probe_tick

        def patched(M, df, a=a, orig=orig, recs=recs):
            snap = {si: dict(pr) for si, pr in a.probes.items()}
            n0 = len(a.c8_log)
            orig(M, df)
            for r in a.c8_log[n0:]:
                if r['verdict'] != 'abstain':
                    continue
                for si, pr in snap.items():
                    if abs(pr['f'] - r['f']) < 1e-6 and pr.get('L0') is not None:
                        k = int(round(pr['f'] / df))
                        if not (0 < k < len(M)):
                            continue
                        L1 = a._level(M, k)
                        gate = pr['FL'] + a.P.probe_floor_M
                        recs.append((pr['L0'] - gate, L1 - gate))
                        break
        a._probe_tick = patched
        mat = mk(DUR, 1000 + sd)
        n = (len(mat) // FRAME) * FRAME
        for i in range(0, n, FRAME):
            a.process_frame(mat[i:i + FRAME], GR)
        sys.stdout.flush()
    if not recs:
        print(f"【{nm}】弃权样本 0 ⇒ 未触达,无结论\n")
        continue
    A = np.array(recs); d0, d1 = A[:, 0], A[:, 1]
    only0 = int(((d0 <= 0) & (d1 > 0)).sum())
    only1 = int(((d0 > 0) & (d1 <= 0)).sum())
    both = int(((d0 <= 0) & (d1 <= 0)).sum())
    tot = len(A)
    print(f"【{nm}】弃权样本 n={tot}")
    print(f"    仅 L0 触发(探针启动时就在本底附近)= {only0:>4} ({only0/tot*100:>5.1f}%)")
    print(f"    仅 L1 触发(判决时跌到本底附近)    = {only1:>4} ({only1/tot*100:>5.1f}%)")
    print(f"    两者皆触发                        = {both:>4} ({both/tot*100:>5.1f}%)")
    for lbl, d in [('L0 距门', d0), ('L1 距门', d1)]:
        neg = d[d <= 0]
        if len(neg):
            print(f"    {lbl}(触发的 {len(neg)} 例):中位 {np.median(neg):+.1f}dB  "
                  f"p10 {np.percentile(neg,10):+.1f}dB  | **距门<3dB 的边际例 = "
                  f"{int((neg>-3).sum())}/{len(neg)} = {(neg>-3).mean()*100:.1f}%**")
    print()
