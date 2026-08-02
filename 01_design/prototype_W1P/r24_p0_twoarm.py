"""r24 双臂:P0 有效性门 开 vs 关(同种子、同素材、同窗长,唯一差异 = 该门)。
关臂 = level_valid_db 设为 -1e9(永不拦)。[L2/宿主仿真·合成料]
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, nhs, fp_suite as S
from nhs import NHS, FRAME, NotchSlot
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
OCC=(NotchSlot.ENGAGE,NotchSlot.HOLD,NotchSlot.LIFT,NotchSlot.STANDBY)
DUR=200.0; N=6
def trial(mk,sd,gate_on):
    a=NHS()
    if not gate_on: a.P.level_valid_db=-1e9
    mat=mk(DUR,1000+sd); n=(len(mat)//FRAME)*FRAME
    occ=[];b1=[]
    for i in range(0,n,FRAME):
        a.process_frame(mat[i:i+FRAME],GR)
        if i%(FRAME*12)==0 and a.t_wall>=150.0:
            o=[s for s in a.slots if s.st in OCC]
            occ.append(len(o)); b1.append(sum(1 for s in o if s.from_abstain))
    c=a.ctr
    ab=sum(1 for r in a.c8_log if r['verdict']=='abstain')
    ex=sum(1 for r in a.c8_log if r['verdict']=='ext')
    hw=sum(1 for r in a.c8_log if r['verdict']=='howl')
    eng=sum(1 for e in a.events if 'engage' in str(e[1]))
    return dict(probe=c.get('c8_probe_started',0), ab=ab, ex=ex, hw=hw, eng=eng,
                blk=c.get('p0_blocked_novalid',0), flt=c.get('instrument_fault',0),
                occ=np.mean(occ) if occ else 0, b1=np.mean(b1) if b1 else 0)
print("r24 · P0 有效性门 双臂(同种子/同素材/同窗长)")
print(f"[L2/宿主仿真·合成料]  窗={DUR:.0f}s  N={N}\n")
print(f"{'素材':<10}{'臂':<10}{'探针':>6}{'挂陷':>6}{'弃权':>6}{'弃权率':>8}"
      f"{'ext':>6}{'howl':>6}{'门拦':>6}{'仪表故障':>9}{'平台占用':>9}{'其中b1':>8}")
res={}
for nm,mk in [('钢琴',S.m_piano),('多人交谈',S.m_multitalk)]:
    for on in (False,True):
        T={k:0 for k in ['probe','ab','ex','hw','eng','blk','flt']}; O=[];B=[]
        for sd in range(N):
            r=trial(mk,sd,on)
            for k in T: T[k]+=r[k]
            O.append(r['occ']); B.append(r['b1'])
        rate=T['ab']/max(T['probe'],1)*100
        res[(nm,on)]=(T,np.mean(O),np.mean(B),rate)
        print(f"{nm:<10}{'开(P0)' if on else '关(对照)':<10}{T['probe']:>6}{T['eng']:>6}"
              f"{T['ab']:>6}{rate:>7.1f}%{T['ex']:>6}{T['hw']:>6}{T['blk']:>6}{T['flt']:>9}"
              f"{np.mean(O):>9.2f}{np.mean(B):>8.2f}")
        sys.stdout.flush()
print("\n"+"="*92)
print("【预注册四条证伪条件逐条判】")
for nm in ['钢琴','多人交谈']:
    T0,O0,B0,r0=res[(nm,False)]; T1,O1,B1,r1=res[(nm,True)]
    d_ab=r0-r1
    d_eng=(T0['eng']-T1['eng'])/max(T0['eng'],1)*100
    d_ext=(T0['ex']-T1['ex'])/max(T0['ex'],1)*100
    print(f"\n  【{nm}】")
    print(f"   ① 弃权率 {r0:.1f}% → {r1:.1f}%(降 {d_ab:.1f}pp)  "
          f"{'**证伪:降幅<10pp ⇒ 归因错**' if d_ab<10 else '✓ 预期成立'}")
    print(f"   ② 挂陷总数 {T0['eng']} → {T1['eng']}(降 {d_eng:.1f}%) vs 弃权率降幅 {d_ab:.1f}pp  "
          f"{'**证伪:挂陷降幅≥弃权降幅 ⇒ 门过强**' if d_eng>=d_ab else '✓ 门未过强'}")
    print(f"   ③ **阴性对照** verdict_ext {T0['ex']} → {T1['ex']}(变 {-d_ext:+.1f}%)  "
          f"{'**证伪:ext 显著下降 ⇒ 门的形式错**' if d_ext>20 else '✓ 阴性对照通过'}")
    print(f"   ④ 平台占用 {O0:.2f} → {O1:.2f}  其中 b1 {B0:.2f} → {B1:.2f}  "
          f"{'**证伪:占用未降 ⇒ 与 r22 b1=85.5% 矛盾**' if O1>=O0 else '✓ 占用下降'}")
    print(f"   · verdict_howl {T0['hw']} → {T1['hw']}  ⚠ **按预注册不作判据**(基数过小)")
