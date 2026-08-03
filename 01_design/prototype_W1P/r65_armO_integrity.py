"""r65 · **臂 O 构造完整性 + INV-O 的可失败性** —— 打护栏本身,不是打结论。

⛔ 未经 critic 评审。[L2/宿主仿真]。
输出:r65_armO_integrity_out.txt      (D6-j:路径唯一)
deps: nhs.py@706b658842d84316, clrig.py@8ad47ce8d260dd18,
      r57_bandlimit.py@74036010b514080d, r61_bwoct_baseline.py@830f15326cf264f6,
      msg_meter.py@a0c16fd22b29f083

═══════════════════════════════════════════════════════════════════
缘起(critic 交接件 §4.1 原话)
═══════════════════════════════════════════════════════════════════
> 「护栏 B 是本轮最好的一条修法。**正因为我给了高评价,请你比对别的更严地打它。**」

**打的结果(代码事实,先写在前面)**:
  `nhs.py:396`  `cov = self._notch_covers(k*df)`   ← 该 bin 是否落在**本层已挂陷波**覆盖内
  `nhs.py:399`  `if gr_ok or cov: gate = P.T_low_gr`(= **−65 dBFS**,不是 999)
⇒ **臂 O 预挂 8 个陷波 ⇒ 这 8 个频点的 `cov` 恒 True ⇒ 它们的门是 −65,不是 999。**
⇒ 「`T_low=999` ⇒ `N2_lvl` 恒 0」**不成立** —— 只有「**首次获取**(未覆盖 bin)」被关掉,
  **维持路径(已覆盖 bin)一直开着**(这正是 `r57` 文件头 2026-08-03 那条勘正说的)。
⇒ **`N2_lvl == 0` 是【经验结果】,不是【构造保证】。**

**已观测(⚠ 探索性预跑,非预测)**:同一条种子上
  `G = −8.0` ⇒ `N2_lvl = 0`;`G = −4.0` ⇒ `N2_lvl = 640`;
  `T60=0.5/sd=1 @ G = −1.0` ⇒ `N2_lvl=1348, N3_gate=144`,**挂陷 8 → 6 且频点 ≠ picks**
  ⇒ **臂 O 的构造在高环路增益下会自己散掉。**

═══════════════════════════════════════════════════════════════════
预注册(⚠ 本段在**本轮扫描跑之前**写下;上面"已观测"三行不属于预测)
═══════════════════════════════════════════════════════════════════
Hq1 · **在实际读数的那个 G 上,臂 O 构造仍成立**
      读数 G ≈ `anchor + ΔMSG_上界`(r57 六条 = 6.00/6.00/7.50/3.50/6.50/4.50)。
      预测:该 G 上 `挂陷 == 8` 且 8 个频点与 `picks` 逐一相等。
      **证伪(任一条不成立)⇒ `r57` 那句「被测对象 = 8 个 RBJ 陷波器,由解析式放在最优点上」
        在【它自己的工作点上】就不准确 ⇒ B-1 的描述还要再往下修一层,须报 lead 并进 FINDINGS。**
Hq2 · **INV-O 会在读数点附近误报**
      预测:存在 `Δ ≤ 8 dB` 使 `N2_lvl > 0` 而构造仍完好(挂陷=8、频点=picks)
      ⇒ 说明 `N2_lvl==0` 作为 INV-O **偏严**,会把好数据判 FAIL。
      判读:若成立 ⇒ INV-O 应改为**构造精确**的形式:`挂陷==8 ∧ 频点==picks`
            (= 「**没有发生新分配**」,这才是 B-1 横幅真正断言的那件事)。
Hq3 · 阴性对照(D6-d:拿掉被测物这个数应该等于多少)
      臂 N(自选、8 槽全空)在同样的 G 上 `挂陷` 应 > 0 而**频点与 picks 不应逐一相等**
      ⇒ 证明本探针的"频点一致性"判据**能分辨两种臂**,不是恒真。

⛔ 本文件不写结论散文;判读由人在看到数之后写。
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME

BW, DEPTH, T_OBS = 1 / 5, -18.0, 6.0
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
# r57_bandlimit_out.txt §2 逐条 ΔMSG_上界@带限8k_神谕选点(同序)
R57_DMSG = [6.00, 6.00, 7.50, 3.50, 6.50, 4.50]
DELTAS = [0.0, 2.0, 4.0, 6.0, 8.0]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def run_arm(hb, D, G, src, mk):
    a = mk()
    def pf(blk, _a=a):
        return _a.process_frame(blk, GR)
    clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
    return dict(n2=int(a.ctr.get('N2_lvl', 0)), n3=int(a.ctr.get('N3_gate', 0)),
                n_notch=len(used),
                fr=sorted(round(float(s.f), 1) for s in used),
                preempt=int(a.ctr.get('preempt', 0)),
                exh=int(a.ctr.get('slots_exhausted', 0)))


def main():
    W("未经 critic 评审 —— r65 · 臂 O 构造完整性 + INV-O 可失败性   [L2/宿主仿真]")
    W("deps: nhs.py@706b658842d84316 clrig.py@8ad47ce8d260dd18 "
      "r57_bandlimit.py@74036010b514080d r61_bwoct_baseline.py@830f15326cf264f6")
    W(f"工作点:f_cut=8k / bw_oct=1/5 / depth={DEPTH} / T_OBS={T_OBS}s / frame={FRAME} / 8 槽")
    W("代码事实:nhs.py:396-401  `cov=_notch_covers(bin)` ⇒ `gr_ok or cov` ⇒ gate=T_low_gr(−65)")
    W("         ⇒ 臂O 的 8 个预挂频点门 = −65 dBFS,**不是 999** ⇒ 维持路径一直开着")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'Δ(dB)':>7}{'G':>8}  {'臂O:N2_lvl':>11}{'N3_gate':>9}"
      f"{'挂陷':>5}{'频点==picks':>12}{'preempt':>8}  || {'臂N:挂陷':>9}{'频点==picks':>12}")
    broken, inv_over = [], []
    for i, (T60, sd) in enumerate(SEEDS):
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        picks = pick_excl(he, BW, 8)
        pk = sorted(round(float(p), 1) for p in picks[:8])
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = 1e-3 * np.random.default_rng(sd).standard_normal(int(T_OBS * FS))
        W(f"  -- T60={T60}/sd={sd}  anchor={anchor:+.2f}  r57读数点 Δ={R57_DMSG[i]:.2f} "
          f"⇒ G≈{anchor + R57_DMSG[i]:+.2f}   picks={pk}")
        for dl in sorted(set(DELTAS + [R57_DMSG[i]])):
            G = anchor + dl
            o = run_arm(hb, D, G, src, lambda: mk_oracle(picks, BW, DEPTH))
            n = run_arm(hb, D, G, src, lambda: (lambda a: (setattr(a.P, 'bw_oct', BW), a)[1])(NHS()))
            same_o = (o['fr'] == pk)
            same_n = (n['fr'] == pk)
            mark = '  ← r57 读数点' if abs(dl - R57_DMSG[i]) < 1e-9 else ''
            W(f"{T60:>5.1f}{sd:>4}{dl:>7.2f}{G:>8.2f}  {o['n2']:>11}{o['n3']:>9}"
              f"{o['n_notch']:>5}{str(same_o):>12}{o['preempt']:>8}  || "
              f"{n['n_notch']:>9}{str(same_n):>12}{mark}")
            if abs(dl - R57_DMSG[i]) < 1e-9:
                if not (o['n_notch'] == 8 and same_o):
                    broken.append((T60, sd, dl, o['n_notch'], same_o))
                if o['n2'] > 0 and o['n_notch'] == 8 and same_o:
                    inv_over.append((T60, sd, dl, o['n2']))
            elif o['n2'] > 0 and o['n_notch'] == 8 and same_o:
                inv_over.append((T60, sd, dl, o['n2']))
        W("")
    W("=" * 110)
    W("§S  预注册假设逐条对表(机械事实;判读由人在看到数之后写)")
    W("=" * 110)
    W(f"  Hq1 在 r57 读数点上臂 O 构造**已散掉**的条(证伪条件:≥1):{len(broken)}  {broken}")
    W(f"  Hq2 `N2_lvl>0` 而构造完好(⇒ INV-O 偏严、会把好数据判 FAIL)的 (T60,sd,Δ,N2_lvl):")
    W(f"      共 {len(inv_over)} 例  {inv_over}")
    W(f"  Hq3 见上表『臂N:频点==picks』列 —— 若恒为 True 则该判据无分辨力(D6-d)")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/'
         'r65_armO_integrity_out.txt', 'w').write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
