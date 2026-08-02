"""W1-P 宿主原型 · 实验套件(核心链 / B1-B12 / B-F1 / 误报 / 标定)
adaptive-dsp(第 3 实例)· 2026-08-01 · 全部产出 [L2/宿主仿真],不得升 [L1]

判定一律看**输出信号**(包络 + 窄带集中度),不信内部旗标 —— 假绿纪律。
"""
import numpy as np
from env import (image_source_rir, synth_speech, synth_music, synth_transients,
                 ClosedLoop, Limiter, env_db, FS, FRAME)
from nhs import NHS, Params

RNG = np.random.default_rng(0)
_RIR_CACHE = {}


def rir(rt60=0.35, seed=0):
    if (rt60, seed) not in _RIR_CACHE:
        _RIR_CACHE[(rt60, seed)] = image_source_rir(rt60=rt60, seed=seed)
    return _RIR_CACHE[(rt60, seed)]


class Bypass:
    events = []
    slots = []
    log = []
    def process_frame(self, x, gr=None): return x
    def duck_gain(self): return 1.0


def metrics(out, t_from=1.0):
    e = env_db(out)
    i0 = int(t_from * FS)
    seg = out[-8192:] * np.hanning(8192)
    X = np.abs(np.fft.rfft(seg))
    return dict(end_db=float(e[-2000]), peak_db=float(np.max(e[i0:])),
                nb=float(X.max()**2 / (np.sum(X**2) + 1e-30)),
                f_peak=float(np.argmax(X) * FS / 8192))


def howling(m, nb_thr=0.25, lvl_thr=-15.0):
    """判"仍在啸":输出末段窄带集中且电平高。纯输出侧判据。"""
    return (m['nb'] >= nb_thr) and (m['end_db'] >= lvl_thr)


# ------------------------------------------------------------ 场景
def scen_ramp(alg, dur=8.0, g0=-2.0, ramp=1.5, rt60=0.35, seed=0):
    h, d = rir(rt60, seed)
    src = 0.02 * np.random.default_rng(seed).normal(0, 1, int(dur * FS))
    lp = ClosedLoop(h, d, alg, g_pre_db=0, g_fwd_db=g0)
    _, out, tap = lp.run(src, g_fwd_ramp_db_per_s=ramp)
    return out, tap


def scen_step(alg, dur=6.0, g0=-6.0, gstep=+10.0, t_step=2.0, rt60=0.35, seed=0):
    """增益阶跃(移麦/推子)⇒ 快起振,GROWTH/PANIC 路的目标场景。"""
    h, d = rir(rt60, seed)
    src = 0.02 * np.random.default_rng(seed).normal(0, 1, int(dur * FS))
    lp = ClosedLoop(h, d, alg, g_pre_db=0, g_fwd_db=g0)
    n = (len(src)//FRAME)*FRAME
    out = np.zeros(n); tap = np.zeros(n)
    i_step = int(t_step * FS)
    from scipy.signal import lfilter
    fb = np.zeros(FRAME); zi = np.zeros(len(h)-1)
    gf = 10**(g0/20.0)
    for i in range(0, n, FRAME):
        if i == (i_step // FRAME) * FRAME:
            gf *= 10**(gstep/20.0)
        mic = src[i:i+FRAME] + fb
        t = mic * lp.g_pre
        y = alg.process_frame(t, {'out_lim_active': False, 'out_lim_gr_db': 0.0})
        y = np.clip(y * gf, -8.0, 8.0)
        fb, zi = lfilter(h, [1.0], y, zi=zi)
        out[i:i+FRAME] = y; tap[i:i+FRAME] = t
    return out, tap


def scen_pinned(alg, dur=10.0, g_fwd=50.0, loop_gain=3.0, thr_db=-6.0,
                rt60=0.35, seed=0, src=None, ramp=None):
    """★ B-F1 核心场景:输出限幅器入环 + 大前向增益 ⇒ tap 电平远低于 T_panic。

    ⚠ 构造要点(第一版做错过,留痕):**前向增益 ≠ 环路增益**。
      真实钉住场景 = 前向 +50dB **且** 声学回程 −50dB ⇒ 环路增益仅略大于 0dB。
      若把 RIR 留在 0dB 而前向给 +50dB,等于给环路 50dB 超额增益 —— 那不是"钉住的
      临界啸叫",是"没救的失控系统",8×18dB 陷波在数学上就不可能稳住它。
      故此处把 RIR 缩放到 (loop_gain − g_fwd) dB,使:
        环路增益 = g_fwd + RIR = loop_gain(略正,会起振后被限幅器钉住)
        tap 电平 ≈ 限幅阈 − g_fwd  (设计件算例:−6 − 50 = −56dBFS,低于 T_low)
    """
    h, d = rir(rt60, seed)
    h = h * 10 ** ((loop_gain - g_fwd) / 20.0)
    if src is None:
        # 种子必须远低于天花板:前向 +50dB 会把种子本身推到限幅器上,
        # 那样限幅器钉的是**底噪**不是啸叫(第一版此处做错,留痕)。
        src = 1e-5 * np.random.default_rng(seed).normal(0, 1, int(dur * FS))
    lim = Limiter(thr_db=thr_db)
    lp = ClosedLoop(h, d, alg, g_pre_db=0, g_fwd_db=g_fwd, limiter=lim)
    _, out, tap = lp.run(src, g_fwd_ramp_db_per_s=ramp)
    return out, tap


def scen_open(alg, material, dur=10.0):
    """开环(无反馈路径)误报套件:素材直接过 DUT,计挂陷次数。"""
    n = (len(material)//FRAME)*FRAME
    out = np.zeros(n)
    for i in range(0, n, FRAME):
        out[i:i+FRAME] = alg.process_frame(material[i:i+FRAME],
                                           {'out_lim_active': False, 'out_lim_gr_db': 0.0})
    return out


def n_engage(alg):
    return sum(1 for e in alg.events if str(e[1]).startswith('engage'))


def tap_level_dbfs(tap, t_from=0.5):
    seg = tap[int(t_from*FS):]
    return 20*np.log10(np.sqrt(np.mean(seg**2)) + 1e-30)


def react_time(alg, out, onset_t):
    """T_react:onset → 输出包络停止增长(取包络峰值时刻)。纯输出侧测量。"""
    e = env_db(out)
    i0 = int(onset_t*FS)
    if i0 >= len(e) - 10:
        return float('nan')
    seg = e[i0:]
    return float(np.argmax(seg) / FS)
