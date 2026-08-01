import numpy as np, time
from env import image_source_rir, ClosedLoop, env_db, FS, FRAME
h,d = image_source_rir(rt60=0.35, seed=0)
Hf=np.abs(np.fft.rfft(h,1<<16)); print(f"RIR |H|max={Hf.max():.4f} @ {np.argmax(Hf)*FS/(1<<16):.1f}Hz  direct={d/FS*1e3:.1f}ms")
class Nop:
    def process_frame(self,x,gr=None): return x
    def duck_gain(self): return 1.0
for lg in (-3.0, 0.0, +3.0):
    src=0.02*np.random.default_rng(0).normal(0,1,int(4.0*FS))
    lp=ClosedLoop(h,d,Nop(),g_pre_db=0,g_fwd_db=lg)
    mic,out,tap=lp.run(src)
    e=env_db(out); X=np.abs(np.fft.rfft(out[-8192:]*np.hanning(8192)))
    print(f"环路增益={lg:+.1f}dB: 包络 0.5s={e[int(0.5*FS)]:6.1f}dB 末={e[-2000]:7.1f}dB "
          f"增长={e[-2000]-e[int(0.5*FS)]:+7.1f}dB 主频={np.argmax(X)*FS/8192:6.1f}Hz "
          f"窄带集中度={X.max()**2/np.sum(X**2):.3f}")
