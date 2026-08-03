"""r51 · 刀 3:**直接实测环路传函**,不依赖任何既有解析推导。

⛔⛔ B-1 限定横幅(2026-08-03,独立 critic verdict FAIL 后补;**引用本文件任何数字前必读**)
   本文件的陷波频点取自 `clrig.critical_points()` = **解析神谕**,不是 NHS 的检测输出;
   且槽被直接写成 `st=HOLD` 并设 `P.T_low = 999.` ⇒ `nhs.py:402` 的门在 999 / 979(=T_low_gr)
   两个取值下都不可能过(信号上限 0 dBFS)⇒ **新分配全程关闭**;
   `nhs.py:94` `lift_after_s=60 > T_OBS` ⇒ 预挂槽整轮不释放。
   ⇒ **被测对象 = 「8 个 RBJ 陷波器,由解析式放在最优点上」= NHS 的【上界】,不是 NHS 的性能。**
   ⇒ 本文件产出的 ΔMSG **不得称作「NHS 实测」,不得用于「达标/未达标」判定。**
   ⇒ NHS 自选下的数 = 未测(整改队列 1(b):自由槽位起振扫描,T_low 默认)。

做法 = 把 clrig.Loop.run 的递推结构原样复制,只把反馈连接断开,注入冲激:
    Loop.run:  inp = src[i] + fb ; y = proc(inp) ; fb = F(G·y)   ← fb 在【下一块】被消费
    本文件  :  inp = x[i]        ; y = proc(inp) ; fb = F(G·y)   ← fb 记到【下一块】位置
⇒ 采到的 L[n] 就是环路绕一圈回来的冲激响应(**含那 1 帧块延迟**,由记录位置体现,
   不是由 h_eff 假设进去的)。

⚠ 被测对象(D6-b):|L(ω)| = **环路一圈的复增益**。
   混淆面:测 proc 自己的传函也能看见陷波,但那证明不了陷波在环内 —— 本文件测的是环。

预注册:PREREG_r51.txt(H1/H2/H3 与证伪条件已先落盘)
输出   :r51_loopTF_out.txt   [L2/宿主仿真]
deps   : clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316,
         howl_detect.py@fd63e901f2d8be33
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz, lfilter
import clrig, nhs
from nhs import NHS
from clrig import FS

FRAME = 64
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
P = nhs.Params()
NFFT = 1 << 18          # 5.46 s @48k,长于任何 h(T60=0.5 ⇒ 48000 抽头)
F_LO, F_HI = 100.0, 8000.0
FULL_LO, FULL_HI = 20.0, 23900.0


# ---------------------------------------------------------------- 与 r50 同源的选点/陷波
def notch_H(f0, fg):
    A = 10 ** (P.max_depth / 40.)
    w0 = 2 * np.pi * f0 / FS
    al = np.sin(w0) * np.sinh(np.log(2) / 2 * P.bw_oct * w0 / np.sin(w0))
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    return freqz(b, a, worN=2 * np.pi * fg / FS)[1]


def pick_excl(he, k=8):
    """与 r50_excl_meas.pick_excl 逐字同构(排他区选法)。"""
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


def np_proc(picks):
    """与 r50_excl_meas.np_proc 逐字同构:8 个槽钉死在 HOLD/最深。"""
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


# ---------------------------------------------------------------- 刀 3 本体
def measure_loop_ir(h, G_db, alg, n=NFFT, frame=FRAME, amp=1e-3):
    """断开反馈的 Loop.run:注入冲激,采环路一圈回来的信号。
    ⚠ fb 记到【下一块】位置 —— 这一条就是 Loop.run 里那 1 帧块延迟的**实测体现**。"""
    G = 10 ** (G_db / 20.)
    x = np.zeros(n)
    x[0] = amp
    L = np.zeros(n)
    zi = np.zeros(len(h) - 1)
    for i in range(0, n - frame, frame):
        inp = x[i:i + frame]
        y = alg.process_frame(inp, GR) if alg is not None else inp
        fb, zi = lfilter(h, [1.0], G * y, zi=zi)
        L[i + frame:i + 2 * frame] = fb
    return L / amp                      # 归一为"每单位输入"的环路增益冲激响应


def crit_from(f, H, lo, hi):
    m = (f >= lo) & (f <= hi)
    return clrig._crit_from_H(f[m], H[m])


def report(tag, fh, out):
    out.append(tag)


def main():
    out = []
    W = out.append
    W("r51 · 刀 3:直接实测环路传函(NHS 关 vs 开)")
    W("deps: clrig.py@8ad47ce8d260dd18  nhs.py@706b658842d84316")
    W("被测对象 = 环路一圈复增益 L(w)=G*N*F*z^-frame,含块延迟;非 proc 传函。")
    W("全部 [L2/宿主仿真]。预注册 = PREREG_r51.txt")
    W("")

    # ═══ 第 0 部分:纯解析的带内 vs 全带临界点(H2 的零成本判读)═══
    W("=" * 78)
    W("§0  解析层:临界点最大值  带内(100-8000) vs 全带(20-23900)   [H2]")
    W("=" * 78)
    W(f"{'T60':>5}{'seed':>5}{'带内max':>10}{'全带max':>10}{'D_band':>9}"
      f"{'全带峰频Hz':>12}{'神谕ΔMSG':>10}{'r50实测':>9}")
    r50_pred = {(0.2, 0): 3.75, (0.2, 1): 6.03, (0.2, 2): 7.74,
                (0.5, 0): 4.67, (0.5, 1): 6.58, (0.5, 2): 4.49}
    r50_meas = {(0.2, 0): 4.00, (0.2, 1): 0.00, (0.2, 2): 1.50,
                (0.5, 0): 1.00, (0.5, 1): 0.50, (0.5, 2): 0.50}
    tbl = {}
    for T60 in (0.2, 0.5):
        for sd in (0, 1, 2):
            h, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
            he = clrig.h_eff(h)
            f, H = clrig.F_response(he, NFFT)
            fin, min_ = crit_from(f, H, F_LO, F_HI)
            ffu, mfu = crit_from(f, H, FULL_LO, FULL_HI)
            i_in, i_fu = int(np.argmax(min_)), int(np.argmax(mfu))
            d = float(mfu[i_fu] - min_[i_in])
            tbl[(T60, sd)] = (h, D, he, float(min_[i_in]), float(mfu[i_fu]),
                              float(ffu[i_fu]), float(fin[i_in]))
            W(f"{T60:>5.1f}{sd:>5}{min_[i_in]:>10.2f}{mfu[i_fu]:>10.2f}{d:>9.2f}"
              f"{ffu[i_fu]:>12.1f}{r50_pred[(T60,sd)]:>10.2f}{r50_meas[(T60,sd)]:>9.2f}")
    W("")
    W("判读锚:D_band = 全带最大 − 带内最大。H2 预测 D_band ≳ 神谕预测(失败种子)。")
    W("")

    # ═══ 第 1 部分:实测环路传函 ═══
    W("=" * 78)
    W("§1  实测:开环冲激 → |L(w)|   NHS 关 vs 开   [H1/H3]")
    W("=" * 78)
    for T60 in (0.2, 0.5):
        for sd in (0, 1, 2):
            h, D, he, in_max, fu_max, fu_f, in_f = tbl[(T60, sd)]
            G_db = -in_max                     # = 带内解析 MSG,r50 的工作点附近
            picks = pick_excl(he, 8)

            L_off = measure_loop_ir(h, G_db, None)
            alg = np_proc(picks)
            L_on = measure_loop_ir(h, G_db, alg)

            f = np.fft.rfftfreq(NFFT, 1 / FS)
            Hoff = np.fft.rfft(L_off, NFFT)
            Hon = np.fft.rfft(L_on, NFFT)

            # --- H3:实测 L_off 对解析 G*H_eff ---
            G = 10 ** (G_db / 20.)
            Hana = G * np.fft.rfft(he, NFFT)
            Nana = np.ones(len(f), dtype=complex)
            for p in picks:
                Nana = Nana * notch_H(p, f)
            band = (f >= 20) & (f <= 23900)
            e_off = 20 * np.log10(np.abs(Hoff[band]) + 1e-30) - \
                    20 * np.log10(np.abs(Hana[band]) + 1e-30)
            e_on = 20 * np.log10(np.abs(Hon[band]) + 1e-30) - \
                   20 * np.log10(np.abs(Hana[band] * Nana[band]) + 1e-30)

            # --- H1:8 个 picks 处的实测下降 ---
            drops = []
            for p in picks:
                k = int(round(p / (FS / NFFT)))
                drops.append(20 * np.log10(abs(Hon[k]) + 1e-30) -
                             20 * np.log10(abs(Hoff[k]) + 1e-30))
            drops = np.array(drops)

            # --- 实测环路的临界点:带内 / 全带,关 vs 开 ---
            # L 已含 G ⇒ 换算回 |F| 口径:MSG = -20log10(max|L|) + G_db
            def mx(Hx, lo, hi):
                fc, md = crit_from(f, Hx, lo, hi)
                if len(md) == 0:
                    return float('nan'), float('nan')
                j = int(np.argmax(md))
                return float(md[j]), float(fc[j])

            oi, oif = mx(Hoff, F_LO, F_HI)
            ni, nif = mx(Hon, F_LO, F_HI)
            of, off_ = mx(Hoff, FULL_LO, FULL_HI)
            nf, nff = mx(Hon, FULL_LO, FULL_HI)

            W(f"--- T60={T60} seed={sd}   G={G_db:.2f}dB(=带内解析 MSG)  "
              f"picks={['%.1f' % p for p in picks]}")
            W(f"    [H3] |L_off| vs 解析 G*H_eff : max|err| = {np.abs(e_off).max():.4f} dB "
              f"(中位 {np.median(np.abs(e_off)):.2e})")
            W(f"    [H3] |L_on|  vs 解析 G*H_eff*N: max|err| = {np.abs(e_on).max():.4f} dB "
              f"(中位 {np.median(np.abs(e_on)):.2e})")
            W(f"    [H1] 8 个 picks 处实测下降 dB: "
              f"{np.array2string(drops, precision=2, floatmode='fixed')}")
            W(f"    [H1] 下降中位 {np.median(drops):.2f} dB / 最浅 {drops.max():.2f} dB")
            W(f"    [H2] 实测环路临界点最大 (口径:20log10|L|, 已含 G={G_db:.2f}dB)")
            W(f"         带内 100-8k : 关 {oi:+7.2f} @{oif:8.1f}Hz  |  "
              f"开 {ni:+7.2f} @{nif:8.1f}Hz  |  Δ={oi-ni:+6.2f} dB")
            W(f"         全带 20-23.9k: 关 {of:+7.2f} @{off_:8.1f}Hz  |  "
              f"开 {nf:+7.2f} @{nff:8.1f}Hz  |  Δ={of-nf:+6.2f} dB")
            W(f"         ⇒ 实测 MSG 提升:带内口径 {oi-ni:+.2f} dB / 全带口径 {of-nf:+.2f} dB"
              f"   (r50 闭环实测 {r50_meas[(T60,sd)]:+.2f} dB)")
            W("")
            sys.stdout.flush()

    txt = "\n".join(out)
    print(txt)
    with open('/home/it1234/processor/01_design/prototype_W1P/r51_loopTF_out.txt',
              'w') as fp:
        fp.write(txt + "\n")


if __name__ == '__main__':
    main()
