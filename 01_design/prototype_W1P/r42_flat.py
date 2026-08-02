"""r42:平坦衰减扫描 —— 新尺子(甲)+ 空对照(乙);并测「覆盖 vs 对准」(③)。
ΔMSG_flat(A) = A 是解析恒等式 ⇒ 差分测量,系统误差抵消。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
FRAME=64; STEP=0.5; T_OBS=6.0; GR={'out_lim_active':False,'out_lim_gr_db':0.0}
def src_of(T,seed): return 1e-3*np.random.default_rng(seed).standard_normal(int(T*FS))
def ref_db(T,seed):
    s=src_of(T,seed); n=(len(s)//FRAME)*FRAME; return HD.rms_db(s[:n])
def howls(h,D,G,pf,T,seed):
    lp=clrig.Loop(h,D,G,proc=pf()); _,loop=lp.run(src_of(T,seed),FRAME)
    return HD.is_howling(loop, ref_db(T,seed), FS, FRAME)[0]
def msg(h,D,pf,T,seed,lo=-40.,hi=25.):
    G=lo; last=lo
    while G<=hi:
        if howls(h,D,G,pf,T,seed): return last
        last=G; G+=STEP
    return float('inf')
def flat_proc(A_db):
    g=10**(-A_db/20.0)
    return lambda: (lambda blk: blk*g)
def notch_proc(k,h):
    def f():
        a=NHS(); fc,mdb=clrig.critical_points(clrig.h_eff(h)); order=np.argsort(mdb)[::-1]
        for i in range(min(k,len(a.slots))):
            s=a.slots[i]; s.st=nhs.NotchSlot.HOLD; s.f=float(fc[order[i]])
            s.depth=a.P.max_depth; s.target=a.P.max_depth; s.set_coef(FS,a.P.bw_oct)
        a.P.T_low=999.
        return lambda blk: a.process_frame(blk,GR)
    return f

print("r42 · 平坦衰减扫描(新尺子 + 空对照)")
print(f"[L2/宿主仿真] 阶梯={STEP}dB T={T_OBS}s\n")
print("【甲 新尺子】ΔMSG_flat(A) 应 = A,斜率应 = 1.00")
print(f"{'T60':>5}{'seed':>5}{'MSG@A=0':>9}" + "".join(f"{'A='+str(a):>8}" for a in [1,2,3,6,10]))
xs=[];ys=[]
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        m0=msg(h,D,lambda:None,T_OBS,sd)
        row=[]
        for A in [1,2,3,6,10]:
            mA=msg(h,D,flat_proc(A),T_OBS,sd)
            row.append(mA-m0); xs.append(A); ys.append(mA-m0)
        print(f"{T60:>5.1f}{sd:>5}{m0:>9.2f}" + "".join(f"{v:>8.2f}" for v in row))
        sys.stdout.flush()
xs=np.array(xs,float); ys=np.array(ys,float)
A_=np.vstack([xs,np.ones(len(xs))]).T
sl,ic=np.linalg.lstsq(A_,ys,rcond=None)[0]
res=ys-(A_@np.array([sl,ic]))
print(f"\n   **斜率 = {sl:.4f}**(应 1.00,门 |slope−1|≤0.10)  截距 = {ic:+.3f} dB  "
      f"残差 σ = {res.std():.3f} dB(门 ≤0.5)")
print(f"   ⇒ {'**斜率通过 ⇒ 刻度准**' if abs(sl-1)<=0.10 else '**斜率不过 ⇒ 台架有 bug**'}"
      f" | {'截距≈0' if abs(ic)<0.3 else f'**截距有偏 {ic:+.2f}dB ⇒ 可标定,从所有 MSG 读数扣除**'}")

print("\n【乙 空对照】陷波臂 vs 平坦臂,同图读出「8 个陷波 ≈ 降低增益 X dB」")
print(f"{'T60':>5}{'seed':>5}{'ΔMSG(8陷波)':>13}{'等效平坦 X':>12}")
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        m0=msg(h,D,lambda:None,T_OBS,sd); m8=msg(h,D,notch_proc(8,h),T_OBS,sd)
        d=m8-m0; X=(d-ic)/sl if sl else float('nan')
        print(f"{T60:>5.1f}{sd:>5}{d:>13.2f}{X:>12.2f}")
        sys.stdout.flush()

print("\n【③ 覆盖 vs 对准】一个陷波实际压低了几个临界点?")
for T60 in [0.2,0.5]:
    h,_=clrig.make_F(T60=T60,delay_ms=8.,seed=0)
    fc,mdb=clrig.critical_points(clrig.h_eff(h)); j=int(np.argmax(mdb)); f0=float(fc[j])
    P=nhs.Params(); bw=max(f0*P.bw_oct,15.)
    ncov=int(((fc>f0-bw/2)&(fc<f0+bw/2)).sum())
    sp=np.median(np.diff(np.sort(fc)))
    print(f"   T60={T60}: 目标 f0={f0:.1f}Hz  陷波带宽={bw:.1f}Hz  "
          f"**带宽内临界点数={ncov}**  临界点中位间距={sp:.1f}Hz")
    print(f"            频率精度 3.75Hz 相对: 间距 {3.75/sp*100:.0f}% / 带宽 {3.75/bw*100:.1f}%"
          f"  ⇒ {'**靠覆盖(带宽内多点)⇒ 频率精度非瓶颈**' if ncov>=3 else '靠对准 ⇒ 频率精度是瓶颈'}")
