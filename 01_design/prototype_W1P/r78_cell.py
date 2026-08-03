"""r78 · `bw_oct` 一维扫描(两职拆开)—— 单格 worker。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r78.txt(跑前落盘)。

一格 = (bw_shape, bw_match) 的一个组合 × 指定的种子子集,固定 src=−20 / 修法关 / T_OBS=12s。
臂:m0(无 proc)/ O(神谕选点,该带宽预算下的上界)/ N(自选+有duck)/ Na(自选+duck消融)

⚠ 评价用邻域(职 D)**钉死 1/5**,四档共用同一把尺子 —— ⛔ 尺子不得跟着被测物一起变。
⚠ 神谕 picks 随 bw_shape 变(职 C)⇒ cov/hit 跨档只可粗读;主判据 = ΔMSG 与挂陷数。
⭐ 搭载:`N0_locmax` / `table_full` / 逐槽 `n_track` ⇒ n_cand=16 与 NT=12 的占用普查(零边际成本)。

⛔ 本文件不含结论性散文。
用法:python3 r78_cell.py --shape 0.125 --match 0.2 --tag C4 --t60 0.2
"""
import sys, json, time, argparse
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME

DEPTH = -18.0
F_CUT = 8000.
STEP = 0.5
T_OBS = 12.0
SRC_DB = -20.0
RULER = 1 / 5          # 职 D:评价用邻域,**钉死**,不随被测 bw 变
DIR = '/home/it1234/processor/01_design/prototype_W1P/'
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def mk_self(ablate, shape, match):
    a = NHS()
    a.P.bw_oct = shape                       # 职 A:滤波器形状
    a.P.bw_oct_match = match                 # 职 B:分配匹配窗(None ⇒ 回落 shape)
    a.P.T_low = -45.
    a.P.prefer_unnotched = False
    if ablate:
        a.duck_gain = lambda: 1.0
    return a


def scan(hb, D, mkf, lo, hi, src, ref):
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
                      ntr_hist=[int(sum(1 for x in ntr if x == k)) for k in range(13)],
                      gmin=float(np.min(rec)) if rec else 0.0,
                      lp_rms=float(HD.rms_db(lp)))
        G += STEP
    return float('nan'), ft, st, 'no_howl'


def axes(fr, picks):
    """⚠ 邻域用 RULER(钉死 1/5),**不用被测的 bw_shape** —— 尺子不跟着被测物变。"""
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
    ap.add_argument('--shape', type=float, required=True)
    ap.add_argument('--match', type=str, default='none')   # 'none' ⇒ 回落 shape
    ap.add_argument('--tag', type=str, required=True)
    ap.add_argument('--t60', type=float, required=True)
    A = ap.parse_args()
    match = None if A.match == 'none' else float(A.match)
    seeds = [(A.t60, s) for s in (0, 1, 2)]
    t0 = time.time()
    W(f"未经 critic 评审 —— r78 单格 tag={A.tag} T60={A.t60}  [L2/宿主仿真]  预注册 = PREREG_r78.txt")
    W(f"格定义:bw_shape(职A 滤波器形状)={A.shape:.6g}(= 1/{1/A.shape:.4g}) / "
      f"bw_match(职B 分配匹配窗)={'回落=shape' if match is None else f'{match:.6g}(= 1/{1/match:.4g})'}")
    W(f"        总陷波带宽预算 = 8 × {A.shape:.6g} = **{8*A.shape:.2f} 倍频程**"
      f"(文献预算 0.8–1.2;现状 1/5 ⇒ 1.60 = 超 1.3–2×)")
    W(f"固定:src_rms={SRC_DB:+.0f} dBFS(标称) / 修法关 / T_OBS={T_OBS:.0f}s / T_low=−45 / "
      f"f_cut={F_CUT:.0f} / 8槽全空 / STEP={STEP} / depth={DEPTH}(臂O)")
    W(f"⚠ 评价用邻域(职D)**钉死 1/{1/RULER:.0f}**,各档共用同一把尺子;"
      f"神谕 picks 随 bw_shape 变(职C)⇒ cov/hit 跨档只可粗读")
    W("⛔ 呈报 = 同条件内比较(Z/Y%),不报绝对值;⛔ 仪器底 0.354 dB,差值 < 它 ⇒ 不可判")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'m0':>8}{'ΔMSG_自选@消融':>15}{'ΔMSG_自选@有duck':>17}"
      f"{'ΔMSG_上界@神谕':>15}{'Z':>7}{'Y%':>6}{'挂陷':>6}{'top1':>7}{'hit':>7}{'cov':>7}")
    rows = []
    for (T60, sd) in seeds:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        picks = pick_excl(he, A.shape, 8)                 # 职 C:随 shape 变
        pk = sorted(round(float(p), 1) for p in picks[:8])
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC_DB / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        m0, _, st0, _ = scan(hb, D, lambda: None, anchor - 3, anchor + 4, src, ref)
        mN, _, stN, _ = scan(hb, D, lambda: mk_self(False, A.shape, match),
                             anchor - 1, anchor + 20, src, ref)
        mA, _, stA, _ = scan(hb, D, lambda: mk_self(True, A.shape, match),
                             anchor - 1, anchor + 20, src, ref)
        mO, _, stO, _ = scan(hb, D, lambda: mk_oracle(picks, A.shape, DEPTH),
                             anchor - 1, anchor + 20, src, ref)
        f = lambda m: (m - m0) if (np.isfinite(m) and np.isfinite(m0)) else float('nan')
        dN, dA, dO = f(mN), f(mA), f(mO)
        Z = (dO - dA) if (np.isfinite(dO) and np.isfinite(dA)) else float('nan')
        Y = (100 * dA / dO) if (np.isfinite(dO) and np.isfinite(dA) and dO) else float('nan')
        t1, hit, cov = axes(stN['fr'] if stN else [], picks)
        W(f"{T60:>5.1f}{sd:>4}{m0:>8.2f}{dA:>15.2f}{dN:>17.2f}{dO:>15.2f}"
          f"{Z:>7.2f}{Y:>6.0f}{(stN['n_notch'] if stN else -1):>6}{str(t1):>7}"
          f"{hit:>7.2f}{cov:>7.2f}")
        W(f"        picks={pk}")
        W(f"        频点 N={stN['fr'] if stN else []}")
        if stN:
            W(f"        ⭐占用普查 N: N0_locmax={stN['n0']} N1_cand={stN['n1']} "
              f"槽数={stN['slots_n']} **table_full={stN['table_full']}**(=len(loc)>16 的槽数) "
              f"**n_track 峰值={stN['ntr_max']}/12** 直方图={stN['ntr_hist']}")
        W(f"        臂O: 挂陷={stO['n_notch'] if stO else -1}/8 频点==picks:"
          f"{(stO['fr'] == pk) if stO else '—'}  (INV-O 构造精确)")
        rows.append(dict(tag=A.tag, shape=A.shape, match=match, T60=T60, sd=sd,
                         m0=m0, dN=dN, dA=dA, dO=dO, Z=Z, Y=Y,
                         n_notch=(stN['n_notch'] if stN else -1),
                         top1=bool(t1), hit=hit, cov=cov,
                         n0=(stN['n0'] if stN else -1), n1=(stN['n1'] if stN else -1),
                         table_full=(stN['table_full'] if stN else -1),
                         slots_n=(stN['slots_n'] if stN else -1),
                         ntr_max=(stN['ntr_max'] if stN else -1),
                         ntr_hist=(stN['ntr_hist'] if stN else []),
                         gmin=(stN['gmin'] if stN else float('nan')),
                         n_notch_O=(stO['n_notch'] if stO else -1),
                         invO=(bool(stO['fr'] == pk and stO['n_notch'] == 8) if stO else False),
                         picks=pk, fr=(stN['fr'] if stN else [])))
        W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + f'r78_cell_{A.tag}_T{A.t60}_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + f'r78_cell_{A.tag}_T{A.t60}.json', 'w') as fp:
        json.dump(rows, fp, default=lambda o: None)


if __name__ == '__main__':
    main()
