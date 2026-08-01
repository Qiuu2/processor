"""W2-P V-25(终局):AEC×NHS 同环路,6dB stability loss 工作点,只看输出信号。
判读由架构侧预先写死,本文照此报,不改。"""
import numpy as np, io, sys
import aec, metrics as M
sys.path.insert(0,'../prototype_W1P')
from env import image_source_rir, synth_speech, synth_music, env_db
import nhs as NHSMOD
from nhs import NHS, Params
from scipy.signal import lfilter
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
FS48=48000.0; BLK=128; NF=64
say("="*104); say("W2-P V-25(终局)· AEC×NHS 同环路 · 只看输出信号 · [L2/宿主仿真]"); say("="*104)
say("  工作点:P.341 强制 stability loss = **6dB**;AEC μ=**0.40**(最坏档),δ=1.0;T_obs=**40s**")
say("  链位(C10 子级裁定):mic → AEC 线性滤波 → **[NHS tap + 陷波器组]** → 前向增益 → 扬声器")
say("  对照:**同一 AEC 冻结**(系数不更新)。判据**只取输出信号**,不看任何内部旗标。")

def build_rir(seed):
    h,d = image_source_rir(rt60=0.35, seed=seed)
    Hf=np.abs(np.fft.rfft(h,1<<16))
    return h/(Hf.max()+1e-30), d

def run_case(seed, adapt, dur=40.0, sl_db=6.0, mu=0.40, material='speech'):
    h,dly = build_rir(seed)
    n=int(dur*FS48)//BLK*BLK
    rng=np.random.default_rng(seed+100)
    far = (synth_speech(dur,seed=seed+7)*0.5 if material=='speech'
           else synth_music(dur,seed=seed+7)*0.5)[:n]
    near = rng.normal(0,1e-4,n)                     # 本地底噪(种子远低于天花板)
    a=aec.MDF(fs=FS48, tail_ms=512.0, block=BLK, mu_max=mu); a.delta=1.0
    alg=NHS(P=Params())
    g=10**(-sl_db/20.0)                              # 本地环路增益 = −6dB(= stability loss 6dB)
    fb=np.zeros(BLK); zi=np.zeros(len(h)-1)
    out=np.zeros(n)
    for i in range(0,n,BLK):
        mic = fb + near[i:i+BLK]
        if adapt:
            e = a.process(far[i:i+BLK], mic)
        else:
            W0=a.W.copy(); e=a.process(far[i:i+BLK], mic); a.W=W0
        y=np.empty(BLK)
        for k in range(0,BLK,NF):
            y[k:k+NF]=alg.process_frame(e[k:k+NF],
                        {'out_lim_active':False,'out_lim_gr_db':0.0,'dyn_active':False})
        o=np.clip(y*g*alg.duck_gain(),-8,8)
        spk = far[i:i+BLK] + o
        fb,zi = lfilter(h,[1.0],spk,zi=zi)
        out[i:i+BLK]=o
    eng=[x for x in alg.events if str(x[1]).startswith('engage')]
    seg=out[-8192:]*np.hanning(8192); X=np.abs(np.fft.rfft(seg))
    return dict(env_end=float(env_db(out,FS48)[-2000]),
                env_peak=float(np.max(env_db(out,FS48)[int(2*FS48):])),
                nb=float(X.max()**2/(np.sum(X**2)+1e-30)),
                n_eng=len(eng), engs=[(round(x[2],1)) for x in eng[:5]])

say("\n### 三次独立实现(不同 RIR 种子 + 素材);报离散度")
say(f"  {'实现':>16}{'条件':>10}{'末包络dB':>10}{'峰包络dB':>10}{'窄带':>8}{'挂陷数':>7}{'挂陷频点':>22}")
rows={'adapt':[], 'frozen':[]}
for si,(seed,mat) in enumerate([(0,'speech'),(1,'music'),(2,'speech')]):
    for nm,ad in (('AEC 自适应',True),('AEC 冻结(对照)',False)):
        r=run_case(seed, ad, material=mat)
        rows['adapt' if ad else 'frozen'].append(r)
        say(f"  {('#%d seed%d %s'%(si+1,seed,mat)):>16}{nm:>10}{r['env_end']:10.1f}{r['env_peak']:10.1f}"
            f"{r['nb']:8.3f}{r['n_eng']:7d}{str(r['engs']):>22}")
say("\n### 两项判读(架构侧预先写死)")
ae=[r['env_peak'] for r in rows['adapt']]; fe=[r['env_peak'] for r in rows['frozen']]
an=[r['nb'] for r in rows['adapt']];       fn=[r['nb'] for r in rows['frozen']]
ag=[r['n_eng'] for r in rows['adapt']];    fg=[r['n_eng'] for r in rows['frozen']]
say(f"  ① 可闻振铃/窄带上冲:峰包络 自适应={np.mean(ae):.1f}±{np.std(ae):.1f}dB  "
    f"冻结={np.mean(fe):.1f}±{np.std(fe):.1f}dB  Δ={np.mean(ae)-np.mean(fe):+.2f}dB")
say(f"                     窄带集中度 自适应={np.mean(an):.3f}±{np.std(an):.3f}  "
    f"冻结={np.mean(fn):.3f}±{np.std(fn):.3f}  Δ={np.mean(an)-np.mean(fn):+.4f}")
say(f"  ② AFC 误挂陷:自适应={ag} (合计{sum(ag)})  冻结={fg} (合计{sum(fg)})  Δ={sum(ag)-sum(fg):+d}")
diff_ring = abs(np.mean(ae)-np.mean(fe))>1.0 or abs(np.mean(an)-np.mean(fn))>0.05
diff_eng  = sum(ag)!=sum(fg)
say()
if not diff_ring and not diff_eng:
    say("  ⇒ **两项均无差异** ⇒ 按架构侧预写判读:**C-8b-stat 成立、C-8f 线闭合、μ 可取 0.40**")
    say("     (ERLE 29.1dB + 收敛最快)⇒ **CTO 不必拍任何取舍**。")
else:
    say("  ⇒ **出现差异** ⇒ 按预写判读:架构侧的拆分被证伪,回二选一,优先上 CTO 定产品取舍。")
    say("     ⚠ 但按纪律:先确认不是台架问题(F8 三连:前向增益≠环路增益 / 种子电平 / RIR 带限),再归因。")
io.open('results_w2_r14.txt','w',encoding='utf-8').write('\n'.join(OUT))
