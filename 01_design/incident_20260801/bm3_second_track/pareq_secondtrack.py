# B-m3 第二轨预备件(adaptive-dsp-2, 2026-08-01)· [L2/桌面数值]
# 目的:为 CHECK A 提供真正独立的第二条设计公式路径(铁律七),替代 v1.0 的虚宣称。
# 轨1 = RBJ Cookbook peaking(负增益):alpha = sin(w0)*sinh(ln2/2*BW*w0/sin(w0))(sin 映射)
# 轨2 = Orfanidis/Välimäki-Reiss 2016 "All About Audio Equalization" Table 7.2 pareq:
#        beta = sqrt((GB^2-1)/(G^2-GB^2)) * tan(dw/2)(tan 预畸变映射),GB=sqrt(G)=半增益(dB)点
# 两轨是不同推导、不同带宽映射(sin vs tan)——预期 @f0 深度严格一致,
# 半深点带宽各自≈设定值但两轨间存在小的约定差(W1-A §3.4 已记的 BW 约定现象),如实报数。
import numpy as np

fs = 48000.0

def rbj_peaking(fs, f0, gain_db, bw_oct):
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) * np.sinh(np.log(2) / 2 * bw_oct * w0 / np.sin(w0))
    b = np.array([1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A])
    return b / a[0], a / a[0]

def vr_pareq(fs, f0, gain_db, bw_oct):
    # Välimäki & Reiss 2016(Orfanidis 系)参数 EQ,GB = 半增益(dB)点(与 RBJ 同一 BW 语义)
    G = 10.0 ** (gain_db / 20.0)
    GB = 10.0 ** (gain_db / 40.0)          # sqrt(G):半增益 dB 点
    w0 = 2 * np.pi * f0 / fs
    w1 = 2 * np.pi * f0 * 2 ** (-bw_oct / 2) / fs
    w2 = 2 * np.pi * f0 * 2 ** (+bw_oct / 2) / fs
    dw = w2 - w1
    beta = np.sqrt((GB * GB - 1.0) / (G * G - GB * GB)) * np.tan(dw / 2)
    b = np.array([(1 + G * beta), -2 * np.cos(w0), (1 - G * beta)]) / (1 + beta)
    a = np.array([1.0, -2 * np.cos(w0) / (1 + beta), (1 - beta) / (1 + beta)])
    return b, a

def mag_db(b, a, f, fs):
    z = np.exp(1j * 2 * np.pi * f / fs)
    H = (b[0] + b[1] / z + b[2] / z**2) / (a[0] + a[1] / z + a[2] / z**2)
    return 20 * np.log10(np.abs(H))

def half_depth_bw_oct(b, a, f0, depth, fs):
    fr = np.geomspace(f0 / 2, f0 * 2, 20001)
    mag = mag_db(b, a, fr, fs)
    idx = np.where(mag <= depth / 2)[0]
    return np.log2(fr[idx[-1]] / fr[idx[0]]) if len(idx) > 1 else float("nan")

print("case                     | @f0: RBJ      VR       diff    | 半深BW(oct): RBJ    VR     互差   | VR极点稳定")
for f0, depth, bw in [(1000.0, -3.0, 0.1), (1000.0, -18.0, 0.1), (250.0, -3.0, 0.2),
                      (100.0, -12.0, 0.1), (6300.0, -6.0, 0.1)]:
    b1, a1 = rbj_peaking(fs, f0, depth, bw)
    b2, a2 = vr_pareq(fs, f0, depth, bw)
    m1, m2 = mag_db(b1, a1, f0, fs), mag_db(b2, a2, f0, fs)
    bw1 = half_depth_bw_oct(b1, a1, f0, depth, fs)
    bw2 = half_depth_bw_oct(b2, a2, f0, depth, fs)
    stable = np.all(np.abs(np.roots(a2)) < 1.0)
    print(f"f0={f0:6.0f} {depth:+5.1f}dB {bw:.2f}oct | {m1:+8.4f} {m2:+8.4f} {abs(m1-m2):.2e} | "
          f"{bw1:6.4f} {bw2:6.4f} {abs(bw1-bw2):6.4f} | {stable}")
print()
print("判定(设计规格点互核,非系数逐项比——两轨带宽映射不同,系数本就不同):")
print(" ①@f0 深度:两轨都必须=设定深度(互差应 <1e-3dB);")
print(" ②半深点带宽:各自应≈设定 BW;两轨互差=sin vs tan 映射的约定差,应 <0.01oct 并如实记录;")
print(" ③VR 轨极点必须全稳。任一不满足 → FAIL。")
