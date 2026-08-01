"""V-23 补:漂移的零假设对照 + C-8f″ 的时长依赖 + E[g] 显著性"""
import numpy as np, io
import aec, probe
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
BLK_MS=probe.BLK/probe.FS*1000.0; TAU=10.0/343.0
class V(aec.MDF):
    def __init__(s2, delta=1.0, **k): super().__init__(**k); s2.delta=delta

say("\n### 补A · **零假设对照**:frozen vs frozen(两次独立冻结跑之差)")
say("  动机:E[g]>0 与 D∝n 都指向『有漂移』,但测量量是 adapt−frozen。")
say("  若两个**都冻结**的跑之间也出现正 E[g],则该漂移是**测量伪影**而非物理漂移。")
def frozen_pair(mu, dur=40.0):
    a=probe.probe_run(V(delta=1.0,mu_max=mu), adapt=False, dur=dur, far_gate=(1.0,1.0))
    b=probe.probe_run(V(delta=1.0,mu_max=mu), adapt=False, dur=dur, far_gate=(1.0,1.0))
    m=min(len(a),len(b)); return a[:m]-b[:m]
def stats(d):
    dt=BLK_MS/1000.0
    cum=np.cumsum(d)*dt/TAU; draw=cum-np.minimum.accumulate(cum)
    ns=np.unique(np.logspace(1.3,np.log10(len(d)-1),14).astype(int))
    Ds=np.array([np.max(draw[:n]) for n in ns]); ok=Ds>0
    sl=np.polyfit(np.log(ns[ok]),np.log(Ds[ok]),1)[0] if ok.sum()>3 else float('nan')
    se=np.std(d)/np.sqrt(len(d))
    return float(np.mean(d)), se, float(np.mean(d)/se if se>0 else 0), sl
say(f"  {'μ':>6}{'条件':>16}{'E[g]':>11}{'SE':>10}{'t 值':>8}{'D 斜率':>9}")
for mu in (0.10,0.40):
    d_af,_=probe.c8f_series(lambda: V(delta=1.0,mu_max=mu), dur=40.0, far_gate=(1.0,1.0))
    for nm,d in (('adapt−frozen',d_af),('frozen−frozen(零假设)',frozen_pair(mu))):
        E,se,t,sl=stats(d)
        say(f"  {mu:6.2f}{nm:>16}{E:11.5f}{se:10.5f}{t:8.1f}{sl:9.3f}")
say("  ⇒ 若零假设行的 E[g]/t/斜率与实验行相当 ⇒ **漂移是伪影**,V-23 的『线性』判定不成立。")
say("  ⇒ 若零假设行 ≈0 而实验行显著 ⇒ 漂移为真,须计入 C-8b。")

say("\n### 补B · C-8f″ 的**观测时长依赖**(门是否良定义)")
say(f"  {'μ':>6}{'时长':>7}{'C-8f max':>10}{'C-8f″(250ms)':>15}")
for mu in (0.10,0.40):
    for dur in (10.0,20.0,40.0,80.0):
        d,_=probe.c8f_series(lambda: V(delta=1.0,mu_max=mu), dur=dur, far_gate=(1.0,1.0))
        wb=max(1,int(round(250/BLK_MS))); k=np.ones(wb)/wb
        say(f"  {mu:6.2f}{dur:7.0f}{np.max(d):10.3f}{float(np.max(np.convolve(d,k,'valid'))):15.3f}")
say("  ⇒ 若 C-8f″ 亦随时长单调增 ⇒ **该门必须附带观测时长约定**,否则不可判。")
io.open('results_w2_r13.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
