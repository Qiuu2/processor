"""r79 · **等预算线** NN × bw_oct ≡ 1.00 oct —— 单格 worker。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r79.txt(跑前落盘)。

一格 = (NN, bw_oct) 的一个组合 × 指定种子子集。固定 src=−20 / 修法关 / T_OBS=12s / n_cand=48。
臂:m0(无 proc)/ O(神谕选点,**⛔ 全程不称「上界」**)/ N(自选+有duck)/ Na(自选+duck消融)

⚠ NN 只在 `NHS.__init__` 里尺寸化 `self.slots`(nhs.py:255)⇒ **必须构造前设进 Params**,
  构造后改 `P.NN` 不会重建槽 —— 与 `T_low_gr` 同型的坑,已实测确认。
⚠ 评价用尺子(职 D)**钉死 1/5**,各档共用;神谕 picks 随 (NN, bw) 变(职 C)⇒ 抬头已写明。
⚠ `15 Hz` 地板只作用在【匹配窗】`_bw_hz`,不作用在【滤波器形状】`set_coef`。

⛔ 本文件不含结论性散文。
用法:python3 r79_cell.py --nn 24 --bw 0.0416667 --ncand 48 --tag N24 --seeds 0,1,2 --t60 0.2
"""
import sys, json, time, argparse
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, GR, FRAME

DEPTH = -18.0
F_CUT = 8000.
STEP = 0.5
T_OBS = 12.0
SRC_DB = -20.0
RULER = 1 / 5                 # 职 D:评价用邻域,**钉死**
DIR = '/home/it1234/processor/01_design/prototype_W1P/'
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def mk_params(NN, bw, ncand):
    """⚠ NN 必须在构造前进 Params —— 构造后改不会重建 slots。"""
    P = nhs.Params()
    P.NN = NN
    P.bw_oct = bw
    P.bw_oct_match = None        # 依 r78 可加性 ⇒ 匹配窗跟形状同动
    P.n_cand = ncand
    P.T_low = -45.
    P.prefer_unnotched = False
    return P


def mk_self(ablate, NN, bw, ncand):
    a = NHS(P=mk_params(NN, bw, ncand))
    assert len(a.slots) == NN, f"槽数未随 NN 重建:{len(a.slots)} != {NN}"
    if ablate:
        a.duck_gain = lambda: 1.0
    return a


def mk_oracle_nn(picks, NN, bw, ncand):
    """臂 O:神谕选点、槽钉死、T_low=999。⛔ 本轮不称「上界」(r78 已证该名在 1/8 及以下不成立)。"""
    a = NHS(P=mk_params(NN, bw, ncand))
    assert len(a.slots) == NN, f"槽数未随 NN 重建:{len(a.slots)} != {NN}"
    for i, f_ in enumerate(picks[:len(a.slots)]):
        s = a.slots[i]
        s.st = nhs.NotchSlot.HOLD
        s.f = f_
        s.depth = DEPTH
        s.target = DEPTH
        s.set_coef(FS, bw)
    a.P.T_low = 999.
    a.duck_gain = lambda: 1.0
    return a


def scan(hb, D, mkf, lo, hi, src, ref):
    G, last, st = lo, None, None
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
            if last is None:
                return float('nan'), None, 'howl_at_lo'
            return last, st, 'ok'
        last = G
        if a is None:
            st = dict(lp_rms=float(HD.rms_db(lp)))
        else:
            used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
            ntr = [int(e.get('n_track', -1)) for e in a.log] if a.log else []
            st = dict(n_notch=len(used),
                      fr=sorted(round(float(s.f), 1) for s in used),
                      n1=int(a.ctr.get('N1_cand', 0)), n2=int(a.ctr.get('N2_lvl', 0)),
                      n0=int(a.ctr.get('N0_locmax', 0)),
                      table_full=int(a.ctr.get('table_full', 0)),
                      slots_n=int(a.ctr.get('slots', 0)),
                      ntr_max=(max(ntr) if ntr else -1),
                      gmin=float(np.min(rec)) if rec else 0.0,
                      lp_rms=float(HD.rms_db(lp)))
        G += STEP
    return float('nan'), st, 'no_howl'


def axes(fr, picks):
    if not picks or not fr:
        return (False, float('nan'), 0.0 if picks else float('nan'))
    def bw(f):
        return max(f * RULER, 15.)
    t = float(picks[0])
    t1 = any(abs(f - t) <= bw(t) / 2 for f in fr)
    hit = sum(1 for f in fr if any(abs(f - p) <= bw(p) / 2 for p in picks)) / len(fr)
    cov = sum(1 for p in picks if any(abs(f - p) <= bw(p) / 2 for f in fr)) / len(picks)
    return (bool(t1), hit, cov)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nn', type=int, required=True)
    ap.add_argument('--bw', type=float, required=True)
    ap.add_argument('--ncand', type=int, required=True)
    ap.add_argument('--tag', type=str, required=True)
    ap.add_argument('--seeds', type=str, required=True)
    ap.add_argument('--t60', type=float, required=True)
    A = ap.parse_args()
    seeds = [(A.t60, int(s)) for s in A.seeds.split(',')]
    f_floor = 15.0 / A.bw                       # 地板转折频率
    t0 = time.time()
    W(f"未经 critic 评审 —— r79 单格 tag={A.tag} T60={A.t60} seeds={A.seeds}  [L2/宿主仿真]")
    W(f"预注册 = PREREG_r79.txt。**等预算线**:NN × bw_oct = {A.nn} × {A.bw:.6g}"
      f" = **{A.nn*A.bw:.3f} 倍频程**(文献预算 0.8–1.2)")
    W(f"格定义:NN={A.nn} / bw_oct=1/{1/A.bw:.4g} / n_cand={A.ncand}(=2×maxNN,四格恒定"
      f" ⇒ n_cand 不与 NN 共变) / bw_oct_match=回落(依 r78 可加性)")
    W(f"固定:src_rms={SRC_DB:+.0f} dBFS(标称) / 修法关 / T_OBS={T_OBS:.0f}s / T_low=−45 / "
      f"f_cut={F_CUT:.0f} / STEP={STEP} / depth={DEPTH}(臂O)")
    W(f"⛔⛔ **本轮全程不用「上界」一词** —— r78 已实测该名在 bw_oct ≤ 1/8 上不成立"
      f"(5/30 格臂 Na ≥ 臂 O 且 INV-O 全 OK)⇒ 一律称 `臂O@神谕选点`")
    W(f"⚠ 职C:神谕 picks 随 (NN, bw) 变 ⇒ **各档的臂 O 是【该 NN 与该预算下的】臂 O,不是同一基准**")
    W(f"⚠ 职D:评价尺子**钉死 1/{1/RULER:.0f}**,各档共用")
    W(f"⚠ 地板:`_bw_hz = max(f·bw, 15Hz)` ⇒ **f < {f_floor:.0f} Hz 处匹配窗被顶成 15 Hz**"
      f"(检测带下沿 120 Hz)⇒ 该段差异⛔不得归因给 NN;地板**不作用于滤波器形状**")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'m0':>8}{'ΔMSG_自选@消融':>15}{'ΔMSG_自选@有duck':>17}"
      f"{'臂O@神谕':>11}{'Z':>7}{'挂陷':>6}{'/NN':>5}{'top1':>7}{'hit':>7}{'cov':>7}{'地板内%':>8}")
    rows = []
    for (T60, sd) in seeds:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        picks = pick_excl(he, A.bw, A.nn)                  # 职 C:随 NN 与 bw 变
        pk = sorted(round(float(p), 1) for p in picks[:A.nn])
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC_DB / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        m0, st0, _ = scan(hb, D, lambda: None, anchor - 3, anchor + 4, src, ref)
        mN, stN, _ = scan(hb, D, lambda: mk_self(False, A.nn, A.bw, A.ncand),
                          anchor - 1, anchor + 20, src, ref)
        mA, stA, _ = scan(hb, D, lambda: mk_self(True, A.nn, A.bw, A.ncand),
                          anchor - 1, anchor + 20, src, ref)
        mO, stO, _ = scan(hb, D, lambda: mk_oracle_nn(picks, A.nn, A.bw, A.ncand),
                          anchor - 1, anchor + 20, src, ref)
        f = lambda m: (m - m0) if (np.isfinite(m) and np.isfinite(m0)) else float('nan')
        dN, dA, dO = f(mN), f(mA), f(mO)
        Z = (dO - dA) if (np.isfinite(dO) and np.isfinite(dA)) else float('nan')
        t1, hit, cov = axes(stN['fr'] if stN else [], picks)
        fr = stN['fr'] if stN else []
        pfloor = (100.0 * sum(1 for x in fr if x < f_floor) / len(fr)) if fr else float('nan')
        invO = bool(stO and stO['n_notch'] == A.nn and stO['fr'] == pk)
        W(f"{T60:>5.1f}{sd:>4}{m0:>8.2f}{dA:>15.2f}{dN:>17.2f}{dO:>11.2f}{Z:>7.2f}"
          f"{(stN['n_notch'] if stN else -1):>6}{A.nn:>5}{str(t1):>7}{hit:>7.2f}{cov:>7.2f}"
          f"{pfloor:>8.1f}")
        W(f"        INV-O(挂陷=={A.nn} ∧ 频点==picks):{'OK' if invO else '⛔FAIL'}"
          f"(臂O挂陷={stO['n_notch'] if stO else -1}/{A.nn})")
        if stN:
            W(f"        ⭐占用: N0_locmax/槽={stN['n0']/max(stN['slots_n'],1):.1f} "
              f"N1_cand/槽={stN['n1']/max(stN['slots_n'],1):.2f}(n_cand={A.ncand}) "
              f"**table_full={stN['table_full']}/{stN['slots_n']}** n_track峰值={stN['ntr_max']}/12 "
              f"g_duck最深={stN['gmin']:+.2f}")
        W(f"        频点 N={fr}")
        rows.append(dict(tag=A.tag, nn=A.nn, bw=A.bw, ncand=A.ncand, T60=T60, sd=sd,
                         m0=m0, dN=dN, dA=dA, dO=dO, Z=Z,
                         n_notch=(stN['n_notch'] if stN else -1),
                         top1=bool(t1), hit=hit, cov=cov, pct_floor=pfloor,
                         n0=(stN['n0'] if stN else -1), n1=(stN['n1'] if stN else -1),
                         table_full=(stN['table_full'] if stN else -1),
                         slots_n=(stN['slots_n'] if stN else -1),
                         ntr_max=(stN['ntr_max'] if stN else -1),
                         gmin=(stN['gmin'] if stN else float('nan')),
                         n_notch_O=(stO['n_notch'] if stO else -1), invO=invO,
                         picks=pk, fr=fr, f_floor=f_floor))
        W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + f'r79_cell_{A.tag}_T{A.t60}_s{A.seeds.replace(",","")}_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + f'r79_cell_{A.tag}_T{A.t60}_s{A.seeds.replace(",","")}.json', 'w') as fp:
        json.dump(rows, fp, default=lambda o: None)


if __name__ == '__main__':
    main()
