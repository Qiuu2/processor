"""r54 · 判定 0.2/seed0 例外:挂陷臂比【全带 MSG】晚触发 ~4 dB,为什么?

r51/r52 已定:基线臂 m0 = MSG_full + 0.08 dB(精确);挂陷臂 mk = MSG_full + 4.08 dB。
而 r51 实测环路传函说挂陷后全带 MSG 只升 0.16 dB ⇒ **挂陷臂多出来的 ~3.9 dB 无来源**。

预注册假设(先写死):
  Ha · g_duck 宽带兜底在动。`nhs.process_frame` 末行 `y = y*duck_gain()` 是**环内**的
       宽带衰减;8 槽全被钉死在 HOLD ⇒ 任何新候选都撞 `if not free:` ⇒ SLOTS_EXHAUSTED
       ⇒ `g_duck_db = max(-6, g_duck_db-1)`。**每 1 dB duck 直接抬高 MSG 1 dB。**
       预测:挂陷臂在 G≥−6 附近 g_duck 明显 <0(量级 −2~−6dB),基线臂恒 0(无 NHS)。
       证伪:g_duck 全程 == 0 ⇒ Ha 死,另找。
  Hb · 触发 duck 的候选来自**带外啸叫的混叠**。旁链 48k→16k 抽取,AA 低通截止 7.2kHz;
       14529.6 Hz 折叠到 |16000−14529.6| = **1470.4 Hz**。
       预测:若 Ha 真,SLOTS_EXHAUSTED 事件的候选频率应聚在 ~1470 Hz 附近。
       证伪:候选频率散布或落在别处 ⇒ 混叠通路不是来源(Ha 仍可能真,来源不同)。
  ⚠ Ha 与 Hb 独立判:Ha 只看 g_duck 轨迹,Hb 只看事件频率。不得用一条的成立去推另一条。

输出:r54_seed0_out.txt   [L2/宿主仿真]
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
T_OBS = 6.0
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
P = nhs.Params()
OUT = []


def W(s):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


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


def src_of(T, s):
    return 1e-3 * np.random.default_rng(s).standard_normal(int(T * FS))


def main():
    T60, sd = 0.2, 0
    h, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
    he = clrig.h_eff(h)
    meter = MSGMeter(he, FS)                  # nfft=2^18(r53 §C 收敛)
    picks = pick_excl(he, 8)
    base = meter.msg(slots=(), g_duck_db=0.0)
    src = src_of(T_OBS, sd)
    ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])

    W("r54 · 0.2/seed0 例外判定    T_OBS=6.0s FRAME=64 nfft=2^18")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 "
      "howl_detect.py@fd63e901f2d8be33")
    W("[L2/宿主仿真]  预注册 = 本文件头(Ha/Hb 与证伪条件)")
    W("")
    W(f"MSG_in(空)  = {base['in']['msg_db']:+.3f} dB @ {base['in']['f_crit']:.1f} Hz")
    W(f"MSG_full(空)= {base['full']['msg_db']:+.3f} dB @ {base['full']['f_crit']:.1f} Hz")
    st0 = meter.msg(slots=mk_alg(picks).slots, g_duck_db=0.0)
    W(f"MSG_in(8陷,g_duck=0)  = {st0['in']['msg_db']:+.3f} dB "
      f"@ {st0['in']['f_crit']:.1f} Hz")
    W(f"MSG_full(8陷,g_duck=0)= {st0['full']['msg_db']:+.3f} dB "
      f"@ {st0['full']['f_crit']:.1f} Hz")
    W(f"picks = {['%.1f' % p for p in picks]}")
    W(f"混叠预测(Hb):14529.6 Hz --(48k→16k)--> "
      f"{abs(16000-14529.6):.1f} Hz")
    W("")
    W("=" * 108)
    W("§1  挂陷臂逐 G:g_duck 轨迹 + 瞬时 MSG + 起振判定       [Ha]")
    W("=" * 108)
    W(f"{'G(dB)':>8}{'起振?':>7}{'帧RMS峰':>9}{'g_duck末':>10}{'g_duck最深':>11}"
      f"{'duck事件数':>11}{'MSG_full末':>11}{'margin末':>10}{'主导频率Hz':>12}")

    rows = []
    for G in (-9.04, -8.54, -8.04, -7.04, -6.04, -5.54, -5.04, -4.54, -4.04):
        alg = mk_alg(picks)
        rec = []

        def wrapped(blk, _a=alg, _r=rec):
            y = _a.process_frame(blk, GR)
            _r.append(_a.g_duck_db)           # ★ 只读,不改行为
            return y

        _, lp = clrig.Loop(h, D, G, proc=wrapped).run(src, FRAME)
        hw, lvmax, lvend = HD.is_howling(lp, ref, FS, FRAME)
        gd = np.array(rec)
        # 末态瞬时 MSG(用真实 g_duck 与真实槽态)
        m_end = meter.msg(slots=alg.slots, g_duck_db=float(gd[-1]))
        n = int(1.0 * FS)
        Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
        ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
        ducke = [e for e in alg.events if 'duck' in str(e[1])]
        rows.append((G, hw, lvmax, gd, alg, m_end, ft, ducke))
        W(f"{G:>8.2f}{('YES' if hw else 'no'):>7}{lvmax:>9.1f}{gd[-1]:>10.2f}"
          f"{gd.min():>11.2f}{len(ducke):>11d}{m_end['full']['msg_db']:>11.2f}"
          f"{m_end['full']['msg_db']-G:>10.2f}{ft:>12.1f}")

    W("")
    W("判读锚(Ha):g_duck 最深 == 0.00 全行 ⇒ Ha 死。")
    W("            g_duck 显著 <0 且 margin 因此转正 ⇒ Ha 立,晚触发有来源。")
    W("")
    W("=" * 108)
    W("§2  基线臂对照(proc=None,结构上没有 NHS ⇒ g_duck 不存在)   [D6-d]")
    W("=" * 108)
    W(f"{'G(dB)':>8}{'起振?':>7}{'帧RMS峰':>9}{'MSG_full':>11}{'margin':>9}"
      f"{'主导频率Hz':>12}")
    for G in (-9.54, -9.04, -8.54, -8.04, -7.04, -6.04, -5.04):
        _, lp = clrig.Loop(h, D, G, proc=None).run(src, FRAME)
        hw, lvmax, lvend = HD.is_howling(lp, ref, FS, FRAME)
        n = int(1.0 * FS)
        Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
        ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
        W(f"{G:>8.2f}{('YES' if hw else 'no'):>7}{lvmax:>9.1f}"
          f"{base['full']['msg_db']:>11.2f}{base['full']['msg_db']-G:>9.2f}{ft:>12.1f}")

    W("")
    W("=" * 108)
    W("§3  SLOTS_EXHAUSTED / duck 事件的候选频率分布           [Hb]")
    W("=" * 108)
    for (G, hw, lvmax, gd, alg, m_end, ft, ducke) in rows:
        ex = [e for e in alg.events if e[1] in ('SLOTS_EXHAUSTED', 'DEPTH_EXHAUSTED')]
        fr = [e[2] for e in ex]
        if not ex:
            W(f"  G={G:+.2f}: 无 EXHAUSTED 事件")
            continue
        fr = np.array(fr, float)
        W(f"  G={G:+.2f}: EXHAUSTED×{len(ex)}  候选频率 中位={np.median(fr):.1f}Hz "
          f"[{fr.min():.1f}..{fr.max():.1f}]  前 8 个={np.array2string(fr[:8], precision=1)}")
    W("")
    W("=" * 108)
    W("§4  g_duck 时间轨迹(挂陷臂,每 0.5s 取一点)")
    W("=" * 108)
    for (G, hw, lvmax, gd, alg, m_end, ft, ducke) in rows:
        step = int(0.5 * FS / FRAME)
        W(f"  G={G:+.2f} {'[起振]' if hw else '[稳]  '}: " +
          " ".join(f"{gd[i]:+.0f}" for i in range(0, len(gd), step)))

    with open('/home/it1234/processor/01_design/prototype_W1P/r54_seed0_out.txt',
              'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
