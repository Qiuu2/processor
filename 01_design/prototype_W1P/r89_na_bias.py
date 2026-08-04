"""r89 · **Na 臂的检测器漏检幅度**(critic r4 MAJOR-1 修法③)。
⛔ 未经 critic 评审。[L2/宿主仿真]。预注册 = PREREG_r89.txt。输出 r89_na_bias_out.txt(D6-j)。

测什么:把 Na 跑出来的**最终陷波配置冻结成 LTI**,对它同时求
   (a) 解析临界增益(MSGMeter,频域)  (b) 时域闭环扫描读数(同一台 is_howling)
⇒ **b − a = 检测器在【Na 形状的临界点谱】上的漏检幅度**
⛔ 而**活的 Na 臂没有解析真值**(时变)⇒ 本件**不**给活臂编近似真值(预注册 §1)。

⚠ 数据缺陷与处置(跑前查出,留痕):`r87_cell_*.json` 里 `fr` 与 `depths` 是**各自独立排序**的
  ⇒ **(f, depth) 配对已丢失** ⇒ ⛔ 不得靠猜配对
  ⇒ 处置 = **确定性重跑**(同 seed / 同参数 / 同终点 G)取回带配对的槽表,
    并**逐格核对**重跑得到的 fr/depths 多重集与归档值一致(不一致即中止该格)。
"""
import sys, json, glob, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import GR, FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SRC, T_OBS, BW_OCT, TLOW, STEP, F_CUT = -20.0, 12.0, 1 / 5, -45.0, 0.5, 8000.
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
OUT = []


def W(s=''):
    OUT.append(s); print(s); sys.stdout.flush()


def mk_live():
    a = NHS(); a.P.bw_oct = BW_OCT; a.P.T_low = TLOW
    a.P.prefer_unnotched = False; a.P.recheck_free = False
    a.duck_gain = lambda: 1.0
    return a


def mk_frozen(pairs):
    """按 (f, depth) 冻结成 LTI:置 HOLD + set_coef;T_low=999 ⇒ 不再新分配。"""
    a = NHS(); a.P.bw_oct = BW_OCT
    for i, (f_, d_) in enumerate(pairs[:len(a.slots)]):
        s = a.slots[i]
        s.st = nhs.NotchSlot.HOLD
        s.f = float(f_); s.depth = float(d_); s.target = float(d_)
        s.set_coef(FS, BW_OCT)
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


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r89 · Na 臂检测器漏检幅度  [L2/宿主仿真]  预注册 = PREREG_r89.txt")
    W("测:冻结 Na 最终配置为 LTI ⇒ (a)解析临界增益 vs (b)时域扫描读数 ⇒ **b−a = 漏检幅度**")
    W("⛔ 活的 Na 臂无解析真值(时变)⇒ 本件不给活臂编近似真值")
    W("")
    R87 = {}
    for p in sorted(glob.glob(DIR + 'r87_cell_*.json')):
        for r in json.load(open(p))['rows']:
            if r['arm'] == 'A_base':
                R87[(r['T60'], r['sd'])] = r
    W(f"{'T60/sd':>8}{'配对复原':>10}{'挂陷':>5}{'(a)解析':>10}{'(b)实测':>10}{'b−a':>9}{'判读':>18}")
    rows = []
    for (T60, sd) in SEEDS:
        rec = R87.get((T60, sd))
        if rec is None:
            W(f"{T60}/{sd:<6}  ⛔ 无 r87 记录"); continue
        h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT); he = clrig.h_eff(hb)
        src = np.random.default_rng(sd).standard_normal(int(T_OBS * FS)) * (10 ** (SRC / 20.))
        ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
        # ── 确定性重跑取回 (f, depth) 配对 ──────────────────────
        a = mk_live()
        clrig.Loop(hb, D, rec['m'], proc=lambda b, _a=a: _a.process_frame(b, GR)).run(src, FRAME)
        used = [s for s in a.slots if s.st != nhs.NotchSlot.FREE]
        pairs = [(round(float(s.f), 1), round(float(s.depth), 2)) for s in used]
        ok = (sorted(p[0] for p in pairs) == list(rec.get('fr', []))
              and sorted(p[1] for p in pairs) == list(rec.get('depths', [])))
        if not ok:
            W(f"{T60}/{sd:<6}{'⛔ 不一致':>10}  ⇒ 该格中止(重跑未复现归档槽表)")
            rows.append(dict(T60=T60, sd=sd, repro=False)); continue
        af = mk_frozen(pairs)
        m_ana = MSGMeter(he, FS).msg(slots=af.slots, g_duck_db=0.)['full']['msg_db']
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        m_meas = scan(hb, D, lambda _p=pairs: mk_frozen(_p), anchor - 1, anchor + 20, src, ref)
        d = m_meas - m_ana
        jd = ('栅格内不可判' if abs(d) < 0.25 else ('一格' if abs(d) < 0.75 else '多格'))
        jd += ('(实测高于解析 ⇒ **漏检**)' if d > 0 else '(实测低于解析)')
        W(f"{T60}/{sd:<6}{'✅':>10}{len(pairs):>5}{m_ana:>10.3f}{m_meas:>10.2f}{d:>+9.3f}{jd:>18}")
        rows.append(dict(T60=T60, sd=sd, repro=True, n=len(pairs), pairs=pairs,
                         m_ana=float(m_ana), m_meas=float(m_meas), bias=float(d)))
    W("")
    W("=" * 104)
    W("§G 起跑前自查的兑现(预注册 §2):**检测器在 Na 形状上确实漏检过吗**")
    W("=" * 104)
    v = [r for r in rows if r.get('repro')]
    pos = [r for r in v if r['bias'] > 0]
    W(f"   b−a > 0 的格:**{len(pos)}/{len(v)}**  逐格 {[round(r['bias'],3) for r in v]}")
    if not pos:
        W("   ⛔ **0 格出现漏检 ⇒ 按预注册不得判「两端相等」**")
        W("      只能报:本手法在 Na 形状上**未测到**漏检;而本手法分辨力 = 栅格 0.5 dB")
        W("      ⇒ 小于半格(0.25)的偏差**本就读不出** ⇒ 「未测到」≠「不存在」")
    else:
        W(f"   ✅ 自查通过:被测量确实动过 ⇒ 幅度可读")
    W("")
    W("   ── 与臂 O 那端并列(verification V-F:实测 dO 高于解析真值 2/6 格,+0.169 / +0.019 dB)")
    W(f"   Na 端(本轮,冻结配置):{[round(r['bias'],3) for r in v]}")
    W("   ⚠ 两端**没有理由相等**:臂 O 是 LTI 的神谕谱;Na 是自适应选点后的谱")
    W("   ⛔ 本轮测的是**冻结配置**下的检测器偏差,**不是活臂在时变过程中的偏差**")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    open(DIR + 'r89_na_bias_out.txt', 'w').write("\n".join(OUT) + "\n")
    json.dump(rows, open(DIR + 'r89_na_bias.json', 'w'))


if __name__ == '__main__':
    main()
