import numpy as np
from experiments import *
from env import synth_speech, synth_music, FS
from nhs import NHS, Params
# 让陷波"够不着"(max_depth=-3dB),使啸叫**持续存在** ⇒ 轨长期存活 + 被语音反复掩蔽
# 这是为了把 B10/B11/B12 的目标机制**逼出来**;非产品配置,仅诊断用。
P = lambda **kw: Params(max_depth=-3.0, depth0=-3.0, **kw)
spx = synth_speech(12.0)*0.5
busy = synth_speech(12.0,seed=7)*0.4 + synth_music(12.0,seed=8)*0.4
t=np.arange(len(busy))/FS
for f in (330.,770.,1310.,1950.,2570.,3130.,4410.,5230.,6110.,6970.): busy += 0.05*np.sin(2*np.pi*f*t)
for nm, src, brk in (('掩蔽(B10)', spx*3e-3, None), ('掩蔽(B10)broken', spx*3e-3, ['B10']),
                     ('重生(B11)', spx*5e-3, None), ('重生(B11)broken', spx*5e-3, ['B11']),
                     ('忙房间(B12)', busy*3e-3, None), ('忙房间(B12)broken', busy*3e-3, ['B12'])):
    a=NHS(P=P(), broken=brk)
    out,tap=scen_pinned(a, src=src+1e-5*np.random.default_rng(1).normal(0,1,len(src)), dur=12.0)
    m=metrics(out)
    print(f"{nm:20s} 末={m['end_db']:6.1f} nb={m['nb']:.3f} 挂陷={n_engage(a):2d} 轨活={sum(1 for x in a.tracks if x.active):2d} "
          f"| unobs={a.ctr['unobs']:4d} readbk={a.ctr['readback_ok']:3d} shadow新={a.ctr['shadow_new']:3d} 继承={a.ctr['shadow_inherit']:3d} umax={a.ctr['umax_hit']:3d}")
