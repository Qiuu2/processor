"""第三轮:E1 = F4 在"GR 由他源驱动"下的真实后果;E2 = B10/B12 可触达性"""
import numpy as np
from multi import MultiLoop, DynPEQ
from env import synth_speech, synth_music, env_db, FS, FRAME
from nhs import NHS, Params
from experiments import metrics, howling, n_engage

def mk_music_burst(dur, on=(0.0,6.0)):
    m = synth_music(dur, seed=5)
    t = np.arange(len(m))/FS
    g = ((t>=on[0])&(t<on[1])).astype(float)
    from scipy.signal import lfilter
    g = lfilter(np.ones(int(0.05*FS))/int(0.05*FS),[1.0],g)
    return m*g*20.0                      # 大动态音乐,足以压住母线限幅器

print("="*76)
print("E1 · F4 真实后果:母线 GR 由**另一通道**驱动,与本通道啸叫无关")
print("="*76)
DUR=18.0
def e1(brk,label):
    ml = MultiLoop(n_ch=2, g_fwd_db=[50.0,0.0], loop_gain_db=[4.0,-60.0],
                   bus_thr_db=-6.0, dyn_thr_db=[-6.0,-6.0])   # dyn 阈很高=基本不介入
    a0 = NHS(P=Params(lift_after_s=60.0), broken=brk); 
    class Nop:
        events=[];slots=[];ctr={}
        def process_frame(self,x,gr=None): return x
        def duck_gain(self): return 1.0
    src0 = 1e-5*np.random.default_rng(0).normal(0,1,int(DUR*FS))
    src1 = mk_music_burst(DUR, on=(0.0,6.0))                  # 音乐只在前 6s
    bus,taps,chs,tr = ml.run([a0,Nop()],[src0,src1],DUR)
    e=env_db(chs[0]); m=metrics(chs[0])
    post=e[int(8*FS):]
    dpn=[x for x in a0.events if x[1]=='deepen' and x[0]*0.016>8.0]
    eng=[x for x in a0.events if str(x[1]).startswith('engage')]
    gr_pre=np.mean([t[1] for t in tr if t[0]<6]); gr_post=np.mean([t[1] for t in tr if t[0]>8])
    print(f"{label:14s} engage={len(eng)} 复发后加深={len(dpn):2d} ch0末={m['end_db']:7.1f}dB nb={m['nb']:.3f} "
          f"复发段峰={np.max(post):7.1f}dB 在啸={howling(m)}")
    print(f"{'':14s} 母线GR占空 前6s={gr_pre*100:.0f}%  后段={gr_post*100:.0f}%  (⇒后段 GR 由他源驱动=已停)")
    return m,dpn,float(np.max(post))
mf,df,pf = e1(None,"F4修法版")
mb,db,pb = e1(['B13'],"B13(v1.4)")
print(f"\n① 复发后加深: 修法={len(df)} v1.4={len(db)}")
print(f"② 复发段峰包络: 修法={pf:.1f}dB v1.4={pb:.1f}dB 差={pb-pf:+.1f}dB")
print(f"③ 末态在啸: 修法={howling(mf)} v1.4={howling(mb)}")
print(f"⇒ {'**F4 真实后果被隔离**' if (pb>pf+3 or (howling(mb) and not howling(mf))) else '仍未隔离'}")

print()
print("="*76)
print("E2 · B10/B12 可触达性:频段选择性钉住(动态PEQ)+ 本通道强语音")
print("="*76)
def e2(brk,label):
    ml = MultiLoop(n_ch=2, g_fwd_db=[45.0,0.0], loop_gain_db=[3.0,-60.0],
                   bus_thr_db=0.0,                      # 母线限幅基本不介入
                   dyn_thr_db=[-42.0,-6.0])             # ★ ch0 动态PEQ 低阈 ⇒ 频段选择性钉住
    a0 = NHS(broken=brk)
    class Nop:
        events=[];slots=[];ctr={}
        def process_frame(self,x,gr=None): return x
        def duck_gain(self): return 1.0
    src0 = synth_speech(DUR,seed=3)*0.35 + 1e-5*np.random.default_rng(0).normal(0,1,int(DUR*FS))
    src1 = np.zeros(int(DUR*FS))
    bus,taps,chs,tr = ml.run([a0,Nop()],[src0,src1],DUR)
    m=metrics(chs[0]); c=a0.ctr
    print(f"{label:14s} 末={m['end_db']:7.1f}dB nb={m['nb']:.3f} 挂陷={n_engage(a0)} "
          f"dynGR占空={np.mean([t[2][0] for t in tr])*100:.0f}%")
    print(f"{'':14s} 计数器 表满={c['table_full']}/{c['slots']} 未观测={c['unobs']} 直读成功={c['readback_ok']} "
          f"影子新={c['shadow_new']} 继承={c['shadow_inherit']} U_max={c['umax_hit']}")
    return m,c
mf2,cf2 = e2(None,"完整")
mb2,cb2 = e2(['B10'],"B10 broken")
print(f"\n⇒ B10 目标机制触达:未观测={cf2['unobs']} 直读={cf2['readback_ok']} "
      f"⇒ {'**已触达**' if (cf2['unobs']+cf2['readback_ok'])>0 else '**仍未触达**'}")
