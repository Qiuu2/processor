"""W2-P V-21:VSS 机制直测(不证理论,直接测能不能用)+ S0 静默冻结验证"""
import numpy as np, io, sys
import aec, metrics as M, rig, probe
from rig import FS, run_aec, BLK
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*100); say("W2-P V-21 · VSS 机制直测 + S0 静默冻结 · [L2/宿主仿真]"); say("="*100)

class VSS(aec.MDF):
    """两段步长:t<t_sw 用 mu_hi(快收敛),之后切 mu_lo(稳态跟踪)。"""
    def __init__(s2, mu_hi=0.4, mu_lo=0.1, t_sw=8.0, delta=1.0, freeze_silence=False, **k):
        super().__init__(mu_max=mu_hi, **k)
        s2.delta=delta; s2.mu_hi=mu_hi; s2.mu_lo=mu_lo
        s2.n_sw=int(t_sw*FS/BLK); s2.nb=0; s2.freeze_silence=freeze_silence
        s2.px_long=1e-9
    def process(s2,x,d):
        s2.nb+=1
        s2.mu_max = s2.mu_hi if s2.nb<=s2.n_sw else s2.mu_lo
        if s2.freeze_silence:                      # S0:远端静默即冻结
            p=float(np.mean(x**2)); s2.px_long=0.999*s2.px_long+0.001*p
            if p < 1e-3*max(s2.px_long,1e-12):
                W0=s2.W.copy(); e=super().process(x,d); s2.W=W0; return e
        return super().process(x,d)

DUR=48.0; T_SW=8.0
css=M.css(DUR); wb=M.white_burst(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]
mask=np.zeros(len(css),bool); mask[int(30*FS):int(40*FS)]=True

def erle_last(alg_fac, sig, near=None, tail_s=8.0):
    a=alg_fac(); d,e,ec,nr=run_aec(a,sig,near)
    i0=int((len(d)/FS-tail_s)*FS)
    if near is not None:
        return float(np.median(M.erle_db(ec,e-nr)[mask]))
    return float(np.median(M.erle_db(d,e)[i0:]))

say("\n### ① VSS 机制直测:μ0.4 收敛 → 切 μ_lo")
say(f"  切换点 t={T_SW}s(μ=0.4 实测收敛 7.74s);稳态窗 = 最后 8s")
say(f"  {'方案':>26}{'ERLE-CSS':>10}{'ERLE-双讲':>10}{'ERLE-白噪':>10}{'C8f max(切换后)':>16}{'门':>5}")
def c8f_post(fac, t_sw=T_SW, dur=20.0):
    """只取切换后的 C-8f(避开阶段1 与切换瞬态)"""
    d,_=probe.c8f_series(fac, dur=dur, far_gate=(1.0,1.0))
    n=len(d); i0=int(n*(t_sw+3.0)/dur)     # 切换后再留 3s 稳定
    seg=d[i0:] if i0<n-10 else d
    return float(np.max(seg)), float(np.median(seg)), float(np.std(seg)), d, i0
rows=[]
for nm,fac in (('μ=0.10 单独(对照)', lambda: VSS(mu_hi=0.1,mu_lo=0.1,t_sw=0.0)),
               ('μ=0.40 单独(对照)', lambda: VSS(mu_hi=0.4,mu_lo=0.4,t_sw=0.0)),
               ('VSS 0.4→0.10',      lambda: VSS(mu_hi=0.4,mu_lo=0.10)),
               ('VSS 0.4→0.05',      lambda: VSS(mu_hi=0.4,mu_lo=0.05))):
    Ec=erle_last(fac,css); Ew=erle_last(fac,wb)
    Ed=erle_last(fac,css,near_src*mask*0+near_src*mask)  # 占位,下面单独算
    a=fac(); d0,e0,ec0,_=run_aec(a,css)
    pe=np.mean(ec0[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
    Ed=erle_last(fac,css,near_src*mask*np.sqrt(pe/pn))
    mx,med,sd,dser,i0=c8f_post(fac)
    rows.append((nm,Ec,Ed,Ew,mx,dser,i0))
    say(f"  {nm:>26}{Ec:10.1f}{Ed:10.1f}{Ew:10.1f}{mx:16.3f}{'✓' if mx<=0.25 else '✗':>5}")

say("\n  -- 陷阱①:切换瞬态本身的 C-8f(可能比稳态更差)--")
for nm,_,_,_,_,dser,i0 in rows[2:]:
    n=len(dser); isw=int(n*T_SW/20.0)
    tr=dser[max(0,isw-5):isw+15]
    say(f"  {nm:>26} 切换瞬态窗 max={np.max(tr):7.3f}dB  稳态段 max={np.max(dser[i0:]):7.3f}dB")

say("\n### ② S0 远端静默冻结验证(零代价选项;若 S0 真冻结,静默段调制应消失)")
say(f"  {'方案':>26}{'全段 max':>10}{'静默段 max':>12}{'活动段 max':>12}{'ERLE-CSS':>10}")
for nm,fz in (('不冻结(现状)',False),('S0 静默冻结',True)):
    fac=lambda: VSS(mu_hi=0.2,mu_lo=0.2,t_sw=0.0,freeze_silence=fz)
    d,fm=probe.c8f_series(fac, dur=12.0, far_gate=(1.0,1.0))
    act=fm>(np.median(fm[fm>0])*0.1 if (fm>0).any() else 0)
    say(f"  {nm:>26}{np.max(d):10.3f}{np.max(d[~act]) if (~act).sum() else float('nan'):12.3f}"
        f"{np.max(d[act]) if act.sum() else float('nan'):12.3f}{erle_last(fac,css):10.1f}")
io.open('results_w2_r11.txt','w',encoding='utf-8').write('\n'.join(OUT))
