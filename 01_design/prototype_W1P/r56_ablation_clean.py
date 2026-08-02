"""r56 · 消融干净性检验(r55 的**预注册证伪条件被触发**,必须独立查,不许解释掉)

r55 报出:消融臂 `duck最深(消)` 六条全 0.00。而 r55 文件头预注册写死:
  「若消融臂 g_duck 恒 0 ⇒ 说明我切断的不止是音频作用,消融不干净,结论作废」。
⇒ 现在必须**独立证明**消融臂的 duck 状态机仍在跑,而不是事后解释。

竞争解释(两条,必须用同一组读数分开判):
  E1 · 消融是干净的,`duck最深(消)` 为 0 只是**取数点**造成的:r55 报的是
       "最后一个**不起振**的 G"上的 g_duck;没有 duck 保护 ⇒ 该 G 上环路根本没长起来
       ⇒ 没有带外啸叫 ⇒ 没有混叠幻峰 ⇒ 没有 EXHAUSTED ⇒ g_duck 本就该是 0。
  E2 · 消融不干净:`alg.duck_gain = lambda: 1.0` 意外改变了状态演化 ⇒ 状态机死了。

判据(先写死):在**带 duck 臂曾观察到 duck 活动**的那些 G 上,直接跑消融臂:
  · 若消融臂 g_duck 仍 **< 0** ⇒ 状态机活着 ⇒ **E1 立、E2 死 ⇒ r55 结论有效**;
  · 若消融臂 g_duck 恒 **== 0** ⇒ **E2 立 ⇒ r55 结论作废**,须换消融手法重做。
附证(同一次跑,不另设判据):消融臂在这些 G 上应**起振**(音频作用确已被切断)。
[L2/宿主仿真]  deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316
               howl_detect.py@fd63e901f2d8be33
"""
import sys; sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
FRAME=64; T_OBS=6.0; GR={'out_lim_active':False,'out_lim_gr_db':0.0}; P=nhs.Params()
O=[]
def W(s):
    O.append(s); print(s); sys.stdout.flush()
def pick_excl(he,k=8):
    fc,mdb=clrig.critical_points(he); o=list(np.argsort(mdb)[::-1]); picks=[]; used=np.zeros(len(fc),bool)
    for i in o:
        if used[i] or len(picks)>=k: continue
        f_=float(fc[i]); picks.append(f_); used|=(np.abs(fc-f_)<=max(f_*P.bw_oct,15.))
    return picks
def mk_alg(picks,no_duck):
    a=NHS()
    for i,f_ in enumerate(picks[:len(a.slots)]):
        s=a.slots[i]; s.st=nhs.NotchSlot.HOLD; s.f=f_; s.depth=a.P.max_depth
        s.target=a.P.max_depth; s.set_coef(FS,a.P.bw_oct)
    a.P.T_low=999.
    if no_duck: a.duck_gain=lambda: 1.0
    return a
T60,sd=0.2,0
h,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd); he=clrig.h_eff(h)
picks=pick_excl(he,8)
src=1e-3*np.random.default_rng(sd).standard_normal(int(T_OBS*FS))
ref=HD.rms_db(src[:(len(src)//FRAME)*FRAME])
W("r56 · 消融干净性检验  T60=0.2 seed=0  T_OBS=6.0s FRAME=64")
W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 howl_detect.py@fd63e901f2d8be33")
W("[L2/宿主仿真] 判据见文件头 E1/E2(跑前落盘)")
W("")
W(f"{'G(dB)':>8}{'臂':>10}{'起振?':>7}{'帧RMS峰':>10}{'g_duck最深':>12}{'g_duck末':>10}{'EXH事件':>9}{'主导频率':>11}")
res={}
for G in (-8.54,-7.04,-6.04,-5.04):
    for nm,nd in (('带duck',False),('消融',True)):
        a=mk_alg(picks,nd); rec=[]
        def pf(blk,_a=a,_r=rec):
            y=_a.process_frame(blk,GR); _r.append(_a.g_duck_db); return y
        _,lp=clrig.Loop(h,D,G,proc=pf).run(src,FRAME)
        hw,lvmax,_=HD.is_howling(lp,ref,FS,FRAME)
        gd=np.array(rec); n=int(FS)
        Xf=np.abs(np.fft.rfft(lp[-n:]*np.hanning(n)))
        ft=float(np.fft.rfftfreq(n,1/FS)[int(np.argmax(Xf))])
        ex=len([e for e in a.events if e[1] in ('SLOTS_EXHAUSTED','DEPTH_EXHAUSTED')])
        res[(G,nm)]=(float(gd.min()),hw)
        W(f"{G:>8.2f}{nm:>10}{('YES' if hw else 'no'):>7}{lvmax:>10.1f}{gd.min():>12.2f}{gd[-1]:>10.2f}{ex:>9d}{ft:>11.1f}")
W("")
abl=[res[(G,'消融')][0] for G in (-8.54,-7.04,-6.04,-5.04)]
hws=[res[(G,'消融')][1] for G in (-8.54,-7.04,-6.04,-5.04)]
W(f"消融臂 g_duck 最深值 = {[round(x,2) for x in abl]}")
if any(x<0 for x in abl):
    W("⇒ **E1 立、E2 死**:消融臂的 duck 状态机仍在跑(g_duck 达到负值),")
    W("   r55 报的 0.00 只是取数点(最后一个不起振 G)造成 ⇒ **r55 结论有效**。")
else:
    W("⇒ **E2 立**:消融破坏了状态机 ⇒ **r55 结论作废**,须换消融手法重做。")
W(f"附证:消融臂在这些 G 上起振 = {hws}(音频作用确已切断 ⇒ 不再被 duck 救)")
open('/home/it1234/processor/01_design/prototype_W1P/r56_ablation_clean_out.txt','w').write("\n".join(O)+"\n")
