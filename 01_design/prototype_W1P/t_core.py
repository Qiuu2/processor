import numpy as np, time
from env import image_source_rir, ClosedLoop, env_db, FS
from nhs import NHS, Params
class Nop:
    def process_frame(self,x,gr=None): return x
    def duck_gain(self): return 1.0
h,d=image_source_rir(rt60=0.35,seed=0)
src=0.02*np.random.default_rng(0).normal(0,1,int(8.0*FS))
for name,alg in (("bypass",Nop()),("NHS",NHS())):
    t0=time.time()
    lp=ClosedLoop(h,d,alg,g_pre_db=0,g_fwd_db=-2.0)
    mic,out,tap=lp.run(src,g_fwd_ramp_db_per_s=1.5)
    e=env_db(out); X=np.abs(np.fft.rfft(out[-8192:]*np.hanning(8192)))
    peak=float(np.max(e[int(1*FS):]))
    print(f"{name:7s}: 末包络={e[-2000]:7.1f}dB 峰包络={peak:7.1f}dB "
          f"窄带集中度={X.max()**2/np.sum(X**2):.3f} ({time.time()-t0:.1f}s)")
    if hasattr(alg,'events'):
        print(f"   事件({len(alg.events)}): {alg.events[:8]}")
        print(f"   末陷波: {[ (round(s.f,1),round(s.depth,1)) for s in alg.slots if s.st!=0]}")
