"""r82 · 修好的失稳判据 + **空测作硬闸门**(不通过则 `sys.exit`,⛔ 不是"检查并记录")。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r82_gate_out.txt(D6-j)。

⭐ D6-ap 的当场自查:「这个检查失败时,会阻止什么?」
   ⇒ 本件的答案:**阻止主扫描启动**(`sys.exit(1)`)。⇒ 所以它是闸门,不是输出行。

r80c 那把尺子的病(F75.1):取「**第一个** slope>0 的 G」⇒ 稳定区斜率在 0 附近随噪声涨落
⇒ 低 G 处一次偶然正斜率就提前终止 ⇒ 空测最大错 18.18 dB。
修法三条:
  ① **扫完整段**,不提前终止
  ② 每个 G 上**多噪声实现平均**(n_rep 条独立源)
  ③ 过零点取【平滑后曲线】的**最后一次由负转正**处线性内插(对孤立噪声尖峰鲁棒)

闸门两条(**都必须过**,任一不过 ⇒ 退出,不进主扫描):
  A **量程不变性**:同一配置、**两个不同的扫描区间** ⇒ MSG 之差 ≤ 仪器底
     (r80c 正是死在这里:m0 臂扫 anchor−3..+6,Δf=0 臂扫 anchor−1..+22 ⇒ 差 18.18 dB)
  B **实现散布**:同一配置、n 条**独立源实现** ⇒ MSG 散布(极差)≤ 仪器底
     ⇒ 它同时给出该判据的**分辨力**,而分辨力未知就不能读差值
"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
FLOOR = 0.25 * (2 ** 0.5)
T_OBS = 12.0
SRC_DB = -20.0
STEP = 0.5
N_REP = 3
SEEDS = [(0.2, 0), (0.2, 1), (0.5, 0), (0.5, 1)]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def slope_dbs(lp):
    n = (len(lp) // FRAME) * FRAME
    lv = np.array([HD.rms_db(lp[i:i + FRAME]) for i in range(0, n, FRAME)])
    y = lv[len(lv) // 3:]
    t = np.arange(len(y)) * FRAME / FS
    return float(np.polyfit(t, y, 1)[0]) if len(y) >= 8 else float('nan')


def msg_slope(hb, D, lo, hi, srcs, proc_factory=None):
    """修好的判据:全段扫 + 多实现平均 + 平滑后【最后一次】负→正 内插。"""
    Gs, sl = [], []
    G = lo
    while G <= hi + 1e-9:
        v = []
        for s in srcs:
            pf = proc_factory() if proc_factory else None
            _, lp = clrig.Loop(hb, D, G, proc=pf).run(s, FRAME)
            v.append(slope_dbs(lp))
        Gs.append(G)
        sl.append(float(np.mean(v)))
        G += STEP
    Gs, sl = np.array(Gs), np.array(sl)
    sm = np.convolve(sl, np.ones(3) / 3, mode='same') if len(sl) >= 3 else sl
    cross = [i for i in range(len(sm) - 1) if sm[i] <= 0 < sm[i + 1]]
    if not cross:
        return float('nan'), list(zip(Gs.round(2), sl.round(4)))
    i = cross[-1]                                   # **最后一次**转正
    g = Gs[i] + (0.0 - sm[i]) * (Gs[i + 1] - Gs[i]) / (sm[i + 1] - sm[i])
    return float(g), list(zip(Gs.round(2), sl.round(4)))


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r82 · 修好的判据 + **空测硬闸门**  [L2/宿主仿真]")
    W("⭐ D6-ap 自查:本闸门失败时**阻止主扫描启动**(sys.exit(1))⇒ 它是闸门,不是输出行")
    W(f"修法:①全段扫不提前终止 ②每 G 上 {N_REP} 条独立源平均 ③平滑后【最后一次】负→正 内插")
    W(f"工作点:src={SRC_DB:+.0f} dBFS / T_OBS={T_OBS:.0f}s / STEP={STEP} / 仪器底 {FLOOR:.3f} dB")
    W("被测臂 = m0(无 proc)—— 空测用它,因为它**最干净且答案已知必须自洽**")
    W("")
    W("=" * 96)
    W("闸门 A · 量程不变性(同配置,两个不同扫描区间 ⇒ MSG 之差应 ≤ 仪器底)")
    W("   ⚠ r80c 正是死在这里:两臂扫描区间不同 ⇒ 空测错 18.18 dB")
    W("=" * 96)
    W(f"{'T60':>5}{'sd':>4}{'区间1(a−4..a+3)':>18}{'区间2(a−1..a+6)':>18}{'差':>8}  判定")
    failA = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        srcs = [np.random.default_rng(1000 + sd * 10 + i).standard_normal(int(T_OBS * FS))
                * (10 ** (SRC_DB / 20.)) for i in range(N_REP)]
        g1, _ = msg_slope(hb, D, anchor - 4, anchor + 3, srcs)
        g2, _ = msg_slope(hb, D, anchor - 1, anchor + 6, srcs)
        d = abs(g1 - g2) if (np.isfinite(g1) and np.isfinite(g2)) else float('inf')
        ok = d <= FLOOR
        if not ok:
            failA.append((T60, sd, d))
        W(f"{T60:>5.1f}{sd:>4}{g1:>18.2f}{g2:>18.2f}{d:>8.2f}  "
          + ('✅ 过' if ok else '⛔ **不过**'))
    W(f"  ⇒ 闸门 A:**{len(SEEDS)-len(failA)}/{len(SEEDS)} 过**")
    W("")
    W("=" * 96)
    W("闸门 B · 实现散布(同配置,各条独立源实现 ⇒ 极差应 ≤ 仪器底)⇒ 同时给出判据分辨力")
    W("=" * 96)
    W(f"{'T60':>5}{'sd':>4}{'逐实现 MSG':>34}{'极差':>8}  判定")
    failB = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        vals = []
        for i in range(N_REP):
            s = [np.random.default_rng(2000 + sd * 10 + i).standard_normal(int(T_OBS * FS))
                 * (10 ** (SRC_DB / 20.))]
            g, _ = msg_slope(hb, D, anchor - 4, anchor + 3, s)
            vals.append(g)
        fin = [v for v in vals if np.isfinite(v)]
        rng_ = (max(fin) - min(fin)) if len(fin) > 1 else float('inf')
        ok = rng_ <= FLOOR
        if not ok:
            failB.append((T60, sd, rng_))
        W(f"{T60:>5.1f}{sd:>4}{str([round(v,2) for v in vals]):>34}{rng_:>8.2f}  "
          + ('✅ 过' if ok else '⛔ **不过**'))
    W(f"  ⇒ 闸门 B:**{len(SEEDS)-len(failB)}/{len(SEEDS)} 过**")
    W("")
    W("=" * 96)
    ok = (not failA) and (not failB)
    W(f"§G **闸门总判定:{'✅ 全过 ⇒ 允许进主扫描' if ok else '⛔ 不过 ⇒ 中止,不进主扫描'}**")
    if not failA and not failB:
        W("   ⇒ 判据分辨力 = 闸门 B 的最大极差(见上)⇒ 小于该值的差**不可判**")
    else:
        W(f"   闸门 A 不过:{failA}")
        W(f"   闸门 B 不过:{failB}")
        W("   ⇒ ⛔ 该判据仍不可用;其任何 MSG 数值不得引用。")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r82_gate_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r82_gate.json', 'w') as fp:
        json.dump(dict(failA=failA, failB=failB, passed=bool(ok)), fp)
    # ⭐ 硬闸门:不过就退出,**阻止**任何后续步骤(D6-ap)
    if not ok:
        print("\n⛔⛔ 闸门未通过 ⇒ sys.exit(1),不进主扫描。", file=sys.stderr)
        sys.exit(1)
    print("\n✅ 闸门通过 ⇒ 允许进主扫描。")


if __name__ == '__main__':
    main()
