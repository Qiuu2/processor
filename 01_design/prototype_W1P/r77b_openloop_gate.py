"""r77b · 开环注入探针【重做】—— r77 器械失效后的修法。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r76.txt **§7(判据)+ §8(修法与两条守卫)**。
输出 r77b_openloop_gate_out.txt(D6-j 路径唯一)。

唯一改动 = **换基线信号来源**(判据 Hs1/Hs2/Hs3 与 §7 逐字相同):
  r77  基线 = `proc=None` @ G=anchor+ΔG  ⇒ **18/18 发散**(anchor 就是无 NHS 的稳定边界)
  r77b 基线 = **闭环 + NHS 在动作 + r76 固定 G 表实测未起振** 的信号
        base ∈ {(ΔG=+1, src=−40), (ΔG=+2, src=−40), (ΔG=+1, src=−20)}(三者均 起振 0/6)

⚠ 跑完必须先看两条守卫(§8),不合格则本件判定同样作废:
  G1 `base_howl` 必须 0/18            ← 防缺陷①(基线发散)
  G2 必须有【挂陷 > 0】的行,且至少 1 个 block 内挂陷数随源电平变化
     ← 防缺陷②(cov 通路没被走到 ⇒ Hs3 恒真 ⇒ 不是能失败的对照)

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
BASES = [(1.0, -40.), (2.0, -40.), (1.0, -20.)]      # (ΔG, 基线源电平)
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DIR = '/home/it1234/processor/01_design/prototype_W1P/'
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def mk():
    a = NHS()
    a.P.bw_oct = BW_OCT
    a.P.T_low = -45.
    return a


def inject(x):
    """开环喂入,丢弃输出 ⇒ 零反馈。返回(第1槽 / 第10槽 / 全程)的漏斗计数。"""
    a = mk()
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
    W("未经 critic 评审 —— r77b · 开环注入探针【重做】  [L2/宿主仿真]")
    W("预注册 = PREREG_r76.txt §7(判据)+ §8(修法与两条守卫,均在本件产出数据之前落盘)")
    W("⛔ 前件 r77 判定【无效】(18/18 基线发散 + 0/108 挂陷 ⇒ 器械无分辨力),已加事后横幅")
    W(f"基线(ΔG, 基线源电平)= {BASES};三者在 r76 固定 G 表上均为 **起振 0/6**(实测,非假设)")
    W(f"工作点:T_OBS={T_OBS:.0f}s / 源电平∈{[int(x) for x in SRC]} / T_low=−45 / bw_oct=1/5 / "
      f"f_cut={F_CUT:.0f} / cal_offset_db=0.0 / 开环(输出丢弃,无反馈)")
    W("")
    rows = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        for (dg, Lb) in BASES:
            G = anchor + dg
            srcb = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (Lb / 20.))
            refb = HD.rms_db(srcb[:(len(srcb) // FRAME) * FRAME])
            ab = mk()
            _, lp = clrig.Loop(hb, D, G, proc=lambda b, _a=ab: _a.process_frame(b, GR)).run(srcb, FRAME)
            hw = bool(HD.is_howling(lp, refb, FS, FRAME)[0])
            nb = sum(1 for t in ab.slots if t.st != nhs.NotchSlot.FREE)
            W(f"### T60={T60} sd={sd}  基线 ΔG={dg:+.0f} @ src={Lb:.0f}  "
              f"(基线自身起振={hw};基线 lp RMS={HD.rms_db(lp):+.2f} dBFS;基线闭环挂陷={nb})")
            W(f"{'注入src':>8}{'N1@槽1':>9}{'N2@槽1':>9}{'挂陷@槽1':>10}"
              f"{'N1@槽10':>9}{'N2@槽10':>9}{'挂陷@槽10':>11}{'N1全程':>9}{'N2全程':>9}{'挂陷':>6}")
            for L in SRC:
                r = inject(lp * (10 ** ((L - Lb) / 20.)))
                s1, s10 = r['slot1'], r['slot10']
                W(f"{int(L):>8}{(s1['n1'] if s1 else -1):>9}{(s1['n2'] if s1 else -1):>9}"
                  f"{(s1['notch'] if s1 else -1):>10}"
                  f"{(s10['n1'] if s10 else -1):>9}{(s10['n2'] if s10 else -1):>9}"
                  f"{(s10['notch'] if s10 else -1):>11}"
                  f"{r['n1']:>9}{r['n2']:>9}{r['notch']:>6}")
                rows.append(dict(T60=T60, sd=sd, dg=dg, base_src=Lb, src=L, base_howl=hw,
                                 base_notch=nb,
                                 n1_s1=(s1['n1'] if s1 else -1), n2_s1=(s1['n2'] if s1 else -1),
                                 notch_s1=(s1['notch'] if s1 else -1),
                                 n1_s10=(s10['n1'] if s10 else -1),
                                 n2_s10=(s10['n2'] if s10 else -1),
                                 notch_s10=(s10['notch'] if s10 else -1),
                                 n1=r['n1'], n2=r['n2'], notch=r['notch'], fr=r['fr']))
            W("")

    blocks = sorted(set((r['T60'], r['sd'], r['dg'], r['base_src']) for r in rows))
    W("=" * 118)
    W("§G 两条守卫(PREREG §8;**不合格则本件判定作废,⛔ 不得报判定**)")
    W("=" * 118)
    bh = [b for b in blocks if any(r['base_howl'] for r in rows
                                   if (r['T60'], r['sd'], r['dg'], r['base_src']) == b)]
    W(f"  G1 基线自身起振的 block:**{len(bh)} / {len(blocks)}**(要求 0)"
      f"  {'✅ 合格' if not bh else '⛔ 不合格:' + str(bh)}")
    nz = [r for r in rows if r['notch'] > 0]
    var = []
    for b in blocks:
        w = sorted([(r['src'], r['notch']) for r in rows
                    if (r['T60'], r['sd'], r['dg'], r['base_src']) == b])
        if len(set(x[1] for x in w)) > 1:
            var.append((b, w))
    W(f"  G2 全程挂陷>0 的行:**{len(nz)} / {len(rows)}**;"
      f"block 内挂陷随源电平变化的 block:**{len(var)} / {len(blocks)}**(要求 ≥1)"
      f"  {'✅ 合格(cov 通路被真的走到 ⇒ Hs3 是能失败的测试)' if var else '⛔ 不合格:Hs3 退化为恒真'}")
    for b, w in var[:6]:
        W(f"     {b}: 挂陷逐档 {w}")
    W("")

    W("=" * 118)
    W("§H 预注册假设逐条机械对表(判据与 §7 逐字相同;⛔ 判读文字由人在看到数之后写)")
    W("=" * 118)
    bad1, n1chk = [], 0
    for b in blocks:
        for k in ('n1_s1', 'n1_s10', 'n1'):
            v = sorted(set(r[k] for r in rows
                           if (r['T60'], r['sd'], r['dg'], r['base_src']) == b))
            if not v:
                continue
            n1chk += 1
            if len(v) > 1:
                bad1.append((b, k, v))
    W(f"  Hs1 `N1_cand` 各档完全相同:已查 {n1chk} 组,违反 **{len(bad1)}**")
    for x in bad1[:20]:
        W(f"     ⛔ {x}")
    for nm, k, note in (
            ('Hs2 **第 1 槽**(挂陷应为 0 ⇒ 门恒为 T_low ⇒ 纯门算术)', 'n2_s1', True),
            ('Hs3 **全程**(⛔ 本条不预测方向)', 'n2', False)):
        bad, chk = [], 0
        for b in blocks:
            v = sorted([(r['src'], r[k], r['notch']) for r in rows
                        if (r['T60'], r['sd'], r['dg'], r['base_src']) == b])
            for i in range(len(v) - 1):
                chk += 1
                if v[i + 1][1] < v[i][1]:
                    bad.append((b, v[i], v[i + 1]))
        W(f"  {nm} `N2_lvl` 单调不减:已比 {chk} 对,违反 **{len(bad)}**")
        for x in bad[:20]:
            W(f"     ⚠ {x}")
        if note:
            nzz = [r for r in rows if r['notch_s1'] not in (0, -1)]
            W(f"     ⚠ 前提核查:第 1 槽时挂陷 ≠ 0 的行数 = **{len(nzz)}**(应为 0)")
    W("")
    W("  判别表(预注册 §7):")
    W("    Hs2 成立 ∧ Hs3 成立   ⇒ 非单调**全部**来自闭环自反馈")
    W("    Hs2 成立 ∧ Hs3 不成立 ⇒ 非单调来自算法自身状态(cov ⇒ 门降到 T_low_gr),不是门算术")
    W("    Hs2 不成立            ⇒ **门算术本身有问题,整轮存疑**")
    W("  ⚠ 该判别表只在 §G 两条守卫**都合格**时可用。")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r77b_openloop_gate_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r77b_openloop_gate.json', 'w') as fp:
        json.dump(rows, fp)


if __name__ == '__main__':
    main()
