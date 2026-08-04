"""r88 · 非统计 plant 对照 —— 单格 worker(一格 = 一条种子 × 三个 plant)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r88.txt。

臂:P_stat(clrig 噪声 RIR)/ P_conf(模态 100 m³,主对比)/ P_booth(模态 14 m³,**阳性对照**)
每 plant:m0(无 proc)+ NHS 自选(duck 消融)⇒ ΔMSG = m_NHS − m0
⛔ 本文件不含结论性散文。用法:python3 r88_cell.py --t60 0.5 --sd 0 --tag t05s0
"""
import sys, json, time, argparse, hashlib
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
import modal_rig_BROKEN_seam16dB as modal_rig   # ⛔ 已知损坏,见 F81;此处仅为复现伪影证据
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME
from r81_windowcheck import envelope_stats

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SRC, T_OBS, BW_OCT, TLOW = -20.0, 12.0, 1 / 5, -45.0
F_CUT, STEP, FLOOR = 8000., 0.5, 0.354
L_CONF, L_BOOTH = (5.8, 4.6, 3.75), (2.6, 2.4, 2.25)
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def sha(f):
    return hashlib.sha256(open(DIR + f, 'rb').read()).hexdigest()[:16]


def mk_self():
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = TLOW
    a.duck_gain = lambda: 1.0
    return a


def scan(hb, D, mkf, lo, hi, src, ref):
    """r76 形态:返回 (m, f_trig, st, status)。m = 最后一个不起振的 G。"""
    G, last, st, ft = lo, None, None, float('nan')
    while G <= hi + 1e-9:
        a = mkf()
        pf = None
        if a is not None:
            def pf(blk, _a=a):
                return _a.process_frame(blk, GR)
        _, lp = clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            n = int(min(1.0, len(lp) / FS) * FS)
            Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
            ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
            return (float('nan') if last is None else last), ft, st, ('howl_at_lo' if last is None else 'ok')
        last = G
        grow, tpk = envelope_stats(lp, T_OBS)
        st = dict(grow=float(grow), tpeak_ratio=float(tpk),
                  upper_only=bool(grow > 0 or tpk >= 0.7))
        if a is not None:
            u = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
            fr = sorted(round(float(s.f), 1) for s in u)
            st.update(n_notch=len(u), fr=fr,
                      n_low=sum(1 for x in fr if x < 300.),
                      dmed=(float(np.median([s.depth for s in u])) if u else float('nan')),
                      n2=int(a.ctr.get('N2_lvl', 0)), n4=int(a.ctr.get('N4_born', 0)))
        G += STEP
    return float('nan'), ft, st, 'no_howl'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t60', type=float, required=True)
    ap.add_argument('--sd', type=int, required=True)
    ap.add_argument('--tag', type=str, required=True)
    A = ap.parse_args()
    t0 = time.time()
    T60, sd = A.t60, A.sd
    P = nhs.Params()
    assert P.recheck_free is False and P.prefer_unnotched is False
    assert P.growth_and_gate is False and P.bw_oct_match is None
    assert T_OBS < P.lift_after_s

    W(f"未经 critic 评审 —— r88 单格 tag={A.tag}  [L2/宿主仿真]  预注册 = PREREG_r88.txt")
    W(f"deps: nhs.py@{sha('nhs.py')} clrig.py@{sha('clrig.py')} modal_rig.py@{sha('modal_rig.py')}")
    W(f"工作点:T60={T60} seed={sd} / src={SRC:+.1f} dBFS(标称) / T_OBS={T_OBS:.0f}s / bw_oct=1/5 / "
      f"NN={P.NN} 槽全空 / T_low={TLOW:+.0f} / duck **消融** / 修法全关 / f_cut={F_CUT:.0f} / STEP={STEP}")
    W(f"plant:P_stat=clrig 噪声RIR / P_conf=模态 {L_CONF} (100 m³) / P_booth=模态 {L_BOOTH} (14 m³,**阳性对照**)")
    W(f"⚠ 模态 plant 的 seed 只换**源/收位置**(几何固定)⇒ 种子间变异性在构造上更小,⛔ 散布不得与统计臂直接比")
    W("")

    src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC / 20.))
    ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
    plants = [('P_stat', lambda: clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)),
              ('P_conf', lambda: modal_rig.make_F_modal(T60=T60, prop_delay_ms=8., seed=sd, L=L_CONF)),
              ('P_booth', lambda: modal_rig.make_F_modal(T60=T60, prop_delay_ms=8., seed=sd, L=L_BOOTH))]
    rows = []
    W(f"{'plant':>9}{'m0':>9}{'m_NHS':>9}{'ΔMSG':>8}{'挂陷':>6}{'<300Hz':>8}{'深度中位':>10}"
      f"{'末−首dB':>10}{'窗判定':>16}{'f_trig':>10}")
    for (nm, mkp) in plants:
        h0, D = mkp()
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        m0, ft0, st0, sta0 = scan(hb, D, lambda: None, anchor - 3, anchor + 4, src, ref)
        mN, ftN, stN, staN = scan(hb, D, mk_self, anchor - 1, anchor + 20, src, ref)
        d = (mN - m0) if (np.isfinite(mN) and np.isfinite(m0)) else float('nan')
        st = stN or {}
        vv = '**⛔ 只能作上界**' if st.get('upper_only') else '✅ 干净'
        W(f"{nm:>9}{m0:>9.2f}{mN:>9.2f}{d:>8.2f}{st.get('n_notch',-1):>6}{st.get('n_low',-1):>8}"
          f"{st.get('dmed',float('nan')):>10.2f}{st.get('grow',float('nan')):>+10.2f}{vv:>16}{ftN:>10.1f}")
        W(f"          频点 {st.get('fr', [])}")
        rows.append(dict(T60=T60, sd=sd, plant=nm, anchor=float(anchor), m0=m0, mN=mN, dmsg=d,
                         f_trig_m0=ft0, f_trig=ftN, st_m0=sta0, st_N=staN, **st))
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + f'r88_cell_{A.tag}_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + f'r88_cell_{A.tag}.json', 'w') as fp:
        json.dump(rows, fp, default=lambda o: None)


if __name__ == '__main__':
    main()
