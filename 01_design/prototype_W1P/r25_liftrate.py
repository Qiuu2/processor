"""r25 ③:`lift_after` 的**作用率**(每缩 1s 减多少槽·秒/秒)。
架构侧纠正:**不能相加的是【基数】,不是【系数】** ⇒ 作用率是机制的性质,**不受 P0 影响,现在就能估**。
⚠ 反向压力如实记:P0 若有效 ⇒ b1 下降 ⇒ **`lift_after` 的绝对收益比现在看起来小**。
[L2/宿主仿真·合成料]
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, nhs, fp_suite as S
from nhs import NHS, FRAME, NotchSlot
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
OCC=(NotchSlot.ENGAGE,NotchSlot.HOLD,NotchSlot.LIFT,NotchSlot.STANDBY)
LA=[60.0,45.0,30.0,15.0]; DUR=200.0; N=5
print("r25 ③ · lift_after 作用率(直接测量,不用模型)")
print(f"[L2/宿主仿真·合成料] 窗={DUR:.0f}s N={N} 钢琴  **P0 门已在代码中,故为 P0 后的基数**\n")
print(f"{'lift_after':>11}{'平台段占用均值':>15}{'其中b1(弃权)':>14}{'弃权数':>8}")
xs,ys,bs=[],[],[]
for la in LA:
    occ=[];b1=[];ab=0
    for sd in range(N):
        a=NHS(); a.P.lift_after_s=la
        mat=S.m_piano(DUR,1000+sd); n=(len(mat)//FRAME)*FRAME
        acc=[];acc1=[]
        for i in range(0,n,FRAME):
            a.process_frame(mat[i:i+FRAME],GR)
            if i%(FRAME*12)==0 and a.t_wall>=150.0:
                o=[s for s in a.slots if s.st in OCC]
                acc.append(len(o)); acc1.append(sum(1 for s in o if s.from_abstain))
        occ.append(np.mean(acc) if acc else 0); b1.append(np.mean(acc1) if acc1 else 0)
        ab+=a.ctr.get('c8_abstain',0)
    xs.append(la); ys.append(np.mean(occ)); bs.append(np.mean(b1))
    print(f"{la:>11.0f}{np.mean(occ):>15.2f}{np.mean(b1):>14.2f}{ab:>8}")
    sys.stdout.flush()
x=np.array(xs); y=np.array(ys); b=np.array(bs)
for lbl,v in [('总占用',y),('b1 弃权占用',b)]:
    A=np.vstack([x,np.ones(len(x))]).T
    sl,ic=np.linalg.lstsq(A,v,rcond=None)[0]
    r=v-(A@np.array([sl,ic])); ss=float((r*r).sum()); st=float(((v-v.mean())**2).sum())
    print(f"\n  【{lbl}】线性拟合 vs lift_after:")
    print(f"     **作用率 = {sl:.4f} 槽 / 每秒 lift_after**  (R²={1-ss/st if st>0 else float('nan'):.4f})")
    print(f"     ⇒ 每缩短 1s lift_after,平台段占用减少 **{sl:.4f} 槽**;缩 30s 减 **{sl*30:.2f} 槽**")
print("\n⚠ 作用率是**机制性质**,不随基数变;**绝对收益 = 作用率 × 基数**,而基数将被 P0 压低。")
