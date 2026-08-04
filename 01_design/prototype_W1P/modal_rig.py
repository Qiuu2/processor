"""`modal_rig` · **非统计 plant**(矩形房间模态叠加)—— 与 `clrig.make_F`(噪声 RIR)对照用。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r88.txt。

⚠⚠ **为什么需要它(一句话)**:现有台架 `clrig.make_F` **按构造就是一个统计模型**
  (文档明写:Rayleigh 幅度 / dB 域 σ≈5.57 / 峰间距≈4/T60)⇒ 在它上面数低频临界点
  只会复现它自己的假设 ⇒ **循环**。本件提供一个**不含该假设**的 plant,
  用途**不是**"更像真实房间",而是回答:
     **【若低频段是可辨模态而非统计场,NHS 的行为会不会不同】**
  ⇒ 若两种场下 NHS 行为无可判差异 ⇒ Schroeder 常数之争**不改变任何决定**(B-1 形式)。

构型:刚性矩形房间本征频率(解析,非随机)
    f_{nx,ny,nz} = (c/2)·√((nx/Lx)² + (ny/Ly)² + (nz/Lz)²)
    模态振型     Ψ = Π cos(n·π·x/L);幅度 a_k = Ψ_k(源)·Ψ_k(收) ⇒ **由几何与位置决定,不是随机抽的**
    h_low(t) = Σ_k a_k · e^{−t/τ} · cos(2π f_k t),  τ = T60/6.908(与 clrig 同式)

⚠⚠ **混合是一个已声明的取舍,不是隐藏假设**:
  全带模态合成不可行(V=60 m³ 到 8 kHz 约 **3.2×10⁶** 个模态)⇒ 本件只在 `f_cross` **以下**
  做模态合成,以上沿用噪声尾。⇒ **低频段(争议所在)是非统计的,高频段两个 plant 同构** ——
  这恰好把变量隔离在争议频段上,但**⛔ 不得把本件称作"真实房间模型"**。

⚠ 与 `clrig.make_F` 的接口**逐字同形**:返回 `(h, D)`,h 已含直达延迟、已归一化单位能量。
"""
import numpy as np

C_SOUND = 343.0
FS = 48000


def mode_freqs(Lx, Ly, Lz, f_max, c=C_SOUND):
    """枚举 f ≤ f_max 的全部 (nx,ny,nz) 本征频率。⛔ 不含 (0,0,0)。"""
    nx_max = int(2 * f_max * Lx / c) + 1
    ny_max = int(2 * f_max * Ly / c) + 1
    nz_max = int(2 * f_max * Lz / c) + 1
    nx, ny, nz = np.meshgrid(np.arange(nx_max + 1), np.arange(ny_max + 1),
                             np.arange(nz_max + 1), indexing='ij')
    nx, ny, nz = nx.ravel(), ny.ravel(), nz.ravel()
    f = (c / 2) * np.sqrt((nx / Lx) ** 2 + (ny / Ly) ** 2 + (nz / Lz) ** 2)
    m = (f > 0) & (f <= f_max)
    return nx[m], ny[m], nz[m], f[m]


def make_F_modal(T60=0.5, prop_delay_ms=8.0, seed=0, fs=FS,
                 dur_mult=2.0, L=(5.0, 4.0, 3.0), f_cross=600.0, c=C_SOUND):
    """返回 (h, D),与 `clrig.make_F` 同形。
    `seed` 只决定**源/收位置**(几何仍是解析的)⇒ 同 seed 可复现。"""
    Lx, Ly, Lz = L
    tau = T60 / 6.908
    D = int(round(prop_delay_ms * 1e-3 * fs))
    n = int(dur_mult * T60 * fs)
    t = np.arange(n) / fs
    env = np.exp(-t / tau)

    rng = np.random.default_rng(seed)
    # 源/收位置:避开墙面与正中(正中会使大量模态振型为 0 ⇒ 人为抹掉模态)
    rs = np.array([rng.uniform(0.15, 0.85) * Lx, rng.uniform(0.15, 0.85) * Ly,
                   rng.uniform(0.15, 0.85) * Lz])
    rm = np.array([rng.uniform(0.15, 0.85) * Lx, rng.uniform(0.15, 0.85) * Ly,
                   rng.uniform(0.15, 0.85) * Lz])

    nx, ny, nz, fk = mode_freqs(Lx, Ly, Lz, f_cross, c)
    psi_s = (np.cos(nx * np.pi * rs[0] / Lx) * np.cos(ny * np.pi * rs[1] / Ly)
             * np.cos(nz * np.pi * rs[2] / Lz))
    psi_m = (np.cos(nx * np.pi * rm[0] / Lx) * np.cos(ny * np.pi * rm[1] / Ly)
             * np.cos(nz * np.pi * rm[2] / Lz))
    a = psi_s * psi_m

    h_low = np.zeros(n)
    for ak, f_ in zip(a, fk):                      # 逐模态累加(⛔ 不建 |modes|×n 的大矩阵)
        h_low += ak * np.cos(2 * np.pi * f_ * t)
    h_low *= env

    # 高频尾:与 clrig.make_F 同式的噪声 RIR,高通到 f_cross 以上
    tail = rng.standard_normal(n) * env
    Nf = 1 << int(np.ceil(np.log2(n)) + 1)
    F = np.fft.rfft(tail, Nf)
    fr = np.fft.rfftfreq(Nf, 1 / fs)
    F[fr < f_cross] = 0.0
    h_high = np.fft.irfft(F, Nf)[:n]

    # 两段各自归一化后再相加 ⇒ 低/高段能量比不随模态数漂移(⛔ 否则 f_cross 会变成一个隐藏增益旋钮)
    def nz_(x):
        e = np.sqrt(np.sum(x ** 2))
        return x / (e + 1e-30)
    h = nz_(h_low) + nz_(h_high)
    h = np.concatenate([np.zeros(D), h])
    return h / (np.sqrt(np.sum(h ** 2)) + 1e-30), D


def stats_db(H_mag, floor=1e-30):
    """dB 域标准差 —— 统计场的判别量(Rayleigh 理论值 ≈ 5.57 dB)。"""
    x = 20 * np.log10(np.abs(H_mag) + floor)
    return float(np.std(x))
