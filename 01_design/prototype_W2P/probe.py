"""W2-P · C-8f/C-8g 探针法(架构侧 v0.9 新立,零实测,挂 V-17)· [L2/宿主仿真]

⭐ 为什么静态纹波测不到这条(架构侧机理,本件要验的就是它):
   NLMS 更新  ŵ ← ŵ + μ·e·u/(uᵀu)  中的 **e 含啸叫/探针**
   ⇒ 啸叫经 ⟨e,u⟩ 泄漏进系数 ⇒ 抵消信号 ŵᵀu 随之抖动
   ⇒ **零均值、但方差 ∝ μ 的环路增益调制**。
   静态/空闲响应测量对此**结构性失明**(空闲时 e 里没有啸叫)。

C-8f:向**本地环路**注持续探针音,元件**正常自适应**运行,
      测 tap 处探针幅度相对**旁路基线**的 max ⇒ 门 ≤ +0.25dB(计入同一 1.0dB 合计)。
C-8g:同探针扫电平 T_low_gr→0dBFS,变化 ⇒ 门 ≤ ±1.0dB。
"""
import numpy as np, sys
from scipy.signal import lfilter
sys.path.insert(0,'../prototype_W1P')
from env import image_source_rir
from scipy.signal import resample_poly

FS = 16000.0
BLK = 128
__version__ = "W2P0.3"


def _paths(seed=0):
    """⚠ 必须按**最大频响**归一化,不是时域峰值。
    环路增益由 |H(f)| 的峰决定;按时域峰归一会让 |H(f)|_max ≫ 1 ⇒ 环路远比设定值不稳。
    这是 W1-F8 同款错误,我在本文件里又犯了一次 —— 留痕。"""
    h48, _ = image_source_rir(rt60=0.35, seed=seed)
    h = resample_poly(h48, 1, 3)
    Hf = np.abs(np.fft.rfft(h, 1 << 15))
    return h/(Hf.max()+1e-30)


def probe_run(alg, probe_hz=1500.0, probe_dbfs=-30.0, dur=8.0, far=None,
              loop_gain_db=-6.0, adapt=True, seed=0, warm_s=3.0, ret_mask=False,
              far_gate=None):
    """本地扩声环路 + 远端回声 + 持续探针音(**台架 v2:物理自洽**)。

    ⚠ v1 的两个混淆(自查抓出,留痕):
      ① 基线用"旁路 AEC" ⇒ 远端回声完全不消 ⇒ 环路内容与激活态**根本不同**,
         测到的是"消不消回声"的差,不是"自适应调制"的差;
      ② echo 与声学回授被写成两条独立路径 ⇒ 扬声器放的东西和麦收的东西对不上。
    v2 修正:
      扬声器 spk = 远端 + 本地扩声输出;麦 mic = RIR*spk + 探针 + 近端 —— **一条路径**;
      **基线 = 同一个已收敛 AEC 但系数冻结**(adapt=False)⇒ 平均抵消量相同,
      唯一差别就是**自适应本身** ⇒ 正对 C-8f 要测的泄漏机理。
    """
    h = _paths(seed)
    n = int(dur*FS)//BLK*BLK
    t = np.arange(n)/FS
    probe = 10**(probe_dbfs/20.0)*np.sin(2*np.pi*probe_hz*t)
    if far is None:
        far = np.random.default_rng(1).normal(0, 0.2, n)
    far = far[:n].copy()
    if far_gate is not None:                      # 门控远端:制造"远端静默"段(补测②所需)
        on, off = far_gate
        tt = np.arange(n)/FS
        far *= ((tt % (on+off)) < on).astype(float)
    g = 10**(loop_gain_db/20.0)
    fb = np.zeros(BLK); zi = np.zeros(len(h)-1)
    amps = []; fmask = []
    W = 2*BLK; win = np.hanning(W); k = int(round(probe_hz/FS*W))
    hist = np.zeros(W)
    for i in range(0, n, BLK):
        mic = fb + probe[i:i+BLK]                       # 麦 = 声学回授(含远端回声)+ 探针
        tap = mic
        if alg is None:
            e = tap
        elif adapt or i < int(warm_s*FS):
            e = alg.process(far[i:i+BLK], tap)          # 正常自适应(冻结态也需先收敛)
        else:
            Wsave = alg.W.copy()
            e = alg.process(far[i:i+BLK], tap)
            alg.W = Wsave                               # 冻结:用收敛系数滤波,不更新
        spk = far[i:i+BLK] + e*g                        # ★ 扬声器 = 远端 + 本地扩声(一条路径)
        fb, zi = lfilter(h, [1.0], spk, zi=zi)
        hist = np.roll(hist, -BLK); hist[-BLK:] = tap
        if i >= max(W, int(warm_s*FS)):
            X = np.fft.rfft(hist*win)
            amps.append(20*np.log10(abs(X[k])+1e-20))
            fmask.append(float(np.sqrt(np.mean(far[i:i+BLK]**2))))
    return (np.array(amps), np.array(fmask)) if ret_mask else np.array(amps)


def c8f_series(alg_factory, **kw):
    """返回 (差值序列 d, 远端块 RMS) —— 供补测②/③ 对**同一批数据**重新出统计。"""
    base, fm = probe_run(alg_factory(), adapt=False, ret_mask=True, **kw)
    act, _ = probe_run(alg_factory(), adapt=True, ret_mask=True, **kw)
    m = min(len(base), len(act), len(fm))
    return act[:m]-base[:m], fm[:m]


def c8f(alg_factory, **kw):
    """C-8f:**同一收敛元件 自适应 vs 冻结**,tap 处探针幅度的 max 抬升(dB)。"""
    d, _ = c8f_series(alg_factory, **kw)
    return float(np.max(d)), float(np.median(d)), float(np.std(d))


def c8f_windowed(d, win_blocks):
    """C-8f′ 窗平均后再取 max(窗内平均 ⇒ 抑制零均值抖动的瞬时尖峰)。"""
    if win_blocks <= 1: return float(np.max(d))
    k = np.ones(win_blocks)/win_blocks
    return float(np.max(np.convolve(d, k, mode='valid')))


def c8g(alg_factory, levels=(-65.0, -45.0, -25.0, -10.0, 0.0), **kw):
    """C-8g:探针电平扫 T_low_gr→0dBFS,测 max 抬升随电平的变化范围(dB)。"""
    out = []
    for L in levels:
        d, _ = c8f_series(alg_factory, probe_dbfs=L, **kw)
        out.append((L, float(np.max(d)), float(np.median(d)), float(np.std(d))))
    vals = [o[1] for o in out]
    return out, float(max(vals)-min(vals))
