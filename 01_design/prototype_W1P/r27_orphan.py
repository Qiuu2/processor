"""r27:验证「故障孤儿」机制 + B臂多出占用的归属 + A→C 净降的归属。
假设(lead 提出,本层读码支持):INSTRUMENT_FAULT 丢弃探针但**陷波留着**,
且其 from_abstain=False ⇒ **每次复检加深都刷新 t_last_hit** ⇒ **LIFT 永不启动** ⇒ 孤儿化。
[L2/宿主仿真·合成料]
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, nhs, fp_suite as S
from nhs import NHS, FRAME, NotchSlot
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
OCC=(NotchSlot.ENGAGE,NotchSlot.HOLD,NotchSlot.LIFT,NotchSlot.STANDBY)
DUR=200.0; N=6
ARMS=[('A 全关',False,False),('B 只开断言',True,False),('C 断言+P0',True,True)]
def clsify(a,s,fault_f):
    if s.from_abstain: return 'b1_弃权'
    for r in reversed(a.c8_log):
        if abs(r['f']-s.f)<max(s.f*0.2,15.0)/2:
            return 'b2_判啸叫' if r['verdict']=='howl' else 'b3_判外部残留'
    if any(abs(f-s.f)<max(s.f*0.2,15.0)/2 for f in fault_f): return '**F_故障孤儿**'
    return 'u_在飞'
def trial(mk,sd,aon,pon):
    a=NHS()
    if not aon: a.P.pair_read_tol_db=1e9
    if not pon: a.P.level_valid_db=-1e9
    mat=mk(DUR,1000+sd); n=(len(mat)//FRAME)*FRAME
    comp={}; ns=0; lift_orphan=0; seen_lift=set()
    for i in range(0,n,FRAME):
        a.process_frame(mat[i:i+FRAME],GR)
        if i%(FRAME*12)==0 and a.t_wall>=150.0:
            ff=[e[2] for e in a.events if e[1]=='INSTRUMENT_FAULT']
            for s in a.slots:
                if s.st not in OCC: continue
                comp[clsify(a,s,ff)]=comp.get(clsify(a,s,ff),0)+1
            ns+=1
        # 故障孤儿是否曾进入 LIFT
        ff=[e[2] for e in a.events if e[1]=='INSTRUMENT_FAULT']
        for si,s in enumerate(a.slots):
            if s.st==NotchSlot.LIFT and not s.from_abstain and si not in seen_lift:
                if any(abs(f-s.f)<max(s.f*0.2,15.0)/2 for f in ff):
                    lift_orphan+=1; seen_lift.add(si)
    return comp, ns, a.ctr.get('instrument_fault',0), lift_orphan
print("r27 · 故障孤儿机制验证 + 占用归属")
print(f"[L2/宿主仿真·合成料] 窗={DUR:.0f}s N={N}\n")
for nm,mk in [('钢琴',S.m_piano),('多人交谈',S.m_multitalk)]:
    print(f"【{nm}】平台段占用构成(槽·采样点均值)")
    for lbl,aon,pon in ARMS:
        C={}; NS=0; FT=0; LO=0
        for sd in range(N):
            c,ns,ft,lo=trial(mk,sd,aon,pon)
            for k,v in c.items(): C[k]=C.get(k,0)+v
            NS+=ns; FT+=ft; LO+=lo
        tot=sum(C.values())/max(NS,1)
        parts=" ".join(f"{k}={C[k]/max(NS,1):.2f}" for k in sorted(C))
        print(f"   {lbl:<12} 总={tot:.2f}  {parts}")
        print(f"   {'':<12} 仪表故障={FT}  **故障孤儿曾进入 LIFT 的槽数={LO}**")
        sys.stdout.flush()
    print()
