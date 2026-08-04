"""r83 · m0 偏高对 ΔMSG 的【低估量级】—— lead 顺手要的量级估计。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r83_m0bias_out.txt(D6-j)。

背景(r81):参照臂 m0 在其自身终点 G 上 **仍在长**(到峰/窗 0.78–1.00,末−首最高 +3.22 dB)
⇒ m0 被高估 ⇒ 而 ΔMSG = m_Na − m_m0 ⇒ **差值被低估**。
做法:从已报的 m0 逐 0.5 dB 往下退,找末秒−首秒 RMS **首次 ≤ 0** 的 G ⇒ 该 G = 更干净的 m0。
      两者之差 = m0 的偏高量 = ΔMSG 的低估量(量级估计,⛔ 非精确标定)。
⚠ 本件只用 m0 臂(无算法动作)⇒ 不涉及 r82 那把没过闸门的判据。
"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
T = 12.0
SRC = -20.
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def main():
    t0 = time.time()
    R = json.load(open(DIR + 'r81_windowcheck.json'))
    W("未经 critic 评审 —— r83 · m0 偏高 ⇒ ΔMSG 低估量级  [L2/宿主仿真]")
    W("背景 r81:m0 臂在其自身终点 G 上仍在长(到峰/窗 0.78–1.00,末−首最高 +3.22 dB)")
    W("做法:从已报 m0 逐 0.5 dB 下退,找末秒−首秒 RMS 首次 ≤0 的 G ⇒ 差值 = m0 偏高量")
    W("⚠ 量级估计,⛔ 非精确标定;只用 m0 臂,不涉及 r82 那把未过闸门的判据")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'已报m0':>9}{'m0处增长':>10}{'退到':>8}{'该处增长':>10}{'m0偏高':>8}")
    bias = []
    rows = []
    for r in [x for x in R if x['src'] == -20. and x['T'] == 12.]:
        T60, sd = r['T60'], r['sd']
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        s = np.random.default_rng(sd).standard_normal(int(T * FS)) * (10 ** (SRC / 20.))
        m0 = r['G'] - r['dA']
        k = int(FS)
        g0, found = None, None
        for step in range(0, 13):
            G = m0 - 0.5 * step
            _, lp = clrig.Loop(hb, D, G, proc=None).run(s, FRAME)
            gr = float(HD.rms_db(lp[-k:]) - HD.rms_db(lp[:k]))
            if step == 0:
                g0 = gr
            if gr <= 0:
                found = (G, gr)
                break
        if found:
            b = m0 - found[0]
            bias.append(b)
            W(f"{T60:>5.1f}{sd:>4}{m0:>9.2f}{g0:>+10.2f}{found[0]:>8.2f}{found[1]:>+10.2f}{b:>8.2f}")
            rows.append(dict(T60=T60, sd=sd, m0=m0, grow0=g0, m0_clean=found[0], bias=b))
        else:
            W(f"{T60:>5.1f}{sd:>4}{m0:>9.2f}{g0:>+10.2f}{'未找到':>8}{'-':>10}{'>6.0':>8}")
            rows.append(dict(T60=T60, sd=sd, m0=m0, grow0=g0, m0_clean=None, bias=None))
    W("")
    if bias:
        W(f"⇒ m0 偏高量 逐条 {[round(x,2) for x in bias]}")
        W(f"⇒ **中位 {np.median(bias):.2f} dB / 最大 {max(bias):.2f} dB**")
        W(f"⇒ ΔMSG = m_Na − m_m0 ⇒ **ΔMSG 被【低估】约 {np.median(bias):.2f} dB(中位)**")
        W(f"⇒ 与仪器底 0.354 dB 比:{'**可观,超过仪器底**' if np.median(bias) > 0.354 else '在仪器底之内,不可判'}")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r83_m0bias_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r83_m0bias.json', 'w') as fp:
        json.dump(rows, fp)


if __name__ == '__main__':
    main()
