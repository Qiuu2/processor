"""r92 · T60=0.35 单格(critic r8 提的中间点;lead 批)。⛔ 不跑冻结 Na(见 PREREG_r92 §1)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r92.txt(§2 判据跑前写死,含"未收敛怎么记")。
输出 r92_cell_<tag>_out.txt(D6-j)。⛔ 本文件不含结论性散文。
"""
import sys, json, time, argparse
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SRC = -20.0
BW, DEPTH, F_CUT, STEP = 1 / 5, -18.0, 8000., 0.5
RUNGS = [12.0, 24.0, 48.0]

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


def verdict(m, ana):
    """三分(PREREG_r91 §2):区间 = [ana − STEP, ana)。"""
    if not np.isfinite(m):
        return '⛔ 无数', 'nan'
    if m >= ana:
        return '(ii) **漏检 = 未收敛**', 'unconv'
    if m < ana - STEP:
        return '(iii) ⛔ **过检** —— 新问题,单列', 'over'
    return '(i) **已收敛**', 'conv'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t60', type=float, required=True)
    ap.add_argument('--sd', type=int, required=True)
    ap.add_argument('--tag', type=str, required=True)
    A = ap.parse_args()
    t0 = time.time(); T60, SD = A.t60, A.sd
    pairs = None   # ⛔ 本轮不跑冻结 Na(PREREG_r92 §1):r89 无该 T60 配置,而本问只需 m 本身的收敛性
    W(f"未经 critic 评审 —— r91 单格 tag={A.tag}(T60={T60}/sd={SD})  [L2/宿主仿真]  预注册 = PREREG_r92.txt")
    W(f"⭐ 解析真值**本轮自算**(MSGMeter),⛔ 不从 critic verdict 转抄")
    W("⛔ 本轮不跑冻结 Na —— 本问只需 m 本身的收敛性,臂 O 是 LTI 有解析真值,足够")
    h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=SD)
    hb = band_limit(h0, F_CUT); he = clrig.h_eff(hb)
    picks = pick_excl(he, BW, 8)
    mt = MSGMeter(he, FS)
    anchor = mt.msg(slots=(), g_duck_db=0.)['full']['msg_db']
    mO_ana = mt.msg(slots=mk_oracle(picks, BW, DEPTH).slots, g_duck_db=0.)['full']['msg_db']
    mN_ana = float('nan')
    W(f"解析:anchor={anchor:.4f}  m_O_解析={mO_ana:.4f}(dO={mO_ana-anchor:.3f})  m_Na_解析={mN_ana:.4f}")
    W(f"自洽区间:臂O [{mO_ana-STEP:.4f}, {mO_ana:.4f})  ｜  Na [{mN_ana-STEP:.4f}, {mN_ana:.4f})")
    W("")
    W(f"{'T_OBS':>7}{'m_O':>10}{'臂O偏差':>10}{'臂O判读':>26}{'m_Na':>10}{'Na偏差':>9}{'Na判读':>26}{'缺口偏差':>11}")
    rows = []
    for T in RUNGS:
        src = np.random.default_rng(SD).standard_normal(int(T * FS)) * (10 ** (SRC / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        mO = scan(hb, D, lambda: mk_oracle(picks, BW, DEPTH), anchor - 1, anchor + 20, src, ref)
        mN = float('nan')
        bO, bN = mO - mO_ana, mN - mN_ana
        vO, kO = verdict(mO, mO_ana); vN, kN = verdict(mN, mN_ana)
        gap = bO - bN
        usable = (kO == 'conv' and kN == 'conv')
        W(f"{T:>7.0f}{mO:>10.4f}{bO:>+10.4f}{vO:>26}{mN:>10.4f}{bN:>+9.4f}{vN:>26}"
          f"{(f'{gap:+.4f}' if usable else '**[未收敛]**'):>11}")
        rows.append(dict(T60=T60, sd=SD, T=T, mO=mO, mN=mN, mO_ana=float(mO_ana), mN_ana=float(mN_ana),
                         bias_O=bO, bias_Na=bN, gap_bias=gap, vO=kO, vN=kN, usable=bool(usable)))
    W("")
    g12 = [r for r in rows if r['T'] == 12.0][0]
    W(f"  Hs2 复现闸门:T=12 缺口偏差 = {g12['gap_bias']:+.4f}(须复现 r89 已报值)")
    W(f"  Hs3 T=48:臂O {rows[-1]['vO']} / Na {rows[-1]['vN']}"
      f"{'  ⇒ ⛔ 48 s 内未收敛,如实记,不外推不加档' if not rows[-1]['usable'] else ''}")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    open(DIR + f'r92_cell_{A.tag}_out.txt', 'w').write("\n".join(OUT) + "\n")
    json.dump(rows, open(DIR + f'r92_cell_{A.tag}.json', 'w'))


if __name__ == '__main__':
    main()
