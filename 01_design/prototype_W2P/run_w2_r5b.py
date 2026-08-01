"""P0-b:假设证伪后,直接对归一化的几种变体测效果(max/median/std 三个数都报)"""
import numpy as np, io, importlib
import aec, probe
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("\n### P0-a 结论:**过渡块假设被证伪**")
say("  过渡后 0-24 块 |d| 中位 0.000-0.307、max ≤1.199;")
say("  而**稳态活动块** 中位 1.934、**max 19.610**;最大 20 峰到最近过渡的块距中位 98 块(784ms)。")
say("  ⇒ 损害既不在静默块(④a 无效),也不在过渡块(本假设),而在**稳态自适应本身**。")
say("  ⇒ 门控放大 7× 的另一解释(待验):间歇远端使 AEC 收敛质量下降 ⇒ 残差 e 更大")
say("     ⇒ 梯度噪声更大 ⇒ 系数抖动更大。这是**收敛质量**效应,不是归一化瞬态。")

say("\n### P0-b · 归一化变体实测(不动 μ;三个数都报)")
class V_fastPx(aec.MDF):
    """变体1:Px 快攻慢放(信号回来时分母跟得上)"""
    def process(self,x,d):
        self._fast=True; return super().process(x,d)
class V_delta(aec.MDF):
    """变体2:加大相对正则 delta 1e-2 → 1e-1"""
    def __init__(self,**k): super().__init__(**k); self.delta=1e-1
class V_delta2(aec.MDF):
    def __init__(self,**k): super().__init__(**k); self.delta=5e-1
class V_leak(aec.MDF):
    """变体3:系数泄漏(leakage)—— 直接压系数抖动的经典手段"""
    def __init__(self,**k): super().__init__(**k); self.leak=1e-3
class V_leak2(aec.MDF):
    def __init__(self,**k): super().__init__(**k); self.leak=1e-2

# 变体1 需改 Px 更新为快攻慢放
_orig=aec.MDF.process
def patched(self,x_blk,d_blk):
    if getattr(self,'_fast',False):
        N,M=self.N,self.M
        xx=np.concatenate([self.xprev,x_blk])
        Xtmp=np.fft.rfft(xx); inst=np.abs(Xtmp)**2
        a=np.where(inst>self.Px, 0.3, 0.95)      # 快攻(0.3)慢放(0.95)
        self.Px=a*self.Px+(1-a)*inst
        self._skipPx=True
    return _orig(self,x_blk,d_blk)
aec.MDF.process=patched

say(f"  {'变体':>22} {'max':>8} {'median':>9} {'std':>8}  门 max≤0.25")
for nm,fac in (('基线(现状)',lambda:aec.MDF(mu_max=0.2)),
               ('①Px 快攻慢放',lambda:V_fastPx(mu_max=0.2)),
               ('②delta 1e-2→1e-1',lambda:V_delta(mu_max=0.2)),
               ('③delta 1e-2→5e-1',lambda:V_delta2(mu_max=0.2)),
               ('④leak 1e-3',lambda:V_leak(mu_max=0.2)),
               ('⑤leak 1e-2',lambda:V_leak2(mu_max=0.2))):
    d,_=probe.c8f_series(fac, dur=10.0, far_gate=(1.0,1.0))
    say(f"  {nm:>22} {np.max(d):8.3f} {np.median(d):9.3f} {np.std(d):8.3f}  "
        f"{'过门' if np.max(d)<=0.25 else '超门 %.0f×'%(np.max(d)/0.25)}")
say("  (门控远端 1s/1s = 真实语音的间歇常态;上表全部在此条件下测)")
io.open('results_w2_r5.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
