import numpy as np
from experiments import *
from env import FS, FRAME, Limiter
from nhs import NHS, Params
from scipy.signal import lfilter
# F4 的 LIFT 探针场景里,啸叫**反复同频复发** ⇒ 是否触达影子继承(B11)?
h,d = rir(); h = h*10**((3.0-50.0)/20.0)
src = 1e-5*np.random.default_rng(0).normal(0,1,int(24.0*FS))
a = NHS(P=Params(lift_after_s=1.5, lift_step_s=0.4, reclaim_s=12.0)); lim=Limiter(thr_db=-6.0)
n=(len(src)//FRAME)*FRAME; fb=np.zeros(FRAME); zi=np.zeros(len(h)-1); gf=10**(50.0/20.0)
for i in range(0,n,FRAME):
    mic=src[i:i+FRAME]+fb
    y=a.process_frame(mic,{'out_lim_active':bool(lim.active),'out_lim_gr_db':float(lim.gr_db)})
    y=np.clip(y*gf*a.duck_gain(),-8,8); y=lim.process(y)
    fb,zi=lfilter(h,[1.0],y,zi=zi)
print("F4 LIFT探针场景 计数器:", a.ctr)
print("影子继承事件:", [e for e in a.events if e[1]=='shadow_inherit'][:6])
print("轨活:", sum(1 for t in a.tracks if t.active), " 影子表:", len(a.shadows))
# 追问:为何 unobs/readback 恒 0 —— 被跟踪峰是否总在 top-16 内?
M_rank=[]
orig=a._analysis_slot
