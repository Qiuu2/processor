"""第四轮 P0/E1:动态PEQ 空闲单位增益后,复跑 F4 真实后果测试。"""
import numpy as np, io
from multi import MultiLoop
from env import synth_music, env_db, FS, FRAME
from nhs import NHS, Params
from experiments import metrics, howling
OUT=[]
def say(s=''):
    print(s); OUT.append(s)

class Nop:
    events=[];slots=[];ctr={}
    def process_frame(self,x,gr=None): return x
    def duck_gain(self): return 1.0

def mk_music_burst(dur, on=(0.0,6.0), amp=20.0):
    m=synth_music(dur,seed=5); t=np.arange(len(m))/FS
    g=((t>=on[0])&(t<on[1])).astype(float)
    from scipy.signal import lfilter
    g=lfilter(np.ones(int(0.05*FS))/int(0.05*FS),[1.0],g)
    return m*g*amp

say("="*76); say("第四轮 · P0 验收 + E1 复跑(动态PEQ 空闲严格单位增益)"); say("="*76)
say("P0: 空闲逐样本误差 = 0.00e+00 dB(见 r4_p0 验收)⇒ 环路余量不再被插损吃掉")

DUR=18.0
def e1(brk,label,lg=3.0):
    ml=MultiLoop(n_ch=2,g_fwd_db=[50.0,0.0],loop_gain_db=[lg,-60.0],
                 bus_thr_db=-6.0,dyn_thr_db=[-6.0,-6.0])
    a0=NHS(P=Params(lift_after_s=60.0),broken=brk)
    src0=1e-5*np.random.default_rng(0).normal(0,1,int(DUR*FS))
    src1=mk_music_burst(DUR,on=(0.0,6.0))
    bus,taps,chs,tr=ml.run([a0,Nop()],[src0,src1],DUR)
    e=env_db(chs[0]); m=metrics(chs[0]); post=e[int(8*FS):]
    dpn=[x for x in a0.events if x[1]=='deepen' and x[0]*0.016>8.0]
    eng=[x for x in a0.events if str(x[1]).startswith('engage')]
    grp=np.mean([t[1] for t in tr if t[0]<6]); grq=np.mean([t[1] for t in tr if t[0]>8])
    say(f"  {label:12s} engage={len(eng)} 复发后加深={len(dpn):2d} ch0末={m['end_db']:7.1f}dB "
        f"nb={m['nb']:.3f} 复发段峰={np.max(post):7.1f}dB 在啸={howling(m)}")
    say(f"  {'':12s} 母线GR占空 前6s={grp*100:.0f}% 后段={grq*100:.0f}%  tap0 RMS="
        f"{20*np.log10(np.sqrt(np.mean(taps[0][int(3*FS):]**2))+1e-30):.1f}dBFS")
    return m,dpn,float(np.max(post)),len(eng)

for lg in (3.0, 6.0):
    say(f"\n-- ch0 环路增益 = +{lg:.0f}dB --")
    mf,df,pf,ef=e1(None,"F4修法版",lg)
    mb,db,pb,eb=e1(['B13'],"B13(v1.4)",lg)
    if ef==0 and eb==0:
        say(f"  ⇒ ch0 仍未起振(engage 双 0),该环路增益下无从比较")
    else:
        say(f"  ⇒ 加深 修法={len(df)}/v1.4={len(db)};复发段峰 {pf:.1f} vs {pb:.1f}dB(差 {pb-pf:+.1f});"
            f"在啸 {howling(mf)}/{howling(mb)}")
io.open('results_r4.txt','w',encoding='utf-8').write('\n'.join(OUT))
