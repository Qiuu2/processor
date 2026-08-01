"""B9 补跑:slot_seq x 轴修正的价值主张必须转到**误报侧**才成立——测它。
闭环侧已实测:朴素 x 轴(算错)反而更早检出(峰包络低 11.7dB)。
CHECK E 说朴素口径会把慢升虚警成 GROWTH ⇒ 代价应出现在**误报**上。跳槽下测。"""
import numpy as np, io
from env import synth_speech, synth_music, synth_transients, FS, FRAME
from nhs import NHS, Params
from experiments import n_engage
OUT=[]
def say(s=''):
    print(s); OUT.append(s)
say("\n### P1b · slot_seq x 轴修正的**误报侧**代价(跳槽降档下开环误报套件)")
say("  闭环侧结论:朴素 x 轴更早检出(峰包络 -16.2 vs -4.5dB)。若修正有价值,应体现在误报少。")
def open_run(mat, brk, skip=True, ratio=3.0):
    a = NHS(P=Params(gap_guard_ratio=ratio), broken=brk)
    if skip:
        a.skip_plan = set(s for s in range(1,4000) if (s//3)%2==1)
    n=(len(mat)//FRAME)*FRAME
    for i in range(0,n,FRAME):
        a.process_frame(mat[i:i+FRAME], {'out_lim_active':False,'out_lim_gr_db':0.0,'dyn_active':False})
    return a
mats = [('语音', synth_speech(12.0)), ('音乐(含长笛)', synth_music(12.0)),
        ('掌声', synth_transients(12.0,kind='clap')), ('咳嗽', synth_transients(12.0,kind='cough'))]
say(f"  {'素材':14s} {'正确x轴(跳槽)':>16s} {'朴素x轴(跳槽)':>16s} {'正确x轴(不跳槽)':>18s}")
tot_c=tot_n=0
for nm, m in mats:
    ac=open_run(m,None); an=open_run(m,['B9']); a0=open_run(m,None,skip=False)
    ec,en,e0 = n_engage(ac), n_engage(an), n_engage(a0)
    tot_c+=ec; tot_n+=en
    say(f"  {nm:14s} {ec:16d} {en:16d} {e0:18d}")
say(f"  {'合计误挂':14s} {tot_c:16d} {tot_n:16d}")
say(f"  ⇒ 误报侧差异 = {tot_n-tot_c:+d} 次(正数=朴素口径更容易误挂,即修正有价值)")
io.open('results_r5.txt','a',encoding='utf-8').write('\n'+'\n'.join(OUT))
