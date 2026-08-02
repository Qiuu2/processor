"""r31 ②:两个分布是否分离 + 新鲜度维度实测。
⚠ 单位陷阱:那 20 例的 L0 是 **bin 电平**(_level(M,k));B-F1 的 −57~−70 是**时域 RMS tap**。
   **不同的量,不可直接比** ⇒ 本脚本测 B-F1 的 **bin 电平**,与 20 例同口径。
同时测【新鲜度】= 挂陷当槽距该轨最近一次有效观测的槽数。
[L2/宿主仿真·合成料]
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, nhs, fp_suite as S, experiments as E
from nhs import NHS, FRAME, NotchSlot
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
def q(a,lbl):
    a=np.array(a)
    if not len(a): print(f"  {lbl}: n=0"); return
    print(f"  {lbl}: n={len(a)}  min={a.min():>8.1f}  p10={np.percentile(a,10):>8.1f}  "
          f"中位={np.median(a):>8.1f}  p90={np.percentile(a,90):>8.1f}  max={a.max():>8.1f}")

def collect(runner, label, nrun):
    """记录每次**新挂陷**当槽的 bin 电平 与 新鲜度(距最近有效观测的槽数)。"""
    LV=[]; FR=[]
    for sd in range(nrun):
        a=NHS()
        oa=a._allocate
        def alloc(h,M=None,df=None,a=a,oa=oa,LV=LV,FR=FR):
            pre={id(s) for s in a.slots if s.st!=NotchSlot.FREE}
            oa(h,M,df)
            if M is None or df is None: return
            for s in a.slots:
                if s.st!=NotchSlot.FREE and id(s) not in pre:
                    k=int(round(s.f/df))
                    if 0<k<len(M): LV.append(a._level(M,k))
                    # 新鲜度:找该频点对应的轨
                    best=None
                    for t in a.tracks:
                        if t.active and abs(t.f-s.f)<max(s.f*0.2,15.0)/2: best=t; break
                    FR.append(a.slot_seq-best.last_obs_seq if best is not None else -1)
        a._allocate=alloc
        runner(a,sd)
    return LV,FR

print("r31 · 两个分布是否分离 + 新鲜度实测")
print("[L2/宿主仿真·合成料]  ⚠ 两侧均用 **bin 电平**(_level),同口径\n")
def run_piano(a,sd):
    mat=S.m_piano(200.0,1000+sd); n=(len(mat)//FRAME)*FRAME
    for i in range(0,n,FRAME): a.process_frame(mat[i:i+FRAME],GR)
def run_bf1(a,sd):
    E.scen_pinned(a,dur=20.0,thr_db=[-6.,-12.,-15.,-18.][sd%4])
print("【钢琴 · 全部新挂陷】")
LVp,FRp=collect(run_piano,'钢琴',6); q(LVp,"bin 电平"); q([f for f in FRp if f>=0],"新鲜度(槽)")
print("\n【B-F1 钉住 · 全部新挂陷】")
LVb,FRb=collect(run_bf1,'B-F1',4); q(LVb,"bin 电平"); q([f for f in FRb if f>=0],"新鲜度(槽)")
print("\n【分离性判定】")
if LVp and LVb:
    lo=np.percentile(LVb,10); hi=np.percentile(LVp,90)
    print(f"  B-F1 bin 电平 p10 = {lo:.1f}dBFS ; 钢琴挂陷 bin 电平 p90 = {hi:.1f}dBFS")
    print(f"  ⇒ {'**分布分离**,电平门仍可能' if lo>hi else '**分布重叠 ⇒ 电平这条路走死,新鲜度是唯一解**'}")
if FRp and FRb:
    fp=[f for f in FRp if f>=0]; fb=[f for f in FRb if f>=0]
    if fp and fb:
        print(f"  新鲜度:钢琴 p90={np.percentile(fp,90):.0f} 槽 ; B-F1 p90={np.percentile(fb,90):.0f} 槽")
        print(f"  ⇒ {'**新鲜度可分**' if np.percentile(fb,90)<np.percentile(fp,90) else '新鲜度不可分'}")
