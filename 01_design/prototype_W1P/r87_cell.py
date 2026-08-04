"""r87 · `recheck_free` 的 **ΔMSG 验证扫描** —— 单格 worker(一格 = 一条种子)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r87b.txt(跑前落盘)。

臂(5 条):m0(无 proc) / A_base(rf=0,duck 消融) / A_rf(rf=1,duck 消融)
          / D_base(rf=0,duck 不消融) / D_rf(rf=1,duck 不消融)
⚠ 主列 = duck 消融;附列(D_*)⛔ 不得单独引用,须与 g_duck最深 同出(F33)。

⚠ 复用声明(PREREG_r87b §1 三核已做):
  `scan()` 取 **r76_cell 形态**(返回 (m, f_trig, st, status));
  `envelope_stats()` 取 r81 形态;`make_F` 用新名 `prop_delay_ms`;
  `−18.00` 在本件一律是**输出读数**,本件不设 depth 输入参数(不建神谕臂)。

⛔ 本文件不含任何结论性散文。用法:python3 r87_cell.py --t60 0.2 --sd 0 --tag t02s0
"""
import sys, json, glob, time, argparse, hashlib
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME
from r81_windowcheck import envelope_stats

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SRC, T_OBS = -20.0, 12.0
BW_OCT, TLOW, DEPTH_FLOOR = 1 / 5, -45.0, None   # ⛔ 本轮无 depth 输入参数
F_CUT, STEP, FLOOR = 8000., 0.5, 0.354
ARMS = [('m0', None, None), ('A_base', 0, True), ('A_rf', 1, True),
        ('D_base', 0, False), ('D_rf', 1, False)]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def sha(f):
    return hashlib.sha256(open(DIR + f, 'rb').read()).hexdigest()[:16]


def mk_self(rf, ablate):
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = TLOW                  # T_low_gr 在 __init__ 已算死 −65,不重算(已知性质)
    a.P.prefer_unnotched = False      # F60 已判不提交
    a.P.recheck_free = bool(rf)
    if ablate:
        a.duck_gain = lambda: 1.0
    return a


def scan(hb, D, mkf, lo, hi, src, ref):
    """r76_cell 形态:返回 (m, f_trig, st, status)。m = **最后一个不起振的 G**。
    st 取自该 G 的那一次跑(含终点包络 —— 必报四项之④)。"""
    G, last, st, ft = lo, None, None, float('nan')
    while G <= hi + 1e-9:
        a = mkf()
        rec = []
        pf = None
        if a is not None:
            def pf(blk, _a=a, _r=rec):
                y = _a.process_frame(blk, GR)
                _r.append(_a.g_duck_db)
                return y
        _, lp = clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            n = int(min(1.0, len(lp) / FS) * FS)
            Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
            ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
            if last is None:
                return float('nan'), ft, None, 'howl_at_lo'
            return last, ft, st, 'ok'
        last = G
        grow, tpk = envelope_stats(lp, T_OBS)          # ④ 末秒−首秒 RMS / 到峰时刻÷窗长
        st = dict(lp_rms=float(HD.rms_db(lp)), grow=float(grow), tpeak_ratio=float(tpk),
                  upper_only=bool(grow > 0 or tpk >= 0.7))
        if a is not None:
            u = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
            c = a.ctr
            st.update(n_notch=len(u),
                      fr=sorted(round(float(s.f), 1) for s in u),
                      depths=sorted(round(float(s.depth), 2) for s in u),
                      dmed=(float(np.median([s.depth for s in u])) if u else float('nan')),
                      gmin=(float(np.min(rec)) if rec else 0.0),
                      n1=int(c.get('N1_cand', 0)), n2=int(c.get('N2_lvl', 0)),
                      n4=int(c.get('N4_born', 0)), n5=int(c.get('N5_howl', 0)),
                      preempt=int(c.get('preempt', 0)), A3=int(c.get('A3_deepen_real', 0)),
                      F2=int(c.get('F2_kept', 0)), F3=int(c.get('F3_dropped', 0)),
                      F4=int(c.get('F4_drop_notched', 0)))
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

    # ── 起跑前再断言一次(G1 的 cell 级复核;闸门本体在 r87_gate.py)──
    P = nhs.Params()
    assert P.recheck_free is False and P.prefer_unnotched is False
    assert P.growth_and_gate is False and P.bw_oct_match is None
    assert P.NN == 8 and P.n_cand == 16 and abs(P.max_depth + 18.) < 1e-9
    assert T_OBS < P.lift_after_s, "T_OBS 必须 < lift_after_s,否则窗内 LIFT"

    W(f"未经 critic 评审 —— r87 单格 tag={A.tag}  [L2/宿主仿真]  预注册 = PREREG_r87b.txt")
    W(f"deps: nhs.py@{sha('nhs.py')} clrig.py@{sha('clrig.py')} "
      f"howl_detect.py@{sha('howl_detect.py')} msg_meter.py@{sha('msg_meter.py')} "
      f"r81_windowcheck.py@{sha('r81_windowcheck.py')}")
    W(f"工作点:T60={T60} seed={sd} / src_rms={SRC:+.1f} dBFS(**标称**) / T_OBS={T_OBS:.0f} s / "
      f"bw_oct=1/5 / T_low={TLOW:+.0f} / T_low_gr={P.T_low_gr:+.0f} / NN={P.NN} 槽全空 / "
      f"n_cand={P.n_cand} / f_cut={F_CUT:.0f}(**环路 8k 以上被带限**) / STEP={STEP} / "
      f"fs=48k / frame={FRAME} / nfft=2^18 / cal_offset_db=0.0 / prefer_unnotched=False")
    W("臂:m0=无proc / A_base=rf关+duck消融(**主列基线**) / A_rf=rf开+duck消融(**主列修法**)")
    W("   D_base=rf关+duck不消融(附列) / D_rf=rf开+duck不消融(附列)")
    W(f"⚠ 仪器底 {FLOOR} dB = STEP/2×√2;而两臂同锚同栅格 ⇒ δ 恒为 0.5 的整数倍(预注册 §5 跑前写死)")
    W("")

    h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
    hb = band_limit(h0, F_CUT)
    he = clrig.h_eff(hb)
    anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
    src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC / 20.))
    ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])

    res = {}
    for (nm, rf, ab) in ARMS:
        t1 = time.time()
        if nm == 'm0':
            m, ft, st, sta = scan(hb, D, lambda: None, anchor - 3, anchor + 4, src, ref)
        else:
            m, ft, st, sta = scan(hb, D, lambda _r=rf, _a=ab: mk_self(_r, _a),
                                  anchor - 1, anchor + 20, src, ref)
        res[nm] = dict(m=m, f_trig=ft, st=st, status=sta, secs=round(time.time() - t1, 1))
        W(f"  臂 {nm:<8} m={m:>7.2f}  f_trig={ft:>8.1f} Hz  status={sta:<10} ({res[nm]['secs']:.0f}s)")
    W("")

    m0 = res['m0']['m']
    W(f"{'臂':>8}{'ΔMSG':>9}{'终点G':>9}{'挂陷':>6}{'深度中位':>10}{'g_duck最深':>11}"
      f"{'末−首dB':>10}{'到峰/窗':>9}{'窗判定':>16}{'f_trig':>10}")
    rows = []
    for (nm, rf, ab) in ARMS:
        r = res[nm]
        st = r['st'] or {}
        d = (r['m'] - m0) if (np.isfinite(r['m']) and np.isfinite(m0)) else float('nan')
        vv = '**⛔ 只能作上界**' if st.get('upper_only') else '✅ 干净'
        W(f"{nm:>8}{d:>9.2f}{r['m']:>9.2f}{st.get('n_notch', -1):>6}"
          f"{st.get('dmed', float('nan')):>10.2f}{st.get('gmin', float('nan')):>11.2f}"
          f"{st.get('grow', float('nan')):>+10.2f}{st.get('tpeak_ratio', float('nan')):>9.2f}"
          f"{vv:>16}{r['f_trig']:>10.1f}")
        rows.append(dict(T60=T60, sd=sd, arm=nm, rf=rf, ablate=ab, src=SRC, T=T_OBS,
                         anchor=float(anchor), m0=m0, m=r['m'], dmsg=d,
                         f_trig=r['f_trig'], status=r['status'], secs=r['secs'], **st))
    W("")
    for nm in ('A_base', 'A_rf', 'D_base', 'D_rf'):
        st = res[nm]['st'] or {}
        W(f"  {nm:<8} 深度分布 {st.get('depths', [])}  频点 {st.get('fr', [])}")
        W(f"           计数 N1={st.get('n1', -1)} N2={st.get('n2', -1)} N4={st.get('n4', -1)} "
          f"N5={st.get('n5', -1)} preempt={st.get('preempt', -1)} A3_deepen_real={st.get('A3', -1)} "
          f"F2_kept={st.get('F2', -1)} F3_dropped={st.get('F3', -1)} F4_drop_notched={st.get('F4', -1)}")
    W("")
    for nm in ('m0', 'A_base', 'A_rf', 'D_base', 'D_rf'):
        ft = res[nm]['f_trig']
        if np.isfinite(ft) and ft < nhs.Params().f_det_lo:
            W(f"  ⚠ {nm}: f_trig={ft:.1f} Hz < f_det_lo=120 ⇒ **NHS 结构上看不见该起振点**(F35/F40.4)")
    W("")

    # ── §7 诊断(**不是闸门**,理由见 PREREG_r87b §7)──────────────
    W("§7 诊断(⛔ 非闸门):A_base vs r76 同工作点已落盘值")
    R = []
    for p in glob.glob(DIR + 'r76_cell_*.json'):
        R += json.load(open(p))
    K = {(r['src'], r['fix'], r['tlow'], r['T60'], r['sd'], r['T']): r for r in R}
    rec = K.get((SRC, 0, TLOW, T60, sd, T_OBS))
    diag = None
    if rec is None:
        W("   ⛔ r76 无该格 ⇒ 无法对照")
    else:
        st = res['A_base']['st'] or {}
        d_now = (res['A_base']['m'] - m0) if np.isfinite(res['A_base']['m']) else float('nan')
        same_d = (abs(d_now - rec['dA']) < 1e-9)
        same_m0 = (abs(m0 - rec['m0']) < 1e-9)
        same_n = (st.get('n_notch', -1) == rec.get('n_notch_Na', -2))
        r76_lp = rec.get('lp_Na')
        r76_lp = float(r76_lp) if isinstance(r76_lp, (int, float)) else float('nan')
        same_lp = bool(abs(float(st.get('lp_rms', 9e9)) - r76_lp) < 0.005)
        diag = dict(same_dmsg=bool(same_d), same_m0=bool(same_m0),
                    same_n_notch=bool(same_n), same_lp=bool(same_lp),
                    r76_dA=rec['dA'], r76_m0=rec['m0'],
                    r76_n_notch_Na=rec.get('n_notch_Na'), r76_lp_Na=rec.get('lp_Na'))
        W(f"   m0      本轮 {m0:+.2f} vs r76 {rec['m0']:+.2f}  ⇒ {'相符' if same_m0 else '**不符**'}")
        W(f"   ΔMSG    本轮 {d_now:+.2f} vs r76 dA={rec['dA']:+.2f}  ⇒ {'相符' if same_d else '**不符**'}")
        W(f"   挂陷    本轮 {st.get('n_notch',-1)} vs r76 n_notch_Na={rec.get('n_notch_Na')}"
          f"  ⇒ {'相符' if same_n else '**不符**'}")
        W(f"   终点lp  本轮 {st.get('lp_rms',float('nan')):+.2f} vs r76 lp_Na={rec.get('lp_Na')}"
          f"  ⇒ {'相符' if same_lp else '**不符**'}")
        W("   ⚠ 四项全符 ⇒ 「recheck_free 默认关 = 行为不变」在 ΔMSG 层面得到一次**事后**支持;")
        W("     ⛔ 它**不等于**盘面上的逐位等价证据件(§1 核①(c):r86a_bitexact 不存在)")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + f'r87_cell_{A.tag}_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + f'r87_cell_{A.tag}.json', 'w') as fp:
        json.dump(dict(rows=rows, diag=diag), fp, default=lambda o: None)


if __name__ == '__main__':
    main()
