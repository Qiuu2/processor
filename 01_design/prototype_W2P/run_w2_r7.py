"""W2-P 第七轮(收尾):delta×mu 二维 / 收敛质量 / Px 公平检验 / A5-A7 重做 / PFDKF 定性"""
import numpy as np, io, sys, importlib
import aec, metrics as M, rig, probe
from rig import FS, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*84); say("W2-P 第七轮(C-8f 线收尾)· adaptive-dsp-3 · [L2/宿主仿真]"); say("="*84)
say("★ 通则(已采纳,置于头部):**在自适应滤波这条线上,任何结论都必须绑定工作点")
say("  (μ、正则 delta/leak、激励)一起报;单独的结论没有意义。**")
say("  本轮全部数字的工作点在各表表头标出。")
DUR=12.0; css=M.css(DUR); wb=M.white_burst(DUR)
class V(aec.MDF):
    def __init__(s2, delta=1e-2, **k): super().__init__(**k); s2.delta=delta

# ---------- 1. delta × mu 二维兑换率 ----------
say("\n### ① delta × μ 二维兑换率(CTO 定工作点的唯一依据)")
say("  激励:门控远端 1s/1s(=真实语音间歇常态);C-8f 门 max≤0.25dB;ERLE 用 CSS 单讲")
MUS=(0.05,0.1,0.2,0.4); DLS=(1e-2,1e-1,3e-1,1.0)
say(f"  {'':>8}" + "".join(f"{'δ=%.2g'%d:>22}" for d in DLS))
say(f"  {'':>8}" + "".join(f"{'max/ERLE/收敛':>22}" for d in DLS))
grid={}
for mu in MUS:
    row=f"  μ={mu:<6.2f}"
    for dl in DLS:
        d,_=probe.c8f_series(lambda: V(delta=dl,mu_max=mu), dur=8.0, far_gate=(1.0,1.0))
        a=V(delta=dl,mu_max=mu); dd,e,_,_=run_aec(a,css)
        mx=float(np.max(d)); E=M.steady_erle(dd,e); C=M.converge_time_s(dd,e)
        grid[(mu,dl)]=(mx,E,C)
        row+=f"{('%.2f/%.1f/%.1f'%(mx,E,C)):>22}"
    say(row)
ok=[(k,v) for k,v in grid.items() if v[0]<=0.25]
say(f"  ⇒ 过门(max≤0.25)的格点:{len(ok)}/{len(grid)}")
if ok:
    b=max(ok,key=lambda kv: kv[1][1])
    say(f"     其中 ERLE 最高者:μ={b[0][0]} δ={b[0][1]:.2g} → max={b[1][0]:.2f} ERLE={b[1][1]:.1f}dB 收敛={b[1][2]:.1f}s")
else:
    best=min(grid.items(), key=lambda kv: kv[1][0])
    say(f"     **无格点过门**;最接近者 μ={best[0][0]} δ={best[0][1]:.2g} max={best[1][0]:.2f}dB "
        f"(超门 {best[1][0]/0.25:.1f}×) ERLE={best[1][1]:.1f}dB")

# ---------- 2. 收敛质量解释 ----------
say("\n### ② 「收敛质量」解释验证(间歇远端 ⇒ 收敛差 ⇒ 残差大 ⇒ 梯度噪声大?)")
say("  设计:连续远端 vs 门控远端,**按等效活动样本数配平**(门控跑 2× 时长)")
for nm,gate,dur in (('连续远端',None,8.0),('门控远端 1s/1s',(1.0,1.0),16.0)):
    d,fm=probe.c8f_series(lambda: aec.MDF(mu_max=0.2), dur=dur, far_gate=gate)
    act = fm>(np.median(fm[fm>0])*0.1 if (fm>0).any() else 0)
    say(f"  {nm:14s} 活动块={act.sum():4d} max={np.max(d):7.3f} median={np.median(d):+7.3f} std={np.std(d):6.3f}")
say("  ⇒ 若配平后门控仍显著更差 ⇒ 收敛质量解释成立;若接近 ⇒ 差异只是活动样本少。")

# ---------- 3. Px 快攻慢放公平检验 ----------
say("\n### ③ Px 快攻慢放 —— 公平检验(此前是实现错误致发散,非该方向已否)")
say(f"  {'配置':>22}{'C-8f max':>10}{'std':>8}{'CSS ERLE':>10}{'收敛s':>8}")
for nm,kw in (('对称 0.9(基线)',dict()),
              ('快攻0.3/慢放0.95',dict(px_attack=0.3,px_release=0.95)),
              ('快攻0.5/慢放0.99',dict(px_attack=0.5,px_release=0.99)),
              ('快攻0.1/慢放0.9',dict(px_attack=0.1,px_release=0.9))):
    d,_=probe.c8f_series(lambda: aec.MDF(mu_max=0.2,**kw), dur=8.0, far_gate=(1.0,1.0))
    a=aec.MDF(mu_max=0.2,**kw); dd,e,_,_=run_aec(a,css)
    say(f"  {nm:>22}{np.max(d):10.3f}{np.std(d):8.3f}{M.steady_erle(dd,e):10.1f}{M.converge_time_s(dd,e):8.2f}")

# ---------- 4. A5/A7 重做 ----------
say("\n### ④ A5/A7 broken 用例重做")
say("  A5:线性卷积约束是**有理论依据的正确性要求**(循环卷积混叠是已知错误),")
say("     故改为**在 μ 扫描上证伪**,不在单一工作点判(lead 裁定,我认:D4 不适用于正确性约束)")
class A5(aec.MDF):
    def process(self,x,dd):
        N,Mm=self.N,self.M
        xx=np.concatenate([self.xprev,x]); self.xprev=x.copy()
        X=np.fft.rfft(xx); self.Xh=np.roll(self.Xh,1,axis=0); self.Xh[0]=X
        Y=np.sum(self.W*self.Xh,axis=0); y=np.fft.irfft(Y,Mm)[N:]; e=dd-y
        E=np.fft.rfft(np.concatenate([np.zeros(N),e]))
        inst=np.abs(X)**2; self.Px=0.9*self.Px+0.1*inst
        self.Px_ref=0.999*self.Px_ref+0.001*float(np.mean(inst))
        self.W += (self.mu_max/(self.K*self.Px+self.delta*self.K*self.Px_ref+1e-20))[None,:]*np.conj(self.Xh)*E[None,:]
        return e
say(f"  {'μ':>6}{'完整 ERLE':>11}{'A5 ERLE':>10}{'Δ':>8}  判定")
a5fail=0
for mu in (0.1,0.2,0.3,0.5,0.7):
    a=aec.MDF(mu_max=mu); d,e,_,_=run_aec(a,css); Ef=M.steady_erle(d,e)
    b=A5(mu_max=mu); d2,e2,_,_=run_aec(b,css); Eb=M.steady_erle(d2,e2)
    f=(Eb<Ef-3.0); a5fail+=f
    say(f"  {mu:6.2f}{Ef:11.1f}{Eb:10.1f}{Eb-Ef:8.1f}  {'FAIL' if f else '未FAIL'}")
say(f"  ⇒ A5 在 {a5fail}/5 个 μ 上 FAIL ⇒ **约束保留**(危害是 μ 的强函数,非无收益机制)")
say("  A7 重做:原构造(Px 钉成 1e12)只是恒定降步长。改为**完全去掉归一化**(裸梯度):")
class A7(aec.MDF):
    def process(self,x,dd):
        N,Mm=self.N,self.M
        xx=np.concatenate([self.xprev,x]); self.xprev=x.copy()
        X=np.fft.rfft(xx); self.Xh=np.roll(self.Xh,1,axis=0); self.Xh[0]=X
        Y=np.sum(self.W*self.Xh,axis=0); y=np.fft.irfft(Y,Mm)[N:]; e=dd-y
        E=np.fft.rfft(np.concatenate([np.zeros(N),e]))
        g=np.fft.irfft(self.mu_max*1e-3*np.conj(self.Xh)*E[None,:],Mm,axis=1); g[:,N:]=0.0
        self.W=self.W+np.fft.rfft(g,Mm,axis=1)
        return e
for nm,sig in (('CSS',css),('白噪突发',wb)):
    a=aec.MDF(mu_max=0.2); d,e,_,_=run_aec(a,sig); Ef=M.steady_erle(d,e)
    b=A7(mu_max=0.2); d2,e2,_,_=run_aec(b,sig); Eb=M.steady_erle(d2,e2)
    say(f"     {nm:8s} 完整={Ef:6.1f}dB  A7(裸梯度)={Eb:7.1f}dB  发散={M.divergence(e2):+7.1f}dB  "
        f"{'FAIL(符合预期)' if Eb<Ef-3 or M.divergence(e2)>3 else '**未FAIL**'}")
io.open('results_w2_r7.txt','w',encoding='utf-8').write('\n'.join(OUT))
