"""r35:(b) 临界点是否抓到全局峰  (a) 临界点是否更靠近 |F| 局部极值
    + 基线重做(≥50 realization,给均值 ± 标准误)。"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig
# ⚠ h_eff 之辨:本文件测的是 **RIR 自身的统计性质**(像不像真实房间)
#   ⇒ **刻意用 h,不用 h_eff** —— 块延迟是台架的,不是房间的。
#   (r43 已实证:改用 h_eff 后 σ_dB/i·D_i/ratio 几乎不动 ⇒ 结论不受影响)
TOPI=20
def spacings(P):
    P=P/P.mean(); S=np.sort(P)[::-1]
    return [i*(S[i-1]-S[i]) for i in range(1,TOPI+1)] if len(S)>TOPI else []

print("r35 · (b) 全局峰  (a) 极值邻近性  + 基线带误差棒\n")
print("【(b) Δ = 20log10( max|F|@全频段 / max|F|@临界点 )】")
print("   Δ≈0 ⇒ 临界点抓到全局峰,MSG 解析式可简化;Δ≫0 ⇒ 相位条件是实质约束")
for T60 in [0.2,0.5]:
    ds=[]
    for sd in range(12):
        h,_=clrig.make_F(T60=T60,delay_ms=8.0,seed=sd)
        f,H=clrig.F_response(h); m=(f>=100)&(f<=8000)
        gmax=20*np.log10(np.abs(H[m]).max())
        _,mdb=clrig.critical_points(h)
        ds.append(gmax-mdb.max())
    ds=np.array(ds)
    print(f"   T60={T60}: Δ = **{ds.mean():.2f} ± {ds.std()/np.sqrt(len(ds)):.2f} dB**  "
          f"(12 种子, min={ds.min():.2f} max={ds.max():.2f})")

print("\n【(a) 临界点 vs 随机点 到最近 |F| 局部极值的距离】")
for T60 in [0.2,0.5]:
    dc=[];dr=[]
    for sd in range(8):
        h,_=clrig.make_F(T60=T60,delay_ms=8.0,seed=sd)
        f,H=clrig.F_response(h); m=(f>=100)&(f<=8000)
        ff=f[m]; mag=np.abs(H[m])
        ext=np.where(((mag[1:-1]>mag[:-2])&(mag[1:-1]>=mag[2:]))|
                     ((mag[1:-1]<mag[:-2])&(mag[1:-1]<=mag[2:])))[0]+1
        fe=ff[ext]
        fc,_=clrig.critical_points(h)
        rr=np.random.default_rng(700+sd).uniform(ff[0],ff[-1],len(fc))
        dc+= list(np.abs(fe[np.searchsorted(fe,fc).clip(0,len(fe)-1)]-fc))
        dr+= list(np.abs(fe[np.searchsorted(fe,rr).clip(0,len(fe)-1)]-rr))
    dc=np.array(dc);dr=np.array(dr)
    print(f"   T60={T60}: 临界点距极值 中位={np.median(dc):.2f}Hz  随机点={np.median(dr):.2f}Hz  "
          f"⇒ {'**临界点显著更近**' if np.median(dc)<0.7*np.median(dr) else '无显著差异'}")

print("\n【① 基线重做:iid Exp(1),50 realization,均值 ± 标准误】")
for N in [218,455]:
    ms=[]
    for r in range(50):
        pool=[]
        for sd in range(8):
            y=np.random.default_rng(10000+r*100+sd).exponential(1.0,N)
            pool+=spacings(y)
        ms.append(np.mean(pool))
    ms=np.array(ms)
    print(f"   N={N}: 基线 = **{ms.mean():.4f} ± {ms.std()/np.sqrt(len(ms)):.4f}**  "
          f"(单次 realization 标准差={ms.std():.4f})")
