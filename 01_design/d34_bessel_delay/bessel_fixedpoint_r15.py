#!/usr/bin/env python3
"""
r15:Bessel 的【定点】表现 —— 群延迟 τ + 零点完整性 + 稳定性。
⛔ 门禁状态:未过门。预注册 PREREG_D34_r15_bessel_fixedpoint.txt(⛔ 写于本文件之前)。

⛔ 本件不预设「差多少算可接受」(先量再定线),
⛔ 也不假定量化只会让 τ 变差(F-3 是一条会响的检查,不是注意事项)。
"""
import math
import importlib.util
import io
import contextlib

COEF_F = 27
I32MAX, I32MIN = (1 << 31) - 1, -(1 << 31)
fails = []


def chk(tag, ok, msg):
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag:<7s} {msg}")
    if not ok:
        fails.append(tag)


# 复用 r14 的设计与群延迟(同一实例内,⛔ 不重抄公式 —— 重抄会引入第二份可能不一致的实现)
_spec = importlib.util.spec_from_file_location("r14", "bessel_delay_r14.py")
r14 = importlib.util.module_from_spec(_spec)
with contextlib.redirect_stdout(io.StringIO()):
    try:
        _spec.loader.exec_module(r14)
    except SystemExit:
        pass


def q427(x):
    """与 chdsp_coef_from_f64 同规格:×2^27,半值远离零舍入,越界即失败。"""
    s = x * (1 << COEF_F)
    if s > I32MAX or s < I32MIN:
        return None
    return (math.floor(s + 0.5) if s >= 0 else math.ceil(s - 0.5)) / (1 << COEF_F)


def quantize_free(sec):
    """**自由量化** —— Bessel 在 C 里走的这条(chdsp_biquad.c:479 `pack()`,三个 b 各自取整)"""
    b0, b1, b2, a0, a1, a2 = sec
    out = [q427(b0), q427(b1), q427(b2), 1.0, q427(a1), q427(a2)]
    return None if any(v is None for v in out) else tuple(out)


def quantize_struct(sec):
    """**结构约束量化** —— BW/LR 的 HPF/LPF 在 C 里走的这条
    (chdsp_biquad.c:228/238 `chdsp_coef_hplp_from_f64`:只量化 b0,b1=∓2b0,b2=b0)
    ⇒ 零点由构造保证,量化后仍精确。"""
    b0, b1, b2, a0, a1, a2 = sec
    qb0 = q427(b0)
    qa1, qa2 = q427(a1), q427(a2)
    if qb0 is None or qa1 is None or qa2 is None:
        return None
    if b2 == 0.0 and a2 == 0.0:                 # 一阶节:b1 = ±b0
        return (qb0, math.copysign(qb0, b1), 0.0, 1.0, qa1, 0.0)
    return (qb0, math.copysign(2.0 * qb0, b1), qb0, 1.0, qa1, qa2)


def quantize(sec, kind):
    """⛔ 按被测物在 C 里【实际走的那条路】选量化模型,不是统一用一种。
    ⚠ 首版对三类都用自由量化 ⇒ 那不是在测 C,是在测一个不存在的实现。"""
    return quantize_free(sec) if kind == "Bessel" else quantize_struct(sec)


DESIGN = {"Bessel": r14.design_bessel_lp,
          "BW": r14.design_butter_lp,
          "LR": r14.design_lr_lp}
ORDERS = [2, 4, 6, 8]
FCS = [80.0, 120.0, 500.0, 2000.0]
BAND = r14.band(20.0, 20000.0, 600)

print("=" * 98)
print("bessel_fixedpoint_r15 —— Bessel 定点表现(τ / 零点 / 稳定性)")
print("预注册: PREREG_D34_r15_bessel_fixedpoint.txt   门禁状态: 未过门")
print("⛔ 不预设可接受线;⛔ 不假定量化单向")
print("=" * 98)

# ── F-1 前提自检:量化必须真的改变了系数 ──────────────────────────────────
n_same = n_tot = 0
for nm, mk in DESIGN.items():
    for n in ORDERS:
        for fc in FCS:
            for s in mk(fc, n):
                qs = quantize(s, nm)
                n_tot += 1
                # ⭐ 前提自检必须收窄到**本测量关心的那几个量** —— 这里是 b0/b1/b2。
                #   ⛔ 首版比的是"任一系数变了没",而 a 变了就通过 ⇒ b 是空操作也照样绿。
                if qs is not None and all(abs(s[k] - qs[k]) < 1e-18 for k in (0, 1, 2)):
                    n_same += 1
print(f"\nF-1 前提自检:{n_tot} 节中,量化后与 double 逐位相同的有 {n_same} 节")
chk("F-1", n_same < n_tot,
    f"量化确实改变了 **b 系数**({n_tot - n_same}/{n_tot} 节)⇒ 零点比对有内容")

# ── E-3 稳定性 ────────────────────────────────────────────────────────────
print("\nE-3 稳定性(量化后须仍在稳定三角内 |a2|<1 ∧ |a1|<1+a2)")
unstable = []
for nm, mk in DESIGN.items():
    for n in ORDERS:
        for fc in FCS:
            for i, s in enumerate(mk(fc, n)):
                qs = quantize(s, nm)
                if qs is None:
                    unstable.append(f"{nm}{n}@{fc:.0f}#{i}(系数越 Q4.27)")
                    continue
                a1, a2 = qs[4], qs[5]
                if s[5] == 0.0 and s[2] == 0.0:
                    if abs(a1) >= 1.0:
                        unstable.append(f"{nm}{n}@{fc:.0f}#{i}(一阶节 |a1|≥1)")
                elif not (abs(a2) < 1.0 and abs(a1) < 1.0 + a2):
                    unstable.append(f"{nm}{n}@{fc:.0f}#{i}")
print(f"    越出稳定三角的节数 = {len(unstable)}")
if unstable:
    for u in unstable[:6]:
        print(f"      {u}")
chk("E-3", not unstable, "量化后全部节仍稳定(⛔ 这是硬要求,不是观测项)")

# ── E-1 定点 τ vs 解析 τ ──────────────────────────────────────────────────
print("\nE-1 定点 τ vs 解析 τ(Δτ = 定点 − 解析)")
print(f"  {'类型/阶':<10}{'fc':>7}{'max|Δτ|':>12}{'解析平坦度':>13}{'定点平坦度':>13}{'定点更平坦?':>13}")
print("  " + "-" * 68)
better_all = True
n_cases = 0
worst_d = 0.0
for nm, mk in DESIGN.items():
    for n in ORDERS:
        for fc in FCS:
            secs = mk(fc, n)
            qsecs = [quantize(s, nm) for s in secs]
            if any(q is None for q in qsecs):
                continue
            ta = [r14.gd_chain_ms(secs, f) for f in BAND]
            tq = [r14.gd_chain_ms(qsecs, f) for f in BAND]
            d = max(abs(x - y) for x, y in zip(ta, tq))
            fa, fq = max(ta) - min(ta), max(tq) - min(tq)
            worst_d = max(worst_d, d)
            n_cases += 1
            if fq >= fa:
                better_all = False
            if fc in (80.0, 2000.0) and n in (2, 8):
                print(f"  {nm + str(n):<10}{fc:>6.0f}{d:>11.5f} ms{fa:>11.4f} ms{fq:>11.4f} ms"
                      f"{('是' if fq < fa else '否'):>12}")
print(f"\n    全部 {n_cases} 个工作点:max|Δτ| = **{worst_d:.5f} ms**")
print(f"    对 12 ms 全链预算的占比 = {worst_d/12.0*100:.4f}%")

# ── F-3 双向陷阱(lead 点名的那条会响的检查)───────────────────────────────
print("\nF-3 双向陷阱:定点是否【系统性地】优于解析")
chk("F-3", not better_all,
    "并非全部工作点都「定点更平坦」⇒ 扰动有正有负,符合预期"
    if not better_all else
    "⛔⛔ 全部工作点定点都更平坦 ⇒ **这是测量出错的信号,不是 Bessel 的优点** ⇒ 去查测量")

# ── E-2 零点完整性(⚠ Bessel 走自由量化,绕过了 CHK-5f 立的守卫)────────────
print("\nE-2 零点完整性(低通:Nyquist 零点 = b0 − b1 + b2,理想 0)")
print(f"  {'类型':<8}{'非 0 节数 / 总节数':>20}{'最坏泄漏':>14}")
print("  " + "-" * 44)
for nm, mk in DESIGN.items():
    nz = tot = 0
    worst = 0.0
    for n in ORDERS:
        for fc in FCS:
            for s in mk(fc, n):
                qs = quantize(s, nm)
                if qs is None:
                    continue
                tot += 1
                if qs[2] == 0.0 and qs[5] == 0.0:      # 一阶节:零点 = b0 − b1
                    v = qs[0] - qs[1]
                else:
                    v = qs[0] - qs[1] + qs[2]
                if v != 0.0:
                    nz += 1
                    worst = max(worst, abs(v))
    lk = 20 * math.log10(worst) if worst > 0 else -999.0
    print(f"  {nm:<8}{nz:>10} / {tot:<8}{lk:>11.2f} dB")

print("\n" + "=" * 98)
print(f"r15 结果: {'全部通过' if not fails else '未通过 ' + ','.join(fails)}")
print("=" * 98)
raise SystemExit(0 if not fails else 1)
