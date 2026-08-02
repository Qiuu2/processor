"""W1-P 宿主原型 · 环境层:房间 RIR(image-source)+ 合成素材 + 闭环台架
adaptive-dsp(第 3 实例)· 2026-08-01 · 全部产出 [L2/宿主仿真]

⚠ 定级与限制(FINDINGS.md 同款声明,勿删):
  1. 本文件全部为**浮点宿主仿真**,不构成定点行为的证据,不得升 [L1]。
  2. RIR = 自写 image-source 法(pyroomacoustics 未装);**非实录 RIR**。
  3. 素材 = **合成**(语音/音乐/掌声/咳嗽);DEMAND/QUT-NOISE 等真实语料未入库
     ⇒ 误报率数字是**合成素材上的**,真实素材须 W2 采集后重跑。
"""
import numpy as np

FS = 48000.0          # 音频域采样率(IF-v1.4 C1)
FRAME = 64            # 样本/帧(C1,750fps)


# ---------------------------------------------------------------- 房间 RIR
def image_source_rir(room=(5.0, 4.0, 3.0), mic=(1.2, 1.0, 1.5), spk=(3.4, 2.6, 1.6),
                     rt60=0.45, fs=FS, order=12, seed=0, max_len=None):
    """image-source 法 RIR(约 50 行,替代 pyroomacoustics)。
    返回 (rir, direct_delay_samples)。反射系数由 RT60 经 Sabine 反推。"""
    rng = np.random.default_rng(seed)
    L = np.asarray(room, float); m = np.asarray(mic, float); s = np.asarray(spk, float)
    V = float(np.prod(L)); S = 2 * (L[0]*L[1] + L[1]*L[2] + L[0]*L[2])
    # Sabine: RT60 = 0.161 V / (S a)  -> 吸收系数 a -> 反射系数 beta
    a = min(0.99, 0.161 * V / (S * max(rt60, 1e-3)))
    beta = float(np.sqrt(max(1e-6, 1.0 - a)))
    c = 343.0
    if max_len is None:
        max_len = int(fs * (rt60 * 1.2 + 0.05))
    h = np.zeros(max_len)
    for nx in range(-order, order + 1):
        for ny in range(-order, order + 1):
            for nz in range(-order, order + 1):
                for px in (0, 1):
                    for py in (0, 1):
                        for pz in (0, 1):
                            # 镜像源坐标
                            ips = np.array([
                                (1 - 2*px) * s[0] + 2*nx*L[0],
                                (1 - 2*py) * s[1] + 2*ny*L[1],
                                (1 - 2*pz) * s[2] + 2*nz*L[2]])
                            d = float(np.linalg.norm(ips - m))
                            if d < 1e-6:
                                continue
                            n_refl = abs(2*nx - px) + abs(2*ny - py) + abs(2*nz - pz)
                            amp = (beta ** n_refl) / (4.0 * np.pi * d)
                            k = int(round(d / c * fs))
                            if 0 <= k < max_len and amp > 1e-7:
                                h[k] += amp
    h += rng.normal(0, 1e-9, max_len)          # 极小抖动,避免完全稀疏的病态谱
    direct = int(round(float(np.linalg.norm(s - m)) / c * fs))
    # ★ 换能器带限(物理必需):image-source 的抽头全为正 ⇒ RIR 含巨大直流分量,
    #   若不带限,|H(f)| 峰必落在 0Hz,闭环会"在直流啸叫"——那是仿真伪影不是声学。
    #   扬声器/传声器都不通直流,故对 RIR 施加 80Hz–8kHz 带通代表电声通路。
    # ★ 台架修(critic 第四条):原用 filtfilt(零相位)⇒ **RIR 非因果**
    #   ⇒ 直达前有 3.76% 能量、首个 >峰−80dB 抽头落在 n=0
    #   ⇒ ClosedLoop 的 `direct_delay > FRAME` 断言校验的是**几何**延迟,
    #      **并未建立它声称的前提**(分块闭环要求真实首抽头晚于块长)。
    #   改为**因果** lfilter;换能器本就是因果系统。
    from scipy.signal import butter, lfilter as _lf
    bb, aa = butter(2, [80.0/(fs/2), 8000.0/(fs/2)], btype='band')
    h = _lf(bb, aa, h)
    # ★ 按**带内最大频响**归一(不是时域峰值):使 |H(f)|_max = 1
    #   ⇒ g_pre_db + g_fwd_db 直接就是"最不利频点的环路增益(dB)",0dB = 起振临界。
    Hf = np.abs(np.fft.rfft(h, 1 << 16))
    h = h / (Hf.max() + 1e-30)
    return h, direct


# ---------------------------------------------------------------- 合成素材
def synth_speech(dur, fs=FS, seed=1, f0=120.0):
    """合成语音:基频滑动 + 5 共振峰 + 音节包络(4-8Hz)+ 停顿。"""
    rng = np.random.default_rng(seed)
    n = int(dur * fs); t = np.arange(n) / fs
    f0t = f0 * (1 + 0.12 * np.sin(2*np.pi*0.7*t) + 0.05*rng.normal(0, 1, n).cumsum()/np.sqrt(n))
    phase = 2*np.pi*np.cumsum(f0t)/fs
    x = np.zeros(n)
    for k in range(1, 26):                      # 谐波族(voiced)
        x += (1.0/k**1.1) * np.sin(k*phase + rng.uniform(0, 2*np.pi))
    from scipy.signal import butter, lfilter    # 共振峰
    for fc, q in [(600, 6), (1200, 8), (2500, 9), (3400, 10)]:
        b, a = butter(2, [fc*(1-1/(2*q))/(fs/2), fc*(1+1/(2*q))/(fs/2)], btype='band')
        x += 0.5 * lfilter(b, a, x)
    syl = 0.5 + 0.5*np.sin(2*np.pi*5.0*t + rng.uniform(0, 6))       # 音节率 5Hz
    turns = (np.sin(2*np.pi*0.18*t + 1.0) > -0.25).astype(float)    # 发言轮次(含停顿)
    from scipy.signal import lfilter as lf
    turns = lf(np.ones(int(0.05*fs))/int(0.05*fs), [1.0], turns)    # 平滑边沿
    x = x * syl * turns
    return 0.25 * x / (np.max(np.abs(x)) + 1e-12)


def synth_music(dur, fs=FS, seed=2):
    """合成音乐:和弦长音 + 渐强 + 弱谐波独奏(长笛类,Rane 指名误报源)。"""
    rng = np.random.default_rng(seed)
    n = int(dur * fs); t = np.arange(n) / fs
    x = np.zeros(n)
    notes = [261.6, 329.6, 392.0, 523.3]
    for f in notes:                              # 强谐波族乐音
        env = 0.5 + 0.5*np.sin(2*np.pi*0.35*t + rng.uniform(0, 6))
        for k in range(1, 9):
            x += env * (0.9/k**1.3) * np.sin(2*np.pi*f*k*t + rng.uniform(0, 6))
    # 长笛类:弱谐波(高次比基频低 20-30dB)+ 颤音 + 渐强 —— 最难区分的一类
    ff = 880.0
    trem = 1 + 0.06*np.sin(2*np.pi*5.5*t)
    cres = np.linspace(0.2, 1.0, n)
    x += cres * trem * (1.0*np.sin(2*np.pi*ff*t) + 0.05*np.sin(2*np.pi*2*ff*t)
                        + 0.03*np.sin(2*np.pi*3*ff*t))
    return 0.25 * x / (np.max(np.abs(x)) + 1e-12)


def synth_transients(dur, fs=FS, seed=3, kind='clap'):
    """掌声/咳嗽:宽带瞬态(检验 PAPR/PNPR 与连续性对孤立帧的淘汰)。"""
    rng = np.random.default_rng(seed)
    n = int(dur * fs); x = np.zeros(n)
    rate = 3.0 if kind == 'clap' else 0.7
    for _ in range(max(1, int(dur * rate))):
        ln = int(0.02*fs) if kind == 'clap' else int(0.25*fs)
        # ★ r10 修:原护栏写死 n-4000,而 cough 的 ln = 0.25*fs = 12000 > 4000
        #   ⇒ dur 较短时 p+ln 越界崩溃。护栏须按 ln 取。
        if n <= ln:
            continue
        p = rng.integers(0, n - ln)
        env = np.exp(-np.arange(ln) / (ln/4))
        burst = rng.normal(0, 1, ln) * env
        if kind == 'cough':                      # 咳嗽:带低频成分
            burst += 0.6*np.sin(2*np.pi*180*np.arange(ln)/fs) * env
        x[p:p+ln] += burst
    return 0.3 * x / (np.max(np.abs(x)) + 1e-12)


# ---------------------------------------------------------------- 闭环台架
class Limiter:
    """输出限幅器(B-F1 的核心道具):峰值限幅 + 快攻慢放,导出 GR 遥测。"""
    def __init__(self, thr_db=-6.0, atk_ms=1.0, rel_ms=80.0, fs=FS):
        self.thr = 10 ** (thr_db / 20.0)
        self.a_a = np.exp(-1.0 / (atk_ms * 1e-3 * fs))
        self.a_r = np.exp(-1.0 / (rel_ms * 1e-3 * fs))
        self.g = 1.0
        self.gr_db = 0.0
        self.active = False

    def process(self, x):
        out = np.empty_like(x)
        g = self.g
        for i, v in enumerate(x):
            target = min(1.0, self.thr / (abs(v) + 1e-12))
            a = self.a_a if target < g else self.a_r
            g = a * g + (1 - a) * target
            out[i] = v * g
        self.g = g
        self.gr_db = 20 * np.log10(max(g, 1e-9))
        self.active = self.gr_db < -0.5
        return out


class ClosedLoop:
    """mic → 前放 → [NHS tap + 陷波器组] → 前向增益 → 限幅 → 扬声器 → RIR → mic

    ⚠ 分块处理的正确性前提:块长(64)< 直达声延迟(样本)。构造时断言。
    """
    def __init__(self, rir, direct_delay, nhs, g_pre_db=20.0, g_fwd_db=0.0,
                 limiter=None, fs=FS):
        assert direct_delay > FRAME, f"直达延迟 {direct_delay} 须 > 块长 {FRAME}(闭环分块前提)"
        self.h = rir; self.nhs = nhs; self.fs = fs
        self.g_pre = 10 ** (g_pre_db / 20.0)
        self.g_fwd = 10 ** (g_fwd_db / 20.0)
        self.lim = limiter
        self.zi = np.zeros(len(rir) - 1)

    def run(self, source, g_fwd_ramp_db_per_s=None, hook=None):
        from scipy.signal import lfilter
        n = (len(source) // FRAME) * FRAME
        mic_log = np.zeros(n); out_log = np.zeros(n); tap_log = np.zeros(n)
        fb = np.zeros(FRAME)
        for i in range(0, n, FRAME):
            src = source[i:i+FRAME]
            mic = src + fb                               # 声学回授
            tap = mic * self.g_pre                       # 前放后 = NHS 检测 tap
            gr = {'out_lim_active': bool(self.lim.active), 'out_lim_gr_db': float(self.lim.gr_db)} \
                if self.lim is not None else {'out_lim_active': False, 'out_lim_gr_db': 0.0}
            y = self.nhs.process_frame(tap, gr)          # 陷波器组(检测在其入口)
            if g_fwd_ramp_db_per_s:
                self.g_fwd *= 10 ** (g_fwd_ramp_db_per_s * (FRAME / self.fs) / 20.0)
            y = y * self.g_fwd
            if self.lim is not None:
                y = self.lim.process(y)
            y = np.clip(y, -8.0, 8.0)                    # 数值安全钳(非声学元件,仅防 inf/nan)
            fb, self.zi = lfilter(self.h, [1.0], y, zi=self.zi)   # 扬声器→房间→麦
            mic_log[i:i+FRAME] = mic; out_log[i:i+FRAME] = y; tap_log[i:i+FRAME] = tap
            if hook:
                hook(i, tap, y)
        return mic_log, out_log, tap_log


def env_db(x, fs=FS, win_ms=20.0):
    """输出包络(dB) —— 判稳/判检出只看**输出信号**,不信内部旗标(假绿纪律)。"""
    w = max(1, int(win_ms * 1e-3 * fs))
    p = np.convolve(x**2, np.ones(w)/w, mode='same')
    return 10 * np.log10(p + 1e-30)


def narrowband_ratio(x, fs=FS):
    """输出信号的窄带集中度:最大 bin 占总能量比 —— 用于判"是否在啸"。"""
    if len(x) < 4096:
        return 0.0
    X = np.abs(np.fft.rfft(x[-8192:] * np.hanning(min(8192, len(x[-8192:])))))
    return float(X.max()**2 / (np.sum(X**2) + 1e-30))
