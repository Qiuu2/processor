"""W2-P · 度量层(度量定义 vs 合格阈值,**来源分离**)
adaptive-dsp-3 · 2026-08-01

⚠⚠ **来源分离(lead 2026-08-01 纠错:G.168 是错的标准族)**
  `G.168` = *Digital network echo cancellers* —— **线路/网络**回声消除器(电话网混合线圈回声)。
  我们做的是**声学**回声消除(房间扬声器→麦克风),回声路径延迟/ERL/尾长量级都不同。
  **我方 D0 雷达第 311 行早已写明**:"G.168 为线路 EC,**限值不可照搬**;G.161 系核验新增,
  验收规格须入列" —— 挖件时只读了雷达的 AEC 段、没读标准/合规段。

| 用途 | 来源 | 定级 |
|---|---|---|
| **度量定义**(ERLE/收敛/发散)| 教科书标准定义,与标准族无关 | [L3/解析] |
| **CSS 测试信号结构** | **G.168 Annex C 原文**(已入库,逐条核过,见下) | **[L1/标准原文]** |
| **合格阈值** | **须用 ITU-T P.340 / P.341(免提终端)+ G.161** | **[待核原文,未取到 ⇒ 留 None]** |

**纪律留痕**:lead 的错误指令 + 我守住纪律6(不编阈值)= 零损害。
若当时"合理地"填了几个看起来对的数,整个验收基线就是错的,且极难发现。**同一个地方不许松。**
"""
import numpy as np

__version__ = "W2P0.2"

# --- 验收阈值:已由 ITU-T P.341 原文回填(L4/待核 → **L1/标准原文**)------------
#   来源:research/sources/standards/ITU-T_P.341_2011_wideband_handsfree_terminals.pdf
#   ⚠ 我方已逐字核过原文(不采信转述)。
ACCEPT_THRESHOLDS = {
    'TCLw_nominal_db': (46.0, '[L1] P.341 §5.1.3.1.1「The TCLw shall be ≥ 46 dB at the nominal '
                              'setting of the user selectable volume control」'),
    'TCLw_maxvol_db':  (40.0, '[L1] 同款「With the volume control set to maximum, TCLw shall be ≥ 40 dB」'
                              ' + 附加义务:音量须每次通话后自动复位至标称,除非最大音量下也能保持 ≥46dB'),
    'stability_loss_db': (6.0, '[L1] P.341 §5.1.3.2「Stability loss shall be at least 6 dB at all '
                               'frequencies in the range 100 Hz to 8000 Hz **and at all settings of '
                               'the receiving volume control**」'),
    'ERLE_min_db': (None, '**无独立门**。ERLE 不等于 TCLw —— TCLw 是 Rin→Sout **整机**耦合损耗 '
                          '= 声学 ERL + AEC 线性级 ERLE + NLP 抑制,三者之和。'
                          'ERLE 的分配门须由 TCLw 分解导出,归 D13。**不得把 46dB 当 ERLE 门。**'),
}
# 测试信号(P.341 §5.1.3.1.2,与 G.168 Annex C 的 CSS 结构互证,且是**宽带 48kHz** 口径)
P341_TEST_SIGNAL = {
    'pn_points': (4096, '[L1] PN 序列 4096 点 @48kHz(P.501)'),
    'crest_db': (6.0, '[L1] crest factor 6dB,相位在 ±180° 随机交替'),
    'min_seqs': (4, '[L1]「at least four sequences of CSS」,总长 ≥1 秒'),
    'level_dbm0': (-3.0, '[L1] 测试信号电平 −3 dBm0'),
    'bandlimit_hz': ((50.0, 7000.0), '[L1]「band-limited to 50 Hz-7000 Hz」'),
}
# 双讲品质分档(P.340 Table 4)——**分级不是门**,供产品定档
P340_DOUBLETALK_GRADES = [
    ('Behaviour 1',  (None, 3.0)), ('Behaviour 2a', (3.0, 6.0)),
    ('Behaviour 2b', (6.0, 9.0)),  ('Behaviour 2c', (9.0, 12.0)),
    ('Behaviour 3',  (12.0, None)),
]
# 兼容旧名(此前全 None)
G168_THRESHOLDS = {k: v[0] for k, v in ACCEPT_THRESHOLDS.items()}

# --- CSS 参数:已对 G.168 Annex C 原文逐条核实(L4 → L1)-----------------------
CSS_SPEC = {
    'voiced_ms':  (50.0,  '[L1] Annex C.2.1「The duration of the signal amounts to 50 ms approximately」'),
    'pn_ms':      (200.0, '[L1] Annex C.2.1「M (close to 200 ms signal duration) may be appropriate」(自适应系统)'),
    'pause_ms':   (125.0, '[L1] Annex C.2.1「The length of the pause is chosen between 100 ms and 150 ms」⇒ 取中值'),
    'invert_alt': (True,  '[L1] Annex C.2.1「the repeated CS-sequence should be inverted in amplitude (phase shift by 180°)」'),
    'period_smp': (5600,  '[L1] 6.4.1.2「period of CSS (5600 for the single-talk portion, 6400 for double talk)」@8kHz = 700/800ms'),
}
def css(dur_s, fs=16000.0, seed=0, voiced_ms=50.0, pn_ms=200.0, pause_ms=125.0,
        invert_alt=True):
    """G.168 Annex C 复合源信号:voiced(P.50 人工语音)→ PN → pause,循环。

    ★ v0.2 勘正(对原文核实后):
      1. 三段时长 48.6/200/101ms → **50/200/125ms**,全部落在原文规定内(L4 → **L1**);
      2. **补上漏掉的一半**:原文要求"repeated CS-sequence should be **inverted in amplitude
         (phase shift by 180°)**" ⇒ 完整周期 = 2×~375ms ≈ 750ms,与 6.4.1.2 的
         **5600 样本 @8kHz = 700ms** 同量级。v0.1 只做了单个序列(349.6ms),**周期差 2×**。
    ⚠ G.168 CSS 定义在 **8kHz(电话带宽)**;本原型在 16kHz 上复现其**结构**,
      不等同于其电平/带宽规定。声学 EC 的合格阈值须用 P.340/P.341。
    """
    rng = np.random.default_rng(seed)
    nv, nn, np_ = [int(x*1e-3*fs) for x in (voiced_ms, pn_ms, pause_ms)]
    t = np.arange(nv)/fs
    f0 = 100.0
    voiced = sum((1.0/k**1.1)*np.sin(2*np.pi*f0*k*t) for k in range(1, 30))
    voiced *= np.hanning(nv); voiced /= (np.max(np.abs(voiced))+1e-12)
    # PN:恒幅谱 + 随机 ±1 相位(Annex C 式 C.2-1)
    M = 1 << int(np.ceil(np.log2(max(nn, 8))))
    W = np.ones(M//2+1); ph = rng.choice([0.0, np.pi], M//2+1)
    pn = np.fft.irfft(W*np.exp(1j*ph), M)[:nn]
    pn /= (np.max(np.abs(pn))+1e-12)
    seq = np.concatenate([voiced, pn*0.6, np.zeros(np_)])
    period = np.concatenate([seq, -seq]) if invert_alt else seq   # ★ 180° 反相的第二半
    reps = int(np.ceil(dur_s*fs/len(period)))
    return np.tile(period, reps)[:int(dur_s*fs)] * 0.5


def white_burst(dur_s, fs=16000.0, seed=0):
    """**非周期**激励(W2-F3:周期信号对整周期位移不敏感 ⇒ 延迟类 broken 必须用它)。"""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 0.3, int(dur_s*fs))
    env = np.clip(np.sin(2*np.pi*0.7*np.arange(len(x))/fs)+0.5, 0, None)
    return x*env


def erle_db(d, e, fs=16000.0, win_ms=100.0):
    """ERLE = 10log10( E[d²] / E[e²] );d=未消回声(麦克风),e=残余。[L3/解析,标准定义]"""
    w = max(1, int(win_ms*1e-3*fs))
    k = np.ones(w)/w
    Pd = np.convolve(d**2, k, mode='same'); Pe = np.convolve(e**2, k, mode='same')
    return 10*np.log10((Pd+1e-20)/(Pe+1e-20))


def steady_erle(d, e, fs=16000.0, from_s=None):
    """稳态 ERLE:取后 1/3 段的中位(避开收敛期)。"""
    i0 = int((from_s if from_s is not None else len(d)/fs*2/3)*fs)
    return float(np.median(erle_db(d[i0:], e[i0:], fs)))


def converge_time_s(d, e, fs=16000.0, target_db=None, frac=0.9):
    """收敛时间:ERLE 首次达到 (稳态 ERLE × frac) 的时刻。
    ⚠ 若 G.168 规定的是绝对门(target_db),取得原文后改用绝对门。"""
    E = erle_db(d, e, fs)
    tgt = target_db if target_db is not None else steady_erle(d, e, fs)*frac
    idx = np.where(E >= tgt)[0]
    return float(idx[0]/fs) if len(idx) else float('nan')


def nearend_loss_db(near_ref, e, fs=16000.0, mask=None):
    """双讲近端损伤:近端原信号 vs 残余中保留的近端 —— 越接近 0 越好。
    只在 mask(双讲段)上算。"""
    if mask is None:
        mask = np.ones(len(e), bool)
    a = near_ref[mask]; b = e[mask]
    if len(a) < 16: return float('nan')
    g = np.dot(a, b)/(np.dot(a, a)+1e-20)      # 最优标量增益 = 近端被保留的比例
    return float(20*np.log10(max(abs(g), 1e-9)))


def divergence(e, fs=16000.0):
    """发散检测:残余能量后段是否显著高于前段(AEC 跑飞的直接证据)。"""
    n = len(e)//3
    p0 = np.mean(e[:n]**2)+1e-20; p2 = np.mean(e[-n:]**2)+1e-20
    return float(10*np.log10(p2/p0))
