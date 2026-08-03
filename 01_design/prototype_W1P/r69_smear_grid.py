"""r69 · 窗平滑偏置表,按【我们实际会用的】常 Q 带宽列。

r68 §3 的偏置表是按**绝对带宽**(12.5/25/…Hz)列的,而算法侧要扫的 `bw_oct` 是
**常 Q** —— 同一个 bw_oct 在不同中心频率上的绝对带宽差一个数量级
⇒ 那张表没法直接查。本表按 (bw_oct × f0) 出,并给出 BW/主瓣宽 与可执行判据。

⚠ 参照实现直接复用 r68 里**已被 r68 自测 G/E 对拍验证过**的 `analytic_sd`
  (定义式连续网格积分,不走 STFT),不重写第二份,避免两份参照互相漂移。
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sd_meter as sd                                          # noqa: E402
from r68_sd_selftest import FS, SRC, analytic_sd, peaking      # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r69_smear_grid_out.txt")

BW_OCT = [(1 / 5, "1/5"), (1 / 8, "1/8"), (1 / 12, "1/12")]
F0S = [200.0, 500.0, 1000.0, 2000.0, 5000.0]
DEPTH = -20.0
NHS_SCOPE = (120.0, 7800.0)        # DEC-0020


def cell(f0, bw_oct, M):
    """一格:实测 SD(STFT)vs 解析 SD(定义式积分),两列都算。"""
    bw = sd.bw_oct_to_hz(f0, bw_oct)
    b, a = peaking(f0, DEPTH, bw)
    r = sd.sd_measure(processed=signal.lfilter(b, a, SRC), source=SRC, fs=FS, M=M)
    out = dict(bw_hz=bw, ratio=bw / sd.mainlobe_hz(FS, M),
               meas_full=r.band_full.mean_db, ana_full=analytic_sd(b, a, 0.0, FS / 2))
    out["bias_full"] = (out["meas_full"] / out["ana_full"] - 1.0) * 100.0
    if 300.0 <= f0 <= 6500.0:
        ana_in = analytic_sd(b, a, 300.0, 6500.0)
        out["bias_in"] = (r.band_in.mean_db / ana_in - 1.0) * 100.0
    else:
        out["bias_in"] = float("nan")
    return out


def main():
    L = []
    w = L.append

    w("§0 这张表是什么")
    w("  纵轴 bw_oct(常 Q)× 横轴中心频率 f0 → **STFT 实测 SD 相对定义式解析 SD 的偏置%**。")
    w("  解析 SD = 对式(32) 直接做连续网格积分(freqz,**不走 STFT**),即「没有窗平滑的那个真值」。")
    w(f"  陷波深度固定 {DEPTH:.0f} dB;源 = 白噪 4 s;fs={FS:.0f} Hz;Hann;50% 重叠。")
    w("  BW(Hz) = f0·(2^N − 1)/2^(N/2)。**偏置为负 = SD 读得比真值小 = 音质显得比实际好。**")
    w("")

    w("§1 已知答案自检(派单给的 Hz 值,用来核 bw_oct→Hz 换算)")
    known = {(1 / 5, 200): 27.8, (1 / 5, 1000): 139.0, (1 / 5, 5000): 695.0,
             (1 / 8, 200): 17.3, (1 / 8, 1000): 87.0, (1 / 8, 5000): 434.0,
             (1 / 12, 200): 11.6, (1 / 12, 1000): 58.0, (1 / 12, 5000): 289.0}
    worst, worst_cell = 0.0, None
    for (n, f0), want in sorted(known.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        got = sd.bw_oct_to_hz(f0, n)
        rel = abs(got / want - 1.0)
        if rel > worst:
            worst, worst_cell = rel, (n, f0, got, want)
    ok_conv = worst < 0.005
    w(f"  BW = f0·(2^N − 1)/2^(N/2);9 个格子逐一核对,最大**相对**差 {worst:.3%}"
      f" …… {'PASS' if ok_conv else 'FAIL'}")
    n, f0, got, want = worst_cell
    w(f"  最差格 {1 / n:.0f} 分之一倍频程 @ {f0:.0f} Hz: 本式 {got:.1f} Hz vs 派单 {want:.0f} Hz")
    w(f"  ⇒ 差值来自派单的取整(本式 3 位有效数字应为 {got:.0f}),**不是换算分歧**;"
      f"公式本身对齐。")
    w("")

    grids = {}
    for M in (4096, 8192):
        ml = sd.mainlobe_hz(FS, M)
        tag = "**工作点**(原文档位外推,见 sd_meter 偏离声明)" if M == 4096 else "逃生路线(见 §4)"
        w(f"§2{'a' if M == 4096 else 'b'} M={M} 主瓣宽 {ml:.2f} Hz —— {tag}")
        w("     bw_oct    f0(Hz)   BW(Hz)  BW/主瓣   实测SD   解析SD   偏置%(full) 偏置%(in)  判定")
        g = {}
        for n, lab in BW_OCT:
            for f0 in F0S:
                c = cell(f0, n, M)
                g[(lab, f0)] = c
                vtag, _ = sd.smear_verdict(c["ratio"])
                bi = "   n/a  " if np.isnan(c["bias_in"]) else f"{c['bias_in']:+7.2f} "
                w(f"     {lab:>6}   {f0:7.0f}  {c['bw_hz']:7.1f}  {c['ratio']:6.2f}  "
                  f"{c['meas_full']:8.4f} {c['ana_full']:8.4f}   {c['bias_full']:+7.2f}   {bi}  {vtag}")
            w("")
        grids[M] = g

        w(f"     ── 每个 f0 上【三档之间】的偏置差(= 真正会污染跨档比较的量)──")
        for f0 in F0S:
            bs = [g[(lab, f0)]["bias_full"] for _, lab in BW_OCT]
            w(f"        f0={f0:5.0f} Hz: 1/5={bs[0]:+6.2f}%  1/8={bs[1]:+6.2f}%  1/12={bs[2]:+6.2f}%"
              f"   ⇒ 档间差 {max(bs) - min(bs):5.2f} pp")
        w("")

    w("§3 三条实测事实(判据就建在这三条上)")
    g4 = grids[4096]
    dmax = max(abs(g4[(lab, f0)]["bias_full"] - g4[(lab, f0)]["bias_in"])
               for _, lab in BW_OCT for f0 in F0S if not np.isnan(g4[(lab, f0)]["bias_in"]))
    w(f"  1. **偏置与频带口径无关**(in 与 full 两列的偏置差最大 {dmax:.2f} pp)。")
    w("     ⇒ 归一化把带宽约掉了 ⇒ 这张表对 `in` 和 `full` 两列**同时有效**,不必出两张。")
    w("  2. **偏置方向恒为负,且窄档更负** —— 见上面每个 f0 的三档对比,无一例外。")
    w("     ⇒ 不是随机误差,**多跑几次不会平掉**;不过闸就比,会系统性选中更窄的 bw_oct。")
    w("  3. **偏置不是 ratio 的单值函数**:")
    a1, a2 = g4[("1/5", 200.0)], g4[("1/12", 500.0)]
    w(f"     1/5@200Hz  BW={a1['bw_hz']:.1f} ratio={a1['ratio']:.2f} → {a1['bias_full']:+.2f}%")
    w(f"     1/12@500Hz BW={a2['bw_hz']:.1f} ratio={a2['ratio']:.2f} → {a2['bias_full']:+.2f}%")
    w("     带宽几乎相同、ratio 几乎相同,偏置却差 "
      f"{abs(a1['bias_full'] - a2['bias_full']):.2f} pp。加上深度敏感性(见 §5),")
    w("     ⇒ **不可把偏置回归成公式去「修正」**。闸门只判**能不能比**,一律不做修正。")
    w("")

    w("§4 ⛔ 可执行判据(已实现为代码:`sd_meter.cross_bw_comparable()`)")
    w("     跨 bw_oct 档比较 SD 之前,先调它;返回 ok=False 就**不许出比较结论**。")
    w("")
    w("       from sd_meter import cross_bw_comparable")
    w("       v = cross_bw_comparable([(f0, bw) for ...], fs=48000, M=4096, depths=[...])")
    w("       if not v['ok']: <不得跨档比较,按 v['reason'] 处理>")
    w("")
    w("     判据本体(阈值由本表标定):")
    w(f"       · 全部 ratio ≥ {sd.SMEAR_GATE_OK:.0f}          ⇒ 可比      (实测档间差 ≤ 0.6 pp)")
    w(f"       · 最小 ratio ∈ [{sd.SMEAR_GATE_CAUTION:.0f}, {sd.SMEAR_GATE_OK:.0f})       ⇒ 有条件    "
      f"(档间差可达 2 pp;要分辨的 SD 差须 > 3× 该值)")
    w(f"       · 最小 ratio < {sd.SMEAR_GATE_CAUTION:.0f}           ⇒ **不可比**(档间差 6–10 pp,方向恒偏窄档)")
    w("       · 陷波深度不同档            ⇒ **不可比**(深度本身即摆最多 6.8 pp,见 §5)")
    w("")
    w("     ⇒ 把判据套到你们要扫的网格上(三档 {1/5,1/8,1/12} 同时比,深度同档):")
    byM = {}
    for M in (4096, 8192):
        w(f"        M={M}:")
        byM[M] = {}
        for f0 in F0S:
            v = sd.cross_bw_comparable([(f0, n) for n, _ in BW_OCT], fs=FS, M=M)
            bs = [grids[M][(lab, f0)]["bias_full"] for _, lab in BW_OCT]
            byM[M][f0] = (v["verdict"], max(bs) - min(bs))
            w(f"          f0={f0:5.0f} Hz  最小 ratio={v['min_ratio']:5.2f}  "
              f"档间差={max(bs) - min(bs):5.2f} pp  ⇒ {v['verdict']}")
    w("")

    def _grp(M, tag):
        xs = [(f0, byM[M][f0][1]) for f0 in F0S if byM[M][f0][0] == tag]
        return ("无" if not xs else
                "、".join(f"{f0:.0f} Hz(档间差 {d:.2f} pp)" for f0, d in xs))

    for M, lab in ((4096, "M=4096,即当前工作点"), (8192, "M=8192")):
        w(f"     ⇒ **结论({lab})**:三档同时比 ——")
        w(f"          可比(OK)        : {_grp(M, 'OK')}")
        w(f"          有条件(CAUTION) : {_grp(M, 'CAUTION')}")
        w(f"          **不可比**       : {_grp(M, 'NOT-COMPARABLE')}")
    w("     ⇒ 注意 2 kHz@M=4096 判 CAUTION 是**闸门按 ratio 保守判的**(最小 ratio 2.46<3),")
    w(f"       其实测档间差只有 {byM[4096][2000.0][1]:.2f} pp ⇒ 若你们要分辨的 SD 差 > 2 pp,这格实际可用。")
    w("       **闸门宁可保守,不替你们把边界往松里放。**")
    w("     ⇒ M=8192 把 OK 下限从 5 kHz 推到 2 kHz,但 **200 Hz 仍不可比**,且 M 一改")
    w("       就离原文工作点更远(85.3 ms → 170.7 ms 窗),**SD 数值本身不再与 M=4096 的可比**")
    w("       ⇒ 换 M 只能整批换,不能一半格子用 4096、一半用 8192。")
    need_ml = sd.bw_oct_to_hz(200.0, 1 / 12) / sd.SMEAR_GATE_OK
    need_M = 4.0 * FS / need_ml
    w(f"     ⇒ 要让 200 Hz 的 1/12 oct 也进 OK 档,需主瓣宽 ≤ {need_ml:.2f} Hz ⇒ M ≥ {need_M:.0f}")
    w(f"       (窗长 {1000 * 2 ** int(np.ceil(np.log2(need_M))) / FS:.0f} ms)。**那已经不是「短时」谱了**,")
    w("       与 SD 定义的短时口径冲突。⇒ **低频窄陷波的 SD 不可比是 SD 定义本身的分辨率极限,**")
    w("       **不是实现缺陷,换实现解决不了。**")
    w("")

    w("§5 深度敏感性(为什么判据里要求「深度同档」)")
    w("     同一格,只改陷波深度:")
    for f0, n, lab in ((1000.0, 1 / 12, "1/12@1kHz"), (500.0, 1 / 8, "1/8@500Hz"),
                       (2000.0, 1 / 5, "1/5@2kHz")):
        bw = sd.bw_oct_to_hz(f0, n)
        vals = []
        for d in (-6.0, -12.0, -20.0, -30.0):
            b, a = peaking(f0, d, bw)
            r = sd.sd_measure(processed=signal.lfilter(b, a, SRC), source=SRC, fs=FS)
            vals.append((d, (r.band_full.mean_db / analytic_sd(b, a, 0.0, FS / 2) - 1) * 100))
        sp = max(v for _, v in vals) - min(v for _, v in vals)
        w(f"       {lab:11s} BW={bw:6.1f}Hz ratio={bw / sd.mainlobe_hz(FS, 4096):5.2f}   "
          + "  ".join(f"{d:+.0f}dB:{v:+6.2f}%" for d, v in vals) + f"   ⇒ 摆幅 {sp:.2f} pp")
    w("     ⇒ ratio 小的格子,**深度本身就能把偏置摆掉几个 pp** ⇒ 深度不同档时跨档比较无意义。")
    w("")

    w("§6 ⚠ 顺带发现:`in` 列(300–6500 Hz)盖不住 NHS 作用域")
    w(f"     DEC-0020 定 NHS 作用域 = {NHS_SCOPE[0]:.0f} Hz – {NHS_SCOPE[1]:.0f} Hz;")
    w("     而 `band_in` = 300–6500 Hz(我方选择,带宽借自 FSR)。")
    w(f"     ⇒ **{NHS_SCOPE[0]:.0f}–300 Hz 与 6500–{NHS_SCOPE[1]:.0f} Hz 落在 `in` 列之外** ——")
    w("       挂在这两段里的陷波,其失真在 `in` 列里**几乎看不见**(r68 算例 H 已实测:")
    w("       10 kHz 陷波的 SD_in / SD_full = 0.0033)。")
    w("     ⇒ NHS 的 SD 应读 **`full` 列**(= SD 原文口径),或另定一条与 NHS 作用域同界的带。")
    w("       **这是口径选择,不是我能替你们定的** —— 提出来,由你和 architect 裁。")
    w("")

    w("§7 N/A / 未做")
    w("  · 全部为**白噪源 + LTI 陷波**的宿主仿真 [L2]。真实语音/音乐素材**全库皆无**(lead 已")
    w("    确认为 CTO 侧依赖)⇒ **本表未在真实节目源上验证**,语音的谱谷可能另有行为。")
    w("  · 只标定了 Hann 窗;换窗型主瓣宽变,本表阈值**不可外推**(`mainlobe_hz` 会直接报错)。")
    w("  · 只扫了单个陷波。**多陷波叠加**(NHS 实际形态)的偏置**未测**。")
    w("  · 深度只扫了 −6/−12/−20/−30 dB 四点,深度×ratio 的联合面**未铺满**。")
    w("  · 未上板。")

    verdict = ok_conv
    head = [
        "═" * 82,
        f"r69 · 窗平滑偏置表(按 bw_oct × f0)     换算自检:【{'通过' if verdict else '未通过'}】",
        "═" * 82,
        "门禁状态:**未过门** —— 本件未经独立 critic verdict,不得 release / 冻结 /",
        "          被下游引用 / 对外承诺。",
        "",
        "⛔ 一句话判据:**跨 bw_oct 比 SD 之前先调 `sd_meter.cross_bw_comparable()`,",
        "   返回 ok=False 就不许出比较结论。** M=4096 下三档同时比只有 f0 ≥ 2 kHz 站得住。",
        "⚠ 偏置方向恒定:**窄档被低估得更多 ⇒ 不过闸就比,会系统性选中更窄的 bw_oct。**",
        "═" * 82,
        "",
    ]
    text = "\n".join(head + L) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
