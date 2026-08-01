"""W1-P 第三轮 · 多通道 + 共享输出母线 + 频段选择性动态处理(8段动态PEQ)
adaptive-dsp(第3实例)· 2026-08-01 · [L2/宿主仿真]

链位按 IF-v1.4 C10 / W1-A §4 推定链位(动态 PEQ 在 tap **下游**、母线限幅之前):
  mic_i → 前放 → [NHS tap_i + 陷波器组_i] → 8段动态PEQ_i → 路由 → 共享母线 → 输出限幅 → 扬声器
                                                                → RIR_ij → mic_j
⚠ 产品本来就是 8进8出共享母线 + PRD §二.4 必备的 8 段动态 PEQ;
  第一/二轮的单通道宽带限幅原型**比真实产品更简单,而不是更保守**。
"""
import numpy as np
from scipy.signal import butter, lfilter, sosfilt, sosfilt_zi, butter as _bt
from env import image_source_rir, Limiter, env_db, FS, FRAME

BANDS = [(60,150),(150,300),(300,600),(600,1200),(1200,2400),(2400,4000),(4000,6000),(6000,9000)]


class DynPEQ:
    """8 段动态 PEQ(P0 重做)· **空闲严格单位增益**

    ⚠ 第三轮的实现是"分带滤波再相加",空闲时有约 6dB 插入损耗(F12),
      它在环路内 ⇒ 直接吃掉环路余量 ⇒ ch0 根本啸不起来,E1 因此测不成。
    正确形态(也与产品一致):**检测支路**用带通只做测量(不在信号路),
      **信号路**= 8 个 RBJ peaking 滤波器**串联**,增益由各段 GR 调制。
      GR=0dB 时 A=1 ⇒ b==a ⇒ 每段严格恒等 ⇒ **整条链空闲时逐样本透明**。
    """
    def __init__(self, thr_db=-30.0, ratio=8.0, atk_ms=3.0, rel_ms=120.0, fs=FS,
                 bw_oct=1.0):
        self.fs = fs; self.bw = bw_oct
        self.fc = [np.sqrt(lo*hi) for lo, hi in BANDS]
        self.det = [_bt(2, [lo/(fs/2), min(hi, fs/2*0.99)/(fs/2)], btype='band', output='sos')
                    for lo, hi in BANDS]
        self.dzi = [sosfilt_zi(x)*0 for x in self.det]
        self.thr = 10**(thr_db/20.0); self.ratio = ratio
        self.a_a = np.exp(-1.0/(atk_ms*1e-3*fs)); self.a_r = np.exp(-1.0/(rel_ms*1e-3*fs))
        self.g = np.ones(len(BANDS)); self.gr_db = np.zeros(len(BANDS))
        self.zi = [np.zeros(2) for _ in BANDS]

    def _peak_coef(self, f0, gain_db):
        A = 10.0**(gain_db/40.0)
        w0 = 2*np.pi*f0/self.fs
        alpha = np.sin(w0)*np.sinh(np.log(2)/2*self.bw*w0/np.sin(w0))
        b = np.array([1+alpha*A, -2*np.cos(w0), 1-alpha*A])
        a = np.array([1+alpha/A, -2*np.cos(w0), 1-alpha/A])
        return b/a[0], a/a[0]

    def process(self, x):
        n = len(x)
        # --- 检测支路(只测量,不在信号路)
        for i, d in enumerate(self.det):
            y, self.dzi[i] = sosfilt(d, x, zi=self.dzi[i])
            pk = np.max(np.abs(y)) + 1e-12
            tgt = 1.0 if pk <= self.thr else (self.thr/pk)**(1.0 - 1.0/self.ratio)
            a = self.a_a if tgt < self.g[i] else self.a_r
            self.g[i] = a**n * self.g[i] + (1 - a**n)*tgt
            self.gr_db[i] = 20*np.log10(max(self.g[i], 1e-9))
        # --- 信号路:串联 peaking,空闲(gr=0)时严格恒等
        out = x
        for i in range(len(BANDS)):
            if self.gr_db[i] > -0.01:
                continue                       # 恒等,跳过(不引入任何增益/相位)
            b, a = self._peak_coef(self.fc[i], self.gr_db[i])
            out, self.zi[i] = lfilter(b, a, out, zi=self.zi[i])
        return out

    @property
    def active(self):
        return bool(np.min(self.gr_db) < -0.5)

    @property
    def max_gr(self):
        return float(np.min(self.gr_db))


class MultiLoop:
    """N 通道共享母线闭环。"""
    def __init__(self, n_ch=2, rt60=0.35, g_fwd_db=None, bus_thr_db=-6.0,
                 dyn_thr_db=None, loop_gain_db=None, seed=0):
        self.n = n_ch
        self.rirs = []
        for j in range(n_ch):                      # 母线扬声器 → 各通道麦
            h, d = image_source_rir(rt60=rt60, mic=(1.2+0.6*j, 1.0+0.3*j, 1.5), seed=seed+j)
            self.rirs.append((h, d))
        self.g_fwd = [10**((g_fwd_db[j] if g_fwd_db else 30.0)/20.0) for j in range(n_ch)]
        self.loop_scale = [10**(((loop_gain_db[j] if loop_gain_db else -20.0)
                                 - (g_fwd_db[j] if g_fwd_db else 30.0))/20.0) for j in range(n_ch)]
        self.dyn = [DynPEQ(thr_db=(dyn_thr_db[j] if dyn_thr_db else -30.0)) for j in range(n_ch)]
        self.bus_lim = Limiter(thr_db=bus_thr_db)
        self.zi = [np.zeros(len(h)-1) for h, _ in self.rirs]

    def run(self, algs, sources, dur):
        n = int(dur*FS)//FRAME*FRAME
        bus_log = np.zeros(n); tap_log = [np.zeros(n) for _ in range(self.n)]
        ch_log = [np.zeros(n) for _ in range(self.n)]
        fb = [np.zeros(FRAME) for _ in range(self.n)]
        trace = []
        for i in range(0, n, FRAME):
            bus = np.zeros(FRAME)
            for j in range(self.n):
                mic = sources[j][i:i+FRAME] + fb[j]
                tap = mic                                   # 前放后 = NHS 检测 tap
                gr = {'out_lim_active': bool(self.bus_lim.active),
                      'out_lim_gr_db': float(self.bus_lim.gr_db),
                      'dyn_active': bool(self.dyn[j].active),
                      'dyn_gr_db': float(self.dyn[j].max_gr)}
                y = algs[j].process_frame(tap, gr)          # 陷波器组(tap 在其入口)
                y = self.dyn[j].process(y)                  # ★ 8段动态PEQ(tap 下游,C10 位5)
                y = y * self.g_fwd[j] * algs[j].duck_gain()
                bus += y
                tap_log[j][i:i+FRAME] = tap; ch_log[j][i:i+FRAME] = y
            bus = np.clip(bus, -8.0, 8.0)
            bus = self.bus_lim.process(bus)                 # 共享母线输出限幅
            for j in range(self.n):
                fb[j], self.zi[j] = lfilter(self.rirs[j][0]*self.loop_scale[j], [1.0],
                                            bus, zi=self.zi[j])
            bus_log[i:i+FRAME] = bus
            if i % (FRAME*375) == 0:
                trace.append((round(i/FS,1), int(self.bus_lim.active),
                              [int(d.active) for d in self.dyn]))
        return bus_log, tap_log, ch_log, trace
