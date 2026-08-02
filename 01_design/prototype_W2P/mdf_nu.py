"""W2-P · 非均匀分区 MDF + 环路内抽取/内插滤波器组
adaptive-dsp-3 · 2026-08-01 · [L2/宿主仿真]

架构要求(非可选):**首分区 ≤32 样本**,把 I/O 延迟与分区数 K 解耦。
关键机理:大分区处理的是**更老的尾段**,其参考样本早已就绪 ⇒
         大分区的块延迟**不进 I/O 路径**,只有首分区的 32 样本进。
⇒ 延迟由首分区定(32/16000 = 2.0ms),而 K 由尾长/分区结构定。
"""
import numpy as np
from scipy.signal import firwin, lfilter

__version__ = "W2P0.5"


class NUMDF:
    """三段非均匀分区 MDF(段内均匀,段间倍增)。
    段 s:块长 L_s,覆盖 [off_s, off_s + L_s*K_s) 样本的尾段。
    """
    def __init__(self, fs=16000.0, stages=((32, 8), (256, 8), (1024, 6)),
                 mu_max=0.2, delta=1.0):
        self.fs = fs; self.mu = mu_max; self.delta = delta
        self.stages = []
        off = 0
        for L, K in stages:
            M = 2 * L; F = M // 2 + 1
            self.stages.append(dict(
                L=L, K=K, M=M, off=off,
                W=np.zeros((K, F), dtype=np.complex128),
                Xh=np.zeros((K, F), dtype=np.complex128),
                Px=np.ones(F) * 1e-6, Px_ref=1e-6,
                xprev=np.zeros(L), acc_x=np.zeros(0), acc_e=np.zeros(0),
                ybuf=np.zeros(0), norm=1.0))
            off += L * K
        self.tail = off
        # ★ 修 W2-F(归一化口径):NLMS 的 ||x||² 应是**整个滤波器**的输入能量,
        #   而非该段自己的。各段原用 K_s·Px_s(∝ L_s·K_s)⇒ 分母偏小 ⇒ 有效步长被放大
        #   8-10.7×(实测:标称 μ=0.05 ≈ 均匀的 μ_eff 0.40,正落发散边界)。
        #   修正因子 = tail_total / (L_s·K_s),使两种结构在同一标称 μ 下可比。
        for s_ in self.stages:
            s_['norm'] = self.tail / float(s_['L'] * s_['K'])
        self.xhist = np.zeros(off + max(s['L'] for s in self.stages) * 2 + 8)

    @property
    def K_total(self):
        return sum(s['K'] for s in self.stages)

    @property
    def io_delay_samples(self):
        return self.stages[0]['L']          # ★ 只有首分区进 I/O 路径

    def process(self, x_blk, d_blk):
        """块长 = 首分区 L0(=32)。返回残余 e。"""
        L0 = self.stages[0]['L']
        assert len(x_blk) == L0
        self.xhist = np.concatenate([self.xhist, x_blk])[-(self.tail + 8192):]
        y = np.zeros(L0)
        for s in self.stages:
            s['acc_x'] = np.concatenate([s['acc_x'], x_blk])
            # ★ 修 W2-F(对齐):**先产出、后消费**。
            #   原实现在本段本次产出**之前**就消费 ybuf ⇒ 每段每次欠一个块
            #   ⇒ 冲激验收里峰偏 +4×L(实测 tap 228 而非 100)。
            #   标准 overlap-save:输入块 n 产出的 y_n 与输入块 n **同时段**,应在本次消费。
            while len(s['acc_x']) >= s['L']:
                xb = s['acc_x'][:s['L']]; s['acc_x'] = s['acc_x'][s['L']:]
                need = s['off'] + s['L']
                if s['off'] > 0:
                    seg = self.xhist[len(self.xhist)-need:len(self.xhist)-s['off']]
                    seg = seg[-s['L']:] if len(seg) >= s['L'] else np.pad(seg, (s['L']-len(seg), 0))
                else:
                    seg = xb
                xx = np.concatenate([s['xprev'], seg]); s['xprev'] = seg.copy()
                X = np.fft.rfft(xx)
                s['Xh'] = np.roll(s['Xh'], 1, axis=0); s['Xh'][0] = X
                Y = np.sum(s['W'] * s['Xh'], axis=0)
                s['ybuf'] = np.concatenate([s['ybuf'], np.fft.irfft(Y, s['M'])[s['L']:]])
                inst = np.abs(X)**2
                s['Px'] = 0.9*s['Px'] + 0.1*inst
                s['Px_ref'] = 0.999*s['Px_ref'] + 0.001*float(np.mean(inst))
            if len(s['ybuf']) >= L0:
                y += s['ybuf'][:L0]; s['ybuf'] = s['ybuf'][L0:]
        e = d_blk - y[:L0]
        # 各段用同一 e 更新(按各自块率累积)
        for s in self.stages:
            s['acc_e'] = np.concatenate([s['acc_e'], e])
            while len(s['acc_e']) >= s['L']:
                eb = s['acc_e'][:s['L']]; s['acc_e'] = s['acc_e'][s['L']:]
                E = np.fft.rfft(np.concatenate([np.zeros(s['L']), eb]))
                step = self.mu / (s['norm']*(s['K']*s['Px'] + self.delta*s['K']*s['Px_ref']) + 1e-20)
                dW = step[None, :] * np.conj(s['Xh']) * E[None, :]
                g = np.fft.irfft(dW, s['M'], axis=1); g[:, s['L']:] = 0.0
                s['W'] = s['W'] + np.fft.rfft(g, s['M'], axis=1)
        return e


class DecimInterp:
    """环路内抽取/内插滤波器组(48k ↔ 16k,3:1)。
    ⚠ C-8 的诞生场景在本链上**第二次出现**(第一次是原型的分带-相加空闲插损 6dB)。
      V-27 要验的就是它的**空闲恒等性**:空场输入,down→up 往返净增益应 ≈0dB。
    """
    def __init__(self, ntap=101, fs=48000.0, fc=6700.0, ratio=3):
        self.r = ratio
        self.h = firwin(ntap, fc/(fs/2))
        self.zd = np.zeros(ntap-1); self.zu = np.zeros(ntap-1)
        self.ntap = ntap

    def down(self, x):
        y, self.zd = lfilter(self.h, [1.0], x, zi=self.zd)
        return y[::self.r]

    def up(self, x):
        u = np.zeros(len(x)*self.r); u[::self.r] = x*self.r
        y, self.zu = lfilter(self.h, [1.0], u, zi=self.zu)
        return y


class NUMDFWrap:
    """128 样本块的适配壳:内部按 32 样本调 NUMDF 4 次。
    使非均匀结构能与均匀 L=128/K=64 在**同一台架、同一块率**下对比(V-26 同参可比要求)。
    暴露 .W 以兼容 probe 的冻结对照(frozen = 各段 W 全部还原)。
    """
    def __init__(self, stages=((32, 8), (256, 8), (1024, 6)), mu_max=0.2,
                 delta=1.0, fs=16000.0, **kw):
        self.core = NUMDF(fs=fs, stages=stages, mu_max=mu_max, delta=delta)
        self.L0 = self.core.stages[0]['L']

    @property
    def W(self):
        return [s['W'].copy() for s in self.core.stages]

    @W.setter
    def W(self, v):
        for s, w in zip(self.core.stages, v):
            s['W'] = w.copy()

    @property
    def K(self):
        return self.core.K_total

    def process(self, x_blk, d_blk):
        out = np.empty(len(x_blk))
        for k in range(0, len(x_blk), self.L0):
            out[k:k+self.L0] = self.core.process(x_blk[k:k+self.L0], d_blk[k:k+self.L0])
        return out

    @property
    def struct_str(self):
        return " + ".join(f"{s['L']}×{s['K']}" for s in self.core.stages)
