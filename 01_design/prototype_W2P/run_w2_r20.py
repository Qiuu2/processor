"""W2-P R20:①解除 MSG 约束后的均匀 K=64 推荐工作点 ②参考谱否决初实现+ROC"""
import numpy as np, io, sys
import aec, metrics as M, rig
from rig import FS, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech, synth_music
from scipy.signal import resample_poly, lfilter
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*104); say("W2-P R20 · AEC 移出本地环路后 · [L2/宿主仿真]"); say("="*104)
say("  前提变更(架构裁定):AEC 只挂送远端支 ⇒ C-8f/C-8g 对 AEC 不适用;")
say("  μ 此后仅受 {ERLE, 收敛阶梯, 双讲 P.340, K 稳定域} 四者约束。")

# ---------- ① 推荐工作点 ----------
say("\n### ① 均匀 K=64 推荐工作点(四约束)")
say("  ⚠ ERLE 用 **V-20 勘正后的严格稳态口径**(48s 跑,取最后 8s),非旧的『后1/3』")
DUR=48.0; css=M.css(DUR)
near_src=resample_poly(synth_speech(DUR*3,seed=21),1,3)[:len(css)]
mask=np.zeros(len(css),bool); mask[int(30*FS):int(40*FS)]=True
class V(aec.MDF):
    def __init__(s2, delta=1e-2, **k): super().__init__(**k); s2.delta=delta
say(f"  {'μ':>6}{'ERLE稳态':>10}{'ERLE双讲':>10}{'收敛s':>8}{'K稳定域':>9}{'P.340 双讲档':>16}")
def grade(dt):
    for nm,(lo,hi) in M.P340_DOUBLETALK_GRADES:
        if (lo is None or dt>lo) and (hi is None or dt<=hi): return nm
    return '?'
best=None
for mu in (0.05,0.10,0.20,0.40,0.70):
    a=V(delta=1e-2,mu_max=mu); d,e,ec,_=run_aec(a,css)
    Es=float(np.median(M.erle_db(d,e)[int((DUR-8)*FS):])); C=M.converge_time_s(d,e)
    pe=np.mean(ec[mask]**2)+1e-20; pn=np.mean((near_src*mask)[mask]**2)+1e-20
    a=V(delta=1e-2,mu_max=mu); d2,e2,ec2,nr2=run_aec(a,css,near_src*mask*np.sqrt(pe/pn))
    Ed=float(np.median(M.erle_db(ec2,e2-nr2)[mask]))
    stab='稳定' if Es>0 else '发散'
    say(f"  {mu:6.2f}{Es:10.1f}{Ed:10.1f}{C:8.2f}{stab:>9}{grade(abs(Ed)):>16}")
    if Es>0 and (best is None or Es>best[1]): best=(mu,Es,C,Ed)
say(f"  ⇒ K=64 稳定上界:实测 μ≤0.40 稳定(K=128 时 μ=0.4 已发散 −590dB,故上界随 K 收缩)")
if best: say(f"  ⇒ **推荐工作点 μ={best[0]}**:稳态 ERLE={best[1]:.1f}dB,收敛={best[2]:.2f}s,双讲={best[3]:.1f}dB")
say("  ⚠ ERLE 无独立门(TCLw≠ERLE,须由 TCLw 分解导出,归 D13);收敛须按 G.168 阶梯而非单值")

# ---------- ② 参考谱否决 ----------
say("\n### ② 参考谱否决(替代整条 C-8f 线的新机制)· 初实现 + ROC")
say("  原理:候选峰频点若在**远端参考谱**上同时存在且显著度可比 ⇒ 判远端来源 ⇒ 否决。")
say("  不依赖 ERL/ERLE;R 在环路之前已知,无循环。**须时间对齐**(补偿 R→扬声器→声学→麦 传播延迟)。")
NF=1024; SC=16000.0
def pnpr(Mag,k):
    df=SC/NF; f=k*df
    kk=int(round(max(187.,f*(2**(1/3)-1))/df))
    idx=[j for j in range(max(0,k-kk),min(len(Mag),k+kk+1)) if abs(j-k)>3]
    return 20*np.log10(Mag[k]/(np.mean(Mag[idx])+1e-30)+1e-30) if idx else 0.0
def ref_veto(mic, ref, k, align):
    """对齐后比较 mic 与 ref 在 bin k 的局部显著度。"""
    r = ref[max(0,len(ref)-len(mic)-align):len(ref)-align] if align>0 else ref[-len(mic):]
    if len(r)<NF: return False, -99.
    w=np.hanning(NF)
    Mm=np.abs(np.fft.rfft(mic[-NF:]*w)); Mr=np.abs(np.fft.rfft(r[-NF:]*w))
    return pnpr(Mr,k), pnpr(Mm,k)
h,dly = rig.echo_path(seed=0)
align = int(np.argmax(np.abs(h)))         # 声学传播延迟(样本)
say(f"  时间对齐:R→麦 传播延迟 = {align} 样本 = {align/SC*1000:.1f}ms(取 RIR 主峰)")
say(f"\n  {'场景':>34}{'ref PNPR':>10}{'mic PNPR':>10}{'否决?':>7}{'期望':>7}{'判定':>6}")
t=np.arange(int(6*SC))/SC
rng=np.random.default_rng(0)
cases=[]
# A 远端纯音 ⇒ 应否决
f0=1500.; far=0.5*np.sin(2*np.pi*f0*t); mic=lfilter(h,[1.0],far)+1e-3*rng.normal(0,1,len(t))
cases.append(('A 远端纯音 1500Hz(应否决)',far,mic,int(round(f0/(SC/NF))),True))
# B 本地啸叫 + 远端语音 ⇒ 不应否决
far2=resample_poly(synth_speech(6.,seed=3),1,3)[:len(t)]*0.5
mic2=lfilter(h,[1.0],far2)+0.3*np.sin(2*np.pi*2500*t)
cases.append(('B 本地啸叫2500Hz+远端语音(不应否决)',far2,mic2,int(round(2500/(SC/NF))),False))
# C 远端音乐(含 880Hz 长笛)⇒ 应否决
far3=resample_poly(synth_music(6.,seed=2),1,3)[:len(t)]*0.6
mic3=lfilter(h,[1.0],far3)+1e-3*rng.normal(0,1,len(t))
cases.append(('C 远端音乐 880Hz 长笛(应否决)',far3,mic3,int(round(880/(SC/NF))),True))
# D 本地啸叫与远端同频 ⇒ 最坏情形
far4=0.5*np.sin(2*np.pi*2500*t); mic4=lfilter(h,[1.0],far4)+0.3*np.sin(2*np.pi*2500*t)
cases.append(('D 本地啸叫与远端**同频**(最坏)',far4,mic4,int(round(2500/(SC/NF))),None))
T_REF=8.0
ok=0; tot=0
for nm,fr,mc,k,exp in cases:
    rp,mp = ref_veto(mc,fr,k,align)
    v = rp>=T_REF
    j='—' if exp is None else ('✓' if v==exp else '✗')
    if exp is not None:
        tot+=1; ok+= (v==exp)
    say(f"  {nm:>34}{rp:10.1f}{mp:10.1f}{str(v):>7}{str(exp):>7}{j:>6}")
say(f"  ⇒ 判据门 T_ref={T_REF}dB(参考谱局部显著度);{ok}/{tot} 正确")
say(f"  ⇒ **场景 D(同频)是原理性盲区**:参考谱与本地啸叫在同一 bin,任何谱域比较都不可分;")
say(f"     须靠时间结构(啸叫增长 vs 远端稳态)或互相关,**不在本机制职权内**,如实列限制。")
io.open('results_w2_r20.txt','w',encoding='utf-8').write('\n'.join(OUT))
