"""r36:非参数路线(主) + ② 群延迟机制(附带)。
⚠ **这条 F(z) 是否代表真实会议室,最终只能由 V-34 的真实 RIR 判定;
   合成料的分布检验只是【代理量】。我们现在争的是代理量对不对。**
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig
# ⚠ h_eff 之辨:本文件测的是 **RIR 自身的统计性质**(像不像真实房间)
#   ⇒ **刻意用 h,不用 h_eff** —— 块延迟是台架的,不是房间的。
#   (r43 已实证:改用 h_eff 后 σ_dB/i·D_i/ratio 几乎不动 ⇒ 结论不受影响)
SEEDS=list(range(12))

def crit_power(h):
    _,mdb=clrig.critical_points(h); P=10**(mdb/10.0)
    return P/P.mean()

print("r36 · 非参数经验分布(主路)+ 群延迟机制(附带)")
print("⚠ 合成料的分布检验只是**代理量**;是否代表真实会议室由 V-34 真实 RIR 判定\n")

for T60 in [0.2,0.5]:
    pool=[]
    for sd in SEEDS:
        h,_=clrig.make_F(T60=T60,delay_ms=8.0,seed=sd); pool.append(crit_power(h))
    allP=np.concatenate(pool)
    print(f"【T60={T60}】临界点 |F|² 池化 N={len(allP)}(12 种子)")
    print("   经验 CDF vs Exp(1) 逐点偏差:")
    print(f"      {'分位':>6}{'经验值':>10}{'Exp(1)值':>10}{'偏差':>9}{'CDF偏差':>9}")
    for q in [0.10,0.25,0.50,0.75,0.90,0.95,0.99]:
        ev=np.quantile(allP,q); tv=-np.log(1-q)
        Fe=(allP<=tv).mean()
        print(f"      {q:>6.2f}{ev:>10.3f}{tv:>10.3f}{ev-tv:>+9.3f}{Fe-q:>+9.3f}")
    # 顶部 20 阶
    tops=[]
    for P in pool:
        S=np.sort(P)[::-1]
        if len(S)>=20: tops.append(S[:20])
    T=np.array(tops)
    print("   **顶部 20 阶经验分布**(ΔMSG 真正吃的部分),对比 Exp(1) 理论 E[X(i)]=Σ_{j=i}^{N}1/j:")
    N=int(np.mean([len(P) for P in pool]))
    print(f"      {'阶i':>4}{'经验均值':>10}{'理论均值':>10}{'比值':>8}")
    for i in [1,2,3,5,10,20]:
        emp=T[:,i-1].mean(); th=sum(1.0/j for j in range(i,N+1))
        print(f"      {i:>4}{emp:>10.3f}{th:>10.3f}{emp/th:>8.3f}")
    lg=np.log(allP)
    print(f"   log|F|² 经验分布:均值={lg.mean():.3f}(Gumbel理论 −γ=−0.5772)  "
          f"标准差={lg.std():.3f}(理论 π/√6=1.2825)  偏度={float(((lg-lg.mean())**3).mean()/lg.std()**3):.3f}(理论 −1.14)")
    print()

print("【② 群延迟机制(待测假说,非判断)】τ_g 在 |F| 高/中/低三分位上的均值")
for T60 in [0.2,0.5]:
    hi=[];mid=[];lo=[]
    for sd in SEEDS[:6]:
        h,_=clrig.make_F(T60=T60,delay_ms=8.0,seed=sd)
        f,H=clrig.F_response(h); m=(f>=100)&(f<=8000)
        ff=f[m]; Hm=H[m]
        ph=np.unwrap(np.angle(Hm))
        tg=-np.gradient(ph,2*np.pi*ff)      # 群延迟(秒)
        mag=np.abs(Hm)
        q1,q2=np.quantile(mag,[1/3,2/3])
        lo.append(tg[mag<=q1].mean()); mid.append(tg[(mag>q1)&(mag<=q2)].mean()); hi.append(tg[mag>q2].mean())
    lo=np.array(lo)*1e3; mid=np.array(mid)*1e3; hi=np.array(hi)*1e3
    print(f"   T60={T60}:  |F|低三分位 τ_g={lo.mean():.2f}ms  中={mid.mean():.2f}ms  高={hi.mean():.2f}ms")
    print(f"            ⇒ {'**两端 > 中间 ⇒ 机制成立**' if (lo.mean()>mid.mean() and hi.mean()>mid.mean()) else '**不成立(两端未同时大于中间)**'}")
