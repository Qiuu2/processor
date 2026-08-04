#!/usr/bin/env python3
"""
r16 —— 批量理由审计(B-1…B-4)+ MAJOR-2 最大节点电平表 + m-3/m-7 定性
⛔ 门禁状态:未过门(未经独立 critic 评审)。
预注册: PREREG_D34_r16_addendum.txt(⛔ 落盘于本脚本任何一次跑之前)

⛔ 本脚本【不 import d34_analysis】,滤波器设计为独立重写。
"""
import math
import cmath
import sys

FS = 48000.0
COEF_F = 27                     # Q4.27
HEADROOM_DB = 20 * math.log10(2 ** 4)   # Q4.27 的链内余量 = 24.0824 dB

_rc = 0


def OK(tag, cond, msg):
    global _rc
    print(f"  [{'PASS' if cond else 'FAIL'}] {tag:<12s} {msg}")
    if not cond:
        _rc = 1


# ---------------------------------------------------------------- 独立滤波器设计
def bw_lp(fc, Q):
    w0 = 2 * math.pi * fc / FS
    al = math.sin(w0) / (2 * Q)
    c = math.cos(w0)
    a0 = 1 + al
    return ((1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0,
            1.0, -2 * c / a0, (1 - al) / a0)


def bw_hp(fc, Q):
    w0 = 2 * math.pi * fc / FS
    al = math.sin(w0) / (2 * Q)
    c = math.cos(w0)
    a0 = 1 + al
    return ((1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0,
            1.0, -2 * c / a0, (1 - al) / a0)


def peaking(f0, Q, gdb):
    A = 10 ** (gdb / 40.0)
    w0 = 2 * math.pi * f0 / FS
    al = math.sin(w0) / (2 * Q)
    c = math.cos(w0)
    a0 = 1 + al / A
    return ((1 + al * A) / a0, -2 * c / a0, (1 - al * A) / a0,
            1.0, -2 * c / a0, (1 - al / A) / a0)


def butter_qs(order):
    return [1.0 / (2 * math.cos(math.pi * (2 * k + 1) / (2 * order)))
            for k in range(order // 2)]


def lr_sections(fc, lr_order, kind):
    bo = lr_order // 2
    mk = bw_lp if kind == 'lp' else bw_hp
    if bo == 1:
        return [mk(fc, 0.5)]
    if bo % 2 == 0:
        return [mk(fc, q) for q in butter_qs(bo) for _ in range(2)]
    if bo == 3:
        return [mk(fc, 0.5)] + [mk(fc, 1.0) for _ in range(2)]
    raise ValueError(lr_order)


def H(sec, w):
    b0, b1, b2, a0, a1, a2 = sec
    z = cmath.exp(-1j * w)
    return (b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)


def casc(secs, w):
    v = 1.0 + 0j
    for s in secs:
        v *= H(s, w)
    return v


def db(x):
    return 20 * math.log10(abs(x) + 1e-300)


print("=" * 88)
print("check_r16 —— 批量理由审计 + MAJOR-2 最大节点电平")
print("门禁状态: 未过门   预注册: PREREG_D34_r16_addendum.txt")
print("=" * 88)

# ================================================================ B-1
print("\n[B-1] erratum2 的批量判断:87.72 dB(EXP-3p)是不是网格伪影?")
print("-" * 88)
print("  被测算例 = 被审件 EXP-3p 原样:LR4 @2000 Hz,理想系数,LP − HP(即错误极性)")
li = lr_sections(2000.0, 4, 'lp')
hi = lr_sections(2000.0, 4, 'hp')
print(f"  {'网格点数':>10s} {'max|偏离| (20Hz–20kHz)':>24s} {'最近网格点距 fc':>18s}")
vals_b1 = []
for N in (20001, 50001, 200001, 500001, 2000001):
    best = -1e9
    nearest = 1e9
    for i in range(N):
        w = 1e-7 + (math.pi - 2e-7) * i / (N - 1)
        f = w * FS / (2 * math.pi)
        if f < 20.0 or f > 20000.0:
            continue
        nearest = min(nearest, abs(f - 2000.0))
        d = abs(db(casc(li, w) - casc(hi, w)))
        if d > best:
            best = d
    vals_b1.append(best)
    print(f"  {N:>10d} {best:>21.2f} dB {nearest:>15.3f} Hz")

mono = all(vals_b1[i] < vals_b1[i + 1] for i in range(len(vals_b1) - 1))
spread = max(vals_b1) - min(vals_b1)
# ⛔ 不依赖网格的独立判据:fc 处的 |LP−HP| 是不是精确 0
w_fc = 2 * math.pi * 2000.0 / FS
resid = abs(casc(li, w_fc) - casc(hi, w_fc))
print(f"\n  ⛔ 不依赖网格的判据:fc 处 |LP − HP| = {resid:.3e}"
      f"(相对 |LP| = {resid / abs(casc(li, w_fc)):.3e})")
OK("B-1a", mono and spread > 20.0,
   f"该值随网格密度单调增大、跨度 {spread:.2f} dB ⇒ 不收敛 ⇒ **是网格伪影**")
OK("B-1b", resid < 1e-12,
   f"fc 处求和残差 {resid:.2e} ≈ 0(float64 底)⇒ 零点真实存在 ⇒ 理想深度 = −∞")
print("  ⇒ 结论:erratum2 的【批量判断】对 87.72 这一条**成立** ⇒ 我上一轮的撤回站得住。")

# ================================================================ B-2
print("\n[B-2] BLOCKER-1 的一句理由盖了三条 ⭐ 结论 —— 逐条代入")
print("-" * 88)
import subprocess
import os
D = os.path.dirname(os.path.abspath(__file__))
probes = [("f_lo* = 105.2 Hz", "EXP-11"), ("Q 的影响是段数的 8.02×", "EXP-10c"),
          ("拒绝率 0 段", "EXP-10b")]
allmiss = True
for name, tag in probes:
    hits = []
    for r in range(2, 8):                       # r2 … r7 = 文档原先列出的那批
        p = os.path.join(D, f"results_d34_r{r}.txt")
        if os.path.exists(p) and tag in open(p, encoding='utf-8').read():
            hits.append(f"r{r}")
    print(f"  {name:<26s} 标识 {tag:<9s} 在 r2–r7 中的命中: "
          f"{'、'.join(hits) if hits else '**零命中**'}")
    if hits:
        allmiss = False
OK("B-2", allmiss, "三条 ⭐ 结论在 r2–r7 全部零命中 ⇒ 该理由对三条【逐条成立】")

# ================================================================ B-3
print("\n[B-3] BLOCKER-1 修法② 说的「r8–r10 出现过的 8 条 FAIL」—— 盘面点数")
print("-" * 88)
union = []
for r in (8, 9, 10):
    p = os.path.join(D, f"results_d34_r{r}.txt")
    ids = []
    for ln in open(p, encoding='utf-8'):
        if ln.strip().startswith("[FAIL]"):
            ids.append(ln.strip().split()[1])
    print(f"  r{r}: FAIL {len(ids)} 条 ⇒ {ids}")
    for i in ids:
        if i not in union:
            union.append(i)
print(f"  ⇒ 并集 = {len(union)} 条:{union}")
OK("B-3", len(union) == 6,
   f"盘面并集 = {len(union)} 条,而 verdict 写的是 8 条 ⇒ **按盘面写**,差异如实标注")

# ================================================================ B-4 / m-3
print("\n[B-4 / m-3] 放行条件 8 把 m-1/m-2/m-3 归为「同一族的口径标注」—— 逐条代入")
print("-" * 88)
print("  m-3 的两个值:§5.3 = 3.744 ms,§5.4(B) = 3.742 ms(LR2 @80 Hz 群延迟最大值)")


def gd_max(secs, grid):
    """群延迟(样本)最大值 + 其出现频率。相位有限差分,两点对称。"""
    best = -1e9
    bf = 0.0
    for f in grid:
        w = 2 * math.pi * f / FS
        h = 1e-6
        p1 = cmath.phase(casc(secs, w - h))
        p2 = cmath.phase(casc(secs, w + h))
        d = -(p2 - p1) / (2 * h)
        if d > best:
            best, bf = d, f
    return best, bf


lr2 = lr_sections(80.0, 2, 'hp')
NG = 20001
log_grid = [20.0 * (20000.0 / 20.0) ** (i / (NG - 1)) for i in range(NG)]
lin_grid = [20.0 + (20000.0 - 20.0) * i / (NG - 1) for i in range(NG)]
g1, f1 = gd_max(lr2, log_grid)
g2, f2 = gd_max(lr2, lin_grid)
print(f"  对数网格({NG} 点):{g1 / FS * 1000:.4f} ms @ {f1:.2f} Hz")
print(f"  线性网格({NG} 点):{g2 / FS * 1000:.4f} ms @ {f2:.2f} Hz")
# 口径能不能解释这 0.002 ms?换口径 = 换评价频带上沿
g3, f3 = gd_max(lr2, [20.0 * (8000.0 / 20.0) ** (i / (NG - 1)) for i in range(NG)])
print(f"  换口径对照(同为对数网格,上沿 8 kHz):{g3 / FS * 1000:.4f} ms @ {f3:.2f} Hz")
OK("B-4", abs(g1 - g3) < 1e-9 and abs(g1 - g2) > 1e-9,
   "换【口径】不改变该值,换【网格】才改变 ⇒ m-3 不属口径族,⛔ 不能与 m-1/m-2 合并处置")
print(f"  ⇒ 峰在带下沿 20 Hz 处(实测 {f1:.2f} / {f2:.2f} Hz),"
      f"而两种网格在 20 Hz 附近的取点间距不同 ⇒ 差异是网格分辨率")

# ================================================================ MAJOR-2
print("\n[MAJOR-2] 最大节点电平 vs Q4.27 链内余量(⛔ 差值不是余量)")
print("-" * 88)
print(f"  Q4.27 链内余量 = 20·log₁₀(2⁴) = {HEADROOM_DB:.4f} dB")
xo4 = lr_sections(120.0, 4, 'hp')
FTEST = 40.0
w_t = 2 * math.pi * FTEST / FS
cfgs = [
    ("① EXP-1 自己的工作点(−20 dBFS,1 段 +12 dB)", -20.0, [peaking(40.0, 1.0, 12.0)]),
    ("② 同 ① 但满刻度输入", 0.0, [peaking(40.0, 1.0, 12.0)]),
    ("③ 满刻度 + 1 段 +15 dB @40 Hz", 0.0, [peaking(40.0, 1.0, 15.0)]),
    ("④ 满刻度 + 2 段 +15 dB @40 Hz(同频)", 0.0, [peaking(40.0, 1.0, 15.0)] * 2),
    ("⑤ 满刻度 + 3 段 +15 dB @40 Hz(同频)", 0.0, [peaking(40.0, 1.0, 15.0)] * 3),
]


def max_node(secs, in_dbfs):
    g = 1.0
    peak = in_dbfs
    for s in secs:
        g *= abs(H(s, w_t))
        peak = max(peak, in_dbfs + db(g))
    return peak


print(f"  {'配置':<40}{'PEQ 在前':>11}{'分频在前':>11}   谁越 {HEADROOM_DB:.2f} dB")
print("  " + "-" * 84)
rows = []
for nm, ind, peq in cfgs:
    a = max_node(peq + xo4, ind)
    b = max_node(xo4 + peq, ind)
    who = ("PEQ 在前越" if a > HEADROOM_DB else "") + \
          ("、分频在前也越" if b > HEADROOM_DB else "")
    rows.append((nm, a, b, a > HEADROOM_DB, b > HEADROOM_DB))
    print(f"  {nm:<40}{a:>+8.2f} dB{b:>+8.2f} dB   {who if who else '谁都不越'}")

c1 = rows[0]
crit = [r for r in rows if r[3] and not r[4]]
OK("MAJOR-2a", (not c1[3]) and (not c1[4]),
   f"EXP-1 自己的工作点上两种顺序都不越余量({c1[1]:+.2f} / {c1[2]:+.2f} dBFS)"
   f" ⇒ 31.14 dB 在该工作点上【没有后果】")
OK("MAJOR-2b", len(crit) > 0,
   f"存在 ±15 dB 量程内的临界配置使「PEQ 在前」越界而「分频在前」不越"
   f"(最早出现在 {crit[0][0].split('(')[0].strip() if crit else '—'})")
print("  ⇒ ∴ 结论「分频必须在 PEQ 之前」成立,而支撑它的是**本表**,⛔ 不是 31.14 dB。")
d_stop = rows[0][1] - rows[0][2]
print(f"  ⇒ 顺带:31.14 dB = 本表 ① 行两列之差 = {d_stop:.2f} dB(类别 = 差值,⛔ 不是余量)")

# ================================================================ m-7
print("\n[m-7] 转换器合计 47.9844 样本的 ms 值")
print("-" * 88)
exact = 47.9844 / 48.0
print(f"  22.9844 + 25.0 = 47.9844 样本 @48 kHz ⇒ {exact:.9f} ms")
print(f"  文档写 0.99967 = 截断;四舍五入 5 位 = {exact:.5f};PREREG_D34_r1.txt 当时写的是 0.99968")
OK("m-7", abs(exact - 0.999675) < 1e-12,
   f"精确值 = {exact:.6f} ms ⇒ 文档的 0.99967 是截断,应为 0.99968(或写 0.9997)")

print("\n" + "=" * 88)
print(f"退出码 = {_rc}")
print("=" * 88)
sys.exit(_rc)
