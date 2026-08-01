"""F4 决定性测试(v3)· 用 LIFT 探针制造**同频复发**——这正是 F4 破坏的功能。
  啸 → 挂陷 → 抑制成功(限幅器松开 ⇒ GR 失活)→ LIFT 把深度还回去 ⇒ **同频复发**
  → 能否被再检出并加深?
判据取输出信号 + 该频点陷波深度轨迹。
"""
import numpy as np
from experiments import *
from env import env_db, FS, FRAME, Limiter
from nhs import NHS, Params

def run(brk, label, dur=24.0, g0=50.0, lg0=3.0):
    from scipy.signal import lfilter
    h, d = rir(); h = h * 10 ** ((lg0 - g0) / 20.0)
    src = 1e-5*np.random.default_rng(0).normal(0,1,int(dur*FS))
    P = Params(lift_after_s=1.5, lift_step_s=0.4, reclaim_s=12.0)   # 缩短 LIFT 以适配短仿真
    a = NHS(P=P, broken=brk); lim = Limiter(thr_db=-6.0)
    n=(len(src)//FRAME)*FRAME; out=np.zeros(n)
    fb=np.zeros(FRAME); zi=np.zeros(len(h)-1); gf=10**(g0/20.0)
    dep_tr=[]; gr_tr=[]
    for i in range(0,n,FRAME):
        mic=src[i:i+FRAME]+fb
        gr={'out_lim_active':bool(lim.active),'out_lim_gr_db':float(lim.gr_db)}
        y=a.process_frame(mic,gr); y=np.clip(y*gf*a.duck_gain(),-8,8); y=lim.process(y)
        fb,zi=lfilter(h,[1.0],y,zi=zi); out[i:i+FRAME]=y
        if i%(FRAME*750)==0:      # 每 1s 采样
            s0=[s for s in a.slots if s.st!=0]
            dep_tr.append(round(min([s.depth for s in s0], default=0.0),1))
            gr_tr.append(int(lim.active))
    e=env_db(out); m=metrics(out)
    dpn=[x for x in a.events if x[1]=='deepen']
    segs=[round(float(np.max(e[int(t*FS):int((t+3)*FS)])),1) for t in range(0,int(dur)-2,3)]
    print(f"{label:20s} engage={len([x for x in a.events if str(x[1]).startswith('engage')])} "
          f"deepen={len(dpn):3d} 末={m['end_db']:6.1f}dB nb={m['nb']:.3f} 仍在啸={howling(m)}")
    print(f"{'':20s} 最深陷波深度轨迹(每1s)={dep_tr}")
    print(f"{'':20s} GR活跃(每1s)          ={gr_tr}")
    print(f"{'':20s} 分段峰包络(每3s)      ={segs}")
    return a,m,dpn,segs

print("=== F4 决定性测试 v3:LIFT 探针 → 同频复发 → 能否再检出并加深 ===")
af,mf,df,sf = run(None,   "F4修法版")
print()
ab,mb,db,sb = run(['B13'],"B13(v1.4行为)")
print()
print(f"① 复发后仍在啸? 修法版={howling(mf)}  v1.4行为={howling(mb)}")
print(f"② 末包络       : 修法版={mf['end_db']:.1f}dB  v1.4行为={mb['end_db']:.1f}dB  差={mb['end_db']-mf['end_db']:+.1f}dB")
print(f"⇒ {'**F4 修法成立**(B13 FAIL / 修法版 PASS)' if (not howling(mf)) and howling(mb) else '未达标,需再诊断'}")
