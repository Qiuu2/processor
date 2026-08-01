"""W2-P 第四轮:三项补测(均值/方差分水岭)· 全部对**已采数据重新出统计**,不重跑台架"""
import numpy as np, io
import aec, probe
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*80); say("W2-P 第四轮 · 三项补测 · adaptive-dsp-3 · [L2/宿主仿真]"); say("="*80)
say("目的:判 **均值支 vs 方差支** —— 决定后面是花 MSG 预算,还是改我的稳健拟合。")
say("纪律:绝不能用一个 max 统计量买一条产品规格(架构侧原话,我认)。")
MU=0.2; DUR=10.0

# ---------------- 补测① C-8g 各电平 median/std ----------------
say("\n### 补测① · C-8g 各电平的 median 与 std(均值/方差分水岭)")
say(f"  {'探针dBFS':>9} {'max':>8} {'median':>9} {'std':>8}   判读")
res,_ = probe.c8g(lambda: aec.MDF(mu_max=MU), dur=DUR)
prev=None
for L,mx,med,sd in res:
    tag = ''
    if prev is not None:
        tag = f"(相邻档 Δmedian={med-prev[0]:+.3f} Δstd={sd-prev[1]:+.3f})"
    say(f"  {L:9.0f} {mx:8.3f} {med:9.3f} {sd:8.3f}   {tag}")
    prev=(med,sd)
meds=[r[2] for r in res]; sds=[r[3] for r in res]
say(f"  ⇒ median 跨电平极差 = {max(meds)-min(meds):.3f}dB;std 跨电平极差 = {max(sds)-min(sds):.3f}dB")
say(f"  ⇒ **判定:{'方差支(median 平坦、std 随电平变)' if (max(meds)-min(meds)) < 0.5*(max(sds)-min(sds)) else '均值支或混合(median 亦随电平变)'}**")
# 架构侧关切的 −45→−25 段
d45 = [r for r in res if r[0]==-45.0][0]; d25 = [r for r in res if r[0]==-25.0][0]
say(f"  ⇒ 架构侧点名的 −45→−25 段:Δmax={d25[1]-d45[1]:+.3f}dB  **Δmedian={d25[2]-d45[2]:+.3f}dB**  Δstd={d25[3]-d45[3]:+.3f}dB")
say(f"     若 Δmedian ≈ 0 ⇒ 该段塌缩**不是**真实斜坡压平(不花 MSG);若 Δmedian 显著 ⇒ 均值支成立。")

# ---------------- 补测② C-8f 远端有活动 / 静默 二分 ----------------
say("\n### 补测② · C-8f 按「远端有活动 / 远端静默」二分(方案④a 的收益上限)")
d, fm = probe.c8f_series(lambda: aec.MDF(mu_max=MU), dur=DUR, far_gate=(1.0,1.0))
thr = np.median(fm)*0.1
act = fm > thr; sil = ~act
say(f"  远端门控 1s 开/1s 合;活动块 {act.sum()} / 静默块 {sil.sum()}")
for nm, m in (('远端有活动', act), ('远端静默', sil)):
    if m.sum() < 5: continue
    say(f"  {nm:8s} max={np.max(d[m]):+7.3f}dB  median={np.median(d[m]):+7.3f}dB  std={np.std(d[m]):6.3f}dB")
say(f"  全段 max={np.max(d):+7.3f}dB")
if sil.sum()>5 and act.sum()>5:
    contrib = np.max(d[sil]) - np.max(d[act])
    say(f"  ⇒ 静默段 max 比活动段高 {contrib:+.3f}dB")
    say(f"  ⇒ **方案④a(远端静默即冻结)的收益上限**:若全局 max 由静默段贡献,冻结后 max 降到")
    say(f"     活动段水平 = {np.max(d[act]):+.3f}dB{'(仍超门)' if np.max(d[act])>0.25 else '(**过门**)'}")

# ---------------- 补测③ C-8f′ 窗平均后取 max ----------------
say("\n### 补测③ · C-8f′ 窗平均后再取 max(零均值抖动的瞬时尖峰应被平掉)")
d2, _ = probe.c8f_series(lambda: aec.MDF(mu_max=MU), dur=DUR)
say(f"  探针块长 = {probe.BLK/probe.FS*1000:.0f}ms;IMSD 分析窗 W_long×T_hop = 8×16 = 128ms = 16 块")
say(f"  {'窗长':>10} {'窗平均后 max':>13}")
for wb, lbl in ((1,'瞬时(1块)'),(2,'16ms'),(4,'32ms'),(8,'64ms'),(16,'128ms(=IMSD窗)'),(32,'256ms')):
    say(f"  {lbl:>10} {probe.c8f_windowed(d2, wb):13.3f}")
say("  ⇒ 若 max 随窗长迅速塌向 0 ⇒ 确认是零均值抖动(方差支);若窗平均后仍超门 ⇒ 均值支。")
io.open('results_w2_r4.txt','w',encoding='utf-8').write('\n'.join(OUT))
