"""r68 · sd_meter.py 自测 —— 已知答案算例 + 变异测试。

⚠ 本脚本**不预写结论**:通过/未通过由末尾按实测结果计算后写入。
⚠ 参照实现(analytic_sd / erb_ref)**故意与 sd_meter 分开写**:变异测试会替换
  sd_meter 内部函数,参照若共用同一份代码就会跟着一起错 = 同实现自比 = 假绿。
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sd_meter as sd  # noqa: E402

TRAPZ = getattr(np, "trapezoid", None) or np.trapz

FS = 48000.0
DUR = 4.0
SEED = 20260803
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r68_sd_selftest_out.txt")


# ─────────────────────────────────────────────── 参照实现(独立于被测件)
def erb_ref(f):
    """Glasberg–Moore ERB。**故意重复实现**,理由见模块头。"""
    return 24.7 * (4.37 * np.asarray(f, float) / 1000.0 + 1.0)


def analytic_sd(b, a, lo, hi, fs=FS, n=400001):
    """直接对定义式积分(连续网格 + freqz),**完全不走 STFT**。

    SD = sqrt( ∫ w(f)·dev(f)² df / ∫ w(f) df ),dev(f) = 20log₁₀|H(f)|。
    对**线性时不变、且源为平稳宽带**的处理,这是 SD 的解析答案。"""
    f = np.linspace(float(lo), float(hi), n)
    _, h = signal.freqz(b, a, worN=f, fs=fs)
    dev = 20.0 * np.log10(np.abs(h) + 1e-300)
    wt = 1.0 / erb_ref(f)
    return float(np.sqrt(TRAPZ(wt * dev * dev, f) / TRAPZ(wt, f)))


def peaking(f0, gain_db, bw_hz, fs=FS):
    """RBJ cookbook peaking EQ(gain_db<0 ⇒ 有限深度陷波,= NHS 实际用的形态)。
    在 f0 处 |H| 恰为 gain_db。"""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2.0 * (f0 / bw_hz))
    b = np.array([1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A])
    return b / a[0], a / a[0]


def broadband_power_cost_db(b, a, fs=FS, n=200001):
    """白噪过该滤波器的**全带功率代价**(dB,正数 = 损失)。"""
    f = np.linspace(0.0, fs / 2.0, n)
    _, h = signal.freqz(b, a, worN=f, fs=fs)
    ratio = TRAPZ(np.abs(h) ** 2, f) / (fs / 2.0)
    return float(-10.0 * np.log10(ratio))


# ─────────────────────────────────────────────── 台架信号
_rng = np.random.default_rng(SEED)
SRC = _rng.standard_normal(int(FS * DUR))


def measure(proc, src=SRC):
    return sd.sd_measure(processed=proc, source=src, fs=FS)


# ─────────────────────────────────────────────── 已知答案算例
def check_A():
    """A · 恒等处理 ⇒ SD 必须 = 0。"""
    r = measure(SRC.copy())
    vals = [r.band_in.mean_db, r.band_in.max_db, r.band_full.mean_db, r.band_full.max_db]
    ok = all(abs(v) < 1e-12 for v in vals)
    return ok, [f"  恒等: in(mean/max)={vals[0]:.3e}/{vals[1]:.3e}  "
                f"full(mean/max)={vals[2]:.3e}/{vals[3]:.3e} dB   判据 |SD|<1e-12"]


def check_B():
    """B · 全带平坦衰减 X dB ⇒ SD 必须 = X(两列、mean 与 max 全部)。

    推论核对(派单要求自己核):d = g·v,g = 10^(−X/20) ⇒ S_d = g²S_v
    ⇒ 10log₁₀(S_d/S_v) ≡ 20log₁₀ g ≡ −X ⇒ 平方后 X² ⇒ SD = X·sqrt(Σp)。
    **仅当 Σp = 1(归一化)时才等于 X** ⇒ 本算例即归一化的定义性测试。"""
    lines, ok = [], True
    for X in (0.5, 6.0, 20.0, 40.0):
        r = measure(SRC * 10.0 ** (-X / 20.0))
        vals = [r.band_in.mean_db, r.band_in.max_db, r.band_full.mean_db, r.band_full.max_db]
        e = max(abs(v - X) for v in vals)
        ok &= e < 1e-9
        lines.append(f"  衰减 {X:5.1f} dB ⇒ in={vals[0]:.9f}/{vals[1]:.9f}  "
                     f"full={vals[2]:.9f}/{vals[3]:.9f}  max|err|={e:.2e}  判据<1e-9")
    r = measure(SRC * 10.0 ** (6.0 / 20.0))
    e = abs(r.band_in.mean_db - 6.0)
    ok &= e < 1e-9
    lines.append(f"  提升 +6.0 dB ⇒ in.mean={r.band_in.mean_db:.9f}  err={e:.2e} "
                 f"(SD 对方向盲,提升与衰减同值 —— 见 M7)")
    return ok, lines


def check_C():
    """C · 单个窄陷波 vs 平坦衰减。**两种"同等"口径结论相反,都报。**"""
    b, a = peaking(1000.0, -20.0, 100.0)
    rn = measure(signal.lfilter(b, a, SRC))
    sd_notch = rn.band_in.mean_db
    lines = []

    # C1 · 同等【MSG 收益】(= 同等深度 20 dB):文献选陷波的**真实**理由
    sd_flat_depth = measure(SRC * 10.0 ** (-20.0 / 20.0)).band_in.mean_db
    ok1 = sd_notch < 0.3 * sd_flat_depth
    lines.append(f"  C1 同等深度 20 dB(= 同等 MSG 收益):")
    lines.append(f"     陷波(1kHz, BW100, −20dB) SD_in={sd_notch:.4f} dB   "
                 f"平坦 −20 dB SD_in={sd_flat_depth:.4f} dB   "
                 f"比值={sd_notch / sd_flat_depth:.4f}  判据<0.30")

    # C2 · 同等【全带功率代价】(= 派单原文的口径)
    cost = broadband_power_cost_db(b, a)
    sd_flat_cost = measure(SRC * 10.0 ** (-cost / 20.0)).band_in.mean_db
    ok2 = sd_notch > sd_flat_cost
    lines.append(f"  C2 同等全带功率代价({cost:.5f} dB):")
    lines.append(f"     陷波 SD_in={sd_notch:.4f} dB   平坦 SD_in={sd_flat_cost:.5f} dB   "
                 f"陷波/平坦={sd_notch / sd_flat_cost:.1f}×  判据: 陷波 > 平坦")
    lines.append("     ⚠ 派单说「陷波 SD 应远小于同等【功率代价】的平坦衰减」 —— **实测相反,且这不是 bug**。")
    lines.append(f"       SD 是对数谱偏差的**加权均方根**,不是功率度量:窄陷波功率代价近乎为 0")
    lines.append(f"       ({cost:.5f} dB)但在窄带内造成 20 dB 的对数偏差 ⇒ SD 必然更大。")
    lines.append(f"       文献选陷波的理由是 **C1(同等 MSG 收益下)**,不是同等功率代价。")
    return ok1 and ok2, lines


def check_E():
    """E · ERB 加权的方向性:等绝对带宽的陷波,低频处 SD 必须显著更大。

    w ∝ 1/ERB ⇒ 权重密度比 = ERB(5000)/ERB(500)。这是**唯一能钉死加权函数**的算例
    (A/B 对任何归一化权重都成立 ⇒ 单靠 A/B 无法发现权重被换成常数)。"""
    out = {}
    for f0 in (500.0, 5000.0):
        b, a = peaking(f0, -20.0, 100.0)
        out[f0] = (measure(signal.lfilter(b, a, SRC)).band_in.mean_db,
                   analytic_sd(b, a, 300.0, 6500.0))
    sd_ratio = out[500.0][0] / out[5000.0][0]
    ana_ratio = out[500.0][1] / out[5000.0][1]
    erb_ratio = float(np.sqrt(erb_ref(5000.0) / erb_ref(500.0)))
    ok = abs(sd_ratio / ana_ratio - 1.0) < 0.10
    return ok, [
        f"  陷波@500Hz  SD_in={out[500.0][0]:.4f} dB (解析 {out[500.0][1]:.4f})",
        f"  陷波@5000Hz SD_in={out[5000.0][0]:.4f} dB (解析 {out[5000.0][1]:.4f})",
        f"  实测比={sd_ratio:.4f}  解析比={ana_ratio:.4f}  偏差={sd_ratio / ana_ratio - 1:+.2%}  判据<10%",
        f"  (纯 ERB 密度预测 sqrt(ERB(5k)/ERB(500))={erb_ratio:.4f};常数权重会给 ≈1.0)",
    ]


def check_G():
    """G · 与定义式的**解析积分**对拍(独立代码路径,不走 STFT)。

    宽陷波(BW=500 Hz ≫ Hann 主瓣 4·fs/M=46.9 Hz)⇒ 窗平滑可忽略 ⇒ 应紧密吻合。"""
    b, a = peaking(1500.0, -20.0, 500.0)
    r = measure(signal.lfilter(b, a, SRC))
    lines, ok = [], True
    for nm, meas, (lo, hi) in (("in", r.band_in.mean_db, (300.0, 6500.0)),
                               ("full", r.band_full.mean_db, (0.0, FS / 2.0))):
        ana = analytic_sd(b, a, lo, hi)
        rel = meas / ana - 1.0
        ok &= abs(rel) < 0.05
        lines.append(f"  {nm:4s}[{lo:.0f}-{hi:.0f}Hz]: 实测={meas:.4f}  解析={ana:.4f}  "
                     f"偏差={rel:+.2%}  判据<5%")
    lines.append(f"  (两列不同值本身即混淆面 4 的实证:同一处理,in/full 差 "
                 f"{r.band_in.mean_db / r.band_full.mean_db:.2f}×)")
    return ok, lines


def check_H():
    """H · 频带选择性:带外(10 kHz)陷波必须几乎不进 `in` 列,但要进 `full` 列。"""
    b, a = peaking(10000.0, -20.0, 200.0)
    r = measure(signal.lfilter(b, a, SRC))
    ana_in = analytic_sd(b, a, 300.0, 6500.0)
    ana_full = analytic_sd(b, a, 0.0, FS / 2.0)
    ok = (r.band_in.mean_db < 0.2 * r.band_full.mean_db
          and abs((r.band_in.mean_db / r.band_full.mean_db) / (ana_in / ana_full) - 1.0) < 0.15)
    return ok, [
        f"  陷波@10kHz(在 300–6500 之外): SD_in={r.band_in.mean_db:.4f}  "
        f"SD_full={r.band_full.mean_db:.4f} dB",
        f"  实测 in/full={r.band_in.mean_db / r.band_full.mean_db:.4f}  "
        f"解析 in/full={ana_in / ana_full:.4f}  判据: in<0.2·full 且比值吻合<15%",
    ]


def check_I():
    """I · 静音源 ⇒ 必须报 N/A(nan)+ 原因,**不得报 0**。"""
    z = np.zeros(int(FS * 0.5))
    r = sd.sd_measure(processed=z, source=z, fs=FS)
    ok = (np.isnan(r.band_in.mean_db) and np.isnan(r.band_full.mean_db)
          and r.n_frames_used == 0 and bool(r.note))
    return ok, [f"  全零源: SD_in={r.band_in.mean_db}  帧 {r.n_frames_used}/{r.n_frames}  "
                f"note={r.note!r}   判据: nan + 0 帧 + 有 note"]


def check_J():
    """J · 接口纪律:**不得存在"一个 SD"的出口**。"""
    r = measure(SRC * 0.5)
    lines, ok = [], True
    for obj, nm in ((r, "SDResult"), (r.band_in, "SDBand")):
        try:
            float(obj)
            ok = False
            lines.append(f"  {nm}: float() **没有报错** ⇒ 存在单值出口 ⇒ 判据失败")
        except TypeError as e:
            lines.append(f"  {nm}: float() 正确拒绝 —— {str(e)[:60]}…")
    for attr in ("band_in", "band_full"):
        for sub in ("mean_db", "max_db"):
            ok &= hasattr(getattr(r, attr), sub)
    lines.append(f"  两列 × (mean,max) 四个数均存在: "
                 f"{r.band_in.mean_db:.4f}/{r.band_in.max_db:.4f} | "
                 f"{r.band_full.mean_db:.4f}/{r.band_full.max_db:.4f}")
    return ok, lines


def check_K():
    """K · 工作点向量完整性(派单要求 4)。"""
    r = measure(SRC * 0.5)
    need = ["fs", "M", "hop", "overlap", "window", "band_in", "band_full",
            "floor_db", "gate_db", "erb_formula", "cite_sd", "deviation",
            "ansi_table2_variant", "t_window", "t_window_lit",
            "t_window_lit_binding", "frame_time_def", "weighting_law",
            "normalize", "psd_est", "integration", "report", "time_align",
            "provenance"]
    miss = [k for k in need if k not in r.workpoint]
    ok = not miss and r.workpoint["deviation"] is not None  # 48 kHz 必须自报偏离
    return ok, [f"  {len(need)} 个必备键,缺失: {miss or '无'}",
                f"  M={r.workpoint['M']} hop={r.workpoint['hop']} "
                f"win={r.workpoint['window']} overlap={r.workpoint['overlap']}",
                f"  自报偏离: {r.workpoint['deviation']}",
                f"  ANSI 变体: {r.workpoint['ansi_table2_variant']}"]


def check_L():
    """L · 平均时间窗:分段已知答案。

    信号前半衰减 6 dB、后半衰减 20 dB。取窗使窗内帧**整帧**落在同一段
    ⇒ SD 必须精确回读该段的衰减值(而不是两段的混合)。
    同时验证:**原文的 30–60 s 窗不会被自动套用**,且套错时是"响的"(N/A + 原因)。"""
    rng = np.random.default_rng(SEED + 1)
    n = int(FS * 12.0)
    src = rng.standard_normal(n)
    g = np.where(np.arange(n) < n // 2, 10.0 ** (-6.0 / 20.0), 10.0 ** (-20.0 / 20.0))
    proc = src * g

    def m(tw):
        return sd.sd_measure(processed=proc, source=src, fs=FS, t_window=tw)

    r1, r2, rall = m((0.5, 5.5)), m((6.5, 11.5)), m(None)
    ok = (abs(r1.band_in.mean_db - 6.0) < 1e-9 and abs(r2.band_in.mean_db - 20.0) < 1e-9
          and 6.0 < rall.band_in.mean_db < 20.0
          and r1.n_frames_used < rall.n_frames_used)

    # 原文窗 (30,60) 套到 12 s 台架上 ⇒ 必须报 N/A + 原因,**不得静默给个数**
    rlit = m(sd.T_WINDOW_JAES2010)
    ok &= np.isnan(rlit.band_in.mean_db) and rlit.n_frames_used == 0 and bool(rlit.note)

    return ok, [
        f"  窗 0.5–5.5 s (前半, 衰减 6 dB) : SD_in={r1.band_in.mean_db:.9f} "
        f"帧 {r1.n_frames_used}/{r1.n_frames}   判据 |SD−6|<1e-9",
        f"  窗 6.5–11.5 s(后半, 衰减 20 dB): SD_in={r2.band_in.mean_db:.9f} "
        f"帧 {r2.n_frames_used}/{r2.n_frames}  判据 |SD−20|<1e-9",
        f"  全时长(默认 None)             : SD_in={rall.band_in.mean_db:.4f} "
        f"帧 {rall.n_frames_used}/{rall.n_frames}  判据 6<SD<20(两段混合)",
        f"  原文窗 {sd.T_WINDOW_JAES2010} 套到 12 s 台架: SD_in={rlit.band_in.mean_db} "
        f"帧 {rlit.n_frames_used}/{rlit.n_frames}",
        f"    note={rlit.note!r}",
        f"    ⇒ 原文窗**未被自动套用**;误套时报 N/A + 原因,不静默出数。",
    ]


def check_N():
    """N · 工作点的**来源身份证**:原文规定的 vs 我们选的,必须分得开。"""
    wp = measure(SRC * 0.5).workpoint
    prov = wp["provenance"]
    tags = ("原文·偏离", "原文·同", "原文", "我方选择", "我方推导")
    bad = [k for k, v in prov.items() if not v.startswith(tags)]
    ok = (not bad
          and wp["t_window"] is None                                # 默认不套原文窗
          and tuple(wp["t_window_lit"]) == (30.0, 60.0)             # 原文值已留痕
          and prov["t_window_lit"].startswith("原文")
          and prov["t_window"].startswith("我方选择")
          and bool(wp["t_window_lit_binding"]))
    counts = {}
    for v in prov.values():
        t = next(x for x in tags if v.startswith(x))
        counts[t] = counts.get(t, 0) + 1
    return ok, [
        f"  {len(prov)} 项工作点全部带来源标签,标签外的项: {bad or '无'}",
        f"  分布: " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        f"  原文窗 t_window_lit={tuple(wp['t_window_lit'])} s ← {prov['t_window_lit']}",
        f"  本次实际 t_window={wp['t_window']} ← {prov['t_window']}",
        f"  绑定条件: {wp['t_window_lit_binding']}",
    ]


NORMAL = [
    ("A", "恒等处理 ⇒ SD=0", check_A),
    ("B", "平坦衰减 X dB ⇒ SD=X", check_B),
    ("C", "窄陷波 vs 平坦衰减(两种口径)", check_C),
    ("E", "ERB 加权方向性(低频陷波更贵)", check_E),
    ("G", "与定义式解析积分对拍", check_G),
    ("H", "频带选择性(带外陷波)", check_H),
    ("I", "静音源 ⇒ N/A 而非 0", check_I),
    ("J", "接口:无单值出口", check_J),
    ("K", "工作点向量完整", check_K),
    ("L", "平均时间窗(含原文 30–60 s 不自动套用)", check_L),
    ("N", "工作点来源身份证:原文 vs 我方", check_N),
]


# ─────────────────────────────────────────────── 变异测试
def _mutate(attr, value, fn):
    old = getattr(sd, attr)
    setattr(sd, attr, value)
    try:
        return fn()
    finally:
        setattr(sd, attr, old)


MUTANTS = [
    ("M1", "加权函数 → 常数(等权 per-Hz)", "_erb_weights_raw",
     lambda f: np.ones_like(np.asarray(f, float)), "E"),
    ("M2", "分母 S_v → S_d(处理后信号自比)", "_ratio_db",
     lambda Sp, Ss: 10.0 * np.log10(Sp / Sp), "B"),
    ("M3", "10·log₁₀ → 20·log₁₀(系数改掉)", "_ratio_db",
     lambda Sp, Ss: 20.0 * np.log10(Sp / Ss), "B"),
    ("M4", "10·log₁₀ → 10·ln(log 底改掉)", "_ratio_db",
     lambda Sp, Ss: 10.0 * np.log(Sp / Ss), "B"),
    ("M5", "去掉 sqrt(归约成均方)", "_reduce",
     lambda p, dev: float(np.sum(p * dev * dev)), "B"),
    ("M6", "去掉权重归一化", "_normalize_weights",
     lambda w: w, "B"),
    ("M7", "加权函数 → 正比 ERB(方向反转)", "_erb_weights_raw",
     lambda f: erb_ref(f), "E"),
    ("M9", "平均时间窗被忽略(恒全选帧)", "_time_mask",
     lambda times, tw: np.ones(len(times), dtype=bool), "L"),
]

CHECK_BY_ID = {cid: fn for cid, _, fn in NORMAL}


# ─────────────────────────────────────────────── 窗平滑偏置表(工作点表,非判据)
def smear_table():
    rows = []
    for bw in (12.5, 25.0, 50.0, 100.0, 200.0, 400.0, 800.0):
        b, a = peaking(1000.0, -20.0, bw)
        meas = measure(signal.lfilter(b, a, SRC)).band_in.mean_db
        ana = analytic_sd(b, a, 300.0, 6500.0)
        rows.append((bw, meas, ana, meas / ana - 1.0))
    return rows


# ─────────────────────────────────────────────── 主流程
def main():
    L = []
    w = L.append

    w("§0 被测件 / 台架")
    w("  被测件 : sd_meter.py")
    w("  SD 主引: van Waterschoot & Moonen, J. Audio Eng. Soc. 58(11), 2010, **式(32) 页 937**")
    w("           —— 取它作主引是因为**它的语境正是 NHS**(S_d 原文写作 "
      "howling-compensated signal)")
    w("  SD 旁证: 同式见 Proc. IEEE 99(2), Feb 2011, 式(111) 页 319(语境为 HA-AFC),")
    w("           谱估计口径(|短时 DFT|²、50% 重叠、M 档位、mean+max 都报)由该处补齐")
    w("  ⚠ 原始出处 Spriet, Eneman, Moonen, Wouters, EUSIPCO 2008 (Lausanne) **不在库**")
    w(f"  台架   : 白噪源 seed={SEED}, fs={FS:.0f} Hz, {DUR:.0f} s, M=4096, Hann, 50% 重叠")
    w(f"  参照   : analytic_sd() —— 对定义式做连续网格积分(freqz,**不走 STFT**),")
    w(f"           ERB 公式在本脚本内**独立重写**,故变异 sd_meter 时参照不会跟着错。")
    w("")

    w("§1 已知答案算例")
    res_normal = {}
    for cid, name, fn in NORMAL:
        ok, lines = fn()
        res_normal[cid] = ok
        w(f"  [{cid}] {name} …… {'PASS' if ok else 'FAIL'}")
        for ln in lines:
            w(ln)
        w("")

    w("§2 变异测试(每个变异体必须让指定算例 FAIL —— 不能 FAIL 的度量不算度量)")
    res_mut = {}
    for mid, desc, attr, mut, target in MUTANTS:
        try:
            ok_under_mut, _ = _mutate(attr, mut, CHECK_BY_ID[target])
            crashed = ""
        except Exception as e:            # 变异体崩溃 = 也算被算例挡住
            ok_under_mut, crashed = False, f"  (变异体抛异常: {type(e).__name__}: {str(e)[:70]})"
        killed = not ok_under_mut
        res_mut[mid] = killed
        w(f"  [{mid}] {desc}")
        w(f"        → 算例 {target} 在变异下 {'FAIL(变异被杀,符合要求)' if killed else 'PASS(⚠ 变异存活 ⇒ 该算例挡不住这个 bug)'}"
          f" …… {'PASS' if killed else 'FAIL'}")
        if crashed:
            w(crashed)
    w("")

    w("  [M8] ⚠ 已知盲点(**不是变异,是 SD 的固有性质,报出来备案**):")
    r1 = sd.sd_measure(processed=SRC * 0.5, source=SRC, fs=FS)
    r2 = sd.sd_measure(processed=SRC, source=SRC * 0.5, fs=FS)
    same = abs(r1.band_in.mean_db - r2.band_in.mean_db)
    w(f"        入参对调 (processed↔source): {r1.band_in.mean_db:.12f} vs "
      f"{r2.band_in.mean_db:.12f}  差={same:.2e}")
    w(f"        ⇒ **SD 对偏差方向完全盲**(平方抵消符号):挖 6 dB 与抬 6 dB 同值,")
    w(f"          且**无法**用 SD 发现入参写反。故 sd_measure 已设为 keyword-only 从结构堵死。")
    w("")

    w("§3 窗平滑偏置表(**工作点表,非判据** —— 但用 SD 比较 NHS 方案前必须先看这张表)")
    w("     1 kHz / −20 dB 陷波,改变带宽;实测 = 4096 点 STFT,解析 = 定义式积分")
    w("     BW(Hz)    实测 SD_in    解析 SD_in     偏差")
    rows = smear_table()
    for bw, meas, ana, rel in rows:
        w(f"     {bw:7.1f}   {meas:10.4f}   {ana:10.4f}   {rel:+7.2%}")
    w(f"     ⇒ Hann 主瓣宽 4·fs/M = {4 * FS / 4096:.1f} Hz。陷波带宽逼近或低于主瓣宽时,")
    w("       STFT 把陷波「抹平」 ⇒ **SD 系统性低估失真**,且**方向偏乐观**(读起来更好听)。")
    w(f"     ⇒ NHS 用的正是窄陷波 ⇒ **本表的偏置必须随 SD 数一起报**;跨不同陷波带宽比较 SD 前")
    w(f"       须先确认带宽同档,否则窄陷波方案会白得一份不存在的音质优势。")
    w("")

    w("§4 N/A 与未解决(不估、不编)")
    w("  · **ANSI S3.5-1997 Table 2 变体:N/A** —— 原文(两处)都说 w_ERB 依 ANSI S3.5-1997")
    w("    Table 2;该标准原件不在库 ⇒ 未实现、未查表、未拟合。本实现用的是 Glasberg–Moore")
    w("    ERB 闭式 [L3/教科书],**不声称与 ANSI Table 2 等价**。二者数值差异 = 未知,未测。")
    w("  · **SD 原始出处 Spriet et al. EUSIPCO 2008 (Lausanne) 不在库** ⇒ 本实现依据的是")
    w("    2010 JAES / 2011 Proc.IEEE 两篇综述的转述,不是 SD 的原始论文。[L2/综述原文]")
    w("  · **未做时间对齐**(原文亦不做)⇒ 处理链群延时会被读成谱失真。本轮台架里陷波器")
    w("    群延时的贡献**未单独分离**,未测其量级。")
    w("  · **谱地板 / 帧门限**(floor_db=-120, gate_db=-80)原文未规定 ⇒ 我方选择,")
    w("    对本轮宽带白噪算例无影响(全部帧均过门),对真实语音的影响**未测**。")
    w("  · 本工具**只在 LTI + 平稳宽带源**上与解析式对拍过。对时变处理(NHS 陷波在跑动中")
    w("    切换)**未验证**;真实语音源**未验证**。")
    w("")

    all_normal = all(res_normal.values())
    all_killed = all(res_mut.values())
    verdict = all_normal and all_killed

    head = [
        "═" * 78,
        f"r68 · sd_meter.py 自测输出     结论:【{'通过' if verdict else '未通过'}】",
        "═" * 78,
        "门禁状态:**未过门** —— 本件未经独立 critic verdict,不得 release / 冻结 /",
        "          被下游引用 / 对外承诺。",
        "",
        f"已知答案算例 {sum(res_normal.values())}/{len(res_normal)} 通过: "
        + "  ".join(f"{k}={'P' if v else 'F'}" for k, v in res_normal.items()),
        f"变异测试     {sum(res_mut.values())}/{len(res_mut)} 被杀: "
        + "  ".join(f"{k}={'kill' if v else 'SURVIVED'}" for k, v in res_mut.items()),
        "",
        "⚠ 随数必读:§3 窗平滑偏置表(窄陷波下 SD 系统性低估,方向偏乐观)、",
        "            §2 M8 盲点(SD 对失真方向完全盲)、§4 N/A 清单。",
        "═" * 78,
        "",
    ]
    text = "\n".join(head + L) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
