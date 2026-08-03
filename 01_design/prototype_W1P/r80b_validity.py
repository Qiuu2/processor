"""r80b · r80 效度诊断 —— 频移臂的 ΔMSG 为什么过了理论最优还在涨?
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r80b_validity_out.txt(D6-j)。

**先更正我自己在 F74.2 里提的那个可疑成因:**
  我猜「`is_howling` 随 Δf 漏检(窄带特征被抹开)」。**读码后:错。**
  `howl_detect.py` 是**宽带 RMS + 双门迟滞 + 末段保持**,取数点在求和节点 —— **与窄带无关**。
  ⇒ 频移不会让它"看不见",因为它数的是总能量。⇒ 原假设作废。

**改判的可疑成因(本件要测的那个):台架的 8 kHz 带限把移频能量【吸走】。**
```
频移 ⇒ 分量每绕一圈上移 Δf ⇒ 绕 N 圈后上移 N·Δf
台架在 8 kHz 处带限 ⇒ 走过 8 kHz 的能量**离开环路,不再回来**
⇒ 逃逸所需圈数 ≈ (8000 − f_start)/Δf;环路往返 ≈ 13.33 ms ⇒ 12 s 窗内约 900 圈
   Δf=200 ⇒ 约 35 圈 ≈ 0.47 s   ← 窗内必然逃逸
   Δf= 20 ⇒ 约 350 圈 ≈ 4.7 s   ← 窗内会逃逸
   Δf=  5 ⇒ 约 1400 圈 ≈ 18.7 s ← **超出 12 s 窗 ⇒ 不逃逸**
⇒ 预测:**Δf ≳ 12–20 起,环内能量应显著上移/减少 ⇒ 稳定度被台架人为抬高**
⇒ 而 Δf ≤ 8 应基本干净
```
判据(逐 Δf 在 r80 报出的终点 G 上直接观测环内信号):
  ① 谱质心(Hz)与 **>6 kHz 能量占比** ⇒ 能量是否被推向带限边缘
  ② 末秒 RMS / 首秒 RMS ⇒ 环路到底在长还是在衰
⛔ 本文件不含结论性散文。
"""
import sys, json, glob, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import FRAME
from fshift import FreqShifter
import r80_cell as C

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
T_OBS = 12.0
SRC_DB = -20.0
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def spec_stats(lp):
    n = len(lp)
    w = np.hanning(n)
    X = np.abs(np.fft.rfft(lp * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / FS)
    tot = X.sum() + 1e-30
    cen = float((f * X).sum() / tot)
    hi = float(X[f > 6000.].sum() / tot)
    return cen, hi


def main():
    t0 = time.time()
    R = []
    for p in glob.glob(DIR + 'r80_cell_*.json'):
        R += json.load(open(p))
    D = {}
    for r in R:
        if r['tag'] != 'BASE':
            D.setdefault(r['tag'], {})[(r['T60'], r['sd'])] = r
    B = {(r['T60'], r['sd']): r for r in R if r['tag'] == 'BASE'}

    W("未经 critic 评审 —— r80b · r80 效度诊断  [L2/宿主仿真]")
    W("⛔ 先更正 F74.2 我自己提的可疑成因:`is_howling` 是**宽带 RMS + 双门迟滞**(读码确认),")
    W("   **与窄带特征无关** ⇒「频移抹开窄带特征 ⇒ 漏检」这个假设**作废**。")
    W("⇒ 改测的假设:**台架 8 kHz 带限把移频能量吸走** ⇒ 逃逸圈数 ≈ (8000−f)/Δf,")
    W("   环路往返 13.33 ms,12 s 窗约 900 圈 ⇒ 预测 Δf ≳ 12–20 起能量显著上移,Δf ≤ 8 干净。")
    W("")
    W(f"{'Δf':>5}{'T60':>5}{'sd':>4}{'终点G':>8}{'谱质心Hz':>10}{'>6k占比':>9}"
      f"{'末秒/首秒dB':>12}{'起振?':>7}")
    rows = []
    for (T60, sd) in [(0.2, 0), (0.2, 1), (0.5, 0), (0.5, 1)]:
        h0, D_ = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC_DB / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        # 参照:只陷波臂(Δf=0)在其终点 G 上
        for tag, df in (('BASE', 0), ('D002', 2), ('D005', 5), ('D008', 8),
                        ('D012', 12), ('D020', 20), ('D200', 200)):
            if tag == 'BASE':
                rec = B[(T60, sd)]
                G = rec['m0'] + rec['d_notch']
                proc, _ = C.make_proc(0.0, True, False)
            else:
                rec = D[tag][(T60, sd)]
                G = rec['m0'] + rec['d_shift']
                proc, _ = C.make_proc(float(df), False, False)
            if not np.isfinite(G):
                continue
            _, lp = clrig.Loop(hb, D_, G, proc=proc).run(src, FRAME)
            hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
            cen, hi = spec_stats(lp)
            k = int(FS)
            grow = HD.rms_db(lp[-k:]) - HD.rms_db(lp[:k])
            W(f"{df:>5}{T60:>5.1f}{sd:>4}{G:>8.2f}{cen:>10.0f}{100*hi:>8.1f}%"
              f"{grow:>+12.2f}{str(hw):>7}")
            rows.append(dict(df=df, T60=T60, sd=sd, G=float(G), centroid=cen,
                             hi6k=hi, growth=grow, howl=bool(hw)))
        W("")
    W("=" * 96)
    W("§V 机械对表(⛔ 判读文字由人在看到数之后写)")
    W("=" * 96)
    for k, nm in (('centroid', '谱质心(Hz)'), ('hi6k', '>6kHz 能量占比'), ('growth', '末秒/首秒(dB)')):
        W(f"  {nm}:")
        for df in (0, 2, 5, 8, 12, 20, 200):
            v = [r[k] for r in rows if r['df'] == df]
            if not v:
                continue
            v2 = [100 * x for x in v] if k == 'hi6k' else v
            W(f"    Δf={df:>3}: 逐条 {[round(x, 2) for x in v2]}  中位 {np.median(v2):.2f}")
        W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r80b_validity_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r80b_validity.json', 'w') as fp:
        json.dump(rows, fp)


if __name__ == '__main__':
    main()
