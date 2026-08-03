"""r77 · **开环注入探针** —— Hr2 被证伪后的独立观测(LESSONS C-4)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r76.txt **§7(跑前追加)**。
输出 r77_openloop_gate_out.txt(D6-j 路径唯一)。

唯一目的:把【门算术】与【闭环自反馈】分开。
构造:注入信号 = 同一条 `lp_base` **逐样本精确缩放**(×10**((L+60)/20))
      ⇒ 各源电平之间只差一个常数因子 —— 这是闭环里拿不到的控制。
⚠ 已核:检测 tap 在陷波器组**入口**(nhs.py:279-280,`_sidechain_push(x)` 在滤波前)
  ⇒ 开环下已挂陷波不改变检测器看到的信号,只经 `cov` 影响门的选择。
⚠ 已核:`GR = {'out_lim_active': False, ...}` ⇒ `gr_active` 恒 False ⇒ `gr_ok` 恒 False
  ⇒ 放宽门 `T_low_gr` **只能经 `cov` 到达**(nhs.py:411-418)。

⛔ 本文件不含结论性散文。
"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, GR, FRAME

BW_OCT = 1 / 5
F_CUT = 8000.
T_OBS = 6.0
SRC = [-60., -50., -40., -30., -20., -10.]
DG = [1.0, 2.0, 4.0]
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DIR = '/home/it1234/processor/01_design/prototype_W1P/'
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def inject(x):
    """开环喂入,丢弃输出。返回(第1槽后 / 第10槽后 / 全程)的漏斗计数。"""
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = -45.
    snap = {}
    n = (len(x) // FRAME) * FRAME
    for i in range(0, n, FRAME):
        a.process_frame(x[i:i + FRAME], GR)
        s = int(a.ctr.get('slots', 0))
        if s in (1, 10) and s not in snap:
            snap[s] = dict(n1=int(a.ctr.get('N1_cand', 0)),
                           n2=int(a.ctr.get('N2_lvl', 0)),
                           notch=sum(1 for t in a.slots if t.st != nhs.NotchSlot.FREE))
    used = [t for t in a.slots if t.st != nhs.NotchSlot.FREE]
    return dict(slot1=snap.get(1), slot10=snap.get(10),
                n1=int(a.ctr.get('N1_cand', 0)), n2=int(a.ctr.get('N2_lvl', 0)),
                notch=len(used), slots=int(a.ctr.get('slots', 0)),
                fr=sorted(round(float(t.f), 1) for t in used))


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r77 · 开环注入探针(把门算术与闭环自反馈分开)  [L2/宿主仿真]")
    W("预注册 = PREREG_r76.txt §7(跑前追加,在本文件产出任何数据之前写下)")
    W("触发:Hr2 证伪 —— r76 固定 G 表 120 对相邻档中 13 对非单调(5 对含起振端,8 对两端均未起振)")
    W("构造:注入信号 = 同一条 lp_base × 10**((L+60)/20) ⇒ **各档逐样本只差常数因子**(构造保证)")
    W(f"工作点:T_OBS={T_OBS:.0f}s / ΔG∈{DG} / 源电平∈{[int(x) for x in SRC]} / "
      f"T_low=−45 / bw_oct=1/5 / f_cut={F_CUT:.0f} / cal_offset_db=0.0 / 开环(输出丢弃,无反馈)")
    W("")
    rows = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src60 = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * 1e-3
        ref60 = HD.rms_db(src60[:(len(src60) // FRAME) * FRAME])
        for dg in DG:
            G = anchor + dg
            _, lp = clrig.Loop(hb, D, G, proc=None).run(src60, FRAME)
            hw = bool(HD.is_howling(lp, ref60, FS, FRAME)[0])
            W(f"### T60={T60} sd={sd} ΔG={dg:+.0f}  (lp_base 由 proc=None 生成;"
              f"该基线自身起振={hw};lp_base RMS@src−60 = {HD.rms_db(lp):+.2f} dBFS)")
            W(f"{'src':>6}{'N1@槽1':>9}{'N2@槽1':>9}{'挂陷@槽1':>10}"
              f"{'N1@槽10':>9}{'N2@槽10':>9}{'N1全程':>9}{'N2全程':>9}{'挂陷':>6}{'总槽':>6}")
            for L in SRC:
                r = inject(lp * (10 ** ((L + 60.) / 20.)))
                s1, s10 = r['slot1'], r['slot10']
                W(f"{int(L):>6}{(s1['n1'] if s1 else -1):>9}{(s1['n2'] if s1 else -1):>9}"
                  f"{(s1['notch'] if s1 else -1):>10}"
                  f"{(s10['n1'] if s10 else -1):>9}{(s10['n2'] if s10 else -1):>9}"
                  f"{r['n1']:>9}{r['n2']:>9}{r['notch']:>6}{r['slots']:>6}")
                rows.append(dict(T60=T60, sd=sd, dg=dg, src=L, base_howl=hw,
                                 n1_s1=(s1['n1'] if s1 else -1), n2_s1=(s1['n2'] if s1 else -1),
                                 notch_s1=(s1['notch'] if s1 else -1),
                                 n1_s10=(s10['n1'] if s10 else -1),
                                 n2_s10=(s10['n2'] if s10 else -1),
                                 n1=r['n1'], n2=r['n2'], notch=r['notch'], slots=r['slots']))
            W("")

    W("=" * 110)
    W("§H 预注册假设逐条机械对表(⛔ 判读文字由人在看到数之后写)")
    W("=" * 110)
    # Hs1:N1_cand 各档完全相同
    bad1, n1chk = [], 0
    for (T60, sd) in SEEDS:
        for dg in DG:
            for k in ('n1_s1', 'n1_s10', 'n1'):
                v = sorted(set(r[k] for r in rows if r['T60'] == T60 and r['sd'] == sd
                               and r['dg'] == dg))
                if not v:
                    continue
                n1chk += 1
                if len(v) > 1:
                    bad1.append((T60, sd, dg, k, v))
    W(f"  Hs1 `N1_cand` 各档完全相同:已查 {n1chk} 组,违反 **{len(bad1)}**"
      + ('  ⛔ 已查 0 组 ⇒ 本项未执行' if n1chk == 0 else ''))
    for b in bad1[:20]:
        W(f"     ⛔ {b}")
    # Hs2:第 1 槽 N2 单调不减(纯门算术)
    bad2, n2chk = [], 0
    for (T60, sd) in SEEDS:
        for dg in DG:
            v = sorted([(r['src'], r['n2_s1'], r['notch_s1']) for r in rows
                        if r['T60'] == T60 and r['sd'] == sd and r['dg'] == dg])
            for i in range(len(v) - 1):
                n2chk += 1
                if v[i + 1][1] < v[i][1]:
                    bad2.append((T60, sd, dg, v[i], v[i + 1]))
    W(f"  Hs2 **第 1 槽**(挂陷必为 0 ⇒ 门恒为 T_low ⇒ 纯门算术)`N2_lvl` 单调不减:"
      f"已比 {n2chk} 对,违反 **{len(bad2)}**"
      + ('  ⛔ 已比 0 对 ⇒ 本项未执行' if n2chk == 0 else ''))
    for b in bad2[:20]:
        W(f"     ⛔ {b}")
    nz = [r for r in rows if r['notch_s1'] not in (0, -1)]
    W(f"     ⚠ 前提核查:第 1 槽时挂陷 ≠ 0 的行数 = **{len(nz)}**(应为 0;非 0 则 Hs2 的"
      f"『纯门算术』前提不成立){[(r['T60'],r['sd'],r['dg'],r['src'],r['notch_s1']) for r in nz[:10]]}")
    # Hs3:全程 N2 单调不减
    bad3, n3chk = [], 0
    for (T60, sd) in SEEDS:
        for dg in DG:
            v = sorted([(r['src'], r['n2'], r['notch']) for r in rows
                        if r['T60'] == T60 and r['sd'] == sd and r['dg'] == dg])
            for i in range(len(v) - 1):
                n3chk += 1
                if v[i + 1][1] < v[i][1]:
                    bad3.append((T60, sd, dg, v[i], v[i + 1]))
    W(f"  Hs3 **全程** `N2_lvl` 单调不减(⛔ 本条不预测方向):已比 {n3chk} 对,违反 **{len(bad3)}**")
    for b in bad3[:20]:
        W(f"     ⚠ {b}")
    W("")
    W("  判别表(预注册 §7):")
    W("    Hs2 成立 ∧ Hs3 成立   ⇒ 非单调**全部**来自闭环自反馈")
    W("    Hs2 成立 ∧ Hs3 不成立 ⇒ 非单调来自算法自身状态(cov ⇒ 门降到 T_low_gr),不是门算术")
    W("    Hs2 不成立            ⇒ **门算术本身有问题,整轮存疑**")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r77_openloop_gate_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r77_openloop_gate.json', 'w') as fp:
        json.dump(rows, fp)


if __name__ == '__main__':
    main()
