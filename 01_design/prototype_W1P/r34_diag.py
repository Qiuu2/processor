"""r34:三条诊断。②检验器自检(D6-d:拿掉被测物)③随机点 vs 临界点 ①尺度比。"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.stats import kstest
import clrig
# ⚠ h_eff 之辨:本文件测的是 **RIR 自身的统计性质**(像不像真实房间)
#   ⇒ **刻意用 h,不用 h_eff** —— 块延迟是台架的,不是房间的。
#   (r43 已实证:改用 h_eff 后 σ_dB/i·D_i/ratio 几乎不动 ⇒ 结论不受影响)
TOPI=20; SEEDS=list(range(8))

def spacings(P):
    """与 r33 完全同一段序统计量代码:自归一化 → 降序 → 顶部 i·D_i。"""
    P=P/P.mean(); S=np.sort(P)[::-1]
    return [i*(S[i-1]-S[i]) for i in range(1,TOPI+1)] if len(S)>TOPI else []

print("r34 · 三条诊断\n")
print("【② 检验器自检(D6-d)】喂已知正确的 iid Exp(1),走同一段代码")
print("   预写:若检验器正确 ⇒ i·D_i 均值应 ≈ 1.000")
for N in [218,455]:
    pool=[]
    for sd in SEEDS:
        y=np.random.default_rng(100+sd).exponential(1.0,N)
        pool+=spacings(y)
    pool=np.array(pool)
    print(f"   N={N}: i·D_i 均值={pool.mean():.3f}  标准差={pool.std():.3f}  "
          f"KS D={kstest(pool,'expon').statistic:.4f}  "
          + ("⇒ **检验器正确**" if abs(pool.mean()-1)<0.15 else "⇒ **检验器本身有 bug**"))

print("\n【① 尺度比】mean(|F|² @临界点) / mean(|F|² @全频点)")
print("   预写:若 ratio ≈ 1.3 ⇒ 临界点选取有偏 ⇒ 动摇「临界点上 |F|² 无偏」这个前提")
for T60 in [0.2,0.5]:
    rs=[]
    for sd in SEEDS:
        h,_=clrig.make_F(T60=T60,delay_ms=8.0,seed=sd)
        f,H=clrig.F_response(h); m=(f>=100)&(f<=8000)
        allp=np.abs(H[m])**2
        _,mdb=clrig.critical_points(h); cp=10**(mdb/10.0)
        rs.append(cp.mean()/allp.mean())
    rs=np.array(rs)
    print(f"   T60={T60}: ratio = {rs.mean():.3f} ± {rs.std():.3f}  (8 种子)")

print("\n【③ 随机点 vs 临界点】同一段代码各跑一次")
for T60 in [0.2,0.5]:
    pc=[];pr=[]
    for sd in SEEDS:
        h,_=clrig.make_F(T60=T60,delay_ms=8.0,seed=sd)
        _,mdb=clrig.critical_points(h); cp=10**(mdb/10.0)
        f,H=clrig.F_response(h); m=(f>=100)&(f<=8000)
        allp=np.abs(H[m])**2
        idx=np.random.default_rng(500+sd).choice(len(allp),size=len(cp),replace=False)
        pc+=spacings(cp); pr+=spacings(allp[idx])
    pc=np.array(pc);pr=np.array(pr)
    print(f"   T60={T60}:  临界点 i·D_i 均值={pc.mean():.3f}   随机点 i·D_i 均值={pr.mean():.3f}")
