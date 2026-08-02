"""W2-P V-26 前置:稠密 RIR 逐段波形验收(不只看峰位)"""
import numpy as np, io, sys
import mdf_nu, rig, aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import lfilter, resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*104); say("W2-P · 稠密 RIR 逐段波形验收(D6-c:补上『被测系统复杂度』这一维)· [L2/宿主仿真]"); say("="*104)
ST=((32,8),(256,8),(1024,6))
h_true,_ = rig.echo_path(seed=0)                      # 稠密真实 RIR
say(f"  真值 RIR:长度 {len(h_true)} 样本,稠密(非稀疏 delta)")
far=resample_poly(synth_speech(60.0,seed=7),1,3)*0.5
echo=lfilter(h_true,[1.0],far)

def seg_corr(b, h):
    rows=[]
    Etot=float(np.sum(h**2))+1e-20
    for si,s in enumerate(b.stages):
        lo,hi=s['off'], s['off']+s['L']*s['K']
        w=np.concatenate([np.fft.irfft(s['W'][k],s['M'])[:s['L']] for k in range(s['K'])])
        ht=np.zeros(len(w)); seg=h[lo:min(hi,len(h))]
        ht[:len(seg)]=seg
        Eseg=float(np.sum(ht**2))
        c=float(np.corrcoef(w,ht)[0,1]) if np.std(w)>1e-12 and np.std(ht)>1e-12 else float('nan')
        rows.append((si,s['L'],s['K'],lo,hi,c,Eseg/Etot))
    return rows

say("\n### 相关阈值依据(lead 要求给阈值与依据,不只报数字)")
say("  用**该段在真值 RIR 中的能量占比**加权:低能量段本就难估,其低相关不应判为 bug。")
say("  判据:段能量占比 ≥5% 的段,要求 |corr| ≥ 0.7;占比 <5% 的段只作参考不作判定。")

say("\n### 收敛时长扫描(lead 要求:分清『没收敛』与『收敛错了』——看相关是否单调上升)")
say(f"  {'时长s':>7}{'段':>4}{'L':>6}{'覆盖tap':>14}{'能量占比':>9}{'相关corr':>10}{'判定':>12}")
prev={}
for dur in (10.0, 30.0, 60.0):
    b=mdf_nu.NUMDF(fs=16000., stages=ST, mu_max=0.05, delta=1.0)
    n=int(min(dur*16000, len(far))//32*32)
    for i in range(0,n,32): b.process(far[i:i+32], echo[i:i+32])
    for si,L,K,lo,hi,c,e in seg_corr(b,h_true):
        if e>=0.05:
            j = '✓高相关' if abs(c)>=0.7 else '✗低相关'
        else:
            j = '(低能量,参考)'
        arrow=''
        if si in prev and not np.isnan(c):
            arrow = ' ↑' if abs(c)>abs(prev[si])+0.02 else (' ↓' if abs(c)<abs(prev[si])-0.02 else ' →')
        prev[si]=c
        say(f"  {dur:7.0f}{si:4d}{L:6d}{('%d-%d'%(lo,hi-1)):>14}{e*100:8.1f}%{c:10.3f}{j:>12}{arrow}")
    say("")
say("  ⇒ 相关**单调上升** ⇒ 只是没收敛完,继续跑会好(非缺陷);")
say("    相关**不升或下降** ⇒ 收敛到了错的解 ⇒ 结构/实现缺陷。")

say("\n### 对照:同一稠密 RIR 上的均匀 K=64")
a=aec.MDF(fs=16000.,tail_ms=512.,block=128,mu_max=0.05); a.delta=1.0
n=int(min(60.0*16000,len(far))//128*128)
for i in range(0,n,128): a.process(far[i:i+128], echo[i:i+128])
w=np.concatenate([np.fft.irfft(a.W[k],a.M)[:a.N] for k in range(a.K)])
ht=np.zeros(len(w)); seg=h_true[:min(len(w),len(h_true))]; ht[:len(seg)]=seg
say(f"  均匀 K=64 全滤波器相关 = {float(np.corrcoef(w,ht)[0,1]):.3f}")
io.open('results_w2_r19.txt','w',encoding='utf-8').write('\n'.join(OUT))
