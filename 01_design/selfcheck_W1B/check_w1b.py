# W1-B NHS 设计桌面自验(关1,非门)· adaptive-dsp 2026-07-31
# 定级声明:本脚本全部为 [L2/桌面数值](公式/估计器/模型层面的数学核对),
# **不构成任何检测率/抑制效果宣称**(效果判据须真实素材+闭环,见设计文档 §7)。
# 铁律七双轨:关键响应用 闭式|H| 与 np.freqz 两条独立路径互核。
import numpy as np

# v3(2026-07-31):按 W1-A v0.2 合同 §7-4(critic-w1 锁版 sha256 bfc9f27d…3cab94858)
# 运行点 = B3(V1 默认):16kHz / N=1024 / 每通道 hop 16ms(75% 重叠)。
# (v2 曾按 v0.1 口径 2048/42.7ms 跑过一轮,合同版本竞态已由 lead 裁定,B3 为准;
#  B2=2048/42.7ms 为备选运行点,对决走 V-10 ROC,本脚本参数化即可复跑。)
fs_sc = 16000.0   # 检测旁链采样率(合同:抽取 16k 固定)
N_FFT = 1024
HOP = 256         # 16ms/通道 hop(系统 500 FFT/s、8 通道错峰,合同 §7-1)

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
print("判定:合同精度语义(v0.2 §7-6)= p95|Δf| ≤ BW/4(恒带宽下限 15Hz → 3.75Hz);"
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
print("判定:偏差应 <10% → 支撑 IMSD 的『dB 域线性增长』物理模型(文档§2.2)")

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
print("判定:a/a2 应 GROWTH;b/c/d 应 not;e 应 not(设计上由 PANIC 电平路兜住,见§3.2)")
print()
print("声明:CHECK D 仅证明规则在构造轨迹上自洽,不构成误触发率/检出率结论;")
print("真判别力须真实素材(会议录音/乐音/长笛)+ 闭环 RIR 仿真,见 §7 与素材采集工单。")
