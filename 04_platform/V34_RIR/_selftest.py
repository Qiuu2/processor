import numpy as np, wave, subprocess, sys
from scipy.signal import fftconvolve
fs=48000; rng=np.random.default_rng(0); n=int(0.5*fs)
h=rng.standard_normal(n)*np.exp(-np.arange(n)/(0.4*fs/6.908))
with wave.open('sweep.wav','rb') as f:
    x=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768.
y=fftconvolve(x,h)[:len(x)]; y=y/np.max(np.abs(y))*0.5
for nm,s in [('_st_rec.wav',y),('_st_ref.wav',rng.standard_normal(len(y))*1e-4)]:
    with wave.open(nm,'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(fs); f.writeframes((s*32767).astype('<i2').tobytes())
print("料 OK,已知真值 T60=0.400s", flush=True)
subprocess.run([sys.executable,"analyze_rir.py","_st_rec.wav","_st_ref.wav"])
