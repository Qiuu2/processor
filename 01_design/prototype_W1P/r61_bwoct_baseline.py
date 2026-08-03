"""r61 · `bw_oct` 扫描 + **M-1 等代价平坦衰减 baseline** —— 整改队列第 2 项。

预注册:PREREG_r61.txt(Hn1–Hn4、等代价定义、三臂定义,跑前落盘)
输出   :r61_bwoct_baseline_out.txt   [L2/宿主仿真]
deps   : clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316,
         howl_detect.py@fd63e901f2d8be33, msg_meter.py, dmsg_two_arm.py,
         r57_bandlimit.band_limit(BL-1 已过)

⛔ B-1 不重蹈:三臂并列,报数经 `dmsg_two_arm.DMSGReport`(**缺臂即抛异常**)。
   臂 O = 神谕选点(上界) / 臂 N = NHS 自选(真实性能) / 臂 F = 等代价平坦(baseline)。
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from dmsg_two_arm import DMSGReport

FRAME = 64
STEP = 0.5
F_CUT = 8000.
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
BWS = [1/5, 1/8, 1/12]
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
OUT = []


def W(s):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def bw_of(f, bw_oct):
    """与 `nhs.py:709` / `r49` 同一约定:带宽(Hz) = max(f·bw_oct, 15)。
    ⚠ 这不是 RBJ 的"倍频程带宽"严格定义(那是 f·(2^(N/2)−2^(−N/2)));
      两者在 N=1/5 时差 ~1.43×。**本文全程用代码约定,并在报头写明**,避免同族二义。"""
    return max(f * bw_oct, 15.0)


def notch_H(f0, fg, bw_oct, depth_db):
    A = 10 ** (depth_db / 40.)
    w0 = 2 * np.pi * f0 / FS
    al = np.sin(w0) * np.sinh(np.log(2) / 2 * bw_oct * w0 / np.sin(w0))
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    return freqz(b, a, worN=2 * np.pi * fg / FS)[1]


def pick_excl(he, bw_oct, k=8):
    fc, mdb = clrig.critical_points(he)
    o = list(np.argsort(mdb)[::-1])
    picks, used = [], np.zeros(len(fc), bool)
    for i in o:
        if used[i] or len(picks) >= k:
            continue
        f_ = float(fc[i])
        picks.append(f_)
        used |= (np.abs(fc - f_) <= bw_of(f_, bw_oct))
    return picks


def coverage(picks, bw_oct, lo=100., hi=8000.):
    """检测带内被陷波覆盖的比例(区间**并集**,不是求和 ⇒ 重叠不重复计)。"""
    iv = []
    for f0 in picks:
        b = bw_of(f0, bw_oct)
        iv.append((max(lo, f0 - b / 2), min(hi, f0 + b / 2)))
    iv = [x for x in iv if x[1] > x[0]]
    iv.sort()
    tot, cur_a, cur_b = 0.0, None, None
    for a, b in iv:
        if cur_a is None:
            cur_a, cur_b = a, b
        elif a <= cur_b:
            cur_b = max(cur_b, b)
        else:
            tot += cur_b - cur_a
            cur_a, cur_b = a, b
    if cur_a is not None:
        tot += cur_b - cur_a
    return tot / (hi - lo)


def cost_median_db(he, picks, bw_oct, depth_db):
    """代价 = **检测带 100–8000 Hz 内 20log10|N(ω)| 的中位**(预注册定义,与 r49 同源)。"""
    f0, _ = clrig.F_response(he, 1 << 18)
    m = (f0 >= 100.) & (f0 <= 8000.)
    fm = f0[m]
    N = np.ones(len(fm), dtype=complex)
    for p in picks:
        N = N * notch_H(p, fm, bw_oct, depth_db)
    return float(20 * np.log10(np.median(np.abs(N))))


def mk_oracle(picks, bw_oct, depth_db):
    """臂 O:神谕选点、槽钉死、`T_low=999` ⇒ **上界**(见 dmsg_two_arm 模块头)。"""
    a = NHS()
    a.P.bw_oct = bw_oct
    for i, f_ in enumerate(picks[:len(a.slots)]):
        s = a.slots[i]
        s.st = nhs.NotchSlot.HOLD
        s.f = f_
        s.depth = depth_db
        s.target = depth_db
        s.set_coef(FS, bw_oct)
    a.P.T_low = 999.
    a.duck_gain = lambda: 1.0          # 锁定被测机制 = 陷波(F33)
    return a


def mk_nhs_self(bw_oct):
    """臂 N:**NHS 默认参数、槽全空、检测/分类/分配全开** ⇒ 真实性能。
    ⚠ duck **不消融** —— 它是 NHS 设计的一部分;是否被触发由 `g_duck` 最深值报出。"""
    a = NHS()
    a.P.bw_oct = bw_oct
    return a


def src_of(T, s):
    return 1e-3 * np.random.default_rng(s).standard_normal(int(T * FS))


def scan(h, D, mk, lo, hi, src, ref, want_state=False):
    G, last = lo, None
    st = None
    while G <= hi + 1e-9:
        alg = mk()
        rec = []
        if alg is None:
            pf = None
        else:
            def pf(blk, _a=alg, _r=rec):
                y = _a.process_frame(blk, GR)
                _r.append(_a.g_duck_db)
                return y
        _, lp = clrig.Loop(h, D, G, proc=pf).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            n = int(min(1.0, len(lp) / FS) * FS)
            Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
            ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
            return (float('nan') if last is None else last), st, ft
        last = G
        if want_state and alg is not None:
            used = [s for s in alg.slots if s.st != nhs.NotchSlot.FREE]
            st = dict(n_notch=len(used), gmin=float(np.min(rec)) if rec else 0.0,
                      fr=sorted(round(float(s.f), 1) for s in used))
        G += STEP
    return float('nan'), st, float('nan')


def main():
    DEPTH = -18.0
    W("r61 · bw_oct 扫描 + M-1 等代价平坦衰减 baseline")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 "
      "howl_detect.py@fd63e901f2d8be33 msg_meter.py dmsg_two_arm.py")
    W("[L2/宿主仿真]  预注册 = PREREG_r61.txt   f_cut=8k / depth=−18dB / 8 槽 / STEP=0.5dB")
    W("⚠ 带宽约定 = 代码约定 `bw(Hz) = max(f·bw_oct, 15)`(nhs.py:709 同源),")
    W("   **不是** RBJ 严格倍频程带宽 `f·(2^(N/2)−2^(−N/2))`;N=1/5 时两者差 ~1.43×。")
    W("⚠ 三臂:ORACLE=神谕选点(上界) / NHS自选=真实性能 / FLAT=等代价平坦(baseline)")
    W("")

    # ── §1 解析层:代价 / 覆盖率 / 总带宽(免费,先全跑) ──
    W("=" * 112)
    W("§1  解析层:代价(检测带中位|N|)· 覆盖率 · 总带宽预算        [Hn1/Hn4]")
    W("=" * 112)
    W(f"{'bw_oct':>8}{'总带宽(oct)':>12}{'T60':>6}{'sd':>4}"
      f"{'代价B_o(dB)':>13}{'覆盖率':>9}{'FLAT臂ΔMSG=|B_o|':>18}")
    ana = {}
    for bw in BWS:
        for (T60, sd) in SEEDS:
            h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
            hb = band_limit(h0, F_CUT)
            he = clrig.h_eff(hb)
            picks = pick_excl(he, bw, 8)
            B_o = cost_median_db(he, picks, bw, DEPTH)
            cov = coverage(picks, bw)
            ana[(bw, T60, sd)] = (hb, D, he, picks, B_o, cov)
            W(f"{bw:>8.4f}{8*bw:>12.2f}{T60:>6.1f}{sd:>4}{B_o:>13.2f}"
              f"{cov*100:>8.1f}%{abs(B_o):>18.2f}")
        cs = [ana[(bw, t, s)][4] for (t, s) in SEEDS]
        vs = [ana[(bw, t, s)][5] for (t, s) in SEEDS]
        W(f"  ── bw={bw:.4f}: 代价中位 {np.median(cs):+.2f} dB | "
          f"覆盖率 {np.mean(vs)*100:.1f}% | 总带宽 {8*bw:.2f} oct "
          f"(文献工程区间 0.8–1.2)")
    W("")

    # ── §2 闭环三臂 ──
    W("=" * 112)
    W("§2  闭环三臂(每格经 DMSGReport,缺臂即抛)      [Hn2/Hn3 + M-1]")
    W("=" * 112)
    for T_OBS in (12.0, 30.0):
        W(f"########## T_OBS = {T_OBS:.0f} s ##########")
        for bw in BWS:
            W(f"--- bw_oct = {bw:.4f}  (总带宽 {8*bw:.2f} oct)")
            for (T60, sd) in SEEDS:
                hb, D, he, picks, B_o, cov = ana[(bw, T60, sd)]
                mt = MSGMeter(he, FS)
                r0 = mt.msg(slots=(), g_duck_db=0.)
                anchor = r0['full']['msg_db']
                src = src_of(T_OBS, sd)
                ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
                m0, _, ft0 = scan(hb, D, lambda: None, anchor - 3, anchor + 3, src, ref)
                mo, _, fto = scan(hb, D, lambda: mk_oracle(picks, bw, DEPTH),
                                  anchor - 1, anchor + 16, src, ref)
                mn, stn, ftn = scan(hb, D, lambda: mk_nhs_self(bw),
                                    anchor - 1, anchor + 16, src, ref, want_state=True)
                d_o = mo - m0 if np.isfinite(mo) and np.isfinite(m0) else None
                d_n = mn - m0 if np.isfinite(mn) and np.isfinite(m0) else None
                d_f = DMSGReport.flat_dmsg_from_cost(B_o)
                note = ''
                if stn:
                    note = (f"NHS自选挂了 {stn['n_notch']} 个陷波 @{stn['fr'][:6]}, "
                            f"g_duck最深 {stn['gmin']:.2f} dB")
                    if stn['gmin'] < 0:
                        note += "  ⚠ duck 参与 ⇒ 该列非纯陷波"
                for f_ in (fto, ftn):
                    if np.isfinite(f_) and f_ < 120.:
                        note += f"  ⚠ f_trig={f_:.1f}Hz <120 ⇒ [未按 F36 收敛],不进结论"
                rep = DMSGReport(
                    workpoint=dict(选点来源='ORACLE解析|NHS自选', T_low='999|-45',
                                   f_cut=F_CUT, T_OBS=T_OBS, bw_oct=bw,
                                   depth=DEPTH, seed=sd, T60=T60, STEP=STEP),
                    oracle=d_o, nhs_self=d_n, flat=d_f, nhs_self_note=note)
                W(f"  {T60}/{sd} 代价{B_o:+6.2f} 覆盖{cov*100:4.1f}% | " + rep.format())
            W("")
    with open('/home/it1234/processor/01_design/prototype_W1P/'
              'r61_bwoct_baseline_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
