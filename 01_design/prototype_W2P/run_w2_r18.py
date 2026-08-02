"""W2-P V-26(正式):非均匀 MDF vs 均匀 K=64 的 μ 稳定域,同参可比"""
import numpy as np, io, sys
import aec, metrics as M, rig, probe, mdf_nu
from rig import FS, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*112); say("W2-P V-26(正式)· 非均匀 MDF vs 均匀 K=64 · μ 稳定域 · [L2/宿主仿真]"); say("="*112)
ST=((32,8),(256,8),(1024,6))
w0=mdf_nu.NUMDFWrap(stages=ST)
say(f"### D6 工作点向量")
say(f"  共同:fs=16000Hz, tail≈512ms, δ=1.0, T_obs=20s(C-8f), 激励=门控远端1s/1s, ERL=n/a")
say(f"  结构A(均匀)  :L=128, K=64,      尾=8192样本=512ms, I/O 延迟=128样本=8.00ms")
say(f"  结构B(非均匀):{w0.struct_str}, K_total={w0.K}, 尾={w0.core.tail}样本={w0.core.tail/FS*1000:.0f}ms, I/O 延迟={w0.core.io_delay_samples}样本={w0.core.io_delay_samples/FS*1000:.2f}ms")
DUR=16.0; css=M.css(DUR); wb=M.white_burst(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]
mask=np.zeros(len(css),bool); mask[int(6*FS):int(11*FS)]=True

def ev(fac):
    d,_=probe.c8f_series(fac, dur=20.0, far_gate=(1.0,1.0))
    a=fac(); dd,e,ec,_=run_aec(a,css); Ec=M.steady_erle(dd,e); C=M.converge_time_s(dd,e)
    a=fac(); dw,ew,_,_=run_aec(a,wb); Ew=M.steady_erle(dw,ew)
    pe=np.mean(ec[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
    a=fac(); d2,e2,ec2,nr2=run_aec(a,css,near_src*mask*np.sqrt(pe/pn))
    Ed=float(np.median(M.erle_db(ec2,e2-nr2)[mask]))
    return float(np.max(d)),float(np.median(d)),float(np.std(d)),Ec,Ed,Ew,C

def mkA(mu):
    a=aec.MDF(fs=FS,tail_ms=512.,block=128,mu_max=mu); a.delta=1.0; return a
def mkB(mu):
    return mdf_nu.NUMDFWrap(stages=ST, mu_max=mu, delta=1.0)

MUS=(0.05,0.10,0.165,0.20,0.30,0.40)
for tag,mk in (('A 均匀 L=128/K=64',mkA),('B 非均匀 32×8+256×8+1024×6',mkB)):
    say(f"\n### 结构{tag}")
    say(f"  {'μ':>6}{'C8f max':>9}{'median':>9}{'std':>8}{'门':>4}{'ERLE单讲':>10}{'ERLE双讲':>10}{'ERLE白噪':>10}{'收敛s':>7}{'判定':>8}")
    R={}
    for mu in MUS:
        try:
            mx,med,sd,Ec,Ed,Ew,C = ev(lambda m=mu: mk(m))
        except Exception as ex:
            say(f"  {mu:6.3f}  异常:{ex}"); continue
        j='发散' if Ec<-50 else ('稳定' if Ec>0 else '劣化')
        R[mu]=(mx,Ec,j)
        say(f"  {mu:6.3f}{mx:9.3f}{med:9.3f}{sd:8.3f}{'✓' if mx<=0.25 else '✗':>4}{Ec:10.1f}{Ed:10.1f}{Ew:10.1f}{C:7.2f}{j:>8}")
    globals()['R_'+tag[0]]=R
say("\n### 逐点对照(结构A vs 结构B)")
say(f"  {'μ':>6}{'A ERLE':>9}{'B ERLE':>9}{'ΔERLE':>8}{'A C8f':>8}{'B C8f':>8}{'A判定':>7}{'B判定':>7}{'结论':>10}")
RA=globals().get('R_A',{}); RB=globals().get('R_B',{})
narrow=same=wide=0
for mu in MUS:
    if mu not in RA or mu not in RB: continue
    a=RA[mu]; b=RB[mu]
    if a[2]==b[2]: c='一致'; same+=1
    elif a[2]=='稳定' and b[2]!='稳定': c='**收窄**'; narrow+=1
    elif a[2]!='稳定' and b[2]=='稳定': c='放宽'; wide+=1
    else: c='差异'
    say(f"  {mu:6.3f}{a[1]:9.1f}{b[1]:9.1f}{b[1]-a[1]:8.1f}{a[0]:8.3f}{b[0]:8.3f}{a[2]:>7}{b[2]:>7}{c:>10}")
say(f"\n  ⇒ 一致 {same} 点 / 收窄 {narrow} 点 / 放宽 {wide} 点")
if narrow==0 and same==len(MUS):
    say("  ⇒ **稳定域一致** ⇒ 十三轮结论在新结构上继承有效;V-25 可在定版结构上跑。")
elif narrow>0:
    say("  ⇒ **稳定域收窄** ⇒ 架构侧须在『延迟解耦』与『μ 可用域』之间重新权衡(其活,非我裁)。")
else:
    say("  ⇒ 混合结果,逐点如实列示,不作单一判定。")
io.open('results_w2_r18.txt','w',encoding='utf-8').write('\n'.join(OUT))
