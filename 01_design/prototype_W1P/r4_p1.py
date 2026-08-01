"""P1:完整台架(多通道+母线+频段选择性动态)上重跑 B10/B11/B12"""
import numpy as np, io
from multi import MultiLoop
from env import synth_speech, synth_music, FS
from nhs import NHS, Params
from experiments import metrics, howling, n_engage
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
class Nop:
    events=[];slots=[];ctr={}
    def process_frame(self,x,gr=None): return x
    def duck_gain(self): return 1.0
say("\n"+"="*76); say("P1 · 完整台架上重跑 B10/B11/B12(前两轮判为'未触达'的三个)"); say("="*76)
DUR=18.0
def rig(brk,seed=3,spk=0.35):
    ml=MultiLoop(n_ch=2,g_fwd_db=[45.0,0.0],loop_gain_db=[3.0,-60.0],
                 bus_thr_db=0.0,dyn_thr_db=[-42.0,-6.0])
    a0=NHS(broken=brk)
    src0=synth_speech(DUR,seed=seed)*spk+1e-5*np.random.default_rng(0).normal(0,1,int(DUR*FS))
    bus,taps,chs,tr=ml.run([a0,Nop()],[src0,np.zeros(int(DUR*FS))],DUR)
    return a0, metrics(chs[0])
rows=[]
for tag,desc in (('B10','"未观测"当"未命中"'),('B11','影子继承去 causal_ok'),('B12','解除 unobs_run ≤ U_max')):
    af,mf=rig(None); ab,mb=rig([tag])
    cf,cb=af.ctr,ab.ctr
    same=(abs(mf['end_db']-mb['end_db'])<0.5 and abs(mf['nb']-mb['nb'])<0.02)
    fail = howling(mb) and not howling(mf)
    say(f"  {tag} {desc:26s} -> {'FAIL(符合预期)' if fail else '**未 FAIL**'}")
    say(f"      完整: 末={mf['end_db']:7.1f}dB nb={mf['nb']:.3f} 挂陷={n_engage(af)} | "
        f"未观测={cf['unobs']} 直读={cf['readback_ok']} 影子新={cf['shadow_new']} 继承={cf['shadow_inherit']} U_max={cf['umax_hit']}")
    say(f"      broken: 末={mb['end_db']:7.1f}dB nb={mb['nb']:.3f} 挂陷={n_engage(ab)} | "
        f"未观测={cb['unobs']} 直读={cb['readback_ok']} 影子新={cb['shadow_new']} 继承={cb['shadow_inherit']} U_max={cb['umax_hit']}")
    say(f"      ⇒ 机制{'**已触达**' if (cf['unobs']+cf['shadow_inherit']+cf['umax_hit'])>0 else '仍未触达'};"
        f"输出级{'**零差异**' if same else '有差异'}")
    rows.append((tag,fail,same))
say(f"\n  ⇒ 汇总:{sum(1 for _,f,_ in rows if f)}/3 FAIL;"
    f"{sum(1 for _,_,s in rows if s)}/3 输出级零差异")
io.open('results_r4.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
