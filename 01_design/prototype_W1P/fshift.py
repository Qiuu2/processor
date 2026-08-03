"""频移器(单边带 / Hilbert 法)—— r80 合成实验用。
⛔ 未经 critic 评审。[L2/宿主仿真]。

原理(Schroeder 1964 §II 的那个器件):把**所有**频率分量同移 `Δf` **赫兹**(不是同比)。
  解析信号 x_a(t) = x(t) + j·H{x(t)};   y(t) = Re{ x_a(t) · e^{j2πΔf t} }
  ⇒ 频谱整体搬移 +Δf Hz。

实现要点(块流式,带状态 —— 环路里必须逐块调用):
  · Hilbert 变换用**奇数长 FIR**(Type III),理想冲激 h[n] = 2/(πn)(n 奇)、0(n 偶),加 Hamming 窗
  · 实支路须**同延迟** M = (ntaps−1)/2 个样本对齐 ⇒ 用同长度的纯延迟线
  · 相位累加器逐样本推进 2π·Δf/fs,**跨块连续**(否则每块起点相位跳变 ⇒ 谱线糊开)
⚠ 本件只负责"把频谱搬走";**可听性与 AEC 兼容性不在本件范围**(架构侧路由)。
"""
import numpy as np
from scipy.signal import lfilter, lfilter_zi


def hilbert_fir(ntaps=257):
    """Type III Hilbert FIR。ntaps 必须为奇数。群延迟 = (ntaps−1)/2 样本。"""
    assert ntaps % 2 == 1, "ntaps 必须为奇数(Type III)"
    M = (ntaps - 1) // 2
    n = np.arange(-M, M + 1)
    h = np.zeros(ntaps)
    odd = (n % 2) != 0
    h[odd] = 2.0 / (np.pi * n[odd])
    h *= np.hamming(ntaps)
    return h, M


class FreqShifter:
    """块流式频移器。`process(x)` 逐块调用,状态跨块保持。

    df_hz = 0 ⇒ **恒等**(⚠ 但仍走同一条延迟路径 ⇒ 与非零档的群延迟一致,
                 这样"只陷波"臂与"陷波+频移"臂的环路延迟差不会混进结果)。
    """

    def __init__(self, df_hz, fs, ntaps=257):
        self.df = float(df_hz)
        self.fs = float(fs)
        self.h, self.M = hilbert_fir(ntaps)
        self.zi_h = np.zeros(len(self.h) - 1)      # Hilbert 支路状态
        self.d = np.zeros(2 * self.M + 1)          # 实支路纯延迟(同群延迟)
        self.d[self.M] = 1.0
        self.zi_d = np.zeros(len(self.d) - 1)
        self.n0 = 0                                 # 相位累加器(样本计数,跨块连续)

    def process(self, x):
        x = np.asarray(x, float)
        xi, self.zi_h = lfilter(self.h, [1.0], x, zi=self.zi_h)   # 虚部(Hilbert)
        xr, self.zi_d = lfilter(self.d, [1.0], x, zi=self.zi_d)   # 实部(同延迟)
        if self.df == 0.0:
            self.n0 += len(x)
            return xr
        n = np.arange(self.n0, self.n0 + len(x))
        self.n0 += len(x)
        w = 2.0 * np.pi * self.df / self.fs
        return xr * np.cos(w * n) - xi * np.sin(w * n)

    def reset(self):
        self.zi_h[:] = 0.0
        self.zi_d[:] = 0.0
        self.n0 = 0
