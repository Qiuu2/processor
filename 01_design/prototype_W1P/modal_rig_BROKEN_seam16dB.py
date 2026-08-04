"""⛔⛔⛔ 本件【已知损坏,未修】—— 警告在**文件名**里,不只在这段注释里。

    缺陷:低段(模态合成)与高段(噪声尾)**各自归一化后相加** ⇒ 同能量摊在窄带 vs 宽带
          ⇒ `f_cross=600 Hz` 以下谱密度高出 **+16.66 dB**(实测;正常 plant 为 +0.32 dB)
          ⇒ 全部最高临界点被搬到接缝下方(模态臂 9/9 格 f_trig 落在 471–595 Hz)
          ⇒ ⇒ **凡用本件产生的 ΔMSG 一律是伪影**(r88b 全列已作废,改名 DMSG_r88b_ARTIFACT_勿用)
    ⭐ 而这条"各自归一化"正是我在 PREREG_r88 §1-③ 为**防止** f_cross 变成隐藏增益旋钮而加的护栏
       ⇒ **护栏不中立,比探针不中立更难发现 —— 它带着"我已经防过这一点了"的心理背书。**
    出处:FINDINGS.md **F81** / r88b_out_ANNOTATION.txt
    ⛔ **不得直接使用**。要用先修接缝(把两段按谱密度而非总能量对齐),而那是新一轮,须先立项。
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
