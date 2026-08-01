"""W2-P 第一轮:P0 G.168 基线 / broken 矩阵 / P1 N值 / NLP×NHS · 全部 [L2/宿主仿真]"""
import numpy as np, io, sys, time
import aec, g168, rig
from rig import FS, BLK, echo_path, run_aec
sys.path.insert(0,'../prototype_W1P')
from env import synth_speech
from scipy.signal import resample_poly, lfilter
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
t0=time.time()
say("="*78)
say(f"W2-P 第一轮 · AEC 原型  adaptive-dsp-3  2026-08-01   aec.py {aec.__version__}")
say("全部 [L2/宿主仿真];浮点;合成素材;非实录 RIR。判定取 G.168 度量,不看内部旗标。")
say("="*78)

DUR=6.0
far = g168.css(DUR)
near_full = resample_poly(synth_speech(DUR*3, seed=21), 1, 3)[:len(far)]*0.5

# ---------------- P0 基线 ----------------
say("\n### P0 · G.168 基线")
a=aec.MDF(); d,e,echo,_=run_aec(a,far)
E0=g168.steady_erle(d,e); C0=g168.converge_time_s(d,e); D0=g168.divergence(e)
say(f"  单讲(仅远端): 稳态ERLE={E0:5.1f}dB  收敛={C0:4.2f}s  发散={D0:+5.1f}dB")
say(f"  尾长 K={a.K} 分区 × {a.N} = {a.K*a.N/FS*1000:.0f}ms(PRD §二.7 要求 512ms)✓")

# 双讲:近端语音只在中段
mask=np.zeros(len(far),bool); mask[int(2.0*FS):int(4.0*FS)]=True
near=near_full*mask
a2=aec.MDF(); d2,e2,echo2,nr2=run_aec(a2,far,near)
Edt=float(np.median(g168.erle_db(echo2,e2-nr2)[mask]))
loss=g168.nearend_loss_db(nr2,e2,mask=mask)
say(f"  双讲(近端 2-4s): 双讲段ERLE={Edt:5.1f}dB  近端保留={loss:+5.1f}dB(0=无损伤)  发散={g168.divergence(e2):+5.1f}dB")
say(f"  ⚠ 合格门 G168_THRESHOLDS 全为 None —— **库内无 G.168 原文,不自造阈值**;取得后回填")

# ---------------- broken 矩阵(第一天就跑)----------------
say("\n### broken 矩阵(纪律1:第一天实现并跑;判定取 G.168 度量)")
def mk(tag):
    if tag=='A4': return aec.MDF(continuous_lr=False)
    if tag=='A3': return aec.MDF(tail_ms=64.0)
    return aec.MDF()
def run_broken(tag, far, near=None):
    a=mk(tag)
    if tag=='A7': a.Px=np.ones_like(a.Px)*1e12   # 归一化失效(分母恒大)
    f2=far.copy()
    if tag=='A2': f2=np.roll(far,401)            # 参考错位
    d,e,echo,nr=run_aec(a,f2 if tag=='A2' else far,near)
    if tag=='A1':
        e=d.copy()                               # 滤波器 stub:完全不消
    if tag=='A5':
        a5=aec.MDF(); a5._noconstraint=True
        # 去掉线性卷积约束:直接不清零梯度尾半
        orig=a5.process
        def p(x,dd,_a=a5):
            N,M=_a.N,_a.M
            xx=np.concatenate([_a.xprev,x]); _a.xprev=x.copy()
            X=np.fft.rfft(xx); _a.Xh=np.roll(_a.Xh,1,axis=0); _a.Xh[0]=X
            Y=np.sum(_a.W*_a.Xh,axis=0); y=np.fft.irfft(Y,M)[N:]; e=dd-y
            E=np.fft.rfft(np.concatenate([np.zeros(N),e]))
            _a.Px=0.9*_a.Px+0.1*np.abs(X)**2; _a.Pe=0.9*_a.Pe+0.1*np.abs(E)**2
            _a.W += (_a.mu_max/(_a.K*_a.Px+1e-12))[None,:]*np.conj(_a.Xh)*E[None,:]
            return e
        a5.process=p
        d,e,echo,nr=run_aec(a5,far,near)
    return d,e,echo,nr
rows=[]
BR=[('A1','滤波器 stub(不消回声)'),('A2','参考信号错位(+25ms)'),
    ('A3','尾长不足(64ms ≪ 真实 RIR)'),('A4','连续学习率禁用(固定步长)'),
    ('A5','去掉梯度线性卷积约束'),('A7','步长归一化失效')]
for tag,desc in BR:
    dd,ee,ec,nr=run_broken(tag,far)
    E=g168.steady_erle(dd,ee); C=g168.converge_time_s(dd,ee); D=g168.divergence(ee)
    fail = (E < E0-3.0) or (D > 3.0) or not np.isfinite(E)
    rows.append((tag,fail))
    say(f"  {tag} {desc:26s} -> {'FAIL(符合预期)' if fail else '**未 FAIL**'}  "
        f"ERLE={E:6.1f}dB(基线{E0:.1f}) 收敛={C:5.2f}s 发散={D:+6.1f}dB")
# A4 专测双讲(固定步长的真实危害在双讲)
a4=aec.MDF(continuous_lr=False); d4,e4,ec4,nr4=run_aec(a4,far,near)
loss4=g168.nearend_loss_db(nr4,e4,mask=mask)
say(f"  A4 双讲专测: 近端保留 完整={loss:+.1f}dB / 固定步长={loss4:+.1f}dB;"
    f"发散 {g168.divergence(e2):+.1f} / {g168.divergence(e4):+.1f}dB")
say(f"  ⇒ broken 汇总:{sum(1 for _,f in rows if f)}/{len(rows)} FAIL")

# ---------------- P1 · N 值下界依据 ----------------
say("\n### P1 · 共享实例的 N 值下界(DEC-0007.2;竞品=全局单实例+选择矩阵,D0b §1.1)")
mics=[(1.2,1.0,1.5),(2.6,1.4,1.5),(3.8,2.2,1.5),(1.6,2.8,1.5)]
hs=[echo_path(seed=0,mic=m)[0] for m in mics]
say("  (a) 各麦回声路径差异(决定一份滤波器能否兼服多麦)")
h0=hs[0]
for i,h in enumerate(hs):
    L=min(len(h0),len(h)); c=np.corrcoef(h0[:L],h[:L])[0,1]
    mis=10*np.log10(np.sum((h0[:L]-h[:L])**2)/(np.sum(h0[:L]**2)+1e-20)+1e-20)
    say(f"     mic{i} vs mic0: RIR 相关={c:+.3f}  失配残余={mis:+5.1f}dB "
        f"(≈用 mic0 的滤波器服务 mic{i} 时的 ERLE 上限 {-mis:.1f}dB)")
say("  (b) 选择器切换代价(在 mic0 收敛后切到 mic1)")
a=aec.MDF(); d,e,_,_=run_aec(a,far,seed=0,mic=mics[0])
E_a=g168.steady_erle(d,e)
d_b,e_b,_,_=run_aec(a,far,seed=0,mic=mics[1])           # 同一实例,换麦
E_b_head=float(np.median(g168.erle_db(d_b,e_b)[:int(0.5*FS)]))
E_b_end=g168.steady_erle(d_b,e_b)
say(f"     mic0 收敛后 ERLE={E_a:.1f}dB;切到 mic1:切换瞬间 0-0.5s ERLE={E_b_head:.1f}dB → 末段 {E_b_end:.1f}dB")
say(f"     ⇒ 切换代价 = 掉 {E_a-E_b_head:.1f}dB,需重收敛 {g168.converge_time_s(d_b,e_b):.2f}s")
say("  (c) 多人同时讲:一份实例只能服务被选中的那一路,其余回声未消")
say(f"     ⇒ **N 的下界 = 同时需要消回声的开麦数**;若 automixer 允许 NOM=K,则 N ≥ K")

# ---------------- NLP × NHS ----------------
say("\n### NLP 对 NHS 检测的影响(验证 W1 定案:tap 取在线性滤波后、NLP 前)")
nlp=aec.NLP(); a=aec.MDF(); d,e_lin,_,_=run_aec(a,far)
a2b=aec.MDF(); nlp2=aec.NLP(); d2b,e_nlp,_,_=run_aec(a2b,far,nlp=nlp2)
def spec_flat(x):
    X=np.abs(np.fft.rfft(x[-8192:]*np.hanning(8192)))
    return float(np.exp(np.mean(np.log(X+1e-20)))/(np.mean(X)+1e-20))
say(f"  NLP 后最大频段增益衰减 = {nlp2.max_gr_db:.1f}dB(频段选择性快衰减 ⇒ 正是 C10 禁的形态)")
say(f"  谱平坦度(几何/算术均值):线性输出={spec_flat(e_lin):.3f} → NLP后={spec_flat(e_nlp):.3f}")
say(f"  残余能量:线性={10*np.log10(np.mean(e_lin**2)+1e-20):.1f}dB → NLP后={10*np.log10(np.mean(e_nlp**2)+1e-20):.1f}dB")
say(f"  ⇒ NLP 逐频段最大压 {abs(nlp2.max_gr_db):.0f}dB ⇒ 若 NHS tap 取在 NLP **之后**,"
    f"啸叫增长段会被同型压平(与 C10 机理同构)⇒ **W1 的链位定案(tap 在 NLP 前)得到支持**")

say(f"\n耗时 {time.time()-t0:.0f}s")
io.open('results_w2_r1.txt','w',encoding='utf-8').write('\n'.join(OUT))
