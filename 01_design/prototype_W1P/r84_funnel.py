"""r84 · 漏斗量化。⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r84.txt。
⛔ 本轮只量不修;本文件不含结论性散文,也不含任何修法。"""
import sys, json, glob, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
T, SRC = 12.0, -20.
OUT = []
def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()

def run(hb, D, G, src, fix):
    a = NHS(); a.P.bw_oct = 1/5; a.P.T_low = -45.
    a.P.prefer_unnotched = bool(fix); a.duck_gain = lambda: 1.0
    _, lp = clrig.Loop(hb, D, G, proc=lambda b, _a=a: _a.process_frame(b, GR)).run(src, FRAME)
    used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
    c = dict(a.ctr)
    c['n_notch'] = len(used)
    c['exe_db'] = float(sum(abs(s.depth) for s in used))
    return c

def main():
    t0 = time.time()
    R76 = []
    for p in glob.glob(DIR + 'r76_cell_*.json'): R76 += json.load(open(p))
    K = {(r['src'], r['fix'], r['tlow'], r['T60'], r['sd'], r['T']): r for r in R76}
    W("未经 critic 评审 —— r84 · 漏斗量化  [L2/宿主仿真]  预注册 = PREREG_r84.txt")
    W("⛔ 本轮**只量不修**;遥测为纯计数,逐位等价已证(新旧 nhs.py 16/16 相同)")
    W(f"工作点:src={SRC:+.0f} dBFS / T_OBS={T:.0f}s / bw_oct=1/5 / T_low=−45 / duck消融 / "
      f"G = r76 已报的该格终点 G")
    W("")
    KEYS = ['N1_cand','N2_lvl','N3_gate','N4_born','F1_cls_out','F2_kept','F3_dropped',
            'F4_drop_notched','F5_kept_notched','A1_in','A2_deepen_branch','A3_deepen_real',
            'n_carried','preempt','n_blocked','slots_exhausted','c8_suppressed',
            'p0_blocked_novalid','depth_exhausted','n_notch']
    rows = []
    for fix in (0, 1):
        W("=" * 118)
        W(f"### 修法 {'开(prefer_unnotched=True,**非提交修法**)' if fix else '关(现状)'}")
        W("=" * 118)
        W(f"{'T60':>5}{'sd':>4}" + "".join(f"{k[:11]:>12}" for k in KEYS[:9]))
        W(f"{'':>9}" + "".join(f"{k[:11]:>12}" for k in KEYS[9:]))
        for (T60, sd) in [(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]:
            rec = K.get((SRC, 0, -45., T60, sd, T))
            if rec is None or not np.isfinite(rec['dA']): continue
            h0, Dp = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
            hb = band_limit(h0, 8000.)
            s = np.random.default_rng(sd).standard_normal(int(T*FS)) * (10**(SRC/20.))
            G = rec['m0'] + rec['dA']
            c = run(hb, Dp, G, s, fix)
            W(f"{T60:>5.1f}{sd:>4}" + "".join(f"{c.get(k,0):>12}" for k in KEYS[:9]))
            W(f"{'':>9}" + "".join((f"{c.get(k,0):>12.1f}" if k=='exe_db' else f"{c.get(k,0):>12}")
                                   for k in KEYS[9:]))
            c.update(T60=T60, sd=sd, fix=fix, G=float(G), cmd_db=float(c.get('A3_cmd_db',0.0)))
            rows.append({k: (float(v) if isinstance(v,(int,float)) else v) for k,v in c.items()
                         if not isinstance(v, (list, dict))})
        W("")
    W("=" * 118)
    W("§F 漏斗汇总(中位,分修法臂)")
    W("=" * 118)
    for fix in (0,1):
        v = [r for r in rows if r['fix']==fix]
        if not v: continue
        W(f"  修法{'开' if fix else '关'}:")
        f1 = np.median([r.get('F1_cls_out',0) for r in v]); f2 = np.median([r.get('F2_kept',0) for r in v])
        f3 = np.median([r.get('F3_dropped',0) for r in v]); f4 = np.median([r.get('F4_drop_notched',0) for r in v])
        W(f"    截断:F1_cls_out {f1:.0f} → F2_kept {f2:.0f}  ⇒ **F3_dropped {f3:.0f}**"
          f"  (占 {100*f3/max(f1,1):.1f}%);其中已挂陷复检 F4 = {f4:.0f}")
        for k in ('A1_in','A2_deepen_branch','A3_deepen_real','n_carried','preempt',
                  'n_blocked','p0_blocked_novalid','slots_exhausted','n_notch'):
            W(f"    {k:<20} 中位 {np.median([r.get(k,0) for r in v]):.1f}"
              f"  逐条 {[int(r.get(k,0)) for r in v]}")
        W(f"    ⭐ 命令量 A3_cmd_db 中位 {np.median([r.get('cmd_db',0) for r in v]):.1f} dB"
          f" ｜ 执行量 exe_db 中位 {np.median([r.get('exe_db',0) for r in v]):.1f} dB"
          f" ⇒ 执行/命令 ≈ {np.median([r.get('exe_db',0) for r in v])/max(np.median([r.get('cmd_db',0) for r in v]),1e-9):.3f}")
        W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读,也不含修法。")
    open(DIR+'r84_funnel_out.txt','w').write("\n".join(OUT)+"\n")
    json.dump(rows, open(DIR+'r84_funnel.json','w'))

if __name__ == '__main__':
    main()
