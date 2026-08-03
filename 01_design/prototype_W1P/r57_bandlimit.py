"""r57 · 带限扫描 = **P-1 的敏感性曲线**(lead 裁定 (c);(a) 加滚降已被禁止)。

⛔⛔ B-1 限定横幅(2026-08-03,独立 critic verdict FAIL 后补;**引用本文件任何数字前必读**)
   本文件的陷波频点取自 `clrig.critical_points()` = **解析神谕**,不是 NHS 的检测输出;
   且槽被直接写成 `st=HOLD` 并设 `P.T_low = 999.` ⇒ `nhs.py:402` 的**首次获取**门 = 999 dBFS
   ⇒ 信号上限 0 dBFS ⇒ **新分配全程关闭**。
   ⚠ **勘正(2026-08-03,critic 抓获;本横幅前一版写"979"是错的)**:
     `T_low_gr` 在 `Params.__init__`(`nhs.py:73`)就按 `T_low−20` **算死为 −65.0**,
     `mk_alg` 在 `NHS()` **构造之后**才改 `P.T_low`,**不会重算 `T_low_gr`**
     ⇒ **`nhs.py:399-401` 的放宽路径(已覆盖 bin 的【维持】)仍然是通的,门只有 −65 dBFS。**
     ⇒ **被关掉的只有「首次获取」,不是「全部」。** 数值影响 = 0(预挂槽已在 max_depth,
       维持路径改不了任何东西),但**描述必须准确** —— 这段文字的用途正是防止别人误读。
   `nhs.py:94` `lift_after_s=60 > T_OBS` ⇒ 预挂槽整轮不释放。
   ⇒ **被测对象 = 「8 个 RBJ 陷波器,由解析式放在最优点上」= NHS 的【上界】,不是 NHS 的性能。**
   ⇒ 本文件产出的 ΔMSG **不得称作「NHS 实测」,不得用于「达标/未达标」判定。**
   ⇒ NHS 自选下的数 = 未测(整改队列 1(b):自由槽位起振扫描,T_low 默认)。

⛔ 本文件**不是**"让台架更真实" —— 那是被禁的 (a)。
   台架 F(z) 平到 24 kHz 与产品"旁链抽取前缺带限"是**同一物理缺陷的两面**;
   给台架加滚降会把 P-1 这个真实缺陷一起藏起来。
⇒ 本文件回答的是:**产品需要多少前置带限,P-1 才不发生。**

预注册:PREREG_r57_r58.txt(BL-1 前置自检 / Hg / Hh / Hi 与证伪条件跑前落盘)
输出   :r57_bandlimit_out.txt   [L2/宿主仿真]
deps   : clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316,
         howl_detect.py@fd63e901f2d8be33, msg_meter.py
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import firwin
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter, BAND_DET, BAND_FULL

FRAME = 64
STEP = 0.5
T_OBS = 6.0
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
P = nhs.Params()
NTAP = 511
F_CUTS = [8000., 10000., 12000., 16000., 24000.]
OUT = []


def W(s):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def band_limit(h, f_cut, fs=FS, ntap=NTAP):
    """线性相位 FIR 低通 + 零相位对齐 + 按 make_F 同法归一。
    ⚠ 左移 (ntap−1)/2 = 255 < D = 384 ⇒ 仍因果,环路延迟不变
      (否则 f_cut 会与延迟混淆,而延迟直接改变临界点密度)。"""
    if f_cut >= fs / 2:
        return np.asarray(h, float).copy()
    lp = firwin(ntap, f_cut / (fs / 2))
    y = np.convolve(np.asarray(h, float), lp)
    k = (ntap - 1) // 2
    y = y[k:k + len(h)]
    return y / (np.sqrt(np.sum(y ** 2)) + 1e-30)


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


def mk_alg(picks, no_duck):
    """⛔ B-1:本函数**关闭 NHS 的检测/选点/分配**,只留滤波与 duck。
    `T_low = 999.` 使 `nhs.py:402` 的门恒不可过(放宽路径 `T_low_gr = 979` 同样不可过)。
    ⇒ 返回的实例**不代表 NHS**,只代表"被放在指定频点上的 8 个 RBJ 陷波器"。
    ⇒ **r59 / r60 直接 import 本函数,同受此限定。**
    ⇒ 要测 NHS 本身:用 `NHS()` 默认参数(`T_low=-45`)、槽全空,见 `r58_freeslot.py`。"""
    a = NHS()
    for i, f_ in enumerate(picks[:len(a.slots)]):
        s = a.slots[i]
        s.st = nhs.NotchSlot.HOLD
        s.f = f_
        s.depth = a.P.max_depth
        s.target = a.P.max_depth
        s.set_coef(FS, a.P.bw_oct)
    a.P.T_low = 999.
    if no_duck:
        a.duck_gain = lambda: 1.0
    return a


def src_of(T, s):
    return 1e-3 * np.random.default_rng(s).standard_normal(int(T * FS))


def scan(h, D, mk, lo, hi, src, ref):
    G, last = lo, None
    while G <= hi + 1e-9:
        alg = mk()
        pf = None if alg is None else (lambda blk, _a=alg: _a.process_frame(blk, GR))
        _, lp = clrig.Loop(h, D, G, proc=pf).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            return float('nan') if last is None else last
        last = G
        G += STEP
    return float('nan')


def main():
    W("r57 · 带限扫描 = P-1 敏感性曲线   (lead 裁定 (c);(a) 加滚降禁止)")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 "
      "howl_detect.py@fd63e901f2d8be33 msg_meter.py")
    W("[L2/宿主仿真]  预注册 = PREREG_r57_r58.txt")
    W(f"带限器 = firwin({NTAP}, f_cut) 线性相位,零相位对齐(左移 {(NTAP-1)//2} < D=384 ⇒ 因果)")
    W("⚠ 本表任何数字**不得**直接写成产品带限指标:它是本台架构造下的敏感性,")
    W("   真实要求取决于真实电声链响应,我们没有 [L1/L2] 数据。")
    W("")

    # ---------- BL-1 前置自检 ----------
    W("=" * 104)
    W("§0  BL-1 前置自检:带限真的发生了吗?(不过则本轮作废)")
    W("=" * 104)
    W(f"{'T60':>5}{'sd':>4}{'f_cut':>8}{'带内max|F|dB':>14}"
      f"{'>f_cut+500 的max|F|dB':>22}{'压制量dB':>10}{'判':>6}")
    bl_ok = True
    HS = {}
    for T60 in (0.2, 0.5):
        for sd in (0, 1, 2):
            h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
            for fc_ in F_CUTS:
                hb = band_limit(h0, fc_)
                HS[(T60, sd, fc_)] = (hb, D)
                f, H = clrig.F_response(clrig.h_eff(hb), 1 << 18)
                a = 20 * np.log10(np.abs(H[(f >= 100) & (f <= 8000)]).max() + 1e-30)
                m2 = (f >= fc_ + 500) & (f <= 23900)
                if not m2.any():
                    W(f"{T60:>5.1f}{sd:>4}{fc_:>8.0f}{a:>14.2f}"
                      f"{'n/a(=Nyquist)':>22}{'n/a':>10}{'—':>6}")
                    continue
                b = 20 * np.log10(np.abs(H[m2]).max() + 1e-30)
                ok = (a - b) >= 40.0
                bl_ok = bl_ok and ok
                W(f"{T60:>5.1f}{sd:>4}{fc_:>8.0f}{a:>14.2f}{b:>22.2f}"
                  f"{a-b:>10.2f}{('OK' if ok else 'FAIL'):>6}")
    W(f"⇒ BL-1 {'PASS(全部 ≥40dB)' if bl_ok else '⛔ FAIL —— 本轮作废'}")
    W("")

    # ---------- 主扫描 ----------
    W("=" * 104)
    W("§1  逐 f_cut:ΔMSG 带内 / 全带 / 全带峰频        [Hg/Hh]")
    W("=" * 104)
    W(f"{'f_cut':>8}{'T60':>5}{'sd':>4}{'MSG带内':>9}{'MSG全带':>9}"
      f"{'D_band':>8}{'ΔMSG带内':>10}{'ΔMSG全带':>10}{'|差|':>7}"
      f"{'全带峰频Hz':>12}{'峰>8k?':>8}")
    tab = {}
    for fc_ in F_CUTS:
        n_out = 0
        for T60 in (0.2, 0.5):
            for sd in (0, 1, 2):
                hb, D = HS[(T60, sd, fc_)]
                he = clrig.h_eff(hb)
                mt = MSGMeter(he, FS)
                r0 = mt.msg(slots=(), g_duck_db=0.0)
                picks = pick_excl(he, 8)
                alg = mk_alg(picks, False)
                r1 = mt.msg(slots=alg.slots, g_duck_db=0.0)
                din = r1['in']['msg_db'] - r0['in']['msg_db']
                dfu = r1['full']['msg_db'] - r0['full']['msg_db']
                dband = r0['in']['msg_db'] - r0['full']['msg_db']
                fpk = r0['full']['f_crit']
                gt = fpk > 8000.
                n_out += int(gt)
                tab[(fc_, T60, sd)] = (r0, r1, din, dfu, dband, fpk, picks, hb, D)
                W(f"{fc_:>8.0f}{T60:>5.1f}{sd:>4}{r0['in']['msg_db']:>9.2f}"
                  f"{r0['full']['msg_db']:>9.2f}{dband:>8.2f}{din:>10.2f}"
                  f"{dfu:>10.2f}{abs(din-dfu):>7.2f}{fpk:>12.1f}"
                  f"{('YES' if gt else 'no'):>8}")
        W(f"  ── f_cut={fc_:.0f}: 全带峰频 >8kHz 的条数 = {n_out}/6 ; "
          f"|ΔMSG差| 最大 = "
          f"{max(abs(tab[(fc_,t,s)][2]-tab[(fc_,t,s)][3]) for t in (0.2,0.5) for s in (0,1,2)):.2f} dB")
    W("")
    w8 = [abs(tab[(8000., t, s)][2] - tab[(8000., t, s)][3])
          for t in (0.2, 0.5) for s in (0, 1, 2)]
    W(f"⇒ Hg(f_cut=8k):|ΔMSG_全带 − ΔMSG_带内| = "
      f"{[round(x,2) for x in w8]}  最大 {max(w8):.2f} dB")
    W(f"   {'⇒ Hg 立:带外主导是本次全部异常的唯一原因' if max(w8) <= 0.5 else '⇒ ⛔ Hg 未全中 ⇒ 还有第二个机制,须单独查'}")
    n8 = sum(int(tab[(8000., t, s)][5] > 8000.) for t in (0.2, 0.5) for s in (0, 1, 2))
    W(f"⇒ Hh(f_cut=8k):全带峰频 >8kHz 条数 = {n8}/6  "
      f"{'⇒ Hh 立' if n8 == 0 else '⇒ ⛔ Hh 死'}")
    W("")

    # ---------- 闭环确认 ----------
    W("=" * 104)
    W("§2  闭环确认 @ f_cut=8k,六条种子(duck 已消融 = 锁定被测机制)   [Hi]")
    W("=" * 104)
    W(f"{'T60':>5}{'sd':>4}{'m0基线':>9}{'mk无duck':>10}{'闭环ΔMSG':>10}"
      f"{'ΔMSG全带(表)':>14}{'|差|':>7}{'mk带duck':>10}{'duck贡献':>10}")
    hi_ok = True
    for T60 in (0.2, 0.5):
        for sd in (0, 1, 2):
            r0, r1, din, dfu, dband, fpk, picks, hb, D = tab[(8000., T60, sd)]
            src = src_of(T_OBS, sd)
            ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
            anchor = r0['in']['msg_db']
            m0 = scan(hb, D, lambda: None, anchor - 6, anchor + 6, src, ref)
            mk2 = scan(hb, D, lambda: mk_alg(picks, True),
                       anchor - 6, anchor + 14, src, ref)
            mk1 = scan(hb, D, lambda: mk_alg(picks, False),
                       anchor - 6, anchor + 14, src, ref)
            d = mk2 - m0
            ok = abs(d - dfu) <= 0.5
            hi_ok = hi_ok and ok
            W(f"{T60:>5.1f}{sd:>4}{m0:>9.2f}{mk2:>10.2f}{d:>10.2f}"
              f"{dfu:>14.2f}{abs(d-dfu):>7.2f}{mk1:>10.2f}{mk1-mk2:>10.2f}")
    W(f"⇒ Hi:{'立(六条全部 |闭环−表| ≤0.5dB)' if hi_ok else '⛔ 未全中,逐条看'}")

    with open('/home/it1234/processor/01_design/prototype_W1P/r57_bandlimit_out.txt',
              'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
