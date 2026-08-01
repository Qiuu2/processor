"""W2-P 收口:阈值回填后重出候选工作点表(补 NLP 承担列)"""
import numpy as np, io, sys
import aec, metrics as M, rig, probe
from rig import FS, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*100); say("W2-P C-8f 线收口 · 验收阈值已回填(P.341 原文)· [L2/宿主仿真]"); say("="*100)
say("\n### 验收阈值(L4/待核 → **L1/标准原文**;我方逐字核过 PDF,不采信转述)")
for k,(v,src) in M.ACCEPT_THRESHOLDS.items():
    say(f"  {k:20s} = {str(v):6s}  {src}")
say("\n  ⚠ 三条使用限定(lead 给的两条 + 我核原文多找到的两条):")
say("    ① TCLw ≠ ERLE(整机耦合损耗 = 声学ERL + AEC线性ERLE + NLP抑制),不得直接当 ERLE 门;")
say("    ② P.340 无数值门(其 §10.3.2.1 指向 P.341);P.340 的 [20 dB] 带方括号=ITU 暂定值,非硬门;")
say("    ③ **附加义务**:音量控制须每次通话后自动复位至标称,除非最大音量下也能保持 TCLw≥46dB;")
say("    ④ stability loss ≥6dB 须在 **100–8000Hz 全频段 且 全部接收音量档位**上成立。")

DUR=12.0; css=M.css(DUR)
class V(aec.MDF):
    def __init__(s2, delta=1e-2, **k): super().__init__(**k); s2.delta=delta
PX={'对称':dict(),'攻0.3/放0.95':dict(px_attack=0.3,px_release=0.95),
    'δ+攻0.5/放0.99':dict(px_attack=0.5,px_release=0.99)}
say("\n### 候选工作点(两项分列 + **NLP 承担列**)")
say("  NLP 需补 = TCLw(46) − 声学ERL − AEC线性ERLE。**声学 ERL 归整机设计,本原型 RIR 已按")
say("  最大频响归一(最不利频点 ERL≈0dB)⇒ 不代表真实整机。故按 ERL ∈ {0,6,12}dB 三档并列。**")
say(f"  {'工作点':>26}{'C-8f':>13}{'ERLE-CSS':>9}{'ERLE-双讲':>10}{'NLP需补@ERL=0':>14}{'@6':>7}{'@12':>7}")
cands=[(0.2,'攻0.3/放0.95',1e-2),(0.2,'对称',1.0),(0.4,'攻0.3/放0.95',1e-1),
       (0.4,'对称',1.0),(0.7,'攻0.3/放0.95',1e-2),(0.7,'对称',1.0)]
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]
mask=np.zeros(len(css),bool); mask[int(4.0*FS):int(8.0*FS)]=True
for mu,pn_,dl in cands:
    fac=lambda: V(delta=dl,mu_max=mu,**PX[pn_])
    d,_=probe.c8f_series(fac,dur=8.0,far_gate=(1.0,1.0)); mx=float(np.max(d))
    a=fac(); dd,e,ec,_=run_aec(a,css); Ec=M.steady_erle(dd,e)
    pe=np.mean(ec[mask]**2)+1e-20; pn2=np.mean((near_src*mask)[mask]**2)+1e-20
    a=fac(); d2,e2,ec2,nr2=run_aec(a,css,near_src*mask*np.sqrt(pe/pn2))
    Ed=float(np.median(M.erle_db(ec2,e2-nr2)[mask]))
    gate='过门' if mx<=0.25 else '超%.1f×'%(mx/0.25)
    say(f"  {('μ%.1f %s δ%.2g'%(mu,pn_,dl)):>26}{('%.2f %s'%(mx,gate)):>13}{Ec:9.1f}{Ed:10.1f}"
        f"{46-0-Ec:14.1f}{46-6-Ec:7.1f}{46-12-Ec:7.1f}")
say("\n### ★ 本轮最重要的耦合链(此前无人连起来)")
say("  把 AEC 线性级 ERLE 压下去 ⇒ 剩余担子全部转给 **NLP**;")
say("  而 NLP 正是 **C10 管辖的那个元件**(频段选择性快衰减,实测最大 −40.1dB),")
say("  **必须留在 NHS tap 下游**。⇒ 三者构成闭链:")
say("     C-8f 门(NHS可检出性)↓ 收紧 → AEC 线性 ERLE ↓ → NLP 承担 ↑ → C10 压力 ↑ + 音质代价 ↑")
say("  ⇒ **不能只在 AEC 内部找工作点**;C-8f 的每一 dB 都会以 NLP 抑制量的形式重新出现。")
say("  ⇒ 且 NLP 抑制量本身还受 stability loss ≥6dB(全频段/全音量档)与双讲档次(P.340 Table 4)双重约束。")
say("\n### 双讲品质定档(P.340 Table 4;分级不是门)")
for nm,(lo,hi) in M.P340_DOUBLETALK_GRADES:
    say(f"  {nm:14s} 双讲衰减 {('≤%.0f'%hi) if lo is None else (('>%.0f'%lo) if hi is None else '%.0f–%.0f'%(lo,hi))} dB")
io.open('results_w2_r9.txt','w',encoding='utf-8').write('\n'.join(OUT))
