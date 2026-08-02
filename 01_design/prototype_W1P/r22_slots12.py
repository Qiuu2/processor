"""r22:「峰值恰好 6」是结构性上限,还是 8 槽在约束?
判形式(lead):同素材同窗长,把槽数调到 12 再跑。
  · 峰值**仍恰好 6** ⇒ **结构性上限**(候选表长度/保鲜期/占用时长决定)
    ⇒ 8 槽从来不是约束 ⇒ 加槽对该素材无价值,D13 那笔账当场结掉;
  · 峰值升到 **7–9**  ⇒ 8 槽此前确实在约束,阻塞以我们没数到的形式发生
    ⇒ 此时 `B_obs` 应同时非零(**两个量互为交叉验证**)。
⚠ 加槽数与降槽数一样**只是器械**;**8 点/通道 = DEC-0007 第 3 项、CTO 对外规格**不受影响,
  结论回到 8 槽须显式说明。
⚠ B_obs = n_blocked / (n_carried + n_blocked),单位已按 D-K 先定:**每个候选计一次**。
[L2/宿主仿真·合成料]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FS, FRAME, NotchSlot

GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
HELD = (NotchSlot.ENGAGE, NotchSlot.HOLD, NotchSlot.LIFT)
OCC = HELD + (NotchSlot.STANDBY,)
DUR = 600.0
N = 5


def origin_of(a, s):
    """占用来源三分:(b1) 弃权产生 / (b2) 探针判啸叫产生 / (u) 探针在飞未判。
    ⚠ **本开环台架无真啸叫** ⇒ 集合1(a) 恒为 0 **by construction**。
      故此处报的是 (b) 的内部构成,而"(a)=0"本身就是结论的一部分,不是缺失。"""
    if s.from_abstain:
        return 'b1_弃权'
    for r in reversed(a.c8_log):
        if abs(r['f'] - s.f) < max(s.f * 0.2, 15.0) / 2:
            return 'b2_判啸叫' if r['verdict'] == 'howl' else 'b3_判外部残留'
    return 'u_在飞'


def trial(seed, nn):
    a = NHS()
    a.P.NN = nn
    a.slots = [NotchSlot() for _ in range(nn)]
    mat = S.m_piano(DUR, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    peak = 0; peak_mix = {}; plat = []
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
        if i % (FRAME * 12) == 0:
            occ = [s for s in a.slots if s.st in OCC]
            if len(occ) > peak:
                peak = len(occ)
                peak_mix = {}
                for s in occ:
                    k = origin_of(a, s)
                    peak_mix[k] = peak_mix.get(k, 0) + 1
            if a.t_wall >= 150.0:                 # 平台段(r20 实测 t≈150s 进平台)
                m = {}
                for s in occ:
                    k = origin_of(a, s)
                    m[k] = m.get(k, 0) + 1
                plat.append(m)
    c = a.ctr
    nb = c.get('n_blocked', 0); nc = c.get('n_carried', 0)
    return peak, nb, nc, c.get('slots_exhausted', 0), c.get('depth_exhausted', 0), peak_mix, plat


print(f"r22 · 「峰值恰好 6」是结构性上限还是 8 槽在约束?  窗={DUR:.0f}s N={N} 钢琴")
print("[L2/宿主仿真·合成料]  ⚠ 加/降槽数**均为器械**;DEC-0007 的 8 点/通道不受影响")
print("⚠ B_obs = n_blocked/(n_carried+n_blocked),单位 = **每个候选计一次**(D-K 先定)\n")
print(f"{'槽数':>5}{'峰值OCC(逐试次)':>26}{'峰值均值':>10}{'n_blocked':>11}"
      f"{'n_carried':>11}{'B_obs':>9}{'SLOTS_EXH':>11}{'DEPTH_EXH':>11}")

store = {}
for nn in [8, 12]:
    pk, NB, NC, SE, DE = [], 0, 0, 0, 0
    PM, PL, PLn = {}, {}, 0
    for i in range(N):
        p, nb, nc, se, de, pm, pl = trial(i, nn)
        for k, v in pm.items(): PM[k] = PM.get(k, 0) + v
        for m in pl:
            for k, v in m.items(): PL[k] = PL.get(k, 0) + v
        PLn += len(pl)
        pk.append(p); NB += nb; NC += nc; SE += se; DE += de
    bobs = NB / (NB + NC) if (NB + NC) else float('nan')
    store[nn] = (pk, bobs, NB, PM, PL, PLn)
    print(f"{nn:>5}{str(pk):>26}{np.mean(pk):>10.2f}{NB:>11}{NC:>11}"
          f"{bobs:>9.4f}{SE:>11}{DE:>11}")
    sys.stdout.flush()

print("\n" + "=" * 90)
print("【⭐ 峰值占用的 (a)/(b) 分解】—— 槽位是为集合1(真啸叫)设的,我们测的却是集合2")
print("⚠ **本开环台架无真啸叫 ⇒ (a) 恒为 0 by construction**;")
print("   ⇒ 下表是 (b) 的**内部构成**,而「(a)=0」本身就是结论的一部分。")
for nn in [8, 12]:
    _, _, _, PM, PL, PLn = store[nn]
    tot = sum(PM.values())
    print(f"  槽数={nn} 峰值时刻合计 {tot} 个占用:")
    for k in sorted(PM):
        print(f"      {k:<14} {PM[k]:>4}  ({PM[k]/tot*100:>5.1f}%)" if tot else "")
    tp = sum(PL.values())
    if tp:
        print(f"    平台段(t≥150s)均值构成,共 {PLn} 个采样点:")
        for k in sorted(PL):
            print(f"      {k:<14} {PL[k]/PLn:>5.2f} 槽  ({PL[k]/tp*100:>5.1f}%)")
    b = sum(v for k, v in PM.items() if k.startswith("b"))
    print(f"    ⇒ (b) 占比 = **{b/tot*100:.1f}%**  "
          + ("⇒ **不该读作『容量紧张』,应读作『误报占了这些槽』**" if b/max(tot,1) >= 0.5 else ""))

pk8, b8, nb8 = store[8]
pk12, b12, nb12 = store[12]
m8, m12 = np.mean(pk8), np.mean(pk12)
print(f"【判读】8 槽峰值均值 {m8:.2f} ｜ 12 槽峰值均值 {m12:.2f}  ⇒ 差 {m12-m8:+.2f}")
if m12 <= m8 + 0.5:
    print("  ⇒ **峰值未随槽数上升 ⇒ 结构性上限**(不是 8 槽在约束)")
    print("  ⇒ **加槽对该素材无价值** —— D13 那笔账在该素材上可结。")
else:
    print("  ⇒ **峰值随槽数上升 ⇒ 8 槽此前确实在约束**")
print(f"  交叉验证:8 槽 B_obs = **{b8:.4f}**(n_blocked={nb8})")
if nb8 == 0 and m12 <= m8 + 0.5:
    print("  ⇒ **两个量一致**:从未拒绝过候选 ∧ 加槽无增益 ⇒ 「余量 2 槽」得第二条独立证据 ✓")
elif nb8 > 0 and m12 <= m8 + 0.5:
    print("  ⇒ **⛔ 两个量打架**:有阻塞但加槽无增益 ⇒ 须查(阻塞可能来自别的原因,非槽位不足)")
elif nb8 == 0 and m12 > m8 + 0.5:
    print("  ⇒ **⛔ 两个量打架**:无阻塞但加槽有增益 ⇒ 须查(n_blocked 可能漏计了某条路径)")
else:
    print("  ⇒ 两个量一致:有阻塞且加槽有增益 ⇒ 8 槽确在约束")
print("\n⚠ 限定:单一素材(钢琴)、合成料、开环、N=5。不外推到其它工况。")
