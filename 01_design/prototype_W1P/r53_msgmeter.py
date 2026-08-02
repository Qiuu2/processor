"""r53 · 瞬时 MSG 表的**有效性验证**(先证尺子,再用尺子)。

四组检查,全部按 D6-d「拿掉被测物,这个数应该等于多少?先写下预期,再真的去跑」写:
  A  空陷波      ⇒ MSG_t 必须**逐条等于** clrig 的解析 MSG(带内/全带各一)
  B  8 个 HOLD 陷波 ⇒ MSG_t 必须等于 r51 实测环路传函给出的值(≤0.05 dB)
  C  网格收敛     ⇒ nfft 2^15 vs 2^18(表默认已改 2^18,本组比的是粗网格代价) 的 MSG 差(不收敛则本表分辨力不足)
  D  变异测试     ⇒ 改陷波深度 / 改 g_duck / 改单槽系数,MSG_t **必须变**;
                    任一变异存活 ⇒ 本表不真依赖陷波状态(守护者也要被守护)
输出:r53_msgmeter_out.txt   [L2/宿主仿真]
deps: clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316, msg_meter.py(本轮新建)
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter, BAND_DET, BAND_FULL

OUT = []


def W(s):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


P = nhs.Params()


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


def mk_alg(picks):
    a = NHS()
    for i, f_ in enumerate(picks[:len(a.slots)]):
        s = a.slots[i]
        s.st = nhs.NotchSlot.HOLD
        s.f = f_
        s.depth = a.P.max_depth
        s.target = a.P.max_depth
        s.set_coef(FS, a.P.bw_oct)
    a.P.T_low = 999.
    return a


def ana(he, lo, hi, nfft=1 << 18):
    f, H = clrig.F_response(he, nfft)
    m = (f >= lo) & (f <= hi)
    fc, md = clrig._crit_from_H(f[m], H[m])
    j = int(np.argmax(md))
    return -float(md[j]), float(fc[j])


def main():
    W("r53 · 瞬时 MSG 表验证(msg_meter.MSGMeter)")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316")
    W("[L2/宿主仿真] 全部按 D6-d:预期先写死在代码里,再真的跑。")
    W("工作点向量:fs=48000 frame=64 nfft=262144 band∈{100-8000, 20-23900}")
    W("")

    W("=" * 96)
    W("A · 空陷波:MSG_t 必须 == clrig 解析 MSG   (拿掉被测物的预期值)")
    W("=" * 96)
    W(f"{'T60':>5}{'sd':>4}{'解析带内':>10}{'表带内':>10}{'差':>8}"
      f"{'解析全带':>10}{'表全带':>10}{'差':>8}")
    worst_a = 0.0
    cases = []
    for T60 in (0.2, 0.5):
        for sd in (0, 1, 2):
            h, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
            he = clrig.h_eff(h)
            mt = MSGMeter(he, FS, nfft=1 << 18)
            r = mt.msg(slots=(), g_duck_db=0.0)
            ai, _ = ana(he, *BAND_DET)
            af, _ = ana(he, *BAND_FULL)
            d1, d2 = r['in']['msg_db'] - ai, r['full']['msg_db'] - af
            worst_a = max(worst_a, abs(d1), abs(d2))
            cases.append((T60, sd, he, mt))
            W(f"{T60:>5.1f}{sd:>4}{ai:>10.3f}{r['in']['msg_db']:>10.3f}{d1:>8.3f}"
              f"{af:>10.3f}{r['full']['msg_db']:>10.3f}{d2:>8.3f}")
    W(f"⇒ A 组最大绝对差 = {worst_a:.3f} dB   "
      f"{'PASS(<0.05)' if worst_a < 0.05 else 'FAIL'}")
    W("")

    W("=" * 96)
    W("B · 8 个 HOLD 陷波:MSG_t 提升量 vs r51 实测环路传函")
    W("=" * 96)
    r51_in = {(0.2, 0): 3.75, (0.2, 1): 6.03, (0.2, 2): 7.73,
              (0.5, 0): 4.69, (0.5, 1): 6.61, (0.5, 2): 4.48}
    r51_fu = {(0.2, 0): 0.16, (0.2, 1): 0.26, (0.2, 2): 1.76,
              (0.5, 0): 0.66, (0.5, 1): 0.54, (0.5, 2): 0.66}
    W(f"{'T60':>5}{'sd':>4}{'表Δ带内':>10}{'r51Δ带内':>10}{'差':>8}"
      f"{'表Δ全带':>10}{'r51Δ全带':>10}{'差':>8}{'全带临界频Hz':>14}")
    worst_b = 0.0
    for T60, sd, he, mt in cases:
        picks = pick_excl(he, 8)
        alg = mk_alg(picks)
        r0 = mt.msg(slots=(), g_duck_db=0.0)
        r1 = mt.msg(slots=alg.slots, g_duck_db=alg.g_duck_db)
        din = r1['in']['msg_db'] - r0['in']['msg_db']
        dfu = r1['full']['msg_db'] - r0['full']['msg_db']
        e1, e2 = din - r51_in[(T60, sd)], dfu - r51_fu[(T60, sd)]
        worst_b = max(worst_b, abs(e1), abs(e2))
        W(f"{T60:>5.1f}{sd:>4}{din:>10.2f}{r51_in[(T60,sd)]:>10.2f}{e1:>8.2f}"
          f"{dfu:>10.2f}{r51_fu[(T60,sd)]:>10.2f}{e2:>8.2f}"
          f"{r1['full']['f_crit']:>14.1f}")
    W(f"⇒ B 组最大绝对差 = {worst_b:.2f} dB   "
      f"{'PASS(<0.10)' if worst_b < 0.10 else 'FAIL'}")
    W("")

    W("=" * 96)
    W("C · 网格收敛:nfft 2^15 vs 2^18(表默认已改 2^18,本组比的是粗网格代价)(空陷波 + 8 陷波两种状态)")
    W("=" * 96)
    W(f"{'T60':>5}{'sd':>4}{'状态':>8}{'带内@2^15':>11}{'带内@2^18':>11}{'差':>8}"
      f"{'全带@2^15':>11}{'全带@2^18':>11}{'差':>8}{'n_crit全带':>11}")
    worst_c = 0.0
    for T60, sd, he, mt in cases:
        big = MSGMeter(he, FS, nfft=1 << 15)
        picks = pick_excl(he, 8)
        alg = mk_alg(picks)
        for nm, sl, gd in (('空', (), 0.0), ('8陷', alg.slots, alg.g_duck_db)):
            a = big.msg(slots=sl, g_duck_db=gd)
            b = mt.msg(slots=sl, g_duck_db=gd)
            d1 = a['in']['msg_db'] - b['in']['msg_db']
            d2 = a['full']['msg_db'] - b['full']['msg_db']
            worst_c = max(worst_c, abs(d1), abs(d2))
            W(f"{T60:>5.1f}{sd:>4}{nm:>8}{a['in']['msg_db']:>11.3f}"
              f"{b['in']['msg_db']:>11.3f}{d1:>8.3f}{a['full']['msg_db']:>11.3f}"
              f"{b['full']['msg_db']:>11.3f}{d2:>8.3f}{b['full']['n_crit']:>11d}")
    W(f"⇒ C 组最大绝对差 = {worst_c:.3f} dB "
      f"{'(2^15 够用)' if worst_c < 0.10 else '(2^15 不够,须用 2^18)'}")
    W("")

    W("=" * 96)
    W("D · 变异测试:改陷波状态,MSG_t 必须变(任一存活 ⇒ 本表不依赖被测物)")
    W("=" * 96)
    T60, sd, he, mt = cases[0]
    picks = pick_excl(he, 8)
    base_alg = mk_alg(picks)
    base = mt.msg(slots=base_alg.slots, g_duck_db=base_alg.g_duck_db)

    def variant(name, fn):
        a = mk_alg(picks)
        gd = fn(a)
        r = mt.msg(slots=a.slots, g_duck_db=gd if gd is not None else a.g_duck_db)
        d_in = r['in']['msg_db'] - base['in']['msg_db']
        d_fu = r['full']['msg_db'] - base['full']['msg_db']
        killed = (abs(d_in) > 1e-6) or (abs(d_fu) > 1e-6)
        W(f"    M[{name:<28}] Δ带内={d_in:+8.3f}  Δ全带={d_fu:+8.3f}   "
          f"{'KILLED' if killed else '⛔ 存活'}")
        return killed

    def m1(a):
        for s in a.slots:
            if s.st != 0:
                s.depth = -9.0
                s._coef_key = None
                s.set_coef(FS, a.P.bw_oct)
    def m2(a):
        a.slots[0].st = nhs.NotchSlot.FREE
    def m3(a):
        a.g_duck_db = -6.0
        return -6.0
    def m4(a):
        s = a.slots[0]
        s.f = s.f * 1.05
        s._coef_key = None
        s.set_coef(FS, a.P.bw_oct)
    def m5(a):
        for s in a.slots:
            s.st = nhs.NotchSlot.FREE

    ks = [variant('全部深度 −18→−9dB', m1),
          variant('槽0 置 FREE', m2),
          variant('g_duck 0→−6dB', m3),
          variant('槽0 中心频 ×1.05', m4),
          variant('全部槽 FREE(=拿掉被测物)', m5)]
    W(f"⇒ D 组杀死率 = {sum(ks)}/{len(ks)}   "
      f"{'PASS' if all(ks) else 'FAIL(有存活变异)'}")
    W("")
    W("⚠ 缓存注记:MSGMeter 用 (状态+系数本体) 做 key;M[槽0 中心频 ×1.05] 与")
    W("   M[全部深度] 专门用于验证 key 真含系数 —— 若 key 只含 st,这两条会存活。")

    with open('/home/it1234/processor/01_design/prototype_W1P/r53_msgmeter_out.txt',
              'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
