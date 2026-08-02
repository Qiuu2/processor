"""r18:**直接测量占用时长分布** —— 替代 λW 模型反推。
排队模型是"没法直接测 W"时的替代品;这里两个因子(到达数、实际驻留)都能直接测。
⚠ 到达率已实证非平稳(λ 25s→200s 降 3.9×)⇒ **驻留时长很可能也非平稳** ⇒ 报分布不只报均值。
⚠ **截尾显式标出**:试次结束仍挂着的占用,真实时长 **≥ 观测值**,混进均值 = 系统性低估。
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


def trial(mk, seed, dur, nn=None):
    a = NHS()
    if nn is not None:
        a.P.NN = nn
        a.slots = [NotchSlot() for _ in range(nn)]
    mat = mk(dur, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    # 每槽当前占用:(起始 t_wall, 是否弃权来源, 是否经历过 LIFT, 频率)
    cur = [None] * len(a.slots)
    recs = []               # (时长, 释放原因, 是否弃权来源)
    prev_f = [s.f for s in a.slots]
    prev_st = [s.st for s in a.slots]
    seen_ev = 0
    preempt_slots = set()
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
        while seen_ev < len(a.events):
            e = a.events[seen_ev]; seen_ev += 1
            if e[1] == 'preempt':
                preempt_slots.add(round(e[2], 0))
        for si, s in enumerate(a.slots):
            occupied = s.st in OCC
            reassigned = occupied and cur[si] is not None and abs(s.f - cur[si][3]) > 1.0
            if cur[si] is not None and (not occupied or reassigned):
                dur_s = a.t_wall - cur[si][0]
                if reassigned:
                    why = 'preempt' if round(s.f, 0) in preempt_slots else 'reassign'
                elif cur[si][2]:
                    why = 'lift'
                else:
                    why = 'other'
                recs.append((dur_s, why, cur[si][1]))
                cur[si] = None
            if occupied and cur[si] is None:
                cur[si] = [a.t_wall, s.from_abstain, False, s.f]
            if cur[si] is not None:
                if s.from_abstain:
                    cur[si][1] = True
                if s.st == NotchSlot.LIFT:
                    cur[si][2] = True
            prev_f[si] = s.f; prev_st[si] = s.st
    # 截尾:试次结束仍挂着
    n_cens = 0
    for si in range(len(a.slots)):
        if cur[si] is not None:
            recs.append((a.t_wall - cur[si][0], 'CENSORED', cur[si][1]))
            n_cens += 1
    c = a.ctr
    return recs, n_cens, c.get('exhausted', 0), c.get('exhausted_rechecks', 0), c.get('c8_abstain', 0)


def report(nm, recs, label):
    ab = [r for r in recs if r[2]]
    if not ab:
        print(f"    {label}: 弃权占用 0 段 —— **未触达,无结论**")
        return
    d = np.array([r[0] for r in ab])
    cens = [r for r in ab if r[1] == 'CENSORED']
    unc = [r for r in ab if r[1] != 'CENSORED']
    print(f"    {label}: 弃权占用 **{len(ab)}** 段  (**截尾 {len(cens)} 段 = {len(cens)/len(ab)*100:.0f}%**)")
    if unc:
        du = np.array([r[0] for r in unc])
        print(f"       未截尾 n={len(unc)}  时长 p10={np.percentile(du,10):.1f}s "
              f"p50={np.percentile(du,50):.1f}s p90={np.percentile(du,90):.1f}s max={du.max():.1f}s")
        from collections import Counter
        cnt = Counter(r[1] for r in unc)
        tot = sum(cnt.values())
        print(f"       释放原因: " + "  ".join(f"{k}={v}({v/tot*100:.0f}%)" for k, v in cnt.most_common()))
    if cens:
        dc = np.array([r[0] for r in cens])
        print(f"       ⚠ 截尾段观测时长 p50={np.percentile(dc,50):.1f}s "
              f"max={dc.max():.1f}s —— **真实时长 ≥ 此值**,不得并入均值")


print("r18 · 占用时长分布(直接测量,替代 λW 反推)")
print("[L2/宿主仿真·合成料]  ⚠ 截尾显式标出;报分布不只报均值\n")

print("【A】钢琴,产品配置 8 槽,多窗长(看驻留是否也非平稳)")
for dur in [50.0, 100.0, 200.0]:
    allr = []; cens = 0; ex = 0; exr = 0; ab = 0
    for i in range(8):
        r, c, e, er, a_ = trial(S.m_piano, i, dur)
        allr += r; cens += c; ex += e; exr += er; ab += a_
    print(f"  窗长 {dur:.0f}s  (N=8):  弃权判决={ab}  EXHAUSTED(新口径)={ex}  复检次数={exr}")
    report('钢琴', allr, f"窗{dur:.0f}s")
    sys.stdout.flush()

print("\n【B】EXHAUSTED 新口径 · **对照臂(弃权关,无弃权参与)** —— lead 指定单报")
for dur in [100.0]:
    ex = exr = 0
    for i in range(8):
        a = NHS(); a.P.probe_floor_M = -999.0
        mat = S.m_piano(dur, 1000 + i)
        n = (len(mat) // FRAME) * FRAME
        for j in range(0, n, FRAME):
            a.process_frame(mat[j:j + FRAME], GR_OFF)
        ex += a.ctr.get('exhausted', 0); exr += a.ctr.get('exhausted_rechecks', 0)
    print(f"  对照臂 窗{dur:.0f}s N=8:  **EXHAUSTED(新口径)= {ex}**  (= {ex/8:.1f}/试次)"
          f"   复检次数={exr}")
    print(f"  ⇒ 该数决定「陷波深度阶梯(−3/步、max −18)够不够」是不是真问题:"
          f"**{'非零 ⇒ 应立项' if ex > 0 else '为零 ⇒ 非问题'}**")
    sys.stdout.flush()

print("\n【C】饱和场景备料 · **降槽数(仅测试器械)**")
print("  ⚠ **8 点/通道是 DEC-0007 第 3 项、CTO 拍的强约束(对外规格)。**")
print("     降槽数**只能作测试器械**;任何结论回到 8 槽产品配置时**必须显式说明如何外推**,")
print("     **不得**把 2–3 槽下测得的数当产品数用。")
for nn in [2, 3, 8]:
    allr = []; pre = 0
    for i in range(8):
        a = NHS(); a.P.NN = nn
        a.slots = [NotchSlot() for _ in range(nn)]
        mat = S.m_piano(100.0, 1000 + i)
        n = (len(mat) // FRAME) * FRAME
        for j in range(0, n, FRAME):
            a.process_frame(mat[j:j + FRAME], GR_OFF)
        pre += a.ctr.get('preempt', 0)
    print(f"  槽数={nn}:  抢占触发 **{pre}** 次  "
          f"{'⇒ **触达 ✓,可抢占可测**' if pre > 0 else '⇒ **仍未触达,D-J 判无效**'}")
    sys.stdout.flush()
