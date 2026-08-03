"""r62 · 第四臂 `N-ablate`(NHS 自选 + duck 消融)+ 臂 N 的**运行时不变量断言**。

缘由(lead 批准,F33 在新一轮重现):r61 的臂 N 六条 `g_duck` 全打到 −6.00,
而只挂了 1–3 个陷波 ⇒ **1.00–2.50 dB 那一列里陷波与宽带兜底的占比未分离**。
⇒ 四臂各有名字,禁止合并:
   O = 神谕选点+无duck(上界) / N = NHS自选+有duck(产品实际) /
   **N-ablate = NHS自选+无duck(陷波在自选下的真实贡献)** / F = 等代价平坦(baseline)

⭐ **运行时不变量(借鉴 critic 判为"本轮最好修法"的护栏 B)**:
   它不是文本 lint,是**运行时断言**,且**不需要任何人事先想到"神谕选点"这个词**:
   > 凡被命名为「NHS 自选」的臂,其 **候选过门计数 `N2_lvl` 与 已分配槽数** 必须 > 0;
   > 若为 0 而仍以该名义报数 ⇒ **当场 FAIL**(那正是 B-1 的形状)。
   ⚠ 双向可失败:臂 O 上同一断言**必须为假**(它本就该是 0)—— 否则说明臂 O 没被真正钉死。

预注册:PREREG_r61.txt(本轮沿用;新增臂与断言为 verdict 整改项,非新假设)
输出   :r62_nablate_out.txt  [L2/宿主仿真]
deps   : clrig.py@8ad47ce8d260dd18, nhs.py@706b658842d84316,
         howl_detect.py@fd63e901f2d8be33, msg_meter.py, r61_bwoct_baseline
"""
import sys
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import (pick_excl, coverage, notch_H, bw_of, mk_oracle,
                                FRAME, STEP, F_CUT, GR, BWS, SEEDS)
OUT = []
def W(s):
    OUT.append(s); print(s); sys.stdout.flush()

def costs_all(he, picks, bw, depth):
    """三口径全报(lead 撤回单一主判据后的裁定):中位 / dB均值 / 功率均值。"""
    f0, _ = clrig.F_response(he, 1 << 18)
    m = (f0 >= 100.) & (f0 <= 8000.); fm = f0[m]
    N = np.ones(len(fm), complex)
    for p in picks: N = N * notch_H(p, fm, bw, depth)
    mag = np.abs(N); d = 20*np.log10(mag+1e-30)
    return float(np.median(d)), float(d.mean()), float(10*np.log10((mag**2).mean()))

def mk_n(bw, ablate):
    a = NHS(); a.P.bw_oct = bw
    if ablate: a.duck_gain = lambda: 1.0
    return a

def src_of(T, s): return 1e-3*np.random.default_rng(s).standard_normal(int(T*FS))

def scan(h, D, mk, lo, hi, src, ref):
    G, last, st = lo, None, None
    while G <= hi + 1e-9:
        alg = mk(); rec = []
        pf = None if alg is None else (lambda blk, _a=alg, _r=rec: (_r.append(_a.g_duck_db) or _a.process_frame(blk, GR)) if False else _post(_a, _r, blk))
        def _pf(blk, _a=alg, _r=rec):
            y = _a.process_frame(blk, GR); _r.append(_a.g_duck_db); return y
        _, lp = clrig.Loop(h, D, G, proc=(None if alg is None else _pf)).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            return (float('nan') if last is None else last), st
        last = G
        if alg is not None:
            used = [s for s in alg.slots if s.st != nhs.NotchSlot.FREE]
            st = dict(n_notch=len(used), gmin=float(np.min(rec)) if rec else 0.0,
                      n2=int(alg.ctr.get('N2_lvl', 0)), fr=sorted(round(float(s.f),1) for s in used))
        G += STEP
    return float('nan'), st

def _post(a, r, blk):
    y = a.process_frame(blk, GR); r.append(a.g_duck_db); return y

def main():
    DEPTH, T_OBS = -18.0, 12.0
    W("r62 · 第四臂 N-ablate + 臂N 运行时不变量断言   T_OBS=12s f_cut=8k depth=-18dB")
    W("deps: clrig.py@8ad47ce8d260dd18 nhs.py@706b658842d84316 howl_detect.py@fd63e901f2d8be33")
    W("[L2/宿主仿真]  三代价口径全报(lead 已撤回单一主判据)")
    W("⚠ M-1 的【胜负】在 SD 仪表化之前不下结论,本文只报条件式。")
    W("")
    W("%5s%4s | %7s %7s %7s | %8s %10s %10s | %s" % (
      'T60','sd','①中位','②dB均','③功率均','N(有duck)','N-ablate','duck贡献','不变量'))
    for bw in BWS:
        W("--- bw_oct = %.4f  (总带宽 %.2f oct)" % (bw, 8*bw))
        for (T60, sd) in SEEDS:
            h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
            hb = band_limit(h0, F_CUT); he = clrig.h_eff(hb)
            picks = pick_excl(he, bw, 8)
            c1, c2, c3 = costs_all(he, picks, bw, DEPTH)
            mt = MSGMeter(he, FS); anchor = mt.msg(slots=(), g_duck_db=0.)['full']['msg_db']
            src = src_of(T_OBS, sd); ref = HD.rms_db(src[:(len(src)//FRAME)*FRAME])
            m0, _ = scan(hb, D, lambda: None, anchor-3, anchor+3, src, ref)
            mn, stn = scan(hb, D, lambda: mk_n(bw, False), anchor-1, anchor+16, src, ref)
            ma, sta = scan(hb, D, lambda: mk_n(bw, True), anchor-1, anchor+16, src, ref)
            mo, sto = scan(hb, D, lambda: mk_oracle(picks, bw, DEPTH), anchor-1, anchor+16, src, ref)
            dn = mn-m0 if np.isfinite(mn) and np.isfinite(m0) else float('nan')
            da = ma-m0 if np.isfinite(ma) and np.isfinite(m0) else float('nan')
            # 运行时不变量:臂 N 必须有分配活动;臂 O 必须没有
            inv_n = (stn and stn['n2'] > 0 and stn['n_notch'] > 0)
            inv_o = (sto is None) or (sto['n2'] == 0)
            tag = ('N:OK' if inv_n else 'N:⛔FAIL') + '/' + ('O:OK' if inv_o else 'O:⛔FAIL')
            W("%5.1f%4d | %7.2f %7.2f %7.2f | %8.2f %10.2f %10.2f | %s" % (
              T60, sd, c1, c2, c3, dn, da, dn-da, tag))
            W("        N: %d陷波 g_duck最深%.2f N2_lvl=%d | N-ablate: %d陷波 g_duck最深%.2f | O: N2_lvl=%s" % (
              stn['n_notch'] if stn else -1, stn['gmin'] if stn else 0, stn['n2'] if stn else -1,
              sta['n_notch'] if sta else -1, sta['gmin'] if sta else 0,
              sto['n2'] if sto else 'n/a(全程未取到稳态)'))
        W("")
    open('/home/it1234/processor/01_design/prototype_W1P/r62_nablate_out.txt','w').write("\n".join(OUT)+"\n")

if __name__ == '__main__':
    main()
