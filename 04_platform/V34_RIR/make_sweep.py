#!/usr/bin/env python3
"""V-34 · 生成指数扫频(ESS)+ 其逆滤波器。

用 ESS 而非白噪/MLS 的理由:非线性谐波在反卷积后【聚到时间轴负侧】,
与线性冲激响应天然分离 ⇒ 扬声器失真不会污染 RIR。
(白噪法做不到这一点,而会议音箱在大音量下必有失真。)
"""
import numpy as np, wave

FS, T, F1, F2 = 48000, 10.0, 20.0, 24000.0
PAD = 2.0   # 尾部留白,给混响衰减

def main():
    n = int(T * FS); t = np.arange(n) / FS
    R = np.log(F2 / F1)
    x = np.sin(2*np.pi*F1*T/R * (np.exp(t*R/T) - 1.0))
    # 首尾各 50 ms 淡入淡出,避免起止咔哒声污染低频
    m = int(0.05*FS); w = np.hanning(2*m)
    x[:m] *= w[:m]; x[-m:] *= w[m:]
    y = np.concatenate([x, np.zeros(int(PAD*FS))])
    y = (y / np.max(np.abs(y)) * 0.7)          # 峰值 −3 dBFS,留削波余量

    with wave.open("sweep.wav","wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(FS)
        f.writeframes((y*32767).astype("<i2").tobytes())

    # 逆滤波器:时间反转 + 幅度补偿(ESS 能量 ∝ 1/f)
    inv = x[::-1] * np.exp(-t[::-1]*R/T)
    np.save("inverse_filter.npy", inv.astype(np.float64))
    np.save("sweep_params.npy", np.array([FS, T, F1, F2, PAD]))
    print(f"✅ sweep.wav  {T+PAD:.0f}s @ {FS}Hz  {F1:.0f}–{F2:.0f}Hz  峰值 -3 dBFS")
    print("   inverse_filter.npy 已存(analyze_rir.py 会用)")

if __name__ == "__main__":
    main()
