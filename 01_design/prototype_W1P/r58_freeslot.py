"""r58 · 空槽下的带外啸叫行为 —— 回答 CTO 问②「带外啸叫时系统做什么」。

r54 只测了**槽被台架钉死**的工况(⇒ 只剩宽带兜底一条路)。
CTO 要的是**产品实际工况**:槽是空的、NHS 可以自由分配。

预注册(PREREG_r57_r58.txt,三种互斥结果 + 反例守卫):
  Hf-A 错误动作:陷波被分配到 1468±30 Hz(= 14531.9 Hz 的混叠像),环路仍起振
  Hf-B 无动作  :0 个陷波、g_duck 恒 0
  Hf-C 兜底生效:无陷波但 g_duck 挂上
  反例守卫:分配频率与 1468 Hz 无关 ⇒ P-1 的混叠像机理在空槽工况下不成立,须改写 P-1 范围

已知参数(读自 nhs.py,非推断):候选提取带 = 120.0 .. 7800.0 Hz(:69 定义 / :357 使用);
旁链 16 kHz ⇒ >8 kHz 结构上不可见。
输出:r58_freeslot_out.txt  [L2/宿主仿真]
deps: clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316,
      howl_detect.py@fd63e901f2d8be33, msg_meter.py
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter

FRAME = 64
T_OBS = 12.0                # ⚠ 比 r52 的 6s 长一倍:要给 NHS 分配+整定的时间
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
OUT = []
ST = {0: 'FREE', 1: 'ENGAGE', 2: 'HOLD', 3: 'LIFT', 4: 'STANDBY'}


def W(s):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def main():
    T60, sd = 0.2, 0
    h, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
    he = clrig.h_eff(h)
    meter = MSGMeter(he, FS)
    r0 = meter.msg(slots=(), g_duck_db=0.0)
    msg_in, msg_fu = r0['in']['msg_db'], r0['full']['msg_db']
    f_fu = r0['full']['f_crit']
    alias = abs(16000. - f_fu)
    src = 1e-3 * np.random.default_rng(sd).standard_normal(int(T_OBS * FS))
    ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])

    W("r58 · 空槽下的带外啸叫行为(CTO 问②)")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 "
      "howl_detect.py@fd63e901f2d8be33 msg_meter.py")
    W(f"[L2/宿主仿真]  T60={T60} seed={sd}  T_OBS={T_OBS}s FRAME=64  预注册=PREREG_r57_r58.txt")
    W("NHS 正常运行:**不预挂任何陷波,T_low 用默认 −45dBFS,8 槽全空可自由分配**")
    W("")
    W(f"MSG_带内(100-8000) = {msg_in:+.2f} dB @ {r0['in']['f_crit']:.1f} Hz")
    W(f"MSG_全带(20-23900) = {msg_fu:+.2f} dB @ {f_fu:.1f} Hz  ← 真正的起振点,**带外**")
    W(f"候选提取带(nhs.py:69) = 120.0 .. 7800.0 Hz;旁链 16 kHz ⇒ >8 kHz 不可见")
    W(f"混叠像预测:|16000 − {f_fu:.1f}| = **{alias:.1f} Hz**")
    W("")
    W("=" * 112)
    W(f"{'G(dB)':>8}{'margin全带':>11}{'起振?':>7}{'帧RMS峰':>10}{'主导频率':>10}"
      f"{'分配陷波数':>11}{'g_duck最深':>11}{'陷波中心频(Hz)':>34}")
    W("=" * 112)
    rows = []
    for G in (msg_fu - 2.0, msg_fu - 0.5, msg_fu + 0.5, msg_fu + 2.0, msg_fu + 4.0):
        alg = NHS()
        gd = []

        def pf(blk, _a=alg, _g=gd):
            y = _a.process_frame(blk, GR)
            _g.append(_a.g_duck_db)
            return y

        _, lp = clrig.Loop(h, D, G, proc=pf).run(src, FRAME)
        hw, lvmax, _ = HD.is_howling(lp, ref, FS, FRAME)
        n = int(1.0 * FS)
        Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
        ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
        used = [s for s in alg.slots if s.st != nhs.NotchSlot.FREE]
        fr = sorted(float(s.f) for s in used)
        gdm = float(np.min(gd)) if gd else 0.0
        rows.append((G, hw, lvmax, ft, fr, gdm, alg, used))
        W(f"{G:>8.2f}{msg_fu-G:>11.2f}{('YES' if hw else 'no'):>7}{lvmax:>10.1f}"
          f"{ft:>10.1f}{len(used):>11d}{gdm:>11.2f}"
          f"{('  '+', '.join('%.0f' % x for x in fr[:6])) if fr else '  (无)':>34}")

    W("")
    W("=" * 112)
    W("§2  逐 G 详情:槽状态 / 与混叠像的距离 / 事件计数")
    W("=" * 112)
    for (G, hw, lvmax, ft, fr, gdm, alg, used) in rows:
        W(f"--- G={G:+.2f} dB  ({'起振' if hw else '未起振'})  环路主导 {ft:.1f} Hz")
        if not used:
            W("      分配陷波:无")
        for s in used:
            W(f"      slot f={s.f:8.1f} Hz  st={ST.get(s.st,'?'):8s} depth={s.depth:6.2f} dB"
              f"   |f − 混叠像 {alias:.1f}Hz| = {abs(s.f-alias):8.1f} Hz"
              f"   |f − 真啸叫 {f_fu:.1f}Hz| = {abs(s.f-f_fu):9.1f} Hz")
        ev = {}
        for e in alg.events:
            ev[e[1]] = ev.get(e[1], 0) + 1
        W(f"      g_duck 最深 {gdm:+.2f} dB;事件 = "
          f"{ {k: v for k, v in sorted(ev.items()) if k in ('SLOTS_EXHAUSTED','DEPTH_EXHAUSTED','duck-slots','duck-depth')} }")
        W("")

    W("=" * 112)
    W("§3  判读(按预注册的三种互斥结果 + 反例守卫)")
    W("=" * 112)
    howled = [r for r in rows if r[1]]
    with_notch = [r for r in rows if r[4]]
    near = []
    for (G, hw, lvmax, ft, fr, gdm, alg, used) in rows:
        near += [f for f in fr if abs(f - alias) <= 30.]
    W(f"  起振的 G 档数            = {len(howled)}/{len(rows)}")
    W(f"  分配到陷波的 G 档数      = {len(with_notch)}/{len(rows)}")
    W(f"  陷波落在混叠像 ±30Hz 内  = {len(near)} 个  {['%.1f' % x for x in near]}")
    W(f"  任何陷波落在真啸叫频率(>8kHz)附近 = 0 个(结构上不可能:候选带上限 7800 Hz)")
    if near and howled:
        W("  ⇒ **Hf-A 立(错误动作)**:NHS 把陷波挂到混叠像上,而真啸叫在带外照旧。")
    elif with_notch and not near:
        W("  ⇒ ⛔ **反例守卫触发**:分配频率与混叠像无关 ⇒ P-1 的混叠像机理在空槽工况下")
        W("     不成立,P-1 表述范围须改写。")
    elif not with_notch and any(r[5] < 0 for r in rows):
        W("  ⇒ **Hf-C 立(只有宽带兜底在兜)**")
    elif not with_notch:
        W("  ⇒ **Hf-B 立(完全无动作)**")

    with open('/home/it1234/processor/01_design/prototype_W1P/r58_freeslot_out.txt',
              'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
