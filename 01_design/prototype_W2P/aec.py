"""W2-P 原型 · AEC(MDF 分块频域自适应)· [L2/宿主仿真]
adaptive-dsp(adaptive-dsp-3)· 2026-08-01

理论链(lead 给的可复用件清单,文献-代码互证):
  Soo & Pang 1990  Multi-Delay block Frequency-domain adaptive filter (MDF)  ← 结构
  Valin 2007       "On Adjusting the Learning Rate in FDAF"                  ← **连续学习率替代硬判决 DTD**
  Enzner & Vary 2006 频域 Kalman                                             ← 一体化步长(本版未采,见 §取舍)
  SpeexDSP mdf.c(BSD-3,无专利条款)                                         ← 基座参考(本机未装,按文献自实现)

⚠ 定级:全部 [L2/宿主仿真],浮点。未过任何门。
⚠ 纪律 D4:**先做最小可用**。本版**不含** Kalman 步长、不含频段化 NLP 档位、不含舒适噪声——
   只在实测显出需要时才加(W1 教训:评审轮次里长出来的机制实测多半无收益)。
"""
import numpy as np

__version__ = "W2P0.1"


class MDF:
    """分块频域自适应滤波器。
    block N;FFT 2N;K 个分区覆盖尾长 K*N 样本。
    步长:Valin 连续学习率 —— 用"残余回声/误差"的在线估计做归一化,**不做硬 DTD 判决**。
    """
    def __init__(self, fs=16000.0, tail_ms=512.0, block=128, mu_max=0.2,
                 continuous_lr=True, leak=0.0, px_attack=None, px_release=None):
        self.fs = fs; self.N = block
        self.K = int(np.ceil(tail_ms * 1e-3 * fs / block))
        self.M = 2 * block
        self.W = np.zeros((self.K, self.M // 2 + 1), dtype=np.complex128)
        self.Xh = np.zeros((self.K, self.M // 2 + 1), dtype=np.complex128)
        self.xprev = np.zeros(block)
        self.eprev = np.zeros(block)
        self.Px = np.ones(self.M // 2 + 1) * 1e-6      # 远端功率(归一化用)
        self.Pe = np.ones(self.M // 2 + 1) * 1e-6      # 误差功率
        self.Py = np.ones(self.M // 2 + 1) * 1e-6      # 估计回声功率
        self.mu_max = mu_max; self.continuous_lr = continuous_lr; self.leak = leak
        self.mu_trace = []
        # ★ 修 W2-F4:正则下限必须**随信号尺度**,不能用 1e-12 这种绝对小数。
        #   否则激励含静音段(白噪突发/CSS 的 pause)时 Px→0 ⇒ 步长爆炸 ⇒ 发散。
        #   Px_ref = 长时平均远端功率;正则 = delta * Px_ref。
        self.Px_ref = 1e-6; self.delta = 1e-2
        # 非对称 Px 平滑(第七轮公平检验用;None ⇒ 对称 0.9,与既有结果一致)
        self.px_attack = px_attack; self.px_release = px_release

    def process(self, x_blk, d_blk):
        """x=远端参考(扬声器信号),d=近端麦克风(含回声)。返回 e(残余)。"""
        N, M = self.N, self.M
        xx = np.concatenate([self.xprev, x_blk]); self.xprev = x_blk.copy()
        X = np.fft.rfft(xx)
        self.Xh = np.roll(self.Xh, 1, axis=0); self.Xh[0] = X
        # --- 滤波
        Y = np.sum(self.W * self.Xh, axis=0)
        y = np.fft.irfft(Y, M)[N:]
        e = d_blk - y
        # --- 误差谱(前半置零 = 线性卷积约束)
        E = np.fft.rfft(np.concatenate([np.zeros(N), e]))
        # --- 功率跟踪
        inst = np.abs(X)**2
        if self.px_attack is None:
            a = 0.9
        else:   # 快攻慢放:功率上升用小 a(跟得快),下降用大 a(放得慢)
            a = np.where(inst > self.Px, self.px_attack, self.px_release)
        self.Px = a*self.Px + (1-a)*inst
        self.Px_ref = 0.999*self.Px_ref + 0.001*float(np.mean(np.abs(X)**2))
        self.Pe = a*self.Pe + (1-a)*np.abs(E)**2
        self.Py = a*self.Py + (1-a)*np.abs(Y)**2
        # --- 步长:Valin 连续学习率(无硬 DTD)
        if self.continuous_lr:
            # μ ≈ E[|残余回声|²]/E[|e|²];用 leakage-free 近似:残余 ∝ 未收敛度
            resid = np.maximum(self.Pe - self._nearend_est(), 1e-12)
            mu = np.clip(resid / (self.Pe + 1e-12), 0.0, 1.0) * self.mu_max
        else:
            mu = self.mu_max                       # broken/对照:固定步长
        self.mu_trace.append(float(np.mean(mu)))
        # --- 梯度更新(频域 NLMS)+ 线性卷积约束(梯度投影)
        G = np.conj(self.Xh) * E[None, :]
        step = mu / (self.K * self.Px + self.delta*self.K*self.Px_ref + 1e-20)
        dW = step[None, :] * G
        g = np.fft.irfft(dW, M, axis=1); g[:, N:] = 0.0
        self.W = (1.0 - self.leak) * self.W + np.fft.rfft(g, M, axis=1)
        return e

    def _nearend_est(self):
        """近端(本地语音+噪声)功率的粗估:误差中无法由远端解释的部分。
        最小可用实现:用误差与估计回声的差做下界钳位。"""
        return np.maximum(self.Pe - self.Py, 0.0) * 0.5


class NLP:
    """残余回声抑制(谱域)——**频段选择性快衰减**。
    ⚠ C10 子级约束:这正是 C10 禁止置于 NHS 检测 tap 之前的形态。
       W1 已定案:NHS tap 取在 **AEC 线性滤波输出之后、NLP 之前**。本原型要验证该链位。
    """
    def __init__(self, nbands=16, fs=16000.0, block=128, aggress=1.0):
        self.nb = nbands; self.block = block; self.aggress = aggress
        self.g = np.ones(nbands); self.prev = np.zeros(block)

    def process(self, e_blk, y_blk):
        M = 2*self.block
        E = np.fft.rfft(np.concatenate([self.prev, e_blk])); self.prev = e_blk.copy()
        Y = np.fft.rfft(np.concatenate([np.zeros(self.block), y_blk]))
        nb = self.nb; L = len(E); edge = np.linspace(0, L, nb+1).astype(int)
        Eo = E.copy()
        for b in range(nb):
            s, t = edge[b], edge[b+1]
            if t <= s: continue
            pe = np.mean(np.abs(E[s:t])**2) + 1e-20
            py = np.mean(np.abs(Y[s:t])**2) + 1e-20
            # 过量抑制:回声占比越高压得越狠(Wiener 型)
            g = pe / (pe + self.aggress*py)
            self.g[b] = 0.5*self.g[b] + 0.5*g
            Eo[s:t] *= self.g[b]
        return np.fft.irfft(Eo, M)[self.block:]

    @property
    def max_gr_db(self):
        return float(20*np.log10(max(np.min(self.g), 1e-9)))


class PFDKF:
    """分块频域 Kalman(PFDKF)—— **异源第二轨**(铁律七),不是重复劳动。
    与 MDF+NLMS 是不同推导:状态协方差 P 与观测噪声 R 显式建模,增益由 Kalman 式给出。
    参考:echocatzh/PFDKF(MIT)结构;Enzner & Vary 2006 频域 Kalman。
    """
    def __init__(self, fs=16000.0, tail_ms=512.0, block=128, A=0.999, eps=1e-8,
                 P0=1.0, q_rel=1e-3):
        """★ v0.4 修 PFDKF(第二轨此前形同未自适应,ERLE 仅 0.6dB):
        病因:P 初值 1e-4 ≪ R 初值 1e-2 ⇒ 分母被 R 主导 ⇒ Kalman 增益 Kg→0 ⇒ 不学;
              且过程噪声 1e-8 过小 ⇒ P 单调塌陷 ⇒ 越学越不学。
        修法:P0 放大到 O(1)(初始不确定度大),过程噪声 Q 取 q_rel·P(相对量,不塌陷),
              协方差更新用标准式 P←(1−Kg·X)·P·A² + Q(去掉我原来拍的 0.5 因子)。
        """
        self.N=block; self.K=int(np.ceil(tail_ms*1e-3*fs/block)); self.M=2*block
        F=self.M//2+1
        self.W=np.zeros((self.K,F),dtype=np.complex128)
        self.Xh=np.zeros((self.K,F),dtype=np.complex128)
        self.P=np.full((self.K,F),P0)
        self.R=np.full(F,1e-3)
        self.A=A; self.eps=eps; self.q_rel=q_rel; self.xprev=np.zeros(block)
    def process(self,x_blk,d_blk):
        N,M=self.N,self.M
        xx=np.concatenate([self.xprev,x_blk]); self.xprev=x_blk.copy()
        X=np.fft.rfft(xx); self.Xh=np.roll(self.Xh,1,axis=0); self.Xh[0]=X
        Y=np.sum(self.W*self.Xh,axis=0); y=np.fft.irfft(Y,M)[N:]; e=d_blk-y
        E=np.fft.rfft(np.concatenate([np.zeros(N),e]))
        self.R=0.9*self.R+0.1*np.abs(E)**2
        Xp=np.abs(self.Xh)**2
        denom=np.sum(Xp*self.P,axis=0)+self.R+self.eps
        Kg=self.P*np.conj(self.Xh)/denom[None,:]          # Kalman 增益
        dW=Kg*E[None,:]
        g=np.fft.irfft(dW,M,axis=1); g[:,N:]=0.0          # 线性卷积约束
        self.W=self.A*self.W+np.fft.rfft(g,M,axis=1)
        self.P=(1.0-np.real(Kg*self.Xh))*self.P*(self.A**2)+self.q_rel*self.P
        self.P=np.clip(self.P,1e-10,1e6)
        return e
