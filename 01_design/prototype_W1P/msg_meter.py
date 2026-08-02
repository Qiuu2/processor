"""瞬时 MSG 表 —— **取代起振检测器**作为闭环台架的因变量。

═══════════════════════════════════════════════════════════════════════════
D6-b · 这个数到底在测什么(报数前必须先写这两句)
═══════════════════════════════════════════════════════════════════════════
**被测对象**:`MSG(t)` = 在 t 时刻的陷波状态下,**环路开环增益达到 1 所需的 G**,
              即闭环极点触及单位圆的临界增益。它是**环路稳定性边界**的度量。
              `margin(t) = MSG(t) − G` = 当前工作点距该边界的 dB 数。

**混淆面(三条,必须随数一起报)**:
  1. **它不是"听得见啸叫"的度量**。`margin<0` 说的是**极点已经出圈**,而可闻啸叫还要
     经过建立时间(∝ 1/margin,margin→0 时发散)。⇒ **MSG(t) 给的是失稳【起点】,
     音频上的啸叫区间会滞后**。二者不可混用一个名字。
  2. **它是模型量不是测量量**:靠"我们精确知道 F(ω) 与陷波系数"成立。台架里 F 已知
     ⇒ 精确;真机上 F 未知 ⇒ **本表不可移植到板上**,板上只能用检测器/实测环路扫描。
  3. **频带口径决定数值**。r51 实测:白噪 RIR 台架的全带最高临界点常在 8 kHz 以上,
     而 NHS 旁链只到 8 kHz ⇒ **带内 MSG 与全带 MSG 可差 0 ~ 2.2 dB**(六条种子)。
     ⇒ **本表恒返回两列(带内 / 全带),不提供"一个 MSG"的接口。**

D6(工作点向量):每个 MSG 数附 `{fs, frame, nfft, band, G, 陷波状态来源}`。
[L2/宿主仿真]
"""
import numpy as np

FS_DEFAULT = 48000.0
BAND_DET = (100.0, 8000.0)        # 检测带(= NHS 旁链 16 kHz 抽取的可及范围)
BAND_FULL = (20.0, 23900.0)       # 全带(= 台架 F(z) 的真实作用范围)


def _crit_max(f, H, lo, hi):
    """相位过零点上的 max 20log10|H|。**与 clrig._crit_from_H 同式**(不 unwrap)。
    返回 (max_dB, f_at_max, n_crit)。"""
    m = (f >= lo) & (f <= hi)
    fb, Hb = f[m], H[m]
    ph = np.angle(Hb)
    sg = np.sign(ph)
    idx = np.where((sg[:-1] * sg[1:] < 0) & (np.abs(ph[:-1] - ph[1:]) < np.pi))[0]
    if len(idx) == 0:
        return float('-inf'), float('nan'), 0
    t = ph[idx] / (ph[idx] - ph[idx + 1])
    fc = fb[idx] + t * (fb[idx + 1] - fb[idx])
    mc = np.abs(Hb[idx]) + t * (np.abs(Hb[idx + 1]) - np.abs(Hb[idx]))
    mdb = 20 * np.log10(mc + 1e-30)
    j = int(np.argmax(mdb))
    return float(mdb[j]), float(fc[j]), int(len(fc))


class MSGMeter:
    """h_eff 固定(台架的 F(z) 不变),陷波状态随时间变 ⇒ 只重算 N(ω)。"""

    def __init__(self, h_eff, fs=FS_DEFAULT, nfft=1 << 18):
        # ⚠ nfft 默认 2^18 是**实测收敛结果**,不是拍的(r53 §C,T60=0.5/seed2/8陷波,最难一档):
        #     2^15 −7.163 / 2^16 −7.332 / 2^17 −7.422 / **2^18 −7.4239** /
        #     2^19 −7.4249 / 2^20 −7.4254   ⇒ 2^18 起变化 ≤0.001 dB,单次 0.035 s。
        #   2^15 的偏差达 **0.26 dB 且系统性偏乐观**(临界点越密偏差越大 ⇒ T60 越大越差)
        #   ⇒ 用粗网格会把"MSG 更高"读成算法收益。**不得为省时间降 nfft。**
        self.fs = float(fs)
        self.nfft = int(nfft)
        self.f = np.fft.rfftfreq(self.nfft, 1 / self.fs)
        self.H = np.fft.rfft(np.asarray(h_eff, float), self.nfft)
        w = 2 * np.pi * self.f / self.fs
        self._z1 = np.exp(-1j * w)
        self._z2 = self._z1 ** 2
        self._cache = {}

    # ---------- 陷波器组频响 ----------
    def notch_resp(self, slots, g_duck_db=0.0):
        """N(ω) = 10^(g_duck/20) · Π_{非 FREE 槽} (b0+b1z⁻¹+b2z⁻²)/(a0+a1z⁻¹+a2z⁻²)
        ⚠ `g_duck` 是**宽带兜底衰减**,`nhs.process_frame` 在陷波器之后施加
          ⇒ 它同样在环内,**必须计入**,否则槽位耗尽时本表会系统性低估 MSG。"""
        N = np.full(len(self.f), 10.0 ** (g_duck_db / 20.0), dtype=complex)
        for s in slots:
            if s.st == 0:                      # NotchSlot.FREE
                continue
            b, a = s.b, s.a
            N = N * ((b[0] + b[1] * self._z1 + b[2] * self._z2) /
                     (a[0] + a[1] * self._z1 + a[2] * self._z2))
        return N

    @staticmethod
    def state_key(slots, g_duck_db=0.0):
        """陷波状态指纹(命中即复用)。含系数本体,系数变了 key 必变。"""
        parts = [round(float(g_duck_db), 9)]
        for s in slots:
            parts.append(int(s.st))
            if s.st != 0:
                parts.extend(np.round(np.concatenate([s.b, s.a]), 12).tolist())
        return tuple(parts)

    # ---------- 主接口 ----------
    def msg(self, slots=(), g_duck_db=0.0, bands=None):
        """返回 {band_name: dict(msg_db, f_crit, n_crit)}。
        **恒返回两列**(见模块头 混淆面 3),不提供单值接口。"""
        bands = bands or {'in': BAND_DET, 'full': BAND_FULL}
        key = self.state_key(slots, g_duck_db)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        N = self.notch_resp(slots, g_duck_db)
        HN = self.H * N
        out = {}
        for nm, (lo, hi) in bands.items():
            mdb, fc, nc = _crit_max(self.f, HN, lo, hi)
            out[nm] = dict(msg_db=-mdb, f_crit=fc, n_crit=nc)
        self._cache[key] = out
        return out

    def margin(self, G_db, slots=(), g_duck_db=0.0, bands=None):
        """margin(t) = MSG(t) − G。**margin < 0 ⇒ 环路极点已出单位圆**(≠ 已听见啸叫)。"""
        m = self.msg(slots, g_duck_db, bands)
        return {k: v['msg_db'] - G_db for k, v in m.items()}


# ---------------------------------------------------------------- HOP / TRI
def intervals(flag, dt):
    """由逐槽布尔序列取区间 [(t_start, t_end), ...]。dt = 每个采样点代表的秒数。"""
    out = []
    st = None
    for i, v in enumerate(flag):
        if v and st is None:
            st = i
        elif not v and st is not None:
            out.append((st * dt, i * dt))
            st = None
    if st is not None:
        out.append((st * dt, len(flag) * dt))
    return out


def hop_tri(flag, dt):
    """HOP 式(112)= Σtᵢ/T ;TRI 式(113)= Σtᵢ/N_HO。
    (van Waterschoot & Moonen 2011 Proc.IEEE 综述)
    ⚠ **偏离声明**:原文的啸叫区间识别是①听②目视的**人工**过程;本实现用
      `margin(t) < 0`(模型 ground truth)替代 ⇒ **更客观但口径不同**,
      且按模块头混淆面 1,本实现给的是**失稳起点**区间,不是可闻啸叫区间。
    返回 (HOP, TRI, N_HO, T_total)。N_HO=0 时 TRI 报 nan,**不报 0**。"""
    T = len(flag) * dt
    iv = intervals(flag, dt)
    tot = sum(b - a for a, b in iv)
    return (tot / T if T > 0 else float('nan'),
            (tot / len(iv)) if iv else float('nan'),
            len(iv), T)
