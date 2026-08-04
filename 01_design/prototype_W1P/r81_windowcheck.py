"""r81 · **窗长有效性回溯复核** —— 把 r80b 那条诊断回溯跑到已报的关键列上。
⛔ 未经 critic 评审。[L2/宿主仿真]。输出 r81_windowcheck_out.txt(D6-j)。

判据(架构侧 v0.44 的通用形式 + 我方 r80b 已验证的那个):
  凡在【固定观测窗】内取"终点值"作稳定值的测量,须报:
    ① **到峰时刻 / 窗长**   ≥ 0.7 ⇒ 判窗不足 ⇒ 该列**只能作上界**
    ② **末秒 − 首秒 RMS**   在衰 ⇒ 干净;在涨 ⇒ 只能作上界
  (r80b 已用 ② 判出:陷波臂 −5.87 dB 在衰;频移臂 +0.77…+4.32 在涨)

⚠ 本件**不重跑扫描** —— 直接取已落盘 json 里的终点 G(= m0 + ΔMSG),在该 G 上跑**一次**,
  复算包络。⇒ 成本 = 每列每种子 1 次闭环,而不是一次扫描。

覆盖(lead 定的优先级):
  ① B-1 条件:src=−60,**T_OBS=6**(r76)      ← 可能动到已报头条
  ② 标称 −20 的 12 s 档(2.00–6.00 dB 那列)
  ③ r78 C1(1/5)/ r79 N08(1/8)的 12 s 档
⛔ 本文件不含结论性散文。
"""
import sys, json, glob, time
sys.path.insert(0, '/home/it1234/processor/01_design/prototype_W1P')
import numpy as np
import clrig, howl_detect as HD, nhs
from nhs import NHS
from clrig import FS
from r57_bandlimit import band_limit
from r61_bwoct_baseline import pick_excl, mk_oracle, GR, FRAME

DIR = '/home/it1234/processor/01_design/prototype_W1P/'
SEEDS = [(0.2, 0), (0.2, 1), (0.2, 2), (0.5, 0), (0.5, 1), (0.5, 2)]
OUT = []


def W(s=''):
    OUT.append(s)
    print(s)
    sys.stdout.flush()


def mk_self(bw, tlow, ablate=True):
    a = NHS()
    a.P.bw_oct = bw
    a.P.T_low = tlow
    a.P.prefer_unnotched = False
    if ablate:
        a.duck_gain = lambda: 1.0
    return a


def envelope_stats(lp, T):
    """返回 (末秒−首秒 dB, 到峰时刻/窗长)。"""
    n = (len(lp) // FRAME) * FRAME
    lv = np.array([HD.rms_db(lp[i:i + FRAME]) for i in range(0, n, FRAME)])
    k = int(FS)
    grow = float(HD.rms_db(lp[-k:]) - HD.rms_db(lp[:k]))
    # 到峰时刻:用滑动 0.5 s 平均后的最大值位置,避免单帧尖峰
    win = max(1, int(0.5 * FS / FRAME))
    sm = np.convolve(lv, np.ones(win) / win, mode='valid')
    t_peak = (int(np.argmax(sm)) + win) * FRAME / FS
    return grow, float(t_peak / T)


def run_at(hb, D, G, src, arm, bw, tlow, picks=None, depth=-18.):
    if arm == 'm0':
        pf = None
    elif arm == 'Na':
        a = mk_self(bw, tlow, True)
        pf = lambda b, _a=a: _a.process_frame(b, GR)
    elif arm == 'O':
        a = mk_oracle(picks, bw, depth)
        pf = lambda b, _a=a: _a.process_frame(b, GR)
    _, lp = clrig.Loop(hb, D, G, proc=pf).run(src, FRAME)
    return lp


def main():
    t0 = time.time()
    W("未经 critic 评审 —— r81 · 窗长有效性【回溯复核】  [L2/宿主仿真]")
    W("判据:①到峰时刻/窗长 ≥ 0.7 ⇒ 窗不足 ⇒ 只能作上界;②末秒−首秒 RMS 在涨 ⇒ 只能作上界")
    W("⚠ 本件**不重跑扫描**,只在已落盘的终点 G 上各跑一次复算包络。")
    W("⚠ 参照点(r80b 已验):Δf=0 的纯陷波臂在其终点 G 上 **−5.87 dB(在衰)** ⇒ 干净的样子长这样")
    W("")
    R76 = []
    for p in glob.glob(DIR + 'r76_cell_*.json'):
        R76 += json.load(open(p))
    K76 = {(r['src'], r['fix'], r['tlow'], r['T60'], r['sd'], r['T']): r for r in R76}
    rows = []
    for src_db, T, label in ((-60., 6., '① B-1 条件 src=−60 T_OBS=**6 s**'),
                             (-60., 12., '   同上 T_OBS=12 s(对照)'),
                             (-20., 6., '② 标称 −20 T_OBS=6 s'),
                             (-20., 12., '② 标称 −20 T_OBS=**12 s**(= 2.00–6.00 dB 那一列)')):
        W("=" * 104)
        W(f"{label}   修法关 / T_low=−45 / bw_oct=1/5 / duck 消融(兜底消融列)")
        W("=" * 104)
        W(f"{'T60':>5}{'sd':>4}{'ΔMSG':>8}{'终点G':>9}"
          f"{'臂Na 末−首dB':>14}{'到峰/窗':>9}{'判定':>22}"
          f"{'臂m0 末−首':>12}{'m0到峰/窗':>11}")
        for (T60, sd) in SEEDS:
            rec = K76.get((src_db, 0, -45., T60, sd, T))
            if rec is None or not np.isfinite(rec['dA']):
                continue
            h0, D = clrig.make_F(T60=T60, prop_delay_ms=8., seed=sd)
            hb = band_limit(h0, 8000.)
            s = np.random.default_rng(sd).standard_normal(int(T * FS)) * (10 ** (src_db / 20.))
            G = rec['m0'] + rec['dA']
            lp = run_at(hb, D, G, s, 'Na', 1 / 5, -45.)
            g, tp = envelope_stats(lp, T)
            lp0 = run_at(hb, D, rec['m0'], s, 'm0', 1 / 5, -45.)
            g0, tp0 = envelope_stats(lp0, T)
            verdict = ('**⛔ 只能作上界**' if (g > 0 or tp >= 0.7) else '✅ 干净')
            W(f"{T60:>5.1f}{sd:>4}{rec['dA']:>8.2f}{G:>9.2f}"
              f"{g:>+14.2f}{tp:>9.2f}{verdict:>22}{g0:>+12.2f}{tp0:>11.2f}")
            rows.append(dict(src=src_db, T=T, T60=T60, sd=sd, dA=rec['dA'], G=float(G),
                             grow=g, tpeak_ratio=tp, grow_m0=g0, tpeak_m0=tp0,
                             upper_only=bool(g > 0 or tp >= 0.7)))
        W("")
    W("=" * 104)
    W("§V 汇总(机械,⛔ 判读文字由人在看到数之后写)")
    W("=" * 104)
    for src_db, T in ((-60., 6.), (-60., 12.), (-20., 6.), (-20., 12.)):
        v = [r for r in rows if r['src'] == src_db and r['T'] == T]
        if not v:
            continue
        nb = sum(1 for r in v if r['upper_only'])
        W(f"  src={int(src_db)} T_OBS={T:.0f}s: **{nb}/{len(v)} 条判为「只能作上界」**"
          f"   末−首 dB 逐条 {[round(r['grow'], 2) for r in v]}"
          f"   到峰/窗 逐条 {[round(r['tpeak_ratio'], 2) for r in v]}")
    W("")
    W(f"  参照:m0 臂 末−首 dB 逐条 {[round(r['grow_m0'], 2) for r in rows[:6]]}"
      f"(m0 臂无算法动作,其形态是「干净」的基准)")
    W("")
    W(f"总耗时 {time.time()-t0:.0f} s。⛔ 未经 critic 评审;本文件不含结论性判读。")
    with open(DIR + 'r81_windowcheck_out.txt', 'w') as fp:
        fp.write("\n".join(OUT) + "\n")
    with open(DIR + 'r81_windowcheck.json', 'w') as fp:
        json.dump(rows, fp)


if __name__ == '__main__':
    main()
