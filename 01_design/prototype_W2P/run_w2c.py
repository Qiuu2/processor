"""W2-P 补跑2(台架修正后):A2 真错位 / A4 真双讲"""
import numpy as np, io, sys, importlib
import aec, g168, rig; importlib.reload(rig)
from rig import FS, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
DUR=6.0; far=g168.css(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(far)]
a0=aec.MDF(); d0,e0,ec0,_=run_aec(a0,far); E0=g168.steady_erle(d0,e0)
say("\n### 补跑2(台架已修:ref 与 far 可分)")
say(f"  基线 ERLE={E0:.1f}dB")
say("\n  -- A2 真·参考错位(回声由 far 生成,AEC 只拿到位移后的 ref)--")
for ms in (25,100,400,600):
    n=int(ms*1e-3*FS); a=aec.MDF()
    d,e,_,_=run_aec(a,far,ref=np.roll(far,n))
    E=g168.steady_erle(d,e)
    say(f"     错位 {ms:4d}ms: ERLE={E:6.1f}dB -> {'FAIL(符合预期)' if E<E0-3 else '未FAIL'}")
a=aec.MDF(); d,e,_,_=run_aec(a,far,ref=np.random.default_rng(9).normal(0,0.5,len(far)))
say(f"     A2' 参考接错信号: ERLE={g168.steady_erle(d,e):6.1f}dB -> "
    f"{'FAIL(符合预期)' if g168.steady_erle(d,e)<E0-3 else '未FAIL'}")

say("\n  -- A4 真双讲(近端/回声比推到 0dB 以上)--")
mask=np.zeros(len(far),bool); mask[int(2.0*FS):int(4.5*FS)]=True
pe=np.mean(ec0[mask]**2)+1e-20
say(f"  {'近端/回声比':>11} {'完整ERLE':>9} {'固定ERLE':>9} {'完整近端保留':>12} {'固定近端保留':>12} {'完整发散':>9} {'固定发散':>9}")
for target in (-10.,0.,+6.,+12.):
    pn=np.mean((near_src*mask)[mask]**2)+1e-20
    amp=np.sqrt(10**(target/10.)*pe/pn); near=near_src*mask*amp
    r={}
    for tag,clr in (('full',True),('fix',False)):
        a=aec.MDF(continuous_lr=clr); d,e,ec,nr=run_aec(a,far,near)
        r[tag]=(float(np.median(g168.erle_db(ec,e-nr)[mask])),
                g168.nearend_loss_db(nr,e,mask=mask), g168.divergence(e))
    say(f"  {target:10.0f}dB {r['full'][0]:9.1f} {r['fix'][0]:9.1f} {r['full'][1]:12.1f} "
        f"{r['fix'][1]:12.1f} {r['full'][2]:9.1f} {r['fix'][2]:9.1f}")
io.open('results_w2_r1.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
