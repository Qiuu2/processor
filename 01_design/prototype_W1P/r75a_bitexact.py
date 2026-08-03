"""r75a · `prefer_unnotched` 默认关的【逐位】等价证明(含阳性对照)。⛔ 未经 critic 评审。[L2]
输出 r75a_bitexact_out.txt。Hq5 的执行件 —— 不读表达式,实跑比对。
"""
import sys, importlib.util
sys.path.insert(0,'/home/it1234/processor/01_design/prototype_W1P')
import numpy as np, clrig
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
ORIG='/tmp/claude-1000/-home-it1234-processor/530be877-5ec0-4df7-ae7b-ed9cade0a0b7/scratchpad/nhs_prev.py'
GR={'out_lim_active':False,'out_lim_gr_db':0.0}
SEEDS=[(0.2,0),(0.2,1),(0.2,2),(0.5,0),(0.5,1),(0.5,2)]
O=[]
def W(s=''):
    O.append(s); print(s); sys.stdout.flush()
def load(p,n):
    sp=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(sp)
    sys.modules[n]=m; sp.loader.exec_module(m); return m
def dig(mod,hb,D,G,src,flag=None,lvl=-60.):
    a=mod.NHS(); a.P.bw_oct=0.2
    if flag is not None: a.P.prefer_unnotched=flag
    def pf(b,_a=a): return _a.process_frame(b,GR)
    y,lp=clrig.Loop(hb,D,G,proc=pf).run(src,64)
    sl=tuple((int(s.st),float(s.f),float(s.depth),float(s.target)) for s in a.slots)
    return (np.asarray(y,np.float64).tobytes(), np.asarray(lp,np.float64).tobytes(),
            tuple(sorted((k,int(v)) for k,v in a.ctr.items() if isinstance(v,(int,np.integer)))), sl)
def main():
    W("未经 critic 评审 —— r75a · prefer_unnotched 默认关的逐位等价证明  [L2/宿主仿真]")
    W("比对:y 原始字节 / loop 原始字节 / 全部 ctr / 全部槽状态")
    W("⭐ 阳性对照:强制 True 对原件比,**必须有差异**;无差异 ⇒ 比对器无分辨力或开关没接上 ⇒ 整件作废")
    W("")
    mo=load(ORIG,'nhs_prev'); mn=load('/home/it1234/processor/01_design/prototype_W1P/nhs.py','nhs_cur')
    W("原件有 prefer_unnotched? %s(应 False) | 现件有? %s(应 True),默认 = %s(应 False)"%(
      hasattr(mo.Params(),'prefer_unnotched'), hasattr(mn.Params(),'prefer_unnotched'),
      mn.Params().prefer_unnotched))
    W("")
    W("%5s%4s%7s | %22s | %22s"%('T60','sd','Δ','Hq5 默认关 vs 原件','阳性对照 强制开 vs 原件'))
    same=n=0; diff=[]
    for (T60,sd) in SEEDS:
        h0,D=clrig.make_F(T60=T60,delay_ms=8.,seed=sd)
        hb=band_limit(h0,8000.); he=clrig.h_eff(hb)
        anchor=MSGMeter(he,FS).msg(slots=(),g_duck_db=0.)['full']['msg_db']
        for lvl in (-60.,-20.):
            src=np.random.default_rng(sd).standard_normal(int(6.0*FS))*(10**(lvl/20.))
            for dl in (1.0,3.0):
                G=anchor+dl
                a=dig(mo,hb,D,G,src); b=dig(mn,hb,D,G,src,False); c=dig(mn,hb,D,G,src,True)
                eq=(a==b); n+=1; same+=int(eq)
                nm=('y','loop','ctr','slots')
                wd=[x for x,p,q in zip(nm,a,c) if p!=q]
                if wd: diff.append((T60,sd,lvl,dl,wd))
                W("%5.1f%4d%7.1f | %22s | %22s"%(T60,sd,dl,
                  '✅逐位相同' if eq else '⛔不同',
                  ('差异于 '+','.join(wd)) if wd else '(无差异)'))
    W("")
    W("  Hq5(默认关 vs 原件):**%d/%d 逐位相同** ⇒ %s"%(same,n,
      'PASS' if same==n else '⛔FAIL —— 立即回滚 nhs.py 并报 lead'))
    W("  阳性对照(强制开):**%d/%d 出现差异** ⇒ %s"%(len(diff),n,
      'PASS(比对器有分辨力且开关接上了)' if diff else '⛔FAIL —— 整件作废'))
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/r75a_bitexact_out.txt','w').write("\n".join(O)+"\n")
if __name__=='__main__': main()
