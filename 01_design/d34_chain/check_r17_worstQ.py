#!/usr/bin/env python3
"""
r17 —— 独立复核 critic `critic_D3D4_r3_verdict_20260805.md` BLOCKER-1 的三层结论
⛔ 门禁状态:未过门。
⛔ 本脚本【不 import d34_analysis / check_noise_chain_r5】,滤波器与噪声积分独立重写。

⭐ 为什么要复核:verdict 里的数【每一跳都要重验】(本库 65.86 那次三跳零复核的教训)。
   ⇒ 而这一次尤其:我要据它去改一个已经报给 CTO 的量级。
"""
import math
import cmath
import sys

FS = 48000.0
COEF_F = 27
Q_DBFS = -173.35                 # 单节噪声底 [L2/宿主实测,任务一],⚠ 所属件未过门
_rc = 0


def OK(tag, cond, msg):
    global _rc
    print(f"  [{'PASS' if cond else 'FAIL'}] {tag:<10s} {msg}")
    if not cond:
        _rc = 1


def q(x):
    v = int(math.floor(x * (1 << COEF_F) + 0.5)) if x >= 0 else \
        int(math.ceil(x * (1 << COEF_F) - 0.5))
    return v / float(1 << COEF_F)


def peaking(f0, Qf, gdb):
    A = 10 ** (gdb / 40.0)
    w = 2 * math.pi * f0 / FS
    al = math.sin(w) / (2 * Qf)
    c = math.cos(w)
    a0 = 1 + al / A
    return (q((1 + al * A) / a0), q(-2 * c / a0), q((1 - al * A) / a0),
            1.0, q(-2 * c / a0), q((1 - al / A) / a0))


def hpf(f0, Qf):
    w = 2 * math.pi * f0 / FS
    al = math.sin(w) / (2 * Qf)
    c = math.cos(w)
    a0 = 1 + al
    b0 = q((1 + c) / 2 / a0)
    return (b0, -2 * b0, b0, 1.0, q(-2 * c / a0), q((1 - al) / a0))   # 结构约束量化


def H(sec, w):
    b0, b1, b2, a0, a1, a2 = sec
    z = cmath.exp(-1j * w)
    return (b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)


def floor_dbfs(secs, NW=4096):
    """链末噪声底:第 k 节输出处一个量化器,其噪声经第 k+1…N 节的 |H|²(0…π 均值)。"""
    ws = [math.pi * (i + 0.5) / NW for i in range(NW)]
    p1 = 10 ** (Q_DBFS / 10.0)
    tot = 0.0
    for k in range(len(secs)):
        s = 0.0
        for w in ws:
            g = 1.0
            for j in range(k + 1, len(secs)):
                g *= abs(H(secs[j], w)) ** 2
            s += g
        tot += p1 * (s / NW)
    return 10 * math.log10(tot)


HP = hpf(80.0, 0.7071)


def d3_chain(f0, Qf, gdb=15.0, n=8):
    return [HP] + [peaking(f0, Qf, gdb) for _ in range(n)]


print("=" * 90)
print("check_r17_worstQ —— 独立复核 critic D3D4-r3 BLOCKER-1(⛔ 不 import 被审件)")
print("门禁状态: 未过门")
print("=" * 90)

# ── 0. 先复现被审件自己那一格,确认两套实现同源可比 ──────────────────
base = floor_dbfs(d3_chain(1000.0, 1.4))
unity = floor_dbfs([HP] + [peaking(1000.0, 1.0, 0.0) for _ in range(8)])
model = Q_DBFS + 10 * math.log10(9)
print(f"\n[0] 同源可比性")
print(f"    各节增益=1     : {unity:8.2f} dBFS(直接相加模型 {model:.2f})")
print(f"    EXP-5c 那一格  : {base:8.2f} dBFS  (f0=1000, Q=1.4, 8 段 +15 dB)")
OK("R0a", abs(unity - model) < 0.01, f"增益=1 时回到直接相加 ⇒ 本脚本的级联积分没写错")
OK("R0b", abs(base - (-76.97)) < 0.01,
   f"逐位复现被审件的 −76.97(实测 {base:.2f})⇒ 两套独立实现可比")

# ── 1. 第①层:钉死 Q=1.4,只挪 f0 ─────────────────────────────────
print(f"\n[1] ⭐ 第①层(最难反驳):**在 EXP-5c 自己钉死的 Q=1.4 上**,只挪 f0")
row = {}
for f0 in (1000.0, 8000.0, 12500.0, 16000.0):
    row[f0] = floor_dbfs(d3_chain(f0, 1.4))
    print(f"    f0 = {f0:7.0f} Hz, Q=1.4 ⇒ {row[f0]:8.2f} dBFS  (破 PRD {row[f0]+106:+.2f} dB)")
worst_default_q = max(row.values())
OK("R1", worst_default_q > base + 5.0,
   f"Q=1.4 那一行的最坏点 = {worst_default_q:.2f} dBFS,比 EXP-5c 报的 {base:.2f} 差 "
   f"{worst_default_q-base:.2f} dB ⇒ **它连自己那一行上的最坏点都不是**")

# ── 2. 第②层:参数字典全范围(band_freq 20…20k × band_q 0.02…50)──
print(f"\n[2] 第②层:参数字典自己声明的范围内扫 f0 × Q(band_gain 固定 +15 = 其上限)")
FS_GRID = [32, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 12500, 16000, 20000]
Q_GRID = [0.02, 0.10, 0.50, 1.40, 50.0]
print("      Q\\f0  " + "".join(f"{f:>7.0f}" for f in FS_GRID))
worst = (-1e9, None, None)
for Qf in Q_GRID:
    cells = []
    for f0 in FS_GRID:
        v = floor_dbfs(d3_chain(float(f0), Qf))
        cells.append(v)
        if v > worst[0]:
            worst = (v, f0, Qf)
    print(f"      {Qf:<6.2f}" + "".join(f"{v:>7.1f}" for v in cells))
print(f"    ⇒ 最坏格 = (f0 = {worst[1]:.0f} Hz, Q = {worst[2]}) ⇒ **{worst[0]:.2f} dBFS**"
      f" ⇒ 破 PRD **{worst[0]+106:.2f} dB**")
OK("R2", abs(worst[0] - (-54.38)) < 0.05 and worst[2] == 0.02,
   f"与 critic 的 −54.38 / (12500, 0.02) 相符(实测 {worst[0]:.2f} @ f0={worst[1]:.0f}, Q={worst[2]})")

# ── 3. 第③层:承重的轴是 Q,不是"同频" ──────────────────────────
print(f"\n[3] ⭐ 第③层:「8 段叠在同一频率」这根轴选对了吗?")
SPREAD = [63, 160, 400, 1000, 2500, 4000, 8000, 12500]
spread_lowq = floor_dbfs([HP] + [peaking(float(f), 0.02, 15.0) for f in SPREAD])
print(f"    8 段【散开】在竞品档位 {SPREAD}、Q 取字典下限 0.02 ⇒ {spread_lowq:8.2f} dBFS")
print(f"    8 段【同频】@1 kHz、Q = 默认 1.4(= EXP-5c)          ⇒ {base:8.2f} dBFS")
OK("R3", spread_lowq > base + 5.0,
   f"散开+低 Q 比 同频+默认Q 还差 {spread_lowq-base:.2f} dB "
   f"⇒ **承重的轴是 Q,不是同频** ⇒ §6.2-4 那句『明文允许同频叠加』论证的是错的那根轴")

# ── 4. 增益方向 + 网格无关(⛔ 两条我不假定,实测)──────────────
print(f"\n[4] 两条我不假定的前提")
g_plus = floor_dbfs(d3_chain(12500.0, 0.02, +15.0))
g_minus = floor_dbfs(d3_chain(12500.0, 0.02, -15.0))
print(f"    band_gain = +15 ⇒ {g_plus:8.2f} dBFS ;  −15 ⇒ {g_minus:8.2f} dBFS")
OK("R4a", g_plus > g_minus,
   f"+15 比 −15 差 {g_plus-g_minus:.2f} dB ⇒ 取 +15 作为增益轴的最坏是对的(⛔ 不是假定)")
v_lo = floor_dbfs(d3_chain(12500.0, 0.02), NW=1024)
v_hi = floor_dbfs(d3_chain(12500.0, 0.02), NW=16384)
print(f"    NW = 1024 ⇒ {v_lo:.3f} ;  NW = 16384 ⇒ {v_hi:.3f}(16×)")
OK("R4b", abs(v_lo - v_hi) < 0.01,
   f"网格 16× 变化下该值动 {abs(v_lo-v_hi):.4f} dB ⇒ ⛔ 不是网格伪影")

# ── 5. m-1:−91.64 与 −76.97 的差,是不是链首那一个量化器 ─────────
print(f"\n[5] m-1 旁证:−91.64(8×PEQ 段)与 −76.97(D3 输入链)差在哪")
peq_only = floor_dbfs([peaking(1000.0, 1.4, 15.0) for _ in range(8)])
print(f"    只有 8×PEQ(⛔ 无链首 HPF)⇒ {peq_only:8.2f} dBFS")
print(f"    加上链首 HPF 的 1 个量化器 ⇒ {base:8.2f} dBFS   差 {base-peq_only:+.2f} dB")
OK("R5", abs(peq_only - (-91.64)) < 0.05,
   f"复现 −91.64 ⇒ 两个数是【两条不同的链】,预注册 §3 预期栏引错了口径"
   f" ⇒ ⭐ 链首那 1 个量化器一个人贡献 {base-peq_only:.2f} dB(它的噪声要过完 8 段 +15 dB)")

print("\n" + "=" * 90)
print(f"退出码 = {_rc}")
print("=" * 90)
sys.exit(_rc)
