"""r43 ③:用 h_eff(含块延迟)重测分布 —— 那个 4σ 过度分散是否是延迟配置错造成的。
先验支持:临界点密度 ∝ 群延迟;块延迟直接改变临界点密度与位置 ⇒ 有机制,不是碰运气。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.stats import kstest
import clrig
TOPI=20; SEEDS=list(range(12))
def spac(P):
    P=P/P.mean(); S=np.sort(P)[::-1]
    return [i*(S[i-1]-S[i]) for i in range(1,TOPI+1)] if len(S)>TOPI else []
print("r43 ③ · h vs h_eff 分布对比\n")
print(f"{'T60':>5}{'口径':>8}{'N_crit':>8}{'σ_dB@临界点':>13}{'σ_dB@全带':>11}"
      f"{'i·D_i均值':>11}{'ratio':>8}")
for T60 in [0.2,0.5]:
    for lbl,tf in [('h',lambda x:x),('h_eff',clrig.h_eff)]:
        sd_c=[];sd_a=[];pool=[];rt=[];nc=[]
        for sd in SEEDS:
            h0,_=clrig.make_F(T60=T60,delay_ms=8.,seed=sd); h=tf(h0)
            f,H=clrig.F_response(h); m=(f>=100)&(f<=8000)
            sd_a.append(np.std(20*np.log10(np.abs(H[m])+1e-30)))
            fc,mdb=clrig.critical_points(h); nc.append(len(fc))
            sd_c.append(np.std(mdb))
            P=10**(mdb/10.); rt.append(P.mean()/ (np.abs(H[m])**2).mean())
            pool+=spac(P/P.mean())
        pool=np.array(pool)
        print(f"{T60:>5.1f}{lbl:>8}{np.mean(nc):>8.0f}{np.mean(sd_c):>13.2f}"
              f"{np.mean(sd_a):>11.2f}{pool.mean():>11.3f}{np.mean(rt):>8.3f}")
        sys.stdout.flush()
print("\n参考:σ_dB 理论 5.57;i·D_i 理论 1.000;ratio 理论 1.000(临界点上 |F|² 无偏)")
