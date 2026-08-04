"""r87 闸门 · **中止条件**(D6-ap)。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r87b.txt §3。

自查句:「这个检查失败时,会阻止什么?」⇒ **阻止主扫描启动**(`sys.exit(1)`,
`r87_launch.sh` 见非零退出码即不起任何 cell)。

G1 配置断言(零成本)      —— 任一不成立即 exit(1)
G2 修法可达性(阳性对照)  —— 6 条种子里 0 条出现差异 ⇒ exit(1)
   ⚠ 门设得极松(≥1 条即过):护栏也会朝【丢掉对的数据】的方向失效(A-1)。

⛔ 本文件不含结论性散文。
"""
import sys, json, glob, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
SRC, T_OBS, BW_OCT, TLOW, STEP = -20.0, 12.0, 1 / 5, -45.0, 0.5
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def flush(code):
    with open(DIR + 'r87_gate_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    sys.exit(code)


def mk(rf):
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = TLOW
    a.P.prefer_unnotched = False
    a.P.recheck_free = bool(rf)
    a.duck_gain = lambda: 1.0
    return a


def probe(hb, D, G, src, rf):
    a = mk(rf)
    clrig.Loop(hb, D, G, proc=lambda b, _a=a: _a.process_frame(b, GR)).run(src, FRAME)
    u = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
    c = a.ctr
    return dict(depths=sorted(round(float(s.depth), 2) for s in u), n=len(u),
                F2=int(c.get('F2_kept', 0)), F3=int(c.get('F3_dropped', 0)),
                F4=int(c.get('F4_drop_notched', 0)), A3=int(c.get('A3_deepen_real', 0)))


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r87 闸门(中止条件)  [L2/宿主仿真]  预注册 = PREREG_r87b.txt §3")
    W("失败后果 = **主扫描不启动**(exit(1));⛔ 本件不是输出行。")
    W("")

    # ── G1 配置断言 ───────────────────────────────────────────────
    W("=" * 100)
    W("G1 · 配置断言")
    W("=" * 100)
    P = nhs.Params()
    checks = [
        ("P.recheck_free 存在且默认 False", hasattr(P, 'recheck_free') and P.recheck_free is False),
        ("P.prefer_unnotched 默认 False", P.prefer_unnotched is False),
        ("P.growth_and_gate 默认 False", P.growth_and_gate is False),
        ("P.bw_oct_match 默认 None", P.bw_oct_match is None),
        ("P.inherit_credit 默认 False", P.inherit_credit is False),
        ("NN == 8", P.NN == 8),
        ("n_cand == 16", P.n_cand == 16),
        ("max_depth == -18.0", abs(P.max_depth + 18.0) < 1e-9),
        ("默认 bw_oct == 1/5", abs(P.bw_oct - 1 / 5) < 1e-12),
        ("本轮 bw_oct == 1/5", abs(BW_OCT - 1 / 5) < 1e-12),
        ("本轮 T_low == -45", abs(TLOW + 45.0) < 1e-9),
        ("T_OBS(12) < lift_after_s(%.0f)" % P.lift_after_s, T_OBS < P.lift_after_s),
        ("STEP == 0.5", abs(STEP - 0.5) < 1e-12),
        ("src_rms == -20.0 dBFS(标称)", abs(SRC + 20.0) < 1e-9),
        ("NHS().cal == 0.0(nhs.py:259,cal_offset_db 默认)", abs(NHS().cal) < 1e-9),
    ]
    bad = 0
    for name, ok in checks:
        W(f"   {'PASS' if ok else '**FAIL**':>10}  {name}")
        bad += (0 if ok else 1)
    W(f"   ⇒ G1 {'通过' if bad == 0 else '**未过** ⇒ 主扫描不启动'}({len(checks)-bad}/{len(checks)})")
    W("")
    if bad:
        W("⛔ G1 未过 ⇒ exit(1)。主扫描**没有启动**。")
        flush(1)

    # ── G2 修法可达性(阳性对照) ─────────────────────────────────
    W("=" * 100)
    W("G2 · 修法可达性(阳性对照;在 r76 已落盘的基线终点 G 上,rf=0 vs rf=1)")
    W("=" * 100)
    R = []
    for p in glob.glob(DIR + 'r76_cell_*.json'):
        R += json.load(open(p))
    K = {(r['src'], r['fix'], r['tlow'], r['T60'], r['sd'], r['T']): r for r in R}
    W(f"{'T60/sd':>8}{'探针G':>9}{'挂陷 0→1':>11}{'深度中位 0→1':>16}"
      f"{'F3_dropped 0→1':>17}{'F4_drop_notched 0→1':>22}{'A3 0→1':>13}{'差异':>8}")
    n_diff = 0
    rows = []
    for (T60, sd) in SEEDS:
        rec = K.get((SRC, 0, TLOW, T60, sd, T_OBS))
        if rec is None or not np.isfinite(rec.get('dA', float('nan'))):
            W(f"{T60}/{sd:<6}   ⛔ r76 无该格 ⇒ 本条跳过(不计入差异计数)")
            continue
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        s = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC / 20.))
        G = rec['m0'] + rec['dA']
        a0 = probe(hb, D, G, s, 0)
        a1 = probe(hb, D, G, s, 1)
        d = (a0['depths'] != a1['depths']) or (a0['n'] != a1['n']) or \
            (a0['F2'] != a1['F2']) or (a0['F3'] != a1['F3']) or \
            (a0['F4'] != a1['F4']) or (a0['A3'] != a1['A3'])
        n_diff += int(d)
        m0d = float(np.median(a0['depths'])) if a0['depths'] else float('nan')
        m1d = float(np.median(a1['depths'])) if a1['depths'] else float('nan')
        c_n = "%d→%d" % (a0['n'], a1['n'])
        c_med = "%.2f→%.2f" % (m0d, m1d)
        c_f3 = "%d→%d" % (a0['F3'], a1['F3'])
        c_f4 = "%d→%d" % (a0['F4'], a1['F4'])
        c_a3 = "%d→%d" % (a0['A3'], a1['A3'])
        W(f"{T60}/{sd:<6}{G:>9.2f}{c_n:>11}{c_med:>16}{c_f3:>17}{c_f4:>22}"
          f"{c_a3:>13}{('**有**' if d else '无'):>8}")
        rows.append(dict(T60=T60, sd=sd, G=float(G), rf0=a0, rf1=a1, diff=bool(d)))
    W("")
    W(f"   ⇒ 出现差异的种子数 = **{n_diff}/{len(rows)}**(门 = ≥1)")
    with open(DIR + 'r87_gate.json', 'w') as fp:
        json.dump(rows, fp)
    if n_diff == 0:
        W("⛔ G2 未过(开关在本工作点不可达)⇒ exit(1)。主扫描**没有启动**。")
        W("   ⇒ 读法:此时 δ≈0 会被误读为「修法无效」,而真相是「没打到」——两者在数据上同形(r66a)。")
        flush(1)
    W(f"   ⇒ G2 通过。总耗时 {time.time()-t0:.0f} s。⇒ 允许主扫描启动。")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    flush(0)


if __name__ == '__main__':
    main()
