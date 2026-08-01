"""P2:maintenance 直读为何 readback_ok=0 —— 是缺场景,还是本产品形态下走不到?"""
import numpy as np, io
from multi import MultiLoop
from env import synth_speech, FS
from nhs import NHS, Params
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
class Nop:
    events=[];slots=[];ctr={}
    def process_frame(self,x,gr=None): return x
    def duck_gain(self): return 1.0

say("\n"+"="*76); say("P2 · maintenance 直读路径诊断"); say("="*76)
DUR=18.0
ml=MultiLoop(n_ch=2,g_fwd_db=[45.0,0.0],loop_gain_db=[3.0,-60.0],
             bus_thr_db=0.0,dyn_thr_db=[-42.0,-6.0])
a0=NHS()
# 拦截:记录每次进入"被挤出候选表"分支时的 PAPR/PNPR
probe=[]
orig=a0._track_missing
def wrapped(tr,M,df,table_full,min_cand_mag,gr_ok):
    k=int(round(tr.f/df))
    if 0<k<len(M)-1 and table_full and M[k]<min_cand_mag:
        probe.append((round(a0._papr(M,k),1), round(a0._pnpr(M,k),1), round(a0._level(M,k),1)))
    return orig(tr,M,df,table_full,min_cand_mag,gr_ok)
a0._track_missing=wrapped
src0=synth_speech(DUR,seed=3)*0.35+1e-5*np.random.default_rng(0).normal(0,1,int(DUR*FS))
ml.run([a0,Nop()],[src0,np.zeros(int(DUR*FS))],DUR)
P=a0.P
say(f"  进入'被挤出候选表'分支 {len(probe)} 次;门:PAPR≥{P.T_papr} ∧ PNPR≥{P.T_pnpr}")
if probe:
    pa=np.array([p[0] for p in probe]); pn=np.array([p[1] for p in probe])
    say(f"  该分支内 PAPR 分布: 中位={np.median(pa):6.1f} p90={np.percentile(pa,90):6.1f} 最大={pa.max():6.1f}")
    say(f"  该分支内 PNPR 分布: 中位={np.median(pn):6.1f} p90={np.percentile(pn,90):6.1f} 最大={pn.max():6.1f}")
    say(f"  仅 PAPR 过门比例 = {np.mean(pa>=P.T_papr)*100:.1f}%")
    say(f"  仅 PNPR 过门比例 = {np.mean(pn>=P.T_pnpr)*100:.1f}%")
    say(f"  现行(PAPR∧PNPR)过门比例 = {np.mean((pa>=P.T_papr)&(pn>=P.T_pnpr))*100:.1f}%")
say(f"  实测 readback_ok = {a0.ctr['readback_ok']}, unobs = {a0.ctr['unobs']}")
io.open('results_r4.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
