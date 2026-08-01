"""W2-P 第五轮 P0-a:验证 lead 的「过渡块」假设 —— 调制峰是否集中在 静默→活动 之后若干块?"""
import numpy as np, io
import aec, probe
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*80); say("W2-P 第五轮 · P0 步长归一化的静默/间歇行为 · [L2/宿主仿真]"); say("="*80)
say("\n### P0-a · 验证「过渡块」假设(lead 提出,我验)")
say("  假设:调制峰集中在『静默→活动』过渡之后若干块 ⇒ 根因是 Px 估计的攻击/释放不对称")
say("        (功率在信号回来时跟不上 ⇒ 分母偏小 ⇒ 头几块步长过大),而非『静默时在学』。")
say("  这与 ④a(静默即冻结)无效的观测一致:损害不在静默块里。")
d, fm = probe.c8f_series(lambda: aec.MDF(mu_max=0.2), dur=12.0, far_gate=(1.0,1.0))
thr = np.median(fm[fm>0])*0.1 if (fm>0).any() else 1e-9
act = fm > thr
# 找 静默→活动 的过渡点
trans = np.where((~act[:-1]) & (act[1:]))[0] + 1
say(f"  远端门控 1s/1s;总块 {len(d)};静默→活动过渡 {len(trans)} 次;全段 max={np.max(d):+.3f}dB")
say(f"  {'相对过渡的块偏移':>16} {'该位置 |d| 中位':>15} {'该位置 max':>11}")
for off in (0,1,2,3,4,6,8,12,16,24):
    vals=[abs(d[t+off]) for t in trans if 0 <= t+off < len(d)]
    if vals:
        say(f"  {('+%d 块(%dms)'%(off,off*8)):>16} {np.median(vals):15.3f} {np.max(vals):11.3f}")
# 对照:远离过渡的稳态活动块
far_from = np.ones(len(d), bool)
for t in trans:
    lo,hi=max(0,t-2),min(len(d),t+25); far_from[lo:hi]=False
steady = far_from & act
say(f"  {'稳态活动块(远离过渡)':>16} {np.median(np.abs(d[steady])):15.3f} {np.max(np.abs(d[steady])):11.3f}")
say(f"  {'静默块':>16} {np.median(np.abs(d[~act])):15.3f} {np.max(np.abs(d[~act])):11.3f}")
top=np.argsort(-np.abs(d))[:20]
near=[min([abs(int(t)-int(i)) for t in trans]) if len(trans) else -1 for i in top]
say(f"  最大 20 个调制峰到最近过渡点的块距:中位={np.median(near):.0f} 块({np.median(near)*8:.0f}ms) "
    f"最小={np.min(near):.0f} 最大={np.max(near):.0f}")
say(f"  ⇒ 假设{'**成立**(峰集中在过渡后数块内)' if np.median(near)<=8 else '**不成立**(峰不集中在过渡附近)'}")
io.open('results_w2_r5.txt','w',encoding='utf-8').write('\n'.join(OUT))
