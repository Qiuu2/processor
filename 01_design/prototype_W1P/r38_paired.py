"""r38:配对对照 —— 三条阳性对照 + ΔMSG 实测 vs 逐条预测(一次式 & 迭代式)。
⚠ 结论强制附带:本合成 F(z) 临界点统计与理论有 ~4σ 偏差、真因未知;
  **绝对数不得外推到真实房间,外推待 V-34。**
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
FRAME=64; GR={'out_lim_active':False,'out_lim_gr_db':0.0}
STEP=0.5; T_OBS=3.0

def src_of(T,seed): return 1e-3*np.random.default_rng(seed).standard_normal(int(T*FS))

def ref_db(proc_f,T,seed):
    s=src_of(T,seed); p=proc_f()
    n=(len(s)//FRAME)*FRAME
    o=np.concatenate([ (p(s[i:i+FRAME]) if p else s[i:i+FRAME]) for i in range(0,n,FRAME)])
    return HD.rms_db(o)

def howls(h,D,G,proc_f,T,seed):
    s=src_of(T,seed); lp=clrig.Loop(h,D,G,proc=proc_f())
    _,loop=lp.run(s,FRAME)
    return HD.is_howling(loop, ref_db(proc_f,T,seed), FS, FRAME)[0]

def msg_ladder(h,D,proc_f,T,seed,lo=-40.0,hi=20.0):
    """+STEP dB 阶梯;**首次判起振的上一步 = MSG**。"""
    G=lo; last=lo
    while G<=hi:
        if howls(h,D,G,proc_f,T,seed): return last
        last=G; G+=STEP
    return float('inf')

def nhs_proc(nnotch=None, offset_bw=0.0, h=None):
    """返回 proc 工厂。nnotch=None ⇒ 关 NHS;否则固定挂 nnotch 个陷波
    (在预测选出的临界点上;offset_bw>0 ⇒ 故意偏移,阳性对照②)。"""
    if nnotch is None: return lambda: None
    def f():
        a=NHS()
        _,hist=clrig.predict_dmsg_iter(clrig.h_eff(h),nnotch)
        fc,mdb=clrig.critical_points(clrig.h_eff(h)); order=np.argsort(mdb)[::-1]
        for i in range(min(nnotch,len(a.slots))):
            s=a.slots[i]; f0=float(fc[order[i]])
            bw=max(f0*a.P.bw_oct,15.0)
            s.st=nhs.NotchSlot.HOLD; s.f=f0+offset_bw*bw
            s.depth=a.P.max_depth; s.target=a.P.max_depth
            s.set_coef(FS,a.P.bw_oct)
        a.P.T_low=999.0                      # 冻结自适应:只测这 k 个陷波的作用
        return lambda blk: a.process_frame(blk,GR)
    return f

print("r38 · 配对对照(阳性对照 + ΔMSG)")
print(f"[L2/宿主仿真]  阶梯={STEP}dB  T={T_OBS}s")
print("⚠ 绝对数**不得外推到真实房间**(临界点统计 4σ 偏差,真因未知);外推待 V-34\n")
print(f"{'T60':>5}{'seed':>5}{'MSG关':>8}{'解析':>8}{'k':>3}{'MSG开':>8}"
      f"{'实测Δ':>8}{'预测一次':>9}{'预测迭代':>9}{'偏移臂Δ':>9}")
rows=[]
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,D=clrig.make_F(T60=T60,delay_ms=8.0,seed=sd)
        ana,_=clrig.analytic_msg_db(clrig.h_eff(h))
        m0=msg_ladder(h,D,lambda:None,T_OBS,sd)
        for k in [1,8]:
            mk=msg_ladder(h,D,nhs_proc(k,0.0,h),T_OBS,sd)
            mo=msg_ladder(h,D,nhs_proc(k,1.5,h),T_OBS,sd) if k==8 else float('nan')
            p1=clrig.predict_dmsg(clrig.h_eff(h),k); p2,_=clrig.predict_dmsg_iter(clrig.h_eff(h),k)
            rows.append((T60,sd,k,m0,mk,mk-m0,p1,p2,mo-m0 if np.isfinite(mo) else float('nan')))
            print(f"{T60:>5.1f}{sd:>5}{m0:>8.2f}{ana:>8.2f}{k:>3}{mk:>8.2f}"
                  f"{mk-m0:>8.2f}{p1:>9.2f}{p2:>9.2f}"
                  f"{(mo-m0) if np.isfinite(mo) else float('nan'):>9.2f}")
            sys.stdout.flush()
