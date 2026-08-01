"""W2-P 收官格:快攻慢放 × delta 组合。四项指标同报,ERLE 阈值待 P.340 不自拍。"""
import numpy as np, io, sys
import aec, metrics as M, rig, probe
from rig import FS, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*96); say("W2-P 收官格 · 快攻慢放 × delta · adaptive-dsp-3 · [L2/宿主仿真]"); say("="*96)
say("★ 通则:结论绑定工作点(μ / delta / px攻放 / 激励)。")
say("★ ⚠ ERLE 的『够不够』**无门可判**:G168_THRESHOLDS 全 None,待 ITU-T P.340/P.341/G.161。")
say("   本表只报 ERLE 数值,**不判定可用性**,标 [待 P.340 阈值]。")
DUR=12.0; css=M.css(DUR); wb=M.white_burst(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]
mask=np.zeros(len(css),bool); mask[int(4.0*FS):int(8.0*FS)]=True

class V(aec.MDF):
    def __init__(s2, delta=1e-2, **k): super().__init__(**k); s2.delta=delta

def evaluate(fac):
    d,_ = probe.c8f_series(fac, dur=8.0, far_gate=(1.0,1.0))
    mx = float(np.max(d))
    a=fac(); dd,e,ec,_=run_aec(a,css); E_css=M.steady_erle(dd,e); C=M.converge_time_s(dd,e)
    a=fac(); dw,ew,_,_=run_aec(a,wb); E_wb=M.steady_erle(dw,ew)
    pe=np.mean(ec[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
    near=near_src*mask*np.sqrt(pe/pn)
    a=fac(); d2,e2,ec2,nr2=run_aec(a,css,near)
    E_dt=float(np.median(M.erle_db(ec2,e2-nr2)[mask]))
    return mx,E_css,E_wb,E_dt,C

PX={'对称':dict(), '攻0.3/放0.95':dict(px_attack=0.3,px_release=0.95),
    '攻0.5/放0.99':dict(px_attack=0.5,px_release=0.99)}
say("\n### 组合扫描(目标:高 μ 保 ERLE + 过 C-8f 门)")
say(f"  {'μ':>5}{'px攻放':>14}{'δ':>7}{'C8f max':>9}{'门':>5}{'ERLE-CSS':>10}{'ERLE-白噪':>10}{'ERLE-双讲':>10}{'收敛s':>7}")
best=[]
for mu in (0.2,0.4,0.7):
    for pn_,pk in PX.items():
        for dl in (1e-2,1e-1,1.0):
            mx,Ec,Ew,Ed,C = evaluate(lambda: V(delta=dl,mu_max=mu,**pk))
            ok = mx<=0.25
            if ok: best.append((mu,pn_,dl,mx,Ec,Ew,Ed,C))
            say(f"  {mu:5.2f}{pn_:>14}{dl:7.2g}{mx:9.3f}{'✓' if ok else '✗':>5}"
                f"{Ec:10.1f}{Ew:10.1f}{Ed:10.1f}{C:7.2f}")
say(f"\n  ⇒ 过门格点 {len(best)}/{3*3*3}")
if best:
    b=max(best,key=lambda r:r[4])
    say(f"  ⇒ 过门且 ERLE-CSS 最高:μ={b[0]} px={b[1]} δ={b[2]:.2g}")
    say(f"     C8f max={b[3]:.3f}(门0.25)| ERLE CSS={b[4]:.1f} 白噪={b[5]:.1f} 双讲={b[6]:.1f} 收敛={b[7]:.2f}s")
    say(f"     **ERLE 是否达产品可用:[待 P.340/P.341 阈值,本文不判]**")
else:
    say("  ⇒ **全空间无过门格点**")
say("\n### 决策包用:候选工作点(两项分列,不合并判定)")
say(f"  {'候选':>28}{'C-8f(NHS可检出性)':>20}{'ERLE-CSS':>10}{'可用性':>16}")
cands=[]
for mu in (0.2,0.4,0.7):
    for pn_,pk in PX.items():
        for dl in (1e-2,1e-1,1.0):
            pass
# 取三个代表性候选
reps=[(0.4,'攻0.5/放0.99',1.0),(0.4,'攻0.3/放0.95',1e-1),(0.7,'攻0.5/放0.99',1.0)]
for mu,pn_,dl in reps:
    mx,Ec,Ew,Ed,C = evaluate(lambda: V(delta=dl,mu_max=mu,**PX[pn_]))
    say(f"  {('μ=%.1f %s δ=%.2g'%(mu,pn_,dl)):>28}{('%.3f %s'%(mx,'过门' if mx<=0.25 else '超门%.1f×'%(mx/0.25))):>20}"
        f"{Ec:10.1f}{'[待P.340阈值]':>16}")
io.open('results_w2_r8.txt','w',encoding='utf-8').write('\n'.join(OUT))
