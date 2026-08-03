"""r66c · 两问,一批跑:①PAPR 在候选链里到底承担什么(答 lead 的 甲/乙/丙)
                        ②`rapid_onset` 的 0/1802 是 A(信号没有)还是 B(门够不到)—— D1 可达性扫

⛔ 未经 critic 评审。[L2/宿主仿真]。输出:r66c_papr_role_out.txt (D6-j)
deps: nhs.py@31decc8e8d07e085(已加 growth_and_gate,行为逐位不变已证)
      clrig.py@8ad47ce8d260dd18  r57_bandlimit.py@74036010b514080d

════════════════════════════════════════════════════════════════════
问 1 · lead 的 甲/乙/丙 —— **移出 PAPR 会不会让候选数爆炸?**
════════════════════════════════════════════════════════════════════
`nhs.py:394,414` 候选门 = `pa < T_papr **或** pn < T_pnpr ⇒ continue`(PAPR ∧ PNPR 的合取门)。
`_papr`/`_pnpr` **全库只在此一处被调用**(已 grep 核实)⇒ 包装即得门的全部统计。
⚠ 上游已有硬帽:候选表 `n_cand = 16`(top-16 局部极大),轨表 `NT = 12`,影子 `NN = 8`
  ⇒ **"爆炸"不是无界的,真正的问题是【轨表会不会被垃圾占满】**(= 僵尸轨,W1-B MAJOR-5)。
⇒ 故不止统计门,**直接跑一条把 PAPR 摘掉的臂**(D6-d:别推断,把被测物拿掉真跑一次)。

  臂 base   现行(PAPR ∧ PNPR)
  臂 noPAPR `_papr` 恒返 +∞ ⇒ 门退化为 **仅 PNPR**
  比:过门数 / 建轨数 / 活跃轨峰值 / 轨表满标志 / 挂陷数 / slots_exhausted

预注册判读(跑前写死):
  Hc1 过门数放大倍数 `R = N3_gate(noPAPR) / N3_gate(base)`。
      `R ≤ 2` 且 活跃轨峰值 < NT ⇒ **(乙) 可做**,移出 PAPR 不会淹掉轨表;
      `R ≫ 2` 或 轨表被占满(`table_full`/`n_blocked` 显著上升)⇒ **(乙) 无意义**,照 lead 说的。
  Hc2 **PAPR 是否曾【单独】否掉过一个 PNPR 已过的候选** —— 即 `pass_pnpr_only > 0`?
      `= 0` ⇒ PAPR 在本工作点集上**从不承担否决**(它的门形同虚设)⇒ 与 ① 同型的第二例;
      `> 0` ⇒ 它确实在否决,那么"否掉的是真啸叫还是噪声"是下一个问题(本轮不答)。

════════════════════════════════════════════════════════════════════
问 2 · `rapid_onset` 的 D1 可达性扫(lead 点名,在跑批空隙做)
════════════════════════════════════════════════════════════════════
`nhs.py:554-560` 置位需**两个合取项同时成立**:
  (i) 跃升: ∃ i<j, j−i ≤ `N_RISE=2`,使 `h[j] − h[i] ≥ R_RISE = 18 dB`   (h = PAPR 轨迹)
  (ii) 平台: `std(h[j:]) ≤ S_PLAT = 2.0`,且平台段 ≥ `MIN_PLAT = 3` 点
⇒ **逐门问「目标场景会不会天然低于它」**(D1 做法),并报**哪一个合取项是绑定约束**:
  A = 信号本就没有快速起振(跃升项远不达标)
  B = 门在结构上够不到(例如平台项恒假 —— 本台架环内无限幅器 ⇒ 啸叫不封顶)
  **两者处置不同**:A ⇒ 记录即可;B ⇒ 它是一段【从未产生过动作】的判据分支,须走 D4。
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


class NoPAPR(NHS):
    """臂 noPAPR:把 PAPR 从候选门里摘掉(恒返 +∞ ⇒ `pa < T_papr` 恒假)。
    ⚠ 只改门,不改其它 —— `papr_hist` 仍存真值?**不**:`obs[k]['papr']` 会记 +∞,
      故本臂**不用于任何 ΔMSG 读数**,只用于回答"候选/轨会不会爆"。"""

    def _papr(self, M, k):
        return 1e9


def probe(alg, hb, D, G, src, collect_hist=False):
    """包装候选门的两个特征函数 + (可选)采集 PAPR 轨迹用于问 2。"""
    rec = {'pairs': [], 'hist': [], 'ntr': 0}
    o_pa, o_pn = alg._papr, alg._pnpr
    box = {'pa': None}

    def w_pa(M, k, _o=o_pa, _b=box):
        v = _o(M, k)
        _b['pa'] = v
        return v

    def w_pn(M, k, _o=o_pn, _b=box, _r=rec):
        v = _o(M, k)
        _r['pairs'].append((_b['pa'], v))
        return v
    alg._papr, alg._pnpr = w_pa, w_pn

    if collect_hist:
        o_im = alg._imsd

        def w_im(tr, _o=o_im, _r=rec):
            _r['hist'].append(list(tr.papr_hist))
            return _o(tr)
        alg._imsd = w_im

    def pf(blk, _a=alg, _r=rec):
        y = _a.process_frame(blk, GR)
        _r['ntr'] = max(_r['ntr'], sum(1 for t in _a.tracks if t.active))
        return y
    clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    return rec


def main():
    P = nhs.Params()
    W("未经 critic 评审 —— r66c · PAPR 在候选链里的角色 + rapid_onset 的 D1 可达性扫")
    W("[L2/宿主仿真]  deps: nhs.py@31decc8e8d07e085 clrig.py@8ad47ce8d260dd18")
    W(f"门值:T_papr={P.T_papr} T_pnpr={P.T_pnpr} n_cand={P.n_cand} NT={P.NT} NN={P.NN}")
    W(f"rapid_onset 门:R_RISE={P.R_RISE} N_RISE={P.N_RISE} S_PLAT={P.S_PLAT} MIN_PLAT={P.MIN_PLAT}")
    W("")
    W("=" * 112)
    W("问 1 · 候选门交叉表 + 摘掉 PAPR 的直跑对照")
    W("=" * 112)
    W(f"{'T60':>5}{'sd':>4}{'Δ':>6} | {'门前候选':>8}{'两者都过':>9}{'仅PNPR过':>10}"
      f"{'仅PAPR过':>10}{'都不过':>8} | {'noPAPR过门':>11}{'R倍':>7}"
      f"{'活跃轨峰值':>11}{'满/阻塞':>9}")
    tot = dict(ev=0, both=0, pnpr_only=0, papr_only=0, none=0, np_gate=0)
    ntr_b, ntr_n, blocked = [], [], []
    allhist = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = 1e-3 * np.random.default_rng(sd).standard_normal(int(T * FS))
        for dl in DELTAS:
            G = anchor + dl
            a = NHS(); a.P.bw_oct = BW
            rb = probe(a, hb, D, G, src, collect_hist=True)
            allhist += rb['hist']
            pr = rb['pairs']
            both = sum(1 for pa, pn in pr if pa >= P.T_papr and pn >= P.T_pnpr)
            po = sum(1 for pa, pn in pr if pa < P.T_papr and pn >= P.T_pnpr)   # 仅 PNPR 过
            ao = sum(1 for pa, pn in pr if pa >= P.T_papr and pn < P.T_pnpr)   # 仅 PAPR 过
            nn = len(pr) - both - po - ao
            b = NoPAPR(); b.P.bw_oct = BW
            rn = probe(b, hb, D, G, src)
            npg = int(b.ctr.get('N3_gate', 0))
            R = (npg / both) if both else float('nan')
            blk = int(b.ctr.get('n_blocked', 0)) + int(b.ctr.get('table_full', 0))
            for k, v in (('ev', len(pr)), ('both', both), ('pnpr_only', po),
                         ('papr_only', ao), ('none', nn), ('np_gate', npg)):
                tot[k] += v
            ntr_b.append(rb['ntr']); ntr_n.append(rn['ntr']); blocked.append(blk)
            W(f"{T60:>5.1f}{sd:>4}{dl:>+6.1f} | {len(pr):>8}{both:>9}{po:>10}"
              f"{ao:>10}{nn:>8} | {npg:>11}{R:>7.2f}"
              f"{rb['ntr']:>4}/{rn['ntr']:<6}{blk:>9}")
    W("-" * 112)
    R = (tot['np_gate'] / tot['both']) if tot['both'] else float('nan')
    W(f"{'合计':>17} | {tot['ev']:>8}{tot['both']:>9}{tot['pnpr_only']:>10}"
      f"{tot['papr_only']:>10}{tot['none']:>8} | {tot['np_gate']:>11}{R:>7.2f}"
      f"{max(ntr_b):>4}/{max(ntr_n):<6}{sum(blocked):>9}")
    W("")
    W(f"  Hc1 放大倍数 R = **{R:.2f}**;活跃轨峰值 base **{max(ntr_b)}** / noPAPR **{max(ntr_n)}**"
      f"(NT={P.NT});table_full+n_blocked 合计 **{sum(blocked)}**")
    W(f"  Hc2 `仅PNPR过` = **{tot['pnpr_only']}** ⇒ "
      f"{'PAPR 在本工作点集上【从不单独否决】,其门形同虚设' if tot['pnpr_only'] == 0 else 'PAPR 确实在否决候选'}")
    W("")
    W("=" * 112)
    W("问 2 · `rapid_onset` D1 可达性扫 —— 两个合取项各自离达标有多远")
    W("=" * 112)
    rises, tails, joint = [], [], 0
    n_eligible = 0
    for h in allhist:
        if len(h) < P.MIN_PLAT + 1:
            continue
        n_eligible += 1
        best = -99.
        bt = None
        for i in range(len(h) - P.MIN_PLAT):
            for j in range(i + 1, min(i + P.N_RISE, len(h) - P.MIN_PLAT) + 1):
                r = h[j] - h[i]
                if r > best:
                    best, bt = r, float(np.std(h[j:]))
                if r >= P.R_RISE and np.std(h[j:]) <= P.S_PLAT:
                    joint += 1
        rises.append(best)
        if bt is not None:
            tails.append(bt)
    W(f"  可参与判定的 (轨,槽) 求值数(len(papr_hist) ≥ {P.MIN_PLAT+1}):**{n_eligible}** "
      f"/ 总采样 {len(allhist)}")
    if rises:
        W(f"  合取项(i) 跃升 `max(h[j]−h[i]), j−i≤{P.N_RISE}`:"
          f"最大 **{max(rises):.2f}** / p95 {np.percentile(rises,95):.2f} / "
          f"中位 {np.median(rises):.2f} dB   **门 = {P.R_RISE} dB**")
        W(f"    ⇒ 达门次数 = **{sum(1 for r in rises if r >= P.R_RISE)}** / {len(rises)}")
    if tails:
        W(f"  合取项(ii) 平台 `std(h[j:])`(取最大跃升处):"
          f"最小 **{min(tails):.2f}** / 中位 {np.median(tails):.2f} dB   **门 = ≤{P.S_PLAT} dB**")
        W(f"    ⇒ 达门次数 = **{sum(1 for t in tails if t <= P.S_PLAT)}** / {len(tails)}")
    W(f"  两项**同时**成立次数 = **{joint}**")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/'
         'r66c_papr_role_out.txt', 'w').write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
