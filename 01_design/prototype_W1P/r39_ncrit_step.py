"""r39 ①:迭代式的自我证伪门 —— 每步的 N_crit 是否系统性下降。
若下降 ⇒ "max over 更少的点"本身就会变小 ⇒ ΔMSG 被伪高,与物理无关 ⇒ 数字全部不可用。
并报:陷波中心附近是否出现相位展开/过零检测失效。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz
import clrig
FS=clrig.FS
def iter_trace(h,k,depth_db=-18.0,bw_oct=0.2,n=1<<16,f_lo=100.,f_hi=8000.):
    f0,H0=clrig.F_response(h,n,FS); m=(f0>=f_lo)&(f0<=f_hi)
    f=f0[m]; H=H0[m].copy(); w=2*np.pi*f/FS
    trace=[]
    fc,mdb=clrig._crit_from_H(f,H); trace.append((len(fc),float(mdb.max())))
    notch_fs=[]
    for _ in range(k):
        fc,mdb=clrig._crit_from_H(f,H)
        if len(fc)==0: break
        fstar=float(fc[int(np.argmax(mdb))]); notch_fs.append(fstar)
        A=10**(depth_db/40.); w0=2*np.pi*fstar/FS
        al=np.sin(w0)*np.sinh(np.log(2)/2*bw_oct*w0/np.sin(w0))
        b=np.array([1+al*A,-2*np.cos(w0),1-al*A]); a=np.array([1+al/A,-2*np.cos(w0),1-al/A])
        _,Hn=freqz(b,a,worN=w); H=H*Hn
        fc2,m2=clrig._crit_from_H(f,H)
        trace.append((len(fc2),float(m2.max()) if len(m2) else float('nan')))
    return trace,f,H,notch_fs

print("r39 ① · 迭代式自我证伪门:每步 N_crit")
print("判据:step0→k 的 N_crit 在 ±10% 内 ⇒ 数字可用;系统性下降 ⇒ 全部不可用\n")
print(f"{'T60':>5}{'seed':>5}  N_crit(step 0..8)                          {'末/初':>7}{'判定':>8}")
bad=0
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,_=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        tr,f,H,nf=iter_trace(h,8)
        ns=[t[0] for t in tr]; r=ns[-1]/ns[0]
        ok=abs(r-1)<=0.10
        if not ok: bad+=1
        print(f"{T60:>5.1f}{sd:>5}  {str(ns):<42}{r:>7.3f}{'✓可用' if ok else '**下降**':>8}")
print()
print("【π 跳变检查】陷波中心 ±2 个 bin 内,相位差是否出现 >π 的跳变(过零检测护栏会漏掉它)")
h,_=clrig.make_F(T60=0.5,delay_ms=8.,seed=0)
tr,f,H,nf=iter_trace(h,8)
ph=np.angle(H); d=np.abs(np.diff(ph))
for fs_ in nf[:4]:
    j=int(np.argmin(np.abs(f-fs_)))
    seg=d[max(0,j-3):j+3]
    print(f"   陷波@{fs_:7.1f}Hz  邻域 |Δ∠| max={seg.max():.3f} rad  "
          f"{'**>π ⇒ 该处过零会被护栏跳过**' if seg.max()>np.pi else '≤π,护栏不触发'}")
print()
print(f"⇒ 总判定:{'**全部通过,迭代式数字可用**' if bad==0 else f'**{bad} 条下降 ⇒ 相应数字不可用**'}")
