"""r19:λ 衰减是**系统的性质**还是**素材的性质**?
假设(lead):保鲜期在**频点集**上累积;钢琴频点集有限(离散音高+谐波)
⇒ λ 衰减主要是"素材把频点用光了",不是"系统自然趋于安静"。
可判:比较不同素材的 λ 衰减曲线 —— 钢琴(离散,应最快衰减)vs 多人交谈(宽带、频点持续变化,
应最慢)vs 空调(稳态窄带,应最快枯竭)。
⇒ 同时直接测**频点预算耗尽**本身:累计不同挂陷频点数是否饱和。
[L2/宿主仿真·合成料]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FS, FRAME, NotchSlot

GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
LENGTHS = [25.0, 50.0, 100.0, 200.0]
N = 6


def trial(mk, seed, dur):
    a = NHS()
    mat = mk(dur, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
    # 累计**不同**挂陷频点(按陷波带宽分箱 ⇒ 同一物理峰不重复计)
    fs = [e[2] for e in a.events if 'engage' in str(e[1])]
    binned = set()
    for f in fs:
        binned.add(round(f / max(f * 0.2, 15.0)))     # 按 bw_oct=1/5 的带宽分箱
    c = a.ctr
    return (c.get('c8_abstain', 0), len(fs), len(binned),
            sum(1 for s in a.slots if s.st != NotchSlot.FREE))


print("r19 · λ 衰减:系统性质 还是 素材性质?")
print(f"[L2/宿主仿真·合成料]  N={N}/点")
print("判据:若 λ 衰减主要由**频点枯竭**驱动,则「累计不同频点数」应随窗长**饱和**,")
print("      且**频点持续变化的素材(多人交谈)衰减应显著更慢**。\n")
print(f"{'素材':<10}{'窗长s':>7}{'弃权数':>8}{'λ/s':>10}{'挂陷次数':>9}"
      f"{'不同频点数':>11}{'新频点/挂陷':>12}{'窗末占用':>9}")

res = {}
for nm, mk in [('钢琴', S.m_piano), ('多人交谈', S.m_multitalk), ('空调', S.m_hvac)]:
    lams, uniq = [], []
    for dur in LENGTHS:
        ab = eng = uq = occ = 0
        for i in range(N):
            r = trial(mk, i, dur)
            ab += r[0]; eng += r[1]; uq += r[2]; occ += r[3]
        lam = ab / (N * dur)
        lams.append(lam); uniq.append(uq / N)
        ratio = (uq / eng) if eng else float('nan')
        print(f"{nm:<10}{dur:>7.0f}{ab:>8}{lam:>10.4f}{eng:>9}{uq/N:>11.1f}"
              f"{ratio:>12.3f}{occ/N:>9.2f}")
        sys.stdout.flush()
    res[nm] = (lams, uniq)
    print()

print("=" * 84)
print("【判读】")
for nm, (lams, uniq) in res.items():
    dec = lams[0] / lams[-1] if lams[-1] > 0 else float('inf')
    # 频点饱和度:200s 的不同频点数 相对 25s 的倍数;若 ≈1 则完全饱和
    grow = uniq[-1] / uniq[0] if uniq[0] > 0 else float('nan')
    # 窗长增长 8×(25→200);若频点数增长 <<8× 则枯竭
    print(f"  {nm:<10} λ 衰减 **{dec:.1f}×**(25s→200s)   "
          f"不同频点数增长 **{grow:.1f}×**(窗长增长 8.0×)")
    if np.isfinite(grow):
        print(f"{'':<12}⇒ 频点数增长 / 窗长增长 = **{grow/8.0:.2f}**  "
              f"{'⇒ 严重枯竭(远小于 1)' if grow/8.0 < 0.35 else ('⇒ 部分枯竭' if grow/8.0 < 0.7 else '⇒ 基本不枯竭')}")
print()
print("⇒ 若「钢琴/空调严重枯竭 且 多人交谈明显不枯竭」⇒ **lead 假设成立**:")
print("   λ 衰减主要是素材性质 ⇒ **长窗必须用多人交谈,否则测的是素材不是系统**。")
print("⇒ 若三者枯竭程度相近 ⇒ 衰减是系统性质(保鲜期机制本身)⇒ 素材选择不改变结论。")
