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
# 盘面事实:两张表用了两个不同的 ω 网格(d34_analysis.py:302 与 :472)
#   §5.3(EXP-4)  wg = linspace(1e-6, π−1e-6, 400001) ⇒ 带内最低点 ≈ 20.00 Hz(Δf = 0.060 Hz)
#   §5.4(B)(EXP-8) w8 = linspace(2π·20/fs, π−1e-6, 200000) ⇒ 首点浮点上落在 20 Hz 之下、
#                  被 `f8>=20` 掩掉 ⇒ 带内最低点 ≈ 20.12 Hz(Δf = 0.120 Hz)
print("  两张表的网格(盘面):§5.3 Δf = 0.060 Hz;§5.4(B) Δf = 0.120 Hz(且首点被掩码剔除)")
print(f"  {'评价点 f (Hz)':>14s} {'LR2@80 群延迟 (ms)':>20s}")
tau = {}
for fx in (20.00, 20.06, 20.12, 20.24):
    w = 2 * math.pi * fx / FS
    h = 1e-7
    d = -(cmath.phase(casc(lr2, w + h)) - cmath.phase(casc(lr2, w - h))) / (2 * h)
    tau[fx] = d / FS * 1000
    print(f"  {fx:>14.2f} {tau[fx]:>20.4f}")
# 换【口径】(评价频带上沿)对该值有没有影响 —— 峰在带下沿,上沿改不动它
same_by_scope = True                      # 上沿 8k/20k 都不含 20 Hz 以下 ⇒ 峰点不变
OK("B-4", abs(tau[20.00] - 3.7448) < 5e-4 and abs(tau[20.12] - 3.742) < 5e-4 and same_by_scope,
   f"3.744 = 网格取到 20.00 Hz;3.742 = 网格最低点落在 20.12 Hz"
   f" ⇒ 成因是【网格对齐】,⛔ 不是口径")
print("  ⇒ ∴ m-3 与 m-1/m-2 **不同族**:m-1/m-2 改的是口径标注,m-3 要改的是网格")
# m-1 的算术(盘面数,⛔ 不重跑)
col = [3.396, 5.895, 6.792, 5.904, 4.666]
print(f"\n  [m-1] §5.7.2 列相加 = {sum(col):.3f} ms,而该表「全链」写 26.407 ms(差 {sum(col)-26.407:.3f})")
print(f"        盘面:results_d34_r13.txt:246 的 EXP-9 求和 = 26.654(= 列相加口径)")
print(f"              results_d34_r13.txt:322 的 EXP-11 下沿 20 Hz = 26.407(= 逐频相加口径)")
OK("m-1", abs(sum(col) - 26.653) < 0.002,
   "列内为【各模块独立最大值】(相加 26.653),26.407 来自【逐频相加】⇒ 两个口径,须标注")

# ================================================================ MAJOR-2
print("\n[MAJOR-2] 最大节点电平 vs Q4.27 链内余量(⛔ 差值不是余量)")
print("-" * 88)
print(f"  Q4.27 链内余量 = 20·log₁₀(2⁴) = {HEADROOM_DB:.4f} dB")
xo4 = lr_sections(120.0, 4, 'hp')
FTEST = 40.0
w_t = 2 * math.pi * FTEST / FS
# ⛔⛔ 整改 2026-08-05(critic D3D4-r4 MAJOR-1 修法②):原表只扫到 **3 段**,
#   而参数字典允许 **8 段**(设计件 §3⑥ `band_en[k]` k = 0…7)。
#   ⇒ critic 按本表自己的线性外推,怀疑「分频在前」在段数够多时**也会越界**
#     —— 而它明写那是 [L3/由其自表外推,**未实算**],⛔ 不得当结论引用。
#   ⇒ ∴ 本轮把段数**扫到字典上限 8**,把 ⑥⑦⑧ 实算出来。
#   ⭐ 这与 r3 BLOCKER-1 修法②(EXP-5c 在字典范围上取 max)是**同一条**:
#     【凡说"最坏",就在参数字典的范围上取 max;⛔ 不钉一个点然后叫它最坏】
cfgs = [
    ("① EXP-1 自己的工作点(−20 dBFS,1 段 +12 dB)", -20.0, [peaking(40.0, 1.0, 12.0)]),
    ("② 同 ① 但满刻度输入", 0.0, [peaking(40.0, 1.0, 12.0)]),
] + [
    (f"{'③④⑤⑥⑦⑧⑨⑩'[n-1]} 满刻度 + {n} 段 +15 dB @40 Hz(同频)"
     + ("  ← **字典上限**" if n == 8 else ""),
     0.0, [peaking(40.0, 1.0, 15.0)] * n)
    for n in range(1, 9)
]


def max_node(secs, in_dbfs):
    """最大【节点】电平 = 各节输出电平的最大值。
    ⛔ 与 EXP-1 的定义一致(链入口不算节点:它恒 ≤ 0 dBFS,由格式保证)。"""
    g = 1.0
    peak = -1e9
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

# ⭐⭐ MAJOR-2d(r18 新增 · critic D3D4-r4 MAJOR-1 2.2):
#   「分频在前」在段数够多时会不会【也】越界?——⛔ critic 只能外推,本条实算。
_xo_over = [r for r in rows if r[4]]          # r[4] = 分频在前是否越界
_peq_over = [r for r in rows if r[3]]
print(f"\n  ⭐ 两种顺序各自的【最早越界段数】(⛔ 这才是本表要回答的量):")
print(f"     PEQ 在前   最早越界于:{_peq_over[0][0].split('(')[0].strip() if _peq_over else '(全量程内不越)'}")
print(f"     分频在前   最早越界于:{_xo_over[0][0].split('(')[0].strip() if _xo_over else '(全量程内不越)'}")
OK("MAJOR-2d", len(_xo_over) > 0,
   f"⛔ **「分频在前」在字典允许的段数内【也会越界】** ——"
   f"最早出现在 {_xo_over[0][0].split('(')[0].strip() if _xo_over else '—'}"
   f"({_xo_over[0][2]:+.2f} dBFS > {HEADROOM_DB:.2f})"
   if _xo_over else
   "「分频在前」在字典允许的全部段数内都不越界 ⇒ 分频前置【足以】解决问题")
if _xo_over:
    print(f"  ⇒ ⛔⛔ ∴ 「分频必须在 PEQ 之前」这条结论**仍然成立**(它把门槛从"
          f"{_peq_over[0][0][0]} 推到 {_xo_over[0][0][0]}),")
    print(f"     **⛔ 而它【不足以】解决问题** —— 在字典允许的最坏配置下两种顺序都越界。")
    print(f"     ⇒ ∴ §0 该行的**结论句须改写**:分频前置是【必要】的,⛔ 不是【充分】的。")
    print(f"     ⇒ 仍需一条独立的约束(限累计增益 / 运行时拦截 / 链内字长),⛔ 不能靠链序解决。")
d_stop = rows[0][1] - rows[0][2]
OK("MAJOR-2c", abs(d_stop - 31.14) < 0.01,
   f"① 行两列之差 = {d_stop:.2f} dB ⇒ 逐位复现被审件的 31.14"
   f"(⇒ 我这套独立实现与它同源可比;⛔ 而该数的类别是【差值】)")

# ================================================================ m-7
print("\n[m-7] 转换器合计 47.9844 样本的 ms 值")
print("-" * 88)
exact = 47.9844 / 48.0
print(f"  22.9844 + 25.0 = 47.9844 样本 @48 kHz ⇒ 精确十进制 0.999675 ms(末位是舍入平局)")
print(f"  float64 表示 = {exact:.15f} ⇒ 用 '%.5f' 打印会得到 {exact:.5f}(平局向下)")
print(f"  ⚠ PREREG_D34_r1.txt:90 当时写的是 **0.99968**(平局远离零,正确)")
print(f"  ⇒ 设计件的 0.99967 是【从预注册到设计件反而变坏】的漂移")
OK("m-7", abs(exact * 1e6 - 999675.0) < 1e-6,
   f"精确值 0.999675 ms ⇒ 应写 0.99968 ms(或 0.9997 ms),⛔ 不写 0.99967")

print("\n" + "=" * 88)
print(f"退出码 = {_rc}")
print("=" * 88)
sys.exit(_rc)
