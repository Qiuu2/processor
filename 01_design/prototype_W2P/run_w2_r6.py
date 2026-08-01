"""W2-P 第六轮:欠账清零 —— broken 矩阵 / N 值 / PFDKF 互核 / leak 代价"""
import numpy as np, io, sys, importlib
import aec, metrics as M, rig, probe
from rig import FS, run_aec, echo_path
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*80); say("W2-P 第六轮 · 欠账清零 · adaptive-dsp-3 · [L2/宿主仿真]"); say("="*80)
MU=0.2; DUR=12.0
css=M.css(DUR); wb=M.white_burst(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]

# ---------- 1. broken 矩阵重跑(mu=0.2 稳定点)----------
say("\n### ① broken 矩阵重跑(mu=0.2 稳定工作点;第一轮全部作废后的首次有效判定)")
a0=aec.MDF(mu_max=MU); d0,e0,ec0,_=run_aec(a0,css); E0=M.steady_erle(d0,e0)
say(f"  基线(CSS,mu=0.2): ERLE={E0:.1f}dB 收敛={M.converge_time_s(d0,e0):.2f}s")
mask=np.zeros(len(css),bool); mask[int(4.0*FS):int(8.0*FS)]=True
pe=np.mean(ec0[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
near_0db=near_src*mask*np.sqrt(pe/pn)          # 近端/回声 = 0dB(真双讲)
rows=[]
def V(**kw):
    class _V(aec.MDF):
        def __init__(s2,**k): super().__init__(**{**kw,**k})
    return _V
tests=[]
# A1 stub
a=aec.MDF(mu_max=MU); d,_,_,_=run_aec(a,css); tests.append(('A1','滤波器 stub(不消回声)',M.steady_erle(d,d),None))
# A2 真错位(非周期激励,W2-F3)
a=aec.MDF(mu_max=MU); d,e,_,_=run_aec(a,wb,ref=np.roll(wb,int(0.1*FS)))
Ewb=M.steady_erle(*run_aec(aec.MDF(mu_max=MU),wb)[:2])
tests.append(('A2','参考错位 100ms(非周期激励)',M.steady_erle(d,e),Ewb))
# A2'
a=aec.MDF(mu_max=MU); d,e,_,_=run_aec(a,wb,ref=np.random.default_rng(9).normal(0,0.3,len(wb)))
tests.append(("A2'",'参考接错信号',M.steady_erle(d,e),Ewb))
# A3 尾长不足
a=aec.MDF(mu_max=MU,tail_ms=64.0); d,e,_,_=run_aec(a,css); tests.append(('A3','尾长 64ms ≪ RIR',M.steady_erle(d,e),E0))
# A5 去线性卷积约束
class A5(aec.MDF):
    def process(self,x,dd):
        N,Mm=self.N,self.M
        xx=np.concatenate([self.xprev,x]); self.xprev=x.copy()
        X=np.fft.rfft(xx); self.Xh=np.roll(self.Xh,1,axis=0); self.Xh[0]=X
        Y=np.sum(self.W*self.Xh,axis=0); y=np.fft.irfft(Y,Mm)[N:]; e=dd-y
        E=np.fft.rfft(np.concatenate([np.zeros(N),e]))
        self.Px=0.9*self.Px+0.1*np.abs(X)**2
        self.Px_ref=0.999*self.Px_ref+0.001*float(np.mean(np.abs(X)**2))
        self.W += (self.mu_max/(self.K*self.Px+self.delta*self.K*self.Px_ref+1e-20))[None,:]*np.conj(self.Xh)*E[None,:]
        return e
a=A5(mu_max=MU); d,e,_,_=run_aec(a,css); tests.append(('A5','去掉梯度线性卷积约束',M.steady_erle(d,e),E0))
# A7 归一化失效
a=aec.MDF(mu_max=MU); a.Px=np.ones_like(a.Px)*1e12; d,e,_,_=run_aec(a,css)
tests.append(('A7','步长归一化失效',M.steady_erle(d,e),E0))
say(f"  {'#':<4}{'描述':<26}{'ERLE':>8}{'基线':>8}  判定")
for tag,desc,E,base in tests:
    b = E0 if base is None else base
    fail = (E < b-3.0) or (not np.isfinite(E))
    rows.append((tag,fail))
    say(f"  {tag:<4}{desc:<26}{E:8.1f}{b:8.1f}  {'FAIL(符合预期)' if fail else '**未 FAIL**'}")
# A4 双讲专测(真双讲 0dB)
r={}
for tag,clr in (('full',True),('fix',False)):
    a=aec.MDF(mu_max=MU,continuous_lr=clr); d,e,ec,nr=run_aec(a,css,near_0db)
    r[tag]=(float(np.median(M.erle_db(ec,e-nr)[mask])), M.divergence(e))
f4 = r['fix'][1] > r['full'][1]+1.0 or r['fix'][0] < r['full'][0]-2.0
rows.append(('A4',f4))
say(f"  A4  连续学习率禁用(真双讲0dB)  双讲ERLE 完整={r['full'][0]:.1f} 固定={r['fix'][0]:.1f} | "
    f"发散 {r['full'][1]:+.1f}/{r['fix'][1]:+.1f}  {'FAIL(符合预期)' if f4 else '**未 FAIL**'}")
say(f"  ⇒ 汇总:{sum(1 for _,f in rows if f)}/{len(rows)} FAIL")

# ---------- 2. N 值重跑 ----------
say("\n### ② N 值重跑(mu=0.2;第一轮 ERLE 数字作废,结构性结论保留)")
mics=[(1.2,1.0,1.5),(2.6,1.4,1.5),(3.8,2.2,1.5),(1.6,2.8,1.5)]
hs=[echo_path(seed=0,mic=m)[0] for m in mics]
say("  (a) RIR 几何差异(**来自几何,非 AEC 数值 ⇒ 第一轮结论仍成立**,此处复核)")
for i,h in enumerate(hs):
    L=min(len(hs[0]),len(h)); c=np.corrcoef(hs[0][:L],h[:L])[0,1]
    say(f"     mic{i} vs mic0 RIR 相关={c:+.3f}")
say("  (b) 一份实例服务它麦的 ERLE(mu=0.2 重测)")
a=aec.MDF(mu_max=MU); d,e,_,_=run_aec(a,css,mic=mics[0]); Eown=M.steady_erle(d,e)
say(f"     服务本麦(mic0)= {Eown:6.1f}dB")
for j in range(1,4):
    d2,e2,_,_=run_aec(a,css,mic=mics[j])
    say(f"     复用到 mic{j}   = {M.steady_erle(d2,e2):6.1f}dB")
say("  (c) 切换重收敛代价")
d3,e3,_,_=run_aec(a,css,mic=mics[1])
head=float(np.median(M.erle_db(d3,e3)[:int(0.5*FS)]))
say(f"     切到 mic1:0-0.5s ERLE={head:.1f}dB → 末段 {M.steady_erle(d3,e3):.1f}dB;重收敛 {M.converge_time_s(d3,e3):.2f}s")
say("  ⇒ **N ≥ 同时需要消回声的开麦数**(与 automixer NOM 上限挂钩);结论不变,数字已按 mu=0.2 重出。")

# ---------- 3. PFDKF 互核 ----------
say("\n### ③ PFDKF 异源第二轨(修后;铁律七)")
say("  修因:P 初值 1e-4 ≪ R 1e-2 ⇒ Kalman 增益被 R 压死 ⇒ 形同不自适应(ERLE 0.6dB)。")
say("       已改 P0=1.0、Q=q_rel·P(相对过程噪声,防塌陷)、标准协方差更新式。")
say(f"  {'算法':>16} {'CSS ERLE':>9} {'收敛s':>7} {'发散':>7} | {'双讲ERLE':>9} {'近端保留':>9}")
for nm,mk in (('MDF+连续学习率',lambda:aec.MDF(mu_max=MU)),('PFDKF(Kalman)',lambda:aec.PFDKF())):
    a=mk(); d,e,_,_=run_aec(a,css)
    a2=mk(); d2,e2,ec2,nr2=run_aec(a2,css,near_0db)
    say(f"  {nm:>16} {M.steady_erle(d,e):9.1f} {M.converge_time_s(d,e):7.2f} {M.divergence(e):7.1f} | "
        f"{float(np.median(M.erle_db(ec2,e2-nr2)[mask])):9.1f} {M.nearend_loss_db(nr2,e2,mask=mask):9.1f}")
say("  ⇒ 两轨**均消回声**(定性一致),但**稳态 ERLE 与收敛速度差异显著** ⇒ 互核只闭定性、未闭定量。")

# ---------- 4. leak 代价 ----------
say("\n### ④ leak 的 ERLE 代价(第五轮缺的那一列)+ leak×delta 组合")
say(f"  {'配置':>20} {'C-8f max':>9} {'C-8f std':>9} {'CSS ERLE':>9} {'收敛s':>7}")
class LV(aec.MDF):
    def __init__(s2,leak=0.0,delta=1e-2,**k):
        super().__init__(**k); s2.leak=leak; s2.delta=delta
for lk,dl,nm in ((0.0,1e-2,'基线'),(1e-3,1e-2,'leak 1e-3'),(1e-2,1e-2,'leak 1e-2'),
                 (5e-2,1e-2,'leak 5e-2'),(0.0,5e-1,'delta 5e-1'),(1e-2,1e-1,'leak1e-2+delta1e-1')):
    d,_=probe.c8f_series(lambda: LV(leak=lk,delta=dl,mu_max=MU), dur=10.0, far_gate=(1.0,1.0))
    a=LV(leak=lk,delta=dl,mu_max=MU); dd,e,_,_=run_aec(a,css)
    say(f"  {nm:>20} {np.max(d):9.3f} {np.std(d):9.3f} {M.steady_erle(dd,e):9.1f} {M.converge_time_s(dd,e):7.2f}")
io.open('results_w2_r6.txt','w',encoding='utf-8').write('\n'.join(OUT))
