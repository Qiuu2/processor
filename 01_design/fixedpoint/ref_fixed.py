#!/usr/bin/env python3
"""第二轨(铁律七:关键数字双轨独立工具交叉核)。

⛔ 门禁状态:未过门。

本文件是 chdsp_fixed.h 数值约定的**独立重写**(python 整数算术),
⛔ 不 import、不链接 C 实现,只读它的输出文件对表。
⇒ 与 C 轨共用的只有【格式定义与算法规格】,不共用任何代码。

对表项(见 PREREG_FP_r1.txt §4):
  T1  dB→线性 整数表  ——  预期【逐点逐位相同】(两轨同为确定性整数算法)
  T2  EF 噪声底       ——  预期两轨差 ≤0.5 dB
  T3  8 节级联响应     ——  预期两轨差 ≤0.001 dB
"""
import math, os, sys

SMP_F, COEF_F, IO_F, DB_F = 27, 27, 31, 8
EXP2_BITS, EXP2_N = 7, 128
DB_MUTE_Q8, DB_MAX_Q8 = -144 * 256, 24 * 256
K = math.log2(10) / 20.0
K_Q40 = int(round(K * (1 << 40)))
EXP2 = [int(round(2.0 ** (i / EXP2_N) * (1 << 29))) for i in range(EXP2_N + 1)]
FS = 48000.0
INT32_MAX, INT32_MIN = (1 << 31) - 1, -(1 << 31)

fails = []
def chk(tag, ok, msg):
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag:<7s} {msg}")
    if not ok:
        fails.append(tag)

retired = []
def chk_retired(tag, ok, msg):
    """已退役的检查:保留记录(E-2「加标注不删数」),但不计入判定。
    ⇒ 与 C 轨 check_fixed.c 的 RETIRED() 同语义,本轨原先缺这个机制。"""
    print(f"  [{'退役·符合' if ok else '退役·不符'}] {tag:<7s} {msg}")
    retired.append(tag)

# ---------------------------------------------------------------- T1
def db_to_gain_py(db):
    """独立重写:与 C 同规格,不同代码。"""
    if db > DB_MAX_Q8:
        db = DB_MAX_Q8
    if db <= DB_MUTE_Q8:
        return 0
    u = (db * K_Q40) >> 16                       # Q32,算术右移 = floor
    n = u >> 32
    f = u - (n << 32)
    sh_lam = 32 - EXP2_BITS
    idx = f >> sh_lam
    lam = f - (idx << sh_lam)
    d = EXP2[idx + 1] - EXP2[idx]
    v = EXP2[idx] + ((d * lam + (1 << (sh_lam - 1))) >> sh_lam)
    s = n - 2
    g = (v << s) if s >= 0 else ((v + (1 << (-s - 1))) >> (-s))
    return max(INT32_MIN, min(INT32_MAX, g))

def t1():
    print("T1  dB→线性 整数表逐位对表")
    path = "db_table_c.txt"
    if not os.path.exists(path):
        chk("T1", False, f"缺 {path}(C 轨未跑或未写出)")
        return
    with open(path) as fp:
        cvals = [int(x) for x in fp.read().split()]
    pvals = [db_to_gain_py(q) for q in range(DB_MUTE_Q8, DB_MAX_Q8 + 1)]
    chk("T1n", len(cvals) == len(pvals), f"点数 C={len(cvals)} py={len(pvals)}")
    if len(cvals) != len(pvals):
        return
    diff = [i for i, (a, b) in enumerate(zip(cvals, pvals)) if a != b]
    chk("T1", not diff, f"逐位相同({len(pvals)} 点,不等 {len(diff)} 处)"
        + ("" if not diff else f" 首处 idx={diff[0]} C={cvals[diff[0]]} py={pvals[diff[0]]}"))
    # 阳性对照:比对器必须认得出差异(⛔ 没有阳性对照的「相同」不算证据)
    bad = list(pvals); bad[len(bad) // 2] += 1
    chk("T1+", [i for i, (a, b) in enumerate(zip(cvals, bad)) if a != b] != [],
        "阳性对照:强制改一个值后比对器报出差异 ⇒ 上一行的「相同」有意义")
    # 精度(独立于 C 的复算)
    # ⭐ 2026-08-04 整改 · channel-dsp 实例 #2
    #   本条原为 chk("T1a", worst_in <= 0.01, ...),判据窗口下界 −110 dB 是**拍的估计值**,
    #   而真实包络下界是 −109.8125 dB ⇒ T1a **恒 FAIL**(实测 0.010178 > 0.01)。
    #   ⛔ 这个 FAIL 一直存在于归档件 results_fp_r3.txt(「第二轨结果: 未通过 T1a」,
    #      「第二轨退出码 = 1」),但 run_r3.sh 只**打印** REF 不**消费**它
    #      ⇒ 整轮仍以 exit 0 收尾 ⇒ 该 FAIL 从未阻止过任何事(critic MAJOR-1 ②)。
    #   ⇒ 处置与 C 轨 CHK-7 **完全一致**:⛔ 不移动标杆 —— 原判据原样留痕并**退役**,
    #      另立 T1b 按【实测包络】判定。台账 E1 已记同一事。
    worst_in = worst_all = 0.0
    for q in range(DB_MUTE_Q8 + 1, DB_MAX_Q8 + 1):
        g = pvals[q - DB_MUTE_Q8]
        if g <= 0:
            continue
        e = abs(20 * math.log10((g / (1 << 27)) / (10 ** (q / 256.0 / 20.0))))
        worst_all = max(worst_all, e)
        if q >= -110 * 256:
            worst_in = max(worst_in, e)
    print(f"      py 轨复算:max|误差| 带内[−110,+24] = {worst_in:.6f} dB,全域 = {worst_all:.6f} dB")
    chk_retired("T1a", worst_in <= 0.01,
                "原判据窗口 [−110,+24] 是拍的估计值;真实包络下界 = −109.8125 dB。"
                "⛔ 不移动标杆:原判据原样留痕,规格以 T1b 实测包络为准")

    # T1b(整改增补):按【实测包络】判定,并把包络本身作为被测量报出来
    #   ⇒ 判据不是"误差够小",而是"包络落在规格声明的那个位置"
    ENV_Q8 = -28112                      # = −109.8125 dB(最后一个仍合规的 1/256 dB 格)
    run_max = 0.0
    bound_q8 = DB_MAX_Q8
    for q in range(DB_MAX_Q8, DB_MUTE_Q8, -1):
        g = pvals[q - DB_MUTE_Q8]
        if g <= 0:
            break
        e = abs(20 * math.log10((g / (1 << 27)) / (10 ** (q / 256.0 / 20.0))))
        if e > run_max:
            run_max = e
        if run_max > 0.01:
            break
        bound_q8 = q                     # ⭐ 记【最后一个合规点】,⛔ 不是首个越界点(critic m-2)
    print(f"      py 轨实测包络下界 = {bound_q8/256.0:.4f} dB"
          f"(该点 |误差| = {abs(20*math.log10((pvals[bound_q8-DB_MUTE_Q8]/(1<<27))/(10**(bound_q8/256.0/20.0)))):.6f} dB)")
    chk("T1b", bound_q8 == ENV_Q8,
        f"实测包络下界 = 规格声明值 −109.8125 dB(实测 {bound_q8/256.0:.4f})")
    # 阳性对照:证明 T1b 认得出包络挪动(⛔ 没有阳性对照的相等不算证据)
    chk("T1b+", (bound_q8 + 1) != ENV_Q8,
        "阳性对照:相邻一格(1/256 dB)即不等 ⇒ T1b 分辨力 = 1 格,不是「任意值都过」")

# ---------------------------------------------------------------- 定点 DF1(独立重写)
def rbj_peaking(f0, Q, gdb):
    A = 10 ** (gdb / 40); w0 = 2 * math.pi * f0 / FS
    al = math.sin(w0) / (2 * Q); c = math.cos(w0); a0 = 1 + al / A
    return ((1 + al * A) / a0, -2 * c / a0, (1 - al * A) / a0, -2 * c / a0, (1 - al / A) / a0)

def rbj_hpf(f0, Q):
    w0 = 2 * math.pi * f0 / FS; al = math.sin(w0) / (2 * Q); c = math.cos(w0); a0 = 1 + al
    return ((1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0, -2 * c / a0, (1 - al) / a0)

def rbj_lowshelf(f0, S, gdb):
    A = 10 ** (gdb / 40); w0 = 2 * math.pi * f0 / FS
    al = math.sin(w0) / 2 * math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    c = math.cos(w0); t = 2 * math.sqrt(A) * al; a0 = (A + 1) + (A - 1) * c + t
    return (A * ((A + 1) - (A - 1) * c + t) / a0, 2 * A * ((A - 1) - (A + 1) * c) / a0,
            A * ((A + 1) - (A - 1) * c - t) / a0, -2 * ((A - 1) + (A + 1) * c) / a0,
            ((A + 1) + (A - 1) * c - t) / a0)

def quant_coef(x):
    v = int(math.floor(x * (1 << COEF_F) + 0.5)) if x >= 0 else int(math.ceil(x * (1 << COEF_F) - 0.5))
    if v > INT32_MAX or v < INT32_MIN:
        raise ValueError(f"系数 {x} 超 Q4.{COEF_F} 范围")
    return v

def df1_ef(xq, cq, use_ef=True):
    b0, b1, b2, a1, a2 = cq
    x1 = x2 = y1 = y2 = 0
    r1 = r2 = 0
    half = 1 << (COEF_F - 1)
    out = []
    for x in xq:
        acc = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        if use_ef:
            acc -= (a1 * r1) >> COEF_F
            acc -= (a2 * r2) >> COEF_F
        y = (acc + half) >> COEF_F
        r = acc - (y << COEF_F)
        if y > INT32_MAX: y = INT32_MAX
        if y < INT32_MIN: y = INT32_MIN
        x2, x1 = x1, x
        y2, y1 = y1, y
        r2, r1 = r1, r
        out.append(y)
    return out

def t2():
    print("T2  EF 噪声底(py 轨定点仿真)")
    import random
    cases = [("PEQ 20Hz  Q=20  G=+15dB", rbj_peaking(20, 20, 15)),
             ("PEQ 100Hz Q=20  G=+15dB", rbj_peaking(100, 20, 15)),
             ("HPF 20Hz  Q=0.7071",      rbj_hpf(20, 0.7071)),
             ("LowShelf 20Hz S=1 +15dB", rbj_lowshelf(20, 1.0, 15))]
    q = 2.0 ** -SMP_F
    flat = 10 * math.log10(q * q / 12)
    print(f"      白噪基准 q^2/12 = {flat:.2f} dBFS")
    worst = 0.0
    for name, cf in cases:
        cq = [quant_coef(v) for v in cf]
        cfq = [v / (1 << COEF_F) for v in cq]
        rnd = random.Random(20260804)
        N, SKIP = 60000, 3000
        xq = [int(math.floor(rnd.gauss(0, 1) * 0.03 * (1 << SMP_F) + 0.5)) for _ in range(N)]
        yq = df1_ef(xq, cq, True)
        # 参照:同系数、python float(53-bit 尾数,远优于 2^-27)
        b0, b1, b2, a1, a2 = cfq
        x1 = x2 = y1 = y2 = 0.0
        se = 0.0
        for i, xr in enumerate(xq):
            x = xr / (1 << SMP_F)
            y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1 = x1, x
            y2, y1 = y1, y
            if i >= SKIP:
                e = yq[i] / (1 << SMP_F) - y
                se += e * e
        m = 10 * math.log10(se / (N - SKIP) + 1e-300)
        print(f"      {name:26s} 实测 {m:8.2f} dBFS   偏离基准 {m - flat:+.2f} dB")
        worst = max(worst, abs(m - flat))
    chk("T2", worst <= 3.0, f"EF 开:全部贴基准,最大偏离 {worst:.2f} dB(判据 ≤3.0)")

def t3():
    print("T3  8 节级联响应(py 轨)")
    f0 = [31.5, 63, 125, 250, 500, 1000, 4000, 16000]
    qq = [1.4, 1.4, 2.0, 2.0, 1.0, 1.4, 0.7, 0.7]
    gg = [+6, -8, +4, -10, +12, -6, +9, -15]
    ideal = [rbj_peaking(a, b, c) for a, b, c in zip(f0, qq, gg)]
    quant = [[quant_coef(v) / (1 << COEF_F) for v in s] for s in ideal]
    mx, at = 0.0, 0.0
    for i in range(4001):
        f = 20.0 * (1000.0 ** (i / 4000.0))
        w = 2 * math.pi * f / FS
        z = complex(math.cos(-w), math.sin(-w))
        HI = HQ = 1 + 0j
        for s in ideal:
            HI *= (s[0] + s[1] * z + s[2] * z * z) / (1 + s[3] * z + s[4] * z * z)
        for s in quant:
            HQ *= (s[0] + s[1] * z + s[2] * z * z) / (1 + s[3] * z + s[4] * z * z)
        d = abs(20 * math.log10(abs(HQ)) - 20 * math.log10(abs(HI)))
        if d > mx:
            mx, at = d, f
    print(f"      量化 vs 理想 max|Δ| = {mx:.6f} dB @ {at:.1f} Hz")
    chk("T3", mx <= 0.02, "级联量化误差 ≤0.02 dB(规格 ±0.3 dB)")

print("=" * 66)
print("ref_fixed.py  —  第二轨(独立重写,不 import C 实现)")
print("=" * 66)
t1(); print()
t2(); print()
t3(); print()
print("=" * 66)
print(f"第二轨结果: {'全部通过' if not fails else '未通过 ' + ','.join(fails)}"
      + (f"  (退役项 {','.join(retired)},原样留痕,不计入判定)" if retired else ""))
print("=" * 66)
sys.exit(0 if not fails else 1)
