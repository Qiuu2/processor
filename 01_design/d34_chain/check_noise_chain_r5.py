#!/usr/bin/env python3
"""
r5 整改验证:§6.4「整条链的噪声底」的适用范围。
⛔ 门禁状态:未过门(未经独立 critic 评审)。

缘起(critic MAJOR-2,成立,我接受)
------------------------------------
§6.4 的模型是  噪声底 = −173.35 + 10·log₁₀(N),即**把 N 个量化噪声源直接功率相加**。
但第 k 节的量化噪声要**经过第 k+1…N 节的传函**才到链末,而链内每一级的增益是自由参数
—— §6.2-4 **明文允许**用户「把 8 段 PEQ 全部 +15 dB 叠在同一频率」。

⇒ 该节标题正是 D-4「⛔ 不许只验单级」,而它的脚注只讨论了**噪声相关性**假设(值 9 dB),
  **恰恰漏掉了级间增益这一维**(值 73 dB)。

本脚本(独立重算,⛔ 不 import 被审件、不 import d34_analysis)
-----------------------------------------------------------
每节噪声功率 = 10^(−173.35/10),经其后各节 |H|² 在 0…π 上取均值后求和。

结论
----
  · 模型在「各节增益 = 1」前提下**精确**(复算 −164.32,与模型逐位相符)
  · 在 §6.2-4 自己允许的【**默认 Q = 1.4 / f0 = 1 kHz** 同频叠加】配置下,链末 −91.64 dBFS
    ⛔⛔ 2026-08-05 更正(critic D3D4-r3 BLOCKER-1):本脚本各配置**取的都是默认 Q**,
      ⇒ 它们**不是最坏合法配置**。量程最坏 = (f0=12500, Q=0.02) ⇒ **−54.38 dBFS ⇒ 破 PRD 51.62 dB**。
      ⇒ 扫量程的那一版在 D3/D4 侧 `d34_analysis.py` 的 EXP-5c;独立复核 `check_r17_worstQ.py`。
      ⚠ 本脚本的**数值本身对**(逐位复现)⇒ E-2 加标注不删数;⛔ 变的是它们头上那个词。
    ⇒ 比 −164.32 差 **72.68 dB**,同时突破 PRD(−106)与设计目标(−120)
  · 在现实预设(②③)下,结论方向(算术噪声不是瓶颈)**仍然成立**
  ⇒ ∴ 要修的是【那个数的适用范围声明】,⛔ 不是格式裁决。
"""
import math
import cmath

FS = 48000.0
Q_DBFS = -173.35          # 单节噪声底,任务一 [L2/宿主实测 CHK-4],⚠ 该值所属件未过门


def peaking(f0, Q, g):
    A = 10 ** (g / 40.0)
    w = 2 * math.pi * f0 / FS
    al = math.sin(w) / (2 * Q)
    c = math.cos(w)
    a0 = 1 + al / A
    return ((1 + al * A) / a0, -2 * c / a0, (1 - al * A) / a0,
            1.0, -2 * c / a0, (1 - al / A) / a0)


def hpf(f0, Q):
    w = 2 * math.pi * f0 / FS
    al = math.sin(w) / (2 * Q)
    c = math.cos(w)
    a0 = 1 + al
    return ((1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0,
            1.0, -2 * c / a0, (1 - al) / a0)


def H(bq, w):
    b0, b1, b2, a0, a1, a2 = bq
    z1 = cmath.exp(-1j * w)
    z2 = z1 * z1
    return (b0 + b1 * z1 + b2 * z2) / (a0 + a1 * z1 + a2 * z2)


def mean_pow_after(sections, k, N=4096):
    """第 k 节的量化噪声经其后各节 |H|² 后的功率增益(0…π 均值)"""
    s = 0.0
    for i in range(N):
        w = math.pi * (i + 0.5) / N
        g = 1.0
        for j in range(k + 1, len(sections)):
            g *= abs(H(sections[j], w)) ** 2
        s += g
    return s / N


def chain_floor(sections, extra_unity_quantizers=0):
    """链末噪声 dBFS。extra_* = 位于链尾、增益为 1 的附加量化器(延时/限幅等)"""
    p1 = 10 ** (Q_DBFS / 10.0)
    tot = sum(p1 * mean_pow_after(sections, k) for k in range(len(sections)))
    tot += p1 * extra_unity_quantizers
    return 10 * math.log10(tot)


MODEL8 = Q_DBFS + 10 * math.log10(8)
FREQS = [60, 150, 350, 800, 1600, 3200, 6400, 12000]

print("=" * 88)
print("check_noise_chain_r5 —— §6.4 噪声模型的适用范围(critic MAJOR-2)")
print("门禁状态: 未过门")
print("=" * 88)
print(f"\n文档 §6.4 的模型:{Q_DBFS} + 10·log₁₀(8) = {MODEL8:.2f} dBFS(**直接功率相加**)\n")

cases = [
    ("① 8 节全单位增益(模型的隐含前提)", [peaking(1000, 1.0, 0.0) for _ in range(8)]),
    ("② 文档 CHK-5 用的那 8 段增益",
     [peaking(f, 1.4, g) for f, g in zip(FREQS, [6, -8, 4, -10, 12, -6, 9, -15])]),
    ("③ 8 段各 +6 dB 分散(现实的一档)", [peaking(f, 1.4, 6.0) for f in FREQS]),
    ("④ §6.2-4 明文允许:8 段全 +15 dB 同频(1 kHz,Q=1.4)",
     [peaking(1000, 1.4, 15.0) for _ in range(8)]),
]
print(f"  {'配置':<48}{'实算链末':>13}{'与模型差':>12}")
print("  " + "-" * 73)
vals = []
for nm, secs in cases:
    v = chain_floor(secs)
    vals.append(v)
    print(f"  {nm:<48}{v:>10.2f} dBFS{v - MODEL8:>+11.2f}")

v4 = vals[3]
print(f"\n  ④ 对 PRD 动态范围 >106 dB(⇒ ≤ −106 dBFS):"
      f"{'⛔ 突破 %.2f dB' % (v4 + 106) if v4 > -106 else 'OK'}")
print(f"  ④ 对设计目标 ≤ −120 dBFS            :"
      f"{'⛔ 突破 %.2f dB' % (v4 + 120) if v4 > -120 else 'OK'}")

# D3 输入链在同一【默认 Q】配置下(HPF + 8×PEQ 全 +15 同频,尾部 3 个单位增益量化器)
# ⛔ 「最坏」这个词已撤(见文件头);⚠ 而 `extra_unity_quantizers=3` 亦已判为错(应为 9 个量化器,
#   门/压限/延时不引入新量化器)⇒ 见 D3/D4 §6 整改留痕 (3)。两条都只影响标注/计数,不影响本行数值。
d3_worst = chain_floor([hpf(80.0, 0.7071)] + [peaking(1000, 1.4, 15.0) for _ in range(8)],
                       extra_unity_quantizers=3)
d3_unity = Q_DBFS + 10 * math.log10(12)
print(f"\n  D3 输入链(12 量化器):各节增益=1 ⇒ {d3_unity:.2f} dBFS;"
      f"默认 Q 下的大增益 ⇒ **{d3_worst:.2f} dBFS**(差 {d3_worst - d3_unity:+.2f} dB)⚠ ⛔ 非量程最坏")

print(f"\n  28 量化器 · 各节增益=1:{Q_DBFS + 10 * math.log10(28):.2f} dBFS(= 文档的 −158.88)")

# ---- 判定 ----
rc = 0
print("\n" + "=" * 88)
ok_model = abs(vals[0] - MODEL8) < 0.01
ok_worst = v4 > -106.0
print(f"  [{'PASS' if ok_model else 'FAIL'}] N1  模型在「各节增益=1」前提下精确"
      f"(复算 {vals[0]:.2f} vs 模型 {MODEL8:.2f})")
print(f"  [{'PASS' if ok_worst else 'FAIL'}] N2  存在**文档自己允许**的配置使链末突破 PRD 的 −106 dBFS"
      f"(实算 {v4:.2f})")
# 阳性对照:证明本脚本的级联计算认得出"没有级间增益"这件事
ok_ctrl = abs(vals[0] - MODEL8) < 0.01 and (vals[3] - vals[0]) > 60.0
print(f"  [{'PASS' if ok_ctrl else 'FAIL'}] N3  阳性对照:同一套代码在增益=1 时回到直接相加、"
      f"在最坏增益时给出 {vals[3] - vals[0]:+.2f} dB ⇒ 它确实在算级间增益")
if not (ok_model and ok_worst and ok_ctrl):
    rc = 1
print("=" * 88)
raise SystemExit(rc)
