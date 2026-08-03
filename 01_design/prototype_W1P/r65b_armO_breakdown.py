"""r65b · **新 INV-O 的 broken 版** —— 证明它【能失败】,否则它只是一段注释。

⛔ 未经 critic 评审。[L2/宿主仿真]。
输出:r65b_armO_breakdown_out.txt   (D6-j:路径唯一)
deps: nhs.py@706b658842d84316, clrig.py@8ad47ce8d260dd18,
      r57_bandlimit.py@74036010b514080d, r61_bwoct_baseline.py@830f15326cf264f6

═══════════════════════════════════════════════════════════════════
为什么必须有这个文件
═══════════════════════════════════════════════════════════════════
`MECHANISM_VERIFICATION_LEDGER.md` 的判据:
> **「一条没对 broken 输入失败过的护栏,不算护栏,是一段注释。」**

`r65` 证明了**旧** INV-O(`N2_lvl == 0`)**偏严**(7 例误杀),并给出了**阴性对照**
(臂 N 的 `频点==picks` 在 30/30 行上恒 False ⇒ 判据有分辨力)。
**但 `r65` 没有给出【新 INV-O 会 FAIL】的正例** —— 它测的 Δ 范围内臂 O 构造全都完好。
⇒ **按本项目自己的判据,新 INV-O 目前【未验】。** 本文件补这一刀。

⚠ 诚实标注:我在写 `r65` 之前的**探索性内联预跑**里见过一次
`T60=0.5/sd=1 @ G=−1.0 ⇒ 挂陷 8→6 且频点 ≠ picks`,但**那次没有落盘**
(只在会话里)⇒ 按「报告会被压缩、转述、随实例退役消失,盘面文件不会」,
**它不算证据**。本文件把它重做成盘面件。

═══════════════════════════════════════════════════════════════════
预注册(本段在本轮跑之前写下)
═══════════════════════════════════════════════════════════════════
Hr1 · **新 INV-O 能失败**
      构造:把环路增益推到远高于 MSG(Δ = anchor 之上 +10 / +12 / +14 dB),
      此时臂 O 的 8 个预挂陷波压不住,**维持路径**(`nhs.py:399` 已覆盖 bin 门 = −65)
      让候选过门 → 过 PAPR/PNPR → 成轨 → 分类 → `_allocate` 改写槽。
      预测:至少 1 例出现 `挂陷 != 8` 或 `频点 != picks` ⇒ **新 INV-O 判 FAIL**。
      证伪:全部 Δ 上构造都完好 ⇒ **新 INV-O 在本台架上不可失败 ⇒ 它不是护栏**,
            须另找能触发它的构造,或如实登记为「未验·可执行」。
Hr2 · **旧判据在同样的构造上分不出来**
      预测:存在 Δ 使 `N2_lvl > 0` 同时出现在【构造完好】与【构造已散】两种情形
      ⇒ 旧判据 `N2_lvl==0` 对"分配是否发生"**无分辨力**(它只是"有没有候选过电平门")。

⚠ 本轮 Δ 取值**远高于任何报数点**(报数点 Δ = ΔMSG_上界 ≈ 3.5–7.5)
  ⇒ 这里的数**不是性能数**,只用来回答"护栏能不能失败"。⛔ 不得当作任何 ΔMSG 引用。
⛔ 本文件不写结论散文。
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME

BW, DEPTH, T_OBS = 1 / 5, -18.0, 6.0
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
DELTAS = [10.0, 12.0, 14.0]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def main():
    W("未经 critic 评审 —— r65b · 新 INV-O 的 broken 版(能不能失败?)  [L2/宿主仿真]")
    W("deps: nhs.py@706b658842d84316 clrig.py@8ad47ce8d260dd18 "
      "r57_bandlimit.py@74036010b514080d r61_bwoct_baseline.py@830f15326cf264f6")
    W("⚠ 本轮 Δ = +10/+12/+14 dB **远高于任何报数点**(报数点 Δ≈3.5–7.5)")
    W("  ⇒ 这里的数不是性能数,只回答『护栏能不能失败』。⛔ 不得当 ΔMSG 引用。")
    W("")
    W(f"{'T60':>5}{'sd':>4}{'Δ':>6}{'G':>8}{'N2_lvl':>8}{'N3_gate':>8}{'挂陷':>5}"
      f"{'频点==picks':>12}{'preempt':>8}{'exh':>5}  {'新INV-O':>8}  {'旧INV-O':>8}")
    fail_new, both = [], {'intact_n2pos': 0, 'broken_n2pos': 0}
    for (T60, sd) in SEEDS:
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, 8000.)
        he = clrig.h_eff(hb)
        picks = pick_excl(he, BW, 8)
        pk = sorted(round(float(p), 1) for p in picks[:8])
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        src = 1e-3 * np.random.default_rng(sd).standard_normal(int(T_OBS * FS))
        for dl in DELTAS:
            G = anchor + dl
            a = mk_oracle(picks, BW, DEPTH)
            def pf(blk, _a=a):
                return _a.process_frame(blk, GR)
            clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
            used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
            fr = sorted(round(float(s.f), 1) for s in used)
            same = (fr == pk)
            n2 = int(a.ctr.get('N2_lvl', 0))
            intact = (len(used) == 8 and same)
            new_v = 'OK' if intact else '⛔FAIL'
            old_v = 'OK' if n2 == 0 else '⛔FAIL'
            if not intact:
                fail_new.append((T60, sd, dl, len(used), fr[:4]))
            if n2 > 0:
                both['intact_n2pos' if intact else 'broken_n2pos'] += 1
            W(f"{T60:>5.1f}{sd:>4}{dl:>6.1f}{G:>8.2f}{n2:>8}"
              f"{int(a.ctr.get('N3_gate', 0)):>8}{len(used):>5}{str(same):>12}"
              f"{int(a.ctr.get('preempt', 0)):>8}{int(a.ctr.get('slots_exhausted', 0)):>5}"
              f"  {new_v:>8}  {old_v:>8}")
    W("")
    W("=" * 104)
    W("§S  预注册假设逐条对表(机械事实;判读由人在看到数之后写)")
    W("=" * 104)
    W(f"  Hr1 新 INV-O 判 FAIL 的例数(证伪条件:0 ⇒ 它不可失败 ⇒ 不是护栏):{len(fail_new)}")
    for x in fail_new:
        W(f"      T60={x[0]}/sd={x[1]} Δ=+{x[2]:.0f}dB ⇒ 挂陷 {x[3]}/8,前 4 个频点 {x[4]}")
    W(f"  Hr2 `N2_lvl>0` 同时出现在两种情形的次数:构造完好 {both['intact_n2pos']} 例 / "
      f"构造已散 {both['broken_n2pos']} 例")
    W(f"      (两者都 >0 ⇒ 旧判据 `N2_lvl==0` 对『分配是否发生』无分辨力)")
    W("")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    open('/home/it1234/processor/01_design/prototype_W1P/'
         'r65b_armO_breakdown_out.txt', 'w').write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
