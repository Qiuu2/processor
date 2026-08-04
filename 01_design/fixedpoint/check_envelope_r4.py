#!/usr/bin/env python3
"""
r4 整改验证:增益硬包络该取 18.0618 还是 18.089?
⛔ 门禁状态:未过门(未经独立 critic 评审)。

缘起
----
critic MAJOR-4 要求把「经验扫描界 11.2148」的残留改成解析界。改完做反扫时,
发现**由旧值推出的那个数**(增益包络 18.089 / 18.09 dB)也在库里传播,
而 critic 的反扫特征串(`11.2148` ∧ `经验扫描界` ∧ `S>1`)一个都不命中它。

它出现在 6 处,其中最要紧的一处是台账里那句
「建议把『架式/PEQ 增益上限 ≤ ±15 dB(硬上限 +18.09 dB)』写进 D2 参数字典并锁死」
—— 即:**它是要被写进单一事实源、被锁死的那个数**。

本脚本回答两个问题(⛔ 不 import 被审件,RBJ 独立重写):
  Q1  两个候选值各自对应的 max|b| 是多少?哪个真的在 Q4.27(|c| < 16)之内?
  Q2  18.089 的适用域是什么?域外它还成立吗?

结论(见 results_envelope_r4.txt)
--------------------------------
  · 18.0618 = 20·log10(8) 是**解析包络**:2·10^(G/20) 恰好 = 16,对任意 f/Q/S 成立。
  · 18.089  是**扫描二分求出的越界点**:在该值处实扫 max|b| = 16.000243 ⇒ **已越界**。
    ⇒ 把它当"硬上限"写进字典 = 字典允许的最大值本身就会让系数计算硬失败。
  · 且 18.089 只在扫描域 f∈[20,20k] 内成立;f=1 Hz 处 max|b| = 16.0477。
  ⇒ ∴ 可锁的只有 18.0618。
"""
import math

FS = 48000.0


def shelf_hi(f, S, G, fs=FS):
    """RBJ 高架,返回归一化后的 max(|b0|,|b1|,|b2|)。独立重写,不 import 被审件。"""
    A = 10.0 ** (G / 40.0)
    w = 2.0 * math.pi * f / fs
    c, s = math.cos(w), math.sin(w)
    al = s / 2.0 * math.sqrt((A + 1.0 / A) * (1.0 / S - 1.0) + 2.0)
    sa = math.sqrt(A)
    b0 = A * ((A + 1.0) + (A - 1.0) * c + 2.0 * sa * al)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * c)
    b2 = A * ((A + 1.0) + (A - 1.0) * c - 2.0 * sa * al)
    a0 = (A + 1.0) - (A - 1.0) * c + 2.0 * sa * al
    return max(abs(b0 / a0), abs(b1 / a0), abs(b2 / a0))


def scan(G, f_lo, f_hi, nf=8000, ns=70):
    best, arg = 0.0, None
    for i in range(nf + 1):
        f = f_lo + i * (f_hi - f_lo) / nf
        for j in range(ns + 1):
            S = 0.3 + j * (1.0 - 0.3) / ns
            v = shelf_hi(f, S, G)
            if v > best:
                best, arg = v, (f, S)
    return best, arg


LIMIT = 16.0
rc = 0
print("=" * 78)
print("check_envelope_r4 —— 增益硬包络 18.0618 vs 18.089")
print("门禁状态: 未过门")
print("=" * 78)

print("\n### Q1. 解析界 2·10^(G/20) 对 Q4.27(|c| < 16)")
print(f"{'G_max [dB]':>12} | {'解析界':>12} | 判定")
for G in (15.0, 18.0, 18.0618, 18.089, 18.09):
    b = 2.0 * 10.0 ** (G / 20.0)
    print(f"{G:>12.4f} | {b:>12.6f} | {'⛔ ≥16 装不下' if b >= LIMIT else 'OK'}")
exact = 20.0 * math.log10(8.0)
print(f"\n  解 2·10^(G/20) = 16  ⇒  G = 20·log10(8) = {exact:.10f} dB")
assert abs(exact - 18.0618) < 5e-5, "解析包络与文档写的 18.0618 不符"

print("\n### Q2. 扫描域 f∈[20,20k](= §3.2.1 声明的域,也是 18.089 的来源域)")
print(f"{'G_max [dB]':>12} | {'实扫 max|b|':>12} | {'@f [Hz]':>10} | 判定")
for G in (18.0618, 18.089, 18.10):
    b, arg = scan(G, 20.0, 20000.0)
    print(f"{G:>12.4f} | {b:>12.6f} | {arg[0]:>10.2f} | "
          f"{'⛔ 越 16' if b >= LIMIT else 'OK'}")
    if G == 18.089 and b < LIMIT:
        print("  ⛔ 证伪:18.089 在其来源域内竟未越界 ⇒ 本脚本的结论不成立")
        rc = 1

print("\n### Q3. 域外(f 低到 1 Hz)—— 18.089 的适用范围声明是否成立")
for G in (18.0618, 18.089):
    b, arg = scan(G, 1.0, 20000.0)
    print(f"  G={G:<8} f∈[1,20k]: max|b| = {b:.6f} @ f={arg[0]:.2f} Hz  "
          f"{'⛔ 越 16' if b >= LIMIT else 'OK(解析界保证)'}")

print("\n### 判定")
b_618, _ = scan(18.0618, 20.0, 20000.0)
b_089, _ = scan(18.089, 20.0, 20000.0)
ok = (b_618 < LIMIT) and (b_089 >= LIMIT)
print(f"  18.0618 处未越界 ({b_618:.6f} < 16) ∧ 18.089 处已越界 ({b_089:.6f} ≥ 16) = {ok}")
if ok:
    print("  ⇒ PASS:可锁的包络是 18.0618;⛔ 18.089 是越界点,不是上限")
else:
    print("  ⛔ FAIL:两个候选值的相对位置与整改结论不符")
    rc = 1

# 阳性对照:证明本脚本的判据认得出"没有越界"这件事
b_ctrl, _ = scan(10.0, 20.0, 20000.0)
print(f"\n  阳性对照(G=10 dB,应远在界内):max|b| = {b_ctrl:.6f} "
      f"⇒ {'✓ 判据认得出界内' if b_ctrl < LIMIT else '⛔ 判据无分辨力'}")
if b_ctrl >= LIMIT:
    rc = 1

print("=" * 78)
raise SystemExit(rc)
