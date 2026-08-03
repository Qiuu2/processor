"""r78a · `bw_oct_match` 默认关的**逐位等价**实跑对照(+ 阳性对照)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r78.txt。
输出 r78a_bitexact_out.txt(D6-j 路径唯一)。

被证的两件(缺一不可,D6-y 双向):
  ① `bw_oct_match=None`(默认)⇒ 与改前 `nhs.py` **逐位相同**
     —— 靠实跑逐位比对,⛔ 不靠"读起来一样"
  ② **阳性对照**:强制 `bw_oct_match` 取别的值 ⇒ **必须出现差异**
     —— 否则说明开关根本没接上,①的"相同"就毫无意义(r77 的教训:器械要能失败)

⚠ 改前行为的基准怎么来:`bw_oct_match=None` 时 `_bw_hz` 的表达式**逐字回落**到
  `max(f*P.bw_oct, 15.0)`,即改前那一行。故 ①的对照臂 = 用一个**独立重实现**的
  `_bw_hz`(直接写死改前表达式)monkey-patch 回去 ⇒ 两臂比对 = 新代码 vs 改前代码。
"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME

BW_OCT = 1 / 5
F_CUT = 8000.
T_OBS = 3.0
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DG = [1.0, 3.0]
SRC = [-20., -60.]
DIR = '/home/it1234/processor/01_design/prototype_W1P/'
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def run(hb, D, G, src, match, legacy):
    """legacy=True ⇒ 把 `_bw_hz` 换成【改前那一行的独立重实现】。"""
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = -45.
    a.P.bw_oct_match = match
    if legacy:
        # 改前原文:return max(f * self.P.bw_oct, 15.0)
        a._bw_hz = lambda f, _a=a: max(f * _a.P.bw_oct, 15.0)
    y, lp = clrig.Loop(hb, D, G, proc=lambda b, _a=a: _a.process_frame(b, GR)).run(src, FRAME)
    used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
    return dict(y=y, lp=lp,
                ctr={k: v for k, v in sorted(a.ctr.items())},
                slots=sorted((round(float(s.f), 6), round(float(s.depth), 6), int(s.st))
                             for s in used))


def cmp(r1, r2):
    d = []
    if not np.array_equal(r1['y'], r2['y']):
        d.append('y')
    if not np.array_equal(r1['lp'], r2['lp']):
        d.append('loop')
    if r1['ctr'] != r2['ctr']:
        d.append('ctr')
    if r1['slots'] != r2['slots']:
        d.append('slots')
    return d


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r78a · `bw_oct_match` 默认关的逐位等价 + 阳性对照  [L2/宿主仿真]")
    W("预注册 = PREREG_r78.txt。⚠ 器械必须能失败(r77 教训)⇒ 阳性对照与等价对照同等必报。")
    W(f"工作点:T_OBS={T_OBS:.0f}s / bw_oct=1/5 / T_low=−45 / ΔG∈{DG} / src∈{[int(x) for x in SRC]}")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'src':>6}{'ΔG':>5} | {'①默认关 vs 改前':>22} | {'②阳性(match=1/12)':>24}")
    n_eq = n_eq_tot = n_pos = n_pos_tot = 0
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        from msg_meter import MSGMeter
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        for L in SRC:
            src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (L / 20.))
            for dg in DG:
                G = anchor + dg
                a_new = run(hb, D, G, src, None, False)      # 新代码,默认关
                a_old = run(hb, D, G, src, None, True)       # 改前那一行(独立重实现)
                a_pos = run(hb, D, G, src, 1 / 12., False)   # 阳性:只动匹配窗
                d1 = cmp(a_new, a_old)
                d2 = cmp(a_new, a_pos)
                n_eq_tot += 1
                n_pos_tot += 1
                if not d1:
                    n_eq += 1
                if d2:
                    n_pos += 1
                W(f"{T60:>5.1f}{sd:>4}{int(L):>6}{dg:>+5.0f} | "
                  f"{('✅逐位相同' if not d1 else '⛔差异于 ' + ','.join(d1)):>22} | "
                  f"{('✅出现差异于 ' + ','.join(d2) if d2 else '⛔(无差异)'):>24}")
    W("")
    W(f"  ① 默认关 vs 改前:**{n_eq}/{n_eq_tot} 逐位相同** ⇒ {'PASS' if n_eq == n_eq_tot else '⛔ FAIL,立即回滚 nhs.py'}")
    W(f"  ② 阳性对照(强制 match=1/12):**{n_pos}/{n_pos_tot} 出现差异** ⇒ "
      f"{'PASS(比对器有分辨力且开关确实接上了)' if n_pos > 0 else '⛔ FAIL:开关没接上 ⇒ ①的「相同」无意义'}")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r78a_bitexact_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
