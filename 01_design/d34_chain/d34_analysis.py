#!/usr/bin/env python3
"""D3/D4 通道链设计的验证件。按 PREREG_D34_r1.txt 逐条执行。

⛔ 门禁状态:未过门。
用法: python3 d34_analysis.py > results_d34_rN.txt

⚠ 假绿纪律:每组带【坏版本】开关,坏版本下对应检查必须 FAIL。
   `python3 d34_analysis.py --broken=<name>`
   name ∈ {polarity, qcoef, freeq, qcoef_and_freeq, hpf_order, xo_order}

⛔⛔ 整改 2026-08-05(critic BLOCKER-2b):`hpf_order` 与 `xo_order` 原先**只存在于本行字符串里**
   —— `BROKEN` 全文件只被消费三次,全属 polarity/qcoef ⇒ 跑它们**一个字节的行为都不变**,
   而结果头照印「坏版本开关: xo_order」⇒ **产出一份看起来像"该变异存活"的归档件**。
   ⇒ 而缺的这两个,恰是 §0 承重表 #1/#3 两条链序结论**唯一可能的变异**。⇒ 现已实现。
"""
import numpy as np, math, sys, hashlib, os
from scipy import signal

FS = 48000.0
COEF_F = 27          # 与 chdsp_fixed.h 的 CHDSP_COEF_FRACBITS 同源
SMP_F  = 27
NOISE_PER_SECTION_DBFS = -173.35   # 任务一 [L2/宿主实测 CHK-4],⚠ 未过门

BROKEN = ''
for a in sys.argv[1:]:
    if a.startswith('--broken='):
        BROKEN = a.split('=', 1)[1]

# ⛔⛔ 整改 2026-08-05(critic BLOCKER-2 修法④,r16 补做)
#   上一轮我报「BLOCKER-2 已闭」,而四条修法里**这一条当时没做** ——
#   实测 `--broken=不存在的名字` 会跑完全程、退出 0,并在结果头照印那个名字
#   ⇒ 正是 critic 点名的那种"看起来像该变异存活"的归档件。
#   ⇒ D6-ap:一个只输出不阻断的检查不是检查。未知变异名必须**当场中止**。
_KNOWN_BROKEN = ('polarity', 'qcoef', 'freeq', 'qcoef_and_freeq', 'hpf_order', 'xo_order')
if BROKEN and BROKEN not in _KNOWN_BROKEN:
    sys.stderr.write(f"⛔ 未知的 --broken 名: {BROKEN!r};已实现的变异 = {_KNOWN_BROKEN}\n"
                     f"⛔ ⛔ 拒绝当作出货构建跑完 —— 那会产出一份看起来像"
                     f"「该变异存活」的归档件。\n")
    sys.exit(2)

_pass, _fail, _retired = 0, 0, 0
_decided = set()          # ⭐ 本次跑批实际出现过的【判定项】标识(META-1 用)
def OK(tag, cond, msg):
    global _pass, _fail
    _decided.add(tag)
    if cond: _pass += 1
    else:    _fail += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {tag:<9s} {msg}")

def RETIRED(tag, cond, msg):
    """已退役的检查:保留记录(E-2 加标注不删数),不计入判定。
    ⛔ 退役项【不进 _decided】—— 那正是 META-1 要抓的一种消失方式。"""
    global _retired
    _retired += 1
    print(f"  [{'退役·符合' if cond else '退役·不符'}] {tag:<9s} {msg}")

# ---------------------------------------------------------------- 滤波器设计
def bw_lp(fc, Q):
    w0 = 2*np.pi*fc/FS; al = np.sin(w0)/(2*Q); c = np.cos(w0); a0 = 1+al
    return np.array([(1-c)/2, 1-c, (1-c)/2])/a0, np.array([1.0, -2*c/a0, (1-al)/a0])
def bw_hp(fc, Q):
    w0 = 2*np.pi*fc/FS; al = np.sin(w0)/(2*Q); c = np.cos(w0); a0 = 1+al
    return np.array([(1+c)/2, -(1+c), (1+c)/2])/a0, np.array([1.0, -2*c/a0, (1-al)/a0])
def rbj_peaking(f0, Q, gdb):
    A = 10**(gdb/40); w0 = 2*np.pi*f0/FS; al = np.sin(w0)/(2*Q); c = np.cos(w0); a0 = 1+al/A
    return np.array([1+al*A, -2*c, 1-al*A])/a0, np.array([1.0, -2*c/a0, (1-al/A)/a0])

def butter_qs(order):
    n = order//2
    return [1.0/(2*math.cos(math.pi*(2*k+1)/(2*order))) for k in range(n)]

def lr_sections(fc, lr_order, kind):
    """LR{n} = (Butterworth n/2 阶)²。返回 biquad 列表。"""
    bo = lr_order//2
    mk = bw_lp if kind == 'lp' else bw_hp
    if bo == 1:
        return [mk(fc, 0.5)]                       # LR2 = 双实极点重合 ⇒ Q=0.5
    if bo % 2 == 0:
        return [mk(fc, q) for q in butter_qs(bo) for _ in range(2)]
    # 奇数阶 BW(LR6 = (3阶BW)²):3 阶 = 一个实极点 + 一个 Q=1 biquad
    if bo == 3:
        return [mk(fc, 0.5)] + [mk(fc, 1.0) for _ in range(2)]
    raise ValueError(f"LR{lr_order} 未实现")

def lr_polarity(lr_order):
    """LR 阶数 mod 4 == 0 ⇒ 同相求和;== 2 ⇒ 需反相。"""
    if BROKEN == 'polarity':
        return +1                                   # ⛔ 坏版本:一律同相
    return +1 if (lr_order % 4 == 0) else -1

# ---------------------------------------------------------------- 定点量化
def qcoef(x):
    # ⛔⛔ 整改 2026-08-05(critic BLOCKER-2a):原先 `qcoef` 这一个开关**同时注入两个缺陷** ——
    #   ① 系数退化到 16-bit(本函数)② 顺手把结构约束量化也关了(qsec 里的 `and BROKEN != 'qcoef'`)
    #   ⇒ 它杀掉的 5 条里,**EXP-3c 与 EXP-4a 实际是被 ② 杀死的,不是被 ① 杀死的**
    #   ⇒ 杀伤矩阵把功记在了错的缺陷上 ⇒ **一条假的杀伤记录**。
    #   ⇒ 现拆成两个独立变异:`qcoef`(只退化位宽)与 `freeq`(只关结构约束)。
    if BROKEN in ('qcoef', 'qcoef_and_freeq'):
        s = 14                                      # ⛔ 坏版本:退化成 Q?.14(16-bit 级)
    else:
        s = COEF_F
    v = int(math.floor(x*(1 << s) + 0.5)) if x >= 0 else int(math.ceil(x*(1 << s) - 0.5))
    if v > (1 << 31)-1 or v < -(1 << 31):
        raise ValueError(f"系数 {x} 超 Q4.{s} 范围")
    return v/float(1 << s)

def qsec(sec, tie=None):
    """量化一个 biquad。tie='hp'/'lp' 时用结构约束量化(b1=∓2b0, b2=b0)。"""
    b, a = sec
    if tie in ('hp', 'lp') and BROKEN not in ('freeq', 'qcoef_and_freeq'):
        b0 = qcoef(b[0])
        b1 = -2*b0 if tie == 'hp' else 2*b0
        bq = np.array([b0, b1, b0])
    else:
        bq = np.array([qcoef(v) for v in b])
    aq = np.array([1.0, qcoef(a[1]), qcoef(a[2])])
    return bq, aq

def casc_H(secs, w):
    z = np.exp(-1j*w); H = np.ones_like(z)
    for b, a in secs:
        H *= (b[0] + b[1]*z + b[2]*z*z)/(a[0] + a[1]*z + a[2]*z*z)
    return H

def sec_H(sec, w):
    b, a = sec; z = np.exp(-1j*w)
    return (b[0] + b[1]*z + b[2]*z*z)/(a[0] + a[1]*z + a[2]*z*z)

# ================================================================
print("="*84)
import os as _os
print(f"results_d34  —  D3/D4 通道链设计 · 验证结果(轮次见文件名)")
print(f"预注册: PREREG_D34_r1.txt + PREREG_D34_r2_addendum.txt(一字未改)")
print(f"deps: d34_analysis.py@{hashlib.sha256(open(__file__,'rb').read()).hexdigest()[:16]}")
print(f"numpy {np.__version__} / scipy {signal.__name__}  fs = {FS} Hz  系数格式 Q4.{COEF_F}")
print(f"坏版本开关: {BROKEN if BROKEN else '无(出货构建)'}")
print("门禁状态: 未过门")
print("="*84)

# ---------------------------------------------------------------- EXP-1
print("\nEXP-1  D4 顺序:PEQ 在分频【前】 vs 【后】(窄带被测量,见 PREREG §0 X-2)")
print("-"*84)
xo  = [qsec(s, 'hp') for s in lr_sections(120.0, 4, 'hp')]
peq = [qsec(rbj_peaking(40.0, 1.0, 12.0))]
NOM = 10**(-20/20.0)      # 标称 −20 dBFS
for ftest, label, band in [(40.0, '阻带激励 40 Hz', 'stop'), (1000.0, '通带对照 1 kHz', 'pass')]:
    w = np.array([2*np.pi*ftest/FS])
    lv = {}
    # ⛔ 坏版本 xo_order:把「分频在前」那一臂也按 PEQ 在前算 ⇒ 两臂等价 ⇒ 差值塌到 0
    #    (整改 2026-08-05 · critic BLOCKER-2b:本变异原先只存在于 docstring 里)
    _arms = [('PEQ 在前', peq+xo),
             ('分频在前', (peq+xo) if BROKEN == 'xo_order' else (xo+peq))]
    for nm, secs in _arms:
        g = 1.0; peaks = []
        for s in secs:
            g *= abs(sec_H(s, w)[0])
            peaks.append(20*math.log10(NOM*g))
        lv[nm] = peaks
        print(f"    {label} / {nm}: 逐节电平(dBFS) = {[round(v,2) for v in peaks]}  ⇒ 最大 {max(peaks):+.2f}")
    d = max(lv['PEQ 在前']) - max(lv['分频在前'])
    print(f"    ⇒ 最大节点电平之差 = {d:+.2f} dB")
    if band == 'stop':
        OK("EXP-1a", d >= 3.0,
           f"阻带激励下「分频在前」省下 {d:.2f} dB 链内电平(判据 ≥3 dB)")
    else:
        OK("EXP-1b", abs(d) <= 0.1,
           f"通带对照两者之差 {d:+.3f} dB(判据 ≤0.1 dB)⇒ 该测量只在阻带有分辨力,符合预期")
# 交换律复核(顺序不改传函)
wfull = np.linspace(1e-7, np.pi-1e-7, 60001)
HA = casc_H(peq+xo, wfull); HB = casc_H(xo+peq, wfull)
dmax = np.max(np.abs(20*np.log10(np.abs(HA)+1e-300) - 20*np.log10(np.abs(HB)+1e-300)))
print(f"    总传函之差 max = {dmax:.3e} dB")
OK("EXP-1c", dmax < 1e-9, "两种顺序总传函严格相等 ⇒ 顺序不能用传函来选,只能用链内电平")

# ---------------------------------------------------------------- EXP-2
print("\nEXP-2  D3 顺序:HPF 在动态处理【之前】的理由")
print("-"*84)
def rms_detector(x, tau_ms):
    """一阶 RMS 检测器(与参数表的 attack/release 同族,单时间常数版)"""
    a = math.exp(-1.0/(tau_ms*1e-3*FS))
    y = np.zeros_like(x); s = 0.0
    for i, v in enumerate(x):
        s = a*s + (1-a)*v*v
        y[i] = s
    return np.sqrt(y)

N = int(FS*2.0)
t = np.arange(N)/FS
burst = np.zeros(N)
period = int(FS*0.5)
for k in range(4):
    lo = k*period; hi = lo + int(period*0.2)
    burst[lo:hi] = np.sin(2*np.pi*1000*t[lo:hi])
burst *= 10**(-30/20.0)
rumble = 10**(-20/20.0)*np.sin(2*np.pi*45*t)
x = burst + rumble
hpf = qsec(bw_hp(80.0, 0.7071), 'hp')
def apply_sec(sec, sig):
    b, a = sec
    return signal.lfilter(b, a, sig)

# ⛔ 坏版本 hpf_order:让「HPF 在动态之前」那一臂实际**不过 HPF** ⇒ 两读数相同 ⇒ EXP-2a 塌
#    (整改 2026-08-05 · critic BLOCKER-2b:本变异原先只存在于 docstring 里)
x_hpf_first = x if BROKEN == 'hpf_order' else apply_sec(hpf, x)
det_first = rms_detector(x_hpf_first, 20.0)      # HPF 在动态之前
det_after = rms_detector(x, 20.0)                # HPF 在动态之后 ⇒ 侧链看到原始信号
# 静默段(每周期的后 60%)
sil = np.zeros(N, dtype=bool)
for k in range(4):
    lo = k*period + int(period*0.4); hi = (k+1)*period
    sil[lo:hi] = True
q_first = 20*math.log10(np.mean(det_first[sil])+1e-300)
q_after = 20*math.log10(np.mean(det_after[sil])+1e-300)
print(f"    静默段侧链检测器读数: HPF 在动态之前 = {q_first:7.2f} dBFS | HPF 在动态之后 = {q_after:7.2f} dBFS")
print(f"    ⇒ 差 = {q_after-q_first:+.2f} dB")
OK("EXP-2a", (q_after - q_first) >= 6.0,
   f"HPF 前置使静默段侧链读数低 {q_after-q_first:.2f} dB(判据 ≥6 dB)")

# 门的行为:阈值 −45 dBFS,比率 1:20
def gate_gain(det, thr_db, ratio=20.0):
    d = 20*np.log10(det+1e-300)
    over = d - thr_db
    g = np.where(over >= 0, 0.0, over*(1.0-1.0/ratio))
    return g
g_first = gate_gain(det_first, -45.0)
g_after = gate_gain(det_after, -45.0)
gf = np.mean(g_first[sil]); ga = np.mean(g_after[sil])
print(f"    静默段门增益均值: HPF 在前 = {gf:7.2f} dB | HPF 在后 = {ga:7.2f} dB")
RETIRED("EXP-2b", gf <= -20.0 and ga > -6.0,
   f"原判据在门限 −45 dBFS 上断言两种链序行为不同,实测都 0.00 dB ⇒ 证伪条件命中。"
   f"根因:−45 是我拍的常数,落在两个检测器读数(−33.4/−23.0)之外 ⇒ 门在两种链序下都开着。"
   f"⛔ 不改门限充数;由 EXP-2c 扫门限给出真实适用区间。")

# ---- EXP-2c(r2):扫门限,给出 HPF 前置收益成立的区间 ----
print("\nEXP-2c 扫门限:HPF 前置的收益在哪个门限区间才成立")
thrs = np.linspace(-60.0, -10.0, 101)
ok_lo, ok_hi = None, None
for th in thrs:
    d = np.mean(gate_gain(det_after, th)[sil]) - np.mean(gate_gain(det_first, th)[sil])
    if d >= 6.0:
        if ok_lo is None: ok_lo = th
        ok_hi = th
if ok_lo is None:
    print("    「差 ≥6 dB」的门限区间为【空】")
else:
    print(f"    「静默段门增益差 ≥6 dB」成立的门限区间 = [{ok_lo:.1f}, {ok_hi:.1f}] dBFS  (宽 {ok_hi-ok_lo:.1f} dB)")
    print(f"    对照:两个检测器读数 = HPF在前 {q_first:.2f} / HPF在后 {q_after:.2f} dBFS")
    for th in [-45.0, -30.0, -28.0, -25.0]:
        d = np.mean(gate_gain(det_after, th)[sil]) - np.mean(gate_gain(det_first, th)[sil])
        print(f"      门限 {th:6.1f} dBFS ⇒ 两种链序门增益差 = {d:6.2f} dB")
OK("EXP-2c", ok_lo is not None,
   "存在非空门限区间使 HPF 前置产生 ≥6 dB 的门行为差异 ⇒ 该理由成立【但有适用范围】")

# ---- EXP-2d(r2):分离度对隆隆声频率 × HPF 阶数的依赖 ----
print("\nEXP-2d 分离度的适用范围:隆隆声频率 × HPF 阶数 × fc")
def hpf_chain(order, fc):
    if order == 2:
        return [qsec(bw_hp(fc, 0.7071), 'hp')]
    return [qsec(bw_hp(fc, q), 'hp') for q in butter_qs(order)]
print(f"    {'隆隆Hz':>7s} {'阶':>3s} {'fc':>5s} {'HPF在前(dBFS)':>14s} {'HPF在后(dBFS)':>14s} {'分离(dB)':>9s}")
sep_tab = {}
for frum in [20.0, 30.0, 45.0, 60.0]:
    for order in [2, 4]:
        for fcc in [60.0, 80.0, 120.0]:
            xx = burst + 10**(-20/20.0)*np.sin(2*np.pi*frum*t)
            yy = xx
            for sec in hpf_chain(order, fcc):
                yy = apply_sec(sec, yy)
            a1 = 20*math.log10(np.mean(rms_detector(yy, 20.0)[sil])+1e-300)
            a2 = 20*math.log10(np.mean(rms_detector(xx, 20.0)[sil])+1e-300)
            sep_tab[(frum, order, fcc)] = a2-a1
            print(f"    {frum:7.0f} {order:3d} {fcc:5.0f} {a1:14.2f} {a2:14.2f} {a2-a1:9.2f}")
mono_ok = all(sep_tab[(f_, 4, c_)] >= sep_tab[(f_, 2, c_)] - 0.01
              for f_ in [20.,30.,45.,60.] for c_ in [60.,80.,120.])
mono_fc = all(sep_tab[(f_, o_, 120.)] >= sep_tab[(f_, o_, 60.)] - 0.01
              for f_ in [20.,30.,45.,60.] for o_ in [2,4])
OK("EXP-2d", mono_ok and mono_fc,
   "分离度对【阶数升高】与【fc 抬高】均单调不减(机理自洽)")

# ---------------------------------------------------------------- EXP-3
print("\nEXP-3  D-4 级联:LR 分频器求和 / DC / Nyquist(lead 点名的那条)")
print("-"*84)
w = np.linspace(1e-7, np.pi-1e-7, 200001); f = w*FS/(2*np.pi)
band = (f >= 20) & (f <= 20000)
sum_worst_q = 0.0; sum_worst_i = 0.0; dcny_worst = -1e9
print(f"    {'分频':10s} {'fc':>7s} {'极性':>5s} {'理想求和偏离':>14s} {'Q4.27求和偏离':>15s} {'HP@DC':>12s} {'LP@Nyq':>12s}")
for lr in [2, 4, 6, 8]:
    for fc in [80.0, 120.0, 2000.0]:
        pol = lr_polarity(lr)
        li = lr_sections(fc, lr, 'lp'); hi_ = lr_sections(fc, lr, 'hp')
        lq = [qsec(s, 'lp') for s in li]; hq = [qsec(s, 'hp') for s in hi_]
        si = casc_H(li, w) + pol*casc_H(hi_, w)
        sq = casc_H(lq, w) + pol*casc_H(hq, w)
        di = np.max(np.abs(20*np.log10(np.abs(si)+1e-300)[band]))
        dq = np.max(np.abs(20*np.log10(np.abs(sq)+1e-300)[band]))
        hp_dc = 20*math.log10(abs(casc_H(hq, np.array([1e-12]))[0]) + 1e-300)
        lp_ny = 20*math.log10(abs(casc_H(lq, np.array([np.pi-1e-12]))[0]) + 1e-300)
        sum_worst_i = max(sum_worst_i, di); sum_worst_q = max(sum_worst_q, dq)
        dcny_worst = max(dcny_worst, hp_dc, lp_ny)
        print(f"    LR{lr:<8d} {fc:7.0f} {'同相' if pol>0 else '反相':>5s} "
              f"{di:12.2e} dB {dq:13.4f} dB {hp_dc:9.1f} dB {lp_ny:9.1f} dB")
OK("EXP-3a", sum_worst_i <= 1e-6, f"正确极性下理想系数求和偏离 ≤1e−6 dB(实测 {sum_worst_i:.2e})")
OK("EXP-3b", sum_worst_q <= 0.05, f"Q4.27 量化后求和偏离 ≤0.05 dB(实测 {sum_worst_q:.4f})")
OK("EXP-3c", dcny_worst <= -120.0, f"HP@DC 与 LP@Nyquist 泄漏 ≤ −120 dB(最坏 {dcny_worst:.1f} dB)")

# 阳性对照:把极性规则写反,求和必须出现深谷
print("    阳性对照(把 LR4 的极性人为写反):")
li = lr_sections(2000.0, 4, 'lp'); hi_ = lr_sections(2000.0, 4, 'hp')
bad = casc_H(li, w) - casc_H(hi_, w)
bd = np.max(np.abs(20*np.log10(np.abs(bad)+1e-300)[band]))
# ⛔⛔ 整改 2026-08-05(critic erratum2 + r16 B-1):此处原先直接印 `bd` 的数值(87.72 dB),
#   而**它不是物理量,是网格伪影** —— 错误极性下 LP−HP 在 fc 处有零点(实测残差 1.4e−15,
#   ≈ float64 底)⇒ 理想深度 = −∞ ⇒ 测到多深只取决于最近网格点离 fc 多近
#   (20001 点→67.85 / 200001→87.72 / 2000001→106.58,单调不收敛,见 check_r16.py B-1)。
#   ⇒ 判据 `bd > 20` 仍成立且稳健(任何网格密度都远超 20);⛔ 塌掉的只是那个"深度数字"。
#   ⇒ 于是这里只报**零点是否存在**,⛔ 不报深度 —— 一个印出来就会被引用的数,不该印。
_resid_fc = abs((casc_H(li, np.array([2*np.pi*2000.0/FS])) -
                 casc_H(hi_, np.array([2*np.pi*2000.0/FS])))[0])
print(f"      LR4 fc=2000 反相求和:fc 处残差 = {_resid_fc:.2e}"
      f"(≈0 ⇒ 存在零点,理想深度 −∞)")
print(f"      ⛔ 深度数值不报 —— 它随网格密度单调发散,是【器械】的性质不是【被测物】的"
      f"(erratum2 / RETRACTED_STRINGS: 87.72 dB)")
OK("EXP-3p", bd > 20.0,
   "极性写反时求和出现【零点】⇒ EXP-3a/b 有分辨力,不是恒真。"
   "⛔ 深度数值不得报出(erratum2:理想深度 = −∞,实测值只反映网格密度)")

# ---- EXP-3d(r16,critic MAJOR-4 修法④):从【界面参数 xo_slope】到极性的映射 ----
# ⛔ 这条守的是 MAJOR-4 点名的那个单位陷阱:实现方手上的是 dB/oct(12/24/36/48),
#    而极性规则里的 N 是**滤波器阶数**(2/4/6/8)。12 mod 4 = 0 ≠ 2 mod 4 ——
#    照参数值直接套规则会把 LR2/LR6 判成同相 ⇒ 分频点出现零点。
def xo_order_n_from_slope(slope_db_oct):
    """dB/oct → 滤波器阶数 N。LR 每阶 6 dB/oct。⛔ 非 6 的整数倍 ⇒ 0(非法)。"""
    if slope_db_oct % 6 != 0:
        return 0
    return slope_db_oct // 6

print("\n    EXP-3d 从界面参数 xo_slope(dB/oct)到求和极性的映射(MAJOR-4)")
_slope_bad = 0
_map_bad = 0
print(f"      {'xo_slope':>9s} {'⇒ 阶数 N':>9s} {'N mod 4':>8s} {'规则给的极性':>10s} "
      f"{'该极性求和偏离':>14s} {'另一极性 fc 处':>14s}")
for _sl in (12, 24, 36, 48):
    _n = xo_order_n_from_slope(_sl)
    _pol = lr_polarity(_n)
    _fc = 1000.0
    _l = lr_sections(_fc, _n, 'lp'); _h = lr_sections(_fc, _n, 'hp')
    _lq = [qsec(s, 'lp') for s in _l]; _hq = [qsec(s, 'hp') for s in _h]
    _wb = np.linspace(2*np.pi*20/FS, 2*np.pi*20000/FS, 40001)
    _dev = np.max(np.abs(20*np.log10(np.abs(casc_H(_lq, _wb) + _pol*casc_H(_hq, _wb))+1e-300)))
    _wfc = np.array([2*np.pi*_fc/FS])
    _res = abs(casc_H(_l, _wfc)[0] - _pol*casc_H(_h, _wfc)[0])   # 另一极性在 fc 处的残差
    if _dev > 0.05:
        _slope_bad += 1
    if _res > 1e-9:
        _map_bad += 1
    print(f"      {_sl:9d} {_n:9d} {_n % 4:8d} {'同相' if _pol > 0 else '反相':>10s} "
          f"{_dev:11.4f} dB {_res:14.2e}")
OK("EXP-3d", _slope_bad == 0 and _map_bad == 0,
   f"四档 xo_slope 按 N = slope÷6 求得的极性,求和偏离全部 ≤0.05 dB(越界 {_slope_bad} 档);"
   f"而另一极性在 fc 处残差全部 ≈0 ⇒ 存在零点(未出现零点 {_map_bad} 档)"
   f" ⇒ ⛔ 若照 12/24/36/48 直接 mod 4,四档全判同相,LR2/LR6 必错")

# ---------------------------------------------------------------- EXP-4
print("\nEXP-4  群延迟与延迟预算(⚠ 强制两轨,因 PREREG §0 X-1)")
print("-"*84)
wg = np.linspace(1e-6, np.pi-1e-6, 400001); fg = wg*FS/(2*np.pi)
mg = (fg >= 20) & (fg <= 20000)
two_track_worst = 0.0; loc_bad = 0
print(f"    {'分频':8s} {'fc':>7s} {'max群延迟(样本)':>16s} {'ms':>8s} {'峰值位置Hz':>12s} {'两轨差(样本)':>13s}")
gd_table = {}
for lr in [2, 4, 8]:
    for fc in [80.0, 120.0, 2000.0]:
        secs = [qsec(s, 'hp') for s in lr_sections(fc, lr, 'hp')]
        gdA = np.zeros_like(wg)
        for b, a in secs:
            _, g = signal.group_delay((b, a), w=wg)
            gdA += g
        z = np.exp(-1j*wg); H = np.ones_like(z)
        for b, a in secs:
            H *= (b[0]+b[1]*z+b[2]*z*z)/(a[0]+a[1]*z+a[2]*z*z)
        gdB = -np.gradient(np.unwrap(np.angle(H)), wg)
        d2 = float(np.max(np.abs(gdA[mg]-gdB[mg])))
        i = int(np.argmax(gdA[mg])); pk = gdA[mg][i]; pf = fg[mg][i]
        two_track_worst = max(two_track_worst, d2)
        if not (fc/8 <= pf <= fc*8): loc_bad += 1
        gd_table[(lr, fc)] = (pk, pf)
        print(f"    LR{lr:<6d} {fc:7.0f} {pk:16.2f} {pk/FS*1000:8.3f} {pf:12.1f} {d2:13.4f}")
OK("EXP-4a", two_track_worst <= 0.05, f"两轨最大差 ≤0.05 样本(实测 {two_track_worst:.4f})")
RETIRED("EXP-4b", loc_bad == 0,
   f"原判据「峰值必在 fc ±3 倍频程」对 LR2(Q=0.5 临界阻尼)不适用:该节群延迟自 DC 单调下降,"
   f"峰本来就在评价带下沿。⇒ 判据错、不是测量错;由 EXP-4d 用闭式解析独立证实后退役。"
   f"({loc_bad}/9 个算例落在原判据之外,全部为 LR2)")

# ---- EXP-4d(r2):闭式解析第三轨 ----
print("\nEXP-4d 独立第三轨(闭式解析):LR2 低频群延迟峰值是不是物理")
print("    模拟原型 H(s)=s^2/(s+wc)^2 ⇒ phi = pi - 2*atan(w/wc) ⇒ tau = 2/(wc*(1+(w/wc)^2))")
worst_rel = 0.0
for fc in [80.0, 120.0, 2000.0]:
    wc = 2*np.pi*fc
    ftest = 20.0
    tau_an = 2.0/(wc*(1.0+(2*np.pi*ftest/wc)**2))     # 秒
    secs = [qsec(s, 'hp') for s in lr_sections(fc, 2, 'hp')]
    wq = np.array([2*np.pi*ftest/FS])
    gd = 0.0
    for b, a in secs:
        _, g = signal.group_delay((b, a), w=wq); gd += g[0]
    tau_num = gd/FS
    rel = abs(tau_num-tau_an)/tau_an*100
    worst_rel = max(worst_rel, rel)
    print(f"    LR2 fc={fc:6.0f}Hz @20Hz: 解析 {tau_an*1e3:7.4f} ms | 数值 {tau_num*1e3:7.4f} ms | 相对差 {rel:5.2f}%")
OK("EXP-4d", worst_rel <= 10.0,
   f"解析与数值最大相对差 {worst_rel:.2f}% ≤10% ⇒ LR2 的低频峰值是物理,原 EXP-4b 判据确实写错了")

ADC, DAC = 22.9844, 25.0
print(f"\n    转换器锚点 [L2/厂家]: ADC {ADC}/fS = {ADC/FS*1e3:.3f} ms;DAC {DAC}/fS = {DAC/FS*1e3:.3f} ms"
      f"  ⇒ 合计 {(ADC+DAC)/FS*1e3:.4f} ms")   # ⛔ m-7:精确 0.999675,末位是舍入平局
      # ⇒ 用 .5f 打印会得到 0.99967(float 表示略小于平局,向下)⇒ 改 .4f = 0.9997,⛔ 不给截断值
print(f"    {'帧长L':>6s} {'块I/O(2L)':>10s} {'FIR taps':>9s} {'FIR群延迟ms':>12s} {'固定合计ms':>11s} {'余(12ms)':>10s}")
for L in [32, 64, 128]:
    for Nt in [128, 256, 512, 1024]:
        gd = (Nt-1)/2
        tot = (ADC+DAC+2*L+gd)/FS*1e3
        print(f"    {L:6d} {2*L:10d} {Nt:9d} {gd/FS*1e3:12.3f} {tot:11.3f} {12.0-tot:+10.3f}")
OK("EXP-4c", (ADC+DAC+2*64+511.5)/FS*1e3 > 12.0,
   "L=64 + FIR 1024 tap 固定合计已超 12 ms ⇒ FIR 抽头数受延迟预算硬约束")

# ---------------------------------------------------------------- EXP-5
print("\nEXP-5  D3/D4 全链量化噪声底(依赖任务一单节实测,同门禁状态)")
print("-"*84)
chains = [("D3 输入链", [("HPF", 1), ("PEQ×8", 8), ("门", 0), ("压缩", 0), ("延时", 0), ("保护限幅", 0)]),
          ("D4 输出链", [("分频 LR8 HP+LP", 8), ("PEQ×10", 10), ("FIR", 1), ("延时", 0),
                        ("输出限幅", 0), ("音箱保护", 0)])]
tot_n = 0
for nm, blocks in chains:
    n = sum(k for _, k in blocks)
    tot_n += n
    fl = NOISE_PER_SECTION_DBFS + 10*math.log10(max(n, 1))
    print(f"    {nm:12s} 量化器 {n:3d} 个(明细: {', '.join(f'{a}={b}' for a,b in blocks)})  ⇒ 噪声底 {fl:8.2f} dBFS")
fl_all = NOISE_PER_SECTION_DBFS + 10*math.log10(tot_n)
print(f"    {'D3+D4 合计':12s} 量化器 {tot_n:3d} 个  ⇒ 噪声底 {fl_all:8.2f} dBFS")
print(f"    对 PRD 动态范围 >106 dB(⇒ ≤ −106 dBFS)余量 = {abs(fl_all)-106:.1f} dB")
OK("EXP-5", fl_all <= -140.0, f"全链噪声底 {fl_all:.2f} dBFS ≤ −140(判据)"
                              f"  ⚠ **仅在各节增益=1 前提下**")
print("    ⚠ 增益/门/压限/延时不引入新量化器:增益并入相邻节的累加器;")
print("      门与压限只做增益相乘(1 次窄化,已计入其上游节);延时是纯搬运。")
print()
print("    ⛔⛔ 适用范围(2026-08-04 整改 · critic MAJOR-2 · channel-dsp 实例 #2)")
print("      上面的模型是【直接功率相加】,**只在各节增益 = 1 时成立**。")
print("      第 k 节的噪声要经第 k+1…N 节的传函才到链末,而 D34 §6.2-4 **明文允许**")
print("      用户把 8 段 PEQ 全部 +15 dB 叠在同一频率(D34_FIXEDPOINT §6.2 第 4 条)。")

# ---- EXP-5b/5c(r16,critic MAJOR-3 修法③):把级间增益【做进模型】,并做成会响的闸门 ----
# ⛔ 整改 2026-08-05:上一轮这一段只是几行 print + 一句"该维的复算件在别处"。
#    ⇒ 而"最坏合法配置突破 PRD"这件事当时是**一行输出**,不是**一个闸门** ——
#      一个只输出不阻断的检查不是检查(D6-ap)。本轮把它接成判定项。
def noise_floor_interstage(secs, n_tail_unity=0, NW=4096):
    """链末噪声底 dBFS。第 k 节输出处有一个量化器,其噪声经第 k+1…N 节的 |H|²。
    n_tail_unity = 位于链尾、其后无任何增益的附加量化器个数。"""
    wv = np.pi*(np.arange(NW)+0.5)/NW
    p1 = 10**(NOISE_PER_SECTION_DBFS/10.0)
    tot = 0.0
    for k in range(len(secs)):
        g = np.ones_like(wv)
        for j in range(k+1, len(secs)):
            g *= np.abs(sec_H(secs[j], wv))**2
        tot += p1*float(np.mean(g))
    return 10*math.log10(tot + p1*n_tail_unity)

_unity8 = [qsec(rbj_peaking(1000.0, 1.0, 0.0)) for _ in range(8)]
_worst8 = [qsec(rbj_peaking(1000.0, 1.4, 15.0)) for _ in range(8)]
_hpf1 = [qsec(bw_hp(80.0, 0.7071), 'hp')]
# D3 输入链 = HPF(1) + PEQ×8(8) = 9 个量化器(与本 EXP-5 上表同一套记账)
d3_unity = noise_floor_interstage(_hpf1 + _unity8)
d3_worst = noise_floor_interstage(_hpf1 + _worst8)
d3_model = NOISE_PER_SECTION_DBFS + 10*math.log10(9)
print(f"      含级间增益的复算(D3 输入链,9 量化器):")
print(f"        ① 各节增益=1                        ⇒ {d3_unity:8.2f} dBFS(直接相加模型 {d3_model:.2f})")
print(f"        ② 8 段 +15 dB 同频 @1 kHz, Q=1.4(**默认 Q**)⇒ {d3_worst:8.2f} dBFS"
      f"(差 {d3_worst-d3_unity:+.2f} dB)")
print(f"          ⛔ 上面这一格【不是最坏合法配置】—— 它是【默认点】,见下 EXP-5c 的扫描")
OK("EXP-5b", abs(d3_unity - d3_model) < 0.01,
   f"含级间增益的模型在【各节增益=1】时回到直接相加({d3_unity:.2f} vs {d3_model:.2f})"
   f" ⇒ 它没写错,且能认出'没有级间增益'这件事")

# ---- EXP-5c(r17 重写 · critic D3D4-r3 BLOCKER-1 修法②)------------------------
# ⛔⛔ 上一版 EXP-5c 把工作点**钉死在 (f0=1000, Q=1.4)** —— 而 Q=1.4 是参数字典的**默认值**,
#   不是量程端点(字典 `band_q ∈ [0.02, 50]`,设计件 :326)。
#   ⇒ 它报的 −76.97 / 破 29.03 dB 被写成了「最坏合法配置」,而 lead 已把 29.03 报给 CTO。
#   ⇒ ⭐ 三层(我用独立实现逐层复核过,`check_r17_worstQ.py` R1/R2/R3):
#     ① 连它自己那一行(Q=1.4)的最坏点都不是:f0 挪到 12500 ⇒ −68.14 ⇒ 破 37.86
#     ② 字典全范围最坏 = (f0=12500, Q=0.02) ⇒ −54.38 ⇒ **破 51.62 dB**
#     ③ 「同频叠加」这根轴选错了:8 段**散开**但 Q 取下限 ⇒ −68.37,仍比同频+默认Q 差 8.59 dB
#        ⇒ ⭐ **承重的轴是 Q(低 Q ⇒ 峰更宽 ⇒ 噪声增益的频率积分更大),不是同频。**
# ⇒ ∴ 本轮改成【在参数字典自己声明的范围上求最坏】,⛔ 不再钉一个点。
#   ⭐ 这样它自带 LESSONS B-4(极值必须带取值范围),且**日后 D2 改 band_q 量程时它会自动跟着变**。
# ⚠ 若判 Q=0.02 不该可达 ⇒ 要改的是**参数字典**,⛔ 不是改本判据
#   ——「把测量点挪回安全区」正是本条预注册明令禁止的那件事。
PEQ_Q_RANGE = (0.02, 50.0)          # 设计件 :326 `band_q[k]`
PEQ_GAIN_MAX = 15.0                 # 设计件 :325 `band_gain[k]` 上限(实测 +15 比 −15 差 118.6 dB
                                    #   ⇒ 取 + 号是最坏,⛔ 这一条是实测的,不是假定的)
_F_GRID = [32., 63., 125., 250., 500., 1000., 2000., 4000., 8000., 12500., 16000., 20000.]
_Q_GRID = [0.02, 0.10, 0.50, 1.40, 50.0]
print(f"\n    EXP-5c 在**参数字典范围**上求最坏(band_q ∈ {PEQ_Q_RANGE},band_gain = +{PEQ_GAIN_MAX:.0f} dB)")
print(f"      ⛔ ⛔ 上一版把工作点钉死在【默认 Q = 1.4 / f0 = 1000】并称之为「最坏合法配置」——")
print(f"         那是【默认点】不是【最坏点】(critic D3D4-r3 BLOCKER-1)。本版扫量程。")
_qf_hdr = "Q \\ f0"
print(f"      {_qf_hdr:>8s}" + "".join(f"{f:>8.0f}" for f in _F_GRID))
_w5c = (-1e9, None, None)
for _qq in _Q_GRID:
    _cells = []
    for _f0 in _F_GRID:
        _v = noise_floor_interstage(
            _hpf1 + [qsec(rbj_peaking(_f0, _qq, PEQ_GAIN_MAX)) for _ in range(8)], NW=1024)
        _cells.append(_v)
        if _v > _w5c[0]:
            _w5c = (_v, _f0, _qq)
    print(f"      {_qq:>8.2f}" + "".join(f"{v:>8.1f}" for v in _cells))
# 最坏格用与其余各处相同的 NW=4096 复算(⚠ 实测 NW 1024→16384 该值动 0.0000 dB)
_w5c_v = noise_floor_interstage(
    _hpf1 + [qsec(rbj_peaking(_w5c[1], _w5c[2], PEQ_GAIN_MAX)) for _ in range(8)])
print(f"      ⇒ 最坏格 = (f0 = {_w5c[1]:.0f} Hz, Q = {_w5c[2]}) ⇒ **{_w5c_v:.2f} dBFS**")
print(f"      ⚠ 与默认点 ({d3_worst:.2f}) 相差 {_w5c_v-d3_worst:.2f} dB ——")
print(f"        **⇒ 报给 CTO 的量级由『破 {abs(d3_worst+106):.2f} dB』更正为『破 {_w5c_v+106:.2f} dB』。**")
print(f"        ⇒ ⚠ 定性结论**不变**(增益结构必须返工);⛔ 变的是量级与「最坏」这个词。")
# ---- 跑后节:对预注册 §3「预期值」的更正(critic D3D4-r3 m-1)-------------------
#   ⛔ 预注册是乙类件,件内一字不动 ⇒ 更正写在这里(本轮结果的跑后节)。
print(f"\n      ⚠ 对 PREREG_D34_r16_addendum §3 预期栏的更正(⛔ 不改预注册原件):")
print(f"        预注册写「预期:EXP-5c FAIL(**实算约 −91.6 dBFS**)」,而 r16 实测 −76.97,差 14.67 dB。")
print(f"        ⛔ 这**不是预测失败**,是【预期值引错了口径】:")
print(f"          −91.64 是 **8×PEQ 段**(8 个量化器)的值;−76.97 是 **D3 输入链**(9 个,多一个链首 HPF)。")
print(f"          两个数在 results_d34_r13.txt:145/146 同时存在,预注册引了另一条链的那个。")
print(f"          ⇒ EXP-5c 的**实现**取的口径与 §3 正文一致(D3 输入链)⇒ **实现对、预期栏错**。")
print(f"        ⭐ 而那 14.67 dB 的物理含义(独立复核 check_r17_worstQ.py R5):")
print(f"          它就是**链首那一个量化器**贡献的 —— 它的噪声要过完后面 8 段 +15 dB。")
print(f"          ⇒ **越靠链首的量化器越贵** ⇒ 与 erratum1 的噪声轴同向(增益越靠后,被放大的上游越多)。")
OK("EXP-5c", _w5c_v <= -106.0,
   f"⛔ 在**参数字典自己声明的范围**(band_q ∈ [{PEQ_Q_RANGE[0]}, {PEQ_Q_RANGE[1]}]、"
   f"band_gain ≤ +{PEQ_GAIN_MAX:.0f} dB、band_freq 20…20 kHz)上求最坏:"
   f"链末噪声底 {_w5c_v:.2f} dBFS @ (f0={_w5c[1]:.0f} Hz, Q={_w5c[2]}) ≤ −106(PRD)"
   f" ⇒ 实测突破 {_w5c_v+106:.2f} dB")
print("      ⛔⛔ EXP-5c 的处置【预先写死在 PREREG_D34_r16_addendum §3】:")
print("        它 FAIL 就以 FAIL 的身份留在结果里。⛔ 不退役、⛔ 不改判据、")
print("        ⛔ 不因'已路由给 architect/D2'就当它不存在 —— 处置权在别人手里,")
print("        不改变【本轮它是 FAIL】这个事实。(EXP-10b 那次是'该响的没响',本条先写死'必须响'。)")
print(f"      ⇒ 处置属**增益结构设计**,是一个 headroom-vs-噪声的**权衡**")
print(f"        (增益靠前:噪声底低、饱和风险高;靠后:反之)⇒ ⛔ 不是改格式。")
print(f"        ⛔ 「把大增益放链尾」已撤回(critic D3D4 erratum1):它在噪声轴上方向反了。")
print(f"      ⚠ 第二轨 = check_noise_chain_r5.py(独立实现,不 import 本件)。")
print(f"        ⛔ 而两轨在【D3 的量化器个数】上不一致:本件按 9(HPF+PEQ×8),")
print(f"        r5 脚本按 12(多算了 3 个'链尾单位增益量化器')—— 而本件 §6 自己写明")
print(f"        门/压限/延时**不引入新量化器** ⇒ **9 是对的,r5 的 12 是错的**;")
print(f"        差 {10*math.log10(12/9):.2f} dB,只影响各节增益=1 那一格,最坏配置那一格几乎不受影响。")

# ---------------------------------------------------------------- EXP-6
print("\nEXP-6  按竞品 Q 口径(0.02~50)重扫 PEQ 系数上界 —— 闭台账 C2")
print("-"*84)
q_lo, q_hi = 0.02, 50.0
fg6 = np.geomspace(20.0, 20000.0, 300)
qg6 = np.geomspace(q_lo, q_hi, 60)
gg6 = np.arange(-15.0, 15.5, 0.5)
best, bpt = 0.0, None
for f0 in fg6:
    for Q in qg6:
        for G in gg6:
            b, a = rbj_peaking(f0, Q, G)
            m = float(np.max(np.abs(b)))
            if m > best: best, bpt = m, (f0, Q, G)
A2 = 10**(15.0/20.0)
print(f"    数值扫描 max|b| = {best:.4f} @ (f={bpt[0]:.1f} Hz, Q={bpt[1]:.4f}, G={bpt[2]:+.1f} dB)")
print(f"    解析第二轨:RBJ 峰型 alpha->inf 时 b0/a0 -> A^2 = 10^(G/20) = {A2:.4f}  (G=+15 dB)")
print(f"    架式的全族最大值(任务一)= 11.2148;Q4.27 上限 = 16")
OK("EXP-6a", best <= A2 + 1e-6, f"数值扫描 {best:.4f} 不超过解析上界 A^2 = {A2:.4f}(两轨自洽)")
OK("EXP-6b", best < 11.2148, f"PEQ 在竞品 Q 口径下仍小于架式的 11.2148 ⇒ 全族最大值不变,C2 可从红降黄")
OK("EXP-6c", best < 16.0, "PEQ 在竞品 Q 口径下不突破 Q4.27 ⇒ 系数格式裁决不被推翻")

# ---------------------------------------------------------------- EXP-7
print("\nEXP-7  系数界:经验扫描界 → 【解析界】(架构侧意见,r4)")
print("-"*84)
print("    解析界(推导见 PREREG_D34_r4_addendum §1):")
print("      峰型   max|b| <= max(2, A^2)          A = 10^(G/40)   —— 与 Q、与频率无关")
print("      架式   max|b| <= 2*A^2                                —— 与 S、与频率无关")
print("      HPF/LPF max|b| <= 2                                   —— 与 Q、与频率无关")
print("      a 系数 稳定三角 |a1|<2, |a2|<1                        —— 构造上不可超越")
print("      ⇒ 全族 max|b| <= 2 * 10^(G_max/20),【只依赖 G_max】")
def rbj_lowshelf(f0, S, gdb):
    A = 10**(gdb/40); w0 = 2*np.pi*f0/FS
    al = np.sin(w0)/2*np.sqrt((A+1/A)*(1/S-1)+2); c = np.cos(w0); t = 2*np.sqrt(A)*al
    a0 = (A+1)+(A-1)*c+t
    return (np.array([A*((A+1)-(A-1)*c+t), 2*A*((A-1)-(A+1)*c), A*((A+1)-(A-1)*c-t)])/a0,
            np.array([1.0, -2*((A-1)+(A+1)*c)/a0, ((A+1)+(A-1)*c-t)/a0]))
def rbj_highshelf(f0, S, gdb):
    A = 10**(gdb/40); w0 = 2*np.pi*f0/FS
    al = np.sin(w0)/2*np.sqrt((A+1/A)*(1/S-1)+2); c = np.cos(w0); t = 2*np.sqrt(A)*al
    a0 = (A+1)-(A-1)*c+t
    return (np.array([A*((A+1)+(A-1)*c+t), -2*A*((A-1)+(A+1)*c), A*((A+1)+(A-1)*c-t)])/a0,
            np.array([1.0, 2*((A-1)-(A+1)*c)/a0, ((A+1)-(A-1)*c-t)/a0]))
fg7 = np.geomspace(20.0, 20000.0, 250)
qg7 = np.geomspace(0.02, 50.0, 40)
sg7 = np.array([0.3, 0.5, 0.7071, 0.85, 1.0, 1.5, 2.0])
viol, tight_bad = 0, 0
print(f"\n    {'G_max':>6s} {'解析界 2*A^2':>13s} {'峰型扫描':>10s} {'架式扫描':>10s} {'HPF/LPF扫描':>12s} {'紧度(架式/界)':>14s}")
for G in [6.0, 12.0, 15.0, 18.0]:
    A2 = 10**(G/20.0)
    an_all = 2*A2
    mp = max(float(np.max(np.abs(rbj_peaking(f, q, g)[0])))
             for f in fg7 for q in qg7 for g in (G, -G))
    ms = max(float(np.max(np.abs(mk(f, sv, g)[0])))
             for f in fg7 for sv in sg7 for g in (G, -G) for mk in (rbj_lowshelf, rbj_highshelf))
    mh = max(float(np.max(np.abs(bw_hp(f, q)[0]))) for f in fg7 for q in qg7)
    mh = max(mh, max(float(np.max(np.abs(bw_lp(f, q)[0]))) for f in fg7 for q in qg7))
    if mp > max(2.0, A2) + 1e-9: viol += 1
    if ms > an_all + 1e-9: viol += 1
    if mh > 2.0 + 1e-9: viol += 1
    tight = ms/an_all
    if tight < 0.99: tight_bad += 1
    print(f"    {G:6.1f} {an_all:13.4f} {mp:10.4f} {ms:10.4f} {mh:12.4f} {tight:14.4f}")
OK("EXP-7a", viol == 0, f"全部数值扫描均不越解析界({viol} 处越界)")
OK("EXP-7b", tight_bad == 0, "架式扫描值/解析界 >= 0.99 ⇒ 界是紧的,可替代扫描")
Ghard = 20*math.log10(8.0)
print(f"\n    ⇒ Q4.27 的【解析硬包络】: 2*10^(G/20) < 16 ⇒ G_max < 20*log10(8) = {Ghard:.4f} dB")
print(f"      (r3 的扫描包络为 18.089 dB;解析值略严,因扫描取不到 c=±1 与 alpha=0 的极限)")
OK("EXP-7c", Ghard < 18.089, "解析硬包络严于扫描包络 ⇒ 用解析界是保守方向")

# ---------------------------------------------------------------- EXP-8
print("\nEXP-8  延迟逐项表(我这一侧)+ 逐频相加 vs 各自最大值相加")
print("-"*84)
def gd_curve(secs, wv):
    g = np.zeros_like(wv)
    for b, a in secs:
        _, gg = signal.group_delay((b, a), w=wv); g += gg
    return g
w8 = np.linspace(2*np.pi*20/FS, np.pi-1e-6, 200000); f8 = w8*FS/(2*np.pi)
m8 = (f8 >= 20) & (f8 <= 20000)
# 我这一侧的典型配置
items = []
items.append(("D3 HPF  BW12 @80Hz", [qsec(bw_hp(80.0, 0.7071), 'hp')]))
peq8 = [qsec(rbj_peaking(f0, q, g)) for f0, q, g in
        [(63,1.4,+4),(160,1.4,-5),(400,2.0,+3),(1000,1.0,-4),
         (2500,1.4,+5),(4000,2.0,-3),(8000,1.0,+4),(12500,0.7,-6)]]
items.append(("D3 PEQ x8(典型设置)", peq8))
items.append(("D4 分频 LR8 HP @80Hz", [qsec(s,'hp') for s in lr_sections(80.0, 8, 'hp')]))
peq10 = peq8 + [qsec(rbj_peaking(f0, q, g)) for f0, q, g in [(315,1.4,+3),(6300,1.4,-4)]]
items.append(("D4 PEQ x10(典型设置)", peq10))
tot = np.zeros_like(w8); sum_of_max = 0.0
print(f"    {'模块':26s} {'最大群延迟(ms)':>15s} {'峰值频率(Hz)':>13s}")
for nm, secs in items:
    g = gd_curve(secs, w8)
    tot += g
    i = int(np.argmax(g[m8])); pk = g[m8][i]/FS*1e3
    sum_of_max += pk
    print(f"    {nm:26s} {pk:15.3f} {f8[m8][i]:13.1f}")
i = int(np.argmax(tot[m8])); aligned = tot[m8][i]/FS*1e3
print(f"    {'——':26s}")
print(f"    (a) 各项最大值【相加】       = {sum_of_max:8.3f} ms   ← 各峰在【不同频率】")
print(f"    (b) 逐频相加后的最大值       = {aligned:8.3f} ms   @ {f8[m8][i]:.1f} Hz  ← 真实最坏频点")
print(f"    ⇒ (a) 高估了 {sum_of_max-aligned:.3f} ms")
RETIRED("EXP-8a", sum_of_max - aligned >= 1.0,
   f"原判据「高估 >=1 ms」实测 {sum_of_max-aligned:.3f} ms ⇒ 未达判据(证伪条件 <0.1 ms 未触发)。"
   f"根因:我选的四个模块峰值频率全部落在 51.5-71.1 Hz —— 低频滤波器的群延迟峰天然都在低频,"
   f"本来就对齐。⇒ 由 EXP-8b 用【峰分散】的配置作独立再观测。")

# ---- EXP-8b(r5):峰是否聚集,决定能不能简单相加 ----
print("\nEXP-8b 峰是否聚集 ⇒ 能不能简单相加(r5 独立再观测)")
for tag, xo_fc in [("配置① 分频 LR8 @80Hz(与低频 PEQ 同处低频)", 80.0),
                   ("配置② 分频 LR8 @2kHz(峰与低频 PEQ 分开)", 2000.0)]:
    it2 = [("D3 HPF BW12 @80Hz", [qsec(bw_hp(80.0, 0.7071), 'hp')]),
           ("D3 PEQ x8", peq8),
           (f"D4 分频 LR8 @{xo_fc:.0f}Hz", [qsec(s,'hp') for s in lr_sections(xo_fc, 8, 'hp')]),
           ("D4 PEQ x10", peq10)]
    tt = np.zeros_like(w8); som = 0.0; pks = []
    for nm2, sc in it2:
        g = gd_curve(sc, w8); tt += g
        j = int(np.argmax(g[m8])); som += g[m8][j]/FS*1e3; pks.append(f8[m8][j])
    j = int(np.argmax(tt[m8])); al = tt[m8][j]/FS*1e3
    print(f"    {tag}")
    print(f"      各峰频率 = {[round(v,1) for v in pks]} Hz")
    print(f"      (a) 各自最大值相加 = {som:7.3f} ms | (b) 逐频相加最大 = {al:7.3f} ms @ {f8[m8][j]:6.1f} Hz | 高估 {som-al:6.3f} ms")
    if xo_fc == 80.0:
        _c1 = som-al
    else:
        _c2 = som-al
RETIRED("EXP-8b", _c1 < 1.0 and _c2 > 2.0,
   f"预注册的【证伪条件命中】:峰分散配置的高估 {_c2:.3f} ms < 1.0 ms(甚至小于峰聚集时的 {_c1:.3f})。"
   f"⇒ 「峰是否聚集决定能否简单相加」这条假设【不成立】。"
   f"根因:被移开的那一项(分频 @2kHz)本身贡献就小(0.627 ms),移开它不产生大缺口。"
   f"⇒ 按 PREREG_D34_r5_addendum §2 预先写死的分支,执行【撤回 r4 的那条更正】。")

print("\n    ⇒ ⭐【给架构侧的一句可执行结论】(按预注册分支执行)")
print(f"      **撤回我在 r4 提的「各自最大值相加会系统性高估」那条更正。**")
print(f"      实测两种配置下高估分别只有 {_c1:.3f} ms 与 {_c2:.3f} ms")
print(f"      ⇒ **简单相加可用,保守量 <0.8 ms;⛔ 不要指望峰错开带来抵消。**")
print(f"      ⇒ 配平表按简单相加做即可,不必逐频卷积。")
OK("EXP-8c", max(_c1, _c2) < 1.0,
   f"两种配置的高估均 <1.0 ms(实测 {_c1:.3f} / {_c2:.3f})⇒ 简单相加是可用的保守近似")

print(f"\n    可降档位(我这一侧):")
rows = []
for lr in [8, 4, 2]:
    for fc in [80.0, 120.0, 200.0]:
        g = gd_curve([qsec(s,'hp') for s in lr_sections(fc, lr, 'hp')], w8)
        rows.append((f"分频 LR{lr} @{fc:.0f}Hz", float(np.max(g[m8]))/FS*1e3))
base = rows[0][1]
for nm, v in rows:
    print(f"      {nm:22s} {v:8.3f} ms   省 {base-v:+8.3f} ms(相对 LR8@80Hz)")
print()
_fir_base = (512-1)/2          # 基准 = 512 tap 的群延迟 255.5 样本
for Nt in [1024, 512, 256, 128, 0]:
    gd = (Nt-1)/2 if Nt > 0 else 0
    tag = f"{Nt} tap" if Nt else "关闭"
    print(f"      FIR {tag:>9}        {gd/FS*1e3:8.3f} ms   省 {(_fir_base-gd)/FS*1e3:+8.3f} ms(相对 512 tap)")
print()
for L in [64, 32]:
    print(f"      块 I/O L={L:3d}(2L 乒乓)  {2*L/FS*1e3:8.3f} ms   省 {(128-2*L)/FS*1e3:+8.3f} ms(相对 L=64)")
print(f"      块 I/O L= 64(单缓冲)     {64/FS*1e3:8.3f} ms   省 {64/FS*1e3:+8.3f} ms  ⚠ 口径归 platform-fw")
print(f"      lim_lookahead 1→0 ms      0.000 ms   省 {1.0:+8.3f} ms  ⚠ 代价:限幅改反馈式,过冲不受控")
# ⛔ 整改 2026-08-05(critic m-7):原先这里写死字面量 0.99967 —— 那是 47.9844/48 = 0.999675
#   的【截断】(平局应远离零 ⇒ 0.99968;PREREG_D34_r1.txt:90 当时写的就是 0.99968)。
#   ⚠ 只有这一处显示是字面量,全部算术走的是下面的 ADC_DAC(由样本数算),⇒ 数值结论不受影响。
print(f"      转换器 ADC+DAC            {(22.9844 + 25.0)/FS*1e3:8.4f} ms   ⛔ 不可降(器件固有)")

# ---------------------------------------------------------------- EXP-9
print("\nEXP-9  参考配置(REF) vs 最坏可配置(WORST) —— 急件,定义与理由见 PREREG_r8 §1/§2")
print("-"*84)
ADC_DAC = (22.9844 + 25.0)/FS*1e3
BLK_L64 = 2*64/FS*1e3

def bq_list(spec):
    return [qsec(rbj_peaking(f0, q, g)) for f0, q, g in spec]
def hp_chain(order, fc):
    if order == 2: return [qsec(bw_hp(fc, 0.7071), 'hp')]
    return [qsec(bw_hp(fc, q), 'hp') for q in butter_qs(order)]

REF_PEQ_IN = [(45,8.0,-6),(72,6.0,-5),(250,1.4,-4),(3150,1.0,+3)]
REF_PEQ_OUT= REF_PEQ_IN + [(8000,0.7,-3)]
WORST_PEQ_IN  = [(20.0,50.0,+15)]*8
WORST_PEQ_OUT = [(20.0,50.0,+15)]*10

def report(tag, hpf_secs, peq_in, peq_out, xo_secs, fir_taps, look_ms):
    rows=[]; tot=np.zeros_like(w8); two=0.0
    def add(nm, secs):
        nonlocal tot, two
        g = gd_curve(secs, w8)
        # 两轨核
        z=np.exp(-1j*w8); H=np.ones_like(z)
        for b,a in secs: H*=(b[0]+b[1]*z+b[2]*z*z)/(a[0]+a[1]*z+a[2]*z*z)
        g2=-np.gradient(np.unwrap(np.angle(H)), w8)
        two=max(two, float(np.max(np.abs(g[m8]-g2[m8]))))
        tot+=g
        i=int(np.argmax(g[m8])); rows.append((nm, g[m8][i]/FS*1e3, f8[m8][i]))
    add("D3 HPF", hpf_secs)
    if peq_in:  add(f"D3 PEQ(启用 {len(peq_in)} 段)", bq_list(peq_in))
    add("D4 分频", xo_secs)
    if peq_out: add(f"D4 PEQ(启用 {len(peq_out)} 段)", bq_list(peq_out))
    fir_ms = ((fir_taps-1)/2)/FS*1e3 if fir_taps else 0.0
    iir_sum = sum(r[1] for r in rows)
    total = ADC_DAC + BLK_L64 + iir_sum + fir_ms + look_ms
    print(f"\n  ── {tag} ──")
    for nm, v, fp in rows:
        print(f"     {nm:24s} {v:9.3f} ms   峰 @ {fp:8.1f} Hz")
    print(f"     {'转换器 ADC+DAC':24s} {ADC_DAC:9.4f} ms")   # ⛔ m-7:.5f 会印出截断值 0.99967
    print(f"     {'块 I/O (L=64, 2L)':24s} {BLK_L64:9.3f} ms")
    print(f"     {'线性相位 FIR':24s} {fir_ms:9.3f} ms   ({fir_taps if fir_taps else '关'} tap)")
    print(f"     {'lim_lookahead':24s} {look_ms:9.3f} ms")
    print(f"     {'——— 求和(lead 已裁定口径)':24s} {total:9.3f} ms   余 {12.0-total:+8.3f} ms")
    return total, iir_sum, two, rows

ref_tot, ref_iir, tw1, ref_rows = report(
    "REF 参考配置(会议室典型部署;依据 PREREG_r8 §1)",
    hp_chain(2, 80.0), REF_PEQ_IN, REF_PEQ_OUT,
    [qsec(x,'hp') for x in lr_sections(80.0, 4, 'hp')], 0, 1.0)
wor_tot, wor_iir, tw2, _ = report(
    "WORST 最坏可配置(参数量程内;⛔ 只用于定运行时拦截线)",
    hp_chain(4, 20.0), WORST_PEQ_IN, WORST_PEQ_OUT,
    [qsec(x,'hp') for x in lr_sections(20.0, 8, 'hp')], 512, 2.0)

print(f"\n  ⇒ WORST / REF = {wor_tot/ref_tot:.1f}×")
OK("EXP-9a", wor_tot/ref_tot >= 10.0, f"WORST/REF = {wor_tot/ref_tot:.1f}× ≥10 ⇒ 运行时校验确有必要")
RETIRED("EXP-9d", max(tw1, tw2) <= 0.05,
   f"两轨最大差 {max(tw1,tw2):.1f} 样本 ⇒ 证伪条件命中。根因非某一轨错,而是 WORST 的极点贴单位圆、"
   f"两轨在同一处一起失去 float64 精度。⇒ 已由 r10 的【按配置分开做两轨】取代(REF 差 0.18 样本可报,"
   f"WORST 数值不得报出、只报量级)。")
peq8_ref = [r[1] for r in ref_rows if r[0].startswith("D3 PEQ")][0]
print(f"  ⇒ REF 的 D3 PEQ 项 = {peq8_ref:.3f} ms;上轮「8 段分散」那组 = 3.771 ms")
RETIRED("EXP-9b", peq8_ref < 3.771,
   f"REF 的 PEQ 项 {peq8_ref:.3f} ms > 上轮 8 段那组 3.771 ms ⇒ 判据未达。"
   f"⇒ 这正是 PREREG_r8 §3 预先写下的另一分支【窄 Q 主导】,已由 EXP-10c 独立证实"
   f"(Q 的影响是段数的 8.02 倍)。⇒ 结论:群延迟由【最低频那段的 Q】决定,不由【启用几段】决定。")

print("\n  EXP-9c  拒绝率的定量代理:从 REF 出发,还能再加几段低频窄 Q 陷波才撞 12 ms")
extra_specs = [(50,8.0,-6),(63,8.0,-6),(90,8.0,-6),(110,8.0,-6),(130,8.0,-6),(160,8.0,-6)]
cur_in = list(REF_PEQ_IN); n_ok = 0
for k, sp in enumerate(extra_specs):
    cur_in.append(sp)
    g_hpf = gd_curve(hp_chain(2, 80.0), w8)
    g_in  = gd_curve(bq_list(cur_in), w8)
    g_xo  = gd_curve([qsec(x,'hp') for x in lr_sections(80.0, 4, 'hp')], w8)
    g_out = gd_curve(bq_list(REF_PEQ_OUT), w8)
    iir = sum(float(np.max(g[m8]))/FS*1e3 for g in (g_hpf, g_in, g_xo, g_out))
    t = ADC_DAC + BLK_L64 + iir + 0.0 + 1.0
    status = "✓ 通过" if t <= 12.0 else "✗ 被拒"
    print(f"     +{k+1} 段({sp[0]} Hz Q={sp[1]} {sp[2]:+} dB) ⇒ 合计 {t:7.3f} ms  余 {12.0-t:+7.3f}  {status}")
    if t <= 12.0: n_ok = k+1
    else: break
print(f"     ⇒ 从 REF 出发可再追加 **{n_ok} 段**低频窄 Q 陷波才撞拒绝线")
RETIRED("EXP-9c", n_ok >= 2, f"可追加 {n_ok} 段(20 Hz–20 kHz 口径)。  ⇒ 这三条断言的是【对一个尚未定义作用域的规格】的符合性:PRD §一.4 只写了 12 ms,没写评价频带。在 CTO 定下频带之前,它们既不能 PASS 也不能 FAIL(与 LESSONS C-3「分辨力之下不可判」同型:此处是【判据本身未定义】)。⇒ 退役为【测量项】,决策输入由 EXP-11 的 f_lo* = 105.2 Hz 给出。")

# ---------------------------------------------------------------- r9
print("\nr9  —— 处置 r8 的三条证伪(见 PREREG_D34_r9_addendum)")
print("-"*84)

def gd_closed_form(secs, wv):
    """第二轨:我自己写的闭式群延迟(⛔ 不调 scipy.group_delay、不做 unwrap)。"""
    tot = np.zeros_like(wv)
    c1, s1 = np.cos(wv), np.sin(wv)
    c2, s2 = np.cos(2*wv), np.sin(2*wv)
    for b, a in secs:
        def darg(k):
            Re = k[0] + k[1]*c1 + k[2]*c2
            Im = -(k[1]*s1 + k[2]*s2)
            Rp = -(k[1]*s1) - 2*k[2]*s2
            Ip = -(k[1]*c1 + 2*k[2]*c2)
            return (Re*Ip - Im*Rp)/(Re*Re + Im*Im)
        tot += -darg(b) + darg(a)
    return tot

# 频率网格改对数,低频加密(F-1 的根因之一)
wl = 2*np.pi*np.geomspace(20.0, FS/2*0.999, 400000)/FS
fl = wl*FS/(2*np.pi)
BANDS = [("(a) 20 Hz–20 kHz", 20.0, 20000.0),
         ("(b) 100 Hz–8 kHz", 100.0, 8000.0),
         ("(c) 200 Hz–8 kHz", 200.0, 8000.0)]

def chain_secs(hp_order, hp_fc, peq_in, xo_lr, xo_fc, peq_out):
    sc = hp_chain(hp_order, hp_fc) + bq_list(peq_in) \
         + [qsec(x,'hp') for x in lr_sections(xo_fc, xo_lr, 'hp')] + bq_list(peq_out)
    return sc

CFG_REF  = dict(hp_order=2, hp_fc=80.0,  peq_in=REF_PEQ_IN,  xo_lr=4, xo_fc=80.0,
                peq_out=REF_PEQ_OUT, fir=0,   look=1.0)
CFG_WOR  = dict(hp_order=4, hp_fc=20.0,  peq_in=WORST_PEQ_IN, xo_lr=8, xo_fc=20.0,
                peq_out=WORST_PEQ_OUT, fir=512, look=2.0)

print("\n  ⭐ EXP-10  12 ms 到底约束哪个频带 —— 三个评价频带各报一次")
print(f"     固定项:转换器 {ADC_DAC:.4f} + 块 I/O {BLK_L64:.3f} ms")   # ⛔ m-7 同上
two_worst = 0.0
tbl = {}
for tag, cfg in [("REF", CFG_REF), ("WORST", CFG_WOR)]:
    sc = chain_secs(cfg['hp_order'], cfg['hp_fc'], cfg['peq_in'],
                    cfg['xo_lr'], cfg['xo_fc'], cfg['peq_out'])
    g1 = gd_curve(sc, wl)                      # 轨1:scipy 逐节求和
    g2 = gd_closed_form(sc, wl)                # 轨2:我写的闭式
    two_worst = max(two_worst, float(np.max(np.abs(g1-g2))))
    fir_ms = ((cfg['fir']-1)/2)/FS*1e3 if cfg['fir'] else 0.0
    fixed = ADC_DAC + BLK_L64 + fir_ms + cfg['look']
    print(f"\n     ── {tag} ──   固定项合计 {fixed:.3f} ms(含 FIR {fir_ms:.3f} + lookahead {cfg['look']:.1f})")
    for bname, lo, hi in BANDS:
        mk = (fl >= lo) & (fl <= hi)
        iir = float(np.max(g1[mk]))/FS*1e3
        pf  = fl[mk][int(np.argmax(g1[mk]))]
        tot = fixed + iir
        tbl[(tag, bname)] = tot
        print(f"        {bname:18s} IIR 峰 {iir:10.3f} ms @ {pf:8.1f} Hz | 全链 {tot:10.3f} ms | 余 {12.0-tot:+9.3f} ms"
              f"  {'✓' if tot <= 12.0 else '✗'}")
# r10:两轨核【按配置分开】(G-1)
for tag, cfg in [("REF", CFG_REF), ("WORST", CFG_WOR)]:
    sc = chain_secs(cfg['hp_order'], cfg['hp_fc'], cfg['peq_in'],
                    cfg['xo_lr'], cfg['xo_fc'], cfg['peq_out'])
    d = float(np.max(np.abs(gd_curve(sc, wl) - gd_closed_form(sc, wl))))
    if tag == "REF":
        OK("r10-2trkREF", d <= 0.5, f"REF 两轨差 {d:.4f} 样本 ≤0.5 ⇒ REF 的数可报")
    else:
        RETIRED("r10-2trkWOR", d <= 0.5,
            f"WORST 两轨差 {d:.1f} 样本 ⇒ 极点半径 r≈1−5e−5,|D| 落到 float64 精度以下,"
            f"**两轨在同一处一起失去精度**。⇒ 按 PREREG_r10 §1:WORST 的群延迟【数值不得报出】,"
            f"只报量级(EXP-13)。")
OK("EXP-10", tbl[("REF","(c) 200 Hz–8 kHz")] <= 12.0,
   f"REF 在 (c) 200 Hz–8 kHz 下全链 {tbl[('REF','(c) 200 Hz–8 kHz')]:.3f} ms ≤ 12 ⇒ 评价频带下沿是决定项")
RETIRED("EXP-10a2", tbl[("REF","(b) 100 Hz–8 kHz")] <= 12.0,
   f"REF 在 (b) 100 Hz–8 kHz 下 {tbl[('REF','(b) 100 Hz–8 kHz')]:.3f} ms(超 0.835),峰恰在 100.0 Hz 带下沿。  ⇒ 这三条断言的是【对一个尚未定义作用域的规格】的符合性:PRD §一.4 只写了 12 ms,没写评价频带。在 CTO 定下频带之前,它们既不能 PASS 也不能 FAIL(与 LESSONS C-3「分辨力之下不可判」同型:此处是【判据本身未定义】)。⇒ 退役为【测量项】,决策输入由 EXP-11 的 f_lo* = 105.2 Hz 给出。")

print("\n  EXP-10b 拒绝率代理:在几个候选评价频带下沿,从 REF 还能加几段低频窄 Q 陷波")
extra = [(50,8.0,-6),(63,8.0,-6),(90,8.0,-6),(110,8.0,-6),(130,8.0,-6),(160,8.0,-6),(200,8.0,-6),(250,8.0,-6)]
n_by_band = {}
for f_edge in [100.0, 125.0, 150.0, 200.0]:
    cur = list(REF_PEQ_IN); nn = 0
    mkb = (fl >= f_edge) & (fl <= 8000.0)
    for k, sp in enumerate(extra):
        cur.append(sp)
        sc = chain_secs(2, 80.0, cur, 4, 80.0, REF_PEQ_OUT)
        iir = float(np.max(gd_curve(sc, wl)[mkb]))/FS*1e3
        t = ADC_DAC + BLK_L64 + iir + 1.0
        if t <= 12.0: nn = k+1
        else: break
    n_by_band[f_edge] = (nn, t)
    print(f"        下沿 {f_edge:5.0f} Hz ⇒ 可再追加 **{nn}** 段(第 {nn+1} 段时全链 {t:.3f} ms 撞线)")
n_ok2 = n_by_band[100.0][0]
RETIRED("EXP-10b", n_ok2 >= 4, f"(b) 口径下可再追加 {n_ok2} 段。  ⇒ 这三条断言的是【对一个尚未定义作用域的规格】的符合性:PRD §一.4 只写了 12 ms,没写评价频带。在 CTO 定下频带之前,它们既不能 PASS 也不能 FAIL(与 LESSONS C-3「分辨力之下不可判」同型:此处是【判据本身未定义】)。⇒ 退役为【测量项】,决策输入由 EXP-11 的 f_lo* = 105.2 Hz 给出。")

print("\n  EXP-10c 敏感度分离:群延迟是【Q】主导还是【段数】主导?")
mka = (fl >= 20.0) & (fl <= 20000.0)
print(f"        ① 固定 4 段(45/72/250/3150 Hz),低频两段的 Q 扫描:")
qs_ = [1.4, 2.0, 4.0, 6.0, 8.0, 10.0]; v1 = []
for qq in qs_:
    spec = [(45,qq,-6),(72,qq,-5),(250,1.4,-4),(3150,1.0,+3)]
    v = float(np.max(gd_curve(bq_list(spec), wl)[mka]))/FS*1e3
    v1.append(v); print(f"           Q = {qq:5.1f} ⇒ {v:8.3f} ms")
print(f"        ② 固定 Q=1.4,段数 1→8(频点分散 63…12500 Hz):")
allspec = [(63,1.4,+4),(160,1.4,-5),(400,1.4,+3),(1000,1.4,-4),(2500,1.4,+5),(4000,1.4,-3),(8000,1.4,+4),(12500,1.4,-6)]
v2 = []
for n in range(1, 9):
    v = float(np.max(gd_curve(bq_list(allspec[:n]), wl)[mka]))/FS*1e3
    v2.append(v); print(f"           段数 = {n} ⇒ {v:8.3f} ms")
r1_ = max(v1)-min(v1); r2_ = max(v2)-min(v2)
print(f"        ⇒ Q 扫描的变化幅度 = {r1_:.3f} ms;段数扫描的变化幅度 = {r2_:.3f} ms;比值 {r1_/max(r2_,1e-9):.2f}×")
OK("EXP-10c", r1_ >= 3.0*r2_,
   f"Q 的影响是段数的 {r1_/max(r2_,1e-9):.2f} 倍(判据 ≥3)⇒ 【窄 Q 主导,段数不主导】,F-2 判读成立")

# ---------------------------------------------------------------- r10
print("\nr10 —— 决策数与杠杆(PREREG_D34_r10_addendum)")
print("-"*84)

def ref_total(f_lo, f_hi=8000.0, peq_in=None, q_lo=None):
    pin = peq_in if peq_in is not None else REF_PEQ_IN
    if q_lo is not None:
        pin = [(45,q_lo[0],-6),(72,q_lo[1],-5),(250,1.4,-4),(3150,1.0,+3)]
    sc = chain_secs(2, 80.0, pin, 4, 80.0, REF_PEQ_OUT)
    mk = (fl >= f_lo) & (fl <= f_hi)
    iir = float(np.max(gd_curve(sc, wl)[mk]))/FS*1e3
    return ADC_DAC + BLK_L64 + iir + 1.0, iir

print("\n  ⭐ EXP-11  REF 恰好等于 12 ms 的评价频带下沿 f_lo*")
lo_, hi_ = 20.0, 500.0
for _ in range(60):
    mid = math.sqrt(lo_*hi_)
    t, _i = ref_total(mid)
    if t > 12.0: lo_ = mid
    else: hi_ = mid
f_lo_star = hi_
t_at, _ = ref_total(f_lo_star)
print(f"     f_lo* = **{f_lo_star:.1f} Hz**(此时 REF 全链 = {t_at:.3f} ms)")
for fx in [20, 50, 80, 100, 125, 150, 200, 250]:
    t, i = ref_total(float(fx))
    print(f"       下沿 {fx:4d} Hz ⇒ IIR 峰 {i:8.3f} ms | 全链 {t:8.3f} ms | 余 {12.0-t:+8.3f}  {'✓' if t<=12 else '✗'}")
OK("EXP-11", 100.0 <= f_lo_star <= 300.0,
   f"f_lo* = {f_lo_star:.1f} Hz 落在 100–300 Hz(证伪线 >300 Hz 未触发)")
mk_ex = (fl >= 20.0) & (fl <= f_lo_star)
sc_ref = chain_secs(2, 80.0, REF_PEQ_IN, 4, 80.0, REF_PEQ_OUT)
ex_max = float(np.max(gd_curve(sc_ref, wl)[mk_ex]))/FS*1e3
print(f"     EXP-11b 代价:被排除的 20–{f_lo_star:.0f} Hz 内,REF 群延迟最大 **{ex_max:.3f} ms**")
print(f"             ⇒ 这是「同意不管的那一段有多糟」的数,交 CTO 权衡")

print("\n  ⭐ EXP-12  杠杆:降低频房间陷波的 Q(在最严的 (a) 20 Hz–20 kHz 口径下)")
base_t = None
for qq in [(8.0,6.0),(6.0,4.0),(4.0,3.0),(2.0,1.4)]:
    t, i = ref_total(20.0, 20000.0, q_lo=qq)
    if base_t is None: base_t = t
    print(f"     房间陷波 Q = {qq[0]:4.1f}/{qq[1]:4.1f} ⇒ IIR 峰 {i:8.3f} ms | 全链 {t:8.3f} ms | 相对 Q=8/6 省 {base_t-t:+7.3f} ms")
t_lowq, _ = ref_total(20.0, 20000.0, q_lo=(2.0,1.4))
OK("EXP-12", base_t - t_lowq >= 5.0,
   f"Q 从 8/6 降到 2/1.4 省 {base_t-t_lowq:.3f} ms(判据 ≥5)⇒ 降 Q 是有效杠杆")
print("     ⚠ 代价:陷波变宽 ⇒ 削掉驻波两侧的有用频段;房间驻波修正效果下降")

print("\n  EXP-13  WORST 只报量级(其群延迟数值在 float64 下不可确定)")
tau_1 = 2*50.0/(2*np.pi*20.0)
print(f"     解析:高 Q 二阶节峰值群延迟 ≈ 2Q/ω₀ [L3];Q=50 @20 Hz ⇒ {tau_1*1e3:.1f} ms / 节")
print(f"     WORST 含 18 个峰型节 ⇒ 量级 ≈ {18*tau_1:.1f} 秒")
print(f"     (r9 的数值轨给 27.9 s,同量级;⛔ 但该数值不可信,只作量级旁证)")
OK("EXP-13", 18*tau_1 >= 1.0, f"解析量级 {18*tau_1:.1f} s ≥ 1 s ⇒ WORST 必须被拦,论证不依赖精确值")
print("     ⇒ ⭐ 运行时校验的拦截线**不应基于群延迟数值**(极端配置下算不准),")
print("        **应基于参数本身**(如 f0 与 Q 的组合上限)。⇒ 已写进设计件。")

# ================================================================ META-1
# ⭐⭐ 元检查(critic D3D4-r3 MAJOR-2 修法②):**登记在案的判定项必须还在**
#   理由(critic 原话):**「EXP-5c 在不在,不能由 EXP-5c 自己回答」** —— 它被删了就不会报警。
#   ⇒ 与 `check_gates_fire.sh` 同型而方向相反:那边验【闸门会响】,这边验【闸门还在】。
# ⚠ 本条只要求它们**存在**,⛔ 不要求它们 FAIL ——
#   若增益结构真被改好,EXP-5c 应当 PASS。**「必须存在」与「必须 FAIL」是两件事。**
# ⛔ 登记住在**不带轮次号**的 `BASELINE_FAILS.txt`;读不到 ⇒ 退出码 2,
#   ⛔ 不得回退到内嵌的默认集合(那正好会让"换驱动件/换脚本"重新变成一条逃逸路径)。
print("\n" + "="*84)
print("META-1  登记在案的判定项是否还在(⛔ 它不能由被登记的那条检查自己回答)")
print("-"*84)
_reg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BASELINE_FAILS.txt")
_meta_rc = 0
if not os.path.exists(_reg_path):
    print(f"  ⛔ 找不到登记件 {_reg_path}")
    print(f"  ⛔ 拒绝在【没有登记件】的情况下报出任何合计 —— 那会让'换驱动件'重新成为逃逸路径。")
    sys.exit(2)
_registered = []
for _ln in open(_reg_path, encoding="utf-8"):
    _ln = _ln.strip()
    if not _ln or _ln.startswith("#") or _ln.startswith("|"):
        continue
    _registered.append(_ln.split("|")[0].strip())
print(f"  登记件: BASELINE_FAILS.txt(⛔ 不带轮次号)  登记 {len(_registered)} 条: {_registered}")
_missing = [t for t in _registered if t not in _decided]
if _missing:
    print(f"  ⛔⛔ [META-1 FAIL] 登记在案却**未出现在本次判定项里**: {_missing}")
    print(f"       ⇒ 它可能被删除、被改名、或被降级为 RETIRED(退役项不计入 _decided)。")
    print(f"       ⇒ ⛔ 退出码 2。删除登记须 lead + 独立 critic,见 BASELINE_FAILS.txt 规矩 ②。")
    _meta_rc = 2
else:
    print(f"  [PASS] META-1   全部登记项都出现在本次判定里"
          f"(⚠ 只验【存在】,⛔ 不验它是 PASS 还是 FAIL)")

print("\n" + "="*84)
print(f"合计: PASS={_pass}  FAIL={_fail}  RETIRED={_retired}(退役项不计入判定,原样留痕)   坏版本开关={BROKEN if BROKEN else '无'}")
print("="*84)
sys.exit(2 if _meta_rc == 2 else (0 if _fail == 0 else 1))
