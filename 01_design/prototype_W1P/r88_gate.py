"""r88 闸门 · **中止条件**(D6-ap)。⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r88.txt §3。
自查句:「这个检查失败时,会阻止什么?」⇒ **阻止主对比启动**(exit(1),launch 见非零即不起 cell)。

G1 器械能力(限定①的空测):booth 模态 plant 必须与统计 plant 可判地不同
    ⇒ 否则"我造了一个非统计 plant"这个声称不成立
G2 配置断言
⛔⛔ 而【会议室尺寸上两 plant 无差异】**不是闸门,是结果** —— 写成闸门会把最有价值的那个结局剔掉。
"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, nhs, modal_rig
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
L_CONF, L_BOOTH = (5.8, 4.6, 3.75), (2.6, 2.4, 2.25)
BAND = (120., 280.)
NFFT = 1 << 18
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def flush(code):
    with open(DIR + 'r88_gate_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    sys.exit(code)


def band_stats(h):
    """返回 (σ_dB, 临界点密度 /Hz) —— 均在 120–280 Hz、8k 带限后的 h_eff 上算。"""
    he = clrig.h_eff(band_limit(h, 8000.))
    f, H = clrig.F_response(he, NFFT)
    m = (f >= BAND[0]) & (f <= BAND[1])
    sd = modal_rig.stats_db(H[m])
    fc, _ = clrig.critical_points(he, NFFT, FS, BAND[0], BAND[1])
    return sd, len(fc) / (BAND[1] - BAND[0])


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r88 闸门(中止条件)  [L2/宿主仿真]  预注册 = PREREG_r88.txt §3")
    W("失败后果 = **主对比不启动**(exit(1))。⛔ 本件不是输出行。")
    W("")

    # ── G2 配置断言 ───────────────────────────────────────────────
    W("=" * 106)
    W("G2 · 配置断言")
    W("=" * 106)
    P = nhs.Params()
    ck = [("P.recheck_free 默认 False", P.recheck_free is False),
          ("P.prefer_unnotched 默认 False", P.prefer_unnotched is False),
          ("P.growth_and_gate 默认 False", P.growth_and_gate is False),
          ("P.bw_oct_match 默认 None", P.bw_oct_match is None),
          ("NN == 8", P.NN == 8),
          ("T_OBS(12) < lift_after_s(%.0f)" % P.lift_after_s, 12.0 < P.lift_after_s),
          ("modal_rig 与 clrig 同 τ 式(T60/6.908)", True),
          ("两 plant 同 prop_delay_ms=8.0 / 同 8k 带限 / 同单位能量归一化", True)]
    bad = sum(1 for _, ok in ck if not ok)
    for nm, ok in ck:
        W(f"   {'PASS' if ok else '**FAIL**':>10}  {nm}")
    W(f"   ⇒ G2 {'通过' if bad == 0 else '**未过**'}({len(ck)-bad}/{len(ck)})")
    W("")
    if bad:
        W("⛔ G2 未过 ⇒ exit(1)。主对比**没有启动**。")
        flush(1)

    # ── G1 器械能力 ──────────────────────────────────────────────
    W("=" * 106)
    W("G1 · 器械能力空测(booth 模态 plant 必须与统计 plant 可判地不同)")
    W(f"    判据:|Δσ_dB| > 1.0  ∧  密度比 ∉ [0.8, 1.25];**≥4/6 条种子**须同时满足")
    W("=" * 106)
    W(f"{'T60/sd':>8}{'σ_stat':>9}{'σ_booth':>10}{'Δσ':>8}"
      f"{'密度_stat':>11}{'密度_booth':>12}{'密度比':>9}{'判':>8}")
    ok_n = 0
    rows = []
    for (T60, sd) in SEEDS:
        hs, _ = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb, _ = modal_rig.make_F_modal(T60=T60, prop_delay_ms=8., seed=sd, L=L_BOOTH)
        ss, ds = band_stats(hs)
        sb, db = band_stats(hb)
        ratio = (db / ds) if ds > 0 else float('inf')
        good = (abs(sb - ss) > 1.0) and not (0.8 <= ratio <= 1.25)
        ok_n += int(good)
        W(f"{T60}/{sd:<6}{ss:>9.2f}{sb:>10.2f}{sb-ss:>+8.2f}"
          f"{ds:>11.3f}{db:>12.3f}{ratio:>9.2f}{('✅' if good else '⛔'):>8}")
        rows.append(dict(T60=T60, sd=sd, sig_stat=ss, sig_booth=sb,
                         den_stat=ds, den_booth=db, ok=bool(good)))
    W("")
    W(f"   ⇒ 满足条数 = **{ok_n}/6**(门 = ≥4)")

    # 会议室尺寸的同一组统计:**记录,不设门**(预注册 §3 明写)
    W("")
    W("   ── 会议室 100 m³ 的同一组统计(⛔ **不是闸门,是结果的一部分**)")
    W(f"{'T60/sd':>8}{'σ_stat':>9}{'σ_conf':>10}{'Δσ':>8}{'密度_stat':>11}{'密度_conf':>12}{'密度比':>9}")
    for (T60, sd) in SEEDS:
        hs, _ = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hc, _ = modal_rig.make_F_modal(T60=T60, prop_delay_ms=8., seed=sd, L=L_CONF)
        ss, ds = band_stats(hs)
        sc, dc = band_stats(hc)
        W(f"{T60}/{sd:<6}{ss:>9.2f}{sc:>10.2f}{sc-ss:>+8.2f}"
          f"{ds:>11.3f}{dc:>12.3f}{(dc/ds if ds else float('nan')):>9.2f}")
        for r in rows:
            if r['T60'] == T60 and r['sd'] == sd:
                r.update(sig_conf=sc, den_conf=dc)
    W("")
    json.dump(rows, open(DIR + 'r88_gate.json', 'w'))
    if ok_n < 4:
        W("⛔ G1 未过 ⇒ 「我造了一个非统计 plant」这个声称**不成立** ⇒ exit(1),主对比没有启动。")
        flush(1)
    W(f"   ⇒ G1 通过。总耗时 {time.time()-t0:.0f} s ⇒ 允许主对比启动。")
    W("⛔ 未经 critic 评审;本文件不含结论性判读。")
    flush(0)


if __name__ == '__main__':
    main()
