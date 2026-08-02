"""W2-P V-26(MDF μ 稳定域复核)+ V-27(抽取/内插空闲恒等性)"""
import numpy as np, io, sys
import aec, metrics as M, rig, mdf_nu
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import lfilter, resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
FS=16000.0
say("="*104); say("W2-P V-26/V-27 · adaptive-dsp-3 · [L2/宿主仿真]"); say("="*104)
say("  工作点向量(D6):{fs=16k, tail=512ms, 结构, μ, δ=1.0, T_obs, ERL=n/a, 单讲}")

# ---------------- V-27 先做(它是 C-8 诞生场景的第二次出现)----------------
say("\n### V-27 · 环路内抽取/内插滤波器组的**空闲恒等性**(C-8 诞生场景第二次出现)")
say("  ⚠ 第一次:原型的 8 段动态 PEQ『分带-相加』空闲插损 6dB ⇒ 吃掉环路余量 ⇒ E1 测不成。")
say("  本次:48k↔16k 抽取/内插(101 tap,通带平坦到 6700Hz,阻带自 8000)。")
di=mdf_nu.DecimInterp()
x=np.random.default_rng(0).normal(0,0.05,48000*3)
y=np.zeros(0)
for i in range(0,len(x)-1440,1440):
    y=np.concatenate([y, di.up(di.down(x[i:i+1440]))])
n=min(len(x),len(y))
# 群延迟对齐后比较
lag=int(np.argmax(np.correlate(y[:20000], x[:20000], 'full'))-(20000-1))
xa=x[max(0,-lag):n-max(0,lag)]; ya=y[max(0,lag):n-max(0,-lag)]
m=min(len(xa),len(ya)); xa,ya=xa[:m],ya[:m]
gain=20*np.log10((np.sqrt(np.mean(ya**2))+1e-20)/(np.sqrt(np.mean(xa**2))+1e-20))
# 通带内逐 bin 增益(只看 <6700Hz)
X=np.fft.rfft(xa[:32768]); Y=np.fft.rfft(ya[:32768]); f=np.fft.rfftfreq(32768,1/48000.)
pb=(f>100)&(f<6700)
g_bin=20*np.log10(np.abs(Y[pb])/(np.abs(X[pb])+1e-20)+1e-20)
say(f"  群延迟 = {lag} 样本 = {lag/48000*1000:.2f}ms")
say(f"  空闲净增益(宽带 RMS) = {gain:+.4f}dB   {'过门(≤0.25dB)' if abs(gain)<=0.25 else '**超门**'}")
say(f"  通带 100-6700Hz 逐 bin:中位={np.median(g_bin):+.3f}dB  p95={np.percentile(g_bin,95):+.3f}dB  "
    f"最大={np.max(g_bin):+.3f}dB")
say(f"  ⇒ D_sup(通带) = {np.max(g_bin):+.3f}dB  {'**超门**(C-8 度量对象=sup_t D)' if np.max(g_bin)>0.25 else '过门'}")

# ---------------- V-26 ----------------
say("\n### V-26 · μ 稳定域:非均匀 MDF vs 均匀 K=64")
say(f"  非均匀结构 = {[(s['L'],s['K']) for s in mdf_nu.NUMDF().stages]},K_total=22,I/O 延迟 2.00ms")
say(f"  均匀结构   = L=128/K=64,I/O 延迟 8.00ms")
h=np.zeros(1600); h[100]=0.6; h[300]=-0.3; h[700]=0.15
far=resample_poly(synth_speech(16.0,seed=7),1,3)*0.5
echo=lfilter(h,[1.0],far)
say(f"  {'μ':>6}{'均匀K=64 ERLE':>15}{'非均匀 ERLE':>13}{'均匀判定':>10}{'非均匀判定':>12}")
for mu in (0.05,0.1,0.2,0.4,0.7,1.0):
    a=aec.MDF(fs=FS,tail_ms=512.,block=128,mu_max=mu); a.delta=1.0
    n=(len(far)//128)*128; e1=np.zeros(n)
    for i in range(0,n,128): e1[i:i+128]=a.process(far[i:i+128], echo[i:i+128])
    E1=M.steady_erle(echo[:n],e1,fs=FS)
    b=mdf_nu.NUMDF(fs=FS, mu_max=mu, delta=1.0)
    n2=(len(far)//32)*32; e2=np.zeros(n2)
    for i in range(0,n2,32): e2[i:i+32]=b.process(far[i:i+32], echo[i:i+32])
    E2=M.steady_erle(echo[:n2],e2,fs=FS)
    j1='发散' if E1<-50 else ('稳定' if E1>0 else '劣化')
    j2='发散' if E2<-50 else ('稳定' if E2>0 else '劣化')
    say(f"  {mu:6.2f}{E1:15.1f}{E2:13.1f}{j1:>10}{j2:>12}")
say("  ⇒ 若两列稳定上界一致 ⇒ K=64 的 μ 结论可迁移到 MDF;若不一致 ⇒ 十三轮结论须在 MDF 上重出。")
io.open('results_w2_r15.txt','w',encoding='utf-8').write('\n'.join(OUT))
