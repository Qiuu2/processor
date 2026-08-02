"""闭环台架 —— 反馈环 + 参数化 F(z) + 解析自检 + N_eff 可执行定义。
[L2/宿主仿真]

⭐ 架构侧勘正(本文件按此实现):
  失稳条件 `G·F = 1` 是**复数等式** ⇒ 既要 |G·F| = 1,又要 ∠F ≡ 0 (mod 2π)。
  ⇒ MSG = −20log10( max{ |F(ω)| : ∠F(ω) ≡ 0 } )   ← **只在相位条件成立的频点上取 max**
  ⇒ 用 max|F| 会**系统性低估 MSG**,自检会误报"台架有 bug"而台架其实是对的。

⭐ 由此得到 **N_eff 的可执行定义**:
  **N_eff = 相位条件成立的【临界频点】数**(而非 |F| 的极大值数)。
  ⚠ 纯延迟 z^(−D) 使相位快速旋转 ⇒ 临界频点很密 ⇒ **D 直接影响 N_eff**,须一并报。
  ⚠ 临界点有无穷多个,只有 |F| 够高的才可能成为起振点
    ⇒ 定义带 margin:N_eff(m) = #{临界点 : |F| ≥ max_critical − m dB}
    ⇒ **报 N_eff 随 m 的曲线,不报单一数字**(避免把一个门限值当成物理量)。
"""
import numpy as np
from scipy.signal import freqz

FS = 48000.0


def make_F(T60=0.5, delay_ms=8.0, seed=0, fs=FS, dur_mult=2.0):
    """⭐ 噪声 RIR(架构侧裁定,取代模态合成):
        h(t) = n(t)·exp(−t/τ),  n ~ 白高斯,  τ = T60 / 6.908
    ⚠ **为什么不用模态合成**:Weyl 公式 dN/df = 4πVf²/c³,V=100m³ ⇒ 1kHz 处 31.1 模态/Hz
      ⇒ 100–8000Hz 约 5.3×10⁶ 个模态 ⇒ K 取几十上百造出的是**离散模态区**的房间,
      而检测带几乎全在**统计区** ⇒ 那不是会议室,是玩具。
    ⭐ 噪声 RIR 使 |H(f)| **在构造上**具有 Rayleigh 幅度、dB 域 σ≈5.57dB、峰间距≈4/T60
      —— 正是架构侧那张表 MC 所用的统计模型 ⇒ **不是"假设成立",是"构造保证"**。
      多径自带,不用另建。
    ⇒ **可扫的轴是 T60,不是 K**。换算 N_eff ≈ 1975·T60。
    返回 (h, D) —— h 已含直达延迟。"""
    rng = np.random.default_rng(seed)
    tau = T60 / 6.908
    D = int(round(delay_ms * 1e-3 * fs))
    n = int(dur_mult * T60 * fs)
    t = np.arange(n) / fs
    h = rng.standard_normal(n) * np.exp(-t / tau)
    h = np.concatenate([np.zeros(D), h])
    return h / (np.sqrt(np.sum(h ** 2)) + 1e-30), D


def rir_stats(h, fs=FS, f_lo=100.0, f_hi=8000.0, nfft=1 << 16):
    """五条真实性检验用的统计量:dB 域 σ、Exp(1) KS、DRR/Rician K、峰间距。"""
    from scipy.stats import kstest
    H = np.fft.rfft(h, nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    m = (f >= f_lo) & (f <= f_hi)
    P = np.abs(H[m]) ** 2
    P = P / P.mean()                       # 归一 ⇒ 理论上 ~Exp(1)
    ks = kstest(P, 'expon')
    sd = float(np.std(20 * np.log10(np.abs(H[m]) + 1e-30)))
    # DRR:直达 = 最大抽头前后 ±0.5ms;混响 = 其余
    k0 = int(np.argmax(np.abs(h))); w = int(0.5e-3 * fs)
    d = float(np.sum(h[max(0, k0 - w):k0 + w] ** 2))
    r = float(np.sum(h ** 2) - d)
    drr = 10 * np.log10(d / (r + 1e-30) + 1e-30)
    return dict(sd_db=sd, ks_stat=float(ks.statistic), ks_p=float(ks.pvalue),
                drr_db=float(drr), rician_k_db=float(drr))


def h_eff(h, frame=64):
    """⭐ **环路有效冲激响应** = RIR + 块延迟。
    ⚠ `Loop.run` 逐块处理 ⇒ 环路含 **1 帧(frame 样本)延迟**。
      **凡对【环路】做解析(临界点/MSG/ΔMSG 预测)的调用,必须传 h_eff(h),不是 h。**
    ⚠ 本层曾写下"必须用 D_det = D_prop + frame"却**没落实到调用处** ——
      「知道了」与「用上了」之间还有一步,而那一步不会自己发生。
      ⇒ 故把它做成**函数**而非注释:调用处写不写 h_eff 是可 grep 的。"""
    return np.concatenate([np.zeros(int(frame)), np.asarray(h, float)])


def F_response(h, n=1 << 16, fs=FS):
    """F(z) = FIR(h) 的频响。返回 (f_hz, H)。"""
    H = np.fft.rfft(h, n)
    f = np.fft.rfftfreq(n, 1 / fs)
    return f, H


def critical_points(h, n=1 << 16, fs=FS, f_lo=100.0, f_hi=8000.0):
    """相位条件 ∠F ≡ 0 (mod 2π) 成立的频点。**这就是 N_eff 的载体。**"""
    f, H = F_response(h, n, fs)
    m = (f >= f_lo) & (f <= f_hi)
    f = f[m]; H = H[m]
    ph = np.angle(H)
    sgn = np.sign(ph)
    idx = np.where((sgn[:-1] * sgn[1:] < 0) & (np.abs(ph[:-1] - ph[1:]) < np.pi))[0]
    if len(idx) == 0:
        return np.array([]), np.array([])
    t = ph[idx] / (ph[idx] - ph[idx + 1])
    fc = f[idx] + t * (f[idx + 1] - f[idx])
    mc = np.abs(H[idx]) + t * (np.abs(H[idx + 1]) - np.abs(H[idx]))
    return fc, 20 * np.log10(mc + 1e-30)


def analytic_msg_db(h, n=1 << 16, fs=FS):
    """MSG = −20log10( max{|F| : ∠F≡0} )。**只在临界点上取 max**(复数失稳条件)。"""
    _, mdb = critical_points(h, n, fs)
    if len(mdb) == 0:
        return float('inf'), float('-inf')
    return float(-mdb.max()), float(mdb.max())


def predict_dmsg(h, k, n=1 << 16, fs=FS):
    """⭐ 对**这一条** F(z) 的精确 ΔMSG 预测(架构侧裁定,取代查表):
        陷掉相位临界点上最高的 k 个 ⇒ 新的失稳点 = 第 k+1 高
        ΔMSG(k) = [最高临界点 dB] − [第 k+1 高临界点 dB]
    ⚠ **本式在 dB 域直接相减**,不写成 10log 或 20log 之比 —— 避免 10/20 二义
      (critical_points 已返回 20log10|F|;若写成 10log10(功率比) 数值相同但易被误抄)。
    ⚠ 不含任何统计假设、不需要 N_crit、不需要 iid ⇒ **可与实测逐条配对比较**。"""
    _, mdb = critical_points(h, n, fs)
    if len(mdb) <= k:
        return float('nan')
    srt = np.sort(mdb)[::-1]
    return float(srt[0] - srt[k])


def _crit_from_H(f, H):
    """从给定频响直接求临界点(供迭代式复用)。

    ⭐⭐ **结构性免疫(不是"实测未发现问题")**:
      本函数用 `np.angle` 直接取主值 + 符号变化检测,**不使用 `np.unwrap`**
      ⇒ "陷波中心 π 跳变导致相位展开失效"这一失效模式**在本实现中无法发生**,
        而不是"这次没发生"。
      ⚠ **若日后有人为性能/可读性加入 `unwrap`,该免疫性即失效** ——
        届时必须重新验证陷波中心邻域的过零检测(r39 的 π 跳变检查)。
      ⚠ `|ph[:-1]-ph[1:]| < π` 这个护栏是为了排除主值绕回造成的假过零;
        它同时意味着**真跳变 >π 处会被跳过** —— 这正是加了 `unwrap` 之后会出问题的地方。
    """
    ph = np.angle(H); sg = np.sign(ph)
    idx = np.where((sg[:-1] * sg[1:] < 0) & (np.abs(ph[:-1] - ph[1:]) < np.pi))[0]
    if len(idx) == 0:
        return np.array([]), np.array([])
    t = ph[idx] / (ph[idx] - ph[idx + 1])
    fc = f[idx] + t * (f[idx + 1] - f[idx])
    mc = np.abs(H[idx]) + t * (np.abs(H[idx + 1]) - np.abs(H[idx]))
    return fc, 20 * np.log10(mc + 1e-30)


def predict_dmsg_iter(h, k, depth_db=-18.0, bw_oct=0.2, n=1 << 16, fs=FS,
                      f_lo=100.0, f_hi=8000.0):
    """⭐ **迭代式**预测(取代一次式的不变性假设)。
    一次式 ΔMSG(k)=X(1)−X(k+1) 默认「挂 k 个陷波后临界点集不变」;
    **但陷波器自身有相位** ⇒ ∠(F·N₁···N_k) ≠ ∠F ⇒ **临界点会移动、也可能新增**。
    迭代式:挂 1 个(在当前临界点最大处)→ **重算 F·N₁ 的临界点集** → 取新最大 → 再挂,共 k 次。
    ⇒ **无任何不变性假设。** 返回 (ΔMSG_dB, 每步的最大临界点 dB 列表)。
    ⚠ 陷波深度按 `depth_db`(默认 max_depth=−18dB,即算法最深);深度是参数不是常数。"""
    from scipy.signal import freqz
    f0, H0 = F_response(h, n, fs)
    m = (f0 >= f_lo) & (f0 <= f_hi)
    f = f0[m]; H = H0[m].copy()
    w = 2 * np.pi * f / fs
    _, m0 = _crit_from_H(f, H)
    if len(m0) == 0:
        return float('nan'), []
    hist = [float(m0.max())]
    for _ in range(k):
        fc, mdb = _crit_from_H(f, H)
        if len(fc) == 0:
            break
        j = int(np.argmax(mdb))
        fstar = float(fc[j])
        # RBJ peaking(负增益)在 fstar 处
        A = 10 ** (depth_db / 40.0)
        w0 = 2 * np.pi * fstar / fs
        alpha = np.sin(w0) * np.sinh(np.log(2) / 2 * bw_oct * w0 / np.sin(w0))
        b = np.array([1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A])
        a = np.array([1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A])
        _, Hn = freqz(b, a, worN=w)
        H = H * Hn
        _, mm = _crit_from_H(f, H)
        hist.append(float(mm.max()) if len(mm) else float('nan'))
    return float(hist[0] - hist[-1]), hist


def n_crit(h, n=1 << 16, fs=FS):
    """N_crit = **独立相位临界点数**(自变量;实测,**不许由 |H| 极大值乘固定系数换算**
    —— 比值在 T60=0.05 时 0.97、≥0.2 才稳定在 0.46)。"""
    fc, _ = critical_points(h, n, fs)
    return int(len(fc))


def ks_on_critical(h, n=1 << 16, fs=FS):
    """⭐ KS 跑在**临界点样本**上(架构侧裁定):
      ①独立性构造保证(临界点间距 ≈ 3.9× 相干带宽);②功效合理;
      ③**它检验的正是模型真正使用的那个总体** —— 原来跑在全频点上不只统计不当,是检验错了对象。
    返回 (D 统计量, N, 偏度, 过量峰度)。**报 D 幅度,不报 p。**"""
    from scipy.stats import kstest, skew, kurtosis
    _, mdb = critical_points(h, n, fs)
    if len(mdb) < 20:
        return float('nan'), len(mdb), float('nan'), float('nan')
    P = 10 ** (mdb / 10.0)          # |F|^2
    P = P / P.mean()                # 归一 ⇒ 理论 Exp(1)
    return (float(kstest(P, 'expon').statistic), int(len(P)),
            float(skew(P)), float(kurtosis(P)))


def delays(D_prop, T60, frame=64, fs=FS):
    """⭐ 两个延迟必须**分成两个名字**(混用差 5.7 倍):
      D_det = 传播 + 块延迟 + 算法内延迟   ⇒ **自检用**:算临界点【位置】
      tau_g = D_det + 混响群延迟(τ/2)     ⇒ **估临界点【数量】用**
    ⚠ 旁链是**并联观测路径,不在环内** ⇒ 分析窗延迟**不计入任何一个**。"""
    D_det_s = D_prop / fs + frame / fs
    tau = T60 / 6.908
    tau_g_s = D_det_s + tau / 2.0
    return dict(D_det_ms=D_det_s * 1e3, tau_g_ms=tau_g_s * 1e3,
                ratio=tau_g_s / D_det_s)


def n_eff(h, margin_db, n=1 << 16, fs=FS):
    """⚠ **降级为诊断量,不得用于查表**:它是**截断计数**,而表用"全部样本再取极值"
      ⇒ 拿截断计数查表 = 极值运算做了两次。报曲线即可。"""
    _, mdb = critical_points(h, n, fs)
    if len(mdb) == 0:
        return 0
    return int((mdb >= mdb.max() - margin_db).sum())


class Loop:
    """闭环:src ──►(+)──► [proc] ──► ×G ──► F(z)=FIR(h) ──┐  反馈回加法器。
    ⚠ F(z) 现为 **FIR(噪声 RIR h)**,用 lfilter 带状态做块卷积(逐样本卷积会慢 4 个数量级)。"""

    def __init__(self, h, D_prop, G_db, proc=None, fs=FS):
        from scipy.signal import lfilter_zi
        self.h = np.asarray(h, float)
        self.D_prop = int(D_prop)
        self.G = 10 ** (G_db / 20.0)
        self.proc = proc
        self.fs = fs
        self.zi = np.zeros(len(self.h) - 1)

    def run(self, src, frame=64):
        """块级闭环:inp = src + fb ; y = proc(inp) ; fb = F(G·y)
        ⚠ 反馈取自 **proc 之后、乘 G 之后**(否则 proc 不在环内)。
        ⚠ 块处理引入 **1 帧环路延迟** ⇒ 自检须用 D_det = D_prop + frame。
        返回 (out, loop_sig):
          out      = proc 之后(扩声输出)
          loop_sig = **求和节点**(src + fb),★ 起振判据取这里 ★
        ⭐ 起振判据取求和节点的理由:它在 NHS **之前**,**完全不受 g_duck/陷波影响**
           ⇒ 判据与被测物**零信号共享**。(取 out 会被 g_duck 压低 ⇒ 洞一。)
        """
        from scipy.signal import lfilter
        n = (len(src) // frame) * frame
        out = np.zeros(n); loop = np.zeros(n)
        fb = np.zeros(frame)
        for i in range(0, n, frame):
            inp = src[i:i + frame] + fb
            loop[i:i + frame] = inp
            y = self.proc(inp) if self.proc is not None else inp
            out[i:i + frame] = y
            fb, self.zi = lfilter(self.h, [1.0], self.G * y, zi=self.zi)
        return out, loop
