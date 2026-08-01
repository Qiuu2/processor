"""P0-c:正则变体的**代价**测量 —— 压调制换来的 ERLE/收敛损失是多少?"""
import numpy as np, io, importlib
import aec; importlib.reload(aec)
import probe, metrics as M, rig
importlib.reload(probe)
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("\n### P0-c · 代价测量(加大正则 = 变相降步长,必须量代价)")
say("  纪律:不能用一个 max 统计量买一条规格 —— 同理,不能只报『调制压下去了』不报代价。")
class V(aec.MDF):
    def __init__(self,delta=1e-2,**k): super().__init__(**k); self.delta=delta
css=M.css(12.0); wb=M.white_burst(12.0)
say(f"  {'delta':>7} {'C-8f max':>9} {'C-8f std':>9} | {'CSS ERLE':>9} {'收敛s':>7} | {'白噪ERLE':>9} {'发散':>7}")
best=None
for dl in (1e-2, 5e-2, 1e-1, 3e-1, 5e-1, 1.0):
    d,_=probe.c8f_series(lambda: V(delta=dl, mu_max=0.2), dur=10.0, far_gate=(1.0,1.0))
    a=V(delta=dl,mu_max=0.2); dd,e,_,_=rig.run_aec(a,css)
    a2=V(delta=dl,mu_max=0.2); d2,e2,_,_=rig.run_aec(a2,wb)
    E=M.steady_erle(dd,e); C=M.converge_time_s(dd,e)
    say(f"  {dl:7.2f} {np.max(d):9.3f} {np.std(d):9.3f} | {E:9.1f} {C:7.2f} | "
        f"{M.steady_erle(d2,e2):9.1f} {M.divergence(e2):7.1f}")
say("  ⇒ 判读:找『C-8f max 尽量小 且 ERLE 尽量保住』的拐点;若无拐点(单调换),")
say("     则这是一条**真实的取舍曲线**,须由 CTO 在『回声消除量』与『NHS 可检出性』之间裁。")
io.open('results_w2_r5.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
