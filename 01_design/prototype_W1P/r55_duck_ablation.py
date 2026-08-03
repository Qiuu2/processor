"""r55 · 宽带兜底(g_duck)消融:r50 的 ΔMSG 里,有多少是【陷波】干的?

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

背景(r54 已坐实,0.2/seed0):
  真啸叫在 14531.9 Hz(带外)→ 经 48k→16k 抽取混叠成旁链里 1468.2 Hz 的**幻峰**
  → 8 槽已被台架钉死 ⇒ SLOTS_EXHAUSTED ⇒ `g_duck` 挂到 **−5.98 dB**(上限 −6)
  → g_duck 是**环内宽带衰减** ⇒ 直接抬高 MSG ⇒ 该臂晚触发 4 dB。
  ⇒ **r50 表里那条"唯一通过接入对照"的 +4.00 dB,可能主要是 duck 不是陷波。**

预注册(先写死,后跑):
  Hc · 关掉 duck 的音频作用后,ΔMSG 应等于【全带神谕】(r51/r53 实测环路口径):
       0.2/0→0.16  0.2/1→0.26  0.2/2→1.76  0.5/0→0.66  0.5/1→0.54  0.5/2→0.66
       判据:|ΔMSG_noduck − 全带神谕| ≤ 0.5 dB(=1 个扫描阶梯)六条全中 ⇒ Hc 立。
  Hd · 0.2/seed0 的 ΔMSG 从 4.00 掉到 ≤0.5 ⇒ 该条的收益归 duck 不归陷波。
       证伪:仍 ≈4 ⇒ duck 不是来源,r54 的归因错,须重查。
  ⚠ 纪律 #8(改了 X 结果变了,须证 X 真被改):**两个挂陷臂都报 g_duck 最深值**——
    带 duck 臂必须 <0(证明 duck 真的在动、消融有对象),消融臂的**状态机照跑**
    (只切断 `duck_gain` 的音频作用),其 g_duck 最深值应与带 duck 臂同量级。
    若消融臂 g_duck 恒 0 ⇒ 说明我切断的不止是音频作用,消融不干净,结论作废。

消融手法:`alg.duck_gain = lambda: 1.0`(实例级)——**只切断音频施加,不改状态演化**。
输出:r55_duck_ablation_out.txt   [L2/宿主仿真]
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
STEP = 0.5
T_OBS = 6.0
GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
P = nhs.Params()
OUT = []
ORACLE_FULL = {(0.2, 0): 0.16, (0.2, 1): 0.26, (0.2, 2): 1.76,
               (0.5, 0): 0.66, (0.5, 1): 0.54, (0.5, 2): 0.66}


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


def mk_alg(picks, no_duck):
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
        a.duck_gain = lambda: 1.0          # ★ 只切断音频施加,状态机照跑
    return a


def src_of(T, s):
    return 1e-3 * np.random.default_rng(s).standard_normal(int(T * FS))


def scan(h, D, mk, lo, hi, src, ref):
    """返回 (m, g_duck最深, 首起振G, 首起振主导频率)。"""
    G, last = lo, None
    gmin_at_last = 0.0
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
        hw, lvmax, _ = HD.is_howling(lp, ref, FS, FRAME)
        gmin = float(np.min(rec)) if rec else 0.0
        if hw:
            n = int(1.0 * FS)
            Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
            ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
            return (float('nan') if last is None else last), gmin_at_last, G, ft
        last, gmin_at_last = G, gmin
        G += STEP
    return float('nan'), gmin_at_last, float('nan'), float('nan')


def main():
    W("r55 · g_duck 消融:ΔMSG 中陷波 vs 宽带兜底的归因")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 "
      "howl_detect.py@fd63e901f2d8be33")
    W("[L2/宿主仿真]  T_OBS=6.0s STEP=0.5dB FRAME=64 nfft=2^18  预注册=本文件头")
    W("被测对象(D6-b):ΔMSG = 挂陷臂与基线臂的**起振阈增益之差**。")
    W("  混淆面:它把【陷波】与【宽带兜底 g_duck】两个完全不同的机制加在一个数里,")
    W("          而 g_duck 是宽带衰减 —— 它抬高 MSG 的方式与'降低增益'没有区别。")
    W("")
    W("=" * 118)
    W(f"{'T60':>5}{'sd':>4}{'m0基线':>9}{'mk带duck':>10}{'ΔMSG带duck':>12}"
      f"{'mk无duck':>10}{'ΔMSG无duck':>12}{'全带神谕':>10}{'|无duck−神谕|':>14}"
      f"{'duck最深(带)':>13}{'duck最深(消)':>13}")
    W("=" * 118)
    rows = []
    for T60 in (0.2, 0.5):
        for sd in (0, 1, 2):
            h, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
            he = clrig.h_eff(h)
            meter = MSGMeter(he, FS)
            base = meter.msg(slots=(), g_duck_db=0.0)
            ana_in = base['in']['msg_db']
            picks = pick_excl(he, 8)
            src = src_of(T_OBS, sd)
            ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
            m0, _, g0, f0 = scan(h, D, lambda: None, ana_in - 6, ana_in + 6, src, ref)
            mk1, gd1, g1, f1 = scan(h, D, lambda: mk_alg(picks, False),
                                    ana_in - 6, ana_in + 12, src, ref)
            mk2, gd2, g2, f2 = scan(h, D, lambda: mk_alg(picks, True),
                                    ana_in - 6, ana_in + 12, src, ref)
            d1, d2 = mk1 - m0, mk2 - m0
            orc = ORACLE_FULL[(T60, sd)]
            rows.append((T60, sd, m0, mk1, d1, mk2, d2, orc, gd1, gd2,
                         f0, f1, f2, base))
            W(f"{T60:>5.1f}{sd:>4}{m0:>9.2f}{mk1:>10.2f}{d1:>12.2f}"
              f"{mk2:>10.2f}{d2:>12.2f}{orc:>10.2f}{abs(d2-orc):>14.2f}"
              f"{gd1:>13.2f}{gd2:>13.2f}")
    W("")
    ok = [abs(r[6] - r[7]) <= 0.5 for r in rows]
    W(f"⇒ Hc:|ΔMSG_无duck − 全带神谕| ≤ 0.5 dB 的条数 = {sum(ok)}/6  "
      f"{'⇒ Hc 立' if all(ok) else '⇒ Hc 未全中(逐条看)'}")
    r0 = [r for r in rows if (r[0], r[1]) == (0.2, 0)][0]
    W(f"⇒ Hd:0.2/seed0  ΔMSG 带duck={r0[4]:.2f} → 无duck={r0[6]:.2f}  "
      f"{'⇒ Hd 立(收益归 duck)' if abs(r0[6]) <= 0.5 else '⇒ Hd 死'}")
    W(f"⇒ 纪律#8 证据:消融臂 g_duck 最深值(状态机仍在跑)= "
      f"{[round(r[9],2) for r in rows]}")
    W("   (若这一行全 0 ⇒ 消融切断了不止音频作用,本轮结论作废)")
    W("")
    W("=" * 118)
    W("§2  首次起振的主导频率(带内?带外?)")
    W("=" * 118)
    W(f"{'T60':>5}{'sd':>4}{'基线f_trig':>12}{'带duckf_trig':>14}"
      f"{'无duckf_trig':>14}{'全带临界f':>12}{'带内临界f':>12}")
    for (T60, sd, m0, mk1, d1, mk2, d2, orc, gd1, gd2, f0, f1, f2, base) in rows:
        W(f"{T60:>5.1f}{sd:>4}{f0:>12.1f}{f1:>14.1f}{f2:>14.1f}"
          f"{base['full']['f_crit']:>12.1f}{base['in']['f_crit']:>12.1f}")

    with open('/home/it1234/processor/01_design/prototype_W1P/'
              'r55_duck_ablation_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
