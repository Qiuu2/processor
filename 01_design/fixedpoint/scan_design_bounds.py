#!/usr/bin/env python3
"""设计推导的可复现件:①系数上界扫描 ②DF2 内节点峰值增益 ③噪声增益 NG ④EF 前后噪声底预测。

⛔ 门禁状态:未过门。
⚠ 本脚本产出的是**设计推导**(选格式用),不是验收证据;验收证据在 check_fixed.c / results_fp_r*.txt。
   立此文件的理由:约定文档 §3.2 / §3.2.1 / §5.3 引用的数原先只存在于临时目录,
   **没有 deps 行的数不得被任何文档引用为证据**(团队纪律)。⇒ 归档并可复现。

用法: python3 scan_design_bounds.py > results_design_bounds.txt
"""
import numpy as np, itertools, math, hashlib, os, sys

FS = 48000.0

def rbj_peaking(f0, Q, gdb, fs=FS):
    A = 10 ** (gdb / 40); w0 = 2 * np.pi * f0 / fs
    al = np.sin(w0) / (2 * Q); c = np.cos(w0); a0 = 1 + al / A
    return np.array([1 + al * A, -2 * c, 1 - al * A]) / a0, np.array([1.0, -2 * c / a0, (1 - al / A) / a0])

def rbj_lowshelf(f0, S, gdb, fs=FS):
    A = 10 ** (gdb / 40); w0 = 2 * np.pi * f0 / fs
    al = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2); c = np.cos(w0); t = 2 * np.sqrt(A) * al
    a0 = (A + 1) + (A - 1) * c + t
    return (np.array([A * ((A + 1) - (A - 1) * c + t), 2 * A * ((A - 1) - (A + 1) * c),
                      A * ((A + 1) - (A - 1) * c - t)]) / a0,
            np.array([1.0, -2 * ((A - 1) + (A + 1) * c) / a0, ((A + 1) + (A - 1) * c - t) / a0]))

def rbj_highshelf(f0, S, gdb, fs=FS):
    A = 10 ** (gdb / 40); w0 = 2 * np.pi * f0 / fs
    al = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2); c = np.cos(w0); t = 2 * np.sqrt(A) * al
    a0 = (A + 1) - (A - 1) * c + t
    return (np.array([A * ((A + 1) + (A - 1) * c + t), -2 * A * ((A - 1) + (A + 1) * c),
                      A * ((A + 1) + (A - 1) * c - t)]) / a0,
            np.array([1.0, 2 * ((A - 1) - (A + 1) * c) / a0, ((A + 1) - (A - 1) * c - t) / a0]))

def rbj_hpf(f0, Q, fs=FS):
    w0 = 2 * np.pi * f0 / fs; al = np.sin(w0) / (2 * Q); c = np.cos(w0); a0 = 1 + al
    return np.array([(1 + c) / 2, -(1 + c), (1 + c) / 2]) / a0, np.array([1.0, -2 * c / a0, (1 - al) / a0])

def rbj_lpf(f0, Q, fs=FS):
    w0 = 2 * np.pi * f0 / fs; al = np.sin(w0) / (2 * Q); c = np.cos(w0); a0 = 1 + al
    return np.array([(1 - c) / 2, 1 - c, (1 - c) / 2]) / a0, np.array([1.0, -2 * c / a0, (1 - al) / a0])

f_grid = np.unique(np.concatenate([np.geomspace(20, 20000, 400), [20.0, 20000.0]]))
q_grid = np.array([0.3, 0.4, 0.5, 0.7071, 1.0, 1.4, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0])
g_grid = np.arange(-15, 15.5, 0.5)
s_grid = np.array([0.3, 0.4, 0.5, 0.7071, 0.85, 1.0])

def scan(name, fn, grids):
    bb, ba, ptb = 0.0, 0.0, None
    for pt in itertools.product(*grids):
        b, a = fn(*pt)
        if not (np.all(np.isfinite(b)) and np.all(np.isfinite(a))):
            continue
        mb = float(np.max(np.abs(b))); ma = float(np.max(np.abs(a[1:])))
        if mb > bb: bb, ptb = mb, pt
        if ma > ba: ba = ma
    print(f"  {name:34s} max|b| = {bb:9.4f} @ {tuple(round(float(x),4) for x in ptb)}    max|a| = {ba:.6f}")
    return bb

print("=" * 92)
print("results_design_bounds  —  设计推导的可复现件(约定文档 §3.2 / §3.2.1 / §5.3 / §5.4 的来源)")
print(f"deps: scan_design_bounds.py@{hashlib.sha256(open(__file__,'rb').read()).hexdigest()[:16]}")
print(f"numpy {np.__version__}   fs = {FS} Hz   门禁状态: 未过门")
print("=" * 92)

print("\n【A】系数上界扫描(约定文档 §3.2)")
res = {}
res['PEQ 峰型 Q∈[0.3,20] G±15']   = scan('PEQ 峰型 Q∈[0.3,20] G±15', rbj_peaking,  [f_grid, q_grid, g_grid])
res['低架 S∈[0.3,1.0] G±15']      = scan('低架 S∈[0.3,1.0] G±15',   rbj_lowshelf, [f_grid, s_grid, g_grid])
res['高架 S∈[0.3,1.0] G±15']      = scan('高架 S∈[0.3,1.0] G±15',   rbj_highshelf,[f_grid, s_grid, g_grid])
res['HPF Q∈[0.3,20]']             = scan('HPF Q∈[0.3,20]',           rbj_hpf,      [f_grid, q_grid])
res['LPF Q∈[0.3,20]']             = scan('LPF Q∈[0.3,20]',           rbj_lpf,      [f_grid, q_grid])
mb = max(res.values())
print(f"\n  ⇒ 全族 max|b| = {mb:.4f}  ⇒ 需整数位 m = {math.ceil(math.log2(mb))} ⇒ 系数格式 Q{math.ceil(math.log2(mb))}.{31-math.ceil(math.log2(mb))}")
print(f"  ⇒ a 系数的界是【数学界】(稳定三角):|a1| < 1+a2 < 2、|a2| < 1,构造上不可超越")

print("\n【B】该界对哪个参数敏感(约定文档 §3.2.1)")
print(f"  高架 @20Hz  S=1.0 G=+15dB : max|b| = {np.max(np.abs(rbj_highshelf(20,1.0,15)[0])):.4f}")
print(f"  高架 @20Hz  S=2.0 G=+15dB : max|b| = {np.max(np.abs(rbj_highshelf(20,2.0,15)[0])):.4f}   ⇒ S 翻倍只动 +0.0144")
print(f"  高架 @20Hz  S=1.0 G=+18dB : max|b| = {np.max(np.abs(rbj_highshelf(20,1.0,18)[0])):.4f}   ⇒ 增益才是驱动量")
lo, hi = 15.0, 40.0
for _ in range(80):
    m = (lo + hi) / 2
    if np.max(np.abs(rbj_highshelf(20, 1.0, m)[0])) < 16.0: lo = m
    else: hi = m
print(f"  ⇒ **Q4.27 的硬包络:架式增益 ≤ {lo:.3f} dB**(该点 max|b| = 16.000,配置 = 高架/20Hz/S=1.0/fs=48k)")

print("\n【C】DF2 内部节点峰值增益 max|1/A|(约定文档 §5.3:DF2 被否决的量化理由)")
def peak_inv_a(a, n=1 << 16):
    w = np.linspace(0, np.pi, n)
    z = np.exp(-1j * w)
    return float(np.max(1.0 / np.abs(1 + a[1] * z + a[2] * z * z)))
cases = [("PEQ 20Hz  Q=20 G=+15dB", rbj_peaking(20, 20, 15)),
         ("PEQ 20Hz  Q=20 G=0dB",   rbj_peaking(20, 20, 0)),
         ("HPF 20Hz  Q=0.7071",     rbj_hpf(20, 0.7071)),
         ("PEQ 1kHz  Q=20 G=0dB",   rbj_peaking(1000, 20, 0))]
for nm, (b, a) in cases:
    p = peak_inv_a(a)
    print(f"  {nm:26s} max|1/A| = {p:11.4e} = {20*math.log10(p):7.2f} dB  ⇒ DF2 需额外 {math.ceil(math.log2(p))} bit 整数位")
print("  ⇒ 32-bit 字长装不下 ⇒ DF2/DF2T 在本参数范围内不可用,取 DF1")

print("\n【D】噪声增益 NG = Σ|h_{1/A}|² 与无 EF 时的噪声底预测(约定文档 §5.4 的「EF 关」列)")
def ng(a, n=400000):
    y1 = y2 = 0.0; s = 0.0
    for i in range(n):
        x = 1.0 if i == 0 else 0.0
        y = x - a[1] * y1 - a[2] * y2
        s += y * y; y2 = y1; y1 = y
    return s
q = 2.0 ** -27
flat = 10 * math.log10(q * q / 12)
print(f"  内部样本 Q4.27 ⇒ q²/12 = {flat:.2f} dBFS")
for nm, (b, a) in [("PEQ 20Hz Q=20 G=+15dB", rbj_peaking(20,20,15)),
                   ("PEQ 100Hz Q=20 G=+15dB", rbj_peaking(100,20,15)),
                   ("HPF 20Hz Q=0.7071", rbj_hpf(20,0.7071)),
                   ("HPF 80Hz Q=0.7071", rbj_hpf(80,0.7071)),
                   ("低架 20Hz S=1 G=+15dB", rbj_lowshelf(20,1.0,15))]:
    g = ng(a)
    print(f"  {nm:26s} NG = {10*math.log10(g):6.2f} dB  ⇒ 无 EF 噪声底预测 = {flat + 10*math.log10(g):8.2f} dBFS")
print(f"  ⇒ 有 EF 时噪声传函 ≡ 1 ⇒ 预测恒为 {flat:.2f} dBFS(实测见 results_fp_r3.txt CHK-4)")
print("\n" + "=" * 92)
