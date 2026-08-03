"""r80c · 换判据重测(定案格)+ 用原文【形状】标定新判据。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r80c_slope_out.txt(D6-j)。

⚠⚠ **先更正 lead 给本格的立论前提(第二次更正同一条,故写在最前):**
```
lead 写:「is_howling 基于【窄带啸叫特征】⇒ 频移抹掉窄带特征 ⇒ 定义上受 Δf 影响」
⇒ **不成立**。`howl_detect.py` 读码确认:它是**宽带 RMS + 双门迟滞 + 末段保持**,
  取数点在求和节点,**全程不含任何窄带/频谱形状的判断**。
⇒ 真正的失效不是"看不见窄带",而是 **【窗长不足】**:
  判据要求 RMS 越过 `ref+6 dB` **并在末 25% 窗内保持**;
  而频移使建立时间变长 ⇒ 12 s 内还没涨到门 ⇒ 被判"未起振"。
⇒ ⇒ 所以换判据的正确方向**不是**"换成不受窄带影响的",而是
  **换成不依赖【窗长】的** —— 即直接测**发散率**,而不是等它越过一个绝对门。
⇒ lead 的处方(③ 换能量发散判据)**正确**,但他给的理由不对 ⇒ 照做,理由改写。
```

新判据(**无新阈值**,这一点是刻意的):
  在每个 G 上取环内信号逐帧 RMS(dB),弃前 1/3(暂态),对剩余段做线性拟合 ⇒ **斜率 dB/s**
  ⇒ 稳定 ⇔ 斜率 ≤ 0;失稳 ⇔ 斜率 > 0
  ⇒ **MSG_slope = 斜率过零点的 G**(线性内插)⇒ 这是失稳的**定义**本身,
    ⛔ 不需要"超过多少 dB"这种绝对门 ⇒ 不受窗长与信号形状影响
  ⚠ 噪声底:m0 臂(无 proc)在远低于失稳的 G 上的斜率散布 ⇒ 本件同时报出,作为过零判读的分辨力

④ 形状标定(lead 提,**本件最有价值的一条**):
  Schroeder §V 预言的是一条**曲线的形状** —— 过 Δf ≈ 4/T60 之后**转平**
    T60=0.2 ⇒ 转折应在 ≈20 Hz;T60=0.5 ⇒ 转折应在 ≈8 Hz
  ⇒ 新判据复现出该转折 ⇒ 判据可信,且旧判据确实在高 Δf 上高估
  ⇒ 新判据仍单调升到 200 Hz ⇒ 不是器械问题,另有其物
  ⇒ **形状比数值更强:它不依赖我方口径、不依赖我方房间参数。**

⛔ 本文件不含结论性散文。
"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import FRAME
import r80_cell as C

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
T_OBS = 12.0
SRC_DB = -20.0
STEP = 0.5
DFS = [0., 2., 5., 8., 20., 200.]
SEEDS = [(0.2, 0), (0.2, 1), (0.5, 0), (0.5, 1)]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def slope_dbs(lp):
    """环内包络斜率(dB/s):逐帧 RMS,弃前 1/3,线性拟合。"""
    n = (len(lp) // FRAME) * FRAME
    lv = np.array([HD.rms_db(lp[i:i + FRAME]) for i in range(0, n, FRAME)])
    k = len(lv) // 3
    y = lv[k:]
    t = np.arange(len(y)) * FRAME / FS
    if len(y) < 8:
        return float('nan')
    return float(np.polyfit(t, y, 1)[0])


def scan_slope(hb, D, mkproc, lo, hi, src):
    """返回 [(G, slope), …] 与 **斜率过零点 G**(线性内插;全程 ≤0 ⇒ nan)。"""
    pts = []
    G = lo
    while G <= hi + 1e-9:
        proc, _ = mkproc()
        _, lp = clrig.Loop(hb, D, G, proc=proc).run(src, FRAME)
        s = slope_dbs(lp)
        pts.append((G, s))
        if s > 0 and len(pts) >= 2:
            (g0, s0), (g1, s1) = pts[-2], pts[-1]
            if s1 != s0:
                return pts, float(g0 + (0.0 - s0) * (g1 - g0) / (s1 - s0))
            return pts, float(g0)
        G += STEP
    return pts, float('nan')


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r80c · 换判据重测(斜率过零)+ 原文形状标定  [L2/宿主仿真]")
    W("⛔⛔ 更正 lead 给本格的前提(第二次更正同一条):")
    W("   `is_howling` **不是**窄带判据,读码确认为**宽带 RMS + 双门迟滞 + 末段保持**;")
    W("   真正失效 = **窗长不足**(频移拉长建立时间 ⇒ 12 s 内没涨到 ref+6 dB)。")
    W("   ⇒ 换判据的正确方向是【不依赖窗长】,不是【不依赖窄带】。lead 的处方对,理由改写。")
    W("新判据:环内包络斜率(dB/s,弃前 1/3 线性拟合)⇒ **MSG_slope = 斜率过零点的 G**")
    W("        ⛔ 无新阈值 —— 过零是失稳的定义本身")
    W(f"工作点:src={SRC_DB:+.0f} dBFS / T_OBS={T_OBS:.0f}s / 频移器 Hilbert 513 taps / 无陷波(纯频移臂)")
    W("")
    rows = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC_DB / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        W(f"### T60={T60} sd={sd}  anchor={anchor:+.2f}")
        # 噪声底:m0 臂在 anchor−6 处的斜率(远低于失稳)
        proc, _ = C.make_proc(0.0, False, False)
        _, lp = clrig.Loop(hb, D, anchor - 6, proc=proc).run(src, FRAME)
        W(f"    斜率噪声底(m0 @ anchor−6):{slope_dbs(lp):+.3f} dB/s")
        m0_pts, m0_g = scan_slope(hb, D, lambda: C.make_proc(0.0, False, False),
                                  anchor - 3, anchor + 6, src)
        W(f"    m0 臂 MSG_slope = {m0_g:+.2f}")
        W(f"{'Δf':>6}{'MSG_slope':>11}{'ΔMSG_slope':>12}{'MSG_旧判据':>12}{'ΔMSG_旧':>10}{'高估':>8}")
        for df in DFS:
            pts, g = scan_slope(hb, D, lambda: C.make_proc(df, False, False),
                                anchor - 1, anchor + 22, src)
            # 旧判据在同一条 src 上重测(同一次扫描的对照)
            Gh, last = anchor - 1, float('nan')
            while Gh <= anchor + 22 + 1e-9:
                pr, _ = C.make_proc(df, False, False)
                _, lph = clrig.Loop(hb, D, Gh, proc=pr).run(src, FRAME)
                if HD.is_howling(lph, ref, FS, FRAME)[0]:
                    break
                last = Gh
                Gh += STEP
            d_new = g - m0_g if np.isfinite(g) and np.isfinite(m0_g) else float('nan')
            d_old = last - m0_g if np.isfinite(last) and np.isfinite(m0_g) else float('nan')
            W(f"{df:>6.0f}{g:>11.2f}{d_new:>12.2f}{last:>12.2f}{d_old:>10.2f}"
              f"{d_old-d_new:>8.2f}")
            rows.append(dict(T60=T60, sd=sd, df=df, msg_slope=g, msg_old=last,
                             m0=m0_g, d_new=d_new, d_old=d_old,
                             slopes=[(round(a, 2), round(b, 3)) for a, b in pts]))
        W("")
    W("=" * 100)
    W("§S ④ 形状标定 —— Schroeder §V:过 Δf ≈ 4/T60 后应【转平】")
    W("=" * 100)
    for lay in (0.2, 0.5):
        opt = 4 / lay
        W(f"  T60={lay}(原文转折应在 ≈{opt:.0f} Hz):")
        for key, nm in (('d_new', '新判据 ΔMSG_slope'), ('d_old', '旧判据 ΔMSG')):
            v = [(df, np.median([r[key] for r in rows if r['T60'] == lay and r['df'] == df]))
                 for df in DFS]
            W(f"    {nm}: " + '  '.join(f"{int(d)}→{m:.2f}" for d, m in v if np.isfinite(m)))
            fin = [(d, m) for d, m in v if np.isfinite(m) and d >= opt]
            if len(fin) >= 2:
                rise = fin[-1][1] - fin[0][1]
                W(f"      ⇒ 转折点({int(opt)} Hz)之后的变化:{rise:+.2f} dB  "
                  f"{'**转平(|Δ| < 仪器底 0.354)**' if abs(rise) < 0.354 else '**仍在变化**'}")
        W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r80c_slope_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r80c_slope.json', 'w') as fp:
        json.dump(rows, fp)


if __name__ == '__main__':
    main()
