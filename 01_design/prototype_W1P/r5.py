"""第五轮:P0 音乐预设+间歇掩蔽(给三条机制翻案机会);P1 B9 护栏定标"""
import numpy as np, io
from multi import MultiLoop
from env import synth_speech, synth_music, synth_transients, env_db, FS, FRAME
from nhs import NHS, Params
from experiments import metrics, howling, n_engage, rir, scen_step, Bypass
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
class Nop:
    events=[];slots=[];ctr={}
    def process_frame(self,x,gr=None): return x
    def duck_gain(self): return 1.0

say("="*78); say("第五轮 · P0 音乐预设+间歇掩蔽(翻案跑) / P1 B9 护栏定标"); say("="*78)
say("判据取输出信号(末包络/窄带/挂陷/复发后加深);计数器仅辅助。全部 [L2/宿主仿真]。")

# ---------------- P0:音乐预设 + 间歇掩蔽 ----------------
DUR=24.0
def music_preset(**kw):
    return Params(P_persist_s=2.5, persist_hit_rate=0.80, T_papr=18.0, T_pnpr=10.0,
                  bw_oct=1/10, max_depth=-12.0, D_harm=30.0, **kw)

def masker(dur, on=1.0, off=1.0, amp=0.55, seed=11):
    """间歇掩蔽源:语音+音乐混合(真实感强于稳态噪声),按 on/off 周期开合。"""
    m = synth_speech(dur, seed=seed)*0.6 + synth_music(dur, seed=seed+1)*0.6
    m = m + synth_transients(dur, seed=seed+2, kind='clap')*0.3
    t = np.arange(len(m))/FS
    g = ((t % (on+off)) < on).astype(float)
    from scipy.signal import lfilter
    g = lfilter(np.ones(int(0.03*FS))/int(0.03*FS),[1.0],g)
    return m*g*amp

def rig_music(brk, on=1.0, off=1.0, amp=0.55, seed=11):
    ml = MultiLoop(n_ch=2, g_fwd_db=[45.0,0.0], loop_gain_db=[3.0,-60.0],
                   bus_thr_db=0.0, dyn_thr_db=[-42.0,-6.0])
    a0 = NHS(P=music_preset(), broken=brk)
    src0 = masker(DUR,on,off,amp,seed) + 1e-5*np.random.default_rng(0).normal(0,1,int(DUR*FS))
    bus,taps,chs,tr = ml.run([a0,Nop()], [src0, np.zeros(int(DUR*FS))], DUR)
    return a0, metrics(chs[0]), chs[0]

say("\n### P0 · 音乐预设(P_persist=2.5s / 命中率门 80%)+ 间歇掩蔽(1s 开 / 1s 合)")
say("  假说:重新获取变贵(需重攒 2.5s 驻留)⇒ 三态若有用,应在此显出收益")
base=None
for tag,desc in ((None,'完整版'),(['B10'],'B10 broken'),(['B11'],'B11 broken'),(['B12'],'B12 broken')):
    a,m,ch = rig_music(tag)
    c=a.ctr
    if base is None: base=m
    d_end = m['end_db']-base['end_db']
    say(f"  {desc:12s} 末={m['end_db']:7.1f}dB nb={m['nb']:.3f} 挂陷={n_engage(a):2d} 在啸={howling(m)} "
        f"| Δ末={d_end:+5.1f}dB")
    say(f"  {'':12s} 未观测={c['unobs']:5d} 直读={c['readback_ok']:3d} 影子新={c['shadow_new']:3d} "
        f"继承={c['shadow_inherit']:3d} U_max={c['umax_hit']:3d}")

say("\n  -- 掩蔽占空扫描(检验收益是否藏在某个占空比)--")
for on,off in ((0.5,0.5),(1.0,1.0),(2.0,1.0),(1.0,3.0)):
    af,mf,_ = rig_music(None,on,off); ab,mb,_ = rig_music(['B10'],on,off)
    say(f"     掩蔽 {on:.1f}s开/{off:.1f}s合: 完整 末={mf['end_db']:6.1f}/nb{mf['nb']:.3f}/挂陷{n_engage(af):2d} | "
        f"B10 末={mb['end_db']:6.1f}/nb{mb['nb']:.3f}/挂陷{n_engage(ab):2d} | Δ末={mb['end_db']-mf['end_db']:+5.1f}dB")

# ---------------- P1:B9 护栏定标 ----------------
say("\n### P1 · B9 空号护栏定标(gap_guard_ratio 扫描;跳槽降档场景)")
say("  护栏语义:窗内 span+1 > ratio×W_long 即拒判。ratio 越大越宽松(越少拒判)")
def skip_run(ratio, brk=None):
    a = NHS(P=Params(gap_guard_ratio=ratio), broken=brk)
    a.skip_plan = set(s for s in range(1,4000) if (s//3)%2==1)
    out,_ = scen_step(a)
    return a, metrics(out)
say(f"  {'ratio':>6} {'峰包络':>9} {'末包络':>9} {'挂陷':>5} {'护栏拒判':>9}")
for r in (1.5, 2.0, 3.0, 4.0, 6.0, 999.0):
    a,m = skip_run(r)
    say(f"  {r:6.1f} {m['peak_db']:9.1f} {m['end_db']:9.1f} {n_engage(a):5d} {a.ctr['gapguard']:9d}")
ab,mb = skip_run(2.0, ['B9'])
say(f"  {'B9破':>6} {mb['peak_db']:9.1f} {mb['end_db']:9.1f} {n_engage(ab):5d} {'-':>9}  (朴素 x 轴,忽略空号)")
io.open('results_r5.txt','w',encoding='utf-8').write('\n'.join(OUT))
say("\n(results_r5.txt 已落盘)")
