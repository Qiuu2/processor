"""r63 · 给运行时不变量做 **broken 版** —— critic 下岗前点名要求的那一条。

critic 原话(经 lead 转):**「一条没对 broken 输入失败过的护栏,不算护栏,是一段注释。」**
并点名要核:**计数取的是【状态机转移】还是【轮询/帧数】—— 取错就恒不为 0,恒绿。**

本文件不产出任何性能数,只回答一个问题:
> **把不变量里的计数器换成"错的那种",它会不会【错误地放行】臂 O?**
> 会 ⇒ 说明现用计数器是承重的;不会 ⇒ 说明这条不变量根本没在判什么。

判据(先写死):
  正确计数器 `N2_lvl`(`nhs.py:404`,**仅在候选通过电平门后**自增)
      ⇒ 臂 O 必须 == 0(被 T_low=999 挡死),臂 N 必须 > 0
  broken-1 `ctr['slots']`(`nhs.py:365`,**每个分析槽无条件**自增)
  broken-2 `frame_i`     (`nhs.py:264`,**每帧无条件**自增)
  broken-3 `n_notch`     (已分配槽数 —— 臂 O 被预挂 8 个 ⇒ 恒 8)
      ⇒ 三者在臂 O 上都应 > 0 ⇒ **若用它们做不变量,臂 O 会被【错误地】判成"NHS 自选"**
      ⇒ 那正是 B-1 的形状:一个恒绿的护栏
[L2/宿主仿真]  deps: nhs.py@706b658842d84316, clrig.py@8ad47ce8d260dd18
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME
O=[]
def W(s):
    O.append(s); print(s); sys.stdout.flush()

T60, sd, BW, DEPTH, T = 0.2, 0, 0.2, -18.0, 4.0
h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
hb = band_limit(h0, 8000.); he = clrig.h_eff(hb)
picks = pick_excl(he, BW, 8)
src = 1e-3*np.random.default_rng(sd).standard_normal(int(T*FS))

def run(alg, G=-8.0):
    def pf(blk, _a=alg): return _a.process_frame(blk, GR)
    clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    return dict(N2_lvl=int(alg.ctr.get('N2_lvl',0)), slots=int(alg.ctr.get('slots',0)),
                frame_i=int(alg.frame_i),
                n_notch=len([s for s in alg.slots if s.st != nhs.NotchSlot.FREE]))

W("r63 · 运行时不变量的 broken 版(critic 点名项)")
W("deps: nhs.py@706b658842d84316 clrig.py@8ad47ce8d260dd18   [L2/宿主仿真]")
W("问题:把不变量的计数器换成『错的那种』,它会不会【错误地放行】臂 O?")
W("")
cO = run(mk_oracle(picks, BW, DEPTH))
n = NHS(); n.P.bw_oct = BW
cN = run(n)
W("%-12s %10s %10s | %s" % ('计数器','臂O(神谕)','臂N(自选)','用它做不变量的后果'))
W("-"*78)
rows = [
 ('N2_lvl',  'nhs.py:404 候选过电平门后自增 = 真·条件计数'),
 ('slots',   'nhs.py:365 每分析槽无条件自增'),
 ('frame_i', 'nhs.py:264 每帧无条件自增'),
 ('n_notch', '已分配槽数(臂O被预挂8个)'),
]
kill = 0
for k, desc in rows:
    o, nn = cO[k], cN[k]
    # 不变量语义:>0 ⇒ 判定为"NHS 自选在工作"
    wrong = (o > 0)          # 臂 O 本该判为"不是 NHS 自选";>0 即被错误放行
    verdict = ('⛔ 错误放行臂O ⇒ 恒绿' if wrong else '✅ 正确判臂O为『非NHS自选』')
    if k != 'N2_lvl' and wrong: kill += 1
    W("%-12s %10d %10d | %s" % (k, o, nn, verdict))
    W("             %s" % desc)
W("")
W("⇒ 现用计数器 N2_lvl:臂O=%d(须为0) 臂N=%d(须>0) ⇒ %s" % (
   cO['N2_lvl'], cN['N2_lvl'],
   'PASS(双向都对)' if cO['N2_lvl']==0 and cN['N2_lvl']>0 else '⛔ FAIL'))
W("⇒ broken 版杀死率 %d/3 —— 三种『错的计数器』中有 %d 种会让不变量恒绿" % (kill, kill))
W("")
W("⭐ 结论:承重的是 **N2_lvl**(条件计数),不是 n_notch。")
W("   若不变量只写 `n_notch > 0`,臂 O 会以 n_notch=%d 通过 ⇒ 与 B-1 同形。" % cO['n_notch'])
W("   ⇒ critic 的担心成立:**计数器选错,护栏就是一段注释。**")
open('/home/it1234/processor/01_design/prototype_W1P/r63_invariant_broken_out.txt','w').write("\n".join(O)+"\n")
