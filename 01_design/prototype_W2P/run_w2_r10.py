"""W2-P V-19 + V-20:δ=1.0 上重扫 μ / 稳态窗口口径澄清"""
import numpy as np, io, sys
import aec, metrics as M, rig, probe
from rig import FS, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*104); say("W2-P V-19/V-20 · adaptive-dsp-3 · [L2/宿主仿真]"); say("="*104)

# ---------------- V-20 先答三问 ----------------
say("\n### V-20 · 先回答架构侧三问(口径问题优先于数据)")
say("  **问2:δ 的定义** —— 我的实现是")
say("     step = μ / ( K·Px[bin] + δ·K·Px_ref + ε )")
say("     Px[bin] = 远端功率谱的**逐 bin 平滑值**;Px_ref = |X|² 的**长时标量均值**。")
say("  ⇒ **δ 不是有效步长的缩放因子,而是分母的『地板』** —— 它只在 Px[bin] 远小于长时均值时起作用")
say("     (远端静默、弱 bin)。那里正是 μ/(K·Px) 爆炸、调制峰产生的地方。")
say("  ⇒ **δ 是峰值步长限幅器,不是平均步长缩放器。** 这解释了为什么它对 max(峰统计量)的压制")
say("     远强于对 ERLE(均值统计量)的代价 —— 也解释了架构侧模型为何在 δ=1.0 上高估 5×:")
say("     模型把 δ 当成了与 μ 同类的标量增益,而它实际是**条件生效**的。")
say("  **问1/问3:稳态窗口口径** —— 我的 steady_erle 取后 1/3。DUR=12s ⇒ 窗起点 8s,")
say("     而 μ=0.05 实测收敛 7.4s ⇒ **窗几乎贴着收敛点** ⇒ 小 μ 被系统性低估。**架构侧的怀疑成立。**")

say("\n  -- V-20 决定性检验:延长到 48s,严格取**最后 8s**为稳态窗 --")
DUR_L=48.0; cssL=M.css(DUR_L)
class V(aec.MDF):
    def __init__(s2, delta=1e-2, **k): super().__init__(**k); s2.delta=delta
say(f"  {'μ':>6}{'ERLE@后1/3(旧口径,12s)':>24}{'ERLE@最后8s(48s跑)':>22}{'收敛s(48s跑)':>14}{'理论失调 M=μ/(2−μ)':>20}")
for mu in (0.05,0.1,0.2,0.4):
    a=V(delta=1.0,mu_max=mu); d,e,_,_=run_aec(a,M.css(12.0)); old=M.steady_erle(d,e)
    a=V(delta=1.0,mu_max=mu); dL,eL,_,_=run_aec(a,cssL)
    new=float(np.median(M.erle_db(dL,eL)[int((DUR_L-8)*FS):]))
    C=M.converge_time_s(dL,eL)
    Mis=10*np.log10(mu/(2-mu))
    say(f"  {mu:6.2f}{old:24.1f}{new:22.1f}{C:14.2f}{Mis:20.1f}")
say("  ⇒ 若『最后8s』列随 μ 减小而**上升**,则方向翻向理论,VSS 方向成立。")

# ---------------- V-19 ----------------
say("\n### V-19 · δ=1.0 上重扫 μ(三个统计量 + 三种激励 ERLE + 外推式检验)")
DUR=16.0; css=M.css(DUR); wb=M.white_burst(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]
mask=np.zeros(len(css),bool); mask[int(6.0*FS):int(11.0*FS)]=True
say(f"  {'μ':>6}{'C8f max':>9}{'median':>9}{'std':>8}{'门':>5}{'ERLE-CSS':>10}{'ERLE-双讲':>10}{'ERLE-白噪':>10}{'收敛s':>7}{'外推预测':>9}{'比值':>7}")
pred=lambda m: 2.40*m**1.256
res=[]
for mu in (0.05,0.10,0.165,0.20,0.30,0.40):
    fac=lambda: V(delta=1.0,mu_max=mu)
    d,_=probe.c8f_series(fac,dur=10.0,far_gate=(1.0,1.0))
    mx,med,sd=float(np.max(d)),float(np.median(d)),float(np.std(d))
    a=fac(); dd,e,ec,_=run_aec(a,css); Ec=M.steady_erle(dd,e); C=M.converge_time_s(dd,e)
    a=fac(); dw,ew,_,_=run_aec(a,wb); Ew=M.steady_erle(dw,ew)
    pe=np.mean(ec[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
    a=fac(); d2,e2,ec2,nr2=run_aec(a,css,near_src*mask*np.sqrt(pe/pn))
    Ed=float(np.median(M.erle_db(ec2,e2-nr2)[mask]))
    p=pred(mu); res.append((mu,mx,p))
    say(f"  {mu:6.3f}{mx:9.3f}{med:9.3f}{sd:8.3f}{'✓' if mx<=0.25 else '✗':>5}{Ec:10.1f}{Ed:10.1f}{Ew:10.1f}{C:7.2f}{p:9.3f}{mx/p:7.2f}")
r=[x[1]/x[2] for x in res]
say(f"  ⇒ 外推式 2.40·μ^1.256 的实测/预测比值:中位={np.median(r):.2f} 范围 {min(r):.2f}–{max(r):.2f}")
say(f"  ⇒ 外推式{'**成立**(比值近 1)' if 0.7<np.median(r)<1.4 else '**不成立**(系统性偏离)'};")
say("     该式由两点反推、未经验证,本轮为其首次独立检验。")
ok=[x for x in res if x[1]<=0.25]
say(f"  ⇒ δ=1.0 下过门的 μ:{[x[0] for x in ok] if ok else '无'}")
io.open('results_w2_r10.txt','w',encoding='utf-8').write('\n'.join(OUT))
