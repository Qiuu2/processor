"""r80 · **合成实验**(陷波 × 频移)—— 单格 worker。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r80.txt(跑前落盘,含两条守卫的实测结果)。

臂(**四臂全部挂同一条 FreqShifter 路径**,非频移臂 df=0 ⇒ 同一被控对象):
  m0        无 NHS,df=0
  陷波      NHS,  df=0            (--base 格才跑)
  频移      无 NHS,df=Δf
  合成-后   NHS → shifter          (陷波在前 = Schroeder Fig.2 的位置)
  合成-前   shifter → NHS          (移频在前 ⇒ 陷波看到已搬移的谱)

⚠ 群延迟 5.33 ms(513 taps)⇒ 环路 8.0 → 13.33 ms
  ⇒ 轮内比较干净(四臂同被控对象),但 ⛔ 绝对值不得与 r76/r78/r79 并列
  ⇒ ⛔ 且不声称"延迟在差里抵消"(D6-ai:只有两臂依赖相同才成立)
⚠ 低频 120–200 Hz 镜像仅 −30…−55 dB ⇒ 该段频移不是干净单边带 ⇒ 结论打折

⛔ 本文件不含结论性散文。
用法:python3 r80_cell.py --df 5 --tag D05
      python3 r80_cell.py --df 0 --base 1 --tag BASE
"""
import sys, json, time, argparse
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME
from fshift import FreqShifter

BW_OCT = 1 / 5
F_CUT = 8000.
STEP = 0.5
T_OBS = 12.0
SRC_DB = -20.0
NTAPS = 513
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DIR = '/home/it1234/processor/01_design/prototype_W1P/'
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def mk_nhs():
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = -45.
    a.P.prefer_unnotched = False
    a.duck_gain = lambda: 1.0          # duck 消融 ⇒ 锁定被测机制 = 陷波(F33)
    return a


def make_proc(df, use_nhs, shift_first):
    """返回 (proc, get_state)。四臂共用同一条 shifter 路径(df=0 ⇒ 恒等但同延迟)。"""
    sh = FreqShifter(df, FS, ntaps=NTAPS)
    a = mk_nhs() if use_nhs else None

    def proc(blk):
        if a is None:
            return sh.process(blk)
        if shift_first:
            return a.process_frame(sh.process(blk), GR)
        return sh.process(a.process_frame(blk, GR))

    return proc, (lambda: a)


def scan(hb, D, mkf, lo, hi, src, ref):
    G, last, st = lo, None, None
    while G <= hi + 1e-9:
        proc, get_a = mkf()
        _, lp = clrig.Loop(hb, D, G, proc=proc).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            if last is None:
                return float('nan'), None, 'howl_at_lo'
            return last, st, 'ok'
        last = G
        a = get_a()
        if a is None:
            st = dict(n_notch=-1, lp_rms=float(HD.rms_db(lp)))
        else:
            used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
            st = dict(n_notch=len(used),
                      fr=sorted(round(float(s.f), 1) for s in used),
                      n2=int(a.ctr.get('N2_lvl', 0)),
                      lp_rms=float(HD.rms_db(lp)))
        G += STEP
    return float('nan'), st, 'no_howl'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--df', type=float, required=True)
    ap.add_argument('--tag', type=str, required=True)
    ap.add_argument('--base', type=int, default=0)   # 1 ⇒ 只跑 m0 + 陷波
    A = ap.parse_args()
    t0 = time.time()
    gd = (NTAPS - 1) / 2 / FS * 1000.
    W(f"未经 critic 评审 —— r80 单格 tag={A.tag}  Δf={A.df:.0f} Hz  [L2/宿主仿真]")
    W(f"预注册 = PREREG_r80.txt(含两条守卫实测:①搬移量误差全 0.00、镜像 −64 dB @1kHz;②200 Hz 阳性对照)")
    W(f"频移器:Hilbert {NTAPS} taps,群延迟 **{gd:.2f} ms** ⇒ 环路 8.00 → **{8.0+gd:.2f} ms**")
    W(f"⚠ 四臂**全部**挂同一条 shifter 路径(非频移臂 df=0)⇒ 同一被控对象;")
    W(f"  ⛔ 但**不声称**延迟在差里抵消(D6-ai);⛔ 绝对值不得与 r76/r78/r79 并列")
    W(f"⚠ 低频 120–200 Hz 镜像仅 −30…−55 dB ⇒ 该段频移非干净单边带 ⇒ 结论打折")
    W(f"固定:src={SRC_DB:+.0f} dBFS / 修法关 / T_OBS={T_OBS:.0f}s / 陷波 8×1/5(本轮不动)/ duck 消融")
    W("")
    hdr = f"{'T60':>5}{'sd':>4}{'m0':>8}"
    hdr += f"{'ΔMSG_陷波':>11}" if A.base else f"{'ΔMSG_频移':>11}{'合成-后':>10}{'合成-前':>10}"
    hdr += f"{'挂陷':>6}"
    W(hdr)
    rows = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC_DB / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        m0, _, _ = scan(hb, D, lambda: make_proc(0.0, False, False),
                        anchor - 3, anchor + 6, src, ref)
        f = lambda m: (m - m0) if (np.isfinite(m) and np.isfinite(m0)) else float('nan')
        r = dict(tag=A.tag, df=A.df, T60=T60, sd=sd, m0=m0, anchor=float(anchor))
        if A.base:
            mN, stN, _ = scan(hb, D, lambda: make_proc(0.0, True, False),
                              anchor - 1, anchor + 20, src, ref)
            r['d_notch'] = f(mN)
            r['n_notch'] = stN['n_notch'] if stN else -1
            r['fr'] = stN['fr'] if stN else []
            W(f"{T60:>5.1f}{sd:>4}{m0:>8.2f}{r['d_notch']:>11.2f}{r['n_notch']:>6}")
        else:
            mS, _, _ = scan(hb, D, lambda: make_proc(A.df, False, False),
                            anchor - 1, anchor + 20, src, ref)
            mCa, stCa, _ = scan(hb, D, lambda: make_proc(A.df, True, False),
                                anchor - 1, anchor + 20, src, ref)
            mCb, stCb, _ = scan(hb, D, lambda: make_proc(A.df, True, True),
                                anchor - 1, anchor + 20, src, ref)
            r.update(d_shift=f(mS), d_comp_after=f(mCa), d_comp_before=f(mCb),
                     n_notch_after=(stCa['n_notch'] if stCa else -1),
                     n_notch_before=(stCb['n_notch'] if stCb else -1),
                     fr_after=(stCa['fr'] if stCa else []))
            W(f"{T60:>5.1f}{sd:>4}{m0:>8.2f}{r['d_shift']:>11.2f}"
              f"{r['d_comp_after']:>10.2f}{r['d_comp_before']:>10.2f}"
              f"{r['n_notch_after']:>6}")
        rows.append(r)
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + f'r80_cell_{A.tag}_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + f'r80_cell_{A.tag}.json', 'w') as fp:
        json.dump(rows, fp, default=lambda o: None)


if __name__ == '__main__':
    main()
