"""r88b 闸门 · **解析先验**中止条件(D6-ap)。⛔ 未经 critic 评审。预注册 = PREREG_r88b.txt §3。
⭐ 与 r88 的关键差别:判别量换成**解析模态重叠 M(f)** —— 零采样噪声,分辨力**先验可证**。
   r88 用的实测 σ_dB 已被证无分辨力(门 1.0 dB < 统计 plant 自身散布 1.42 dB)⇒ 降级为诊断。
自查句:「失败时会阻止什么?」⇒ **阻止主对比启动**(exit(1))。
"""
import sys, json, math, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs, modal_rig
from clrig import FS
from r57_bandlimit import band_limit

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
C = 343.0
BAND = (120., 280.)
L_MOD9, L_CONF = (2.2, 2.1, 1.95), (5.8, 4.6, 3.75)
T_POS = 0.5
OUT = []


def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()


def flush(code):
    open(DIR + 'r88b_gate_out.txt', 'w').write("\n".join(OUT) + "\n")
    sys.exit(code)


def M(V, f, T60):
    return 4 * math.pi * V * f * f / C ** 3 * (2.2 / T60)


def vol(L):
    return L[0] * L[1] * L[2]


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r88b 闸门(**解析先验**)  [L3/解析]  预注册 = PREREG_r88b.txt §3")
    W("失败后果 = **主对比不启动**(exit(1))。⛔ 本件不是输出行。")
    W("")
    W("=" * 100)
    W("G1 · 解析先验:M(f) = (4πVf²/c³)·(2.2/T60),零采样噪声")
    W("=" * 100)
    V9, Vc = vol(L_MOD9), vol(L_CONF)
    fs_grid = np.arange(BAND[0], BAND[1] + 1, 1.0)
    m9 = [M(V9, f, T_POS) for f in fs_grid]
    ok9 = all(x < 1.0 for x in m9)
    W(f"   P_mod9  L={L_MOD9}  V={V9:.2f} m³  T60={T_POS}")
    W(f"     M@120={m9[0]:.3f}  M@200={M(V9,200,T_POS):.3f}  M@280={m9[-1]:.3f}"
      f"   ⇒ 全频点 M<1 ? **{ok9}**")
    okc = True
    W(f"   P_conf  L={L_CONF}  V={Vc:.1f} m³")
    for T in (0.2, 0.5):
        mc = M(Vc, 120., T)
        okc = okc and (mc > 1.0)
        W(f"     T60={T}: M@120={mc:.2f}  M@280={M(Vc,280.,T):.2f}  ⇒ M(120)>1 ? {mc > 1.0}")
    W("")
    W(f"   ⇒ G1 {'通过' if (ok9 and okc) else '**未过**'}"
      f"(阳性对照全段模态={ok9} ∧ 主对比臂非孤立={okc})")
    W("")
    if not (ok9 and okc):
        W("⛔ G1 未过 ⇒ exit(1)。主对比**没有启动**。")
        flush(1)
    W("=" * 100)
    W("G2 · 配置断言")
    W("=" * 100)
    P = nhs.Params()
    ck = [("P.recheck_free 默认 False", P.recheck_free is False),
          ("P.prefer_unnotched 默认 False", P.prefer_unnotched is False),
          ("P.growth_and_gate 默认 False", P.growth_and_gate is False),
          ("P.bw_oct_match 默认 None", P.bw_oct_match is None),
          ("NN == 8", P.NN == 8),
          ("T_OBS(12) < lift_after_s(%.0f)" % P.lift_after_s, 12.0 < P.lift_after_s)]
    bad = sum(1 for _, o in ck if not o)
    for nm, o in ck:
        W(f"   {'PASS' if o else '**FAIL**':>10}  {nm}")
    W(f"   ⇒ G2 {'通过' if bad == 0 else '**未过**'}({len(ck)-bad}/{len(ck)})")
    if bad:
        W("⛔ G2 未过 ⇒ exit(1)。")
        flush(1)
    W("")
    W("=" * 100)
    W("§D 诊断(⛔ **非闸门**):实测 σ_dB —— r88 已证该判据无分辨力,此处只记录不判定")
    W("=" * 100)
    W(f"{'T60/sd':>8}{'σ_stat':>9}{'σ_mod9':>9}{'σ_conf':>9}")
    rows = []
    for (T60, sd) in [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]:
        def sig(h):
            he = clrig.h_eff(band_limit(h, 8000.))
            f, H = clrig.F_response(he, 1 << 18)
            m = (f >= BAND[0]) & (f <= BAND[1])
            return modal_rig.stats_db(H[m])
        ss = sig(clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)[0])
        sc = sig(modal_rig.make_F_modal(T60=T60, prop_delay_ms=8., seed=sd, L=L_CONF)[0])
        s9 = (sig(modal_rig.make_F_modal(T60=T60, prop_delay_ms=8., seed=sd, L=L_MOD9)[0])
              if abs(T60 - T_POS) < 1e-9 else float('nan'))
        W(f"{T60}/{sd:<6}{ss:>9.2f}{s9:>9.2f}{sc:>9.2f}")
        rows.append(dict(T60=T60, sd=sd, sig_stat=ss, sig_mod9=s9, sig_conf=sc))
    json.dump(rows, open(DIR + 'r88b_gate.json', 'w'))
    W("")
    W(f"   ⇒ G1/G2 均通过。总耗时 {time.time()-t0:.0f} s ⇒ 允许主对比启动。")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    flush(0)


if __name__ == '__main__':
    main()
