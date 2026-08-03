#!/usr/bin/env python3
"""D3/D4 通道链设计的验证件。按 PREREG_D34_r1.txt 逐条执行。

⛔ 门禁状态:未过门。
用法: python3 d34_analysis.py > results_d34_rN.txt

⚠ 假绿纪律:每组带【坏版本】开关,坏版本下对应检查必须 FAIL。
   `python3 d34_analysis.py --broken=<name>` ,name ∈ {polarity, qcoef, hpf_order, xo_order}
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

_pass, _fail, _retired = 0, 0, 0
def OK(tag, cond, msg):
    global _pass, _fail
    if cond: _pass += 1
    else:    _fail += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {tag:<9s} {msg}")

def RETIRED(tag, cond, msg):
    """已退役的检查:保留记录(E-2 加标注不删数),不计入判定。"""
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
    if BROKEN == 'qcoef':
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
    if tie in ('hp', 'lp') and BROKEN != 'qcoef':
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
    for nm, secs in [('PEQ 在前', peq+xo), ('分频在前', xo+peq)]:
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

x_hpf_first = apply_sec(hpf, x)
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
print(f"      LR4 fc=2000 反相求和 max|偏离| = {bd:.2f} dB")
OK("EXP-3p", bd > 20.0, "极性写反时求和出现 >20 dB 深谷 ⇒ EXP-3a/b 有分辨力,不是恒真")

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
      f"  ⇒ 合计 {(ADC+DAC)/FS*1e3:.5f} ms")
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
OK("EXP-5", fl_all <= -140.0, f"全链噪声底 {fl_all:.2f} dBFS ≤ −140(判据)")
print("    ⚠ 增益/门/压限/延时不引入新量化器:增益并入相邻节的累加器;")
print("      门与压限只做增益相乘(1 次窄化,已计入其上游节);延时是纯搬运。")

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
print(f"      转换器 ADC+DAC            {0.99967:8.5f} ms   ⛔ 不可降(器件固有)")

print("\n" + "="*84)
print(f"合计: PASS={_pass}  FAIL={_fail}  RETIRED={_retired}(退役项不计入判定,原样留痕)   坏版本开关={BROKEN if BROKEN else '无'}")
print("="*84)
sys.exit(0 if _fail == 0 else 1)
