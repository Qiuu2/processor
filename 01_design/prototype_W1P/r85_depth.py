"""r85 · 量深度分布。⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r85.txt。
⛔ 本轮只量不修;不含结论性散文,不含修法。"""
import sys, json, glob, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME
DIR='/home/it1234/processor/01_design/prototype_W1P/'; T,SRC=12.0,-20.; OUT=[]
def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()
def run(hb,D,G,src,fix):
    a=NHS(); a.P.bw_oct=1/5; a.P.T_low=-45.
    a.P.prefer_unnotched=bool(fix); a.duck_gain=lambda:1.0
    clrig.Loop(hb,D,G,proc=lambda b,_a=a:_a.process_frame(b,GR)).run(src,FRAME)
    used=[s for s in a.slots if s.st!=nhs.NotchSlot.FREE]
    return dict(depths=sorted(round(float(s.depth),2) for s in used),
                targets=sorted(round(float(s.target),2) for s in used),
                n=len(used), preempt=int(a.ctr.get('preempt',0)),
                plog=[(round(p['depth_old'],2),round(p['target_old'],2)) for p in a.preempt_log])
def main():
    t0=time.time(); R=[]
    for p in glob.glob(DIR+'r76_cell_*.json'): R+=json.load(open(p))
    K={(r['src'],r['fix'],r['tlow'],r['T60'],r['sd'],r['T']):r for r in R}
    W("未经 critic 评审 —— r85 · 深度分布(不量计数)  [L2/宿主仿真]  预注册 = PREREG_r85.txt")
    W("⛔ 两条限定:①只有 1/6 种子有抖动 ⇒ **不得当趋势**,目标是机制不是量级")
    W("            ②若假设成立,须答「为什么只有这一条」;答不出 ⇒ 不得推广")
    W("遥测纯计数,逐位等价已证(新旧 nhs.py 12/12 相同)")
    W(f"工作点:src={SRC:+.0f} / T_OBS={T:.0f}s / 同一个 G(r76 该格终点)/ duck消融")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'臂':>5}{'挂陷':>5}{'抢占':>7}{'深度中位':>10}{'深度总和':>10}   深度分布")
    rows=[]
    for (T60,sd) in [(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]:
        rec=K.get((SRC,0,-45.,T60,sd,T))
        if rec is None or not np.isfinite(rec['dA']): continue
        h0,Dp=clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd); hb=band_limit(h0,8000.)
        s=np.random.default_rng(sd).standard_normal(int(T*FS))*(10**(SRC/20.))
        G=rec['m0']+rec['dA']
        for fix in (0,1):
            c=run(hb,Dp,G,s,fix)
            d=c['depths']
            W(f"{T60:>5.1f}{sd:>4}{('开' if fix else '关'):>5}{c['n']:>5}{c['preempt']:>7}"
              f"{(np.median(d) if d else float('nan')):>10.2f}{sum(d):>10.2f}   {d}")
            c.update(T60=T60,sd=sd,fix=fix,G=float(G)); rows.append(c)
        W("")
    W("="*110); W("§D 判据对表"); W("="*110)
    for (T60,sd) in [(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]:
        a=[r for r in rows if r['T60']==T60 and r['sd']==sd and r['fix']==0]
        b=[r for r in rows if r['T60']==T60 and r['sd']==sd and r['fix']==1]
        if not a or not b: continue
        a,b=a[0],b[0]
        ma=np.median(a['depths']) if a['depths'] else float('nan')
        mb=np.median(b['depths']) if b['depths'] else float('nan')
        dm=mb-ma; ds=sum(b['depths'])-sum(a['depths'])
        W(f"  T60={T60} sd={sd}: 深度中位 关 {ma:.2f} → 开 {mb:.2f}  差 {dm:+.2f}"
          f"  {'**开臂更浅(可判)**' if dm>0.354 else ('**开臂更深(可判)**' if dm<-0.354 else '(底下,不可判)')}"
          f"   深度总和 关 {sum(a['depths']):.1f} → 开 {sum(b['depths']):.1f}(Δ{ds:+.1f})")
    W("")
    W("  He2 抢占时【被抢走那个槽已压到多深】(depth_old):")
    for r in rows:
        if r['preempt']>0:
            dd=[x[0] for x in r['plog']]
            W(f"    T60={r['T60']} sd={r['sd']} 修法{'开' if r['fix'] else '关'}:抢占 {r['preempt']} 次,"
              f"depth_old 中位 **{np.median(dd):.2f}** 范围 [{min(dd):.2f}, {max(dd):.2f}]"
              f"  (depth0=−3,max_depth=−18)")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;不含结论性判读,不含修法。")
    open(DIR+'r85_depth_out.txt','w').write("\n".join(OUT)+"\n")
    json.dump(rows, open(DIR+'r85_depth.json','w'))
if __name__=='__main__': main()
