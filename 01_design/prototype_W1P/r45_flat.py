"""r45:平坦衰减扫描(修正挂陷频点 + **按臂缩窗**)。
⭐ 窗口必须**按臂**算,含预期抬升 —— 否则会把要测的东西挡在窗外:
   基线臂  [ana−6, ana+6]
   平坦臂A [ana+A−6, ana+A+6]
   陷波臂k [ana−6, ana+pred_iter+6]   ← **下界不抬**
   ⚠ 陷波臂窗口**不对称,这是必须的**:挂第一个陷波可能让 MSG **下降**(上界约 Δ=1.4dB),
     下界跟着抬就测不到"变差"那一侧了。
⚠ **保留线性阶梯,不改二分 —— 两条理由,第二条更硬**:
   (1) **鲁棒性**:接近 MSG 时"是否发散"的判定本身是噪声的(已确认的物理)。
       二分对单次误判无恢复能力——走错一支就回不来;线性阶梯对单次误判只偏一步。
   (2) ⭐ **独立性**:本设计的窗口上界 = 解析MSG + **迭代式预测** + 6dB ⇒ **窗口位置含预测值**。
       **二分从【中点】起搜,而中点位置含预测值 ⇒ 二分会把预测值引入测量过程 ⇒ 假吻合(D 侧)。**
       线性阶梯从**下界**起单向向上 ⇒ 上界仅能**截断**,截断由边界断言捕获 ⇒ 独立性成立。
   ⇒ 阶梯的鲁棒性是用时间买来的;**独立性则是这个窗口设计下的必要条件,不可交易。**
⚠ 命中边界 ⇒ 判**窗口不足、结果无效**,**留痕并进报告**;**不自动加宽重试**
   (自动重试会把"我们对该臂的预期偏了多少"这个信息抹掉)。
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
FRAME=64; STEP=0.5; T_OBS=6.0; GR={'out_lim_active':False,'out_lim_gr_db':0.0}
BOUND_HITS=[]
def src_of(T,seed): return 1e-3*np.random.default_rng(seed).standard_normal(int(T*FS))
def ref_db(T,seed):
    s=src_of(T,seed); n=(len(s)//FRAME)*FRAME; return HD.rms_db(s[:n])
def howls(h,D,G,pf,T,seed):
    lp=clrig.Loop(h,D,G,proc=pf()); _,loop=lp.run(src_of(T,seed),FRAME)
    return HD.is_howling(loop, ref_db(T,seed), FS, FRAME)[0]
def msg(h,D,pf,T,seed,lo,hi,tag=''):
    G=lo; last=None
    while G<=hi+1e-9:
        if howls(h,D,G,pf,T,seed):
            if last is None:
                BOUND_HITS.append((tag,'下界',lo,hi)); return float('nan')
            return last
        last=G; G+=STEP
    BOUND_HITS.append((tag,'上界',lo,hi)); return float('nan')
def flat_proc(A): 
    g=10**(-A/20.); return lambda: (lambda blk: blk*g)
def notch_proc(k,h):
    def f():
        a=NHS(); fc,mdb=clrig.critical_points(clrig.h_eff(h)); order=np.argsort(mdb)[::-1]
        for i in range(min(k,len(a.slots))):
            s=a.slots[i]; s.st=nhs.NotchSlot.HOLD; s.f=float(fc[order[i]])
            s.depth=a.P.max_depth; s.target=a.P.max_depth; s.set_coef(FS,a.P.bw_oct)
        a.P.T_low=999.
        return lambda blk: a.process_frame(blk,GR)
    return f
print("r45 · 平坦扫描(修正挂陷 + 按臂缩窗)")
print(f"[L2/宿主仿真] 阶梯={STEP}dB T={T_OBS}s  窗口按臂算,陷波臂**下界不抬**\n")
print(f"{'T60':>5}{'seed':>5}{'解析':>8}{'基线MSG':>9}" + "".join(f"{'A='+str(a):>7}" for a in [1,2,3,6,10]) + f"{'Δ8陷波':>9}{'预测迭代':>9}{'等效X':>8}")
xs=[];ys=[]
for T60 in [0.2,0.5]:
    for sd in [0,1,2]:
        h,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        he=clrig.h_eff(h); ana,_=clrig.analytic_msg_db(he)
        m0=msg(h,D,lambda:None,T_OBS,sd,ana-6,ana+6,f'{T60}/{sd}/base')
        row=[]
        for A in [1,2,3,6,10]:
            mA=msg(h,D,flat_proc(A),T_OBS,sd,ana+A-6,ana+A+6,f'{T60}/{sd}/flat{A}')
            d=mA-m0 if np.isfinite(mA) and np.isfinite(m0) else float('nan')
            row.append(d)
            if np.isfinite(d): xs.append(A); ys.append(d)
        pi,_=clrig.predict_dmsg_iter(he,8)
        m8=msg(h,D,notch_proc(8,h),T_OBS,sd,ana-6,ana+pi+6,f'{T60}/{sd}/notch8')
        d8=m8-m0 if np.isfinite(m8) and np.isfinite(m0) else float('nan')
        print(f"{T60:>5.1f}{sd:>5}{ana:>8.2f}{m0:>9.2f}" + "".join(f"{v:>7.2f}" for v in row)
              + f"{d8:>9.2f}{pi:>9.2f}{d8:>8.2f}")
        sys.stdout.flush()
if xs:
    A_=np.vstack([np.array(xs,float),np.ones(len(xs))]).T; yv=np.array(ys,float)
    sl,ic=np.linalg.lstsq(A_,yv,rcond=None)[0]; res=yv-(A_@np.array([sl,ic]))
    print(f"\n【甲 改动局部性对照 + 新尺子】斜率={sl:.4f}(应1.00) 截距={ic:+.3f} 残差σ={res.std():.3f}")
print(f"\n【边界命中留痕】共 {len(BOUND_HITS)} 次" + (" —— **无**" if not BOUND_HITS else ":"))
for t in BOUND_HITS: print(f"   {t[0]:<22} 命中{t[1]}  窗口[{t[2]:.2f},{t[3]:.2f}]  ⇒ **该点无效**")
