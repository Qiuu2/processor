"""P0 · D6-d 回溯检查:W1 承重度量的空对照(拿掉被测物,数应归零)
adaptive-dsp-3 · 2026-08-02 · [L2/宿主仿真]
口诀:能失败的对照才是对照。恒等自比/时移不变量/无区分力阈值,一律不计为证据。
"""
import numpy as np, io, hashlib, os
from experiments import *
from env import synth_speech, synth_music, synth_transients, env_db, FS, FRAME
from nhs import NHS, Params
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
def sha(p):
    return hashlib.sha256(io.open(p,'rb').read()).hexdigest()[:16]
say("deps: nhs.py@%s, env.py@%s, experiments.py@%s" % (sha('nhs.py'),sha('env.py'),sha('experiments.py')))
say("="*96); say("W1-P · D6-d 回溯空对照 · [L2/宿主仿真]"); say("="*96)
res=[]
def verdict(name, expect, got, ok, note=""):
    res.append((name, ok))
    say(f"  [{'✓' if ok else '**✗ 对照失守**'}] {name}")
    say(f"        预期={expect}   实测={got}   {note}")

# ---- 1 抑制量:陷波器组整个 bypass ⇒ 抑制量应归零 ----
say("\n### 1. 抑制量(原报 40.7dB)· 拿掉陷波器组")
_,_ = None,None
a_full=NHS(); out_f,_=scen_ramp(a_full); m_f=metrics(out_f)
a_byp =NHS(broken=['B2']); out_b,_=scen_ramp(a_byp); m_b=metrics(out_b)   # B2=深度恒0
out_n,_=scen_ramp(Bypass()); m_n=metrics(out_n)
supp_full=m_n['end_db']-m_f['end_db']; supp_null=m_n['end_db']-m_b['end_db']
verdict("抑制量", "陷波 bypass 后 ≈0dB", f"{supp_null:+.1f}dB(完整版 {supp_full:+.1f}dB)",
        abs(supp_null)<3.0)

# ---- 2 挂陷数:检测器 stub ⇒ 应为 0 ----
say("\n### 2. 挂陷数 · 拿掉检测器")
a_s=NHS(broken=['B1']); scen_ramp(a_s)
verdict("挂陷数", "检测器 stub ⇒ 0", f"{n_engage(a_s)}(完整版 {n_engage(a_full)})", n_engage(a_s)==0)

# ---- 3 ★ 误报套件:拿掉素材(喂静音)⇒ 应为 0 ----
say("\n### 3. ★ 误报套件 · 拿掉素材(喂静音/纯底噪)")
rng=np.random.default_rng(0)
for nm, mat in (('静音(全零)', np.zeros(int(10*FS))),
                ('纯底噪 −80dBFS', 1e-4*rng.normal(0,1,int(10*FS)))):
    a=NHS(); scen_open(a, mat)
    verdict(f"误报@{nm}", "0 次挂陷", f"{n_engage(a)} 次", n_engage(a)==0)
a_mus=NHS(); scen_open(a_mus, synth_music(10.0))
say(f"        (对照:音乐素材 {n_engage(a_mus)} 次 ⇒ 该度量{'**有区分力**' if n_engage(a_mus)>0 else '**无区分力**'})")

# ---- 4 啸叫类指标:环路增益设到不可能起啸 ----
say("\n### 4. 啸叫类指标 · 环路增益 −40dB(不可能起啸)")
h,d=rir(); src=0.02*rng.normal(0,1,int(6*FS))
lp=ClosedLoop(h,d,Bypass(),g_pre_db=0,g_fwd_db=-40.0)
_,o,_=lp.run(src); mn=metrics(o)
verdict("窄带集中度", "不起啸 ⇒ 低窄带(<0.25)", f"nb={mn['nb']:.3f} 末={mn['end_db']:.1f}dB",
        mn['nb']<0.25, f"(起啸场景 nb={m_n['nb']:.3f})")

# ---- 5 B-F1 tap 电平:限幅器旁路 ⇒ 钉住现象应消失 ----
say("\n### 5. B-F1 钉住 · 拿掉限幅器")
_,tap_lim=scen_pinned(Bypass())
h2,d2=rir(); h2=h2*10**((3.0-50.0)/20.0)
src2=1e-5*rng.normal(0,1,int(10*FS))
lp2=ClosedLoop(h2,d2,Bypass(),g_pre_db=0,g_fwd_db=50.0,limiter=None)
_,o2,tap_nolim=lp2.run(src2)
e_lim=env_db(scen_pinned(Bypass())[0]); e_no=env_db(o2)
flat_lim=float(np.std(e_lim[int(4*FS):])); flat_no=float(np.std(e_no[int(4*FS):]))
verdict("钉住(输出包络被钉平)", "无限幅器 ⇒ 不再钉平(包络方差显著变大或发散)",
        f"有限幅器 std={flat_lim:.2f}dB / 无限幅器 std={flat_no:.2f}dB",
        flat_no > flat_lim*2 or not np.isfinite(flat_no))

# ---- 6 PAPR/PNPR:把峰抹掉 ⇒ 应塌到底噪 ----
say("\n### 6. PAPR/PNPR · 把峰整个抹掉")
alg=NHS(); NB=513; DF=16000.0/1024
s=-95.+rng.normal(0,1.5,NB); kh=int(round(2500./DF))
Mwith=10**(s/20.); Mwith[kh]=10**(-56./20.)
Mno  =10**(s/20.)                      # 无峰
pa_w,pn_w=alg._papr(Mwith,kh),alg._pnpr(Mwith,kh)
pa_n,pn_n=alg._papr(Mno,kh),  alg._pnpr(Mno,kh)
verdict("PAPR", "无峰 ⇒ 塌到底噪(<门 15dB)", f"有峰={pa_w:.1f} 无峰={pa_n:.1f}dB", pa_n<15.0)
verdict("PNPR", "无峰 ⇒ 塌到底噪(<门 8dB)",  f"有峰={pn_w:.1f} 无峰={pn_n:.1f}dB", pn_n<8.0)

ok=sum(1 for _,v in res if v)
say(f"\n### 汇总:{ok}/{len(res)} 条对照守住")
if ok<len(res):
    say("  ⇒ **失守的对照 = 该度量测的不是它声称的东西**,相关结论须撤回或重述。")
io.open('results_w1p_r8.txt','w',encoding='utf-8').write('\n'.join(OUT))
