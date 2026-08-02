"""闭环台架 · 起振判据 —— **与 nhs.py 零代码共享、零信号共享**。
⚠ 本文件**不得 import nhs**(CHECK 断言)。只用 numpy 做时域 RMS。

⭐ 两个洞的修法(架构侧指出):
  **洞一:零共享【代码】≠ 零共享【信号】。** 宽带 RMS 会被 NHS 的 `g_duck` 压低
    ⇒ 啸叫已起振而 RMS 不超门。**⇒ 取数点改在【求和节点】(NHS 之前),不受 g_duck 影响。**
  **洞二:「连续 N 帧单调增长」对已饱和的啸叫失效** —— 起振后被限幅钳住就不再增长。
    **⇒ 改为「超门 + 保持」+ 双门迟滞,配增益阶梯扫描。**

⚠ 物理上限:稳定环路的建立时间 ∝ 1/(1−|GF|) 发散
  ⇒ **MSG 只能测到有限精度,精度由观察时长 T 决定** ⇒ 每个 MSG 必带 T。
"""
import numpy as np

TH_ON_DB = 6.0     # 双门迟滞:上门(超过即置位)
TH_OFF_DB = 3.0    # 双门迟滞:下门(跌破才复位)
HOLD_FRAC = 0.25   # 保持:置位状态须覆盖观察窗末段的这一比例


def rms_db(x):
    return 20.0 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-30)


def is_howling(loop_sig, ref_db, fs, frame=64,
               th_on=TH_ON_DB, th_off=TH_OFF_DB, hold_frac=HOLD_FRAC):
    """在观察窗内是否起振。**输入必须是求和节点信号**(NHS 之前)。
    判据:逐帧 RMS 越 ref+th_on 置位、跌破 ref+th_off 复位(双门迟滞);
          **末段 hold_frac 内保持置位** ⇒ 判起振。
    ⇒ 对**已饱和**的啸叫仍成立(不要求继续增长)。"""
    n = (len(loop_sig) // frame) * frame
    lv = np.array([rms_db(loop_sig[i:i + frame]) for i in range(0, n, frame)])
    st = False
    states = np.zeros(len(lv), dtype=bool)
    for i, v in enumerate(lv):
        if not st and v > ref_db + th_on:
            st = True
        elif st and v < ref_db + th_off:
            st = False
        states[i] = st
    tail = states[int(len(states) * (1 - hold_frac)):]
    return bool(tail.all()), float(lv.max()), float(lv[-1])
