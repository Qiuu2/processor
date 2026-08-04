"""r93 · **换被测量:连续的检出时刻 t_det**。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r93.txt(§2 判据跑前写死;§1 已做【可表示性自查】)。
⭐ 本件是 `marks.py` 四记号 + 聚合护栏的**第一次实用**(critic r12 MAJOR-2 修法)。
⛔ 本文件不含结论性散文。"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME
import marks
from marks import UNCONVERGED, AggregateBlocked

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SRC, BW, DEPTH, F_CUT, STEP, T_WIN = -20.0, 1/5, -18.0, 8000., 0.5, 48.0
T60S, SDS = [0.20, 0.35, 0.50], [0, 1, 2]
OUT = []
def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()

def t_det(lp, ref):
    """首次越 ref+TH_ON 的时刻(s);从不越 ⇒ UNCONVERGED。分辨力 = 一帧 = 1.33 ms。"""
    n = (len(lp)//FRAME)*FRAME
    lv = np.array([HD.rms_db(lp[i:i+FRAME]) for i in range(0, n, FRAME)])
    idx = np.where(lv > ref + HD.TH_ON_DB)[0]
    if len(idx) == 0:
        return UNCONVERGED(f'{T_WIN:.0f}s 内从不触发')
    return float(idx[0]) * FRAME / FS

def main():
    t0 = time.time()
    W("未经 critic 评审 —— r93 · 连续被测量 `t_det`  [L2/宿主仿真]  预注册 = PREREG_r93.txt")
    W(f"被测量:首次越 ref+{HD.TH_ON_DB} dB 的时刻(s);分辨力 = 一帧 = {FRAME/FS*1000:.2f} ms ⇒ **实质连续**")
    W(f"工作点:G = 解析临界 + {STEP} dB(一格之上,⛔ 不在临界点上量)· 窗 {T_WIN:.0f}s · 臂 O(LTI)")
    W("⭐ 记号用 `marks.py` 四记号,⛔ 不出现 nan;聚合走护栏(遇非数值记号 ⇒ 中止并报 FAIL)")
    W("")
    W(f"{'T60':>6}{'sd':>4}{'解析临界':>10}{'G':>9}{'t_det (s)':>14}")
    rows = []
    for T60 in T60S:
        for sd in SDS:
            h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
            hb = band_limit(h0, F_CUT); he = clrig.h_eff(hb)
            picks = pick_excl(he, BW, 8)
            ana = MSGMeter(he, FS).msg(slots=mk_oracle(picks, BW, DEPTH).slots,
                                       g_duck_db=0.)['full']['msg_db']
            G = ana + STEP
            src = np.random.default_rng(sd).standard_normal(int(T_WIN*FS)) * (10**(SRC/20.))
            ref = HD.rms_db(src[:(len(src)//FRAME)*FRAME])
            a = mk_oracle(picks, BW, DEPTH)
            _, lp = clrig.Loop(hb, D, G, proc=lambda b, _a=a: _a.process_frame(b, GR)).run(src, FRAME)
            td = t_det(lp, ref)
            W(f"{T60:>6.2f}{sd:>4}{ana:>10.4f}{G:>9.4f}{repr(td) if isinstance(td, marks.Mark) else f'{td:>14.3f}'}")
            rows.append(dict(T60=T60, sd=sd, ana=float(ana), G=float(G),
                             t_det=(None if isinstance(td, marks.Mark) else td),
                             mark=(td.KIND if isinstance(td, marks.Mark) else None)))
    W("")
    W("="*86); W("§H 逐层统计(⭐ 聚合走护栏 —— 遇非数值记号当场中止并报 FAIL)"); W("="*86)
    med = {}
    for T60 in T60S:
        vals = [(UNCONVERGED(r['mark']) if r['mark'] else r['t_det'])
                for r in rows if r['T60'] == T60]
        try:
            m = marks.safe_median(vals); rng = marks.safe_max(vals) - min(v for v in vals)
            med[T60] = m
            W(f"  T60={T60:.2f}: 中位 **{m:.3f} s** ｜ 三格 {[round(v,3) for v in vals]} ｜ 极差 {rng:.3f} s")
        except AggregateBlocked as e:
            med[T60] = None
            W(f"  T60={T60:.2f}: {e}")
    W("")
    if all(med.get(t) is not None for t in T60S):
        a, b, c = (med[t] for t in T60S)
        mono = a < b < c
        va = [r['t_det'] for r in rows if r['T60'] == 0.20]
        vb = [r['t_det'] for r in rows if r['T60'] == 0.35]
        vc = [r['t_det'] for r in rows if r['T60'] == 0.50]
        sep = (max(va) < min(vb)) and (max(vb) < min(vc))
        W(f"  H1 单调 ∧ 区间不重叠 ⇒ {'✅ **成立**' if (mono and sep) else '⛔ 不成立'}"
          f"(单调={mono} / 不重叠={sep})")
        if mono and not sep:
            W("  ⇒ **H2**:顺序成立,而**本设计分辨不出 0.35 是否自成一层**(区间重叠)⛔ 不记为 H1")
        if not mono:
            W("  ⇒ ⛔ **H3 证伪:该推广作废**")
    else:
        W("  ⛔ 有层被护栏中止 ⇒ 该层无可报中位 ⇒ ⛔ 不得跨层比较")
    W("")
    W("⚠ 样本 = **9 格 × 1 plant 族 × 1 条轴 ⇒ 9/∞**,⛔ 不是全称")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    open(DIR+'r93_tdet_out.txt','w').write("\n".join(OUT)+"\n")
    json.dump(rows, open(DIR+'r93_tdet.json','w'))

if __name__ == '__main__':
    main()
