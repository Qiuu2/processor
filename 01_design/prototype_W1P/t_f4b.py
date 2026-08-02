"""F4 隔离测试(v4)· 亚天花板复发 —— 这才是 F4 唯一破坏的情形。
若复发能重新顶到天花板,限幅器再次动作 ⇒ v1.4 的 GR 门也会打开 ⇒ 测不出 F4。
故构造:抑制成功后**小幅**抬增益,使该频点复发但**不足以再触发限幅器**。
判据(输出):复发段的峰包络与"是否被再次压住"。"""
import numpy as np
from experiments import *
from env import env_db, FS, FRAME, Limiter
from nhs import NHS, Params
from scipy.signal import lfilter

def run(brk, label, dur=18.0, g0=50.0, lg0=3.0, t_step=8.0, dlg=1.5):
    h,d = rir(); h = h*10**((lg0-g0)/20.0)
    src = 1e-5*np.random.default_rng(0).normal(0,1,int(dur*FS))
    a = NHS(P=Params(lift_after_s=60.0), broken=brk)   # 不让 LIFT 介入,隔离变量
    lim = Limiter(thr_db=-6.0)
    n=(len(src)//FRAME)*FRAME; out=np.zeros(n)
    fb=np.zeros(FRAME); zi=np.zeros(len(h)-1); gf=10**(g0/20.0); gr_on=[]
    for i in range(0,n,FRAME):
        if i == int(t_step*FS)//FRAME*FRAME: gf *= 10**(dlg/20.0)
        mic=src[i:i+FRAME]+fb
        y=a.process_frame(mic,{'out_lim_active':bool(lim.active),'out_lim_gr_db':float(lim.gr_db)})
        y=np.clip(y*gf,-8,8); y=lim.process(y)
        fb,zi=lfilter(h,[1.0],y,zi=zi); out[i:i+FRAME]=y
        if i>int(t_step*FS): gr_on.append(int(lim.active))
    e=env_db(out); m=metrics(out)
    post=e[int(t_step*FS):]
    dpn=[x for x in a.events if x[1]=='deepen' and x[0]*0.016>t_step]
    live=sum(1 for t in a.tracks if t.active)
    print(f"{label:16s} 复发后:峰包络={np.max(post):7.1f}dB 末={m['end_db']:7.1f}dB nb={m['nb']:.3f} "
          f"加深={len(dpn):2d} 活轨={live} GR占空={np.mean(gr_on)*100:.0f}% 在啸={howling(m)}")
    return m, dpn, float(np.max(post))

print("=== F4 隔离测试 v4:亚天花板复发(LIFT 关闭,只测'成功后还看不看得见')===")
mf,df,pf = run(None,   "F4修法版")
mb,db,pb = run(['B13'],"B13(v1.4)")
print(f"\n① 复发后加深次数: 修法={len(df)} v1.4={len(db)}")
print(f"② 复发段峰包络  : 修法={pf:.1f}dB v1.4={pb:.1f}dB  差={pb-pf:+.1f}dB")
print(f"⇒ {'**F4 隔离成立**' if (len(df)>len(db) and pb>pf+2) else '未能隔离(见报告如实说明)'}")
