#!/usr/bin/env python3
"""⛔⛔ 自测【未通过】—— 2026-08-03,四轮修复后仍失败。不得用于真实测量。

已知真值合成料(T60 = 0.400 s)上的实测:
  T60          报 1.387 s        ⛔ 错 3.5x
  相位过零     报 0 个            ⛔ 应为数百
  诊断         21572 个 bin 相位【全部为负、只跨 1 rad】([-1.978, -0.951])
               ⇒ 房间 IR 的相位会反复缠绕 ⇒ 被分析的 h 不是冲激响应
  ⇒ 根因在【反卷积 / 逆滤波器】,不在下游统计量。前三轮修的都是下游。

已修好的(勿重复):
  · 截断:改用相对峰值 −60 dB(原用"末段中位+3dB",而末段是数值零 ⇒ 截断形同虚设)
  · NF ≥ len(h)(np.fft.rfft 在 NF<len 时【静默截断】)
  · sign(0) 归一(避免一次过零被算成两次)

⚠ `make_sweep.py` 与 `README_MEASURE.md` 已验证可用 —— 测量可以先做,分析等本文件修好。
"""
import sys, wave, numpy as np

BAND_DET = (100.0, 8000.0)          # NHS 检测带(与 msg_meter 同源)
FS_EXPECT = 48000

def rd(p):
    with wave.open(p,"rb") as f:
        fs, n, sw, ch = f.getframerate(), f.getnframes(), f.getsampwidth(), f.getnchannels()
        raw = f.readframes(n)
    if sw != 2: sys.exit(f"⛔ {p}: 需 16-bit PCM,实为 {sw*8}-bit")
    x = np.frombuffer(raw, "<i2").astype(np.float64)/32768.0
    if ch > 1: x = x.reshape(-1,ch)[:,0]
    return x, fs

def deconv(rec, inv):
    n = len(rec)+len(inv)-1; N = 1<<int(np.ceil(np.log2(n)))
    h = np.fft.irfft(np.fft.rfft(rec,N)*np.fft.rfft(inv,N), N)
    k = int(np.argmax(np.abs(h)))            # 线性 IR 在直达峰处;谐波在其【左】侧
    return h[k:], k

def truncate_at_noise(h, fs, floor_db=-60.0):
    """截到 峰值 floor_db 以下 —— 判据必须【相对峰值】,不能用"末段中位+guard"。
    自测实证:用末段中位时,末段是数值零 ⇒ 任何数值噪声都算"在本底之上"
             ⇒ 33.66s 只截到 33.46s,截断形同虚设,T60 被高估 3.5x。"""
    w = int(0.005*fs); m = len(h)//w
    if m < 10: return h, len(h), "序列过短,未截断"
    e = np.array([np.mean(h[i*w:(i+1)*w]**2) for i in range(m)])
    e_db = 10*np.log10(e/ (e.max()+1e-30) + 1e-30)          # 相对峰值
    above = np.where(e_db > floor_db)[0]
    if len(above) == 0: return h, len(h), "全程低于阈值 ⇒ 未截断,结果存疑"
    end = min(len(h), (above[-1]+1)*w)
    return h[:end], end, None

def t60_schroeder(h, fs):
    """Schroeder 反向积分 + T20 外推。⚠ 必须喂【已截断】的 h ——
    否则把本底噪声算进衰减,T60 被高估(自测实证:0.400 → 1.388 s)。"""
    e = np.cumsum(h[::-1]**2)[::-1]; e = 10*np.log10(e/e[0] + 1e-30)
    try:
        i5, i25 = np.where(e<=-5)[0][0], np.where(e<=-25)[0][0]
    except IndexError:
        return None, "衰减未达 −25 dB(录音过短或本底过高)"
    return (i25-i5)/fs*3.0, None

def main():
    if len(sys.argv) < 3: sys.exit("用法: analyze_rir.py rec.wav rec_ref.wav")
    rec, fs = rd(sys.argv[1]); ref, fs2 = rd(sys.argv[2])
    inv = np.load("inverse_filter.npy")
    out = []; P = out.append
    P("V-34 RIR 分析 [L1/实测] —— 本脚本只报数,判读交人")
    P("="*72)
    if fs != FS_EXPECT: P(f"⚠ 采样率 {fs} ≠ {FS_EXPECT},结果不可与台架直接比对")
    if fs != fs2:      P(f"⛔ rec 与 ref 采样率不同({fs}/{fs2})—— 本底比较无效")
    if np.max(np.abs(rec)) >= 0.999: P("⛔ rec.wav 削波 ⇒ 本次作废,必须重录")

    h_raw, k = deconv(rec, inv); hr_raw, _ = deconv(ref, inv)
    h,  n_end, warn = truncate_at_noise(h_raw, fs)
    hr = hr_raw[:n_end]
    np.save("rir.npy", h)
    P(f"\n直达峰位置 {k} 样本")
    P(f"反卷积原始长度 {len(h_raw)} ({len(h_raw)/fs:.2f}s) ⇒ 截到本底后 {len(h)} ({len(h)/fs:.3f}s)")
    if warn: P(f"  ⚠ {warn}")
    P("  ⇒ rir.npy(已截断)")

    # ── Q2: T60 / DRR ────────────────────────────────────────────
    t60, err = t60_schroeder(h, fs)
    P("\n【Q2】房间参数")
    P(f"  T60(T20 外推) = {'N/A — '+err if err else f'{t60:.3f} s'}")
    d = int(0.0025*fs)                                    # 直达段 2.5 ms
    drr = 10*np.log10((np.sum(h[:d]**2)+1e-30)/(np.sum(h[d:]**2)+1e-30))
    P(f"  DRR(直混比)  = {drr:+.2f} dB   [直达段取前 2.5 ms]")

    # ── Q1: 8 kHz 以上还有没有能量 ───────────────────────────────
    P("\n【Q1】⭐ 8 kHz 以上是否还有足以维持啸叫的能量")
    NF = max(1<<17, 1<<int(np.ceil(np.log2(len(h)))))   # ⚠ 必须 ≥ len(h):
    #    np.fft.rfft(h, NF) 在 NF<len(h) 时【静默截断】,自测中导致相位过零报 0
    H  = 20*np.log10(np.abs(np.fft.rfft(h,  NF))+1e-30)
    HR = 20*np.log10(np.abs(np.fft.rfft(hr, NF))+1e-30)   # 本底
    f  = np.fft.rfftfreq(NF, 1/fs)
    P(f"  {'频段':<14}{'RIR 中位':>10}{'本底中位':>10}{'信噪余量':>10}   判读")
    for lo,hi in [(100,1000),(1000,4000),(4000,8000),(8000,12000),(12000,16000),(16000,20000),(20000,24000)]:
        m = (f>=lo)&(f<hi)
        if not m.any(): continue
        a, b = np.median(H[m]), np.median(HR[m]); s = a-b
        tag = "本底限 ⇒ N/A" if s < 6 else ("有能量" if s >= 12 else "接近本底")
        P(f"  {lo:>5}-{hi:<8}{a:>10.1f}{b:>10.1f}{s:>10.1f}   {tag}")
    ref_m = (f>=1000)&(f<4000); ref_lv = np.median(H[ref_m])
    P(f"\n  相对 1–4 kHz({ref_lv:.1f} dB)的滚降:")
    for lo,hi in [(8000,12000),(12000,16000),(16000,20000)]:
        m=(f>=lo)&(f<hi)
        P(f"    {lo//1000}–{hi//1000} kHz: {np.median(H[m])-ref_lv:+.1f} dB")
    P("  ⚠ 判读须人做。参考:台架 f_cut=8k 假设【8 kHz 以上不足以维持啸叫】。")
    P("     若 8–20 kHz 相对滚降不足 −10 dB 且信噪余量 ≥12 dB ⇒ 该假设存疑,须报。")

    # ── Q3: N_crit / σ_dB ────────────────────────────────────────
    P("\n【Q3】临界点统计(检测带 100–8000 Hz)")
    m = (f>=BAND_DET[0])&(f<=BAND_DET[1])
    P(f"  σ_dB = {np.std(H[m]):.2f} dB   [瑞利理论普适值 5.57;偏离大 ⇒ 非扩散场或本底污染]")
    ph = np.angle(np.fft.rfft(h, NF))
    phm = ph[m]
    sg = np.sign(phm); sg[sg == 0] = 1.0            # ⚠ sign 可能给 0,会把一次过零算成两次
    z  = np.where(np.diff(sg) != 0)[0]
    P(f"  相位过零(∝ N_crit)= {len(z)} 个;密度 {len(z)/(BAND_DET[1]-BAND_DET[0])*1000:.1f} /kHz")
    P(f"    [诊断] 该带 bin 数={m.sum()}  相位范围 [{phm.min():+.3f},{phm.max():+.3f}] rad"
      f"  正/负 bin = {(phm>0).sum()}/{(phm<0).sum()}")
    if len(z) == 0:
        P("    ⛔ 过零数为 0 —— 若正负 bin 都非零则本行有 bug,不得当作物理结论")
    if t60: P(f"  Schroeder 式 1975·T60 预测 = {1975*t60:.0f}  [对照用,非同一定义]")

    P("\n"+"="*72)
    P("⚠ 一次测量 = 一个房间一个摆位,不得外推。")
    P("⚠ 本报告不回答『NHS 值几 dB』—— 那是 B-1 的活,与本测量无关。")
    txt = "\n".join(out)
    open("rir_report.txt","w",encoding="utf-8").write(txt+"\n")
    print(txt); print("\n⇒ 已存 rir.npy / rir_report.txt")

if __name__ == "__main__":
    main()
