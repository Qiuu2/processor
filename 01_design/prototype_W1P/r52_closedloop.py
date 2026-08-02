"""r52 · 复现 r50 扫描 + 起振时刻仪表化,判定 0.2/seed0 例外。

预注册:PREREG_r52.txt(H4/H5/H6/H7 与证伪条件跑前落盘)
输出   :r52_closedloop_out.txt   [L2/宿主仿真]
deps   : clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316,
         howl_detect.py@fd63e901f2d8be33

⚠ 扫描/选点/陷波三段**逐字复制自 r50_excl_meas.py**(366b9c821ff6c124),
  只增加仪表,不改行为 —— 否则复现不成立。
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS

FRAME = 64
STEP = 0.5
T_OBS = 6.0                       # ★ D6 工作点向量的一维,每个 m 必带
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
P = nhs.Params()
NFFT_A = 1 << 18
F_LO, F_HI = 100.0, 8000.0
FULL_LO, FULL_HI = 20.0, 23900.0
OUT = []


def W(s):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


# ---------- 与 r50 逐字同构 ----------
def notch_H(f0, fg):
    A = 10 ** (P.max_depth / 40.)
    w0 = 2 * np.pi * f0 / FS
    al = np.sin(w0) * np.sinh(np.log(2) / 2 * P.bw_oct * w0 / np.sin(w0))
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    return freqz(b, a, worN=2 * np.pi * fg / FS)[1]


def pick_excl(he, k=8):
    fc, mdb = clrig.critical_points(he)
    o = list(np.argsort(mdb)[::-1])
    picks, used = [], np.zeros(len(fc), bool)
    for i in o:
        if used[i] or len(picks) >= k:
            continue
        f_ = float(fc[i])
        picks.append(f_)
        used |= (np.abs(fc - f_) <= max(f_ * P.bw_oct, 15.))
    return picks


def src_of(T, s):
    return 1e-3 * np.random.default_rng(s).standard_normal(int(T * FS))


def ref_db(T, s):
    x = src_of(T, s)
    return HD.rms_db(x[:(len(x) // FRAME) * FRAME])


def np_proc(picks):
    def f():
        a = NHS()
        for i, f_ in enumerate(picks[:len(a.slots)]):
            s = a.slots[i]
            s.st = nhs.NotchSlot.HOLD
            s.f = f_
            s.depth = a.P.max_depth
            s.target = a.P.max_depth
            s.set_coef(FS, a.P.bw_oct)
        a.P.T_low = 999.
        return lambda blk: a.process_frame(blk, GR)
    return f


# ---------- 仪表 ----------
def dominant_f(loop_sig, sec=1.0):
    """末 sec 秒的谱主峰(Hann 窗)。**被测对象 = 环路信号的主导频率**,不是 NHS 的判据。"""
    n = int(sec * FS)
    x = loop_sig[-n:]
    Xf = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / FS)
    k = int(np.argmax(Xf))
    return float(f[k])


def run_one(h, D, G, pf, T, s):
    _, lp = clrig.Loop(h, D, G, proc=pf()).run(src_of(T, s), FRAME)
    hw, lvmax, lvend = HD.is_howling(lp, ref_db(T, s), FS, FRAME)
    return hw, lvmax, lvend, lp


def scan(h, D, pf, T, s, lo, hi, tag, picks=None):
    """r50.msg() 同构 + 逐步留痕。返回 (m, trace, first_howl_info)。"""
    G = lo
    last = None
    trace = []
    info = None
    while G <= hi + 1e-9:
        hw, lvmax, lvend, lp = run_one(h, D, G, pf, T, s)
        trace.append((G, hw, lvmax, lvend))
        if hw:
            ft = dominant_f(lp)
            inb = 'IN ' if F_LO <= ft <= F_HI else 'OUT'
            innotch = 'n/a'
            if picks:
                hit = [p for p in picks if abs(ft - p) <= max(p * P.bw_oct, 15.) / 2]
                innotch = ('落陷波内 %.1f' % hit[0]) if hit else '不在任何陷波内'
            info = (G, ft, inb, innotch, lvmax)
            if last is None:
                return float('nan'), trace, info      # 下界命中
            return last, trace, info
        last = G
        G += STEP
    return float('nan'), trace, info                  # 上界命中


def ana_pair(he):
    """(带内解析 MSG, 全带解析 MSG, 带内峰频, 全带峰频) —— MSG 取正号 = 可用增益 dB。"""
    f, H = clrig.F_response(he, NFFT_A)
    def mx(lo, hi):
        m = (f >= lo) & (f <= hi)
        fc, md = clrig._crit_from_H(f[m], H[m])
        j = int(np.argmax(md))
        return float(md[j]), float(fc[j])
    a_in, f_in = mx(F_LO, F_HI)
    a_fu, f_fu = mx(FULL_LO, FULL_HI)
    return -a_in, -a_fu, f_in, f_fu


def main():
    W("r52 · 闭环扫描复现 + 起振仪表化      T_OBS=6.0s / STEP=0.5dB / FRAME=64")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 "
      "howl_detect.py@fd63e901f2d8be33")
    W("[L2/宿主仿真]  预注册 = PREREG_r52.txt")
    W("被测对象(D6-b):m0/mk = **6s 内能长到超 6dB 门的最低 G**,不是解析 MSG;")
    W("                超出量小时会系统性【高读】(晚触发),这是本轮判读的关键混淆面。")
    W("")
    W("=" * 100)
    W(f"{'T60':>5}{'sd':>4}{'MSG_in':>9}{'MSG_full':>10}{'m0实测':>9}{'mk实测':>9}"
      f"{'ΔMSG':>7}{'m0−MSGfull':>12}{'m0−MSGin':>10}")
    W("=" * 100)
    rows = []
    for T60 in (0.2, 0.5):
        for sd in (0, 1, 2):
            h, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
            he = clrig.h_eff(h)
            msg_in, msg_fu, f_in, f_fu = ana_pair(he)
            ana = msg_in                       # r50 用的就是带内值做扫描锚点
            picks = pick_excl(he, 8)
            pred_in = None
            # 带内神谕(与 r50 的 oracle 同构)
            f0, H0 = clrig.F_response(he, NFFT_A)
            m = (f0 >= F_LO) & (f0 <= F_HI)
            fm, Hm = f0[m], H0[m]
            Nt = np.ones(len(fm), dtype=complex)
            for p in picks:
                Nt = Nt * notch_H(p, fm)
            _, a_ = clrig._crit_from_H(fm, Hm)
            _, b_ = clrig._crit_from_H(fm, Hm * Nt)
            pred_in = float(a_.max() - b_.max())

            m0, tr0, i0 = scan(h, D, lambda: None, T_OBS, sd,
                               ana - 6, ana + 6, f'{T60}/{sd}/base')
            mk, trk, ik = scan(h, D, np_proc(picks), T_OBS, sd,
                               ana - 6, ana + pred_in + 6, f'{T60}/{sd}/excl',
                               picks=picks)
            d = mk - m0 if np.isfinite(mk) and np.isfinite(m0) else float('nan')
            rows.append((T60, sd, msg_in, msg_fu, m0, mk, d, i0, ik, f_in, f_fu,
                         pred_in, picks, tr0, trk))
            W(f"{T60:>5.1f}{sd:>4}{msg_in:>9.2f}{msg_fu:>10.2f}{m0:>9.2f}{mk:>9.2f}"
              f"{d:>7.2f}{m0-msg_fu:>12.2f}{m0-msg_in:>10.2f}")

    W("")
    W("=" * 100)
    W("§2  起振时刻仪表(首次判起振的那一步)      [H5/H6]")
    W("=" * 100)
    for (T60, sd, msg_in, msg_fu, m0, mk, d, i0, ik, f_in, f_fu, pred_in,
         picks, tr0, trk) in rows:
        W(f"--- T60={T60} seed={sd}  带内峰 {f_in:.1f}Hz / 全带峰 {f_fu:.1f}Hz  "
          f"带内神谕ΔMSG={pred_in:.2f}")
        for nm, i in (('基线', i0), ('挂8陷', ik)):
            if i is None:
                W(f"    {nm}: 未触发(窗内无起振)")
                continue
            G, ft, inb, innotch, lvmax = i
            W(f"    {nm}: 首起振 G={G:+.2f}dB  主导频率 {ft:8.1f}Hz [{inb}]  "
              f"帧RMS峰 {lvmax:+.1f}dB  {innotch}")
            W(f"          |f_trig − 全带峰| = {abs(ft-f_fu):8.1f} Hz   "
              f"|f_trig − 带内峰| = {abs(ft-f_in):8.1f} Hz")
        W("")

    W("=" * 100)
    W("§3  逐步扫描留痕(G, 起振?, 帧RMS峰dB, 末帧dB) —— 让【晚触发】可见")
    W("=" * 100)
    for (T60, sd, msg_in, msg_fu, m0, mk, d, i0, ik, f_in, f_fu, pred_in,
         picks, tr0, trk) in rows:
        W(f"--- T60={T60} seed={sd}   MSG_in={msg_in:.2f}  MSG_full={msg_fu:.2f}")
        for nm, tr in (('基线', tr0), ('挂8陷', trk)):
            W(f"    {nm}: " + "  ".join(
                f"[{g:+.1f}{'H' if hw else '.'}{mx:+.0f}]" for g, hw, mx, le in tr))
        W("")

    with open('/home/it1234/processor/01_design/prototype_W1P/r52_closedloop_out.txt',
              'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
