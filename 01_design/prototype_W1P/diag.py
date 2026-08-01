import numpy as np
from experiments import *
from env import synth_speech, synth_music, FS
from nhs import NHS
spx = synth_speech(10.0)*0.5
busy = synth_speech(10.0,seed=7)*0.4 + synth_music(10.0,seed=8)*0.4
t=np.arange(len(busy))/FS
for f in (330.,770.,1310.,1950.,2570.,3130.,4410.,5230.,6110.,6970.): busy += 0.03*np.sin(2*np.pi*f*t)
cases = {
 'B10场景(钉住+语音掩蔽)': spx*1e-3 + 1e-5*np.random.default_rng(1).normal(0,1,len(spx)),
 'B11场景(钉住+强语音)':  spx*2e-3 + 1e-5*np.random.default_rng(2).normal(0,1,len(spx)),
 'B12场景(忙房间)':      busy*1e-3 + 1e-5*np.random.default_rng(3).normal(0,1,len(busy)),
}
for nm,src in cases.items():
    a=NHS(); out,tap=scen_pinned(a,src=src)
    m=metrics(out)
    print(f"{nm}: 末={m['end_db']:.1f}dB nb={m['nb']:.3f} 挂陷={n_engage(a)}")
    print(f"   计数器 {a.ctr}")
    print(f"   轨活={sum(1 for x in a.tracks if x.active)} 影子={len(a.shadows)}")
