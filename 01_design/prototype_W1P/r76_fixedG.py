"""r76 · **固定 G 表** —— 拆开效应 A(绝对门相对位置平移)与效应 B(扫描终点 G 平移)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r76.txt(§3 Hr2)。
输出 r76_fixedG_out.txt(D6-j 路径唯一)。

为什么需要它:扫描表里的每一档,其【报数点的 G 不同】⇒ 环路放大不同 ⇒ 检测器看到的绝对电平
不只由源电平决定。F57.2 已实证:源更安静的臂能存活到更高的 G,ΔMSG 反而更高。
⇒ 本表把 G **钉死在 anchor+{0,1,2,4}**,只让源电平变 ⇒ 剩下的只有效应 A。

臂 = N(NHS 自选,duck 不消融,prefer_unnotched=False,T_low=−45)单臂。
⛔ 本文件不含结论性散文。
"""
import sys, time, json
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
DG = [0.0, 1.0, 2.0, 4.0]
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DIR = '/home/it1234/processor/01_design/prototype_W1P/'
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r76 固定 G 表(拆效应 A / 效应 B)  [L2/宿主仿真]  预注册 = PREREG_r76.txt")
    W(f"臂 N 单臂:NHS 自选 / duck 不消融 / prefer_unnotched=False / T_low=−45 / "
      f"T_low_gr={nhs.Params().T_low_gr:+.0f} / T_panic={nhs.Params().T_panic:+.0f}")
    W(f"工作点:cal_offset_db=0.0 / T_OBS={T_OBS:.0f}s / bw_oct=1/5 / f_cut={F_CUT:.0f} / "
      f"frame={FRAME} / 8 槽全空 / G 钉死在 anchor+{DG}")
    W("⛔ G 固定 ⇒ 本表【不含】ΔMSG(ΔMSG 是扫描终点量,固定 G 下无定义)")
    W("")
    W(f"{'ΔG':>5}{'T60':>5}{'sd':>4}{'src':>6}{'N1_cand':>9}{'N2_lvl':>8}{'过门率':>9}"
      f"{'挂陷':>6}{'top1':>7}{'PANIC':>7}{'lp_rms':>9}{'起振':>6}")
    rows = []
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        picks = pick_excl(he, BW_OCT, 8)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        for dg in DG:
            G = anchor + dg
            for L in SRC:
                src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (L / 20.))
                ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
                a = NHS()
                a.P.bw_oct = BW_OCT
                a.P.T_low = -45.
                _, lp = clrig.Loop(hb, D, G, proc=lambda b, _a=a: _a.process_frame(b, GR)).run(src, FRAME)
                hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
                used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
                fr = sorted(round(float(s.f), 1) for s in used)
                n1 = int(a.ctr.get('N1_cand', 0)); n2 = int(a.ctr.get('N2_lvl', 0))
                pan = int(sum(1 for e in a.cls_log if e.get('cls') == 'PANIC'))
                t = float(picks[0])
                t1 = any(abs(f - t) <= max(t * BW_OCT, 15.) / 2 for f in fr)
                rate = (n2 / n1) if n1 else float('nan')
                lprms = float(HD.rms_db(lp))
                W(f"{dg:>+5.0f}{T60:>5.1f}{sd:>4}{L:>6.0f}{n1:>9}{n2:>8}{100*rate:>8.2f}%"
                  f"{len(used):>6}{str(t1):>7}{pan:>7}{lprms:>9.2f}{str(hw):>6}")
                rows.append(dict(dg=dg, T60=T60, sd=sd, src=L, n1=n1, n2=n2, rate=rate,
                                 n_notch=len(used), top1=bool(t1), panic=pan,
                                 lp_rms=lprms, howl=bool(hw), fr=fr, anchor=float(anchor)))
            W("")
    W("=" * 110)
    W("§F 单调性机械检查(Hr2:固定 G 下过门率随源电平**单调不减**;⛔ 判读文字由人在看到数之后写)")
    W("=" * 110)
    for dg in DG:
        for (T60, sd) in SEEDS:
            v = [(r['src'], r['n2']) for r in rows if r['dg'] == dg and r['T60'] == T60 and r['sd'] == sd]
            v.sort()
            bad = [(v[i][0], v[i][1], v[i + 1][0], v[i + 1][1])
                   for i in range(len(v) - 1) if v[i + 1][1] < v[i][1]]
            W(f"  ΔG={dg:+.0f} T60={T60} sd={sd}: N2_lvl 逐档 {v}   "
              f"{'✅单调不减' if not bad else '⛔ 出现下降:' + str(bad)}")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r76_fixedG_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r76_fixedG.json', 'w') as fp:
        json.dump(rows, fp)


if __name__ == '__main__':
    main()
