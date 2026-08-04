#!/usr/bin/env python3
"""
r8:分频器补全(奇数阶 + Bessel)的**设计期**验证。
⛔ 门禁状态:未过门。预注册见 PREREG_D34_r8_xover.txt(⛔ 写于本文件之前)。

⛔ 顺序纪律:**先扫界,后实现**(Y7)。本文件跑完之前,C 侧不加 Bessel。
"""
import math
import cmath

import numpy as np
from scipy import signal

FS = 48000.0
fails = []
retired = []


def chk(tag, ok, msg):
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag:<8s} {msg}")
    if not ok:
        fails.append(tag)


# ---------------------------------------------------------------- Bessel 极点(第一轨:自算)
def bessel_sections(n):
    """从**反 Bessel 多项式**求根,归一化到 −3 dB,返回 [(f0_rel, Q), ...] + 是否含一阶节。

    θ_n(s) = Σ_{k=0..n} [(2n−k)! / (2^(n−k) · k! · (n−k)!)] · s^k
    ⛔ 不 import scipy —— scipy 是第二轨(EXP-10)。
    """
    coeff = [math.factorial(2 * n - k) //
             (2 ** (n - k) * math.factorial(k) * math.factorial(n - k))
             for k in range(n + 1)]
    # numpy.roots 要降幂
    roots = np.roots(list(reversed([float(c) for c in coeff])))

    # 归一化到 −3 dB:H(s) = θ_n(0)/θ_n(s/w3);求 w3 使 |H(j·w3)| = 1/√2
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
    w3 = 0.5 * (lo + hi)

    secs, first = [], None
    used = [False] * len(roots)
    for i, r in enumerate(roots):
        if used[i]:
            continue
        if abs(r.imag) < 1e-9:
            used[i] = True
            first = abs(r.real) / w3          # 一阶节:f0_rel
        else:
            # 找共轭伙伴
            for j in range(i + 1, len(roots)):
                if not used[j] and abs(roots[j] - r.conjugate()) < 1e-7:
                    used[i] = used[j] = True
                    w0 = abs(r) / w3
                    Q = abs(r) / (2.0 * abs(r.real))
                    secs.append((w0, Q))
                    break
    secs.sort(key=lambda t: t[1])
    return secs, first


# ---------------------------------------------------------------- RBJ 双二阶 + 一阶(设计期)
def rbj_lp_hp(f0, Q, hp):
    w = 2 * math.pi * f0 / FS
    c, s = math.cos(w), math.sin(w)
    al = s / (2.0 * Q)
    a0 = 1 + al
    if hp:
        return ((1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0, 1.0, -2 * c / a0, (1 - al) / a0)
    return ((1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0, 1.0, -2 * c / a0, (1 - al) / a0)


def first_order(f0, hp):
    """一阶 LPF/HPF(双线性,预畸)。以双二阶形式返回(b2 = a2 = 0)。"""
    K = math.tan(math.pi * f0 / FS)
    if hp:
        return (1.0 / (K + 1), -1.0 / (K + 1), 0.0, 1.0, (K - 1) / (K + 1), 0.0)
    return (K / (K + 1), K / (K + 1), 0.0, 1.0, (K - 1) / (K + 1), 0.0)


def H(bq, w):
    b0, b1, b2, a0, a1, a2 = bq
    z1 = cmath.exp(-1j * w)
    z2 = z1 * z1
    return (b0 + b1 * z1 + b2 * z2) / (a0 + a1 * z1 + a2 * z2)


def bessel_poles_norm(n):
    """归一化到 −3 dB 的**模拟** Bessel 极点(⛔ 不 import scipy)。"""
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
    w3 = 0.5 * (lo + hi)
    return [complex(r) / w3 for r in roots]


def design_bessel(fc, order, hp):
    """数字 Bessel:**模拟原型 → 单次预畸 → 双线性**(⛔ 不是逐节 RBJ)。

    ⛔⛔ 这是 r8 的核心更正(证伪条件 F-2 命中后定位出来的):
    ------------------------------------------------------------------
    初版把每一节按 (f0 = fc·ω0_rel, Q) 交给 RBJ 设计。**那是错的**,两处:
      ① 高通:低通→高通要做 s → ωa/s ⇒ 各节频率应 **fc / ω0_rel**,不是 fc · ω0_rel。
         初版把方向搞反 ⇒ 8 阶 HP 与第二轨差 **91.7 dB**。
      ② 低通:RBJ **在每节自己的 f0 上预畸**;而正确做法是对整支滤波器
         **在 fc 上预畸一次**再双线性。双线性是非线性映射 ⇒ 两者不等,
         且各节 ω0_rel 离 1 越远、阶数越高,差越大(实测 2 阶 0.015 → 8 阶 0.277 dB)。
    ⇒ ⭐ 为什么 Butterworth / LR 用逐节 RBJ **是对的**:它们**所有节共用同一个 ω0 = ωc**
      ⇒ "逐节各自预畸" 与 "整支预畸一次" 恰好重合。**Bessel 各节 ω0 互不相同 ⇒ 重合消失。**
    ⇒ ∴ Bessel **不能复用** `chdsp_bq_design(FT_LPF, f0, Q)` 这条路径。
    """
    c = 2.0 * FS
    wa = c * math.tan(math.pi * fc / FS)          # 单次预畸
    p = bessel_poles_norm(order)
    if hp:
        poles = [wa / pk for pk in p]
        zeros = [0.0 + 0j] * order                # 高通:s^n
    else:
        poles = [wa * pk for pk in p]
        zeros = []
    # 双线性:z = (1 + s/c)/(1 − s/c);缺的零点补到 z = −1
    zd = [(1 + zk / c) / (1 - zk / c) for zk in zeros]
    pd = [(1 + pk / c) / (1 - pk / c) for pk in poles]
    zd += [-1.0 + 0j] * (len(pd) - len(zd))
    # 增益:LP 在 z=1 归一,HP 在 z=−1 归一
    zt = 1.0 + 0j if not hp else -1.0 + 0j
    num = 1.0 + 0j
    for zk in zd:
        num *= (zt - zk)
    den = 1.0 + 0j
    for pk in pd:
        den *= (zt - pk)
    k = abs(den / num)

    # ---- 分组成节 ----
    # ⛔ 首跑这里错了一次,留痕:原 take_pair 对**实数**根只取【一个】,
    #    于是双二阶节拿到 (1 + z⁻¹) 而不是 (1 + z⁻¹)² ⇒ 每个双二阶节少一个 z=−1 零点
    #    ⇒ 增益差恰好 2 倍 = 6.0206 dB/节对 —— 实测 LP 阶 2/3→6.02、4/5→12.04、
    #      6/7→18.06、8→24.08 dB,**正好是 6.0206 的整数倍**,这就是它的指纹。
    #    ⇒ 修法:先把极点分组,再按【该组要几个零点】去取零点(2 个或 1 个)。
    def split(lst):
        pairs, reals, used = [], [], [False] * len(lst)
        for i, v in enumerate(lst):
            if used[i]:
                continue
            if abs(v.imag) < 1e-9:
                used[i] = True
                reals.append(v.real)
                continue
            for j in range(i + 1, len(lst)):
                if not used[j] and abs(lst[j] - v.conjugate()) < 1e-7:
                    used[i] = used[j] = True
                    pairs.append(v)
                    break
            else:
                used[i] = True
                reals.append(v.real)
        return pairs, reals

    ppair, preal = split(pd)
    zpair, zreal = split(zd)

    def take_zeros(want):
        """取 want(1 或 2)个零点,返回 (b1, b2)"""
        if want == 2:
            if zpair:
                z = zpair.pop(0)
                return -2.0 * z.real, abs(z) ** 2
            if len(zreal) >= 2:
                r1, r2 = zreal.pop(0), zreal.pop(0)
                return -(r1 + r2), r1 * r2
            if len(zreal) == 1:
                r1 = zreal.pop(0)
                return -r1, 0.0
            return 0.0, 0.0
        if zreal:
            r1 = zreal.pop(0)
            return -r1, 0.0
        if zpair:                      # 不该发生:一阶节配不上共轭对
            z = zpair.pop(0)
            zpair.insert(0, z)
        return 0.0, 0.0

    out = []
    for p in ppair:
        b1, b2 = take_zeros(2)
        out.append([1.0, b1, b2, 1.0, -2.0 * p.real, abs(p) ** 2])
    for r in preal:
        b1, b2 = take_zeros(1)
        out.append([1.0, b1, b2, 1.0, -r, 0.0])
    if zpair or zreal:
        raise AssertionError(f"零点未用尽:pair={len(zpair)} real={len(zreal)} "
                             f"⇒ 分组错误,⛔ 不得当作通过")
    for i in range(3):
        out[0][i] *= k
    return [tuple(s) for s in out]


def butter_sections(order):
    """Butterworth 各节 Q;奇数阶另含一个一阶节。

    ⭐⭐ Q_k = 1 / (2·**sin**(π(2k+1)/(2n)))   ⛔ 不是 cos
    ----------------------------------------------------------------
    ⚠ C 侧 `chdsp_biquad.c:butter_q()` 写的是 **cos**。对**偶数**阶它给出的是
      **同一个 Q 集合、只是顺序相反**(证:sin x = cos(π/2−x),而
      π/2 − π(2k+1)/(2n) = π(2k′+1)/(2n) 当 k′ = n/2−k−1,偶数 n 时 k′ 必为合法整数)
      ⇒ 级联顺序不改变总传函 ⇒ **C 侧目前是对的**。
    ⛔ 但对**奇数**阶两式不等:n=3 时 cos 式给 0.5774,正确值是 1.0。
      ⇒ **本轮要加奇数阶,若照搬 cos 式会静默产出错的滤波器。**
      ⇒ 这条已写进 C 侧改动(butter_q 改 sin,并加偶数阶逐位回归 F-4)。
    """
    qs = [1.0 / (2.0 * math.sin(math.pi * (2 * i + 1) / (2.0 * order)))
          for i in range(order // 2)]
    return qs, (order % 2 == 1)


def design_butter(fc, order, hp):
    qs, has_first = butter_sections(order)
    out = [first_order(fc, hp)] if has_first else []
    out += [rbj_lp_hp(fc, q, hp) for q in qs]
    return out


def design_lr(fc, order, hp):
    """LR{order} = (BW_{order/2})² ⇒ 把 BW 的每一节【串两遍】。
    ⚠ 一阶节平方 = 两个一阶节级联(= Q=0.5 的双二阶),本函数直接串两个一阶节。"""
    bo = order // 2
    return design_butter(fc, bo, hp) * 2


print("=" * 90)
print("xover_r8 —— 分频器补全(奇数阶 + Bessel)· 设计期验证")
print("预注册: PREREG_D34_r8_xover.txt   门禁状态: 未过门")
print("=" * 90)

# ---------------------------------------------------------------- EXP-9
print("\nEXP-9  Bessel 各节 max|b|(判据 <16;预测 ≤2)")
print("-" * 90)
worst_b, worst_at = 0.0, None
for order in range(1, 9):
    for hp in (0, 1):
        om = 0.0
        for i in range(60):
            fc = 20.0 * (1000.0 ** (i / 59.0))
            for bq in design_bessel(fc, order, hp):
                m = max(abs(bq[0]), abs(bq[1]), abs(bq[2]))
                if m > om:
                    om = m
                if m > worst_b:
                    worst_b, worst_at = m, (order, 'HP' if hp else 'LP', fc)
        print(f"    order={order} {'HP' if hp else 'LP'}: max|b| = {om:.6f}")
print(f"\n    全域最大 = {worst_b:.6f} @ order={worst_at[0]} {worst_at[1]} fc={worst_at[2]:.1f} Hz")
chk("EXP-9", worst_b < 16.0, f"Bessel 全族 max|b| = {worst_b:.6f} < 16(Q4.27 装得下)")
chk("EXP-9p", worst_b <= 2.0 + 1e-9,
    f"⭐ 预测兑现:≤2 —— 与 D34 §3.2.0 的 LPF/HPF 解析界一致(换 (f0,Q) 不换结构)")

# ---------------------------------------------------------------- EXP-9b
print("\nEXP-9b 一阶节 max|b|(判据 ≤1)")
print("-" * 90)
wb1 = 0.0
for i in range(200):
    fc = 20.0 * (1000.0 ** (i / 199.0))
    for hp in (0, 1):
        bq = first_order(fc, hp)
        wb1 = max(wb1, abs(bq[0]), abs(bq[1]), abs(bq[2]))
print(f"    一阶节全域 max|b| = {wb1:.6f}")
chk("EXP-9b", wb1 <= 1.0 + 1e-12, f"一阶节 max|b| = {wb1:.6f} ≤ 1")

# ---------------------------------------------------------------- EXP-10 两轨
print("\nEXP-10 两轨交叉核:自算 Bessel 极点 vs scipy.signal.bessel(判据 ≤0.01 dB)")
print("-" * 90)
worst_d, worst_case = 0.0, None
for order in (1, 2, 3, 4, 5, 6, 7, 8):
    for hp in (0, 1):
        fc = 1000.0
        mine = design_bessel(fc, order, hp)
        # 第二轨:scipy,数字域,norm='mag3db' 与我的 −3 dB 归一化同口径
        sos = signal.bessel(order, fc / (FS / 2), btype='highpass' if hp else 'lowpass',
                            output='sos', norm='mag')
        d = 0.0
        for i in range(400):
            f = 20.0 * (1000.0 ** (i / 399.0))
            w = 2 * math.pi * f / FS
            hm = 1.0
            for bq in mine:
                hm *= H(bq, w)
            hs = 1.0
            for row in sos:
                hs *= H(tuple(row), w)
            a, b = abs(hm), abs(hs)
            if a > 1e-12 and b > 1e-12:
                d = max(d, abs(20 * math.log10(a / b)))
        if d > worst_d:
            worst_d, worst_case = d, (order, 'HP' if hp else 'LP')
        print(f"    order={order} {'HP' if hp else 'LP'}: max|Δ| = {d:.6f} dB")
print(f"\n    全域最大 = {worst_d:.6f} dB @ order={worst_case[0]} {worst_case[1]}")
chk("EXP-10", worst_d <= 0.01, f"两轨幅频 max|Δ| = {worst_d:.6f} dB ≤ 0.01")

# 阳性对照:把一节 Q 改错 ⇒ 必须报出差异
bad = design_bessel(1000.0, 4, 0)
bad[0] = rbj_lp_hp(1000.0, 5.0, 0)
sos = signal.bessel(4, 1000.0 / (FS / 2), btype='lowpass', output='sos', norm='mag')
dbad = 0.0
for i in range(400):
    f = 20.0 * (1000.0 ** (i / 399.0))
    w = 2 * math.pi * f / FS
    hm = 1.0
    for bq in bad:
        hm *= H(bq, w)
    hs = 1.0
    for row in sos:
        hs *= H(tuple(row), w)
    a, b = abs(hm), abs(hs)
    if a > 1e-12 and b > 1e-12:
        dbad = max(dbad, abs(20 * math.log10(a / b)))
chk("EXP-10p", dbad > 0.01,
    f"阳性对照:人为把一节 Q 改成 5.0 ⇒ 两轨差 {dbad:.3f} dB ⇒ EXP-10 不是恒真")

# ---------------------------------------------------------------- EXP-11 求和平坦度
print("\nEXP-11 分频 LP+HP 求和平坦度(观测,⛔ 不设通过线)")
print("-" * 90)
print(f"    {'类型/阶':<18}{'同相求和 max|偏离|':>22}{'反相求和 max|偏离|':>22}")


def sum_flatness(secs_lp, secs_hp):
    best = []
    for sgn in (+1.0, -1.0):
        d = 0.0
        for i in range(600):
            f = 20.0 * (1000.0 ** (i / 599.0))
            w = 2 * math.pi * f / FS
            hl = hh = 1.0
            for bq in secs_lp:
                hl *= H(bq, w)
            for bq in secs_hp:
                hh *= H(bq, w)
            m = abs(hl + sgn * hh)
            if m > 1e-12:
                d = max(d, abs(20 * math.log10(m)))
        best.append(d)
    return best


fc = 1000.0
for order in (2, 4, 6, 8):
    a, b = sum_flatness(design_lr(fc, order, 0), design_lr(fc, order, 1))
    print(f"    {'LR' + str(order):<18}{a:>20.4f} dB{b:>20.4f} dB")
for order in (1, 3, 5):
    a, b = sum_flatness(design_butter(fc, order, 0), design_butter(fc, order, 1))
    print(f"    {'BW' + str(order) + '(奇)':<18}{a:>20.4f} dB{b:>20.4f} dB")
for order in (2, 3, 4, 6, 8):
    a, b = sum_flatness(design_bessel(fc, order, 0), design_bessel(fc, order, 1))
    print(f"    {'Bessel' + str(order):<18}{a:>20.4f} dB{b:>20.4f} dB")

bes4 = sum_flatness(design_bessel(fc, 4, 0), design_bessel(fc, 4, 1))
chk("EXP-11", min(bes4) > 0.01,
    f"⭐ 预测兑现:Bessel 求和**不平坦**(4 阶最好一相 {min(bes4):.3f} dB)"
    f" ⇒ LR 的「阶数 mod 4 定极性」规则**对 Bessel 不适用**")

print("\n" + "=" * 90)
print(f"r8 结果: {'全部通过' if not fails else '未通过 ' + ','.join(fails)}")
print("=" * 90)
raise SystemExit(0 if not fails else 1)
