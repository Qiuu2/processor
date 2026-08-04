#!/usr/bin/env python3
"""
r14:Bessel 群延迟平坦度(唯一未测的卖点)。
⛔ 门禁状态:未过门。预注册 PREREG_D34_r14_bessel_delay.txt(⛔ 写于本文件之前)。

⛔⛔ 本件**刻意不含任何达标线** —— 群延迟平坦度是卖点数,先量再定线(见预注册 §0)。
"""
import math
import cmath

import numpy as np
from scipy import signal

FS = 48000.0
fails = []


def chk(tag, ok, msg):
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag:<8s} {msg}")
    if not ok:
        fails.append(tag)


# ── 设计:与 xover_r8.py 同一套(独立重写,⛔ 不 import 被审件)──────────────
def bessel_poles_norm(n):
    coeff = [math.factorial(2 * n - k) //
             (2 ** (n - k) * math.factorial(k) * math.factorial(n - k))
             for k in range(n + 1)]
    roots = np.roots(list(reversed([float(c) for c in coeff])))
    c0 = float(coeff[0])

    def mag(w):
        s = 1j * w
        v = sum(float(coeff[k]) * s ** k for k in range(n + 1))
        return abs(c0 / v)

    lo, hi = 1e-6, 100.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mag(mid) > 1.0 / math.sqrt(2.0):
            lo = mid
        else:
            hi = mid
    return [complex(r) / (0.5 * (lo + hi)) for r in roots]


def bilinear_sections(poles, zeros_at, fc):
    """模拟极点 → 单次预畸 → 双线性 → 双二阶/一阶节列表 (b0,b1,b2,1,a1,a2)"""
    c = 2.0 * FS
    wa = c * math.tan(math.pi * fc / FS)
    pd = [(1 + (wa * p) / c) / (1 - (wa * p) / c) for p in poles]
    zd = [zeros_at] * len(pd)
    # ⭐ 每节按 C 侧 design_bessel 的口径归一化:LP 在 z=1、HP 在 z=−1 处增益 1。
    # ⛔ 首版漏了这一步 ⇒ b 恒为精确整数 {1,2,1} ⇒ **量化对 b 是空操作**
    #   ⇒ r15 的零点完整性与 Bessel 的 Δτ 全是伪影。τ 本身不受影响(相位与常数增益无关),
    #     但**定点比对必须有它**。⇒ 见 r15 §「测量有效性」。
    zt = 1.0 if zeros_at < 0 else -1.0
    out, used = [], [False] * len(pd)
    for i, p in enumerate(pd):
        if used[i]:
            continue
        if abs(p.imag) < 1e-9:
            used[i] = True
            g = abs((zt - p.real) / (zt - zeros_at))
            out.append((g, -zeros_at * g, 0.0, 1.0, -p.real, 0.0))
        else:
            for j in range(i + 1, len(pd)):
                if not used[j] and abs(pd[j] - p.conjugate()) < 1e-7:
                    used[i] = used[j] = True
                    den = (zt - p.real) ** 2 + p.imag ** 2
                    g = abs(den / ((zt - zeros_at) ** 2))
                    out.append((g, -2.0 * zeros_at * g, (zeros_at ** 2) * g,
                                1.0, -2.0 * p.real, abs(p) ** 2))
                    break
    _ = zd
    return out


def rbj_lp(f0, Q):
    w = 2 * math.pi * f0 / FS
    c, s = math.cos(w), math.sin(w)
    al = s / (2.0 * Q)
    a0 = 1 + al
    return ((1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0, 1.0, -2 * c / a0, (1 - al) / a0)


def butter_q(n, k):
    return 1.0 / (2.0 * math.sin(math.pi * (2 * k + 1) / (2.0 * n)))


def design_bessel_lp(fc, n):
    return bilinear_sections(bessel_poles_norm(n), -1.0, fc)


def design_butter_lp(fc, n):
    out = []
    if n % 2 == 1:
        K = math.tan(math.pi * fc / FS)
        out.append((K / (K + 1), K / (K + 1), 0.0, 1.0, (K - 1) / (K + 1), 0.0))
    out += [rbj_lp(fc, butter_q(n, i)) for i in range(n // 2)]
    return out


def design_lr_lp(fc, n):
    """LR n = (BW n/2)² ⇒ 每节串两遍"""
    return design_butter_lp(fc, n // 2) * 2


# ── 群延迟:逐节求和(⛔ 不对级联后的高阶多项式直接求)──────────────────────
def gd_section(bq, f):
    """单节群延迟(样本数)。解析:τ = −d arg H/dω,用中心差分对相位求导(解缠绕)。"""
    b0, b1, b2, a0, a1, a2 = bq
    d = 1e-6

    def ph(w):
        z1 = cmath.exp(-1j * w)
        z2 = z1 * z1
        return cmath.phase((b0 + b1 * z1 + b2 * z2) / (a0 + a1 * z1 + a2 * z2))

    w = 2 * math.pi * f / FS
    p1, p2 = ph(w - d), ph(w + d)
    dp = p2 - p1
    while dp > math.pi:
        dp -= 2 * math.pi
    while dp < -math.pi:
        dp += 2 * math.pi
    return -dp / (2 * d)


def gd_chain_ms(secs, f):
    return sum(gd_section(s, f) for s in secs) / FS * 1000.0


def band(f_lo, f_hi, npts):
    return [f_lo * (f_hi / f_lo) ** (i / (npts - 1)) for i in range(npts)]


print("=" * 96)
print("bessel_delay_r14 —— Bessel 群延迟平坦度")
print("预注册: PREREG_D34_r14_bessel_delay.txt   门禁状态: 未过门")
print("⛔ 本件不含达标线 —— 卖点数,先量再定线")
print("=" * 96)

FC = 120.0
ORDERS = [2, 4, 6, 8]
FULL = band(20.0, 20000.0, 900)
PASSB = band(FC * 0.1, FC * 10.0, 900)     # 通带口径(fc 的 0.1×…10×)

# ── E-4 两轨 ──────────────────────────────────────────────────────────────
print("\nE-4 两轨(逐节解析 vs scipy.signal.group_delay 逐节)")
worst2 = 0.0
for n in ORDERS:
    for name, secs in (("Bessel", design_bessel_lp(FC, n)), ("BW", design_butter_lp(FC, n))):
        for s in secs:
            b = [s[0], s[1], s[2]]
            a = [s[3], s[4], s[5]]
            if s[2] == 0.0 and s[5] == 0.0:
                b, a = b[:2], a[:2]
            for f in (30.0, 120.0, 500.0, 5000.0):
                w = 2 * math.pi * f / FS
                _, g = signal.group_delay((np.array(b), np.array(a)), w=[w])
                mine = gd_section(s, f)
                worst2 = max(worst2, abs(mine - g[0]))
print(f"    两轨 max|Δτ| = {worst2:.3e} 样本 = {worst2/FS*1000:.3e} ms")
chk("E-4", worst2 / FS * 1000.0 <= 1e-3, f"两轨一致 ≤1e−3 ms(实测 {worst2/FS*1000:.2e})")

# ── P-2 第三轨:一阶节闭式 ────────────────────────────────────────────────
print("\nP-2 第三轨:一阶节闭式 τ = (1/ωc)/(1+(ω/ωc)²)")
K = math.tan(math.pi * FC / FS)
first = (K / (K + 1), K / (K + 1), 0.0, 1.0, (K - 1) / (K + 1), 0.0)
wc = 2 * math.pi * FC
w3 = 0.0
for f in band(20.0, 2000.0, 200):
    num = gd_section(first, f) / FS
    ana = (1.0 / wc) / (1.0 + (2 * math.pi * f / wc) ** 2)
    w3 = max(w3, abs(num - ana))
print(f"    闭式 vs 数值 max|Δ| = {w3*1000:.4e} ms")
chk("P-2", w3 * 1000.0 < 0.02, f"逐节求和这条路本身没写错(差 {w3*1000:.2e} ms)")

# ── P-1 阳性对照 ──────────────────────────────────────────────────────────
good = design_butter_lp(FC, 4)
bad = list(good); bad[0] = rbj_lp(FC, 5.0)
dmax = max(abs(gd_chain_ms(good, f) - gd_chain_ms(bad, f)) for f in FULL)
chk("P-1", dmax > 0.1, f"阳性对照:把一节 Q 改成 5.0 ⇒ τ 变化 {dmax:.3f} ms ⇒ 测量对系数敏感")

# ── E-1 / E-2 / E-3 主表 ──────────────────────────────────────────────────
print(f"\nE-1/E-2/E-3 主表(fc = {FC:.0f} Hz,低通支,⛔ 按【阶数】对齐)")
print(f"  {'类型/阶':<12}{'全带平坦度':>12}{'通带平坦度':>12}{'全带 max τ':>13}{'通带 max τ':>13}")
print("  " + "-" * 62)
tab = {}
for n in ORDERS:
    for name, mk in (("Bessel", design_bessel_lp), ("BW", design_butter_lp), ("LR", design_lr_lp)):
        secs = mk(FC, n)
        gf = [gd_chain_ms(secs, f) for f in FULL]
        gp = [gd_chain_ms(secs, f) for f in PASSB]
        tab[(name, n)] = (max(gf) - min(gf), max(gp) - min(gp), max(gf), max(gp))
        print(f"  {name + str(n):<12}{max(gf)-min(gf):>10.4f} ms{max(gp)-min(gp):>10.4f} ms"
              f"{max(gf):>11.4f} ms{max(gp):>11.4f} ms")

# ── F-1 / F-3 判定(⛔ 只判"卖点成不成立",不判"够不够好")──────────────────
print("\nF-1 / F-3 判定")
f1_bad, f3_bad = [], []
for n in ORDERS:
    for idx, lab in ((0, "全带"), (1, "通带")):
        if tab[("Bessel", n)][idx] >= tab[("BW", n)][idx]:
            f1_bad.append(f"n={n}/{lab}")
    if tab[("Bessel", n)][2] > tab[("LR", n)][2]:
        f3_bad.append(f"n={n}")
chk("F-1", not f1_bad,
    "「Bessel 群延迟更平坦」在**两个口径下都**成立" if not f1_bad
    else f"⛔ 证伪条件命中:{','.join(f1_bad)} 处 Bessel 不优于同阶 BW")
print(f"  F-3 绝对延迟 vs 同阶 LR:{'Bessel 更大的档 = ' + ','.join(f3_bad) if f3_bad else 'Bessel 全部 ≤ LR'}")

print("\n" + "=" * 96)
print(f"r14 结果: {'全部通过' if not fails else '未通过 ' + ','.join(fails)}")
print("⛔ 本件不给「达标/不达标」—— 是否提供 Bessel、提供哪几档,由产品定")
print("=" * 96)
raise SystemExit(0 if not fails else 1)
