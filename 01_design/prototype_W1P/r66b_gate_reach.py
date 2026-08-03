"""r66b · **诊断 r66a 的 Hb2 失败** —— 是"开关没接上"、"比对器无分辨力",还是"这条旁路根本没被走过"?

⛔ 未经 critic 评审。[L2/宿主仿真]。输出:r66b_gate_reach_out.txt (D6-j)

════════════════════════════════════════════════════════════════════
背景:`r66a` 的结果
  Hb1(默认关 vs 原件)   **54/54 逐位相同**
  Hb2(强制开 vs 原件)   **0/54 出现差异**  ⇒ 按 r66a 预注册,**整件作废,不得据 Hb1 放行**
三个互斥假说,本件用**直接观测**分开(LESSONS B-2:能直接看就别推断):
  (a) 开关没接上 —— 我改的那行没生效
  (b) 比对器无分辨力 —— 它其实没在比东西
  (c) **`rapid_onset` 那条 OR 旁路在这些工作点上【从未被走过】**
      ⇒ `(imsd_hit ∨ rapid_onset)` 与 `imsd_hit` 给出相同结果 ⇒ 开关接上了也看不出差别
      ⇒ **若为 (c),则修法 ① 在这些工作点上是【空操作】**,
        = `PREREG_r66.txt` Hs3(a) 预写的那一类阴性结论,只是提前一步到达。

════════════════════════════════════════════════════════════════════
两项直接观测(跑前写死判据)
════════════════════════════════════════════════════════════════════
**观测 1 · 可达性计数(在真实闭环里)**
  `_imsd` 只在 `_classify` 内被调用一处(`nhs.py:863`,已 grep 核实)
  ⇒ 包装 `_imsd` 即可在**判据求值的那一刻**记录 `(imsd_hit, tr.rapid_onset, tr.relaxed)`。
  关键量 = **`N_bypass` = #{ imsd_hit=False ∧ rapid_onset=True ∧ relaxed=False }**
  —— **这是开关唯一能改变结果的那一格**。
  判读:`N_bypass == 0` ⇒ **(c) 成立**,开关在这些工作点上无从生效。

**观测 2 · 接线测试(构造一个开关【应该】响应的输入)**
  子类覆写:`_imsd` 恒返 `(False, ...)`(旁路成为唯一入口)+ `_update_tracks` 后把所有轨的
  `rapid_onset` 置 True ⇒ **人为把 `N_bypass` 拉到非零**。
  然后比 `growth_and_gate` 关/开 的 GROWTH 分类数。
  判读:**两者必须不同**。相同 ⇒ **(a) 或 (b) 成立**,须回滚 `nhs.py` 并报 lead。
  ⚠ 本观测**不是性能测量**,是**对开关本身的 broken 版**:它构造的是一个不真实的输入,
    唯一目的是证明「这个开关确实控制着那条分支」。⛔ 其数不得作任何性能引用。

⛔ 本文件不写结论散文。
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit

GR = {'out_lim_active': False, 'out_lim_gr_db': 0.0}
FRAME, BW, T = 64, 1 / 5, 6.0
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DELTAS = [-1.0, 1.0, 3.0]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def run_counted(alg, hb, D, G, src):
    """包装 `_imsd`,在判据求值那一刻记录三元组。返回可达性计数。"""
    log = []
    orig = alg._imsd

    def wrapped(tr, _o=orig, _l=log):
        r = _o(tr)
        _l.append((bool(r[0]), bool(tr.rapid_onset), bool(tr.relaxed)))
        return r
    alg._imsd = wrapped

    def pf(blk, _a=alg):
        return _a.process_frame(blk, GR)
    clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    n_eval = len(log)
    n_ro = sum(1 for h, ro, rx in log if ro)
    n_bypass = sum(1 for h, ro, rx in log if (not h) and ro and (not rx))
    n_imsd = sum(1 for h, ro, rx in log if h)
    n_growth = sum(1 for h, ro, rx in log if (h or ro) and (not rx))
    return dict(eval=n_eval, ro=n_ro, bypass=n_bypass, imsd=n_imsd, growth=n_growth)


class ForcedBypass(NHS):
    """观测 2 专用:人为把 `N_bypass` 拉到非零。⛔ 非真实工况,数不得作性能引用。"""

    def _imsd(self, tr):
        return (False, 0.0)

    def _update_tracks(self, *a, **kw):
        r = super()._update_tracks(*a, **kw)
        for tr in self.tracks:
            tr.rapid_onset = True
        return r


def growth_count(alg, hb, D, G, src):
    n = {'g': 0}
    orig = alg._classify

    def wrapped(*a, _o=orig, _n=n):
        out = _o(*a)
        _n['g'] += len(out)
        return out
    alg._classify = wrapped

    def pf(blk, _a=alg):
        return _a.process_frame(blk, GR)
    clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    return n['g']


def main():
    W("未经 critic 评审 —— r66b · 诊断 r66a 的 Hb2 失败(直接观测,不推断)")
    W("[L2/宿主仿真]  deps: nhs.py(已加 growth_and_gate) clrig.py@8ad47ce8d260dd18")
    W("")
    W("=" * 100)
    W("观测 1 · 可达性计数 —— `N_bypass` = #{imsd_hit=False ∧ rapid_onset=True ∧ relaxed=False}")
    W("          (= 开关唯一能改变结果的那一格;`_imsd` 只在 `nhs.py:863` 被调用)")
    W("=" * 100)
    W(f"{'T60':>5}{'sd':>4}{'Δ':>6}  {'判据求值次数':>12}{'rapid_onset为真':>16}"
      f"{'imsd命中':>10}{'⭐N_bypass':>12}{'GROWTH入选':>12}")
    tot = dict(eval=0, ro=0, bypass=0, imsd=0, growth=0)
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = 1e-3 * np.random.default_rng(sd).standard_normal(int(T * FS))
        for dl in DELTAS:
            a = NHS()
            a.P.bw_oct = BW
            c = run_counted(a, hb, D, anchor + dl, src)
            for k in tot:
                tot[k] += c[k]
            W(f"{T60:>5.1f}{sd:>4}{dl:>+6.1f}  {c['eval']:>12}{c['ro']:>16}"
              f"{c['imsd']:>10}{c['bypass']:>12}{c['growth']:>12}")
    W("-" * 100)
    W(f"{'合计':>15}{'':>2}  {tot['eval']:>12}{tot['ro']:>16}"
      f"{tot['imsd']:>10}{tot['bypass']:>12}{tot['growth']:>12}")
    W("")
    W(f"⇒ N_bypass 合计 = **{tot['bypass']}**"
      f"  ⇒ {'假说 (c) 成立:该 OR 旁路在这些工作点上从未被走过' if tot['bypass'] == 0 else '旁路确被走过 ⇒ (c) 不成立,须查 (a)/(b)'}")
    W("")
    W("=" * 100)
    W("观测 2 · 接线测试(构造开关【应该】响应的输入)⛔ 非真实工况,数不得作性能引用")
    W("=" * 100)
    W(f"{'T60':>5}{'sd':>4}{'Δ':>6}  {'gate=False 的分类数':>20}{'gate=True 的分类数':>20}  {'开关是否生效':>14}")
    wired = 0
    ncell = 0
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = 1e-3 * np.random.default_rng(sd).standard_normal(int(T * FS))
        for dl in DELTAS:
            a0 = ForcedBypass()
            a0.P.bw_oct = BW
            a0.P.growth_and_gate = False
            g0 = growth_count(a0, hb, D, anchor + dl, src)
            a1 = ForcedBypass()
            a1.P.bw_oct = BW
            a1.P.growth_and_gate = True
            g1 = growth_count(a1, hb, D, anchor + dl, src)
            ok = (g0 != g1)
            wired += int(ok)
            ncell += 1
            W(f"{T60:>5.1f}{sd:>4}{dl:>+6.1f}  {g0:>20}{g1:>20}  "
              f"{('✅ 生效' if ok else '⛔ 无差异'):>14}")
    W("-" * 100)
    W(f"⇒ 接线测试:**{wired}/{ncell} 格证明开关确实控制该分支**"
      f"  ⇒ {'假说 (a)(b) 排除' if wired > 0 else '⛔ 开关没接上或比对器无分辨力 —— 回滚 nhs.py 并报 lead'}")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/'
         'r66b_gate_reach_out.txt', 'w').write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
