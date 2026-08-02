"""r21 ②:撞顶后残余的**单调性判别** + **阴性对照**(硬要求,不通过则不出结论)。
判别:最后几步加深时,输出上该频点残余是否仍单调下降?
  · 仍下降 ⇒ 深度不够,可议加深;
  · 不再下降 ⇒ 陷波没对准,加深无效 ⇒ 兜底是唯一正解。
⚠ **阴性对照**:把陷波中心**偏移 1 个带宽**再扫一遍。
   若偏移与对准的残余曲线**无差别** ⇒ 该器械在此素材下**分不出对准与否** ⇒ **判别结论无效**。
   (与裸停构造同型:无分辨力的载体会给出看似有意义的读数。)
⚠ D-J:须报被测分支实际触达次数;0 次 ⇒ 判「无效」而非「通过」。
[L2/宿主仿真·合成料]
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import nhs
import fp_suite as S
from nhs import NHS, FS, FRAME, NFFT, FS_SC, NotchSlot

GR_OFF = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
P0 = nhs.Params()
STEPS = [P0.depth0 + P0.depth_step * k for k in range(6)]      # -3 … -18
DUR = 90.0


def residual_at(mat, f_notch, f_probe, depth):
    """把素材过一个**固定深度、固定中心**的单陷波,量 f_probe 处输出残余(dB)。
    冻结自适应(T_low 抬到不可达)⇒ 只测"这个陷波造成了什么",不掺算法自己的动作。"""
    b = NHS()
    b.P.T_low = 999.0
    sl = b.slots[0]
    sl.st = NotchSlot.HOLD; sl.f = f_notch
    sl.depth = depth; sl.target = depth
    sl.set_coef(FS, b.P.bw_oct)
    for s2 in b.slots[1:]:
        s2.st = NotchSlot.FREE
    n = (len(mat) // FRAME) * FRAME
    ys = []
    for i in range(0, n, FRAME):
        ys.append(b.process_frame(mat[i:i + FRAME], GR_OFF))
    y = np.concatenate(ys)
    acc = np.convolve(y, nhs._AA_LP, mode='same')[::nhs.DEC]
    df = FS_SC / NFFT
    k = int(round(f_probe / df))
    w = np.hanning(NFFT)
    mags = []
    for j in range(0, len(acc) - NFFT, NFFT):
        M = np.abs(np.fft.rfft(acc[j:j + NFFT] * w))
        if 0 < k < len(M):
            mags.append(20 * np.log10(M[k] * 4.0 / NFFT + 1e-30))
    return float(np.median(mags)) if mags else float('nan')


print("r21 ② · 撞顶后残余单调性判别 + **阴性对照**")
print("[L2/宿主仿真·合成料]  **阴性对照不通过 ⇒ 不出结论**(硬要求,不是加分项)")
print(f"深度台阶:{[f'{d:.0f}' for d in STEPS]}  素材窗={DUR:.0f}s\n")

n_reach = 0
verdicts = []
for sd in range(4):
    mat = S.m_piano(DUR, 1000 + sd)
    a = NHS()
    n = (len(mat) // FRAME) * FRAME
    for i in range(0, n, FRAME):
        a.process_frame(mat[i:i + FRAME], GR_OFF)
    ev = [e for e in a.events if e[1] == 'DEPTH_EXHAUSTED']
    if not ev:
        print(f"  试次{sd}: DEPTH_EXHAUSTED 未触达 ⇒ 跳过")
        sys.stdout.flush()
        continue
    n_reach += 1
    f0 = float(ev[0][2])
    bw = max(f0 * P0.bw_oct, 15.0)
    ali = [residual_at(mat, f0, f0, d) for d in STEPS]
    mis = [residual_at(mat, f0 + bw, f0, d) for d in STEPS]     # ★ 阴性对照:偏移 1 个带宽
    print(f"  试次{sd}  f0={f0:.0f}Hz  bw={bw:.0f}Hz")
    print(f"    对准 残余: " + "  ".join(f"{d:.0f}→{r:6.1f}" for d, r in zip(STEPS, ali)))
    print(f"    偏移 残余: " + "  ".join(f"{d:.0f}→{r:6.1f}" for d, r in zip(STEPS, mis)))
    # ⛔ r21b 判据勘正(自查):初版用「深度台阶间的落差跨度」作对照判据 ——
    #   **那正是被判别的量本身** ⇒ 对照只有在结论为"仍下降"时才可能通过
    #   ⇒ **只能朝一个方向通过的对照不是对照**(循环论证)。
    #   正确的对照量 = **同一深度下,对准 vs 偏移的绝对电平差**:
    #   差大 ⇒ 器械确实"看得见"陷波对没对准 ⇒ 有分辨力。
    sep = float(np.mean([m - a for a, m in zip(ali, mis)]))   # 偏移 − 对准(应为正且大)
    ctrl_ok = sep >= 6.0
    span_a = ali[0] - ali[-1]
    print(f"    ★对照量(同深度下 偏移−对准 的电平差)= **{sep:+.1f}dB**  "
          + ("**对照通过 ✓(器械看得见对准与否)**" if ctrl_ok
             else "**⛔ 对照不通过 ⇒ 本试次判别无效**"))
    print(f"    被判别量(−3→−18 的总落差)= {span_a:+.1f}dB")
    if not ctrl_ok:
        verdicts.append(None)
        sys.stdout.flush()
        continue
    d3 = np.diff(ali)[-3:]
    mono = all(x < -0.5 for x in d3)
    verdicts.append(mono)
    print(f"    最后 3 步变化 = {np.round(d3, 2)}  ⇒ "
          + ("**仍单调下降 ⇒ 深度不够,可议加深**" if mono
             else "**不再下降 ⇒ 加深无效 ⇒ 兜底是唯一正解**"))
    sys.stdout.flush()

print(f"\n  ⇒ DEPTH_EXHAUSTED 触达 **{n_reach}/4** 试次"
      + ("" if n_reach else "  ⇒ **D-J 判「无效」**"))
val = [v for v in verdicts if v is not None]
if not val:
    print("  ⇒ **所有试次的阴性对照均未通过 ⇒ 本判别无结论**(不得读作「加深无效」)")
else:
    print(f"  ⇒ 有效试次 {len(val)}/{len(verdicts)}:仍下降 {sum(val)} / 不再下降 {len(val)-sum(val)}")
