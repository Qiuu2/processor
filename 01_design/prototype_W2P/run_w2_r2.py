"""W2-P 第二轮:P3 非周期激励 / P2 PFDKF 异源第二轨 / P1 N 值完整量化"""
import numpy as np, io, sys, importlib
import aec, metrics as M, rig
from rig import FS, run_aec, echo_path
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly, lfilter
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*78); say("W2-P 第二轮 · adaptive-dsp-3 · 2026-08-01 · 全部 [L2/宿主仿真]"); say("="*78)
DUR=6.0
say("\n### P0 结果 · CSS 已对 G.168 Annex C 原文核实(L4 → L1)")
for k,(v,src) in M.CSS_SPEC.items(): say(f"  {k:11s} = {str(v):6s}  {src}")
say(f"  合格阈值 = {M.G168_THRESHOLDS} ⇒ **仍待 P.340/P.341/G.161,不填**")

say("\n### P3 · 延迟类 broken 必须用非周期激励(W2-F3 落进设计)")
for nm, sig in (('CSS(周期 750ms)', M.css(DUR)), ('白噪突发(非周期)', M.white_burst(DUR))):
    a=aec.MDF(); d,e,_,_=run_aec(a,sig); E0=M.steady_erle(d,e)
    row=[]
    for ms in (100, 400, 750, 1500):
        n=int(ms*1e-3*FS); a2=aec.MDF()
        d2,e2,_,_=run_aec(a2,sig,ref=np.roll(sig,n))
        row.append(f"{ms}ms:{M.steady_erle(d2,e2):5.1f}")
    say(f"  {nm:18s} 基线={E0:5.1f}dB  错位后 ERLE → {' '.join(row)}")
say("  ⇒ 若某激励下『错位 750ms』与基线接近,即该激励的周期性使延迟测试失真。")

say("\n### P2 · PFDKF 异源第二轨(铁律七:两条独立推导互核)")
far=M.white_burst(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(far)]
mask=np.zeros(len(far),bool); mask[int(2.0*FS):int(4.5*FS)]=True
a0=aec.MDF(); d0,e0,ec0,_=run_aec(a0,far)
say(f"  {'算法':>16} {'单讲ERLE':>9} {'收敛s':>7} {'发散dB':>8} | 双讲(近端/回声=0dB): {'ERLE':>6} {'近端保留':>9} {'发散':>7}")
pe=np.mean(ec0[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
near=near_src*mask*np.sqrt(pe/pn)
for nm,mk in (('MDF+连续学习率(自实现)',lambda:aec.MDF()), ('PFDKF(Kalman,异源)',lambda:aec.PFDKF())):
    a=mk(); d,e,_,_=run_aec(a,far)
    a2=mk(); d2,e2,ec2,nr2=run_aec(a2,far,near)
    Edt=float(np.median(M.erle_db(ec2,e2-nr2)[mask]))
    say(f"  {nm:>16} {M.steady_erle(d,e):9.1f} {M.converge_time_s(d,e):7.2f} {M.divergence(e):8.1f} | "
        f"{Edt:19.1f} {M.nearend_loss_db(nr2,e2,mask=mask):9.1f} {M.divergence(e2):7.1f}")
say("  ⇒ 两轨若同向且量级相当 ⇒ 互核通过;若分歧 ⇒ 至少一条实现有错,须查。")

say("\n### P1 · N 值完整量化(同时开麦场景;接第一轮的下界依据)")
mics=[(1.2,1.0,1.5),(2.6,1.4,1.5),(3.8,2.2,1.5),(1.6,2.8,1.5)]
say("  场景:K 支麦同时开,共享 N 份 AEC 实例(选择器把前 N 支接入)")
say(f"  {'K(同时开麦)':>12} {'N=1 平均ERLE':>13} {'N=K 平均ERLE':>13} {'未服务麦的ERLE':>14}")
for K in (1,2,3,4):
    # N=K:每麦一份实例
    erle_full=[]
    for j in range(K):
        a=aec.MDF(); d,e,_,_=run_aec(a,far,mic=mics[j]); erle_full.append(M.steady_erle(d,e))
    # N=1:一份实例服务 mic0,其余麦回声未消
    a=aec.MDF(); d,e,_,_=run_aec(a,far,mic=mics[0])
    served=M.steady_erle(d,e); unserved=[]
    for j in range(1,K):
        d2,e2,_,_=run_aec(a,far,mic=mics[j])     # 复用已收敛于 mic0 的实例
        unserved.append(M.steady_erle(d2,e2))
    n1=np.mean([served]+unserved) if unserved else served
    say(f"  {K:12d} {n1:13.1f} {np.mean(erle_full):13.1f} "
        f"{(np.mean(unserved) if unserved else float('nan')):14.1f}")
say("  ⇒ 未服务麦的 ERLE ≈ 0 或负 ⇒ **共享实例对未被选中的麦完全无效**;")
say("    N 必须 ≥ 同时需要消回声的开麦数(与 automixer 的 NOM 上限挂钩)。")
io.open('results_w2_r2.txt','w',encoding='utf-8').write('\n'.join(OUT))
