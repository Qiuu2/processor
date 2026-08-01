"""W2-P V-23:D 的标度律(√n vs 线性)/ C-8f″ 250ms 窗均 / E[g] 交叉验证
全部对已采序列重新出统计,零新台架。"""
import numpy as np, io
import aec, probe
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
BLK_MS=probe.BLK/probe.FS*1000.0; TAU=10.0/343.0; GATE=0.25; T_H=0.250
say("="*104); say("W2-P V-23 · D 标度律 / C-8f″ / E[g] · [L2/宿主仿真]"); say("="*104)
say(f"  块长 {BLK_MS:.1f}ms;往返 τ={TAU*1000:.1f}ms;C-8f″ 窗 T_H={T_H*1000:.0f}ms = {T_H*1000/BLK_MS:.1f} 块")
say("  ⚠ 自核量纲:stability loss = dB/**往返**(P.341 单趟损耗),D = **纯量 dB**(跨 n 往返求和)。")
say("     二者不可直接比。**我上轮给 D 贴的『与 MSG 直接可比』标签是错的** —— 是那个标签把对照引过去的。")
say("     代回包络方程:μ=0.10 的 D=5.51 需 ~1800 往返(52s),同区间 M·n=10800dB ⇒ D 湮没。架构侧判对。")

class V(aec.MDF):
    def __init__(s2, delta=1.0, **k): super().__init__(**k); s2.delta=delta

def analyze(mu, dur=40.0):
    d,_=probe.c8f_series(lambda: V(delta=1.0,mu_max=mu), dur=dur, far_gate=(1.0,1.0))
    dt=BLK_MS/1000.0
    # --- ① D 的标度律:对运行前缀逐段算 D
    cum=np.cumsum(d)*dt/TAU
    runmin=np.minimum.accumulate(cum)
    draw=cum-runmin                       # 每一点的当前回撤
    Ds=[]; ns=[]
    for n in np.unique(np.logspace(1.3, np.log10(len(d)-1), 14).astype(int)):
        Ds.append(float(np.max(draw[:n]))); ns.append(int(n))
    ns=np.array(ns); Ds=np.array(Ds)
    ok=Ds>0
    slope=np.polyfit(np.log(ns[ok]), np.log(Ds[ok]), 1)[0] if ok.sum()>3 else float('nan')
    # --- ② C-8f″:250ms 窗均后取 max
    wb=max(1,int(round(T_H*1000/BLK_MS)))
    k=np.ones(wb)/wb
    c8f2=float(np.max(np.convolve(d,k,mode='valid')))
    # --- ③ E[g] 算术均值
    Eg=float(np.mean(d))
    # --- ④ 漂移率(若线性):dB/往返
    drift=Eg*dt/TAU
    return dict(max=float(np.max(d)), c8f2=c8f2, Eg=Eg, slope=slope, drift=drift,
                ns=ns, Ds=Ds, n_tot=len(d))

say(f"\n### ① D 的标度律(无漂移 ⇒ D∝√n,指数≈0.5;有正漂移 ⇒ D∝n,指数≈1.0)")
say(f"  {'μ':>6}{'样本数':>8}{'log-log 斜率':>13}{'判定':>22}")
R={}
for mu in (0.10,0.20,0.40):
    r=analyze(mu); R[mu]=r
    if np.isnan(r['slope']): j='无法判定'
    elif r['slope']<0.70: j='**√n(无漂移)**'
    elif r['slope']>0.85: j='**线性(有漂移)**'
    else: j='介于两者之间'
    say(f"  {mu:6.2f}{r['n_tot']:8d}{r['slope']:13.3f}{j:>22}")
say(f"\n  D vs n 明细(μ=0.10):")
r=R[0.10]
say("    n     = "+" ".join(f"{v:7d}" for v in r['ns'][:8]))
say("    D(dB) = "+" ".join(f"{v:7.2f}" for v in r['Ds'][:8]))

say(f"\n### ② C-8f″(T_H=250ms 窗均后取 max;门 0.25dB)vs 架构侧预测")
pred={0.10:0.10, 0.20:0.25, 0.40:1.5}
say(f"  {'μ':>6}{'C-8f max(旧口径)':>18}{'C-8f″(250ms窗均)':>19}{'架构侧预测':>11}{'实测/预测':>10}{'门':>6}")
for mu in (0.10,0.20,0.40):
    r=R[mu]
    say(f"  {mu:6.2f}{r['max']:18.3f}{r['c8f2']:19.3f}{pred[mu]:11.2f}"
        f"{r['c8f2']/pred[mu]:10.2f}{'✓过' if r['c8f2']<=GATE else '✗超':>6}")

say(f"\n### ③ E[g] 交叉验证(dB 域算术均值)+ ④ 漂移率")
say(f"  {'μ':>6}{'E[g] (dB)':>12}{'漂移率 (dB/往返)':>18}{'与 M=6dB/往返 比':>18}")
for mu in (0.10,0.20,0.40):
    r=R[mu]
    say(f"  {mu:6.2f}{r['Eg']:12.5f}{r['drift']:18.6f}{r['drift']/6.0*100:17.4f}%")
say("  ⇒ 若 E[g]>0 且 D 判为线性 ⇒ 该漂移是**永久的每往返裕度消耗**,加窗不赦免,须直接计入 C-8b。")
say("  ⇒ 若 E[g]≈0 且 D∝√n ⇒ 无永久消耗,C-8f″ 加窗判据成立。")

say(f"\n### ⚠ 方法学限制(必须随数字一起报)")
say(f"  ① **max 不是稳定统计量,随观测时长增长**:同一 μ=0.40,10s 跑得 0.793、20s 跑得 1.781。")
say(f"     ⇒ 任何以 max 为门的判据都隐含一个观测时长约定;C-8f″ 的窗均缓解但未消除这一点。")
say(f"  ② 探针分辨率 = {BLK_MS:.0f}ms ⇒ 『时长中位 8.0ms』是**分辨率下限,不是真实中位**。")
say(f"     若要论证 μ=0.10 放行,须 ≤2ms 分辨率重跑(架构侧已列为非急项)。")
io.open('results_w2_r13.txt','w',encoding='utf-8').write('\n'.join(OUT))
