"""r64 · **自由槽位起振扫描 + `T_OBS` 自适应阶梯** —— critic verdict 放行条件第 1 项 b 支。

⛔ 未经 critic 评审。全部 [L2/宿主仿真]。
预注册:PREREG_r64.txt(三臂定义 / 双向不变量 / T_OBS 阶梯与收敛判据 / Hp1–Hp5,**跑前落盘**)
        + 同文件 §9「跑前修订 A」(A-1 INV-N 改三分,不再丢不利数据 / A-2 Hp2 拆 a·b /
          A-3 未收敛条另计一行)
        + 同文件 §10「跑前修订 B」(**B-1 INV-O 改构造精确 `挂陷8 ∧ 频点==picks`,
          旧 `N2_lvl==0` 降为诊断量;B-2 作废范围按【臂】不按【行】;B-3 臂O 构造逐档打印**)
        —— 两次修订均在**产出任何数据之前**追加,`PREREG §0–§8` 一字未改(E-2)。
        ⚠ 14:13:39 曾按修订 A 版启动一次注册跑,14:18:03 主动中止(理由 = §10),
          **未产出输出文件**;日志留存为 `r64_run_ABORTED_1418.log`,不得当数据引用。
输出   :r64_freeslot_ladder_out.txt      日志:r64_run.log(nohup,独立于会话)
deps   : nhs.py@706b658842d84316, clrig.py@8ad47ce8d260dd18,
         howl_detect.py@fd63e901f2d8be33, msg_meter.py@a0c16fd22b29f083,
         r57_bandlimit.py@74036010b514080d, r61_bwoct_baseline.py@830f15326cf264f6,
         dmsg_two_arm.py@53067e5a6a0c3cb5

回答的问题(D6-b 被测对象):**NHS 在 8 槽全空、自己检测/选点/分配的条件下,
把闭环 MSG 抬高了多少 dB。** 混淆面见 PREREG_r64.txt §8。

⛔ 本文件**不含任何结论性散文** —— 结论只能在看到数之后写(纪律 7)。
   脚本里唯一的判定语句 = `≥4dB?/≥5dB?` 阈值比较(阈值由 CTO 给定)与运行时不变量。
"""
import sys, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from msg_meter import MSGMeter
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME
from dmsg_two_arm import DMSGReport

# ── 工作点(锁死;⛔ 本轮不扫 bw_oct)──────────────────────────────
BW_OCT = 1 / 5
DEPTH = -18.0
F_CUT = 8000.
STEP = 0.5
CONV_TOL = STEP / 2                      # 收敛容差 = 半个阶梯 = 0.25 dB
LADDER = [6.0, 12.0, 24.0, 48.0]
T_MAX = LADDER[-1]
F_REF = 120.0                            # = nhs.py:69 f_det_lo,C1 的 1/f 锚点
T_BASE = 6.0
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
TARGETS = (4.0, 5.0)                     # CTO 给定的目标区间下沿/上沿
# D6-j:输出路径唯一。**只有注册跑写这个路径**;机制烟测须改写本常量,不得复用。
OUT_PATH = ('/home/it1234/processor/01_design/prototype_W1P/'
            'r64_freeslot_ladder_out.txt')

OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def src_of(T, s):
    """⚠ 同一 seed 下,长窗的前缀 == 短窗 ⇒ 阶梯各档是【严格延长】,不是换信号。"""
    return 1e-3 * np.random.default_rng(s).standard_normal(int(T * FS))


def t_req_of(f_min):
    """C1:`T_req(f) = 6.0 × max(1, 120/f)`(PREREG §4)。f 非有限 ⇒ 无法判定。"""
    if f_min is None or not np.isfinite(f_min) or f_min <= 0:
        return float('nan')
    return T_BASE * max(1.0, F_REF / f_min)


def scan(h, D, mk, lo, hi, src, ref):
    """增益阶梯扫描:返回 (m, f_trig, state, status)。
    m      = **最后一个不起振的 G**;f_trig = **第一个起振的 G** 上末 1 s 的主导频率
    state  = m 那一点的实例状态(n_notch / N2_lvl / g_duck 最深 / 频点表)
    status = 'ok' | 'howl_at_lo'(起点即起振,须回落重扫)| 'no_howl'(到 hi 仍不起振)
    """
    G, last, st = lo, None, None
    while G <= hi + 1e-9:
        alg = mk()
        rec = []
        if alg is None:
            pf = None
        else:
            def pf(blk, _a=alg, _r=rec):
                y = _a.process_frame(blk, GR)
                _r.append(_a.g_duck_db)
                return y
        _, lp = clrig.Loop(h, D, G, proc=pf).run(src, FRAME)
        hw, _, _ = HD.is_howling(lp, ref, FS, FRAME)
        if hw:
            n = int(min(1.0, len(lp) / FS) * FS)
            Xf = np.abs(np.fft.rfft(lp[-n:] * np.hanning(n)))
            ft = float(np.fft.rfftfreq(n, 1 / FS)[int(np.argmax(Xf))])
            if last is None:
                return float('nan'), ft, None, 'howl_at_lo'
            return last, ft, st, 'ok'
        last = G
        if alg is not None:
            used = [s for s in alg.slots if s.st != nhs.NotchSlot.FREE]
            st = dict(n_notch=len(used),
                      n2=int(alg.ctr.get('N2_lvl', 0)),
                      preempt=int(alg.ctr.get('preempt', 0)),
                      gmin=float(np.min(rec)) if rec else 0.0,
                      fr=sorted(round(float(s.f), 1) for s in used))
        G += STEP
    return float('nan'), float('nan'), st, 'no_howl'


def mk_self(ablate):
    """臂 N / 臂 Na:`NHS()` 默认参数(`T_low=−45`)、**8 槽全空**、检测/分类/分配全开。
    ablate=True ⇒ 只切 `duck` 的**音频施加**,状态机照跑(§7.4② 既定手法)。"""
    a = NHS()
    a.P.bw_oct = BW_OCT
    if ablate:
        a.duck_gain = lambda: 1.0
    return a


def run_rung(hb, D, picks, anchor, T60, sd, T, prev_m):
    """跑一档 T_OBS 的四个臂。prev_m = 上一档各臂的 m(用于起点上移,PREREG §4)。"""
    src = src_of(T, sd)
    ref = HD.rms_db(src[:(len(src) // FRAME) * FRAME])
    res, fallbacks = {}, []
    plan = [
        ('m0', lambda: None,                          anchor - 3, anchor + 4),
        ('O',  lambda: mk_oracle(picks, BW_OCT, DEPTH), anchor - 1, anchor + 20),
        ('N',  lambda: mk_self(False),                anchor - 1, anchor + 20),
        ('Na', lambda: mk_self(True),                 anchor - 1, anchor + 20),
    ]
    for key, mk, lo0, hi in plan:
        lo = lo0
        if prev_m and np.isfinite(prev_m.get(key, float('nan'))):
            # 起点上移省算力:m 随 T 单调不增 ⇒ 留 1.5 dB(3 格)余量;
            # **不得低于原始下限 lo0**,且两者都在 `anchor + 0.5×整数` 栅格上 ⇒ 栅格不变。
            lo = max(lo0, prev_m[key] - 1.5)
        m, ft, st, status = scan(hb, D, mk, lo, hi, src, ref)
        if status == 'howl_at_lo':                    # 回落全程重扫,并留痕
            fallbacks.append(f"{key}@lo={lo:+.2f}")
            m, ft, st, status = scan(hb, D, mk, anchor - 3, hi, src, ref)
        res[key] = dict(m=m, f_trig=ft, st=st, status=status)
    fts = [res[k]['f_trig'] for k in res if np.isfinite(res[k]['f_trig'])]
    f_min = min(fts) if fts else float('nan')
    m0 = res['m0']['m']
    for k in ('O', 'N', 'Na'):
        res[k]['d'] = (res[k]['m'] - m0) if (np.isfinite(res[k]['m']) and np.isfinite(m0)) \
            else float('nan')
    return dict(T=T, res=res, f_min=f_min, t_req=t_req_of(f_min), fallbacks=fallbacks)


def invariants(rung, pk):
    """护栏 B —— PREREG §3 + **修订 A-1** + **修订 B-1/B-2**。返回 (inv_O, inv_N, 说明串)。

    ⛔ 修订 B-1:INV-O 改为【构造精确】—— `挂陷==8 ∧ 频点逐一==picks`(= **没有发生新分配**)。
       旧判据 `N2_lvl == 0` **降级为诊断量**:`nhs.py:396-401` 对**已覆盖 bin** 的维持路径
       门是 `T_low_gr = −65`(不是 999),故 `N2_lvl` 在高环路增益下本就会 > 0,
       与"分配是否发生"无关。`r65` 实测 Δ=+8 dB 时 `N2_lvl=611/374` 而构造完好。
    ⛔ 修订 B-2:作废范围**按臂**,不按行 —— 臂 O 散掉不作废臂 N 的读数。

    inv_O: 'OK' | 'FAIL'                  → 只管 `ΔMSG_上界@神谕` 一列
    inv_N: 'OK' | 'ZERO_ACT' | 'FAIL'     → 只管 `ΔMSG_自选@…` 两列
           ZERO_ACT = NHS 全程零动作且 ΔMSG ≤ STEP ⇒ **合法的不利结果,照常计入统计**
           FAIL     = 零动作却有收益 = B-1 的形状(收益来自别处)
    ⚠ 原值(N2_lvl / 挂陷 / 频点)一律打印,不只打印判定 —— 判定看不出成因。
    """
    r = rung['res']
    msgs = []
    so = r['O']['st']
    if so is None:
        inv_O = 'FAIL'
        msgs.append("O:⛔无状态(未取到不起振点)")
    else:
        same = (so['fr'] == pk)
        good = (so['n_notch'] == 8 and same)
        inv_O = 'OK' if good else 'FAIL'
        msgs.append(f"O:挂陷={so['n_notch']}/8,频点==picks:{same}"
                    f"{'✅未发生新分配' if good else '⛔构造已散(臂O 无效)'}"
                    f"(诊断 N2_lvl={so['n2']},非判据)")
    inv_N = 'OK'
    for k in ('N', 'Na'):
        s, d = r[k]['st'], r[k]['d']
        if s is None:
            inv_N = 'FAIL'
            msgs.append(f"{k}:⛔无状态")
            continue
        if s['n2'] > 0 and s['n_notch'] > 0:
            msgs.append(f"{k}:N2_lvl={s['n2']},挂陷={s['n_notch']}✅动作发生")
        elif np.isfinite(d) and abs(d) <= STEP + 1e-9:
            if inv_N != 'FAIL':
                inv_N = 'ZERO_ACT'
            msgs.append(f"{k}:N2_lvl={s['n2']},挂陷={s['n_notch']},ΔMSG={d:+.2f}"
                        f" ⇒ **NHS 全程零动作**(合法的不利结果,计入统计)")
        else:
            inv_N = 'FAIL'
            msgs.append(f"{k}:N2_lvl={s['n2']},挂陷={s['n_notch']},ΔMSG={d:+.2f}"
                        f" ⇒ ⛔零动作却有收益 = **B-1 的形状**,收益来自别处")
    return inv_O, inv_N, ' | '.join(msgs)


def main():
    t_all = time.time()
    assert T_MAX < nhs.Params().lift_after_s, \
        "T_MAX 必须 < lift_after_s,否则臂 O 的预挂槽会在窗内 LIFT ⇒ 被测对象在窗内改变"
    W("未经 critic 评审 —— r64 · 自由槽位起振扫描 + T_OBS 自适应阶梯(B-1(b))")
    W("deps: nhs.py@706b658842d84316 clrig.py@8ad47ce8d260dd18 "
      "howl_detect.py@fd63e901f2d8be33 msg_meter.py@a0c16fd22b29f083")
    W("      r57_bandlimit.py@74036010b514080d r61_bwoct_baseline.py@830f15326cf264f6 "
      "dmsg_two_arm.py@53067e5a6a0c3cb5")
    W("[L2/宿主仿真]  预注册 = PREREG_r64.txt(跑前落盘)")
    W("  + §9「跑前修订 A」 A-1 INV-N 改三分(零动作是**合法的不利结果**,不得剔除)/ "
      "A-2 Hp2 拆 a·b / A-3 未收敛条另计一行")
    W("  + §10「跑前修订 B」 B-1 INV-O 改**构造精确**(挂陷8 ∧ 频点==picks;旧 `N2_lvl==0` "
      "降为诊断量,证据 r65)/ B-2 作废**按臂不按行** / B-3 臂O 构造逐档打印")
    W("  ⚠ 两次修订均在【产出任何数据之前】追加,PREREG §0–§8 一字未改(E-2)。")
    W("  ⚠ 14:13:39 曾按修订 A 版启动一次注册跑,14:18:03 主动中止(理由 = §10),**未产出输出文件**;")
    W("    日志留存为 r64_run_ABORTED_1418.log,**不得当数据引用**。")
    W(f"工作点:fs=48k / frame={FRAME} / f_cut={F_CUT:.0f}(**对被控对象的前提**,非评价频段) / "
      f"STEP={STEP} / bw_oct=1/5(锁死) / depth={DEPTH}(臂O) / 8 槽全空(臂N,Na) / nfft=2^18")
    W(f"阶梯:T_OBS ∈ {LADDER} s;C1 T_req=6.0×max(1,120/f_min);C2 |ΔΔ|<{CONV_TOL} dB;"
      f"T_MAX={T_MAX} < lift_after_s=60 ✓")
    W("三臂:O=神谕选点(**上界**,T_low=999) / N=NHS自选+有duck(产品实际) / "
      "Na=NHS自选+duck消融(陷波真实贡献)")
    W("⛔ 本轮不扫 bw_oct、不做 M-1 等代价对照(r61 已结算)、不做 SD ⇒ 任何数都不构成『净收益』")
    W()

    rows = []
    for (T60, sd) in SEEDS:
        t0 = time.time()
        h0, D = clrig.make_F(T60=T60, delay_ms=8., seed=sd)
        hb = band_limit(h0, F_CUT)
        he = clrig.h_eff(hb)
        picks = pick_excl(he, BW_OCT, 8)
        pk = sorted(round(float(p), 1) for p in picks[:8])   # INV-O 的比对基准(修订 B-1)
        anchor = MSGMeter(he, FS).msg(slots=(), g_duck_db=0.)['full']['msg_db']
        W("=" * 118)
        W(f"### T60={T60} / seed={sd}   anchor(MSG_全带解析)={anchor:+.3f} dB   "
          f"[{time.strftime('%H:%M:%S')}]")
        W("=" * 118)
        W(f"{'T_OBS':>7}{'m0':>8}{'ΔMSG_上界':>11}{'ΔMSG_自选':>11}{'ΔMSG_自选':>11}"
          f"{'f_min':>9}{'T_req':>8}  {'C1':>3} {'C2':>3}")
        W(f"{'(s)':>7}{'':>8}{'@带限8k':>11}{'@有duck':>11}{'@duck消融':>11}"
          f"{'(Hz)':>9}{'(s)':>8}")
        ladder, prev, conv_at = [], None, None
        for T in LADDER:
            rg = run_rung(hb, D, picks, anchor, T60, sd, T, prev)
            c1 = np.isfinite(rg['t_req']) and (T >= rg['t_req'] - 1e-9)
            if ladder:
                p = ladder[-1]['res']
                c2 = all(np.isfinite(rg['res'][k]['d']) and np.isfinite(p[k]['d'])
                         and abs(rg['res'][k]['d'] - p[k]['d']) < CONV_TOL
                         for k in ('O', 'N', 'Na'))
            else:
                c2 = False
            rg['c1'], rg['c2'] = bool(c1), bool(c2)
            ladder.append(rg)
            r = rg['res']
            W(f"{T:>7.0f}{r['m0']['m']:>8.2f}{r['O']['d']:>11.2f}{r['N']['d']:>11.2f}"
              f"{r['Na']['d']:>11.2f}{rg['f_min']:>9.1f}{rg['t_req']:>8.1f}"
              f"  {'✓' if c1 else '✗':>3} {'✓' if c2 else '✗':>3}")
            W(f"        f_trig: m0={r['m0']['f_trig']:.1f} O={r['O']['f_trig']:.1f} "
              f"N={r['N']['f_trig']:.1f} Na={r['Na']['f_trig']:.1f} Hz"
              + (f"   ⚠回落重扫:{','.join(rg['fallbacks'])}" if rg['fallbacks'] else "")
              + (f"   ⚠status:{ {k: r[k]['status'] for k in r if r[k]['status'] != 'ok'} }"
                 if any(r[k]['status'] != 'ok' for k in r) else ""))
            inv_O, inv_N, inv_s = invariants(rg, pk)
            rg['inv_O'], rg['inv_N'] = inv_O, inv_N
            W(f"        不变量[O:{inv_O} | N:{inv_N}]: {inv_s}")
            for k, nm in (('O', 'O '), ('N', 'N '), ('Na', 'Na')):
                s = r[k]['st']
                if s:
                    W(f"        臂{nm}: 挂陷 {s['n_notch']} 个 @{s['fr'][:8]}  "
                      f"g_duck最深 {s['gmin']:+.2f} dB"
                      + (f"  preempt={s['preempt']}" if k == 'O' else ""))
            prev = {k: r[k]['m'] for k in r}
            if c1 and c2:
                conv_at = T
                break
        fin = ladder[-1]
        W(f"  ⇒ 收敛:{'✅ T_OBS=' + str(int(conv_at)) + ' s' if conv_at else '⛔ 未收敛@%ds' % int(T_MAX)}"
          f"   不变量 O:{fin['inv_O']} / N:{fin['inv_N']}(**按臂作废,不按行**,修订 B-2)"
          f"   [{time.time()-t0:.0f} s]")
        rep = DMSGReport(
            workpoint=dict(选点来源='臂O=解析神谕|臂N/Na=NHS自选', T_low='臂O=999|臂N/Na=-45',
                           f_cut=F_CUT, T_OBS=fin['T'], bw_oct=BW_OCT, depth=DEPTH,
                           槽数=8, seed=sd, T60=T60, STEP=STEP, duck='N=不消融|Na=消融',
                           f_min_Hz=round(float(fin['f_min']), 1)),
            oracle=fin['res']['O']['d'], nhs_self=fin['res']['N']['d'], flat=None,
            nhs_self_note=f"臂Na(duck消融) {fin['res']['Na']['d']:.2f} dB;"
                          f"duck 贡献 {fin['res']['N']['d'] - fin['res']['Na']['d']:+.2f} dB")
        W("  " + rep.format().replace("\n", "\n  "))
        W()
        rows.append(dict(T60=T60, sd=sd, conv_at=conv_at, fin=fin, ladder=ladder,
                         anchor=anchor))

    # ── 汇总(⛔ 只有阈值比较,无结论散文)────────────────────────────
    W("=" * 118)
    W("§S  汇总表 —— 六条种子 × 收敛档   ⛔ 未经 critic 评审")
    W("=" * 118)
    W(f"{'T60':>5}{'sd':>4}{'收敛T_OBS':>10}{'f_trig(该档f_min)':>18}"
      f"{'ΔMSG_自选@有duck':>18}{'ΔMSG_自选@消融':>16}{'ΔMSG_上界@神谕':>16}"
      f"{'挂陷':>5}{'duck参与':>9}{'≥4dB?':>7}{'≥5dB?':>7}{'INV_O':>7}{'INV_N':>9}")
    for r in rows:
        f = r['fin']
        rr = f['res']
        st = rr['N']['st']
        dN, dNa, dO = rr['N']['d'], rr['Na']['d'], rr['O']['d']
        # 修订 A-1:ZERO_ACT 是**合法的不利结果**,照常计入;只有 FAIL 才剔除
        # 修订 B-2:达标统计只看 INV_N,**与 INV_O 无关**(按臂作废,不按行)
        usable = (r['conv_at'] is not None) and (f['inv_N'] != 'FAIL') and np.isfinite(dN)
        r['usable'] = usable
        r['o_usable'] = (r['conv_at'] is not None) and (f['inv_O'] != 'FAIL') and np.isfinite(dO)
        g4 = ('✓' if dN >= TARGETS[0] else '✗') if usable else '—'
        g5 = ('✓' if dN >= TARGETS[1] else '✗') if usable else '—'
        W(f"{r['T60']:>5.1f}{r['sd']:>4}"
          f"{(str(int(r['conv_at'])) + 's') if r['conv_at'] else '未收敛':>10}"
          f"{f['f_min']:>18.1f}{dN:>18.2f}{dNa:>16.2f}{dO:>16.2f}"
          f"{(st['n_notch'] if st else -1):>5}"
          f"{('是 %.1f' % st['gmin']) if (st and st['gmin'] < 0) else '否':>9}"
          f"{g4:>7}{g5:>7}{f['inv_O']:>7}{f['inv_N']:>9}")
    W()
    W("  INV_N 三档(修订 A-1):OK=动作发生 / ZERO_ACT=NHS 全程零动作(**合法的不利结果,"
      "照常计入统计**)/ FAIL=零动作却有收益 = B-1 形状,该列作废")
    W("  INV_O 两档(修订 B-1,**构造精确**):OK=挂陷8 且频点==picks(未发生新分配)/ FAIL=构造已散")
    W("    ⚠ 旧判据 `N2_lvl==0` 已降级为诊断量 —— `nhs.py:396-401` 对**已覆盖 bin** 的维持路径")
    W("      门是 `T_low_gr=−65`(不是 999),`r65` 实测 Δ=+8dB 时 N2_lvl=611/374 而构造完好。")
    W("  ⇒ **按臂作废,不按行**(修订 B-2):INV_O FAIL 只作废『上界』列,不动『自选』两列。")
    W("  列名(D6-t 全限定,⛔ 不得简称为裸 ΔMSG):")
    W("    ΔMSG_自选@有duck  = ΔMSG_实测@带限8k_NHS自选_有duck_[L2/宿主仿真]")
    W("    ΔMSG_自选@消融    = ΔMSG_实测@带限8k_NHS自选_duck消融_[L2/宿主仿真]")
    W("    ΔMSG_上界@神谕    = ΔMSG_上界@带限8k_神谕选点_[L2/宿主仿真]  ⛔ 禁称『NHS 实测』")
    W()

    # 分层(M-2:⛔ 不报跨层均值)
    W("§S2  分层报(M-2:均值不得跨过受控因子 T60)")
    for lay in (0.2, 0.5):
        sel = [r for r in rows if r['T60'] == lay]
        for nm, key in (('ΔMSG_自选@有duck', 'N'), ('ΔMSG_自选@消融', 'Na'),
                        ('ΔMSG_上界@神谕', 'O')):
            ok = 'o_usable' if key == 'O' else 'usable'      # 修订 B-2:按臂
            v = [r['fin']['res'][key]['d'] for r in sel
                 if r[ok] and np.isfinite(r['fin']['res'][key]['d'])]
            if v:
                W(f"  T60={lay}  {nm:<18} n={len(v)}/3  逐条 {[round(x,2) for x in v]}  "
                  f"取值范围 [{min(v):.2f}, {max(v):.2f}]  中位 {np.median(v):.2f}")
            else:
                W(f"  T60={lay}  {nm:<18} n=0/3  ⛔ 无可用条(未收敛或 INV-FAIL)")
    W("  ⛔ 不报跨层均值(T60 是受控因子;r61 实测两层差 1.67 dB)")
    W()
    usable = [r for r in rows if r['usable']]
    W(f"§S3  达标计数(对表列 = ΔMSG_实测@带限8k_NHS自选_**有duck**_[L2];"
      f"可用条 {len(usable)}/6)")
    for th in TARGETS:
        hit = [r for r in usable if r['fin']['res']['N']['d'] >= th]
        W(f"  ≥{th:.0f} dB:{len(hit)}/{len(usable)} 条"
          f"  —— {[(r['T60'], r['sd']) for r in hit]}")
    # 修订 A-3:未收敛条另给一行,免得"只报主统计"把不利数据挡在门外
    nc = [r for r in rows if not r['usable'] and np.isfinite(r['fin']['res']['N']['d'])]
    if nc:
        W(f"  ⤷ 另计:把 {len(nc)} 条未收敛/INV-FAIL 的条**按其最后一档({int(T_MAX)}s)读数**"
          f"计入后(修订 A-3,防止只报主统计把不利数据挡在门外):")
        allr = usable + nc
        for th in TARGETS:
            hit = [r for r in allr if r['fin']['res']['N']['d'] >= th]
            W(f"     ≥{th:.0f} dB:{len(hit)}/{len(allr)} 条  —— "
              f"未收敛条读数 {[(r['T60'], r['sd'], round(r['fin']['res']['N']['d'], 2)) for r in nc]}")
    else:
        W("  ⤷ 无未收敛 / INV-FAIL 条 ⇒ 修订 A-3 的第二统计与主统计相同。")
    W("  ⚠ 该列含最深 −6 dB 的**宽带兜底(g_duck)**;其音质代价 SD 未仪表化")
    W("    ⇒ 它不是『纯陷波收益』,也不构成『净收益』。扣掉兜底的数见『@消融』列。")
    W("  ⚠ 全部数成立于『环路在 8 kHz 以上被带限』这一**对被控对象的前提**,该前提无 [L1/L2] 依据。")
    W()
    W("§S4  预注册假设逐条对表(⚠ 判读文字由人在看到数之后写,本节只给机械事实)")
    hp1 = [(r['T60'], r['sd']) for r in rows
           if np.isfinite(r['fin']['res']['N']['d']) and np.isfinite(r['fin']['res']['O']['d'])
           and r['fin']['res']['N']['d'] >= r['fin']['res']['O']['d']]
    W(f"  Hp1 臂N ≥ 臂O 的条数(证伪条件:≥1):{len(hp1)}  {hp1}")
    W(f"  INV_O 汇总(修订 B-1 构造精确判据):"
      f"{[(r['T60'], r['sd'], r['fin']['inv_O']) for r in rows]}")
    up = {'O': [], 'NNa': []}
    for r in rows:
        for a, b in zip(r['ladder'], r['ladder'][1:]):
            for k in ('O', 'N', 'Na'):
                if np.isfinite(a['res'][k]['d']) and np.isfinite(b['res'][k]['d']) \
                        and b['res'][k]['d'] - a['res'][k]['d'] >= STEP:
                    up['O' if k == 'O' else 'NNa'].append(
                        (r['T60'], r['sd'], k, a['T'], b['T'],
                         round(a['res'][k]['d'], 2), round(b['res'][k]['d'], 2)))
    W(f"  Hp2a 臂 O(固定滤波器)ΔMSG 随 T_OBS 上升 ≥1 阶梯(证伪条件:≥1):"
      f"{len(up['O'])}  {up['O']}")
    W(f"  Hp2b 臂 N/Na(自适应)同上 —— **修订 A-2 后不预测方向,仅记录**:"
      f"{len(up['NNa'])}  {up['NNa']}")
    W("       (成因两向相反:窗长⇒更易抓起振使 m 降;窗长⇒NHS 有时间加深使 m 升)")
    W("  Hp2· 逐条 ΔMSG_自选@有duck 随 T_OBS 的完整轨迹(判断 NHS 建立是否已被窗覆盖):")
    for r in rows:
        traj = [(int(g['T']), round(g['res']['N']['d'], 2)) for g in r['ladder']]
        W(f"       T60={r['T60']}/sd={r['sd']}: {traj}")
    slow = [(r['T60'], r['sd'], round(float(r['fin']['f_min']), 1), r['conv_at'])
            for r in rows if r['conv_at'] and r['conv_at'] >= 24.]
    W(f"  Hp3 需 T_OBS≥24s 才收敛的条及其 f_min:{slow}")
    duck = [(r['T60'], r['sd'], round(r['fin']['res']['N']['d'] - r['fin']['res']['Na']['d'], 2))
            for r in rows]
    W(f"  Hp4 duck 贡献(有duck − 消融)逐条:{duck}")
    W(f"  Hp5 见 §S3。")
    W()
    W(f"总耗时 {time.time()-t_all:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(OUT_PATH, 'w') as fp:
        fp.write("\n".join(OUT) + "\n")


if __name__ == '__main__':
    main()
