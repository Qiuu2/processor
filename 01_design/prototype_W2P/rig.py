"""W2-P · AEC 台架:远端 → 扬声器 → RIR(回声路径)→ 麦克风;近端语音叠加。"""
import numpy as np, sys
sys.path.insert(0, '../prototype_W1P')
from env import image_source_rir, synth_speech
from scipy.signal import lfilter, resample_poly

FS = 16000.0
BLK = 128
_RIR = {}

def echo_path(seed=0, rt60=0.35, fs=FS, mic=(1.2,1.0,1.5)):
    """回声路径 RIR(复用 W1 的 image-source;重采到 16k)。"""
    key=(seed,rt60,mic)
    if key not in _RIR:
        h48, d = image_source_rir(rt60=rt60, seed=seed, mic=mic)
        h = resample_poly(h48, 1, 3)
        h = h/ (np.max(np.abs(h))+1e-12) * 0.6
        _RIR[key]=(h,int(d/3))
    return _RIR[key]

def run_aec(alg, far, near=None, seed=0, rt60=0.35, mic=(1.2,1.0,1.5),
            nlp=None, blk=BLK, ref=None):
    """返回 (d 麦克风信号, e 残余, echo 纯回声, near 近端)。
    ⚠ 构造要点(第一版做错过,留痕):`far` 生成回声,`ref` 是喂给 AEC 的参考。
      二者**必须可分**,否则"参考错位/接错"类 broken 版根本没错位——
      我第一版用同一个 far 同时生成回声与参考,于是错位 1000ms 仍得基线 ERLE。"""
    h, _ = echo_path(seed, rt60, mic=mic)
    echo = lfilter(h, [1.0], far)
    ref = far if ref is None else ref[:len(far)]
    near = np.zeros_like(far) if near is None else near[:len(far)]
    d = echo + near
    n = (len(far)//blk)*blk
    e_out = np.zeros(n); y_out = np.zeros(n)
    for i in range(0, n, blk):
        x = ref[i:i+blk]; dd = d[i:i+blk]
        e = alg.process(x, dd)
        y = dd - e
        if nlp is not None:
            e = nlp.process(e, y)
        e_out[i:i+blk] = e; y_out[i:i+blk] = y
    return d[:n], e_out, echo[:n], near[:n]
