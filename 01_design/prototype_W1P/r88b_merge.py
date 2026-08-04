"""r88 归并。⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r88b.txt。
⛔ 本文件不含结论性散文;判读由人在看到数之后写。"""
import sys, json, glob
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
FLOOR = 0.354
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def mark(d):
    if not np.isfinite(d):
        return '⛔ 无数'
    if abs(d) < FLOOR:
        return '不可判(⛔≠没变化)'
    return ('**更高(一格)**' if 0 < d < 0.75 else '**更低(一格)**' if -0.75 < d < 0 else
            '**更高(多格)**' if d > 0 else '**更低(多格)**')


def main():
    R = []
    for p in sorted(glob.glob(DIR + 'r88b_cell_*.json')):
        R += json.load(open(p))
    K = {(r['T60'], r['sd'], r['plant']): r for r in R}
    W("未经 critic 评审 —— r88 · **非统计 plant 对照**  [L2/宿主仿真]  预注册 = PREREG_r88b.txt")
    W("问:**若低频段是可辨模态而非统计场,NHS 的行为会不会不同**")
    W("⛔ 本轮**不**声称非统计 plant 更真实;⛔ 不据它改任何设计")
    W(f"仪器底 {FLOOR} dB;两臂同锚同栅格 ⇒ δ 恒为 0.5 整数倍 ⇒ |δ|=0.50 只是一格")
    W("")
    W("=" * 116)
    W("① 逐种子 ΔMSG(duck 消融列)· 三个 plant")
    W("=" * 116)
    W(f"{'T60/sd':>8}{'P_stat':>9}{'P_conf':>9}{'P_mod9':>10}"
      f"{'δ=conf−stat':>13}{'判读(主问)':>22}{'δ=booth−stat':>14}{'判读(阳性对照,仅T60=0.5)':>26}")
    dc, db = [], []
    for (t, s) in SEEDS:
        a, b, c = K.get((t, s, 'P_stat')), K.get((t, s, 'P_conf')), K.get((t, s, 'P_mod9'))
        if not (a and b and c):
            W(f"{t}/{s:<6}  ⛔ 缺格")
            continue
        d1, d2 = b['dmsg'] - a['dmsg'], c['dmsg'] - a['dmsg']
        dc.append(d1)
        db.append(d2)
        W(f"{t}/{s:<6}{a['dmsg']:>9.2f}{b['dmsg']:>9.2f}{c['dmsg']:>10.2f}"
          f"{d1:>13.2f}{mark(d1):>22}{d2:>14.2f}{mark(d2):>24}")
    W("")
    nc = sum(1 for d in dc if abs(d) >= FLOOR)
    nb = sum(1 for d in db if abs(d) >= FLOOR)
    W(f"   Hp1 主问:P_conf vs P_stat **可判 {nc}/{len(dc)}**")
    W(f"   Hp2 阳性对照:P_mod9 vs P_stat **可判 {nb}/{len(db)}**")
    W(f"   ⇒ 机械判读(按预注册 §4):")
    if nb == 0:
        W("     ⛔ **阳性对照未出现差异 ⇒ 本对比无分辨力 ⇒ Hp1 的『无差异』不得读作阴性结论**")
    elif nc == 0:
        W("     ✅ 阳性对照有差异 ∧ 主问 0/6 可判 ⇒ **『常数之争不改变决定』成立(B-1 形式)**")
    else:
        W("     ⚠ 主问出现可判差异 ⇒ **争议【会】影响决定** ⇒ 须逐条看是哪些种子")
    W("")
    W("=" * 116)
    W("② Hp3 低频行为(挂陷频点 <300 Hz 的个数)+ 挂陷总数 —— ⛔ 与 ΔMSG 分开报")
    W("=" * 116)
    W(f"{'T60/sd':>8}{'挂陷 stat/conf/booth':>24}{'<300Hz stat/conf/booth':>26}{'深度中位 stat/conf/booth':>28}")
    for (t, s) in SEEDS:
        a, b, c = K.get((t, s, 'P_stat')), K.get((t, s, 'P_conf')), K.get((t, s, 'P_mod9'))
        if not (a and b and c):
            continue
        W(f"{t}/{s:<6}"
          f"{'%d / %d / %d' % (a.get('n_notch',-1), b.get('n_notch',-1), c.get('n_notch',-1)):>24}"
          f"{'%d / %d / %d' % (a.get('n_low',-1), b.get('n_low',-1), c.get('n_low',-1)):>26}"
          f"{'%.2f / %.2f / %.2f' % (a.get('dmed',float('nan')), b.get('dmed',float('nan')), c.get('dmed',float('nan'))):>28}")
    W("")
    W("=" * 116)
    W("③ 窗长有效性(各 plant 的 NHS 臂在其终点 G 上)")
    W("=" * 116)
    nb2 = tot = 0
    for (t, s) in SEEDS:
        for nm in ('P_stat', 'P_conf', 'P_mod9'):
            r = K.get((t, s, nm))
            if not r:
                continue
            tot += 1
            up = bool(r.get('upper_only'))
            nb2 += int(up)
    W(f"   判为「只能作上界」的格:**{nb2}/{tot}**")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。全部 [L2/宿主仿真]。⛔ 未 commit。")
    with open(DIR + 'r88b_plant_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    json.dump(R, open(DIR + 'r88b_plant.json', 'w'), default=lambda o: None)


if __name__ == '__main__':
    main()
