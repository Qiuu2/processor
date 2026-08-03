"""r74 · **源电平敏感性扫描** —— 把一个拿不到的常数变成一根曲线(lead 裁定)。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r74_srclevel_out.txt (D6-j)
deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18 howl_detect.py@fd63e901f2d8be33
      msg_meter.py@a0c16fd22b29f083 r57_bandlimit.py@74036010b514080d

════════════════════════════════════════════════════════════════════
⚠ lead 点的那个坑:**扫源电平 = 一次动三个门**
════════════════════════════════════════════════════════════════════
源电平平移 ΔL ⇒ 检测器输入整体平移 ΔL ⇒ **等价于三个绝对门同时平移 −ΔL**
(`T_low = −45` / `T_low_gr = −65` / `T_panic = −6`)⇒ 与 `bw_oct` 那次"一次改两个变量"同型。
**⇒ 我判【需要拆】,而拆法是现成的**:
  `nhs.py:67` `T_low_gr` 在 `Params.__init__` 就按 `T_low − 20` **算死**,
  **构造后改 `P.T_low` 不会重算它**(这正是 B-1 那条勘正查明的性质)
  ⇒ **`a.P.T_low = X` 天然就是「只动 T_low,另两门不动」** ⇒ 臂 T 零成本。

臂:
  m0    proc=None                 ⇒ **兼作标度不变性对照**:MSG 由环路增益决定,
                                     **理应对源电平不变**;若它随源电平漂 ⇒ 台架有问题(D6-d)
  N     NHS 自选 + duck 不消融     ⇒ 产品实际
  Na    NHS 自选 + duck 消融       ⇒ 陷波真实贡献
  T     固定源电平,只扫 `P.T_low ∈ {−45(实现), −50(字典)}` ⇒ **拆开"三门齐动"的混淆**

预注册(跑前落盘):
  Hn1 · **m0 对源电平不变**(标度不变性)。证伪:m0 随源电平变化 >1 阶梯 ⇒ 台架有问题,整轮作废。
  Hn2 · **过门率随源电平单调上升**。同时报之,因为它是"敏感与否"的判据。
        ⚠ 过门率接近 0 或接近 100% 的档,其 ΔMSG **不可比**,单列不进结论(lead 要求 2)。
  Hn3 · **B-1 那个 1.00–2.50 对源电平有多敏感** —— 逐档报 ΔMSG。
        若跨档极差 ≤ 1 阶梯(0.5 dB)⇒ B-1 结论存活,只是多一个已验维度;
        若极差 ≫ 0.5 ⇒ **B-1 的数必须带源电平限定**。
  Hn4 · **PANIC 何时开始动作** —— 逐档报触发数(它在 −6 dBFS,高源电平档可能进入新regime)。
  Hn5 · 臂 T:`T_low` 两档的差,与"等效源电平平移 5 dB"的差**是否一致**
        ⇒ 一致 ⇒ 三门齐动的混淆可忽略;不一致 ⇒ 必须拆开报。
⚠ **算力截断(显式留痕)**:`T_OBS = 6 s` 单档,不做 F36 阶梯。
  理由:本轮问的是**跨源电平的相对变化**(配对差),不是绝对值;⛔ 故本轮数**不得当绝对值引用**。
⛔ 结论行看到数之后再写;若修法/门值效果在不同源电平上**变号**,⛔ 不得平均掉(lead 要求 3)。
"""
import sys, numpy as np
sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import clrig, howl_detect as HD, nhs
from nhs import NHS, NotchSlot
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
FRAME,BW,STEP,T_OBS=64,1/5,0.5,6.0
SEEDS=[(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
SRC_DB=[-70.,-60.,-50.,-40.,-30.]      # −60 = 现值(1e-3·N(0,1) 的 RMS)
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()

def src_of(sd, lvl_db):
    x=np.random.default_rng(sd).standard_normal(int(T_OBS*FS))
    return x*(10**(lvl_db/20.))          # N(0,1) 的 RMS=1 ⇒ 直接乘即得目标 RMS

def mk(ablate, t_low=None):
    a=NHS(); a.P.bw_oct=BW
    if t_low is not None: a.P.T_low=t_low   # ⇒ T_low_gr 不重算(nhs.py:67 已算死)
    if ablate: a.duck_gain=lambda: 1.0
    return a

def scan(hb,D,mkf,lo,hi,src,ref):
    G,last,st=lo,None,None
    while G<=hi+1e-9:
        a=mkf(); 
        pf=None
        if a is not None:
            def pf(b,_a=a): return _a.process_frame(b,GR)
        _,lp=clrig.Loop(hb,D,G,proc=pf).run(src,FRAME)
        if HD.is_howling(lp,ref,FS,FRAME)[0]:
            return (float('nan') if last is None else last), st
        last=G
        if a is not None:
            u=[s for s in a.slots if s.st!=NotchSlot.FREE]
            st=dict(n=len(u), fr=sorted(round(float(s.f),1) for s in u),
                    n1=int(a.ctr.get('N1_cand',0)), n2=int(a.ctr.get('N2_lvl',0)),
                    panic=int(a.ctr.get('N5_howl',0)), gmin=0.0)
        G+=STEP
    return float('nan'), st

def top1(fr,picks):
    if not picks or not fr: return False
    t=float(picks[0]); return any(abs(f-t)<=max(t*BW,15.)/2 for f in fr)

def main():
    W("未经 critic 评审 —— r74 · 源电平敏感性扫描(把常数变成曲线)  [L2/宿主仿真]")
    W("deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18")
    W("⚠ 算力截断(显式):T_OBS=6s 单档,不做 F36 阶梯 ⇒ ⛔ 本轮数不得当绝对值引用,只作跨档比较")
    W("⚠ 扫源电平 = **三个绝对门同时平移**(T_low/T_low_gr/T_panic)⇒ 臂 T 用于拆开")
    W("")
    W("%6s%5s%4s | %8s%10s%10s | %9s%8s%8s%9s"%('源dBFS','T60','sd',
      'm0','ΔMSG_有duck','ΔMSG_消融','过门率','挂陷','top1','N5_howl'))
    env={}
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        env[(T60,sd)]=(hb,D,pick_excl(he,BW,8),
                       MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db'])
    tab={}
    for L in SRC_DB:
        for (T60,sd) in SEEDS:
            hb,D,picks,anchor=env[(T60,sd)]
            src=src_of(sd,L); ref=HD.rms_db(src[:(len(src)//FRAME)*FRAME])
            m0,_=scan(hb,D,lambda: None, anchor-3, anchor+4, src, ref)
            mn,stn=scan(hb,D,lambda: mk(False), anchor-1, anchor+20, src, ref)
            ma,sta=scan(hb,D,lambda: mk(True),  anchor-1, anchor+20, src, ref)
            dn=mn-m0 if np.isfinite(mn) and np.isfinite(m0) else float('nan')
            da=ma-m0 if np.isfinite(ma) and np.isfinite(m0) else float('nan')
            rate=(stn['n2']/stn['n1']) if (stn and stn['n1']) else float('nan')
            tab.setdefault(L,[]).append((T60,sd,m0,dn,da))
            W("%6.0f%5.1f%4d | %8.2f%10.2f%10.2f | %8.2f%%%8d%8s%9d"%(L,T60,sd,m0,dn,da,
              100*rate, stn['n'] if stn else -1,
              str(top1(stn['fr'],picks)) if stn else '-', stn['panic'] if stn else -1))
        W("")
    W("="*100); W("§S 汇总"); W("="*100)
    for L in SRC_DB:
        v=[x[3] for x in tab[L] if np.isfinite(x[3])]
        m=[x[2] for x in tab[L] if np.isfinite(x[2])]
        if v: W("  源 %6.0f dBFS: ΔMSG_有duck 逐条 %s  极差 %.2f | m0 逐条 %s"%(
            L,[round(x,2) for x in v],max(v)-min(v),[round(x,2) for x in m]))
    W("")
    W("  Hn1 标度不变性:各源电平下 m0 逐条见上;⚠ 若跨源电平变化 >1 阶梯 ⇒ 台架有问题")
    W("  Hn3 B-1 敏感性:比较各档 ΔMSG_有duck 的逐条值 ⇒ 判 B-1 那个 1.00–2.50 要不要带源电平限定")
    W("")
    W("="*100); W("臂 T · 只动 T_low(源电平固定 −60,T_low_gr/T_panic 不动)—— 拆开三门齐动"); W("="*100)
    W("%8s%5s%4s | %10s%10s%9s%8s"%('T_low','T60','sd','ΔMSG_有duck','ΔMSG_消融','过门率','挂陷'))
    for tl in (-45.,-50.):
        for (T60,sd) in SEEDS:
            hb,D,picks,anchor=env[(T60,sd)]
            src=src_of(sd,-60.); ref=HD.rms_db(src[:(len(src)//FRAME)*FRAME])
            m0,_=scan(hb,D,lambda: None, anchor-3, anchor+4, src, ref)
            mn,stn=scan(hb,D,lambda: mk(False,tl), anchor-1, anchor+20, src, ref)
            ma,_ =scan(hb,D,lambda: mk(True,tl),  anchor-1, anchor+20, src, ref)
            dn=mn-m0 if np.isfinite(mn) and np.isfinite(m0) else float('nan')
            da=ma-m0 if np.isfinite(ma) and np.isfinite(m0) else float('nan')
            rate=(stn['n2']/stn['n1']) if (stn and stn['n1']) else float('nan')
            W("%8.0f%5.1f%4d | %10.2f%10.2f%8.2f%%%8d"%(tl,T60,sd,dn,da,100*rate,
              stn['n'] if stn else -1))
        W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r74_srclevel_out.txt','w').write("\n".join(O)+"\n")

if __name__=='__main__': main()
