"""r50:排他区选法的**实测** vs 神谕预测,六条种子。宽带衰减口径 = **100–8000Hz 内中位**。"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
from scipy.signal import freqz
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
FRAME=64; STEP=0.5; T_OBS=6.0; GR={'out_lim_active':False,'out_lim_gr_db':0.0}
P=nhs.Params(); BOUND=[]
def notch_H(f0,fg):
    A=10**(P.max_depth/40.); w0=2*np.pi*f0/FS
    al=np.sin(w0)*np.sinh(np.log(2)/2*P.bw_oct*w0/np.sin(w0))
    b=np.array([1+al*A,-2*np.cos(w0),1-al*A]); a=np.array([1+al/A,-2*np.cos(w0),1-al/A])
    return freqz(b,a,worN=2*np.pi*fg/FS)[1]
def pick_excl(he,k=8):
    fc,mdb=clrig.critical_points(he); o=list(np.argsort(mdb)[::-1])
    picks=[]; used=np.zeros(len(fc),bool)
    for i in o:
        if used[i] or len(picks)>=k: continue
        f_=float(fc[i]); picks.append(f_); used |= (np.abs(fc-f_)<=max(f_*P.bw_oct,15.))
    return picks
def oracle(he,picks):
    f0,H0=clrig.F_response(he); m=(f0>=100)&(f0<=8000)
    fm=f0[m]; Hm=H0[m]; Nt=np.ones(len(fm),dtype=complex)
    for f_ in picks: Nt=Nt*notch_H(f_,fm)
    _,a=clrig._crit_from_H(fm,Hm); _,b=clrig._crit_from_H(fm,Hm*Nt)
    return float(a.max()-b.max()), float(20*np.log10(np.median(np.abs(Nt))))
def src_of(T,s): return 1e-3*np.random.default_rng(s).standard_normal(int(T*FS))
def ref_db(T,s):
    x=src_of(T,s); return HD.rms_db(x[:(len(x)//FRAME)*FRAME])
def howls(h,D,G,pf,T,s):
    _,lp=clrig.Loop(h,D,G,proc=pf()).run(src_of(T,s),FRAME)
    return HD.is_howling(lp,ref_db(T,s),FS,FRAME)[0]
def msg(h,D,pf,T,s,lo,hi,tag):
    G=lo; last=None
    while G<=hi+1e-9:
        if howls(h,D,G,pf,T,s):
            if last is None: BOUND.append((tag,'下界')); return float('nan')
            return last
        last=G; G+=STEP
    BOUND.append((tag,'上界')); return float('nan')
def np_proc(picks):
    def f():
        a=NHS()
        for i,f_ in enumerate(picks[:len(a.slots)]):
            s=a.slots[i]; s.st=nhs.NotchSlot.HOLD; s.f=f_
            s.depth=a.P.max_depth; s.target=a.P.max_depth; s.set_coef(FS,a.P.bw_oct)
        a.P.T_low=999.
        return lambda blk: a.process_frame(blk,GR)
    return f
print("r50 · 排他区选法:实测 vs 神谕(六条种子)")
print("⚠ 宽带衰减口径 = **检测带 100–8000 Hz 内中位**\n")
print(f"{'T60':>5}{'seed':>5}{'神谕预测':>10}{'实测':>9}{'差(实−神)':>11}{'宽带@100-8k':>13}")
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd); he=clrig.h_eff(h)
        ana,_=clrig.analytic_msg_db(he)
        pk=pick_excl(he,8); pred,bb=oracle(he,pk)
        m0=msg(h,D,lambda:None,T_OBS,sd,ana-6,ana+6,f'{T60}/{sd}/base')
        mk=msg(h,D,np_proc(pk),T_OBS,sd,ana-6,ana+pred+6,f'{T60}/{sd}/excl')
        d=mk-m0 if np.isfinite(mk) and np.isfinite(m0) else float('nan')
        print(f"{T60:>5.1f}{sd:>5}{pred:>10.2f}{d:>9.2f}{d-pred:>11.2f}{bb:>13.2f}")
        sys.stdout.flush()
print(f"\n边界命中: {len(BOUND)}" + ("" if not BOUND else f"  {BOUND}"))
