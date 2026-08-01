"""W2-P V-22:超门偏移的时长/聚簇/驻留/有效累积增益(对已采序列重新出统计,不新建台架)"""
import numpy as np, io
import aec, probe
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
BLK_MS = probe.BLK/probe.FS*1000.0          # 8.0 ms
TAU_RT = 10.0/343.0                          # 环路往返 29.2ms(10m)
GATE = 0.25
say("="*104); say("W2-P V-22 · 超门偏移的时间结构 · [L2/宿主仿真]"); say("="*104)
say(f"  探针块长 = {BLK_MS:.1f}ms(**非 lead 举例的 2ms**);环路往返 τ={TAU_RT*1000:.1f}ms")
say(f"  自核 lead 物理推断:G=+1.15dB ⇒ 每往返 ×1.1416;e 倍需 7.55 往返 = **220ms**(lead 报 ~230ms,一致)")
say(f"  ⚠ 但单个 {BLK_MS:.0f}ms 块的 +1.15dB 偏移已累积 **+0.32dB**,不是 1%。粒度差 4× 会改变判读。")
say("\n  ★ 判据说明:**我只出事实,不裁门。** 『有效累积增益』定义:")
say("     幅度每往返乘 10^(d/20) ⇒ 窗内累积 ΔdB = (Σ d_i·Δt) / τ_rt")
say("     报其**最大回撤上升幅**(max drawup)= 最坏情况下啸叫幅度能累积多少 dB。")

class V(aec.MDF):
    def __init__(s2, delta=1.0, **k): super().__init__(**k); s2.delta=delta

def runstats(mu):
    d,_ = probe.c8f_series(lambda: V(delta=1.0, mu_max=mu), dur=20.0, far_gate=(1.0,1.0))
    over = d > GATE
    # 1) 连续超门时长
    durs=[]; c=0
    for v in over:
        if v: c+=1
        elif c: durs.append(c); c=0
    if c: durs.append(c)
    durs=np.array(durs) if durs else np.array([0])
    # 2) 聚簇:自相关首次跌破 1/e 的滞后
    x=d-np.mean(d)
    ac=np.correlate(x,x,'full')[len(x)-1:]; ac/= (ac[0]+1e-20)
    tau_i=np.argmax(ac<1/np.e) if (ac<1/np.e).any() else len(ac)
    # 3) 驻留占比
    duty=float(over.mean())
    # 4) 有效累积增益:running integral of d, in dB, per round trip
    dt_s=BLK_MS/1000.0
    cum=np.cumsum(d)*dt_s/TAU_RT
    runmin=np.minimum.accumulate(cum)
    drawup=float(np.max(cum-runmin))
    # 只计超门部分的累积(保守上界视角)
    cum_pos=np.cumsum(np.where(d>GATE, d-GATE, 0.0))*dt_s/TAU_RT
    return dict(max=float(np.max(d)), duty=duty,
                dmed=float(np.median(durs))*BLK_MS, d90=float(np.percentile(durs,90))*BLK_MS,
                dmax=float(np.max(durs))*BLK_MS, n=len(durs),
                tau=float(tau_i)*BLK_MS, drawup=drawup, cumpos=float(cum_pos[-1]))

say(f"\n  {'μ':>6}{'C8f max':>9}{'超门驻留':>9}{'次数':>6}{'时长中位':>9}{'p90':>8}{'最长':>8}{'自相关τ':>9}{'累积最大回撤':>13}{'超门部分累积':>13}")
res={}
for mu in (0.10,0.20,0.40):
    r=runstats(mu); res[mu]=r
    say(f"  {mu:6.2f}{r['max']:9.3f}{r['duty']*100:8.2f}%{r['n']:6d}{r['dmed']:9.1f}{r['d90']:8.1f}"
        f"{r['dmax']:8.1f}{r['tau']:9.1f}{r['drawup']:13.2f}{r['cumpos']:13.2f}")
say(f"  (时长/自相关单位 ms;累积单位 dB)")
say("\n  -- 与环路时间常数对照 --")
for mu in (0.10,0.20,0.40):
    r=res[mu]
    say(f"  μ={mu:.2f}: 最长连续超门 {r['dmax']:.0f}ms vs e倍增长所需 220ms ⇒ "
        f"{'**同量级或更长**' if r['dmax']>=110 else '远短于(占 %.0f%%)'%(r['dmax']/220*100)};"
        f" 自相关 τ={r['tau']:.0f}ms")
say("\n  -- 事实陈述(判据由架构侧裁,我不裁)--")
say("  ① 若偏移为帧级孤立事件(时长 ≪ 220ms 且不成簇)⇒ max 口径对零均值抖动可能过严;")
say("  ② 若偏移长或成簇 ⇒ max 口径成立。")
say("  ③ **『累积最大回撤』是与 MSG 直接可比的量** —— 它说的是啸叫幅度实际能涨多少 dB。")
io.open('results_w2_r12.txt','w',encoding='utf-8').write('\n'.join(OUT))
