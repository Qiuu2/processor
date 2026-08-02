"""r17b:多试次长度拟合 λ、W —— 按架构侧新判据「单点比对不构成验证」。
排队瞬态解:L(t) = λ·W·(1 − exp(−t/W))
⇒ 取多个 (t, L) 拟合 λ、W,再与**独立测得**的 λ(弃权到达率)、W(理论驻留)比对。
含「可抢占」(r17b)。[L2/宿主仿真·合成料]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FS, FRAME, NotchSlot

GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
HELD = (NotchSlot.ENGAGE, NotchSlot.HOLD, NotchSlot.LIFT)   # 音质害口径:深度非零
OCC = (NotchSlot.ENGAGE, NotchSlot.HOLD, NotchSlot.LIFT, NotchSlot.STANDBY)  # 资源害口径:槽位不可用

LENGTHS = [25.0, 50.0, 100.0, 200.0]
N = 8


def run(mk, seed, dur):
    a = NHS()
    mat = mk(dur, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
    c = a.ctr
    return (sum(1 for s in a.slots if s.st in HELD),
            sum(1 for s in a.slots if s.st in OCC),
            c.get('c8_abstain', 0), c.get('exhausted', 0), c.get('preempt', 0))


print("r17b · 多试次长度拟合(含可抢占)—— 单点比对不构成验证")
print(f"[L2/宿主仿真·合成料]  长度={LENGTHS}  N={N}/点")
print("⚠ **两个害分开报**:音质害 = HELD(深度非零,听得见);资源害 = OCC(槽位不可用)")
print("⚠ 功效:N=8/点 ⇒ 每点均值 SE 较大;拟合结果**给区间不给点值**\n")

for nm, mk in [('钢琴', S.m_piano)]:
    ts, Lh, Lo, lam_meas = [], [], [], []
    print(f"{'长度s':>7}{'音质害 HELD':>13}{'资源害 OCC':>12}{'弃权数':>8}"
          f"{'λ实测/s':>10}{'EXHAUST':>9}{'抢占':>7}")
    for dur in LENGTHS:
        h = o = ab = ex = pe = 0
        for i in range(N):
            r = run(mk, i, dur)
            h += r[0]; o += r[1]; ab += r[2]; ex += r[3]; pe += r[4]
        lam = ab / (N * dur)
        ts.append(dur); Lh.append(h / N); Lo.append(o / N); lam_meas.append(lam)
        print(f"{dur:>7.0f}{h/N:>13.2f}{o/N:>12.2f}{ab:>8}{lam:>10.4f}{ex:>9}{pe:>7}")
        sys.stdout.flush()

    print()
    for label, L in [('音质害 HELD', Lh), ('资源害 OCC', Lo)]:
        t = np.array(ts, float); y = np.array(L, float)
        best = None
        for W in np.arange(5.0, 300.0, 1.0):          # 网格搜 W,λ 由最小二乘闭式给
            b = 1.0 - np.exp(-t / W)
            if (b * b).sum() <= 0:
                continue
            lamW = (y * b).sum() / (b * b).sum()      # = λ·W
            r = y - lamW * b
            ss = float((r * r).sum())
            if best is None or ss < best[0]:
                best = (ss, W, lamW)
        ss, W, lamW = best
        lam_fit = lamW / W
        ybar = y.mean(); sstot = float(((y - ybar) ** 2).sum())
        r2 = 1 - ss / sstot if sstot > 0 else float('nan')
        lam_ind = float(np.mean(lam_meas))
        print(f"  【{label}】拟合 L(t)=λW(1−e^(−t/W)):")
        print(f"     W_fit = {W:.0f}s   λ_fit = {lam_fit:.4f}/s   L_ss = λW = {lamW:.2f}   R²={r2:.4f}")
        print(f"     独立测得 λ = {lam_ind:.4f}/s  ⇒ 比值 λ_fit/λ_indep = {lam_fit/lam_ind:.2f}"
              f"  {'✔ 同量级' if 0.5 <= lam_fit/lam_ind <= 2.0 else '⛔ 不符,提示第二条来源'}")
    print()
    print("  ⇒ 需要几个槽才不饱和(给 D13 的输入):")
    for label, L in [('音质害 HELD', Lh), ('资源害 OCC', Lo)]:
        t = np.array(ts, float); y = np.array(L, float)
        print(f"     {label}: 最长窗实测 {y[-1]:.2f} 槽 ⇒ 若要留 ≥2 槽给真啸叫,"
              f"需 **{int(np.ceil(y[-1])) + 2}** 槽(现 8)")
