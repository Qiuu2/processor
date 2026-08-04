"""r87 归并 —— 把 6 个 cell 汇成必报四项。⛔ 未经 critic 评审。[L2/宿主仿真]。
预注册 = PREREG_r87b.txt。⛔ 本文件不含结论性散文;判读由人在看到数之后写。
"""
import sys, json, glob
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
FOCUS = [(0.2, 1), (0.5, 2)]          # r86 基线深度未到顶的两条(Hg1)
FLOOR = 0.354
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def mark(d):
    """预注册 §5 三分:δ=0 不可判;|δ|=0.5 一格(弱);|δ|≥1 多格。"""
    if not np.isfinite(d):
        return '⛔ 无数'
    if abs(d) < FLOOR:
        return '不可判(⛔≠没变化)'
    if abs(d) < 0.75:
        return ('**更好(一格)**' if d > 0 else '**更差(一格)**')
    return ('**更好(多格)**' if d > 0 else '**更差(多格)**')


def main():
    R = []
    diags = {}
    for p in sorted(glob.glob(DIR + 'r87_cell_*.json')):
        o = json.load(open(p))
        R += o['rows']
        if o.get('diag'):
            k = (o['rows'][0]['T60'], o['rows'][0]['sd'])
            diags[k] = o['diag']
    K = {(r['T60'], r['sd'], r['arm']): r for r in R}

    W("未经 critic 评审 —— r87 · `recheck_free` 的 **ΔMSG 验证扫描**  [L2/宿主仿真]")
    W("预注册 = PREREG_r87b.txt(跑前落盘,§4/§5 跑后未改)。闸门 = r87_gate_out.txt")
    W("工作点:src_rms=**−20.0 dBFS(标称)** / T_OBS=**12 s** / prefer_unnotched=**关** /")
    W("       bw_oct=1/5 / T_low=−45 / NN=8 槽全空 / n_cand=16 / STEP=0.5 / **环路 8 kHz 以上被带限**")
    W(f"仪器底 = {FLOOR} dB(= STEP/2×√2);⚠ 两臂同锚同栅格 ⇒ δ 恒为 0.5 的整数倍(预注册 §5)")
    W("⛔ 「不可判」不得读作「没变化」。⛔ 深度到顶不得当作 ΔMSG 改善的证据。")
    W("")

    # ── ① 逐种子 ΔMSG(两臂)+ ③ 逐格标底 ────────────────────────
    W("=" * 118)
    W("① 逐种子 ΔMSG(主列 = duck **消融**;正数 = 修法更好)      ③ 每格对 0.354 dB 仪器底标注")
    W("=" * 118)
    W(f"{'T60/sd':>8}{'ΔMSG基线':>10}{'ΔMSG修法':>10}{'δ=修法−基线':>13}{'判读':>22}"
      f"{'挂陷 基→修':>12}{'深度中位 基→修':>18}{'f_trig 基→修':>18}")
    for (t, s) in SEEDS:
        a, b = K.get((t, s, 'A_base')), K.get((t, s, 'A_rf'))
        if not a or not b:
            W(f"{t}/{s:<6}  ⛔ 缺格")
            continue
        d = b['dmsg'] - a['dmsg']
        nn = "%d→%d" % (a.get('n_notch', -1), b.get('n_notch', -1))
        dm = "%.2f→%.2f" % (a.get('dmed', float('nan')), b.get('dmed', float('nan')))
        ftr = "%.0f→%.0f" % (a.get('f_trig', float('nan')), b.get('f_trig', float('nan')))
        star = ' ⭐' if (t, s) in FOCUS else ''
        W(f"{str(t)+'/'+str(s)+star:>8}{a['dmsg']:>10.2f}{b['dmsg']:>10.2f}{d:>13.2f}"
          f"{mark(d):>22}{nn:>12}{dm:>18}{ftr:>18}")
    W("")
    W("   附列(duck **不消融**;⛔ 不得单独引用,须与 g_duck最深 同出 —— F33 已发生三次)")
    W(f"{'T60/sd':>8}{'ΔMSG基线':>10}{'ΔMSG修法':>10}{'δ':>9}{'判读':>22}"
      f"{'g_duck最深 基→修':>20}")
    for (t, s) in SEEDS:
        a, b = K.get((t, s, 'D_base')), K.get((t, s, 'D_rf'))
        if not a or not b:
            continue
        d = b['dmsg'] - a['dmsg']
        gd = "%.2f→%.2f" % (a.get('gmin', float('nan')), b.get('gmin', float('nan')))
        W(f"{t}/{s:<6}{a['dmsg']:>10.2f}{b['dmsg']:>10.2f}{d:>9.2f}{mark(d):>22}{gd:>20}")
    W("")

    # ── ② 单列两条焦点种子 ───────────────────────────────────────
    W("=" * 118)
    W("② ⭐ 单列【基线下深度卡住】的两条(r86:0.2/sd1 = −15.00、0.5/sd2 = −16.50;其余四条已到 −18.00)")
    W("   Hg1:若机制是「补足深度」,收益应集中在这两条      Hg2:若收益反在其余四条 ⇒ 另有其物")
    W("=" * 118)
    foc, oth = [], []
    for (t, s) in SEEDS:
        a, b = K.get((t, s, 'A_base')), K.get((t, s, 'A_rf'))
        if not a or not b:
            continue
        d = b['dmsg'] - a['dmsg']
        (foc if (t, s) in FOCUS else oth).append(((t, s), d, a, b))
    for tag, grp in (("焦点两条(基线深度未到顶)", foc), ("其余四条(基线深度已到顶)", oth)):
        W(f"  ── {tag}")
        for (ts, d, a, b) in grp:
            W(f"     {ts[0]}/{ts[1]}: ΔMSG {a['dmsg']:+.2f} → {b['dmsg']:+.2f}  δ={d:+.2f}  {mark(d)}"
              f"   深度中位 {a.get('dmed', float('nan')):.2f} → {b.get('dmed', float('nan')):.2f}")
    nf = sum(1 for (_, d, _, _) in foc if abs(d) >= FLOOR)
    no = sum(1 for (_, d, _, _) in oth if abs(d) >= FLOOR)
    npf = sum(1 for (_, d, _, _) in foc if d >= FLOOR)
    npo = sum(1 for (_, d, _, _) in oth if d >= FLOOR)
    W("")
    W(f"   ⇒ 焦点两条:可判 {nf}/{len(foc)}(其中变好 {npf});其余四条:可判 {no}/{len(oth)}(其中变好 {npo})")
    W(f"   ⇒ Hg1(收益集中在焦点两条):{'**支持**' if (npf > 0 and npo == 0) else '**不支持**'}")
    W(f"   ⇒ Hg2(收益反在其余四条):{'**触发 ⇒ 另有其物,须查**' if (npo > 0 and npf == 0) else '未触发'}")
    hurt = [(ts, d) for (ts, d, _, _) in foc + oth if d <= -FLOOR]
    W(f"   ⇒ Hg3(不得伤害:任一条变差 > {FLOOR}):"
      f"{'**触发 ⇒ 判有害** ' + str(hurt) if hurt else '未触发(0 条变差)'}")
    W("")

    # ── ④ 窗长有效性 ────────────────────────────────────────────
    W("=" * 118)
    W("④ 各臂在其**终点 G** 上的末秒−首秒 RMS(在衰=稳定点;在长 ⇒ 该格只能作上界)")
    W("   参照(r80b 已验):干净的样子 = −5.87 dB(在衰);到峰/窗 ≥ 0.7 亦判上界")
    W("=" * 118)
    W(f"{'T60/sd':>8}{'臂':>9}{'终点G':>9}{'ΔMSG':>8}{'末−首dB':>10}{'到峰/窗':>9}{'判定':>18}")
    nb = 0
    tot = 0
    for (t, s) in SEEDS:
        for arm in ('m0', 'A_base', 'A_rf', 'D_base', 'D_rf'):
            r = K.get((t, s, arm))
            if not r:
                continue
            tot += 1
            up = bool(r.get('upper_only'))
            nb += int(up)
            W(f"{t}/{s:<6}{arm:>9}{r['m']:>9.2f}{r['dmsg']:>8.2f}"
              f"{r.get('grow', float('nan')):>+10.2f}{r.get('tpeak_ratio', float('nan')):>9.2f}"
              f"{('**⛔ 只能作上界**' if up else '✅ 干净'):>18}")
        W("")
    W(f"   ⇒ 判为「只能作上界」的格:**{nb}/{tot}**")
    W("")

    # ── §7 诊断汇总(非闸门)────────────────────────────────────
    W("=" * 118)
    W("§7 诊断(⛔ 非闸门):A_base vs r76 同工作点已落盘值(四项:m0 / ΔMSG / 挂陷 / 终点lp)")
    W("=" * 118)
    ok = 0
    for (t, s) in SEEDS:
        d = diags.get((t, s))
        if not d:
            W(f"   {t}/{s}: ⛔ 无对照")
            continue
        four = [d['same_m0'], d['same_dmsg'], d['same_n_notch'], d['same_lp']]
        ok += int(all(four))
        W(f"   {t}/{s}: m0 {'✓' if d['same_m0'] else '✗'} | ΔMSG {'✓' if d['same_dmsg'] else '✗'}"
          f"(本轮 vs r76 dA={d['r76_dA']:+.2f}) | 挂陷 {'✓' if d['same_n_notch'] else '✗'}"
          f" | 终点lp {'✓' if d['same_lp'] else '✗'}")
    W(f"   ⇒ 四项全符的种子:**{ok}/{len(SEEDS)}**")
    W("   ⚠ 全符 ⇒ 「recheck_free 默认关 = 行为不变」在 ΔMSG 层面得到**事后**支持;")
    W("     ⛔ 它不等于盘面上的逐位等价证据件(`r86a_bitexact` 在本目录**不存在**,PREREG_r87b §1 核①(c))")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。全部 [L2/宿主仿真]。⛔ 未 commit。")
    with open(DIR + 'r87_dmsg_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    json.dump(R, open(DIR + 'r87_dmsg.json', 'w'), default=lambda o: None)


if __name__ == '__main__':
    main()
