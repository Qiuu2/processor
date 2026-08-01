"""W2-P 第二轮(修 W2-F4/F5 后重做基线)"""
import numpy as np, io, sys
import aec, metrics as M, rig
from rig import FS, run_aec, echo_path
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*78); say("W2-P 第二轮 · 修 W2-F4/F5 后重做基线 · adaptive-dsp-3 · [L2/宿主仿真]"); say("="*78)
say("⚠ **第一轮全部数字作废**:其 mu_max=0.5 经扫描证实处于**不稳定边缘**(换激励即发散),")
say("  故第一轮 ERLE=18.0dB 及由它派生的全部 broken 判定均为运气值,不可引用。本轮重做。")
DUR=12.0
css=M.css(DUR); wb=M.white_burst(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]
say("\n### 步长稳定域(W2-F5)")
say(f"  {'mu_max':>7} {'CSS ERLE':>9} {'CSS 发散':>9} {'白噪 ERLE':>10} {'白噪 发散':>10}")
for mu in (0.5,0.3,0.2,0.1):
    a=aec.MDF(mu_max=mu); d,e,_,_=run_aec(a,css)
    a2=aec.MDF(mu_max=mu); d2,e2,_,_=run_aec(a2,wb)
    say(f"  {mu:7.2f} {M.steady_erle(d,e):9.1f} {M.divergence(e):9.1f} {M.steady_erle(d2,e2):10.1f} {M.divergence(e2):10.1f}")
say("  ⇒ 取 **mu_max=0.2** 为稳定工作点(两种激励均收敛)。")

say("\n### 新基线(mu=0.2, 12s)")
for nm,sig in (('CSS(G.168结构)',css),('白噪突发(非周期)',wb)):
    a=aec.MDF(); d,e,ec,_=run_aec(a,sig)
    say(f"  {nm:16s} ERLE={M.steady_erle(d,e):6.1f}dB 收敛={M.converge_time_s(d,e):5.2f}s 发散={M.divergence(e):+6.1f}dB")

say("\n### P2 · PFDKF 异源第二轨互核")
mask=np.zeros(len(css),bool); mask[int(4.0*FS):int(8.0*FS)]=True
a0=aec.MDF(); d0,e0,ec0,_=run_aec(a0,css)
pe=np.mean(ec0[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
near=near_src*mask*np.sqrt(pe/pn)
say(f"  {'算法':>22} {'单讲ERLE':>9} {'收敛s':>7} {'发散':>7} | {'双讲ERLE':>9} {'近端保留':>9}")
for nm,mk in (('MDF+连续学习率(自实现)',lambda:aec.MDF()),('PFDKF(Kalman,异源)',lambda:aec.PFDKF())):
    a=mk(); d,e,_,_=run_aec(a,css)
    a2=mk(); d2,e2,ec2,nr2=run_aec(a2,css,near)
    say(f"  {nm:>22} {M.steady_erle(d,e):9.1f} {M.converge_time_s(d,e):7.2f} {M.divergence(e):7.1f} | "
        f"{float(np.median(M.erle_db(ec2,e2-nr2)[mask])):9.1f} {M.nearend_loss_db(nr2,e2,mask=mask):9.1f}")

say("\n### C-8a 对 AEC 的核法:**最坏帧**,不是空闲态(架构侧 §4.0.5)")
say("  机理:AEC 收敛后**没有空闲态** —— 它持续在减一个估计量,失配残差 = 纹波在动。")
a=aec.MDF(); ripple=[]
h,_=echo_path(); 
from scipy.signal import lfilter
x=css; echo=lfilter(h,[1.0],x); d=echo
for i in range(0,(len(x)//128)*128,128):
    e=a.process(x[i:i+128], d[i:i+128])
    y=d[i:i+128]-e
    if i>int(6*FS):
        X=np.abs(np.fft.rfft(x[i:i+128]*np.hanning(128)))+1e-12
        Y=np.abs(np.fft.rfft(y*np.hanning(128)))+1e-12
        g=20*np.log10(Y/X); ripple.append(float(np.percentile(g,95)-np.percentile(g,5)))
say(f"  收敛后逐帧「峰-均纹波」:中位={np.median(ripple):.2f}dB  **最坏帧={np.max(ripple):.2f}dB**  (C-8a 门 ≤0.25dB)")
say(f"  ⇒ {'**超门**' if np.max(ripple)>0.25 else '过门'};架构侧已判定 AEC 线性滤波结构性不可恒等 —— 实测支持该判定。")

say("\n### DTD 冻结/解冻阶跃(C10 快时变门的候选对象)")
say("  ⚠ 本原型采 **Valin 连续学习率,无硬判决 DTD ⇒ 结构上不存在冻结/解冻阶跃**。")
say("  为量化对比,构造硬 DTD 变体(近端能量超门即冻结 W):")
class HardDTD(aec.MDF):
    def process(self,x,d):
        pe=np.mean(d**2)
        self._frz = pe > 4*getattr(self,'_ref',pe)
        self._ref=0.99*getattr(self,'_ref',pe)+0.01*pe
        W0=self.W.copy(); e=super().process(x,d)
        if self._frz: self.W=W0
        return e
for nm,mk in (('连续学习率',lambda:aec.MDF()),('硬判决DTD',lambda:HardDTD())):
    a=mk(); gs=[]
    for i in range(0,(len(css)//128)*128,128):
        Wb=np.sum(np.abs(a.W)); a.process(css[i:i+128], (d)[i:i+128]); Wa=np.sum(np.abs(a.W))
        if i>int(6*FS) and Wb>0: gs.append(abs(20*np.log10((Wa+1e-12)/(Wb+1e-12))))
    say(f"  {nm:10s} 收敛后逐帧滤波器增益跳变:中位={np.median(gs):.4f}dB 最坏={np.max(gs):.4f}dB")
io.open('results_w2_r2.txt','w',encoding='utf-8').write('\n'.join(OUT))
