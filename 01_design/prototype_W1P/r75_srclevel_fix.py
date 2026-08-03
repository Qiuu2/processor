"""r75 · 源电平 × 修法 主扫描。⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r75.txt
输出 r75_srclevel_fix_out.txt。deps: nhs.py@a6b467df127e741f clrig.py@8ad47ce8d260dd18
⛔ 结论行看到数之后再写;修法臂标「非提交修法」。
"""
import sys, numpy as np
sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import clrig, howl_detect as HD, nhs
from nhs import NHS, NotchSlot
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
FRAME,BW,STEP=64,1/5,0.5
SEEDS=[(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
SRC=[-20.,-60.]          # 主档 −20(标称) / 对齐档 −60(B-1)
RUNGS=[6.,12.]
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()
def mk(fix,ablate):
    a=NHS(); a.P.bw_oct=BW; a.P.T_low=-45.; a.P.prefer_unnotched=fix
    if ablate: a.duck_gain=lambda: 1.0
    return a
def scan(hb,D,mkf,lo,hi,src,ref):
    G,last,st=lo,None,None
    while G<=hi+1e-9:
        a=mkf(); pf=None
        if a is not None:
            def pf(b,_a=a): return _a.process_frame(b,GR)
        _,lp=clrig.Loop(hb,D,G,proc=pf).run(src,FRAME)
        if HD.is_howling(lp,ref,FS,FRAME)[0]:
            return (float('nan') if last is None else last), st
        last=G
        if a is not None:
            u=[s for s in a.slots if s.st!=NotchSlot.FREE]
            st=dict(n=len(u), fr=sorted(round(float(s.f),1) for s in u),
                    n1=int(a.ctr.get('N1_cand',0)), n2=int(a.ctr.get('N2_lvl',0)))
        G+=STEP
    return float('nan'), st
def axes(fr,picks):
    if not picks: return (None,float('nan'),float('nan'))
    bw=lambda f: max(f*BW,15.)
    t=float(picks[0])
    t1=any(abs(f-t)<=bw(t)/2 for f in fr) if fr else False
    hit=(sum(1 for f in fr if any(abs(f-p)<=bw(p)/2 for p in picks))/len(fr)) if fr else float('nan')
    cov=sum(1 for p in picks if any(abs(f-p)<=bw(p)/2 for f in fr))/len(picks)
    return (t1,hit,cov)
def main():
    W("未经 critic 评审 —— r75 · 源电平 × 修法 主扫描  [L2/宿主仿真]  预注册 = PREREG_r75.txt")
    W("deps: nhs.py@a6b467df127e741f(prefer_unnotched 默认 False;逐位等价见 r75a:24/24 PASS,阳性对照 9/24)")
    W("⛔ 算力截断(显式):源电平只跑 {−20 标称, −60 对齐 B-1};砍 −40/−30/−10;")
    W("   T_low 定 −45(架构侧已裁,分叉已闭),砍 −50 对照;T_OBS 钉死 {6,12},不做 F36 阶梯")
    W("   ⇒ T60=0.5 层未收敛(r64 已证 48s 仍不收敛)⇒ **该层 δ 不得单独成句**")
    W("⛔ 修法臂 = **非提交修法**,其数不得当修法收益引用")
    W("⚠ B-1 的 1.00–2.50 dB 系在 **src_rms = −60 dBFS** 上测得,而**标称为 −20 dBFS**")
    W("")
    W("%7s%6s%5s%4s%6s | %8s%10s%10s | %8s%7s%7s%7s"%('src','修法','T60','sd','T_OBS',
      'm0','ΔMSG_有duck','ΔMSG_消融','过门率','挂陷','top1','cov'))
    env={}
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        env[(T60,sd)]=(hb,D,pick_excl(he,BW,8),
                       MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db'])
    R={}
    for L in SRC:
        for fx in (False,True):
            for (T60,sd) in SEEDS:
                hb,D,picks,anchor=env[(T60,sd)]
                for T in RUNGS:
                    src=np.random.default_rng(sd).standard_normal(int(T*FS))*(10**(L/20.))
                    ref=HD.rms_db(src[:(len(src)//FRAME)*FRAME])
                    m0,_=scan(hb,D,lambda: None, anchor-3, anchor+4, src, ref)
                    mn,stn=scan(hb,D,lambda: mk(fx,False), anchor-1, anchor+20, src, ref)
                    ma,_ =scan(hb,D,lambda: mk(fx,True),  anchor-1, anchor+20, src, ref)
                    dn=mn-m0 if np.isfinite(mn) and np.isfinite(m0) else float('nan')
                    da=ma-m0 if np.isfinite(ma) and np.isfinite(m0) else float('nan')
                    t1,hit,cov=axes(stn['fr'] if stn else [],picks)
                    rate=(stn['n2']/stn['n1']) if (stn and stn['n1']) else float('nan')
                    R[(L,fx,T60,sd,T)]=(dn,da,stn['n'] if stn else -1,t1,rate)
                    W("%7.0f%6s%5.1f%4d%6.0f | %8.2f%10.2f%10.2f | %7.2f%%%7d%7s%7.2f"%(
                      L,('开' if fx else '关'),T60,sd,T,m0,dn,da,100*rate,
                      stn['n'] if stn else -1,str(t1),cov))
            W("")
    W("="*104); W("§S 修法配对差 δ = ΔMSG(修法开) − ΔMSG(修法关),同源电平同档配对"); W("="*104)
    for L in SRC:
        W("--- src = %.0f dBFS"%L)
        for T in RUNGS:
            v=[]
            for (T60,sd) in SEEDS:
                a=R.get((L,False,T60,sd,T)); b=R.get((L,True,T60,sd,T))
                if a and b and np.isfinite(a[0]) and np.isfinite(b[0]):
                    v.append((T60,sd,round(b[0]-a[0],2),a[2],b[2]))
            W("  T_OBS=%.0fs  δ 逐条(T60,sd,δ,挂陷关,挂陷开):%s"%(T,v))
            s=[x[2] for x in v]
            if s: W("        符号:正 %d / 零 %d / 负 %d  ⇒ %s"%(
                sum(1 for x in s if x>0),sum(1 for x in s if x==0),sum(1 for x in s if x<0),
                '⚠ **变号 —— 按 Hq4 不得平均**' if (any(x>0 for x in s) and any(x<0 for x in s)) else '同号'))
        W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r75_srclevel_fix_out.txt','w').write("\n".join(O)+"\n")
if __name__=='__main__': main()
