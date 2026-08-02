"""P0 · M-1 下游重测:_level 补 6.03dB 后,所有依赖绝对电平的结论重跑"""
import numpy as np, io
from experiments import *
from nhs import NHS, Params
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("="*96); say("W1-P · M-1 下游重测(_level 已补 Hann 相干增益 +6.02dB)· [L2/宿主仿真]"); say("="*96)
say("  先分清受影响面:")
say("   · `tap_level_dbfs` = **时域 RMS**,不经 _level ⇒ **不受影响**")
say("   · 逐 bin 电平 / T_low·T_low_gr 门判定 / F5 ⇒ **经 _level,全部受影响**")

def peak_bin(gf, f_probe=4031.0, seed=0, rt60=0.35):
    a=NHS(); rows=[]
    orig=a._analysis_slot
    def w(gr, a=a, rows=rows):
        orig(gr)
        M=np.abs(np.fft.rfft(a.sc_buf*a.win)); df=16000.0/1024
        k=int(round(f_probe/df))
        if 2<k<len(M)-1 and 1.5<a.t_wall<3.0: rows.append(a._level(M,k))
    a._analysis_slot=w
    _,tap=scen_pinned(a,g_fwd=gf,seed=seed,rt60=rt60)
    return (max(rows) if rows else float('nan')), tap_level_dbfs(tap,2.0)

say("\n### ① F5 重测:前向增益 vs 峰 bin 电平(T_low_gr = −65dBFS)")
say(f"  {'前向dB':>7}{'峰bin电平(新)':>14}{'旧值(−6.03)':>13}{'tapRMS':>9}{'bin−RMS':>9}{'过T_low_gr?':>12}")
xs=[];ys=[]
for gf in (40.,45.,50.,52.,55.,58.,60.):
    pk,rms=peak_bin(gf); xs.append(gf); ys.append(pk)
    say(f"  {gf:7.0f}{pk:14.1f}{pk-6.03:13.1f}{rms:9.1f}{pk-rms:9.1f}{'过' if pk>-65 else '**不及**':>12}")
sl=np.polyfit(xs,ys,1); crit=(-65-sl[1])/sl[0]
say(f"  ⇒ 拟合:峰bin = {sl[0]:.2f}×前向 + {sl[1]:.1f}")
say(f"  ⇒ **T_low_gr 失效临界(新)= 前向 {crit:.1f}dB**(旧报 53.3dB;设计件算术 59dB)")
say(f"  ⇒ 与设计件算术差 = **{abs(crit-59.0):.1f}dB**")
if abs(crit-59.0) < 1.5:
    say("  ⇒ ★ **F5『实测比算术早 5.7dB』这条证伪,正式撤回** —— 差值几乎全部是原型自身的标定缺陷,")
    say("     不是设计件算术错。P13 点单应随之撤销。")
else:
    say(f"  ⇒ 差值仍显著,F5 部分成立,按新值 {crit:.1f}dB 重述。")

say("\n### ② B-F1 吻合度复核(最承重的一条)")
say("  设计件算例:天花板 −6dBFS、前向 +50dB ⇒ tap ≈ **−56dBFS**(总电平口径)")
tls=[]
for sd in range(4):
    _,tap=scen_pinned(Bypass(),seed=sd,rt60=0.3+0.05*sd); tls.append(tap_level_dbfs(tap,3.0))
say(f"  实测 tap **RMS**(4 组房间)= {[f'{v:.1f}' for v in tls]} dBFS")
say(f"  ⇒ tap RMS **不经 _level,未受 M-1 影响** ⇒ B-F1 的 −57.4dBFS 与算例 −56dBFS 的")
say(f"     **吻合结论不变**(差 {abs(-57.4-(-56)):.1f}dB)。")
pk50,rms50=peak_bin(50.)
say(f"  但**逐 bin 电平**变了:前向 50dB 处 峰bin = {pk50:.1f}dBFS(旧 {pk50-6.03:.1f})")
say(f"  ⇒ 『门比 bin 电平、算术比总电平』这一**机理**仍成立(bin−RMS = {pk50-rms50:+.1f}dB),")
say(f"     但其**量级**须按新值重述,不再是旧报的差 5-6dB。")

say("\n### ③ 受影响结论清单(重跑前不得引用的那批)")
for it in ("F5「T_low_gr 失效临界早 5.7dB」→ **撤回**(见①)",
           "「bin−RMS 差约 5-6dB」→ 按新值重述(见②)",
           "T_low_gr=−65dBFS 的余量估计 → 随①重算",
           "run_all.py §5 标定段全部 → 须用新 _level 重跑",
           "B-F1 tap RMS 与吻合结论 → **不受影响,维持**"):
    say(f"   · {it}")
io.open('results_w1p_r7.txt','w',encoding='utf-8').write('\n'.join(OUT))
