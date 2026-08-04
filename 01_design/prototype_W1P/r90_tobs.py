"""r90 · `0.5/0` 单格窗长加跑(critic ARM_O_RECALC MAJOR-1)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r90.txt(§2 判据跑前写死)。
输出 r90_tobs_out.txt(D6-j)。⛔ 本文件不含结论性散文。
"""
import sys, json, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
T60, SD, SRC = 0.5, 0, -20.0
BW, DEPTH, F_CUT, STEP = 1 / 5, -18.0, 8000., 0.5
RUNGS = [6.0, 12.0, 24.0, 48.0]
M_O_ANA, DO_ANA = -9.2924, 3.198          # 第三方已两次复现
LO_OK, HI_OK = M_O_ANA - STEP, M_O_ANA    # 自洽区间 [−9.7924, −9.2924)
NA_PAIRS = None                            # 由 r89 的冻结配置载入
OUT = []


def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()


def mk_frozen(pairs):
    a = NHS(); a.P.bw_oct = BW
    for i, (f_, d_) in enumerate(pairs[:len(a.slots)]):
        s = a.slots[i]
        s.st = nhs.NotchSlot.HOLD
        s.f = float(f_); s.depth = float(d_); s.target = float(d_)
        s.set_coef(FS, BW)
    a.P.T_low = 999.
    a.duck_gain = lambda: 1.0
    return a


def scan(hb, D, mkf, lo, hi, src, ref):
    G, last = lo, None
    while G <= hi + 1e-9:
        a = mkf()
        pf = None if a is None else (lambda blk, _a=a: _a.process_frame(blk, GR))
        _, lp = clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            return (float('nan') if last is None else last)
        last = G
        G += STEP
    return float('nan')


def verdict(m):
    if not np.isfinite(m):
        return '⛔ 无数'
    if m >= HI_OK:
        return '(ii) **漏检**(T 不足)'
    if m < LO_OK:
        return '(iii) ⛔ **过检**(临界之下就响)—— 新问题'
    return '(i) **已收敛**(落在自洽区间)'


def main():
    t0 = time.time()
    global NA_PAIRS
    NA_PAIRS = [tuple(p) for r in json.load(open(DIR + 'r89_na_bias.json'))
                if r.get('repro') and r['T60'] == T60 and r['sd'] == SD for p in r['pairs']]
    W("未经 critic 评审 —— r90 · `0.5/0` 单格窗长加跑  [L2/宿主仿真]  预注册 = PREREG_r90.txt")
    W(f"解析真值(第三方两次复现):m_O = **{M_O_ANA}**,dO = **{DO_ANA}**")
    W(f"⭐ 自洽区间 [m_O_解析 − STEP, m_O_解析) = **[{LO_OK:.4f}, {HI_OK:.4f})** —— 判据跑前写死(§2)")
    W(f"⚠ T=12 的 m_O = −9.4907 **已在区间内** ⇒ 「再跌一整格」将是【过检】,不是「窗更长抓到更早失稳」")
    W(f"冻结 Na 配置(取自 r89):{NA_PAIRS}")
    W("")
    h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=SD)
    hb = band_limit(h0, F_CUT)
    he = clrig.h_eff(hb)
    picks = pick_excl(he, BW, 8)
    anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
    W(f"anchor(解析 m0)= {anchor:.4f}")
    W("")
    W(f"{'T_OBS':>7}{'m0':>10}{'m_O':>10}{'dO':>8}{'臂O偏差':>10}"
      f"{'m_Na冻结':>11}{'Na偏差':>9}{'缺口偏差':>10}{'判读(臂O)':>28}")
    rows = []
    for T in RUNGS:
        src = np.random.default_rng(SD).standard_normal(int(T * FS)) * (10 ** (SRC / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        m0 = scan(hb, D, lambda: None, anchor - 3, anchor + 4, src, ref)
        mO = scan(hb, D, lambda: mk_oracle(picks, BW, DEPTH), anchor - 1, anchor + 20, src, ref)
        mN = scan(hb, D, lambda: mk_frozen(NA_PAIRS), anchor - 1, anchor + 20, src, ref)
        dO = mO - m0 if np.isfinite(mO) and np.isfinite(m0) else float('nan')
        bO = mO - M_O_ANA
        # Na 的解析真值:冻结配置的 MSGMeter
        mNa_ana = MSGMeter(he, FS).msg(slots=mk_frozen(NA_PAIRS).slots, g_duck_db=0.)['full']['msg_db']
        bN = mN - mNa_ana
        gap = bO - bN
        W(f"{T:>7.0f}{m0:>10.4f}{mO:>10.4f}{dO:>8.2f}{bO:>+10.4f}"
          f"{mN:>11.4f}{bN:>+9.4f}{gap:>+10.4f}{verdict(mO):>28}")
        rows.append(dict(T=T, m0=m0, mO=mO, dO=dO, bias_O=bO, mNa=mN,
                         mNa_ana=float(mNa_ana), bias_Na=bN, gap_bias=gap))
    W("")
    W("=" * 108)
    W("§H 预注册假设逐条对表(⛔ 判据取自 PREREG_r90 §2,跑后未改)")
    W("=" * 108)
    g = {r['T']: r for r in rows}
    # H4 复现闸门
    ok6 = abs(g[6.0]['dO'] - 3.5) < 1e-9
    ok12 = abs(g[12.0]['dO'] - 3.0) < 1e-9
    W(f"  H4 复现闸门:T=6 dO={g[6.0]['dO']:.2f}(须 3.50){'✅' if ok6 else '⛔'} ｜ "
      f"T=12 dO={g[12.0]['dO']:.2f}(须 3.00){'✅' if ok12 else '⛔'}")
    if not (ok6 and ok12):
        W("  ⛔⛔ **复现失败 ⇒ 按预注册 H4,整件作废,不出结论**")
    else:
        W("  ✅ 复现通过 ⇒ 可读后续")
    W("")
    W(f"  H1 m_O(24) / m_O(48) 是否仍 == m_O(12) = {g[12.0]['mO']:.4f}?")
    for T in (24.0, 48.0):
        same = abs(g[T]['mO'] - g[12.0]['mO']) < 1e-9
        W(f"     T={T:.0f}: m_O={g[T]['mO']:.4f} ⇒ {'**相同**' if same else '**变了**'}"
          f"  臂O偏差 {g[T]['bias_O']:+.4f}  {verdict(g[T]['mO'])}")
    W("")
    W("  H2(承重)任一档 |缺口偏差| ≥ 0.50 ⇒ ②「0/6 格达整格」当场作废")
    mx = max(abs(r['gap_bias']) for r in rows if np.isfinite(r['gap_bias']))
    W(f"     逐档 |缺口偏差| = {[round(abs(r['gap_bias']),4) for r in rows]}  max = **{mx:.4f}**")
    W(f"     ⇒ {'⛔⛔ **≥0.50 ⇒ ② 作废,顶格报**' if mx >= 0.5 else '✅ **<0.50 ⇒ ② 在本格上未被推翻**'}")
    W("")
    W("  H3 举证门槛按不利方向设:若「不跌」,须同时给自洽区间证据(⛔ 不得只报两档相同)")
    for T in RUNGS:
        W(f"     T={T:.0f}: m_O={g[T]['mO']:.4f} vs 区间 [{LO_OK:.4f}, {HI_OK:.4f}) ⇒ {verdict(g[T]['mO'])}")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    open(DIR + 'r90_tobs_out.txt', 'w').write("\n".join(OUT) + "\n")
    json.dump(rows, open(DIR + 'r90_tobs.json', 'w'))


if __name__ == '__main__':
    main()
