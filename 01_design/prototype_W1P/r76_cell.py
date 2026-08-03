"""r76 · 源电平扫描【补齐】—— 单格 worker。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r76.txt(跑前落盘)。

一格 = (src_rms_dbfs, prefer_unnotched, T_low) 的一个组合 × 6 种子 × T_OBS {6,12}。
臂:m0(proc=None,标度不变性对照)/ O(神谕选点,上界;仅 --oracle 1 的格跑)
    N(NHS 自选 + duck 不消融)/ Na(NHS 自选 + duck 消融,= 兜底消融列)

⛔ 本文件不含任何结论性散文。脚本里唯一的判定语句 = 不变量与阈值比较。
用法:python3 r76_cell.py --src -20 --fix 0 --tlow -45 --oracle 1 --tag s20f0
"""
import sys, os, json, time, argparse
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME

BW_OCT = 1 / 5
DEPTH = -18.0
F_CUT = 8000.
STEP = 0.5
RUNGS = [6.0, 12.0]
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DIR = '/home/it1234/processor/01_design/prototype_W1P/'

OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def src_of(T, sd, lvl_db):
    """⚠ 与 r64/r75 逐字同构:N(0,1) 的 RMS=1 ⇒ 直接乘 10**(L/20) 即得目标 RMS。
    同一 seed 下长窗的前缀 == 短窗 ⇒ 阶梯各档是【严格延长】,不是换信号。"""
    return np.random.default_rng(sd).standard_normal(int(T * FS)) * (10 ** (lvl_db / 20.))


def mk_self(ablate, fix, tlow):
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = tlow                 # ⇒ T_low_gr 不重算(nhs.py:67 在 __init__ 已算死)
    a.P.prefer_unnotched = bool(fix)  # **非提交修法**
    if ablate:
        a.duck_gain = lambda: 1.0
    return a


def scan(hb, D, mkf, lo, hi, src, ref):
    """返回 (m, f_trig, st, status)。m = 最后一个不起振的 G。"""
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
        # ★ lp_rms = 报数点(该 G 上)求和节点 RMS ⇒ 用于拆效应 B(PREREG §3 Hr2b)
        lprms = float(HD.rms_db(lp))
        if a is None:
            st = dict(lp_rms=lprms)
        else:
            used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
            st = dict(n_notch=len(used),
                      fr=sorted(round(float(s.f), 1) for s in used),
                      n1=int(a.ctr.get('N1_cand', 0)),
                      n2=int(a.ctr.get('N2_lvl', 0)),
                      n4=int(a.ctr.get('N4_born', 0)),
                      n5=int(a.ctr.get('N5_howl', 0)),
                      preempt=int(a.ctr.get('preempt', 0)),
                      panic=int(sum(1 for e in a.cls_log if e.get('cls') == 'PANIC')),
                      gmin=float(np.min(rec)) if rec else 0.0,
                      lp_rms=lprms)
        G += STEP
    return float('nan'), ft, st, 'no_howl'


def axes(fr, picks):
    """选点四量之三(第四量 = 挂陷数,在 st 里)。bw 与分配匹配窗同源。"""
    if not picks or not fr:
        return (False, float('nan'), 0.0 if picks else float('nan'))
    def bw(f):
        return max(f * BW_OCT, 15.)
    t = float(picks[0])
    t1 = any(abs(f - t) <= bw(t) / 2 for f in fr)
    hit = sum(1 for f in fr if any(abs(f - p) <= bw(p) / 2 for p in picks)) / len(fr)
    cov = sum(1 for p in picks if any(abs(f - p) <= bw(p) / 2 for f in fr)) / len(picks)
    return (bool(t1), hit, cov)


def inv_N(st, d):
    """INV-N 三分(PREREG_r64 修订 A-1;零动作是**合法的不利结果**,不得剔除)。"""
    if st is None:
        return 'FAIL', '无状态(未取到不起振点)'
    if st['n2'] > 0 and st['n_notch'] > 0:
        return 'OK', f"N2_lvl={st['n2']},挂陷={st['n_notch']}"
    if np.isfinite(d) and abs(d) <= STEP + 1e-9:
        return 'ZERO_ACT', f"N2_lvl={st['n2']},挂陷={st['n_notch']},ΔMSG={d:+.2f}(零动作,计入统计)"
    return 'FAIL', f"N2_lvl={st['n2']},挂陷={st['n_notch']},ΔMSG={d:+.2f} ⇒ 零动作却有收益"


def inv_O(st, pk):
    """INV-O **构造精确**(修订 B-1);旧 `N2_lvl==0` 仅作诊断量打印。见 PREREG_r76 §4 偏离声明。"""
    if st is None:
        return 'FAIL', '无状态(未取到不起振点)'
    same = (st['fr'] == pk)
    good = (st['n_notch'] == 8 and same)
    return ('OK' if good else 'FAIL',
            f"挂陷={st['n_notch']}/8,频点==picks:{same}(诊断 N2_lvl={st['n2']},非判据)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', type=float, required=True)
    ap.add_argument('--fix', type=int, required=True)
    ap.add_argument('--tlow', type=float, default=-45.)
    ap.add_argument('--oracle', type=int, default=0)
    ap.add_argument('--tag', type=str, required=True)
    A = ap.parse_args()
    t_all = time.time()
    assert max(RUNGS) < nhs.Params().lift_after_s, "T_OBS 必须 < lift_after_s,否则臂 O 预挂槽会在窗内 LIFT"

    W(f"未经 critic 评审 —— r76 单格 tag={A.tag}  [L2/宿主仿真]  预注册 = PREREG_r76.txt")
    W(f"格定义:src_rms_dbfs={A.src:+.0f} / prefer_unnotched={bool(A.fix)}(**非提交修法**) / "
      f"T_low={A.tlow:+.0f} / 臂O={'跑' if A.oracle else '不跑'}")
    W(f"工作点:cal_offset_db=0.0(nhs.py:236 默认,从未被用过) / fs=48k / frame={FRAME} / "
      f"f_cut={F_CUT:.0f} / STEP={STEP} / bw_oct=1/5 / depth={DEPTH}(臂O) / 8槽全空(臂N,Na) / "
      f"T_OBS∈{RUNGS} / nfft=2^18 / T_low_gr={nhs.Params().T_low_gr:+.0f}(构造后不随 T_low 重算)")
    W("臂:m0=无 proc(标度不变性对照) / O=神谕选点 T_low=999(**上界**,⛔禁称 NHS 实测) / "
      "N=自选+有duck / Na=自选+duck消融(**兜底消融列**)")
    W("")
    hdr = (f"{'T60':>5}{'sd':>4}{'T_OBS':>7}{'m0':>8}{'ΔMSG_自选@有duck':>17}"
           f"{'ΔMSG_自选@消融':>16}{'ΔMSG_上界@神谕':>16}"
           f"{'过门率':>9}{'挂陷':>6}{'top1':>7}{'hit':>7}{'cov':>7}"
           f"{'PANIC':>7}{'lp_rms@m_N':>12}{'INV_N':>10}{'INV_O':>7}")
    W(hdr)
    rows = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        picks = pick_excl(he, BW_OCT, 8)
        pk = sorted(round(float(p), 1) for p in picks[:8])
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        for T in RUNGS:
            src = src_of(T, sd, A.src)
            ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
            m0, ft0, st0, sta0 = scan(hb, D, lambda: None, anchor - 3, anchor + 4, src, ref)
            mN, ftN, stN, staN = scan(hb, D, lambda: mk_self(False, A.fix, A.tlow),
                                      anchor - 1, anchor + 20, src, ref)
            mA, ftA, stA, staA = scan(hb, D, lambda: mk_self(True, A.fix, A.tlow),
                                      anchor - 1, anchor + 20, src, ref)
            if A.oracle:
                mO, ftO, stO, staO = scan(hb, D, lambda: mk_oracle(picks, BW_OCT, DEPTH),
                                          anchor - 1, anchor + 20, src, ref)
            else:
                mO, ftO, stO, staO = float('nan'), float('nan'), None, 'skipped'
            f = lambda m: (m - m0) if (np.isfinite(m) and np.isfinite(m0)) else float('nan')
            dN, dA, dO = f(mN), f(mA), f(mO)
            t1, hit, cov = axes(stN['fr'] if stN else [], picks)
            rate = (stN['n2'] / stN['n1']) if (stN and stN['n1']) else float('nan')
            iN, sN = inv_N(stN, dN)
            iA, sA = inv_N(stA, dA)
            iNc = 'FAIL' if 'FAIL' in (iN, iA) else ('ZERO_ACT' if 'ZERO_ACT' in (iN, iA) else 'OK')
            if A.oracle:
                iO, sO = inv_O(stO, pk)
            else:
                iO, sO = '—', '未跑'
            W(f"{T60:>5.1f}{sd:>4}{T:>7.0f}{m0:>8.2f}{dN:>17.2f}{dA:>16.2f}{dO:>16.2f}"
              f"{100*rate:>8.2f}%{(stN['n_notch'] if stN else -1):>6}{str(t1):>7}"
              f"{hit:>7.2f}{cov:>7.2f}{(stN['panic'] if stN else -1):>7}"
              f"{(stN['lp_rms'] if stN else float('nan')):>12.2f}{iNc:>10}{iO:>7}")
            W(f"        不变量 N:{iN}/{sN} | Na:{iA}/{sA} | O:{iO}/{sO}")
            W(f"        计数 N: N1_cand={stN['n1'] if stN else -1} N2_lvl={stN['n2'] if stN else -1} "
              f"N4_born={stN['n4'] if stN else -1} N5_howl={stN['n5'] if stN else -1} "
              f"preempt={stN['preempt'] if stN else -1} g_duck最深={stN['gmin'] if stN else float('nan'):+.2f} dB")
            W(f"        频点 N:{stN['fr'] if stN else []}")
            W(f"        picks :{pk}")
            W(f"        lp_rms@m: m0={st0['lp_rms'] if st0 else float('nan'):+.2f} "
              f"N={stN['lp_rms'] if stN else float('nan'):+.2f} "
              f"Na={stA['lp_rms'] if stA else float('nan'):+.2f} "
              f"O={stO['lp_rms'] if stO else float('nan'):+.2f} dBFS  | "
              f"m: m0={m0:+.2f} N={mN:+.2f} Na={mA:+.2f} O={mO:+.2f} dB")
            W(f"        f_trig: m0={ft0:.1f} N={ftN:.1f} Na={ftA:.1f} O={ftO:.1f} Hz  "
              f"status={ {'m0': sta0, 'N': staN, 'Na': staA, 'O': staO} }")
            rows.append(dict(src=A.src, fix=A.fix, tlow=A.tlow, T60=T60, sd=sd, T=T,
                             anchor=float(anchor), m0=m0, mN=mN, mA=mA, mO=mO,
                             dN=dN, dA=dA, dO=dO, rate=rate,
                             n_notch=(stN['n_notch'] if stN else -1),
                             top1=bool(t1), hit=hit, cov=cov,
                             n1=(stN['n1'] if stN else -1), n2=(stN['n2'] if stN else -1),
                             panic=(stN['panic'] if stN else -1),
                             gmin=(stN['gmin'] if stN else float('nan')),
                             fr=(stN['fr'] if stN else []), picks=pk,
                             lp_m0=(st0['lp_rms'] if st0 else float('nan')),
                             lp_N=(stN['lp_rms'] if stN else float('nan')),
                             lp_Na=(stA['lp_rms'] if stA else float('nan')),
                             lp_O=(stO['lp_rms'] if stO else float('nan')),
                             n_notch_Na=(stA['n_notch'] if stA else -1),
                             n_notch_O=(stO['n_notch'] if stO else -1),
                             n2_O=(stO['n2'] if stO else -1),
                             inv_N=iNc, inv_Na=iA, inv_N_only=iN, inv_O=iO,
                             st_m0=sta0, st_N=staN, st_Na=staA, st_O=staO))
        W("")
    W(f"总耗时 {time.time()-t_all:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + f'r76_cell_{A.tag}_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + f'r76_cell_{A.tag}.json', 'w') as fp:
        json.dump(rows, fp, default=lambda o: None)


if __name__ == '__main__':
    main()
