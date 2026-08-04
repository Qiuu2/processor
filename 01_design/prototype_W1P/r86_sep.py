"""r86 · 机制 B 分离 + 第一次修法试探。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r86.txt。⛔ 验收判据 = **深度分布**,不用挂陷数(lead 限定③)。"""
import sys, json, glob, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME
DIR='/home/it1234/processor/01_design/prototype_W1P/'; T,SRC=12.0,-20.; F=0.354; OUT=[]
def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()
def run(hb,D,G,src,fix,rf):
    a=NHS(); a.P.bw_oct=1/5; a.P.T_low=-45.
    a.P.prefer_unnotched=bool(fix); a.P.recheck_free=bool(rf); a.duck_gain=lambda:1.0
    clrig.Loop(hb,D,G,proc=lambda b,_a=a:_a.process_frame(b,GR)).run(src,FRAME)
    u=[s for s in a.slots if s.st!=nhs.NotchSlot.FREE]
    d=sorted(round(float(s.depth),2) for s in u)
    return dict(depths=d, n=len(u), med=(float(np.median(d)) if d else float('nan')),
                tot=float(sum(d)), preempt=int(a.ctr.get('preempt',0)),
                A3=int(a.ctr.get('A3_deepen_real',0)), F3=int(a.ctr.get('F3_dropped',0)))
def main():
    t0=time.time(); R=[]
    for p in glob.glob(DIR+'r76_cell_*.json'): R+=json.load(open(p))
    K={(r['src'],r['fix'],r['tlow'],r['T60'],r['sd'],r['T']):r for r in R}
    W("未经 critic 评审 —— r86 · 机制B分离 + 修法试探  [L2/宿主仿真]  预注册 = PREREG_r86.txt")
    W("开关 `recheck_free`:复检不消耗槽 ⇒ 不占名额(默认关;逐位等价 12/12,阳性对照 8/12 已证)")
    W("⛔ 验收判据 = **深度分布**(挂陷数在这件事上无分辨力:8→8 而 ΔMSG 掉 3.5)")
    W("⛔ 逐种子报,不报聚合(D6-ar)")
    W("")
    SE=[(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
    TAG={(0.2,0):'抖动种子(唯一满槽)',(0.5,0):'机制B种子(零抢占却变浅)',
         (0.5,2):'机制B种子(零抢占却变浅)'}
    rows=[]
    W(f"{'T60/sd':>8}{'臂':>22}{'挂陷':>5}{'抢占':>7}{'深度中位':>10}{'深度总和':>10}  深度分布")
    for (T60,sd) in SE:
        rec=K.get((SRC,0,-45.,T60,sd,T))
        if rec is None or not np.isfinite(rec['dA']): continue
        h0,Dp=clrig.make_F(T60=T60,prop_delay_ms=8.,seed=sd); hb=band_limit(h0,8000.)
        s=np.random.default_rng(sd).standard_normal(int(T*FS))*(10**(SRC/20.))
        G=rec['m0']+rec['dA']
        cur={}
        for (fix,rf,nm) in ((0,0,'基线(修法关)'),(1,0,'prefer_unnotched 开'),
                            (0,1,'**recheck_free 开**'),(1,1,'两个都开')):
            c=run(hb,Dp,G,s,fix,rf)
            W(f"{T60}/{sd:<6}{nm:>22}{c['n']:>5}{c['preempt']:>7}{c['med']:>10.2f}{c['tot']:>10.2f}  {c['depths']}")
            cur[(fix,rf)]=c
            c.update(T60=T60,sd=sd,fix=fix,rf=rf); rows.append(c)
        W(f"{'':>8}{TAG.get((T60,sd),'(深度差不可判的对照种子)'):>22}")
        W("")
    W("="*112); W("§H 预注册假设逐条对表"); W("="*112)
    def get(t,s,fix,rf):
        v=[r for r in rows if r['T60']==t and r['sd']==s and r['fix']==fix and r['rf']==rf]
        return v[0] if v else None
    W("  Hf1 机制B分离:两条零抢占种子上,开 recheck_free 后「修法开 vs 关」的深度差是否消失")
    for (t,s) in [(0.5,0),(0.5,2)]:
        a=get(t,s,0,0); b=get(t,s,1,0); c=get(t,s,0,1); d=get(t,s,1,1)
        if not all([a,b,c,d]): continue
        d0=b['med']-a['med']; d1=d['med']-c['med']
        W(f"    T60={t} sd={s}: recheck_free 关时 深度差 {d0:+.2f} ｜ 开时 {d1:+.2f}"
          f"  ⇒ {'**差消失/缩小 ⇒ Hf1 支持**' if abs(d1)<F<=abs(d0) else ('**差未消失 ⇒ Hf1 证伪**' if abs(d1)>=F else '(两侧都不可判)')}")
    W("")
    W("  Hf2 不得伤及无辜:三条不可判种子在 recheck_free 下深度不得变浅(>底即判有害)")
    for (t,s) in [(0.2,1),(0.2,2),(0.5,1)]:
        a=get(t,s,0,0); c=get(t,s,0,1)
        if not a or not c: continue
        dd=c['med']-a['med']
        W(f"    T60={t} sd={s}: 基线 {a['med']:.2f} → recheck_free {c['med']:.2f}  差 {dd:+.2f}"
          f"  ⇒ {'⛔ **变浅,有害**' if dd>F else ('✅ 变深' if dd<-F else '✅ 不可判(无害)')}")
    W("")
    W("  Hf3 抖动种子(⛔ 不预测方向):B 是否放大 A")
    a=get(0.2,0,0,0); c=get(0.2,0,0,1)
    if a and c:
        W(f"    抢占 {a['preempt']} → {c['preempt']} ｜ 深度中位 {a['med']:.2f} → {c['med']:.2f}"
          f"  ⇒ {'**抢占上升且变浅 ⇒ 冲突被坐实**' if (c['preempt']>a['preempt'] and c['med']-a['med']>F) else '(未同时满足冲突签名)'}")
    W("")
    W("  ⭐ 修法试探(recheck_free 单开 vs 基线)逐种子深度中位:")
    for (t,s) in SE:
        a=get(t,s,0,0); c=get(t,s,0,1)
        if not a or not c: continue
        dd=c['med']-a['med']
        W(f"    T60={t} sd={s}: {a['med']:.2f} → {c['med']:.2f}  Δ{dd:+.2f}"
          f"  {'**更深(好)**' if dd<-F else ('**更浅(坏)**' if dd>F else '(不可判)')}")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    open(DIR+'r86_sep_out.txt','w').write("\n".join(OUT)+"\n")
    json.dump(rows, open(DIR+'r86_sep.json','w'))
if __name__=='__main__': main()
