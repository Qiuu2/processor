"""W2-P 补跑:①A2 用例修正(延迟须 > 尾长)②A4 连续学习率的公平机会(加严双讲)"""
import numpy as np, io, sys
import aec, g168, rig
from rig import FS, run_aec, echo_path
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
DUR=6.0; far=g168.css(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(far)]
a0=aec.MDF(); d0,e0,_,_=run_aec(a0,far); E0=g168.steady_erle(d0,e0)

say("\n### 补跑1 · A2 用例修正:参考延迟 vs 尾长")
say(f"  基线 ERLE={E0:.1f}dB;尾长=512ms。假说:延迟只要落在尾长内就被自适应吸收 ⇒ 原用例无效")
for ms in (25, 100, 400, 600, 1000):
    n=int(ms*1e-3*FS); a=aec.MDF(); d,e,_,_=run_aec(a,np.roll(far,n))
    E=g168.steady_erle(d,e)
    say(f"  参考错位 {ms:5d}ms ({'尾长内' if ms<512 else '**超尾长**'}): ERLE={E:6.1f}dB  "
        f"{'FAIL' if E<E0-3 else '未FAIL(被自适应吸收)'}")
say("  ⇒ **A2 原用例(25ms)无效**:延迟在尾长内 ⇒ 滤波器直接学到偏移后的路径。")
say("    有效的参考类 broken 必须是:延迟 > 尾长、或**接错通道/错信号**。")
# 错通道版
a=aec.MDF(); d,e,_,_=run_aec(a, np.random.default_rng(9).normal(0,0.5,len(far)))
say(f"  A2' 参考接错信号(无关噪声): ERLE={g168.steady_erle(d,e):6.1f}dB -> "
    f"{'FAIL(符合预期)' if g168.steady_erle(d,e)<E0-3 else '未FAIL'}")

say("\n### 补跑2 · A4 连续学习率的公平机会(逐级加严双讲)")
say("  纪律:上一轮我在 P22 上据不充分证据下过结论。此处**先给它可能救它的场景**再判。")
say(f"  {'近端/回声比':>12} {'完整版ERLE':>11} {'固定步长ERLE':>13} {'完整近端保留':>13} {'固定近端保留':>13} {'完整发散':>9} {'固定发散':>9}")
mask=np.zeros(len(far),bool); mask[int(2.0*FS):int(4.5*FS)]=True
for amp in (0.2, 0.5, 1.0, 2.0, 4.0):
    near=near_src*mask*amp
    r={}
    for tag,clr in (('full',True),('fix',False)):
        a=aec.MDF(continuous_lr=clr); d,e,ec,nr=run_aec(a,far,near)
        Edt=float(np.median(g168.erle_db(ec,e-nr)[mask]))
        r[tag]=(Edt, g168.nearend_loss_db(nr,e,mask=mask), g168.divergence(e))
    ner=10*np.log10((np.mean((near_src*mask*amp)[mask]**2)+1e-20)/(np.mean(d0[mask]**2)+1e-20))
    say(f"  {ner:11.1f}dB {r['full'][0]:11.1f} {r['fix'][0]:13.1f} {r['full'][1]:13.1f} "
        f"{r['fix'][1]:13.1f} {r['full'][2]:9.1f} {r['fix'][2]:9.1f}")
say("  判读:若连续学习率有价值,应在**近端/回声比升高**时体现为 完整版发散更小 / 近端保留更好。")
io.open('results_w2_r1.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
