"""r20 ①:8 槽 + 长窗(600s)钢琴 —— 占用曲线在哪里停。
不需要模型、不需要对照臂、不需要外推:直接看峰值、到峰时间、峰后是否回落、是否触及 8。
判据(lead):**到峰时间 < 窗长 × 0.7** 才算"这个峰是真峰";否则仍是上升沿取数。
⚠ 8 点/通道 = DEC-0007 第 3 项、CTO 对外规格 —— 本轮就是产品配置,无需外推。
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


def trial(seed):
    a = NHS()
    mat = S.m_piano(DUR, 1000 + seed)
    n = (len(mat) // FRAME) * FRAME
    ts, occ, held = [], [], []
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
        if i % (FRAME * 12) == 0:
            ts.append(a.t_wall)
            occ.append(sum(1 for s in a.slots if s.st in OCC))
            held.append(sum(1 for s in a.slots if s.st in HELD))
    return np.array(ts), np.array(occ), np.array(held), a.ctr


print(f"r20 ① · 8 槽 · 窗 {DUR:.0f}s · 钢琴 · N={N}")
print("[L2/宿主仿真·合成料]  产品配置直接测,**无需外推**")
print(f"判据:到峰时间 < 窗长×0.7 = {DUR*0.7:.0f}s 才算真峰;否则仍是上升沿取数\n")

allocc, allheld, tss = [], [], None
ctrs = []
for i in range(N):
    ts, o, h, c = trial(i)
    if tss is None:
        tss = ts
    L = min(len(tss), len(o))
    allocc.append(o[:L]); allheld.append(h[:L]); tss = tss[:L]
    ctrs.append(c)
    print(f"  试次{i}: 峰值OCC={o.max()}  到峰={ts[int(np.argmax(o))]:.0f}s  "
          f"峰值HELD={h.max()}  末值OCC={o[-1]}  触及8={'**是**' if o.max() >= 8 else '否'}")
    sys.stdout.flush()

O = np.vstack(allocc); H = np.vstack(allheld)
mo = O.mean(axis=0); mh = H.mean(axis=0)
ipk = int(np.argmax(mo)); tpk = float(tss[ipk])
print(f"\n  ── 均值曲线(N={N})──")
print(f"  峰值 OCC = **{mo.max():.2f}**  到峰时间 = **{tpk:.0f}s**  "
      f"(窗长×0.7 = {DUR*0.7:.0f}s) ⇒ {'**真峰 ✓**' if tpk < DUR*0.7 else '**仍在上升沿,需更长窗**'}")
print(f"  峰值 HELD = {mh.max():.2f}   末值 OCC = {mo[-1]:.2f}  "
      f"⇒ 峰后{'回落' if mo[-1] < mo.max()-0.3 else '未明显回落'}")
print(f"  **单试次最大 OCC = {O.max():.0f} / 8**  "
      f"⇒ {'**触及上限,须报 D13**' if O.max() >= 8 else '未触及 8'}")
print(f"\n  曲线采样(均值 OCC):")
step = max(1, len(tss)//12)
for j in range(0, len(tss), step):
    print(f"    t={tss[j]:>6.0f}s  OCC={mo[j]:>5.2f}  HELD={mh[j]:>5.2f}")
tot = {}
for c in ctrs:
    for k, v in c.items():
        if k.startswith(('c8_', 'exhaust', 'preempt')):
            tot[k] = tot.get(k, 0) + v
print(f"\n  计数合计:{dict(sorted(tot.items()))}")
