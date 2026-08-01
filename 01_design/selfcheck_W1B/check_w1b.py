# W1-B NHS 设计桌面自验(关1,非门)· adaptive-dsp
# 定级声明:本脚本全部为 [L2/桌面数值](公式/估计器/模型层面的数学核对),
# **不构成任何检测率/抑制效果宣称**(效果判据须真实素材+闭环,见设计文档 §7)。
# 铁律七双轨:关键响应用 闭式|H| 与 np.freqz 两条独立路径互核。
import numpy as np

# v6(2026-08-01,adaptive-dsp 第 3 实例;critic-w1b-r2 复审 FAILED 后):
#   - 新增 **CHECK G**(豁免式合取门可达性审计,MAJOR-1 的机械核对);
#   - CHECK A2 增"报数用值=实跑最大值"行(m-4:文档曾报得比实测紧 5 倍);
#   - CHECK F-1 由"空场景"改为带伴随语音(m-5:原构造下三门必过=检查不可能失败);
#   - 新增同目录 `mem_sizeof.c`(§8.2 内存的**编译器实算第二轨**,MAJOR-3)。
# v5(2026-08-01):
#   - 契约引用全量切 **IF-v1.4 条款Cx**(旧注释的 "§7-x"/"v0.2 §7-4" 系合同独立成文件之前的
#     章节号,已作废;IF-v1.4 sha256[0:16]=ee35800c0be9844c,接收方回执 2026-08-01);
#   - 新增 CHECK A2(B-m3 真·异源第二轨,来源 = adaptive-dsp-2 的 bm3_second_track/,署名 -2);
#   - 新增 CHECK E(跳槽 × LS 时间轴,支撑 IF-v1.4 C4 使用注记:计数语义二分);
#   - 新增 CHECK F(候选表容量轴排挤,支撑 C4 "无绝对电平门" 的容量轴保留)。
# v4:新增 CHECK D2(快升入台签名);v3:按 B3 运行点重跑;
# v2 曾按已作废口径(2048/42.7ms)跑过一轮,合同版本竞态已由 lead 裁定,B3 为准。
# 运行点 = B3(V1 默认,IF-v1.4 C4):16kHz / N=1024 / 每通道 hop 16ms(75% 重叠)。
# B2=2048/42.7ms 为备选运行点,对决走 V-10 ROC,本脚本参数化即可复跑。
fs_sc = 16000.0   # 检测旁链采样率(IF-v1.4 C4:抽取 16k 固定)
N_FFT = 1024
HOP = 256         # 16ms/通道 hop(系统 500 FFT/s、8 通道错峰,IF-v1.4 C1)

print("=" * 72)
print("CHECK A: RBJ peaking(cut) 深度陷波 — 深度/带宽双轨核")
print("=" * 72)
# 设计文档 §4.1:深度可控陷波 = RBJ peaking EQ 负增益(RBJ Cookbook, W3C Note, W0 已核)
fs = 48000.0

def rbj_peaking(fs, f0, gain_db, bw_oct):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / fs
    # RBJ cookbook BW(oct) 公式: alpha = sin(w0)*sinh(ln2/2 * BW * w0/sin(w0))
    alpha = np.sin(w0) * np.sinh(np.log(2) / 2 * bw_oct * w0 / np.sin(w0))
    b = np.array([1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A])
    return b / a[0], a / a[0]

def mag_closed_form(b, a, f, fs):
    # 闭式 |H|(与 vendor NotchFilter.hpp getMagnitudeResponse 同法,独立于 freqz 的多项式求值)
    w = 2 * np.pi * f / fs
    b0, b1, b2 = b
    a1, a2 = a[1], a[2]
    num = (b0 * b0 + b1 * b1 + b2 * b2
           + 2 * (b0 * b1 + b1 * b2) * np.cos(w) + 2 * b0 * b2 * np.cos(2 * w))
    den = (1 + a1 * a1 + a2 * a2 + 2 * (a1 + a1 * a2) * np.cos(w) + 2 * a2 * np.cos(2 * w))
    return np.sqrt(num / den)

def mag_freqz(b, a, f, fs):
    w = 2 * np.pi * f / fs
    z = np.exp(1j * w)
    H = (b[0] + b[1] / z + b[2] / z**2) / (1 + a[1] / z + a[2] / z**2)
    return np.abs(H)

for f0, depth, bw in [(1000.0, -3.0, 0.1), (1000.0, -18.0, 0.1), (250.0, -3.0, 0.2),
                      (100.0, -12.0, 0.1), (6300.0, -6.0, 0.1)]:
    b, a = rbj_peaking(fs, f0, depth, bw)
    m_cf = 20 * np.log10(mag_closed_form(b, a, f0, fs))
    m_fz = 20 * np.log10(mag_freqz(b, a, f0, fs))
    # 半深点带宽数值核算(C2 措辞:本脚本全部为 L2 桌面数值,不用"实测"一词)
    fr = np.geomspace(f0 / 2, f0 * 2, 20001)
    mag = 20 * np.log10(mag_freqz(b, a, fr, fs))
    half = depth / 2
    idx = np.where(mag <= half)[0]
    bw_meas_oct = np.log2(fr[idx[-1]] / fr[idx[0]]) if len(idx) > 1 else float("nan")
    stable = np.all(np.abs(np.roots([1, a[1], a[2]])) < 1.0)
    print(f"f0={f0:7.1f}Hz depth={depth:+5.1f}dB bw_set={bw:.2f}oct | "
          f"closed-form@f0={m_cf:+7.3f}dB freqz@f0={m_fz:+7.3f}dB "
          f"两轨差={abs(m_cf-m_fz):.2e}dB | 半深点带宽={bw_meas_oct:.3f}oct | 稳定={stable}")
print("判定:两轨差应 <1e-4 dB(低频 f0/fs 小时 float64 调理数变差,100Hz 例约 1e-5,"
      "无工程影响但如实记录;这也是文档 §4.4 低频定点精度警示的浮点侧影);"
      "@f0 深度应=设定深度;半深点带宽应≈设定 BW(RBJ 定义即半增益点)")

print()
print("=" * 72)
print("CHECK A2: 陷波系数第二轨 — RBJ(sin 映射) vs Välimäki-Reiss 2016(tan 预畸变)")
print("=" * 72)
# B-m3 闭合件。**来源:adaptive-dsp-2**(`01_design/incident_20260801/bm3_second_track/`,
# 2026-08-01 跑通),本轮集成为 CHECK A2 —— v1.0 曾把 pareq 第二轨写成"已做"实为虚账,
# 处置 = **补跑关闭**(非删宣称),署名保留给 -2(DEC-0011 归因更正的落实)。
# 轨1 = RBJ Cookbook peaking(负增益):alpha = sin(w0)*sinh(ln2/2*BW*w0/sin(w0))
# 轨2 = Orfanidis 系 / Välimäki & Reiss 2016 Table 7.2:beta = sqrt((GB^2-1)/(G^2-GB^2))*tan(dw/2)
# 两轨=不同推导、不同带宽映射 ⇒ 系数本就不同;互核点 = 设计规格点(@f0 深度、半深带宽、极点)。
def vr_pareq(fs, f0, gain_db, bw_oct):
    G = 10.0 ** (gain_db / 20.0)
    GB = 10.0 ** (gain_db / 40.0)          # sqrt(G):半增益 dB 点(与 RBJ 同一 BW 语义)
    w0 = 2 * np.pi * f0 / fs
    w1 = 2 * np.pi * f0 * 2 ** (-bw_oct / 2) / fs
    w2 = 2 * np.pi * f0 * 2 ** (+bw_oct / 2) / fs
    beta = np.sqrt((GB * GB - 1.0) / (G * G - GB * GB)) * np.tan((w2 - w1) / 2)
    b = np.array([(1 + G * beta), -2 * np.cos(w0), (1 - G * beta)]) / (1 + beta)
    a = np.array([1.0, -2 * np.cos(w0) / (1 + beta), (1 - beta) / (1 + beta)])
    return b, a

def half_depth_bw_oct(b, a, f0, depth, fs):
    fr = np.geomspace(f0 / 2, f0 * 2, 20001)
    mag = 20 * np.log10(mag_freqz(b, a, fr, fs))
    idx = np.where(mag <= depth / 2)[0]
    return np.log2(fr[idx[-1]] / fr[idx[0]]) if len(idx) > 1 else float("nan")

print("case                      | @f0: RBJ      VR       互差    | 半深BW(oct): RBJ    VR     互差 | VR极点稳")
_a2_dmax, _a2_bwmax = 0.0, 0.0
for f0, depth, bw in [(1000.0, -3.0, 0.1), (1000.0, -18.0, 0.1), (250.0, -3.0, 0.2),
                      (100.0, -12.0, 0.1), (6300.0, -6.0, 0.1)]:
    b1, a1 = rbj_peaking(fs, f0, depth, bw)
    b2, a2 = vr_pareq(fs, f0, depth, bw)
    m1 = 20 * np.log10(mag_freqz(b1, a1, f0, fs))
    m2 = 20 * np.log10(mag_freqz(b2, a2, f0, fs))
    bw1, bw2 = half_depth_bw_oct(b1, a1, f0, depth, fs), half_depth_bw_oct(b2, a2, f0, depth, fs)
    stable = np.all(np.abs(np.roots(a2)) < 1.0)
    _a2_dmax = max(_a2_dmax, abs(m1 - m2)); _a2_bwmax = max(_a2_bwmax, abs(bw1 - bw2))
    print(f"f0={f0:6.0f} {depth:+5.1f}dB {bw:.2f}oct | {m1:+8.4f} {m2:+8.4f} {abs(m1-m2):.2e} | "
          f"{bw1:6.4f} {bw2:6.4f} {abs(bw1-bw2):6.4f} | {stable}")
# m-4:文档须按**实跑最大值**报,不得报得比实测更紧(方向=高估一致性)
print(f"** 报数用值(m-4):@f0 两轨互差 **最大** = {_a2_dmax:.2e} dB;半深带宽两轨互差最大 = {_a2_bwmax:.1e} oct")
print("判定:①@f0 两轨深度都=设定值(互差 <1e-3dB);②半深带宽各自≈设定 BW,两轨互差=sin vs tan")
print("      映射的约定差(<0.01oct,如实记录);③VR 轨极点全稳。任一不满足 → FAIL。")

print()
print("=" * 72)
print("CHECK B: Quinn 第二估计器 bin 内插精度(1024pt Hann @16kHz, bin=15.625Hz, B3)")
print("=" * 72)
def quinn2(X, k):
    # Quinn's Second Estimator(与 vendor GyroFFT.cpp EstimatePeakFrequencyBin 同式,float 重写)
    def tau(x):
        return 0.25 * np.log(3 * x * x + 6 * x + 1) - np.sqrt(6) / 24 * np.log(
            (x + 1 - np.sqrt(2 / 3)) / (x + 1 + np.sqrt(2 / 3)))
    ap = (X[k + 1].real * X[k].real + X[k + 1].imag * X[k].imag) / (abs(X[k]) ** 2)
    dp = -ap / (1 - ap)
    am = (X[k - 1].real * X[k].real + X[k - 1].imag * X[k].imag) / (abs(X[k]) ** 2)
    dm = am / (1 - am)
    d = (dp + dm) / 2 + tau(dp * dp) - tau(dm * dm)
    return k + d

rng = np.random.default_rng(1234)
win = np.hanning(N_FFT)
for snr_db in [30.0, 10.0]:
    errs = []
    for _ in range(200):
        f_true = rng.uniform(200, 7000)
        n = np.arange(N_FFT)
        sig = np.sin(2 * np.pi * f_true / fs_sc * n + rng.uniform(0, 2 * np.pi))
        noise = rng.normal(0, 10 ** (-snr_db / 20) / np.sqrt(2), N_FFT)
        X = np.fft.rfft((sig + noise) * win)
        k = np.argmax(np.abs(X[2:N_FFT // 2 - 2])) + 2
        f_est = quinn2(X, k) * fs_sc / N_FFT
        errs.append(abs(f_est - f_true))
    errs = np.array(errs)
    print(f"SNR={snr_db:4.0f}dB: |f_err| median={np.median(errs):6.3f}Hz "
          f"p95={np.percentile(errs, 95):6.3f}Hz max={errs.max():6.3f}Hz (200 trials)")
print("判定:合同精度语义(IF-v1.4 C7)= p95|Δf| ≤ BW/4(恒带宽下限见 W1-A §5 字典 → 3.75Hz);"
      "FFT 供给归架构侧,本检查是该语义可实现性的独立旁证(p95 应 ≤3.75Hz)")

print()
print("=" * 72)
print("CHECK C: 环路增长物理模型 — 闭环仿真斜率 vs 理论 20·log10(g)/τ")
print("=" * 72)
# 模型:y[n] = g·y[n-D] + e[n](环路延迟 D,环路增益 g>1 → 指数增长,dB 域线性)
# 用脉冲种子(确定性)激励:e = δ[0],此后环路自持增长,消除噪声实现的随机抖动;
# 拟合段取轨迹尾部线性区(终值-40dB → 终值-3dB),避开起始瞬态。
for g, D_ms, T_sim in [(1.05, 10.0, 2.0), (1.02, 25.0, 8.0)]:
    D = int(D_ms / 1000 * fs_sc)
    theory = 20 * np.log10(g) / (D_ms / 1000)  # dB/s
    Nsim = int(T_sim * fs_sc)
    y = np.zeros(Nsim)
    y[0] = 1e-6
    for n in range(D, Nsim):
        y[n] = g * y[n - D]
    # 用设计的旁链参数(1024 Hann, hop 256)提 STFT 峰值轨迹,LS 拟合 dB 斜率
    hops, mags = [], []
    for start in range(0, Nsim - N_FFT, HOP):
        X = np.abs(np.fft.rfft(y[start:start + N_FFT] * win))
        mags.append(20 * np.log10(X.max() + 1e-30))
        hops.append(start / fs_sc)
    hops, mags = np.array(hops), np.array(mags)
    seg = (mags > mags[-1] - 40) & (mags < mags[-1] - 3)
    slope = np.polyfit(hops[seg], mags[seg], 1)[0]
    print(f"g={g} τ={D_ms}ms: 理论={theory:8.2f} dB/s  STFT轨迹拟合={slope:8.2f} dB/s  "
          f"偏差={abs(slope-theory)/theory*100:5.1f}%  (拟合点数={seg.sum()})")
print("判定:偏差应 <10% → 证明本设计的 STFT 轨迹提取管线(1024 Hann/hop 256/峰值/LS 拟合)")
print("      对指数增长信号**无斜率偏置**(IMSD 测量链可信);『dB 域线性增长』模型本身")
print("      是反馈环路常识 [L3],不由本检查证明(B-m5 结论域限定,文档 §2.1/§2.5)")

print()
print("=" * 72)
print("CHECK D: IMSD 判别边界自洽性(合成轨迹,阈值初值 [L4/待标定] 的桌面预检)")
print("=" * 72)
# 规则(文档§2.2,B3 hop=16ms):W=8 hop(128ms)窗上 LS 斜率 b、残差 RMS s、总升幅 dL,
# 判 GROWTH ⟺ β_min≤b≤β_max ∧ s≤s_max ∧ dL≥ΔL_min
# 阈值以 dB/s 定义、换算到 16ms/hop:β_min=60dB/s→0.96, β_max=750dB/s→12 [dB/hop]
W = 8
BETA_MIN, BETA_MAX, S_MAX, DL_MIN = 0.96, 12.0, 1.5, 6.0

def imsd(traj):
    x = np.arange(len(traj))
    b, c = np.polyfit(x, traj, 1)
    s = np.sqrt(np.mean((traj - (b * x + c)) ** 2))
    dL = traj[-1] - traj[0]
    return b, s, dL, (BETA_MIN <= b <= BETA_MAX and s <= S_MAX and dL >= DL_MIN)

cases = {}
# a) 中速啸叫:130dB/s ≈ 2.08dB/hop@16ms 线性增长 + 0.5dB shimmer(应 GROWTH)
cases["howl_130dB/s"] = 2.08 * np.arange(W) + rng.normal(0, 0.5, W)
# a2) 慢啸叫:70dB/s ≈ 1.12dB/hop(应 GROWTH;注意对 β_min=0.96 与 ΔL_min=6 均为边际通过,
#     70dB/s 附近即本判据的设计灵敏度下缘,更慢者交 PERSIST 路——如实记录)
cases["howl_70dB/s"] = 1.12 * np.arange(W) + rng.normal(0, 0.3, W)
# b) 稳态纯音/工频(应 NOT — 由持续路 B 另行处理)
cases["steady_tone"] = 60.0 + rng.normal(0, 0.5, W)
# c) 元音:128ms 窗见起音+平台前段(音节周期 125-250ms ≥ 窗长)(应 NOT:残差大)
vowel = np.concatenate([[40, 55], 60 + np.cumsum(rng.normal(0, 1.2, W - 2))])
cases["vowel_attack+plateau"] = vowel
# d) 渐强音乐(相对量:PAPR 轨迹——峰与谱底同升 → 相对斜率≈0)(应 NOT)
cases["crescendo_relative"] = 20.0 + rng.normal(0, 0.5, W)  # PAPR 不变
# e) 起音后即饱和的快啸(前 2 hop 冲顶):IMSD 窗内非线性 → 由 PANIC 路兜(标注)
cases["fast_howl_saturating"] = np.concatenate([[30, 60], 62 + rng.normal(0, 0.5, W - 2)])
for name, traj in cases.items():
    b, s, dL, hit = imsd(np.asarray(traj, dtype=float))
    print(f"{name:26s} b={b:+6.2f}dB/hop s={s:5.2f}dB dL={dL:+6.1f}dB -> "
          f"{'GROWTH' if hit else 'not-growth'}")
print("判定:a/a2 应 GROWTH;b/c/d 应 not;e 应 not(e 的分类路覆盖见 CHECK D2 与文档 §3.2/§3.5-#11)")

print()
print("=" * 72)
print("CHECK D2: 快升入台签名检测器(B-F1 修法①的可测性预检,参数 [L4/待标定])")
print("=" * 72)
# 签名定义(文档 §3.2 v1.1):任意 ≤N_RISE hop 内升幅 ≥R_RISE,其后 ≥MIN_PLAT hop
# 平台(std ≤ S_PLAT)。作用:使 PHPR 削波豁免在"IMSD 结构性不中"的快饱和场景可达
# (B-F1 修复);它**不承担**元音区分——区分靠 PHPR 因果时序(谐波出现晚于增长起点),
# 该时序超出本标量轨迹测试床,归 §7.3 ROC(合成削波啸叫素材)。
R_RISE, N_RISE, S_PLAT, MIN_PLAT = 18.0, 2, 2.0, 3

def fast_rise_plateau(traj):
    for i in range(len(traj) - MIN_PLAT):
        for j in range(i + 1, min(i + N_RISE, len(traj) - MIN_PLAT) + 1):
            if traj[j] - traj[i] >= R_RISE:
                plat = traj[j:]
                if len(plat) >= MIN_PLAT and np.std(plat) <= S_PLAT:
                    return True
    return False

for name, traj in cases.items():
    fired = fast_rise_plateau(np.asarray(traj, dtype=float))
    print(f"{name:26s} -> fast_rise_plateau = {fired}")
print("判定:fast_howl_saturating 必须 True(否则 B-F1 修法失效=FAIL);")
print("      稳态/渐强/慢啸应 False;元音起音若 True 属预期内(签名不区分元音,")
print("      豁免仍被因果时序条件拦住——该拦截须 ROC 素材验证,此处如实暴露依赖)")
print()
print("=" * 72)
print("CHECK E: 跳槽 × LS 时间轴(IF-v1.4 C4 slot_seq 使用注记的数值坐实)")
print("=" * 72)
# IF-v1.4 C4 原文:"接收方全部连续性/老化/驻留计数按已交付分析槽计"。
# 本检查坐实:该规则对**存在性计数**正确,对**速率估计**(IMSD 的 b/s)有害——
# IMSD 的 LS 拟合 x 轴必须用 slot_seq 差值(真实时间轴),否则跳槽窗被压缩,
# 斜率与线性度残差同时失真。**双向都错**(既漏检真啸叫,又把慢升虚警成 GROWTH)。
def imsd_x(traj, x):
    b, c = np.polyfit(x, traj, 1)
    s = np.sqrt(np.mean((traj - (b * x + c)) ** 2))
    dP = traj[-1] - traj[0]
    return b, s, dP, (BETA_MIN <= b <= BETA_MAX and s <= S_MAX and dP >= DL_MIN)

HOP_S = 0.016
for nm, seq, rate in [
        ("真啸叫 250dB/s,窗中跳 6 槽", np.array([0, 1, 2, 3, 10, 11, 12, 13]), 250.0),
        ("真啸叫 400dB/s,窗中跳 4 槽", np.array([0, 1, 2, 3, 4, 9, 10, 11]), 400.0),
        ("慢升 40dB/s(设计上应交PERSIST),跳 8 槽", np.array([0, 1, 2, 3, 12, 13, 14, 15]), 40.0),
        ("无跳槽对照 250dB/s", np.arange(8), 250.0)]:
    traj = rate * HOP_S * seq.astype(float)
    bn, sn, dn, hn = imsd_x(traj, np.arange(len(seq), dtype=float))   # 朴素:已交付槽序当 x
    bt, st, dt, ht = imsd_x(traj, seq.astype(float))                  # 正确:x = Δslot_seq
    print(f"{nm}")
    print(f"   朴素 x=0..W-1: b={bn:+6.2f}dB/hop({bn/HOP_S:7.1f}dB/s) s={sn:5.2f} -> "
          f"{'GROWTH' if hn else 'not-growth'}")
    print(f"   正确 x=Δseq  : b={bt:+6.2f}dB/hop({bt/HOP_S:7.1f}dB/s) s={st:5.2f} -> "
          f"{'GROWTH' if ht else 'not-growth'}")
print("判定:前两例朴素列必须 not-growth 而正确列 GROWTH(=朴素口径漏检真啸叫);")
print("      第三例朴素列必须 GROWTH 而正确列 not(=朴素口径虚警)。任一同向 → 本注记失去依据。")
print("      配套设计规则(文档 §2.2):窗内空号 > W_used/2 时本槽不出 IMSD 判定,交 PERSIST 路。")

print()
print("=" * 72)
print("CHECK F: 钉住啸叫的前置门可达性(容量轴 + PAPR 全带统计;D1 扫的数值坐实)")
print("=" * 72)
# 两个子场景,**结论相反**,故必须并列跑——只跑其一都会得出错误的一般结论:
#  F-1 宽带限幅钉住的稳态平衡(语音间歇):啸叫是本通道 tap 上的主导分量 ⇒ 门全可达;
#  F-2 频段选择性钉住(8段动态PEQ,IF-v1.4 C10/C11 作用域内)+ 带外强语音:
#      啸叫未被抑制,却要与几十条语音谐波争 ≤16 个候选名额,且 PAPR 是**全带**统计。
# 度量约定(v1.2 勘正,见文档 §1.2):PAPR/PNPR 均取 **20·log10(幅度比)= 常规 dB**。
#  ⚠ PX4 GyroFFT.cpp:514 对同一幅度比取 10·log10(= 本文数值的一半),其 MIN_SNR/参数
#    **不可直接搬**;本行是本项目第三次同族二义(每侧/全宽、半/满 LSB、半/常规 dB)。
NB, DF = 512, fs_sc / N_FFT          # 512 bin @ 15.625Hz(B3,IF-v1.4 C4)
T_PAPR, T_PNPR = 15.0, 8.0           # 候选门初值 [L4/待标定](常规 dB 约定)

def build_spec(speech_peak_db):
    # m-5 修正:F-1 不再用"空场景"(仅底噪+一条线)——那种构造下三门必过,检查不可能失败。
    # 现按钉住平衡的物理约束给 F-1 配真实伴随内容:啸叫顶到母线天花板 ⇒ 本通道其余内容
    # 必在其下,故语音峰取 啸叫−10dB(仍是有利条件,但**可能失败**,不再是恒真构造)。
    s = -95.0 + rng.normal(0, 1.5, NB)                       # 本底
    if speech_peak_db is not None:
        for h in range(1, 41):                               # 语音谐波族(-6dB/oct 滚降)
            fh = 140.0 * h
            if fh < NB * DF:
                k = int(round(fh / DF))
                s[k] = max(s[k], speech_peak_db - 6.0 * np.log2(h) + rng.normal(0, 2.0))
                s[k - 1] = max(s[k - 1], s[k] - 12); s[k + 1] = max(s[k + 1], s[k] - 12)
    k_h = int(round(2500.0 / DF))
    s[k_h] = -56.0                                           # 钉住啸叫:单线,tap 电平
    return 10 ** (s / 20.0), k_h

def papr_db(M, k):   # 峰 vs 全带均值(幅度比 → 常规 dB);原料 = C4 的 P_peak/全带均值
    return 20 * np.log10((NB - 1) * M[k] / (np.sum(M) - M[k]))

def pnpr_db(M, k):   # 峰 vs 邻域均值;邻域定义以 IF-v1.4 C5 为准(此处按其形态构造)
    f = k * DF
    kk = int(round(max(187.0, f * (2 ** (1 / 3) - 1)) / DF))
    idx = [j for j in range(max(0, k - kk), min(NB, k + kk + 1)) if abs(j - k) > 3]
    return 20 * np.log10(M[k] / np.mean(M[idx]))

for tag, spk in [("F-1 宽带钉住稳态(伴随语音在啸叫下 10dB,由钉住平衡物理定)", -66.0),
                 ("F-2 频段选择性钉住 + 带外强语音(语音峰 −30dB)", -30.0)]:
    M, k_h = build_spec(spk)
    loc = [k for k in range(2, NB - 2) if M[k] > M[k - 1] and M[k] >= M[k + 1]]
    by_mag = sorted(loc, key=lambda k: -M[k])
    by_papr = sorted(loc, key=lambda k: -papr_db(M, k))
    pa, pn = papr_db(M, k_h), pnpr_db(M, k_h)
    line16 = 20 * np.log10(M[by_mag[min(15, len(by_mag) - 1)]])
    print(f"{tag}")
    print(f"   局部峰数={len(loc):3d} | 幅度 top-16 含啸叫线={k_h in by_mag[:16]!s:5s} "
          f"(第16名={line16:6.1f}dBFS = 该槽的**有效**准入线) | PAPR top-16 含={k_h in by_papr[:16]}")
    print(f"   已知 bin 直读主谱:PAPR={pa:+6.1f}dB(门{T_PAPR:.0f}) {'✓' if pa>=T_PAPR else '✗'}"
          f"   PNPR={pn:+6.1f}dB(门{T_PNPR:.0f}) {'✓' if pn>=T_PNPR else '✗'}")
print("判定与结论域(如实,含一条推翻我方事前预期的结果):")
print(" ① F-1(伴随语音在啸叫下 10dB,**非空场景**)三门全过 ⇒ 主场景前置门可达,不得夸大为普遍洞。")
print("    ⚠ m-5 勘正:F-1 仍是**有利条件下的存在性演示**;承重的是同段 [L3] 物理论证(啸叫顶到")
print("      母线天花板 ⇒ 它在 tap 上亦为主导),**本检查是该论证的旁证,不是『证明』**;")
print(" ② F-2 幅度 top-16 **排除**啸叫线 ⇒ 容量轴的有效准入线随房间变吵而抬高(回执 §3 保留成立);")
print(" ③ F-2 的 **PAPR(全带统计)亦不过门** —— 本项事前预期是'PAPR 排序能救回来',**被本检查证伪**:")
print("    全带均值被带外语音抬高,弱峰的 PAPR 随之塌陷 ⇒ PAPR 排序同样排除它。")
print("    ⇒ 掩蔽下**唯一存活的窄带证据是 PNPR(局部统计)**,这是文档 §1.2/§3.2 GR 放宽路径")
print("      改以 PNPR 承重、并对 IF-v1.4 C11-② 的 'PAPR ≥ T_papr_high' 提点单的依据。")
print(" 阈值全为初值 [L4/待标定];本检查是构造谱上的**存在性**演示,不构成检出率/排挤概率结论。")

print()
print("声明:CHECK D/D2/E/F 仅证明规则在构造轨迹/构造谱上自洽,不构成误触发率/检出率结论;")
print("真判别力须真实素材(会议录音/乐音/长笛)+ 闭环 RIR 仿真,见 §7 与素材采集工单。")

print()
print("=" * 72)
print("CHECK G: 豁免式**合取门**可达性审计(MAJOR-1 修法的机械核对)")
print("=" * 72)
# 立法理由(critic-w1b-r2 MAJOR-1):v1.2 的可达性表按"**哪条臂能命中**"填,
# 而规则本体是**三重合取** `族内最大 ∧ 因果时序 ∧ (臂1∨臂2∨臂3)`。
# 合取门为假时,臂命中也不产生豁免。本检查把规则本体编码,对每个场景**逐合取项**求值,
# 再与文档表的宣称逐格比对 —— 即"用检查别人的尺子量自己"。
#
# 因果时序定义:causal_ok ⟺ (t_veto_start − t_onset) ≥ CAUSAL_MIN 槽
CAUSAL_MIN = 2

# 场景:(名, t_onset, t_veto_start, family_max, arm1, arm2, arm3, dom_v12, dom_v13,
#        是否重生轨, 继承来的 causal_ok, v1.2 文档表宣称是否"豁免可达")
SC = [
 ("(a) 慢升削波啸叫",            100, 106, True,  True,  False, True,  True,  True,  False, None, True),
 ("(a) 快升入台",                100, 103, True,  False, True,  True,  True,  True,  False, None, True),
 ("(a') 臂间隙(仅臂3)",         100, 104, True,  False, False, True,  True,  True,  False, None, True),
 ("(b1) NOM 开门接入已振铃环路",  200, 200, True,  False, False, True,  True,  True,  False, None, True),
 ("(b4) 中断重生·v1.2 影子",      300, 250, True,  False, False, True,  True,  True,  True,  None, True),
 ("(b4) 中断重生·完全不继承",     300, 300, True,  False, False, True,  True,  True,  True,  None, True),
 ("(b5) 冷启动接入已振铃环路",      0,   0, True,  False, False, True,  True,  True,  False, None, True),
 ("(c1) 讲话后重生(保鲜期内)",   400, 350, True,  False, False, True,  True,  True,  True,  True, True),
 ("(c2) 掩蔽:2f 与语音谐波重合",  100, 106, False, True,  False, True,  False, True,  False, None, True),
]

def eval_v12(t_on, t_veto, fam, a1, a2, a3, dom12, reborn, inh):
    causal = (t_veto - t_on) >= CAUSAL_MIN       # 重生轨:t_on=重生时刻,t_veto=继承的旧值 ⇒ 负
    arm = a1 or a2 or (a3 and dom12)
    return fam, causal, arm, (fam and causal and arm)

def eval_v13(t_on, t_veto, fam, a1, a2, a3, dom13, reborn, inh):
    # v1.3 修法:①重生轨的因果时序按**继承的锚**求值(继承 causal_ok 布尔 + t_onset),
    #            不用重生时刻重算;②臂3 谓词 dom 改按 PNPR(局部统计)定义,掩蔽下不塌陷。
    if reborn and inh is not None:
        causal = inh
    else:
        causal = (t_veto - t_on) >= CAUSAL_MIN
    arm = a1 or a2 or (a3 and dom13)
    return fam, causal, arm, (fam and causal and arm)

print(f"{'场景':30s} | v1.2: 族最大 因果 臂 => 豁免 | v1.3: 族最大 因果 臂 => 豁免 | v1.2表宣称 | 一致?")
mismatch = 0
for (nm, t_on, t_veto, fam, a1, a2, a3, d12, d13, reborn, inh, claim) in SC:
    f2, c2, m2, e2 = eval_v12(t_on, t_veto, fam, a1, a2, a3, d12, reborn, inh)
    f3, c3, m3, e3 = eval_v13(t_on, t_veto, fam, a1, a2, a3, d13, reborn, inh)
    ok = (e2 == claim)
    if not ok:
        mismatch += 1
    B = lambda x: "T" if x else "F"
    print(f"{nm:30s} |   {B(f2)}     {B(c2)}   {B(m2)} =>   {B(e2)}   |   {B(f3)}     {B(c3)}   {B(m3)} =>   {B(e3)}   |     {B(claim)}      | {'✓' if ok else '**不符**'}")

print()
print(f"v1.2 规则求值与 v1.2 可达性表宣称**不符的格数 = {mismatch}/{len(SC)}**")
print("判定与结论(本检查的存在意义 = 机械暴露下面这条,而不是确认设计正确):")
print(" ① v1.2 的可达性表在 (b1)/(b4)/(b5)/(c1)/(c2) 上宣称豁免可达,而**规则本体求值为 False**")
print("    —— 因果时序是三臂**共用**的合取门,臂3 命中不能绕过它。文档表按'哪条臂命中'填,")
print("    这正是 B-F1 病型第二次复现(用目标场景里为假的前提去关/开一条路)。")
print(" ② (b4) v1.2 影子只继承 t_veto_start 不继承 t_onset ⇒ 重生轨 t_veto < t_onset ⇒ 因果时序")
print("    **结构性为假**:救 case (b) 的机制反而把被救的轨焊死(继承比不继承更糟)。")
print(" ③ v1.3 修法后:重生/继承类((b4)继承态、(c1))恢复可达;**(b1)/(b5) 真·诞生即平台**")
print("    **仍不可达 —— 这是真盲区,v1.3 按此改写盲区公式,不再宣称'有臂3 即可达'**。")
print(" ④ (c2) 族内最大在掩蔽下可为假(2f 与语音谐波重合)⇒ 另一条独立失效路径,已入 D1 表。")
print(" 本检查为规则层求值,不含物理量;场景的可能性判断见文档 §3.2 与 §10.3。")
