#!/usr/bin/env python3
"""合成料自测:已知真值 T60 = 0.400 s,判 analyze_rir.py 三条判据。

合成料 = 白噪 × 指数衰减包络,长 0.5 s。真值推导:
  幅度包络 exp(-n/τ),τ = 0.400·fs/6.908 ⇒ 衰 60 dB 需 n = 6.9078·τ = 0.400·fs ⇒ T60 = 0.400 s。
  0.5 s 处已衰 −75 dB,T20 外推(需 −25 dB,出现在 0.167 s)不受料长截断影响。
⚠ 本料是【扩散场类】随机响应 ⇒ σ_dB 应 ≈ 瑞利普适值 5.57、频响应平坦、
  DRR 解析值 = −10.45 dB。这三个是免费的交叉验证,别忽略。
"""
import numpy as np, wave, subprocess, sys, re
from scipy.signal import fftconvolve
fs=48000; rng=np.random.default_rng(0); n=int(0.5*fs)
T60_TRUE=0.400
h=rng.standard_normal(n)*np.exp(-np.arange(n)/(T60_TRUE*fs/6.908))
with wave.open('sweep.wav','rb') as f:
    x=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768.
y=fftconvolve(x,h)[:len(x)]; y=y/np.max(np.abs(y))*0.5
for nm,s in [('_st_rec.wav',y),('_st_ref.wav',rng.standard_normal(len(y))*1e-4)]:
    with wave.open(nm,'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(fs); f.writeframes((s*32767).astype('<i2').tobytes())
print(f"料 OK,已知真值 T60={T60_TRUE:.3f}s", flush=True)
r=subprocess.run([sys.executable,"analyze_rir.py","_st_rec.wav","_st_ref.wav"],capture_output=True,text=True)
print(r.stdout, end=""); print(r.stderr, end="", file=sys.stderr)

# ── 判据(三条同时满足才 PASS)──────────────────────────────────
o=r.stdout
def grab(pat, cast=float):
    m=re.search(pat,o); return cast(m.group(1)) if m else None
t60 = grab(r"T60\(T20 外推\) = ([\d.]+) s")
zc  = grab(r"相位过零\(∝ N_crit\)= (\d+) 个", int)
pos = grab(r"正/负 bin = (\d+)/\d+", int); neg = grab(r"正/负 bin = \d+/(\d+)", int)
chk=[("T60 ≈ %.3f s (±10%%)"%T60_TRUE,
      t60 is not None and abs(t60-T60_TRUE)<=0.1*T60_TRUE, f"报 {t60} s"),
     ("相位过零 = 数百量级",
      zc is not None and zc>=100, f"报 {zc} 个"),
     ("相位有正有负",
      bool(pos and neg), f"正/负 bin = {pos}/{neg}")]
print("\n"+"="*72+"\n自测判据")
for name,ok,got in chk: print(f"  [{'PASS' if ok else 'FAIL'}] {name:<28} {got}")
allok=all(c[1] for c in chk)
print(f"⇒ {'✅ 自测通过' if allok else '⛔ 自测未通过'}")
sys.exit(0 if allok else 1)
